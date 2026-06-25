#!/usr/bin/env python3
"""
Agent Core - Agent 核心实现

使用整合后的工具系统，完全基于 LLM 驱动的决策
"""

import sys
import os
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from enum import Enum

from agent.session import session_manager, Session, Message
from tools.integrated_tools import (
    get_integrated_engine,
    initialize_tools
)
from common.logging_manager import (
    get_decision_logger,
    get_llm_logger,
    set_log_level,
)

from agent.curator.trajectory_recorder import TrajectoryRecorder
from agent.curator import Curator, SkillWriter


class ActionType(Enum):
    """Action type enum"""
    TOOL_CALL = "tool_call"
    DIRECT_RESPONSE = "direct_response"
    CLARIFICATION = "clarification"

logger = logging.getLogger(__name__)


@dataclass
class AgentResponse:
    """Agent 响应"""
    content: str
    tool_used: Optional[str] = None
    tool_result: Optional[Any] = None
    confidence_score: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0


class Agent:
    """
    Agent - 使用整合后的工具系统
    
    特点：
    1. 使用 LLM 直接做工具选择决策
    2. 整合了 ToolRegistry 中的所有工具
    3. 支持会话管理（自动检测今日会话）
    4. 支持记忆系统
    """
    
    def __init__(
        self,
        llm_provider=None,
        enable_session: bool = True,
        session_id: Optional[str] = None,
        force_new_session: bool = False,
        enable_curator: bool = True,
        debug_logs: bool = False
    ):
        """
        Args:
            llm_provider: LLM Provider
            enable_session: Enable session management
            session_id: Session ID (if resuming session). Use "last" for latest session
            force_new_session: Force create a new session even if today's session exists
            enable_curator: Enable Curator for self-improvement
            debug_logs: Enable DEBUG level logging for Trajectory and Curator
        """
        if debug_logs:
            set_log_level("detailed")
            logging.getLogger("TrajectoryRecorder").setLevel(logging.DEBUG)
            logging.getLogger("Curator").setLevel(logging.DEBUG)
        
        httpx_logger = logging.getLogger("httpx")
        httpx_logger.setLevel(logging.WARNING)
        
        self.llm_provider = llm_provider
        self.enable_session = enable_session
        self.enable_curator = enable_curator
        
        self._decision_logger = get_decision_logger("Agent", sublayer="task")
        self._llm_logger = get_llm_logger("Agent")

        self.engine = get_integrated_engine(llm_provider=llm_provider)

        # 初始化任务规划中间件
        self._task_planning_middleware = None

        # 初始化统一的 ContextBuilder（所有模式共用）
        from agent.context import ContextBuilder
        tools_dict = {t.name: t for t in self.engine.tool_selector.tools.values()}
        self._context_builder = ContextBuilder(tools=tools_dict)

        # 初始化 ContextCompressor（所有模式共用压缩功能）
        from agent.context.context_compressor import ContextCompressor
        model_name = getattr(self.llm_provider, 'model', 'gpt-4o')
        self._context_compressor = ContextCompressor(
            model=model_name,
            threshold_percent=0.75,
            protect_first_n=3,
            protect_last_n=10,
            summary_target_ratio=0.20,
            quiet_mode=True,
            llm_client=self.llm_provider,
        )

        # 初始化统一的 ContextManager（所有 LLM 调用共用）
        from agent.context import ContextManager
        self._context_manager = ContextManager(
            context_compressor=self._context_compressor,
            context_builder=self._context_builder
        )
        
        # 初始化统一的 LLMClient（所有 LLM 调用共用）
        from agent.llm import LLMClient, LLMAuxConfig
        self._llm_client = LLMClient(
            llm_provider=llm_provider,
            context_manager=self._context_manager,
            aux_config=LLMAuxConfig()
        )
        
        # 统一上下文管理：通过 engine._context_manager property 自动同步给 tool_selector
        self.engine._context_manager = self._context_manager
        self.engine._llm_client = self._llm_client

        self._session: Optional[Session] = None
        if self.enable_session:
            if session_id == "last" or session_id is None and not force_new_session:
                self._session = session_manager.get_or_create_today_session()
                if session_manager.get_latest_today_session():
                    self._decision_logger.info(f"Continuing today's session: {self._session.session_id}")
                else:
                    self._decision_logger.info(f"Created new session: {self._session.session_id}")
            else:
                self._session = session_manager.create_session(session_id)
                self._decision_logger.info(f"Resumed session: {session_id}")
        
        # 流式输出相关
        self._stream_callback = None
        self._stream_emitter = None
        
        # 中断机制
        self._interrupt_requested = False
        
        self._init_trajectory_and_curator()
    
    def interrupt(self):
        """请求中断当前处理
        
        可以在另一个线程中调用此方法来中断正在进行的操作。
        """
        self._decision_logger.warning("中断请求已触发")
        self._interrupt_requested = True
        
        # 通知流式发射器
        if self._stream_emitter:
            from common.streaming import ErrorEvent
            self._stream_emitter.emit_error("用户请求中断", "InterruptedError")
            self._stream_emitter.interrupt()  # 触发 StreamEmitter 的中断
    
    def is_interrupted(self) -> bool:
        """检查是否请求了中断"""
        return self._interrupt_requested
    
    def clear_interrupt(self):
        """清除中断标志"""
        self._interrupt_requested = False
        if self._stream_emitter:
            self._stream_emitter.clear_interrupt()
    
    def set_stream_callback(self, callback):
        """设置流式输出回调
        
        Args:
            callback: 回调函数，签名为 on_delta(text: str)
        """
        self._stream_callback = callback
    
    def set_thinking_callback(self, callback):
        """设置思考内容回调
        
        Args:
            callback: 回调函数，签名为 on_thinking(text: str)
        """
        self._thinking_callback = callback
    
    def set_stream_emitter(self, emitter):
        """设置流式发射器
        
        Args:
            emitter: StreamEmitter 实例
        """
        self._stream_emitter = emitter
    
    def _emit_stream(self, text: str):
        """发射流式文本到所有消费者"""
        if text:
            if self._stream_callback:
                self._stream_callback(text)
            if self._stream_emitter:
                self._stream_emitter.emit_delta(text)
    
    def _emit_stream_complete(self, text: str = ""):
        """发射流式完成信号"""
        if self._stream_emitter:
            self._stream_emitter.emit_complete(text)
    
    def _init_trajectory_and_curator(self):
        """初始化 TrajectoryRecorder 和 Curator"""
        self._trajectory_recorder = TrajectoryRecorder()
        
        session_id = self._session.session_id if self._session else "default"
        self._trajectory_recorder.initialize(session_id)
        
        self._curator = None
        if self.enable_curator:
            try:
                self._curator = Curator(
                    trajectory_recorder=self._trajectory_recorder,
                    skill_writer=SkillWriter(),
                    enable_auto_learn=True
                )
                self._decision_logger.info("Curator enabled for self-improvement")
            except Exception as e:
                self._decision_logger.warning(f"Failed to initialize Curator: {e}")
    
    async def _process_trajectory_async(self, response: AgentResponse):
        """异步处理轨迹（让 Curator 分析）"""
        trajectory_metadata = {
            'trajectory_id': f"traj_{self._session.session_id if self._session else 'unknown'}",
            'session_id': self._session.session_id if self._session else 'unknown',
            'confidence_score': response.confidence_score,
            'execution_time': response.execution_time,
            'success': response.confidence_score > 0.5,
            'tool_used': response.tool_used,
        }
        
        if self._curator and self.enable_curator:
            try:
                trajectory = self._trajectory_recorder.get_trajectory()
                if trajectory:
                    result = await self._curator.process_trajectory({
                        **trajectory_metadata,
                        'trajectory': trajectory,
                    })
                    trajectory_metadata['curator_result'] = {
                        'skill_synthesized': result is not None,
                        'skill_name': result.name if result else None,
                    }
                    self._decision_logger.info("Trajectory processed by Curator")
            except Exception as e:
                self._decision_logger.warning(f"Failed to process trajectory with Curator: {e}")
                trajectory_metadata['curator_error'] = str(e)
        
        self._trajectory_recorder.save_trajectory(metadata=trajectory_metadata)
        self._decision_logger.debug(f"Trajectory saved to {self._trajectory_recorder._save_path}")
    
    async def _should_use_react(
        self,
        user_input: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> bool:
        """
        判断是否使用 ReAct 模式

        使用消息列表模式进行上下文构建。
        """
        if not self.llm_provider:
            return False

        # 使用消息列表模式构建上下文
        from agent.context import ContextPurpose
        
        # MODE_DECISION 使用自己的压缩逻辑，所以这里传入 include_tools=False
        messages_result = await self._context_manager.build_messages(
            user_message=user_input,
            conversation_history=conversation_history,
            purpose=ContextPurpose.MODE_DECISION,
            include_tools=False
        )

        # 构建消息列表（系统消息 + 用户消息）
        messages = messages_result.messages.copy()
        
        # 添加任务特定的指导
        messages.append({
            "role": "user",
            "content": f"""## Current Task
{user_input}

Is this a complex task that needs ReAct mode? (multi-step planning, multiple tools, tool execution)

Answer ONLY with this exact JSON format (no other text):
{{"use_react": true/false, "reasoning": "brief reason"}}"""
        })

        try:
            import json
            import re
            # 使用空 prompt，因为消息列表已包含用户消息
            response = await self.llm_provider.generate(prompt="", messages=messages)
            content = response.content if hasattr(response, 'content') else str(content)

            # 尝试从内容中提取 JSON
            result = None
            try:
                # 方法1：尝试直接解析整个内容
                result = json.loads(content)
            except:
                # 方法2：找最后一个 { 到最后一个 } 之间的内容
                last_brace = content.rfind('}')
                if last_brace != -1:
                    first_brace = -1
                    brace_count = 0
                    for i in range(last_brace, -1, -1):
                        if content[i] == '}':
                            brace_count += 1
                        elif content[i] == '{':
                            brace_count -= 1
                            if brace_count == 0:
                                first_brace = i
                                break
                    if first_brace != -1:
                        try:
                            result = json.loads(content[first_brace:last_brace+1])
                        except:
                            pass

            # 如果没有找到有效的 JSON，使用 ReAct
            if result is None:
                self._decision_logger.info(f"ReAct 模式判断: 未找到有效 JSON，默认使用 ReAct")
                return True

            # 兼容 use_react 和 action 两种格式
            if "use_react" in result:
                use_react = result.get("use_react", False)
            elif "action" in result:
                # action 格式: "react"=需要 ReAct, "direct_response"/其他=直接回复
                use_react = result.get("action") == "react"
            else:
                self._decision_logger.info(f"ReAct 模式判断: JSON 中没有 use_react 或 action 字段，默认使用 ReAct")
                return True

            reasoning = result.get("reasoning", "")
            self._decision_logger.info(f"ReAct 模式判断: {use_react} - {reasoning}")
            return use_react
        except Exception as e:
            self._decision_logger.warning(f"ReAct 判断失败: {e}，默认使用 ReAct 模式（更好的错误恢复）")
            return True  # 默认使用 ReAct 模式（有更好的重试机制）
    
    async def _chat_react(
        self,
        user_input: str,
        conversation_history: Optional[List[Dict]] = None,
        subtasks: Optional[List[Dict]] = None
    ) -> AgentResponse:
        """
        使用 ReAct 模式处理用户输入
        
        ReAct 模式特点：
        1. LLM 每次决策都可能调用工具
        2. 支持复杂任务的多步骤执行
        3. 集成 Rail 机制（事件追踪、权限控制等）
        
        Args:
            user_input: 用户输入
            conversation_history: 可选的对话历史
            
        Returns:
            AgentResponse
        """
        from agent.react import ReActLoop, ReActContext
        from agent.rails import get_rail_manager, TaskEventRail
        
        session_id = self._session.session_id if self._session else "default"
        
        rails = []
        try:
            rail_manager = get_rail_manager(session_id)
            rail_manager.register_rail(TaskEventRail(session_id))
            rails = [TaskEventRail(session_id)]
        except Exception as e:
            self._decision_logger.warning(f"Rail 初始化失败: {e}")
        
        # 复用已初始化的 ContextBuilder 中的工具字典
        loop = ReActLoop(
            llm_provider=self.llm_provider,
            session_id=session_id,
            rails=rails,
            tools=self._context_builder.tools,
            stream_emitter=self._stream_emitter,
            context_manager=self._context_manager
        )

        # 压缩逻辑已统一到 ContextManager，此处不再重复压缩
        # ContextManager.build_messages() 会自动处理压缩
        compressed_history = conversation_history

        tools = self.engine.tool_selector.get_tools_schema()
        tool_handlers = {
            t.name: t.handler for t in self.engine.tool_selector.tools.values()
        }

        context = ReActContext(
            task_description=user_input,
            tools=tools,
            tool_handlers=tool_handlers,
            conversation_history=compressed_history
        )
        
        # 将子任务存入 context（用于进度跟踪）
        if subtasks:
            context.set('subtasks', subtasks)
        
        result = await loop.run(context)
        
        final_result = result.get("final_result", "")
        iterations = result.get("iterations", 0)
        
        if isinstance(final_result, dict):
            final_result = json.dumps(final_result, ensure_ascii=False)
        
        self._decision_logger.info(
            f"[/✅Task] ReAct 完成，迭代 {iterations} 次"
        )
        
        return AgentResponse(
            content=str(final_result),
            confidence_score=0.9,
            metadata={"react_iterations": iterations}
        )
    
    async def chat(
        self,
        user_input: str,
        conversation_history: Optional[List[Dict]] = None,
        use_react: Optional[bool] = None,
        enable_stream: bool = False,
        stream_callback = None
    ) -> AgentResponse:
        """
        处理用户输入（主要接口
        
        自动判断使用哪种模式：
        - 复杂任务 → ReAct 模式（多步骤循环执行）
        - 简单任务 → 直接模式（单次交互）
        
        Args:
            user_input: 用户输入
            conversation_history: 可选的对话历史
            use_react: 强制指定模式，None 则自动判断
            enable_stream: 是否启用流式输出
            stream_callback: 流式输出回调函数，签名为 on_delta(text: str)
            
        Returns:
            AgentResponse
        """
        self._decision_logger.info(f"User input: {user_input[:50]}...")

        # 设置流式回调
        if stream_callback:
            self.set_stream_callback(stream_callback)
        
        # 如果启用流式，设置默认的控制台输出
        if enable_stream and not stream_callback:
            self._setup_default_stream()

        if use_react is None:
            use_react = await self._should_use_react(user_input, conversation_history)
        
        # 如果使用 ReAct 模式，先进行任务规划检测
        if use_react:
            planning_result = await self._check_and_emit_task_planning(user_input, use_react=True)
            subtasks = planning_result.subtasks if planning_result else None
            return await self._chat_react(user_input, conversation_history, subtasks=subtasks)
        
        return await self._chat_simple(user_input, conversation_history)

    async def _check_and_emit_task_planning(self, user_input: str, use_react: bool = False):
        """检查是否需要任务规划，并发射规划事件"""
        try:
            # 懒加载初始化任务规划中间件
            if self._task_planning_middleware is None:
                from agent.task.task_middleware import TaskPlanningMiddleware
                session_id = self._session.session_id if self._session else "default"
                self._task_planning_middleware = TaskPlanningMiddleware(
                    llm_provider=self.llm_provider,
                    session_id=session_id,
                    enable_logging=True,
                    enable_collaboration=False
                )
            
            # 设置流式发射器
            if self._stream_emitter:
                self._task_planning_middleware.set_stream_emitter(self._stream_emitter)
            
            # 进行复杂度分析和任务规划（TaskPlanning 已输出子任务列表）
            # 如果 ReAct=true，强制进行任务拆解，不再做复杂度判断
            if use_react:
                planning_result = await self._task_planning_middleware.process(
                    user_input, force_planning=True
                )
            else:
                planning_result = await self._task_planning_middleware.process(user_input)
            
            # 记录子任务数量（TaskPlanning 已输出详细列表）
            subtask_count = len(planning_result.subtasks) if planning_result.subtasks else 0
            if subtask_count > 0:
                self._decision_logger.info(f"任务规划完成，共 {subtask_count} 个子任务")
        except Exception as e:
            # 静默处理，避免影响主流程
            self._decision_logger.warning(f"任务规划检查失败: {e}")
    
    def _setup_default_stream(self):
        """设置默认的流式输出（控制台）"""
        from common.streaming import ConsoleConsumer, StreamEmitter, ConsumerRegistry
        
        registry = ConsumerRegistry()
        registry.register(ConsoleConsumer())
        
        self._stream_emitter = StreamEmitter(registry)
        self._stream_emitter.start()
    
    def _cleanup_stream(self):
        """清理流式输出"""
        if self._stream_emitter:
            self._stream_emitter.stop()
            self._stream_emitter = None
    
    async def _chat_simple(
        self,
        user_input: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> AgentResponse:
        """
        简单模式：单次交互
        
        Args:
            user_input: 用户输入
            conversation_history: 可选的对话历史
            
        Returns:
            AgentResponse
        """
        import time
        start_time = time.time()
        
        self._trajectory_recorder.add_human_message(user_input)
        
        history = conversation_history
        if not history and self._session:
            history = self._get_session_messages()
        
        if self._session:
            self._session.add_message('user', user_input)
        
        result = await self.engine.process(
            user_input,
            conversation_history=history
        )
        
        self._decision_logger.info(f"Engine result type: {result['type']}")
        
        final_response = ""
        
        if result['type'] == 'tool_execution':
            tool_name = result['tool']
            tool_result = result['result']
            
            self._decision_logger.info(f"Executed tool: {tool_name}")
            
            self._trajectory_recorder.add_tool_call(
                tool_name=tool_name,
                arguments=result.get('parameters', {}),
                reasoning=result.get('reasoning', '')
            )
            self._trajectory_recorder.add_tool_response(
                tool_name=tool_name,
                content=tool_result
            )
            
            if self.llm_provider:
                final_response = await self._summarize_with_llm(
                    user_input,
                    tool_name,
                    tool_result,
                    conversation_history=history
                )
            else:
                final_response = f"Executed {tool_name}: {json.dumps(tool_result, ensure_ascii=False)}"
            
            response_obj = AgentResponse(
                content=final_response,
                tool_used=tool_name,
                tool_result=tool_result,
                confidence_score=getattr(result.get('selection'), 'confidence', 0.8)
            )
        
        elif result['type'] == 'direct_response':
            # 检查是否启用流式输出
            has_stream = self._stream_callback is not None or self._stream_emitter is not None
            if has_stream and self.llm_provider:
                try:
                    final_response = await self._generate_direct_response_stream(user_input, conversation_history=history)
                    if isinstance(final_response, str) and hasattr(response, 'content'):
                        pass  # 流式已经返回字符串
                except Exception as e:
                    self._decision_logger.warning(f"Stream failed, fallback to non-stream: {e}")
                    response = await self._generate_direct_response(user_input, conversation_history=history)
                    final_response = response.content if hasattr(response, 'content') else str(response)
            elif self.llm_provider:
                response = await self._generate_direct_response(user_input, conversation_history=history)
                final_response = response.content if hasattr(response, 'content') else str(response)
            else:
                final_response = "This is a direct response (no LLM configured)."
            
            response_obj = AgentResponse(
                content=final_response,
                confidence_score=1.0
            )
        
        elif result['type'] == 'clarification_needed':
            selection = result.get('selection')
            clarification = getattr(selection, 'reasoning', 'Could you provide more details?')
            
            if self.llm_provider:
                response = await self._generate_clarification_response(
                    user_input,
                    clarification,
                    conversation_history=history
                )
                final_response = response.content if hasattr(response, 'content') else str(response)
            else:
                final_response = clarification
            
            response_obj = AgentResponse(
                content=final_response,
                confidence_score=0.5
            )
        
        else:
            final_response = "I'm not sure how to respond to that."
            response_obj = AgentResponse(
                content=final_response,
                confidence_score=0.3
            )
        
        if self._session:
            self._session.add_message('assistant', final_response)
        
        self._trajectory_recorder.add_gpt_message(final_response)
        
        response_obj.execution_time = time.time() - start_time
        
        self._decision_logger.debug(f"Response generated in {response_obj.execution_time:.2f}s")
        
        await self._process_trajectory_async(response_obj)
        
        return response_obj
    
    async def _summarize_with_llm(
        self,
        user_input: str,
        tool_name: str,
        tool_result: Any,
        conversation_history: Optional[List[Dict]] = None
    ) -> str:
        """使用 LLM 总结工具执行结果（使用消息列表模式）"""
        try:
            from agent.context import ContextPurpose
            
            result_str = json.dumps(tool_result, ensure_ascii=False)
            
            # 使用消息列表模式构建上下文
            messages_result = await self._context_manager.build_messages(
                user_message=f"{user_input}\n\nI executed tool: {tool_name}\nTool result: {result_str}\n\nPlease provide a natural language response to the user based on the tool result.",
                conversation_history=conversation_history,
                purpose=ContextPurpose.TOOL_RESULT_SUMMARY,
                include_tools=False,
                model=getattr(self.llm_provider, 'model', None)
            )
            
            self._decision_logger.info(
                f"Context Manager: tool_result_summary - "
                f"messages={len(messages_result.messages)}, "
                f"compressed={messages_result.compressed}"
            )
            
            # 使用空 prompt，因为消息列表已包含用户消息
            response = await self.llm_provider.generate(
                prompt="",
                messages=messages_result.messages
            )
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            logger.error(f"Failed to summarize with LLM: {e}")
            return f"Tool {tool_name} executed. Result: {json.dumps(tool_result, ensure_ascii=False)}"
    
    async def _generate_direct_response(
        self,
        user_input: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> str:
        """使用对话历史生成直接回复（使用消息列表模式）"""
        try:
            from agent.context import ContextPurpose
            
            # 使用消息列表模式构建上下文
            messages_result = await self._context_manager.build_messages(
                user_message=user_input,
                conversation_history=conversation_history,
                purpose=ContextPurpose.DIRECT_RESPONSE,
                include_tools=False,
                model=getattr(self.llm_provider, 'model', None)
            )

            self._decision_logger.info(
                f"Context Manager: direct_response - "
                f"messages={len(messages_result.messages)}, "
                f"compressed={messages_result.compressed}, "
                f"history msgs={messages_result.compressed_count}"
            )

            # 使用空 prompt，因为消息列表已包含用户消息
            response = await self.llm_provider.generate(
                prompt="",
                messages=messages_result.messages
            )
            return response
        except Exception as e:
            logger.error(f"Failed to generate with history: {e}")
            # 降级：直接使用用户输入（消息列表模式）
            response = await self.llm_provider.generate(
                prompt="",
                messages=[{"role": "user", "content": user_input}]
            )
            return response
    
    async def _generate_direct_response_stream(
        self,
        user_input: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> str:
        """使用对话历史生成直接回复（流式版本，使用消息列表模式）"""
        try:
            from agent.context import ContextPurpose
            from common.streaming import StreamingThinkScrubber
            
            scrubber = StreamingThinkScrubber()
            
            # 使用消息列表模式构建上下文
            messages_result = await self._context_manager.build_messages(
                user_message=user_input,
                conversation_history=conversation_history,
                purpose=ContextPurpose.DIRECT_RESPONSE,
                include_tools=False,
                model=getattr(self.llm_provider, 'model', None)
            )

            self._decision_logger.info(
                f"Context Manager: direct_response (stream) - "
                f"messages={len(messages_result.messages)}, "
                f"compressed={messages_result.compressed}, "
                f"history msgs={messages_result.compressed_count}"
            )

            # 使用流式调用（传递消息列表，使用空 prompt）
            accumulated = ""
            thinking_accumulated = ""
            async for chunk in self.llm_provider.generate_stream(
                prompt="",
                messages=messages_result.messages
            ):
                delta = chunk.delta if hasattr(chunk, 'delta') else (chunk.content if hasattr(chunk, 'content') else str(chunk))
                if delta:
                    visible, thinking = scrubber.feed(delta)
                    
                    if visible:
                        self._emit_stream(visible)
                        accumulated += visible
                    
                    if thinking:
                        thinking_accumulated += thinking
                        if hasattr(self, '_thinking_callback') and self._thinking_callback:
                            self._thinking_callback(thinking)
            
            remaining_visible, remaining_thinking = scrubber.flush()
            if remaining_visible:
                self._emit_stream(remaining_visible)
                accumulated += remaining_visible
            if remaining_thinking:
                thinking_accumulated += remaining_thinking
                if hasattr(self, '_thinking_callback') and self._thinking_callback:
                    self._thinking_callback(remaining_thinking)
            
            self._emit_stream_complete(accumulated)
            return accumulated
        except Exception as e:
            logger.error(f"Failed to generate stream: {e}")
            # 降级到非流式
            return await self._generate_direct_response(user_input, conversation_history)

    async def _generate_clarification_response(
        self,
        user_input: str,
        clarification: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> str:
        """使用对话历史生成澄清回复（使用消息列表模式）"""
        try:
            from agent.context import ContextPurpose
            
            # 使用消息列表模式构建上下文
            messages_result = await self._context_manager.build_messages(
                user_message=f"User asked: {user_input}\n\nYou need to ask for clarification. Reason: {clarification}\n\nPlease ask for more details in a natural way.",
                conversation_history=conversation_history,
                purpose=ContextPurpose.CLARIFICATION,
                include_tools=False,
                model=getattr(self.llm_provider, 'model', None)
            )
            
            self._decision_logger.info(
                f"Context Manager: clarification - "
                f"messages={len(messages_result.messages)}"
            )
            
            # 使用空 prompt，因为消息列表已包含用户消息
            response = await self.llm_provider.generate(
                prompt="",
                messages=messages_result.messages
            )
            return response
        except Exception as e:
            logger.error(f"Failed to generate clarification: {e}")
            return f"You need to clarify: {clarification}"
    
    def _get_session_messages(self) -> List[Dict]:
        """从会话中获取消息列表"""
        if not self._session:
            return []
        
        return [
            {"role": msg.role, "content": msg.content}
            for msg in self._session.messages
        ]
    
    def get_tool_list(self) -> List[Dict[str, Any]]:
        """获取可用工具列表"""
        return [
            {
                'name': tool.name,
                'description': tool.description,
                'category': tool.category
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
