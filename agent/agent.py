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
    get_access_logger,
    get_decision_logger,
    get_execution_logger,
    get_llm_logger,
    get_tool_logger
)


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
        force_new_session: bool = False
    ):
        """
        Args:
            llm_provider: LLM Provider
            enable_session: Enable session management
            session_id: Session ID (if resuming session). Use "last" for latest session
            force_new_session: Force create a new session even if today's session exists
        """
        httpx_logger = logging.getLogger("httpx")
        httpx_logger.setLevel(logging.WARNING)
        
        self.llm_provider = llm_provider
        self.enable_session = enable_session
        
        self._access_logger = get_access_logger("Agent")
        self._decision_logger = get_decision_logger("Agent")
        self._execution_logger = get_execution_logger("Agent")
        self._tool_logger = get_tool_logger("Agent")
        
        self.engine = get_integrated_engine(llm_provider=llm_provider)
        
        self._session: Optional[Session] = None
        if self.enable_session:
            if session_id == "last" or session_id is None and not force_new_session:
                self._session = session_manager.get_or_create_today_session()
                if session_manager.get_latest_today_session():
                    self._access_logger.info(f"Continuing today's session: {self._session.session_id}")
                else:
                    self._access_logger.info(f"Created new session: {self._session.session_id}")
            else:
                self._session = session_manager.create_session(session_id)
                self._access_logger.info(f"Resumed session: {session_id}")
    
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
            self._decision_logger.debug(f"ReAct 模式判断: {use_react} - {reasoning}")
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
        
        self._access_logger.info(f"[/✅Task] 使用 ReAct 模式")
        
        session_id = self._session.session_id if self._session else "default"
        
        rails = []
        try:
            rail_manager = get_rail_manager(session_id)
            rail_manager.register_rail(TaskEventRail(session_id))
            rails = [TaskEventRail(session_id)]
        except Exception as e:
            self._decision_logger.warning(f"Rail 初始化失败: {e}")
        
        loop = ReActLoop(
            llm_provider=self.llm_provider,
            session_id=session_id,
            rails=rails
        )
        
        tools = self.engine.tool_selector.get_tools_schema()
        tool_handlers = {
            t.name: t.handler for t in self.engine.tool_selector.tools.values()
        }
        
        context = ReActContext(
            task_description=user_input,
            tools=tools,
            tool_handlers=tool_handlers,
            conversation_history=conversation_history
        )
        
        result = await loop.run(context)
        
        final_result = result.get("final_result", "")
        iterations = result.get("iterations", 0)
        
        if isinstance(final_result, dict):
            final_result = json.dumps(final_result, ensure_ascii=False)
        
        self._access_logger.info(
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
        
        self._access_logger.info(f"User input: {user_input[:50]}...")
        
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
            
            self._tool_logger.info(f"Executed tool: {tool_name}")
            
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
        
        response_obj.execution_time = time.time() - start_time
        
        self._access_logger.info(f"Response generated in {response_obj.execution_time:.2f}s")
        
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
        """使用对话历史生成直接回复"""
        try:
            messages = []
            system_prompt = self._build_identity_prompt()
            messages.append({"role": "system", "content": system_prompt})
            
            if conversation_history:
                messages.extend(conversation_history)
            
            messages.append({"role": "user", "content": user_input})
            
            response = await self.llm_provider.generate(user_input, messages=messages)
            return response
        except Exception as e:
            logger.error(f"Failed to generate with history: {e}")
            response = await self.llm_provider.generate(user_input)
            return response
    
    def _build_identity_prompt(self) -> str:
        """构建 Agent 身份提示词"""
        from agent.llm_tool_selector import AgentDefinitionLoader
        
        loader = AgentDefinitionLoader()
        identity = loader.get_identity_summary()
        capabilities = loader.get_capabilities_summary()
        
        return f"""{identity}

{capabilities}

Please respond naturally based on your identity and capabilities. When asked "who are you" or "你是谁", introduce yourself as Handsome Agent."""
    
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
