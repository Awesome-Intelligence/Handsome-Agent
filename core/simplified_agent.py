"""
Simplified Agent Core - 简化版 Agent 核心

展示如何移除意图识别层，使用 LLM 直接决策

旧架构流程：
Input → Intent Recognition → Tool Selection → Tool Execution → Response

新架构流程：
Input + Tools Schema + Context → LLM Direct Decision → Tool Execution → Response

核心变化：
1. 移除 IntentClassifier
2. 移除 IntentResult
3. LLM 直接看工具列表，自己决定用哪个
4. 简化决策流程
"""

import json
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum


class ActionType(Enum):
    """动作类型"""
    USE_TOOL = "use_tool"
    DIRECT_RESPONSE = "direct_response"
    ASK_CLARIFICATION = "ask_clarification"


@dataclass
class Tool:
    """工具定义"""
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    handler: Optional[Callable] = None


@dataclass
class DecisionResult:
    """LLM 决策结果"""
    action: ActionType
    selected_tool: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""
    confidence: float = 0.0


class SimplifiedAgent:
    """
    简化版 Agent - 无意图识别层

    核心特点：
    1. LLM 直接看工具，自己选
    2. 不做预分类
    3. 简单直接
    """

    def __init__(
        self,
        llm_provider=None,
        tools: Optional[List[Tool]] = None
    ):
        """
        Args:
            llm_provider: LLM 提供者
            tools: 可用工具列表
        """
        self.llm_provider = llm_provider
        self.tools = {t.name: t for t in (tools or [])}
        self.logger = logging.getLogger(self.__class__.__name__)

    def add_tool(self, tool: Tool):
        """添加工具"""
        self.tools[tool.name] = tool

    def _build_tools_prompt(self) -> str:
        """构建工具描述（给 LLM 看）"""
        if not self.tools:
            return "No tools available."

        tools_desc = []
        for name, tool in self.tools.items():
            params = json.dumps(tool.parameters, ensure_ascii=False)
            tools_desc.append(f"- {name}: {tool.description}\n  Parameters: {params}")

        return "\n".join(tools_desc)

    async def _llm_decide(
        self,
        user_input: str,
        context: Dict[str, Any]
    ) -> DecisionResult:
        """
        LLM 自己做决策

        这是核心变化：不给 LLM 预定义的意图类型，
        让它直接看工具列表，自己决定要不要用，用哪个
        """
        if not self.llm_provider:
            return DecisionResult(
                action=ActionType.DIRECT_RESPONSE,
                reasoning="No LLM provider"
            )

        tools_prompt = self._build_tools_prompt()
        history = context.get('conversation_history', [])
        memory = context.get('relevant_memory', [])

        # 构建提示词
        prompt = f"""You are an AI assistant.

Available tools:
{tools_prompt}

Recent conversation:
{json.dumps(history[-6:], ensure_ascii=False)}

Your knowledge:
{json.dumps(memory, ensure_ascii=False)}

User request: {user_input}

Decide:
- If the user wants to use a tool (search, calculate, execute command, etc.), respond with:
  {{"action": "use_tool", "tool": "tool_name", "parameters": {{}}, "reasoning": "..."}}

- If you can answer directly without tools, respond with:
  {{"action": "direct_response", "reasoning": "..."}}

- If you need more information, respond with:
  {{"action": "ask_clarification", "reasoning": "..."}}

Respond with ONLY JSON."""

        try:
            response = await self.llm_provider.generate(prompt)
            result = json.loads(response.strip())

            action = ActionType(result.get('action', 'direct_response'))
            return DecisionResult(
                action=action,
                selected_tool=result.get('tool'),
                parameters=result.get('parameters', {}),
                reasoning=result.get('reasoning', ''),
                confidence=0.8
            )

        except Exception as e:
            self.logger.error(f"LLM decision failed: {e}")
            return DecisionResult(
                action=ActionType.DIRECT_RESPONSE,
                reasoning=f"Error: {str(e)}"
            )

    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> Any:
        """执行工具"""
        if tool_name not in self.tools:
            return {'error': f"Tool '{tool_name}' not found"}

        tool = self.tools[tool_name]
        if not tool.handler:
            return {'error': f"Tool '{tool_name}' has no handler"}

        try:
            return await tool.handler(parameters)
        except Exception as e:
            return {'error': str(e)}

    async def chat(
        self,
        user_input: str,
        conversation_history: Optional[List[Dict]] = None,
        memory: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        处理用户输入

        流程：
        1. LLM 决定是否用工具
        2. 如果用，执行工具
        3. 如果不用或工具执行完，返回结果给主 LLM 生成回复
        """
        context = {
            'conversation_history': conversation_history or [],
            'relevant_memory': memory or []
        }

        # 1. LLM 决策
        decision = await self._llm_decide(user_input, context)

        self.logger.info(
            f"Decision: {decision.action.value} "
            f"(tool: {decision.selected_tool})"
        )

        # 2. 执行或准备回复
        if decision.action == ActionType.USE_TOOL:
            tool_result = await self.execute_tool(
                decision.selected_tool,
                decision.parameters
            )

            return {
                'type': 'tool_used',
                'tool': decision.selected_tool,
                'result': tool_result,
                'needs_summary': True  # 需要 LLM 总结结果
            }

        elif decision.action == ActionType.DIRECT_RESPONSE:
            return {
                'type': 'direct',
                'needs_llm_response': True  # 需要 LLM 直接回复
            }

        elif decision.action == ActionType.ASK_CLARIFICATION:
            return {
                'type': 'clarification',
                'question': "Could you provide more details?",
                'needs_llm_response': True
            }

        return {
            'type': 'unknown',
            'needs_llm_response': True
        }


# 示例：使用简化版 Agent
async def example():
    """使用示例"""
    # 模拟 LLM provider
    class MockLLM:
        async def generate(self, prompt: str) -> str:
            if "use_tool" in prompt:
                return '{"action": "use_tool", "tool": "calculator", "parameters": {"expr": "2+2"}}'
            return '{"action": "direct_response", "reasoning": "Simple greeting"}'

    # 创建 Agent
    async def calc_handler(params):
        expr = params.get('expr', '0')
        return {'result': eval(expr)}

    tools = [
        Tool(
            name='calculator',
            description='Calculate mathematical expressions',
            parameters={'expr': 'expression string'},
            handler=calc_handler
        ),
        Tool(
            name='web_search',
            description='Search the web for information',
            parameters={'query': 'search query'},
            handler=None
        )
    ]

    agent = SimplifiedAgent(llm_provider=MockLLM(), tools=tools)

    # 处理请求
    result = await agent.chat("What is 2+2?")

    print(f"Result: {result}")
    # 输出: {'type': 'tool_used', 'tool': 'calculator', 'result': {'result': 4}, 'needs_summary': True}


# 使用提示
"""
迁移指南：

旧代码：
  from core.router import IntentClassifier
  from core.llm_intent_service import LLMIntentService

  intent_classifier = IntentClassifier()
  intent_result = await intent_classifier.classify(user_input)
  if intent_result == 'operation':
      tool = select_operation_tool(...)
      result = await tool.execute(...)

新代码：
  from core.llm_tool_selector import SimplifiedAgent

  agent = SimplifiedAgent(llm_provider=llm, tools=my_tools)
  decision = await agent.chat(user_input, history, memory)

  if decision['type'] == 'tool_used':
      # 工具已执行，结果在 decision['result']
      result = decision['result']
  elif decision['needs_llm_response']:
      # 需要 LLM 直接回复用户
      response = await llm.generate(user_input)

主要变化：
1. 移除 IntentClassifier - 不再做预分类
2. 移除 IntentResult - 用 DecisionResult 替代
3. LLM 直接看工具，自己决定用哪个
4. 简化决策流程
"""
