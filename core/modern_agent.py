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

from core.simplified_agent import ActionType
from core.session import session_manager, Session, Message
from tools.integrated_tools import (
    get_integrated_engine,
    initialize_tools
)
from core.logging_manager import (
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
    3. 支持会话管理
    4. 支持记忆系统
    """
    
    def __init__(
        self,
        llm_provider=None,
        enable_session: bool = True,
        session_id: Optional[str] = None
    ):
        """
        Args:
            llm_provider: LLM 提供者
            enable_session: 是否启用会话管理
            session_id: 会话 ID（如果需要恢复会话）
        """
        self.llm_provider = llm_provider
        self.enable_session = enable_session
        
        # 初始化工具引擎
        self.engine = get_integrated_engine(llm_provider=llm_provider)
        
        # 初始化会话
        self._session: Optional[Session] = None
        if self.enable_session:
            self._session = session_manager.create_session(session_id)
        
        # 获取日志记录器
        self._access_logger = get_access_logger("ModernAgent")
        self._decision_logger = get_decision_logger("ModernAgent")
        self._execution_logger = get_execution_logger("ModernAgent")
        self._tool_logger = get_tool_logger("ModernAgent")
    
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
        
        # 准备对话历史
        history = conversation_history
        if not history and self._session:
            history = self._get_session_messages()
        
        # 记录到会话
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
            
            # 让 LLM 总结工具结果
            if self.llm_provider:
                final_response = await self._summarize_with_llm(
                    user_input,
                    tool_name,
                    tool_result
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
            # 直接使用 LLM 响应
            if self.llm_provider:
                final_response = await self.llm_provider.generate(user_input)
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
                final_response = await self.llm_provider.generate(
                    f"User asked: {user_input}. You need to ask for clarification. Reason: {clarification}"
                )
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
        tool_result: Any
    ) -> str:
        """
        使用 LLM 总结工具执行结果
        
        Args:
            user_input: 用户输入
            tool_name: 工具名称
            tool_result: 工具结果
        
        Returns:
            总结后的响应
        """
        try:
            result_str = json.dumps(tool_result, ensure_ascii=False)
            prompt = f"""User asked: {user_input}

I executed tool: {tool_name}
Tool result: {result_str}

Please provide a natural language response to the user based on the tool result."""
            
            return await self.llm_provider.generate(prompt)
        except Exception as e:
            logger.error(f"Failed to summarize with LLM: {e}")
            return f"Tool {tool_name} executed. Result: {json.dumps(tool_result, ensure_ascii=False)}"
    
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
