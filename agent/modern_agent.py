#!/usr/bin/env python3
"""
Modern Agent Core - 现代版 Agent 核心

使用整合后的工具系统，完全基于 LLM 驱动的决策

这是推荐使用的新 Agent 实现
"""

import sys
import os
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

# 添加项目根目录
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from agent.simplified_agent import ActionType
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

logger = logging.getLogger(__name__)


@dataclass
class ModernAgentResponse:
    """现代版 Agent 响应"""
    content: str
    tool_used: Optional[str] = None
    tool_result: Optional[Any] = None
    confidence_score: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0


class ModernAgent:
    """
    现代版 Agent - 使用整合后的工具系统
    
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
        # Configure httpx logger to avoid polluting output
        httpx_logger = logging.getLogger("httpx")
        httpx_logger.setLevel(logging.WARNING)
        
        self.llm_provider = llm_provider
        self.enable_session = enable_session
        
        # Initialize loggers FIRST (before using them)
        self._access_logger = get_access_logger("ModernAgent")
        self._decision_logger = get_decision_logger("ModernAgent")
        self._execution_logger = get_execution_logger("ModernAgent")
        self._tool_logger = get_tool_logger("ModernAgent")
        
        # Initialize tool engine
        self.engine = get_integrated_engine(llm_provider=llm_provider)
        
        # Initialize session
        self._session: Optional[Session] = None
        if self.enable_session:
            if session_id == "last" or session_id is None and not force_new_session:
                # Auto-detect: get today's session or create new
                self._session = session_manager.get_or_create_today_session()
                if session_manager.get_latest_today_session():
                    self._access_logger.info(f"Continuing today's session: {self._session.session_id}")
                else:
                    self._access_logger.info(f"Created new session: {self._session.session_id}")
            else:
                # Create/resume specific session
                self._session = session_manager.create_session(session_id)
                self._access_logger.info(f"Resumed session: {session_id}")
    
    async def chat(
        self,
        user_input: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> ModernAgentResponse:
        """
        处理用户输入（主要接口）
        
        Args:
            user_input: 用户输入
            conversation_history: 可选的对话历史（如果不提供，会使用内部会话记录）
        
        Returns:
            ModernAgentResponse
        """
        import time
        start_time = time.time()
        
        # 记录输入
        self._access_logger.info(f"User input: {user_input[:50]}...")
        
        # 准备对话历史（在添加新消息之前获取，避免重复）
        history = conversation_history
        if not history and self._session:
            history = self._get_session_messages()
        
        # 记录到会话（在获取历史之后添加，避免包含当前消息）
        if self._session:
            self._session.add_message('user', user_input)
        
        # 使用决策引擎处理
        result = await self.engine.process(
            user_input,
            conversation_history=history
        )
        
        self._decision_logger.info(f"Engine result type: {result['type']}")
        
        final_response = ""
        
        if result['type'] == 'tool_execution':
            # 工具被使用了
            tool_name = result['tool']
            tool_result = result['result']
            
            self._tool_logger.info(f"Executed tool: {tool_name}")
            
            # 让 LLM 总结工具结果，带对话历史
            if self.llm_provider:
                final_response = await self._summarize_with_llm(
                    user_input,
                    tool_name,
                    tool_result,
                    conversation_history=history
                )
            else:
                # 没有 LLM，直接返回工具结果
                final_response = f"Executed {tool_name}: {json.dumps(tool_result, ensure_ascii=False)}"
            
            response_obj = ModernAgentResponse(
                content=final_response,
                tool_used=tool_name,
                tool_result=tool_result,
                confidence_score=getattr(result.get('selection'), 'confidence', 0.8)
            )
        
        elif result['type'] == 'direct_response':
            # 直接使用 LLM 响应，带对话历史
            if self.llm_provider:
                response = await self._generate_direct_response(user_input, conversation_history=history)
                final_response = response.content if hasattr(response, 'content') else str(response)
            else:
                final_response = "This is a direct response (no LLM configured)."
            
            response_obj = ModernAgentResponse(
                content=final_response,
                confidence_score=1.0
            )
        
        elif result['type'] == 'clarification_needed':
            # 需要澄清
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
            
            response_obj = ModernAgentResponse(
                content=final_response,
                confidence_score=0.5
            )
        
        else:
            # 未知类型
            final_response = "I'm not sure how to respond to that."
            response_obj = ModernAgentResponse(
                content=final_response,
                confidence_score=0.3
            )
        
        # 记录响应
        if self._session:
            self._session.add_message('assistant', final_response)
        
        # 计算执行时间
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
        """
        使用 LLM 总结工具执行结果，带对话历史
        
        Args:
            user_input: 用户输入
            tool_name: 工具名称
            tool_result: 工具结果
            conversation_history: 对话历史
        
        Returns:
            总结后的响应
        """
        try:
            result_str = json.dumps(tool_result, ensure_ascii=False)
            
            # 构建完整的消息列表：历史消息 + 当前用户输入
            messages = []
            if conversation_history:
                messages.extend(conversation_history)
            
            # 添加当前用户输入
            messages.append({"role": "user", "content": user_input})
            
            prompt = f"""I executed tool: {tool_name}
Tool result: {result_str}

Please provide a natural language response to the user based on the tool result."""
            
            # 添加总结提示作为最后一条消息
            messages.append({"role": "user", "content": prompt})
            
            # LLM provider 返回 LLMResponse 对象
            response = await self.llm_provider.generate(prompt, messages=messages)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            logger.error(f"Failed to summarize with LLM: {e}")
            # 回退到简单方法
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
        """
        使用对话历史生成直接回复
        
        Args:
            user_input: 用户输入
            conversation_history: 对话历史
        
        Returns:
            LLM 生成的回复
        """
        try:
            # 构建完整的消息列表：系统提示 + 历史消息 + 当前用户输入
            messages = []
            
            # 添加系统提示（包含 Agent 身份定义）
            system_prompt = self._build_identity_prompt()
            messages.append({"role": "system", "content": system_prompt})
            
            # 添加对话历史
            if conversation_history:
                messages.extend(conversation_history)
            
            # 添加当前用户输入作为最后一条消息
            messages.append({"role": "user", "content": user_input})
            
            # LLM provider 直接返回字符串
            response = await self.llm_provider.generate(user_input, messages=messages)
            return response
        except Exception as e:
            logger.error(f"Failed to generate with history: {e}")
            # 回退到简单方法
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
        """
        使用对话历史生成澄清回复
        
        Args:
            user_input: 用户输入
            clarification: 澄清内容
            conversation_history: 对话历史
        
        Returns:
            LLM 生成的回复
        """
        try:
            # 构建完整的消息列表：历史消息 + 当前用户输入
            messages = []
            if conversation_history:
                messages.extend(conversation_history)
            
            # 添加当前用户输入
            messages.append({"role": "user", "content": user_input})
            
            prompt = f"""User asked: {user_input}

You need to ask for clarification. Reason: {clarification}

Please ask for more details in a natural way."""
            
            # 添加澄清提示作为最后一条消息
            messages.append({"role": "user", "content": prompt})
            
            # LLM provider 直接返回字符串
            response = await self.llm_provider.generate(prompt, messages=messages)
            return response
        except Exception as e:
            logger.error(f"Failed to generate clarification: {e}")
            # 回退到简单方法
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


# 简单测试
if __name__ == "__main__":
    print("Testing ModernAgent initialization...")
    initialize_tools()
    
    # 创建 Agent（无 LLM）
    agent = ModernAgent(llm_provider=None)
    
    print(f"\n✅ ModernAgent initialized with {len(agent.get_tool_list())} tools!")
    print("\nAvailable tools:")
    for tool in agent.get_tool_list():
        print(f"  - {tool['name']} ({tool.get('category', 'general')})")
