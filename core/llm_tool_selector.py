"""LLM-Driven Tool Selector - LLM 直接驱动的工具选择器

移除意图识别层，让 LLM 直接基于工具 schema 和上下文做决策。

架构变化：
旧架构：输入 → 意图识别 → 工具选择 → 执行
新架构：输入 + 工具列表 + 上下文 → LLM 直接决策 → 执行

设计原则：
1. LLM 自主决策 - 不做预分类，让 LLM 自己理解并选择
2. 工具 Schema 驱动 - 提供完整工具定义，LLM 理解能力
3. 上下文感知 - 会话历史和记忆提供上下文
4. 简单降级 - 无 LLM 时使用简单规则
"""

import json
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum


@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Optional[Callable] = None
    category: str = "general"
    examples: List[str] = field(default_factory=list)


@dataclass
class ToolSelectionResult:
    """工具选择结果"""
    selected_tool: Optional[str]
    action: str  # "use_tool", "direct_response", "ask clarification"
    reasoning: str
    parameters: Dict[str, Any]
    confidence: float
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None


class LLMToolSelector:
    """
    LLM 直接驱动的工具选择器

    工作流程：
    1. 构建工具 Schema（给 LLM 看）
    2. 构建上下文（给 LLM 参考）
    3. LLM 直接决策选择工具
    4. 如果没有 LLM，使用关键词回退
    """

    def __init__(self, llm_provider=None):
        """
        Args:
            llm_provider: LLM 提供者
        """
        self.llm_provider = llm_provider
        self.tools: Dict[str, ToolDefinition] = {}
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.propagate = False

    def register_tool(self, tool: ToolDefinition):
        """注册工具"""
        self.tools[tool.name] = tool
        self.logger.info(f"Registered tool: {tool.name}")

    def register_tools(self, tools: List[ToolDefinition]):
        """批量注册工具"""
        for tool in tools:
            self.register_tool(tool)

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """获取工具 Schema（用于 LLM）"""
        schema = []
        for tool in self.tools.values():
            schema.append({
                'name': tool.name,
                'description': tool.description,
                'parameters': tool.parameters
            })
        return schema

    def _build_system_prompt(self, conversation_history: Optional[List[Dict]] = None) -> str:
        """构建系统提示词"""
        tools_schema = json.dumps(self.get_tools_schema(), ensure_ascii=False, indent=2)

        history_context = ""
        if conversation_history:
            recent = conversation_history[-6:]  # 最近 6 轮对话
            history_context = "\n\nRecent conversation:\n"
            for msg in recent:
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')[:200]  # 截断
                history_context += f"- {role}: {content}\n"

        prompt = f"""You are a helpful AI assistant with access to various tools.

Available tools:
{tools_schema}

{history_context}

Your task:
1. Understand the user's request
2. Decide if you need to use a tool or respond directly
3. If using a tool, select the most appropriate one and provide parameters

Decision rules:
- Use a tool ONLY when necessary (e.g., need external data, execute commands, access files)
- For general knowledge questions, greetings, or conversations, respond directly
- If unsure about parameters, use reasonable defaults or ask for clarification

Response format (JSON):
{{
    "action": "use_tool" or "direct_response" or "ask_clarification",
    "selected_tool": "tool_name" (if action is "use_tool"),
    "parameters": {{}} (tool parameters if action is "use_tool"),
    "reasoning": "why you made this decision",
    "confidence": 0.0-1.0
}}

Respond with ONLY the JSON object, no other text."""

        return prompt

    def _keyword_fallback(self, user_input: str) -> ToolSelectionResult:
        """
        关键词回退（当没有 LLM 时使用）

        简单的关键词匹配，不做复杂分类
        """
        user_lower = user_input.lower()

        # 简单关键词映射
        tool_keywords = {
            'web_search': ['搜索', '搜一下', 'search', 'google', '百度', '查一下'],
            'terminal': ['终端', '命令', 'terminal', '执行', 'run', '打开', 'open', '启动'],
            'file_read': ['读取', '查看', 'cat', 'read'],
            'file_write': ['写入', '写', '保存', 'create file'],
            'weather': ['天气', 'weather', '温度'],
            'calculator': ['计算', '算一下', 'calculate', '计算器']
        }

        for tool_name, keywords in tool_keywords.items():
            if tool_name in self.tools:
                for keyword in keywords:
                    if keyword in user_lower:
                        return ToolSelectionResult(
                            selected_tool=tool_name,
                            action="use_tool",
                            reasoning=f"Keyword '{keyword}' matched {tool_name}",
                            parameters={'query': user_input},
                            confidence=0.6
                        )

        # 默认直接回复
        return ToolSelectionResult(
            selected_tool=None,
            action="direct_response",
            reasoning="No tool keyword matched, will respond directly",
            parameters={},
            confidence=0.5
        )

    async def select_tool(
        self,
        user_input: str,
        conversation_history: Optional[List[Dict]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ToolSelectionResult:
        """
        让 LLM 选择工具

        Args:
            user_input: 用户输入
            conversation_history: 对话历史
            context: 额外上下文（记忆等）

        Returns:
            ToolSelectionResult: 工具选择结果
        """
        # 如果没有注册工具，直接回复
        if not self.tools:
            return ToolSelectionResult(
                selected_tool=None,
                action="direct_response",
                reasoning="No tools registered",
                parameters={},
                confidence=1.0
            )

        # 如果没有 LLM，使用关键词回退
        if not self.llm_provider:
            self.logger.warning("No LLM provider, using keyword fallback")
            return self._keyword_fallback(user_input)

        try:
            # 构建提示词
            system_prompt = self._build_system_prompt(conversation_history)

            # 添加上下文（如果有）
            if context:
                context_str = "\n\nContext:\n"
                for key, value in context.items():
                    context_str += f"- {key}: {value}\n"
                system_prompt += context_str

            # 调用 LLM
            self.logger.info("LLM Tool Selector: Requesting tool selection")
            response = await self.llm_provider.generate(system_prompt + f"\n\nUser: {user_input}")

            # 解析响应
            try:
                result = json.loads(response.strip())
                return ToolSelectionResult(
                    selected_tool=result.get('selected_tool'),
                    action=result.get('action', 'direct_response'),
                    reasoning=result.get('reasoning', ''),
                    parameters=result.get('parameters', {}),
                    confidence=result.get('confidence', 0.5)
                )
            except json.JSONDecodeError:
                self.logger.error(f"Failed to parse LLM response as JSON: {response[:200]}")
                # 回退到直接回复
                return ToolSelectionResult(
                    selected_tool=None,
                    action="direct_response",
                    reasoning="LLM response parsing failed, responding directly",
                    parameters={},
                    confidence=0.3
                )

        except Exception as e:
            self.logger.error(f"Tool selection failed: {e}")
            return ToolSelectionResult(
                selected_tool=None,
                action="direct_response",
                reasoning=f"Error in tool selection: {str(e)}",
                parameters={},
                confidence=0.0,
                error=str(e)
            )


class DirectToolRouter:
    """
    直接工具路由器（无 LLM）

    基于工具描述的相似度匹配
    """

    def __init__(self):
        self.tools: Dict[str, ToolDefinition] = {}
        self.logger = logging.getLogger(self.__class__.__name__)

    def register_tool(self, tool: ToolDefinition):
        """注册工具"""
        self.tools[tool.name] = tool

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """简单的文本相似度计算"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union)

    async def route(self, user_input: str) -> Optional[ToolDefinition]:
        """
        路由到合适的工具

        Args:
            user_input: 用户输入

        Returns:
            最匹配的工具，如果没有匹配返回 None
        """
        if not self.tools:
            return None

        best_tool = None
        best_score = 0.0

        for tool in self.tools.values():
            # 计算与工具描述的相似度
            score = self._calculate_similarity(user_input, tool.description)

            # 额外检查关键词
            for keyword in tool.examples:
                if keyword.lower() in user_input.lower():
                    score += 0.3

            if score > best_score:
                best_score = score
                best_tool = tool

        if best_score > 0.1:  # 阈值
            self.logger.info(f"Routed to {best_tool.name} with score {best_score:.2f}")
            return best_tool

        return None


class ToolExecutionEngine:
    """
    工具执行引擎

    负责执行选定的工具
    """

    def __init__(self):
        self.tools: Dict[str, ToolDefinition] = {}
        self.logger = logging.getLogger(self.__class__.__name__)

    def register_tool(self, tool: ToolDefinition):
        """注册工具及其处理器"""
        self.tools[tool.name] = tool
        self.logger.info(f"Registered tool handler: {tool.name}")

    async def execute(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行工具

        Args:
            tool_name: 工具名称
            parameters: 工具参数
            context: 执行上下文

        Returns:
            执行结果
        """
        if tool_name not in self.tools:
            return {
                'success': False,
                'error': f"Tool '{tool_name}' not found",
                'result': None
            }

        tool = self.tools[tool_name]

        if not tool.handler:
            return {
                'success': False,
                'error': f"Tool '{tool_name}' has no handler",
                'result': None
            }

        try:
            self.logger.info(f"Executing tool: {tool_name}")
            result = await tool.handler(parameters, context or {})

            return {
                'success': True,
                'error': None,
                'result': result,
                'tool': tool_name
            }

        except Exception as e:
            self.logger.error(f"Tool execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'result': None,
                'tool': tool_name
            }


class LLMDrivenDecisionEngine:
    """
    LLM 驱动的决策引擎（核心）

    整合工具选择和执行，移除意图识别层
    """

    def __init__(
        self,
        llm_provider=None,
        enable_llm_selection: bool = True
    ):
        """
        Args:
            llm_provider: LLM 提供者
            enable_llm_selection: 是否启用 LLM 工具选择
        """
        self.tool_selector = LLMToolSelector(llm_provider)
        self.direct_router = DirectToolRouter()
        self.execution_engine = ToolExecutionEngine()
        self.enable_llm_selection = enable_llm_selection
        self.logger = logging.getLogger(self.__class__.__name__)

    def register_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Optional[Callable] = None,
        category: str = "general",
        examples: Optional[List[str]] = None
    ):
        """注册工具"""
        tool = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler,
            category=category,
            examples=examples or []
        )

        self.tool_selector.register_tool(tool)
        self.direct_router.register_tool(tool)
        self.execution_engine.register_tool(tool)

    async def process(
        self,
        user_input: str,
        conversation_history: Optional[List[Dict]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        处理用户输入

        流程：
        1. LLM 选择工具（或关键词回退）
        2. 如果需要工具，执行工具
        3. 如果直接回复，返回控制权给主 LLM

        Args:
            user_input: 用户输入
            conversation_history: 对话历史
            context: 上下文（记忆等）

        Returns:
            处理结果
        """
        # 1. 工具选择
        if self.enable_llm_selection:
            selection = await self.tool_selector.select_tool(
                user_input,
                conversation_history,
                context
            )
        else:
            # 使用直接路由
            selected_tool = await self.direct_router.route(user_input)
            if selected_tool:
                selection = ToolSelectionResult(
                    selected_tool=selected_tool.name,
                    action="use_tool",
                    reasoning="Matched via direct routing",
                    parameters={},
                    confidence=0.5
                )
            else:
                selection = ToolSelectionResult(
                    selected_tool=None,
                    action="direct_response",
                    reasoning="No tool matched",
                    parameters={},
                    confidence=0.5
                )

        self.logger.info(
            f"Decision: {selection.action} "
            f"(tool: {selection.selected_tool}, confidence: {selection.confidence:.2f})"
        )

        # 2. 执行或返回
        if selection.action == "use_tool" and selection.selected_tool:
            result = await self.execution_engine.execute(
                selection.selected_tool,
                selection.parameters,
                context
            )

            return {
                'type': 'tool_execution',
                'tool': selection.selected_tool,
                'result': result,
                'selection': selection,
                'requires_llm_response': True  # 工具执行后需要 LLM 总结
            }

        elif selection.action == "direct_response":
            return {
                'type': 'direct_response',
                'selection': selection,
                'requires_llm_response': True  # 需要 LLM 直接回复
            }

        elif selection.action == "ask_clarification":
            return {
                'type': 'clarification_needed',
                'selection': selection,
                'requires_llm_response': True  # 需要 LLM 询问
            }

        else:
            return {
                'type': 'unknown',
                'selection': selection,
                'requires_llm_response': True
            }

    def get_capabilities(self) -> Dict[str, Any]:
        """获取当前能力"""
        return {
            'tool_count': len(self.tools),
            'tools': [
                {
                    'name': tool.name,
                    'description': tool.description,
                    'category': tool.category
                }
                for tool in self.tool_selector.tools.values()
            ],
            'llm_selection_enabled': self.enable_llm_selection
        }
