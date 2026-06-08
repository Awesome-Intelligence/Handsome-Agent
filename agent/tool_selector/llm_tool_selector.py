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
5. Agent 定义集成 - 从 agent.md、capabilities.md 等文件加载身份和能力边界
"""

import json
import logging
import os
import re
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from common.logging_manager import get_decision_logger, get_llm_logger


@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Optional[Callable] = None
    category: str = "general"
    examples: List[str] = field(default_factory=list)
    # 🏃 Execution - 🛠️ ToolExec - 工具标识（类型图标）
    emoji: str = "🔧"  # 默认图标，会被显示为 🔧=🔧
    
    def get_display_name(self) -> str:
        """获取带 emoji 的显示名称
        
        格式: 🔧=类型图标 工具名
        例如: 🔧=📁 read_file
        """
        return f"🔧={self.emoji} {self.name}"


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


class AgentDefinitionLoader:
    """
    Agent 定义加载器
    
    从 workspace 加载 Agent 的身份、性格、能力边界和用户信息
    参考 Hermes 和 OpenClaw 的实现方式
    
    架构：
    - 模板目录 (agent/templates/) - 存放默认配置模板
    - 用户工作空间 (~/.handsome_agent/) - 用户实际修改的配置
    """
    
    def __init__(self):
        from agent.workspace import get_workspace_manager
        
        self.workspace_manager = get_workspace_manager()
        self._definitions: Dict[str, str] = {}
        self.logger = get_decision_logger(self.__class__.__name__)
        self._load_definitions()
    
    def _load_definitions(self):
        """加载所有 agent 定义文件"""
        definition_files = {
            'identity': 'agent.md',
            'capabilities': 'capabilities.md',
            'memory': 'memory.md',
            'user': 'user.md',
            'tools': 'tools.md'
        }
        
        for key, filename in definition_files.items():
            try:
                content = self.workspace_manager.load_workspace_file(filename)
                if content:
                    self._definitions[key] = content
                    self.logger.info(f"Loaded agent definition from workspace: {filename}")
                else:
                    self.logger.warning(f"Agent definition file not found in workspace: {filename}")
            except Exception as e:
                self.logger.error(f"Failed to load {filename}: {e}")
    
    def get_identity_summary(self) -> str:
        """获取 Agent 身份摘要（用于系统提示）"""
        if 'identity' not in self._definitions:
            return "You are a helpful AI assistant."
        
        identity = self._definitions['identity']
        lines = identity.split('\n')
        summary_lines = []
        
        for line in lines:
            if line.startswith('#') or line.startswith('>'):
                continue
            if '## 🎭 身份定义' in line or '## 🧠 性格设定' in line:
                summary_lines.append(line)
            elif line.strip() and not line.startswith('---'):
                summary_lines.append(line)
        
        return '\n'.join(summary_lines[:50])
    
    def get_capabilities_summary(self) -> str:
        """获取能力摘要"""
        if 'capabilities' not in self._definitions:
            return ""
        
        capabilities = self._definitions['capabilities']
        lines = capabilities.split('\n')
        summary_lines = []
        
        for line in lines:
            if '## 🎯 能力概览' in line or '## ✅ 你能做的' in line or '## ❌ 你不能做的' in line:
                summary_lines.append(line)
            elif line.strip() and not line.startswith('---') and not line.startswith('#'):
                summary_lines.append(line)
        
        return '\n'.join(summary_lines[:30])
    
    def get_user_summary(self) -> str:
        """获取用户信息摘要（用于个性化服务）"""
        if 'user' not in self._definitions:
            return ""
        
        user_def = self._definitions['user']
        lines = user_def.split('\n')
        summary_lines = []
        
        # 提取关键用户信息
        for i, line in enumerate(lines):
            # 基本信息
            if '## 👤 用户基本信息' in line:
                summary_lines.append(line)
                # 添加接下来的配置行
                for j in range(i+1, min(i+10, len(lines))):
                    if lines[j].startswith('##'):
                        break
                    if lines[j].strip() and not lines[j].startswith('```'):
                        summary_lines.append(lines[j])
            
            # 交互偏好
            elif '## ⚙️ 用户偏好设置' in line:
                summary_lines.append(line)
            
            # 工作场景
            elif '## 🎯 工作场景' in line:
                summary_lines.append(line)
        
        if summary_lines:
            return '\n'.join(summary_lines)
        return ""
    
    def get_all_definitions(self) -> Dict[str, str]:
        """获取所有定义"""
        return self._definitions.copy()
    
    def reload(self):
        """重新加载配置（用于配置更新后）"""
        self._definitions.clear()
        self.workspace_manager.clear_cache()
        self._load_definitions()


class LLMToolSelector:
    """
    LLM 直接驱动的工具选择器

    职责：
    1. 工具注册与管理
    2. 工具选择（让 LLM 决定使用哪个工具）
    3. 工具执行
    
    注意：上下文构建已分离到 ContextBuilder
    """

    def __init__(self, llm_provider=None):
        """
        Args:
            llm_provider: LLM 提供者
        """
        self.llm_provider = llm_provider
        self.tools: Dict[str, ToolDefinition] = {}
        # 🧠 Decision - [/🔧ToolSelect] - 使用 tool_select 子层
        self.logger = get_decision_logger(self.__class__.__name__, sublayer="tool_select")
        
        # 工具选择器不负责上下文构建，移除了 AgentDefinitionLoader

    def register_tool(self, tool: ToolDefinition):
        """注册工具"""
        self.tools[tool.name] = tool
        self.logger.debug(f"Registered tool: {tool.name}")

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

    def _build_system_prompt(
        self, 
        conversation_history: Optional[List[Dict]] = None,
        user_input: str = ""
    ) -> str:
        """构建系统提示词（包含 Agent 定义和自动预取的记忆）
        
        注意：此方法已重定向到 ContextBuilder，会自动预取相关记忆（Hermes 风格）
        """
        from agent.context.context_builder import ContextBuilder
        
        # 🧠 Decision - [/🔧ToolSelect] - 委托给 ContextBuilder（传入 user_input 用于记忆预取）
        context_builder = ContextBuilder(tools=self.tools)
        return context_builder.build_system_prompt(
            conversation_history=conversation_history,
            user_message=user_input
        )

    def _keyword_fallback(self, user_input: str) -> ToolSelectionResult:
        """
        基于工具描述的相似度匹配（当 LLM 返回非 JSON 格式时使用）

        使用文本相似度而非硬编码关键词来匹配工具
        """
        if not self.tools:
            return ToolSelectionResult(
                selected_tool=None,
                action="direct_response",
                reasoning="No tools available",
                parameters={},
                confidence=0.0
            )

        best_tool = None
        best_score = 0.0

        # 计算用户输入与每个工具描述的相似度
        for tool_name, tool in self.tools.items():
            # 使用 Jaccard 相似度：用户输入 vs 工具描述
            score = self._calculate_similarity(user_input, tool.description)

            # 额外检查工具名称的匹配
            if tool_name.lower() in user_input.lower():
                score += 0.3

            if score > best_score:
                best_score = score
                best_tool = tool_name

        # 阈值判断
        if best_score > 0.05:
            # 相似度回退使用较高的最低 confidence，确保工具被执行
            confidence = max(0.5, best_score * 1.5)
            self.logger.info(f"Fallback matched {best_tool} with score {best_score:.2f}, confidence {confidence:.2f}")
            return ToolSelectionResult(
                selected_tool=best_tool,
                action="use_tool",
                reasoning=f"Similarity matched {best_tool} (score: {best_score:.2f})",
                parameters={},
                confidence=confidence
            )

        self.logger.info("No tool matched in similarity fallback")
        return ToolSelectionResult(
            selected_tool=None,
            action="direct_response",
            reasoning="No tool matched via similarity fallback",
            parameters={},
            confidence=0.1
        )

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本的相似度（Jaccard 系数）

        Args:
            text1: 用户输入
            text2: 工具描述

        Returns:
            相似度分数 (0.0 - 1.0)
        """
        # 分词（简单按中英文分割）
        import re
        words1 = set(re.findall(r'[\w]+', text1.lower()))
        words2 = set(re.findall(r'[\w]+', text2.lower()))

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0

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
            # 构建提示词（传入 user_input 用于记忆预取）
            system_prompt = self._build_system_prompt(conversation_history, user_input)

            # 添加上下文（如果有）
            if context:
                context_str = "\n\nContext:\n"
                for key, value in context.items():
                    context_str += f"- {key}: {value}\n"
                system_prompt += context_str

            # 调用 LLM
            self.logger.info("LLM Tool Selector: Requesting tool selection")
            # 添加决策格式说明（明确：需要工具时 action 为 use_tool）
            decision_instruction = '\n\n重要：请以 JSON 格式返回你的决策：\n- 如果需要使用工具：{"action": "use_tool", "tool": "工具名", "parameters": {...}}\n- 如果不需要工具：{"action": "direct_response", "reasoning": "原因"}'
            user_input_formatted = user_input + decision_instruction
            response = await self.llm_provider.generate(
                user_input_formatted,
                system_prompt=system_prompt
            )

            # 解析响应
            try:
                from agent.llm.providers.base import ProviderResponse
                if isinstance(response, ProviderResponse):
                    content = response.content
                else:
                    content = str(response)
                
                # 先尝试提取 JSON（处理模型返回的思维链标签）
                content_str = content.strip()
                # 匹配完整的 JSON 对象（支持嵌套），找第一个 { 到最后一个 } 之间的内容
                json_pattern = r'\{[\s\S]*"action"[\s\S]*\}'
                json_match = re.search(json_pattern, content_str)
                if json_match:
                    # 找到了包含 action 的 JSON，尝试解析
                    result = json.loads(json_match.group(0))
                else:
                    # 没有找到标准 JSON，尝试提取任何 JSON 对象
                    json_pattern_any = r'\{[\s\S]*\}'
                    json_match_any = re.search(json_pattern_any, content_str)
                    if json_match_any:
                        try:
                            result = json.loads(json_match_any.group(0))
                        except json.JSONDecodeError:
                            # JSON 解析失败，跳过工具调用
                            result = {}
                    else:
                        result = {}
                
                # 解析结果
                action = result.get('action')
                selected_tool = result.get('selected_tool') or result.get('tool')
                parameters = result.get('parameters', {})
                reasoning = result.get('reasoning', '')
                
                # 处理意外格式（如 {"decision": "allow", ...} 或 {"action": "finish", ...}）
                if not action:
                    # 没有 action 字段，检查是否有其他线索
                    if selected_tool:
                        action = "use_tool"
                    elif '_response' in result or 'response' in result:
                        # LLM 返回了回复内容但没有 action，说明不需要工具
                        action = "direct_response"
                        reasoning = result.get('reasoning') or result.get('reason', '')
                    else:
                        action = "direct_response"
                
                # 处理 "finish" 等非标准 action
                if action in ("finish", "end", "stop", "done", "allow", "none"):
                    action = "direct_response"
                
                # 如果 action 是 direct_response 且没有有效的 tool，使用关键词回退
                if action == "direct_response" and (not selected_tool or selected_tool not in self.tools):
                    self.logger.debug(f"LLM returned direct_response or unknown tool, using keyword fallback")
                    fallback_result = self._keyword_fallback(user_input)
                    return fallback_result
                
                # 验证工具是否存在
                if selected_tool and selected_tool not in self.tools:
                    self.logger.warning(f"LLM returned unknown tool: {selected_tool}, falling back to keyword matching")
                    # 尝试用关键词回退
                    fallback_result = self._keyword_fallback(user_input)
                    return fallback_result
                
                return ToolSelectionResult(
                    selected_tool=selected_tool,
                    action=action,
                    reasoning=reasoning,
                    parameters=parameters,
                    confidence=result.get('confidence', 0.5)
                )
            except json.JSONDecodeError:
                # 检测回复是否是对话内容（闲聊、问候等）
                content_str = content.strip() if isinstance(content, str) else str(content)
                
                # 🏃 Execution - 🛠️ ToolExec - 检测 XML 工具调用标签格式
                tool_call_pattern = r'<(\w+)>([^<]*)</\1>'
                tool_matches = re.findall(tool_call_pattern, content_str)
                
                if tool_matches:
                    # 过滤掉思维链标签（think, thought, reasoning 等）
                    thinking_tags = {"think", "thought", "reasoning", "analysis", "internal_thought", "reflection"}
                    valid_tool_matches = [(name, content) for name, content in tool_matches if name.lower() not in thinking_tags]
                    
                    if not valid_tool_matches:
                        self.logger.debug(f"Detected only thinking tags, skipping tool call detection")
                        # 继续检查是否是闲聊
                    else:
                        # 检测到工具调用标签，解析第一个匹配的工具
                        tool_name = valid_tool_matches[0][0]
                        # 参数解析（简单处理：如果有 command= 则提取）
                        params = {}
                        params_match = re.search(r'<parameters>(.*?)</parameters>', content_str, re.DOTALL)
                        if params_match:
                            try:
                                params = json.loads(params_match.group(1))
                            except:
                                pass
                        else:
                            # 尝试从工具标签内容中提取参数
                            tool_content = valid_tool_matches[0][1].strip()
                            if tool_name == 'execute_terminal':
                                cmd_match = re.search(r'<command>(.*?)</command>', tool_content, re.DOTALL)
                                if cmd_match:
                                    params['command'] = cmd_match.group(1).strip()
                        
                        self.logger.info(f"Detected tool call XML tag: {tool_name}, params: {params}")
                        return ToolSelectionResult(
                            selected_tool=tool_name,
                            action="use_tool",
                            reasoning=f"Detected tool call from XML tag: {tool_name}",
                            parameters=params,
                            confidence=0.9
                        )
                
                # 如果回复看起来像对话（短、以标点/表情开头、包含问候语等），视为闲聊
                is_conversation = (
                    len(content_str) < 500 and  # 回复较短
                    any(greeting in content_str for greeting in ['你好', '嗨', '哈', '嗨', 'hi', 'hello', '👋', '😊', '您好']) or
                    content_str.startswith(('哈哈', '嗯', '好的', '好的', 'OK', '好', '好的', '没问题'))
                )
                
                if is_conversation:
                    self.logger.info(f"Detected conversational response, treating as direct_response")
                    return ToolSelectionResult(
                        selected_tool=None,
                        action="direct_response",
                        reasoning="User appears to be greeting or chatting, responding directly",
                        parameters={},
                        confidence=0.8
                    )
                else:
                    self.logger.warning(f"Failed to parse LLM response as JSON: {content_str[:200]}")
                    # 无法解析 JSON，尝试使用关键词回退
                    self.logger.debug("Attempting keyword fallback for non-JSON response")
                    fallback_result = self._keyword_fallback(user_input)
                    return fallback_result

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
        self.logger = get_decision_logger(self.__class__.__name__)

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
        self.logger = get_decision_logger(self.__class__.__name__, sublayer="tool_select")

    def register_tool(self, tool: ToolDefinition):
        """注册工具及其处理器"""
        self.tools[tool.name] = tool
        self.logger.debug(f"Registered tool handler: {tool.name}")

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
            # 🏃 Execution - 🛠️ ToolExec - 使用带 emoji 的工具名称
            self.logger.info(f"Executing tool: {tool.get_display_name()}")
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
        self._llm_provider = llm_provider
        self.tool_selector = LLMToolSelector(llm_provider)
        self.direct_router = DirectToolRouter()
        self.execution_engine = ToolExecutionEngine()
        self.enable_llm_selection = enable_llm_selection
        self.logger = get_decision_logger(self.__class__.__name__)

    @property
    def llm_provider(self):
        """获取 LLM provider"""
        return self._llm_provider or self.tool_selector.llm_provider

    @llm_provider.setter
    def llm_provider(self, value):
        """设置 LLM provider（同时更新 tool_selector）"""
        self._llm_provider = value
        self.tool_selector.llm_provider = value

    def register_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Optional[Callable] = None,
        category: str = "general",
        examples: Optional[List[str]] = None,
        # 🏃 Execution - 🛠️ ToolExec - 工具标识
        emoji: str = "🔧"
    ):
        """注册工具"""
        tool = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler,
            category=category,
            examples=examples or [],
            emoji=emoji
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

        elif selection.action in ("finish", "end", "stop", "done"):
            # LLM 返回结束动作，应该视为 direct_response
            return {
                'type': 'direct_response',
                'selection': selection,
                'requires_llm_response': True
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
            'tool_count': len(self.tool_selector.tools),
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
