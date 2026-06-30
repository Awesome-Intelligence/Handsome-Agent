#!/usr/bin/env python3
# 🧠 Decision - Agent 主入口

"""
Agent Core - Agent 核心实现

使用统一的 AgentLoop 处理所有用户输入，LLM 自主决定是否调用工具、何时结束。
"""

import sys
import os
import json
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from dataclasses import dataclass as dc

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from enum import Enum

from agent.session import session_manager, Session, Message
from tools.integrated_tools import get_integrated_engine, initialize_tools
from common.logging_manager import (
    get_decision_logger,
    get_llm_logger,
    set_log_level,
)

from agent.curator import Curator, SkillWriter
from agent.curator.trajectory import Trajectory, TrajectoryManager
from agent.goal import GoalManager
from agent.checkpoint import get_checkpoint_manager
from agent.state import AgentState, AgentStatus


class ActionType(Enum):
    TOOL_CALL = "tool_call"
    DIRECT_RESPONSE = "direct_response"
    CLARIFICATION = "clarification"


logger = logging.getLogger(__name__)


@dataclass
class AgentResponse:
    content: str
    tool_used: Optional[str] = None
    tool_result: Optional[Any] = None
    confidence_score: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0


class Agent:
    """
    Agent - 使用统一的 AgentLoop 处理所有用户输入

    特点：
    1. 统一循环：LLM 自主决策
    2. 使用 LLM 直接做工具选择决策
    3. 整合了 ToolRegistry 中的所有工具
    4. 支持会话管理（自动检测今日会话）
    5. 支持记忆系统
    """

    def __init__(
        self,
        llm_provider=None,
        enable_session: bool = True,
        session_id: Optional[str] = None,
        force_new_session: bool = False,
        enable_curator: bool = True,
        debug_logs: bool = False,
        checkpoints_enabled: bool = True,
    ):
        if debug_logs:
            set_log_level("detailed")
            logging.getLogger("TrajectoryManager").setLevel(logging.DEBUG)
            logging.getLogger("Curator").setLevel(logging.DEBUG)

        httpx_logger = logging.getLogger("httpx")
        httpx_logger.setLevel(logging.WARNING)

        self.llm_provider = llm_provider
        self.enable_session = enable_session
        self.enable_curator = enable_curator

        self._decision_logger = get_decision_logger("Agent", sublayer="task")
        self._llm_logger = get_llm_logger("Agent")

        # 初始化 TodoStore（参考 Hermes）
        from tools.todo_tool import get_session_todo_store
        self._todo_store = get_session_todo_store()

        self.engine = get_integrated_engine(llm_provider=llm_provider)

        from agent.context import ContextBuilder

        tools_dict = {t.name: t for t in self.engine.tool_selector.tools.values()}
        self._context_builder = ContextBuilder(tools=tools_dict)

        from agent.context.context_compressor import ContextCompressor

        model_name = getattr(self.llm_provider, "model", "gpt-4o")
        self._context_compressor = ContextCompressor(
            model=model_name,
            threshold_percent=0.75,
            protect_first_n=3,
            protect_last_n=10,
            summary_target_ratio=0.20,
            quiet_mode=True,
            llm_client=self.llm_provider,
        )

        from agent.context import ContextManager

        self._context_manager = ContextManager(
            context_compressor=self._context_compressor,
            context_builder=self._context_builder,
        )

        from agent.llm import LLMClient, LLMAuxConfig

        self._llm_client = LLMClient(
            llm_provider=llm_provider,
            context_manager=self._context_manager,
            aux_config=LLMAuxConfig(),
        )

        self.engine._context_manager = self._context_manager
        self.engine._llm_client = self._llm_client

        self._session: Optional[Session] = None
        if self.enable_session:
            if session_id == "last" or session_id is None and not force_new_session:
                self._session = session_manager.get_or_create_today_session()
                if session_manager.get_latest_today_session():
                    self._decision_logger.info(
                        f"Continuing today's session: {self._session.session_id}"
                    )
                else:
                    self._decision_logger.info(
                        f"Created new session: {self._session.session_id}"
                    )
            else:
                self._session = session_manager.create_session(session_id)
                self._decision_logger.info(f"Resumed session: {session_id}")

        self._stream_callback = None
        self._stream_emitter = None

        # ── 加载 Tool Loop Guardrail 配置 ──
        tool_loop_config = None
        try:
            from common.config import get_settings
            settings = get_settings()
            if hasattr(settings, "tool_loop_guardrail") and settings.tool_loop_guardrail:
                from agent.rails.tool_loop import ToolLoopConfig
                tool_loop_config = ToolLoopConfig.from_mapping(settings.tool_loop_guardrail)
                self._decision_logger.debug(f"ToolLoopConfig loaded from settings")
        except Exception as e:
            self._decision_logger.debug(f"Failed to load ToolLoopConfig: {e}")

        # 统一状态管理器（替代 InterruptController, BudgetController, LoopExitChecker）
        # 参考 Hermes：父代理默认 90 次迭代
        self._state = AgentState(max_iterations=90, max_turns=90, tool_loop_config=tool_loop_config)

        from tools.todo_tool import get_session_todo_store

        self._todo_store = get_session_todo_store()

        # 初始化 GoalManager（与 AgentState 关联）
        session_id = self._session.session_id if self._session else "default"
        self._goal_manager = GoalManager(
            session_id=session_id,
            judge_llm_provider=llm_provider,
            default_max_turns=90,  # 参考 Hermes：父代理默认 90 次
            on_state_change=self._state.sync_from_goal_state,
        )
        self._decision_logger.debug(f"GoalManager initialized for session: {session_id}")
        
        # 将 GoalManager 关联到 AgentState
        self._state.set_goal_manager(self._goal_manager)

        # 初始化 CheckpointManager
        self._checkpoint_manager = get_checkpoint_manager(enabled=checkpoints_enabled)
        if checkpoints_enabled:
            self._decision_logger.info("Checkpoint enabled for dangerous operations")

        # Rails 注册跟踪（避免重复注册）
        # Rails 在首次使用时注册，保持与其他组件一致的初始化模式
        self._rails_registered_sessions: set = set()

        self._init_trajectory_and_curator()

    def interrupt(self):
        self._decision_logger.warning("中断请求已触发")
        self._state.request_interrupt("user_requested")

        if self._stream_emitter:
            from common.streaming import ErrorEvent

            self._stream_emitter.emit_error("用户请求中断", "InterruptedError")
            self._stream_emitter.interrupt()

    def is_interrupted(self) -> bool:
        return self._state.is_interrupt_requested

    def clear_interrupt(self):
        self._state.clear_interrupt()
        if self._stream_emitter:
            self._stream_emitter.clear_interrupt()

    def _ensure_rails_registered(self, session_id: str) -> None:
        """
        确保 Rails 已注册（延迟初始化模式）

        设计原则（参考 Hermes）：
        - 统一在 Agent 级别管理 Rails 初始化
        - 避免每次 chat() 调用时重复注册
        - 与 AgentState、GoalManager 等组件保持一致的初始化模式

        Args:
            session_id: 会话 ID
        """
        if session_id in self._rails_registered_sessions:
            # 已注册，跳过
            return

        try:
            from agent.rails.registry import get_rail_registry
            rail_registry = get_rail_registry()

            # 创建并注册 TaskEventRail（如果未注册）
            if not rail_registry.has_rail(session_id, "task_event"):
                from agent.rails import TaskEventRail
                task_rail = TaskEventRail(session_id)
                rail_registry.register(session_id, task_rail)
                self._decision_logger.debug(f"Registered TaskEventRail for session: {session_id}")

            # 创建并注册 CheckpointRail（如果未注册）
            if not rail_registry.has_rail(session_id, "checkpoint"):
                from agent.rails.checkpoint_rail import CheckpointRail
                checkpoint_rail = CheckpointRail(
                    session_id,
                    enabled=self._checkpoint_manager.is_enabled(),
                    checkpoint_manager=self._checkpoint_manager,
                )
                rail_registry.register(session_id, checkpoint_rail)
                self._decision_logger.debug(f"Registered CheckpointRail for session: {session_id}")

            # 标记为已注册
            self._rails_registered_sessions.add(session_id)

        except Exception as e:
            self._decision_logger.warning(f"Rail 初始化失败: {e}")

    @property
    def state(self) -> AgentState:
        """获取统一状态管理器"""
        return self._state

    def set_stream_callback(self, callback):
        self._stream_callback = callback

    def set_thinking_callback(self, callback):
        self._thinking_callback = callback

    def set_stream_emitter(self, emitter):
        self._stream_emitter = emitter

    def _emit_stream(self, text: str):
        if text:
            if self._stream_callback:
                self._stream_callback(text)
            if self._stream_emitter:
                self._stream_emitter.emit_delta(text)

    def _emit_stream_complete(self, text: str = ""):
        if self._stream_emitter:
            self._stream_emitter.emit_complete(text)

    def _init_trajectory_and_curator(self):
        self._trajectory_manager = TrajectoryManager()

        self._curator = None
        if self.enable_curator:
            try:
                self._curator = Curator(
                    skill_writer=SkillWriter(),
                    enable_auto_learn=True,
                )
                self._decision_logger.info("Curator enabled for self-improvement")
            except Exception as e:
                self._decision_logger.warning(f"Failed to initialize Curator: {e}")

    async def _process_trajectory_async(self, response: AgentResponse):
        trajectory_metadata = {
            "trajectory_id": f"traj_{self._session.session_id if self._session else 'unknown'}",
            "session_id": self._session.session_id if self._session else "unknown",
            "confidence_score": response.confidence_score,
            "execution_time": response.execution_time,
            "success": response.confidence_score > 0.5,
            "tool_used": response.tool_used,
        }

        # 一次性从 Session 创建 Trajectory 对象
        trajectory = Trajectory.from_session(self._session, metadata=trajectory_metadata)

        # Curator 处理轨迹（不保存）
        if self._curator and self.enable_curator:
            try:
                result = await self._curator.process_trajectory(
                    {
                        **trajectory_metadata,
                        "messages": trajectory.messages,
                    }
                )
                if result:
                    trajectory_metadata["curator_result"] = {
                        "skill_synthesized": len(result.get("skills", [])) > 0,
                        "skill_name": result["skills"][0].name if result.get("skills") else None,
                    }
                    self._decision_logger.info("Trajectory processed by Curator")
            except Exception as e:
                self._decision_logger.warning(f"Curator 处理失败: {e}")
                trajectory_metadata["curator_error"] = str(e)

        # 使用 TrajectoryManager 保存轨迹
        save_path = self._trajectory_manager.save(trajectory, metadata=trajectory_metadata)
        self._decision_logger.debug(f"Trajectory saved to {save_path}")

    async def chat(
        self,
        user_input: str,
        conversation_history: Optional[List[Dict]] = None,
        enable_stream: bool = False,
        stream_callback=None,
    ) -> AgentResponse:
        """
        处理用户输入（主要接口）

        使用统一的 AgentLoop 处理所有输入：
        - LLM 自主决定是否调用工具、调用哪些工具、何时结束
        - 简单问答：LLM 直接回答，循环一轮结束
        - 复杂任务：LLM 链式调用多个工具，循环多轮结束

        设计原则：
        - 意图理解使用 LLM 动态判断，禁止硬编码关键词
        - 任务完成由 LLM 自主判断何时结束
        - 无显式的 Goal 模式，简化处理流程

        Args:
            user_input: 用户输入
            conversation_history: 可选的对话历史
            enable_stream: 是否启用流式输出
            stream_callback: 流式输出回调函数，签名为 on_delta(text: str)

        Returns:
            AgentResponse
        """
        start_time = time.time()
        self._decision_logger.info(f"User input: {user_input[:50]}...")

        if stream_callback:
            self.set_stream_callback(stream_callback)

        if enable_stream and not stream_callback:
            self._setup_default_stream()

        if conversation_history is None:
            conversation_history = self._get_session_messages()

        # 记录原始历史消息数，用于只添加新生成的消息
        history_count = len(conversation_history)

        result = await self._run_loop(user_input, conversation_history)

        final_result = result.get("final_result", "")
        iterations = result.get("iterations", 0)
        final_action = result.get("final_action", "")

        if isinstance(final_result, dict):
            final_result = json.dumps(final_result, ensure_ascii=False)

        if self._session:
            full_messages = result.get("full_messages", [])
            if full_messages:
                # 只添加新生成的消息（超出原始历史的那些）
                # 避免重复添加已存在于 session 中的历史消息
                for msg in full_messages[history_count:]:
                    role = msg.get("role")
                    content = msg.get("content", "")
                    tool_calls = msg.get("tool_calls")
                    tool_call_id = msg.get("tool_call_id")
                    if role and (content or tool_calls):
                        self._session.add_message(
                            role=role,
                            content=content,
                            tool_calls=tool_calls,
                            tool_call_id=tool_call_id,
                        )
            else:
                self._session.add_message("assistant", str(final_result))

        execution_time = time.time() - start_time

        self._decision_logger.info(
            f"[/✅Task] 循环完成，迭代 {iterations} 次，耗时 {execution_time:.2f}s"
        )

        response_obj = AgentResponse(
            content=str(final_result),
            confidence_score=0.9,
            metadata={"iterations": iterations, "final_action": final_action},
        )
        response_obj.execution_time = execution_time

        await self._process_trajectory_async(response_obj)

        return response_obj

    async def _run_loop(
        self,
        user_input: str,
        conversation_history: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        运行 AgentLoop（使用单一循环）

        核心流程：
        1. 检测 /goal 命令，创建或恢复 Goal
        2. 配置预算和退出检查器
        3. 调用 AgentLoop.run() 执行单一循环

        设计原则：
        - /goal 命令用于创建复杂任务的 Standing Goal
        - Judge 机制确保复杂任务被完整执行
        - LLM 自主决定是否调用工具、调用哪些工具
        - 循环控制统一在 AgentLoop.run() 中

        Args:
            user_input: 用户输入
            conversation_history: 可选的对话历史

        Returns:
            循环执行结果字典
        """
        from agent.execution import AgentLoop, ExecutionContext
        from agent.rails import TaskEventRail

        session_id = self._session.session_id if self._session else "default"

        # ─────────────────────────────────────────────────────────────────
        # 1. 检测 /goal 命令，创建或更新 Goal（参考 Hermes，GoalManager 统一管理）
        # ─────────────────────────────────────────────────────────────────
        effective_input = user_input

        if user_input.startswith("/goal"):
            # 解析 /goal 命令（注意：子命令判断必须从长到短，避免前缀匹配错误）
            if user_input.startswith("/goal clear"):
                self._goal_manager.clear()
                self._emit_stream("🗑️ Goal 已清除\n\n")
                return {"success": True, "state": "goal_cleared", "final_result": "Goal cleared"}
            elif user_input.startswith("/goal pause"):
                reason = user_input[11:].strip() or None
                self._goal_manager.pause(reason)
                self._emit_stream("⏸️ Goal 已暂停\n\n")
                return {"success": True, "state": "goal_paused", "final_result": "Goal paused"}
            elif user_input.startswith("/goal resume"):
                self._goal_manager.resume()
                # 同步预算信息到 AgentState
                if self._goal_manager.state:
                    self._state.sync_from_goal_state(self._goal_manager.state)
                self._emit_stream("▶️ Goal 已恢复\n\n")
                effective_input = "继续执行目标任务"
            elif user_input == "/goal":
                # /goal 无参数，显示状态
                status = self._goal_manager.status_line()
                self._emit_stream(f"{status}\n")
                return {"success": True, "state": "goal_status", "final_result": status}
            elif user_input.startswith("/goal "):
                # /goal <text> - 创建新目标（放在最后，避免与子命令冲突）
                goal_text = user_input[6:].strip()
                if goal_text:
                    # 由 GoalManager 统一管理 Goal 状态
                    self._goal_manager.set(goal_text)
                    # 同步预算信息到 AgentState
                    if self._goal_manager.state:
                        self._state.sync_from_goal_state(self._goal_manager.state)
                    self._decision_logger.info(f"Goal created: {goal_text[:50]}...")
                    self._emit_stream(f"📌 目标已设置: {goal_text}\n\n")
                    effective_input = "继续执行目标任务"
                else:
                    # /goal 无参数，显示状态
                    status = self._goal_manager.status_line()
                    self._emit_stream(f"{status}\n")
                    return {"success": True, "state": "goal_status", "final_result": status}

        # ─────────────────────────────────────────────────────────────────
        # 2. 尝试加载已保存的 Goal（参考 Hermes）
        # ─────────────────────────────────────────────────────────────────
        if not self._goal_manager.is_active() and session_id:
            saved_goal = self._goal_manager.load_goal(session_id)
            if saved_goal and saved_goal.status == "active":
                # 同步预算信息到 AgentState
                self._state.sync_from_goal_state(saved_goal)
                self._decision_logger.info(f"Resumed saved goal: {saved_goal.goal[:50]}...")

        # ─────────────────────────────────────────────────────────────────
        # 3. 初始化 Rails（统一使用 _ensure_rails_registered）
        # ─────────────────────────────────────────────────────────────────
        self._ensure_rails_registered(session_id)

        # ─────────────────────────────────────────────────────────────────
        # 4. 创建 ExecutionContext
        # ─────────────────────────────────────────────────────────────────
        tools = self.engine.tool_selector.get_tools_schema()
        tool_handlers = {
            t.name: t.handler for t in self.engine.tool_selector.tools.values()
        }

        context = ExecutionContext(
            task_description=effective_input,
            tools=tools,
            tool_handlers=tool_handlers,
            conversation_history=conversation_history,
        )

        # ─────────────────────────────────────────────────────────────────
        # 5. 配置状态管理器（参考 Hermes，GoalManager 统一管理 Goal）
        # ─────────────────────────────────────────────────────────────────
        goal_active = self._goal_manager.is_active()

        # 同步 Goal 预算信息到 AgentState
        if goal_active and self._goal_manager.state:
            self._state.sync_from_goal_state(self._goal_manager.state)

        # 首次执行，发送 Goal 状态
        if goal_active:
            self._emit_stream(f"🎯 {self._goal_manager.status_line()}\n\n")

        # ─────────────────────────────────────────────────────────────────
        # 6. 设置 Todo Store 到 AgentState（用于检查 todo 完成度）
        # ─────────────────────────────────────────────────────────────────
        self._state.set_todo_store(self._todo_store)

        # ─────────────────────────────────────────────────────────────────
        # 7. 创建 AgentLoop（使用 AgentState）
        # ─────────────────────────────────────────────────────────────────
        loop = AgentLoop(
            llm_provider=self.llm_provider,
            session_id=session_id,
            tools=self._context_builder.tools,
            stream_emitter=self._stream_emitter,
            context_manager=self._context_manager,
            todo_store=self._todo_store,
            agent_state=self._state,  # 使用统一状态管理器
            agent=self,  # 传递自身实例，用于工具的 parent_agent
        )

        # ─────────────────────────────────────────────────────────────────
        # 8. 启动状态并执行循环
        # ─────────────────────────────────────────────────────────────────
        self._state.start()
        result = await loop.run(context)

        # 如果 Goal 模式下添加了额外信息，记录到结果中（通过 GoalManager 获取）
        if goal_active and self._goal_manager.state:
            result["goal_status"] = self._goal_manager.state.status
            result["goal_turns"] = self._goal_manager.state.current_turn

        # 返回完整的消息历史（用于保存到 Session）
        result["full_messages"] = context.to_messages_dict()

        return result

    def _setup_default_stream(self):
        from common.streaming import ConsoleConsumer, StreamEmitter, ConsumerRegistry

        registry = ConsumerRegistry()
        registry.register(ConsoleConsumer())

        self._stream_emitter = StreamEmitter(registry)
        self._stream_emitter.start()

    def _cleanup_stream(self):
        if self._stream_emitter:
            self._stream_emitter.stop()
            self._stream_emitter = None

    def _get_session_messages(self) -> List[Dict]:
        if not self._session:
            return []

        messages = []
        for msg in self._session.messages:
            msg_dict = {"role": msg.role}
            if msg.content:
                msg_dict["content"] = msg.content
            if msg.tool_calls:
                msg_dict["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                msg_dict["tool_call_id"] = msg.tool_call_id
            messages.append(msg_dict)
        return messages

    def get_tool_list(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "category": tool.category,
            }
            for tool in self.engine.tool_selector.tools.values()
        ]


if __name__ == "__main__":
    print("Testing Agent initialization...")
    initialize_tools()

    agent = Agent(llm_provider=None)

    print(f"\n✅ Agent initialized with {len(agent.get_tool_list())} tools!")
    print("\nAvailable tools:")
    for tool in agent.get_tool_list():
        print(f"  - {tool['name']} ({tool.get('category', 'general')})")
