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
        
        self._decision_logger = get_decision_logger("Agent")
        self._llm_logger = get_llm_logger("Agent")

        self.engine = get_integrated_engine(llm_provider=llm_provider)

        # 初始化统一的 ContextBuilder（所有模式共用）
        from agent.context import ContextBuilder
        tools_dict = {t.name: t for t in self.engine.tool_selector.tools.values()}
        self._context_builder = ContextBuilder(tools=tools_dict)

        # 初始化 ContextCompressor（所有模式共用压缩功能）
        from agent.context_compressor import SummaryCompressor
        self._context_compressor = SummaryCompressor(recent_messages=10)

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
        
        self._init_trajectory_and_curator()
    
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
    
    async def _should_use_react(self, user_input: str) -> bool:
        """
        判断是否使用 ReAct 模式
        """
        if not self.llm_provider:
            return False
        
        prompt = f"""用户输入：{user_input}

判断这个任务是否需要使用 ReAct 循环模式（多步骤任务规划）？

ReAct 模式特点：
- 复杂任务（需要多个步骤）
- 任务规划（需要拆解子任务）
- 项目开发（需要创建文件、目录）
- 多工具协作（需要调用多个工具）

简单任务（不需要 ReAct）：
- 简单问答
- 单一操作
- 信息查询

返回 JSON：
{{"use_react": true/false, "reasoning": "判断理由"}}

Respond with ONLY the JSON object."""

        try:
            import json
            response = await self.llm_provider.generate(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            result = json.loads(content)
            use_react = result.get("use_react", False)
            reasoning = result.get("reasoning", "")
            self._decision_logger.info(f"ReAct 模式判断: {use_react} - {reasoning}")
            return use_react
        except Exception as e:
            self._decision_logger.warning(f"ReAct 判断失败: {e}")
            return False
    
    async def _chat_react(
        self,
        user_input: str,
        conversation_history: Optional[List[Dict]] = None
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
        
        self._decision_logger.info(f"[/✅Task] 使用 ReAct 模式")
        
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
            tools=self._context_builder.tools
        )

        # 如果有历史消息，先检查是否需要压缩
        compressed_history = conversation_history
        if conversation_history and len(conversation_history) > 10:
            result = await self._context_compressor.compress(
                conversation_history,
                max_messages=10
            )
            compressed_history = result.compressed_messages
            self._decision_logger.info(
                f"Context Compression: {result.original_count} -> {result.compressed_count} messages"
            )

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
        use_react: Optional[bool] = None
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
            
        Returns:
            AgentResponse
        """
        self._decision_logger.info(f"User input: {user_input[:50]}...")
        
        if use_react is None:
            use_react = await self._should_use_react(user_input)
        
        if use_react:
            return await self._chat_react(user_input, conversation_history)
        
        return await self._chat_simple(user_input, conversation_history)
    
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
            if self.llm_provider:
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
        """使用 LLM 总结工具执行结果"""
        try:
            result_str = json.dumps(tool_result, ensure_ascii=False)
            
            messages = []
            if conversation_history:
                messages.extend(conversation_history)
            messages.append({"role": "user", "content": user_input})
            
            prompt = f"""I executed tool: {tool_name}
Tool result: {result_str}

Please provide a natural language response to the user based on the tool result."""
            
            messages.append({"role": "user", "content": prompt})
            
            response = await self.llm_provider.generate(prompt, messages=messages)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            logger.error(f"Failed to summarize with LLM: {e}")
            try:
                prompt = f"""User asked: {user_input}

I executed tool: {tool_name}
Tool result: {result_str}

Please provide a natural language response to the user based on the tool result."""
                response = await self.llm_provider.generate(prompt)
                return response.content if hasattr(response, 'content') else str(response)
            except:
                return f"Tool {tool_name} executed. Result: {json.dumps(tool_result, ensure_ascii=False)}"
    
    async def _generate_direct_response(
        self,
        user_input: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> str:
        """使用对话历史生成直接回复（使用统一的 ContextBuilder + 压缩）"""
        try:
            # 如果有历史消息，先检查是否需要压缩
            compressed_history = conversation_history
            if conversation_history and len(conversation_history) > 10:
                result = await self._context_compressor.compress(
                    conversation_history,
                    max_messages=10
                )
                compressed_history = result.compressed_messages
                self._decision_logger.info(
                    f"Context Compression: {result.original_count} -> {result.compressed_count} messages"
                )

            # 使用统一的 ContextBuilder 构建系统提示词
            system_prompt = self._context_builder.build_system_prompt(
                conversation_history=compressed_history,
                include_tools=False
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ]

            self._decision_logger.info(
                f"Context Assembly: direct_response - "
                f"prompt chars={len(system_prompt)}, "
                f"history msgs={len(compressed_history) if compressed_history else 0}"
            )

            response = await self.llm_provider.generate(
                user_input,
                system_prompt=system_prompt
            )
            return response
        except Exception as e:
            logger.error(f"Failed to generate with history: {e}")
            response = await self.llm_provider.generate(user_input)
            return response

    async def _generate_clarification_response(
        self,
        user_input: str,
        clarification: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> str:
        """使用对话历史生成澄清回复"""
        try:
            messages = []
            if conversation_history:
                messages.extend(conversation_history)
            messages.append({"role": "user", "content": user_input})
            
            prompt = f"""User asked: {user_input}

You need to ask for clarification. Reason: {clarification}

Please ask for more details in a natural way."""
            
            messages.append({"role": "user", "content": prompt})
            
            response = await self.llm_provider.generate(prompt, messages=messages)
            return response
        except Exception as e:
            logger.error(f"Failed to generate clarification: {e}")
            response = await self.llm_provider.generate(
                f"User asked: {user_input}. You need to ask for clarification. Reason: {clarification}"
            )
            return response
    
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
