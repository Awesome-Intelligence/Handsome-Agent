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
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


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
        from .workspace import get_workspace_manager
        
        self.workspace_manager = get_workspace_manager()
        self._definitions: Dict[str, str] = {}
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
                    logging.getLogger(__name__).info(f"Loaded agent definition from workspace: {filename}")
                else:
                    logging.getLogger(__name__).warning(f"Agent definition file not found in workspace: {filename}")
            except Exception as e:
                logging.getLogger(__name__).error(f"Failed to load {filename}: {e}")
    
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
        
        self.agent_loader = AgentDefinitionLoader()

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
        """构建系统提示词（包含 Agent 定义）"""
        tools_schema = json.dumps(self.get_tools_schema(), ensure_ascii=False, indent=2)

        history_context = ""
        if conversation_history:
            recent = conversation_history[-6:]
            history_context = "\n\nRecent conversation:\n"
            for msg in recent:
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')[:200]
                history_context += f"- {role}: {content}\n"

        identity_summary = self.agent_loader.get_identity_summary()
        capabilities_summary = self.agent_loader.get_capabilities_summary()
        user_summary = self.agent_loader.get_user_summary()

        prompt = f"""{identity_summary}

{capabilities_summary}

User Profile:
{user_summary if user_summary else "User information not configured. Provide general assistance."}

Available tools:
{tools_schema}

{history_context}

Your task:
1. Understand the user's request based on your identity and capabilities
2. Consider the user's background and preferences
3. Decide if you need to use a tool or respond directly
4. If using a tool, select the most appropriate one and provide parameters
5. Stay within your capabilities - do not attempt actions you cannot perform

Decision rules:
- Use a tool ONLY when necessary (e.g., need external data, execute commands, access files)
- For general knowledge questions, greetings, or conversations, respond directly
- If unsure about parameters, use reasonable defaults or ask for clarification
- If the request is outside your capabilities, politely explain and suggest alternatives
- Personalize your response based on the user's background and preferences

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

        # 关键词到工具的映射
        keyword_tool_mapping = {
            # 计算器相关
            '计算': 'open_calculator',
            '算一下': 'open_calculator',
            'calculator': 'open_calculator',
            '打开计算器': 'open_calculator',
            # 记事本相关
            '记事本': 'open_notepad',
            '打开记事本': 'open_notepad',
            # CMD相关
            'cmd': 'open_cmd',
            '命令提示符': 'open_cmd',
            '终端': 'open_cmd',
            '打开终端': 'open_cmd',
            # 文件夹相关
            '文件夹': 'open_folder',
            '打开文件夹': 'open_folder',
            '打开目录': 'open_folder',
            # 浏览器相关
            '浏览器': 'launch_app',
            '打开浏览器': 'launch_app',
            # 文件操作相关（优先于通用"打开"）
            '打开文件': 'open_file',
            '读取文件': 'read_file',
            '查看文件': 'read_file',
            '看看文件': 'read_file',
            '读文件': 'read_file',
            'open file': 'open_file',
            'read file': 'read_file',
            # 打开/启动相关（catch-all，放在最后）
            '打开': 'launch_app',
            '启动': 'launch_app',
            'open': 'launch_app',
            'launch': 'launch_app',
        }

        # 搜索匹配的关键词
        for keyword, tool_name in keyword_tool_mapping.items():
            if keyword in user_lower:
                if tool_name in self.tools:
                    # 为 open_folder 特殊处理参数
                    if tool_name == 'open_folder':
                        path = user_lower.replace('帮我', '').replace('请', '').replace('打开', '').replace('文件夹', '').replace('目录', '').strip()
                        return ToolSelectionResult(
                            selected_tool=tool_name,
                            action="use_tool",
                            reasoning=f"Keyword '{keyword}' matched {tool_name}",
                            parameters={'path': path if path else None},
                            confidence=0.8
                        )
                    # 为 read_file / open_file 特殊处理参数
                    if tool_name in ('read_file', 'open_file'):
                        path = user_lower.replace('帮我', '').replace('请', '').replace('打开', '').replace('读取', '').replace('查看', '').replace('看看', '').replace('读', '').replace('文件', '').replace('open', '').replace('read', '').replace('file', '').strip()
                        return ToolSelectionResult(
                            selected_tool=tool_name,
                            action="use_tool",
                            reasoning=f"Keyword '{keyword}' matched {tool_name}",
                            parameters={'path': path if path else None},
                            confidence=0.8
                        )
                    else:
                        return ToolSelectionResult(
                            selected_tool=tool_name,
                            action="use_tool",
                            reasoning=f"Keyword '{keyword}' matched {tool_name}",
                            parameters={'app_name': keyword.replace('打开', '').replace('启动', '')},
                            confidence=0.7
                        )

        # 如果没有关键词匹配，但用户明确说要打开应用，尝试使用 launch_app
        if any(word in user_lower for word in ['打开', '启动', 'open', 'launch', 'start']):
            raw_name = user_lower.replace('帮我', '').replace('请', '').replace('打开', '').replace('启动', '').strip()
            # 如果提取的名称看起来像文件（有扩展名 或 被引号包裹），用 open_file
            has_extension = '.' in raw_name.split()[-1] if raw_name else False
            if has_extension and 'open_file' in self.tools:
                return ToolSelectionResult(
                    selected_tool='open_file',
                    action="use_tool",
                    reasoning="Detected open intent for file (has extension), using open_file",
                    parameters={'path': raw_name},
                    confidence=0.7
                )
            if 'launch_app' in self.tools:
                return ToolSelectionResult(
                    selected_tool='launch_app',
                    action="use_tool",
                    reasoning="Detected open/launch intent, using launch_app",
                    parameters={'app_name': raw_name},
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
                
                # 兼容两种格式："selected_tool" 或 "tool"
                selected_tool = result.get('selected_tool') or result.get('tool')
                
                return ToolSelectionResult(
                    selected_tool=selected_tool,
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
