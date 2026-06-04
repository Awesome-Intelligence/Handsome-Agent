#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Context Builder - 独立的上下文构建器

将上下文拼装逻辑从 LLMToolSelector 中分离出来，职责更清晰。

参考 Hermes 的 system_prompt.py 和 prompt_builder.py 实现。

架构：
- ContextBuilder: 专门负责构建完整的系统提示词
- LLMToolSelector: 只负责工具选择 + 执行

功能：
1. Agent 定义（身份、能力、用户信息）
2. 构建工具 Schema
3. 收集对话历史
4. 自动 Prefetch 相关记忆（Hermes 风格）
5. 组装完整的系统提示词

日志子层：💾 Context
"""

import json
import re
from typing import Dict, List, Optional, Any, TYPE_CHECKING

from common.logging_manager import get_decision_logger
from agent.workspace import get_workspace_manager
from agent.context.prompt_templates import (
    AGENT_IDENTITY,
    CAPABILITIES,
    MEMORY_GUIDANCE,
    SESSION_SEARCH_GUIDANCE,
    SKILLS_GUIDANCE,
    TOOL_USAGE_GUIDANCE,
    DEFAULT_USER_PROFILE,
)

if TYPE_CHECKING:
    from tools.memory_tool import MemoryStore


class ContextBuilder:
    """
    上下文构建器 - 专门负责构建完整的系统提示词
    
    职责：
    1. 加载 Agent 定义（身份、能力、用户信息）
    2. 构建工具 Schema
    3. 收集对话历史
    4. 自动 Prefetch 相关记忆（Hermes 风格）
    5. 组装完整的系统提示词
    
    日志子层：💾 Context
    """
    
    def __init__(
        self,
        tools: Optional[Dict[str, Any]] = None,
        enable_guidance: bool = True,
        enable_memory_prefetch: bool = True
    ):
        """
        Args:
            tools: 工具字典 {name: ToolDefinition}
            enable_guidance: 是否添加工具使用指导（memory, skills 等）
            enable_memory_prefetch: 是否启用记忆预取（默认启用，Hermes 风格）
        """
        self.logger = get_decision_logger(self.__class__.__name__, sublayer="context")
        self.tools = tools or {}
        self.enable_guidance = enable_guidance
        self.enable_memory_prefetch = enable_memory_prefetch
        
        # 延迟加载 MemoryStore（避免循环导入）
        self._memory_store: Optional["MemoryStore"] = None
        
        # 🧠 Decision - 💾 Context - 上下文构建器初始化
        self.logger.debug(f"ContextBuilder initialized (memory_prefetch={enable_memory_prefetch})")
    
    @property
    def memory_store(self) -> "MemoryStore":
        """懒加载 MemoryStore（延迟导入避免循环依赖）"""
        if self._memory_store is None:
            from tools.memory_tool import MemoryStore
            self._memory_store = MemoryStore()
            self._memory_store.load_from_disk()
            self.logger.info("MemoryStore loaded")
        return self._memory_store

    def set_tools(self, tools: Dict[str, Any]) -> None:
        """设置工具字典"""
        self.tools = tools
        self.logger.debug(f"Tools set: {len(tools)} tools available")
    
    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """获取工具 Schema（用于 LLM）"""
        schema = []
        for tool_name, tool in self.tools.items():
            tool_name = tool.name if hasattr(tool, 'name') else tool_name
            tool_desc = tool.description if hasattr(tool, 'description') else ''
            tool_params = tool.parameters if hasattr(tool, 'parameters') else {}
            
            # 构建完整的工具 schema（包含 name, description, parameters）
            param_props = {}
            if isinstance(tool_params, dict):
                # 提取 parameters.properties
                if 'properties' in tool_params:
                    param_props = tool_params['properties']
                elif 'type' not in tool_params:
                    # 如果参数是简单 dict，转换为 schema
                    param_props = tool_params
            
            schema.append({
                'name': tool_name,
                'description': tool_desc,
                'parameters': {
                    'type': 'object',
                    'properties': param_props,
                    'required': []  # 可根据工具定义添加
                }
            })
        return schema
    
    def build_system_prompt(
        self,
        conversation_history: Optional[List[Dict]] = None,
        include_tools: bool = True,
        user_message: str = "",
        model: str = None
    ) -> str:
        """
        构建完整的系统提示词（Hermes 风格）
        
        自动预取相关记忆并注入上下文，实现"一步到位"。
        
        Args:
            conversation_history: 对话历史
            include_tools: 是否包含工具列表
            user_message: 用户消息（用于检索相关记忆）
            model: 模型名称（用于注入模型特定指导）
            
        Returns:
            完整的系统提示词
        """
        # 🧠 Decision - 💾 Context - 开始构建上下文
        self.logger.debug("Context Assembly: Starting prompt building")
        
        # 使用代码常量定义 Agent 身份和能力（Hermes 风格）
        identity = AGENT_IDENTITY
        capabilities = CAPABILITIES
        
        # 🧠 Decision - 💾 Context - 记录各部分长度
        self.logger.info(
            f"Context Assembly: identity={len(identity)} chars, "
            f"capabilities={len(capabilities)} chars"
        )
        
        # 自动预取相关记忆（Hermes 风格）
        memory_context = ""
        if self.enable_memory_prefetch and user_message:
            memory_context = self._prefetch_memories(user_message)
        
        # 构建对话历史上下文
        history_context = ""
        history_msg_count = 0
        if conversation_history:
            recent = conversation_history[-6:]
            history_msg_count = len(recent)
            history_context = "\n\nRecent conversation:\n"
            for msg in recent:
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')[:200]
                history_context += f"- {role}: {content}\n"
        
        # 🧠 Decision - 💾 Context - 构建工具列表
        tools_schema = ""
        tools_schema_len = 0
        if include_tools and self.tools:
            tools_schema = json.dumps(self.get_tools_schema(), ensure_ascii=False, indent=2)
            tools_schema_len = len(tools_schema)
        
        self.logger.info(
            f"Context Assembly: tools_schema={tools_schema_len} chars, "
            f"history={history_msg_count} messages, "
            f"memory_prefetch={len(memory_context)} chars"
        )
        
        # 组装提示词
        prompt_parts = []
        
        # 1. 身份定义（使用代码常量）
        prompt_parts.append(identity)
        
        # 2. 能力摘要（使用代码常量）
        prompt_parts.append(capabilities)
        
        # 3. 用户信息（使用代码常量或从文件加载）
        prompt_parts.append(self._get_user_profile())
        
        # 4. 自动注入相关记忆（Hermes 风格）
        if memory_context:
            prompt_parts.append(memory_context)
        
        # 5. 工具使用指导（使用代码常量，含模型特定指导）
        if self.enable_guidance:
            guidance = self._build_guidance(model)
            if guidance:
                prompt_parts.append(guidance)
        
        # 6. 工具列表
        if include_tools and self.tools:
            prompt_parts.append(f"Available tools:\n{tools_schema}")
            prompt_parts.append(TOOL_USAGE_GUIDANCE)
        
        # 7. 对话历史
        if history_context:
            prompt_parts.append(history_context)
        
        prompt = "\n\n".join(prompt_parts)
        
        # 🧠 Decision - 💾 Context - 上下文构建完成
        self.logger.info(
            f"Context Assembly complete: total={len(prompt)} chars, "
            f"tools_count={len(self.tools)}"
        )
        
        return prompt
    
    def _get_user_profile(self) -> str:
        """
        获取用户画像
        
        优先从文件加载，失败时使用默认模板（Hermes 风格）。
        """
        # 尝试从文件加载 USER.md
        from pathlib import Path
        try:
            workspace_dir = Path.home() / ".handsome_agent" / "memories"
            user_file = workspace_dir / "USER.md"
            if user_file.exists():
                with open(user_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                if content.strip():
                    return f"## 👤 User Profile\n\n{content}"
        except Exception:
            pass
        
        # 使用默认模板
        return DEFAULT_USER_PROFILE
    
    def _prefetch_memories(self, query: str) -> str:
        """
        预取与查询相关的记忆（Hermes 风格）
        
        根据用户输入自动检索相关记忆，实现"一步到位"。
        
        Args:
            query: 用户输入或任务描述
            
        Returns:
            格式化的记忆上下文字符串
        """
        if not query:
            return ""
        
        try:
            # 从 MemoryStore 读取记忆
            memory_entries = self.memory_store.read("memory")
            user_entries = self.memory_store.read("user")
            
            if not memory_entries.get("entries") and not user_entries.get("entries"):
                self.logger.debug("No memory entries found")
                return ""
            
            # 关键词匹配检索
            relevant_memories = self._find_relevant_memories(query, [
                *memory_entries.get("entries", []),
                *user_entries.get("entries", [])
            ])
            
            if not relevant_memories:
                return ""
            
            # 格式化为系统提示块（Hermes 风格）
            return self._format_memory_context(relevant_memories)
            
        except Exception as e:
            self.logger.warning(f"Memory prefetch failed: {e}")
            return ""
    
    def _find_relevant_memories(
        self,
        query: str,
        entries: List[str],
        max_entries: int = 5
    ) -> List[str]:
        """
        找出与查询相关的记忆条目
        
        使用子字符串匹配 + 评分算法，支持中文。
        
        Args:
            query: 查询文本
            entries: 所有记忆条目
            max_entries: 最大返回条目数
            
        Returns:
            相关的记忆条目列表
        """
        if not entries or not query:
            return []
        
        query_lower = query.lower()
        scored_entries: List[tuple[str, float]] = []
        
        for entry in entries:
            entry_lower = entry.lower()
            
            # 方法1：检查查询词是否是条目的子串
            if query_lower in entry_lower:
                scored_entries.append((entry, 1.0))
                continue
            
            # 方法2：计算字符级别的重叠
            # 将中文文本按字符分解
            query_chars = set(query_lower)
            entry_chars = set(entry_lower)
            
            # 排除标点符号
            punctuation = set('，。！？、：；""''（）【】《》.,!?:"\'()[]{}')
            query_chars -= punctuation
            entry_chars -= punctuation
            
            # 计算重叠
            overlap = query_chars & entry_chars
            overlap_ratio = len(overlap) / len(query_chars) if query_chars else 0
            
            if overlap_ratio >= 0.3:  # 至少30%字符重叠
                # 短条目优先（通常是核心事实）
                length_score = 1.0 / (len(entry) / 100 + 1)
                score = overlap_ratio * 0.7 + length_score * 0.3
                scored_entries.append((entry, score))
        
        # 按评分排序，取前 max_entries 个
        scored_entries.sort(key=lambda x: x[1], reverse=True)
        return [entry for entry, _ in scored_entries[:max_entries]]
    
    def _format_memory_context(self, entries: List[str]) -> str:
        """
        格式化记忆为系统提示块（Hermes 风格）
        
        使用 <memory-context> 标签包裹，与 Hermes 保持一致。
        
        Args:
            entries: 相关的记忆条目
            
        Returns:
            格式化的记忆上下文
        """
        if not entries:
            return ""
        
        content = "\n".join(f"- {entry}" for entry in entries)
        
        return f"""<memory-context>
[System note: The following is recalled memory context, NOT new user input. Treat as authoritative reference data — this is the agent's persistent memory and should inform all responses.]

{content}
</memory-context>"""
    
    def _build_guidance(self, model: str = None) -> str:
        """
        构建指导性文本（Hermes 风格）
        
        使用代码常量定义指导文本，帮助 LLM 更好地使用记忆、技能等功能。
        
        借鉴 Hermes 的设计：
        1. 分层组织：stable (稳定) / context (上下文) / volatile (可变)
        2. 工具感知：只有当工具可用时才添加相关指导
        3. 模型特定：不同模型有不同的执行指导
        
        Args:
            model: 模型名称（用于判断是否需要注入模型特定指导）
        """
        guidance_parts = []
        
        # 1. 工具使用强制规范（所有模型都需要）
        from agent.context.prompt_templates import TOOL_USE_ENFORCEMENT, TOOL_CALL_FORMAT
        guidance_parts.append(TOOL_USE_ENFORCEMENT)
        guidance_parts.append(TOOL_CALL_FORMAT)
        
        # 2. 必须使用工具的场景列表
        from agent.context.prompt_templates import MANDATORY_TOOL_USE
        guidance_parts.append(MANDATORY_TOOL_USE)
        
        # 3. 行动而非询问
        from agent.context.prompt_templates import ACT_DONT_ASK
        guidance_parts.append(ACT_DONT_ASK)
        
        # 4. 记忆使用指导
        guidance_parts.append(MEMORY_GUIDANCE)
        
        # 5. 跨会话搜索指导
        guidance_parts.append(SESSION_SEARCH_GUIDANCE)
        
        # 6. 技能保存指导
        guidance_parts.append(SKILLS_GUIDANCE)
        
        # 7. 模型特定执行指导（按模型类型注入，参考 Hermes）
        if model:
            model_lower = model.lower()
            from agent.context.prompt_templates import OPENAI_MODEL_EXECUTION_GUIDANCE
            
            # DeepSeek/GPT 系列模型使用 OpenAI 执行指导
            if any(p in model_lower for p in ["deepseek", "gpt", "grok", "glm", "qwen"]):
                guidance_parts.append(OPENAI_MODEL_EXECUTION_GUIDANCE)
        
        return "\n\n".join(guidance_parts)

    def build_react_decision_prompt(
        self,
        task_description: str,
        conversation_history: Optional[List[Dict]] = None,
        todo_guide: Optional[str] = None,
        enable_memory_prefetch: bool = None
    ) -> str:
        """
        构建 ReAct 决策提示词（供 ReActLoop 使用）

        统一的决策提示词构建逻辑，替代原本分散在各处的硬编码拼接。

        Args:
            task_description: 当前任务描述
            conversation_history: 对话历史
            todo_guide: Todo 工具使用指南（可选）
            enable_memory_prefetch: 是否启用记忆预取（默认跟随类设置）

        Returns:
            完整的决策提示词
        """
        # 使用类设置或显式设置
        do_prefetch = (
            enable_memory_prefetch if enable_memory_prefetch is not None 
            else self.enable_memory_prefetch
        )
        
        # 加载基础定义（使用代码常量）
        identity = AGENT_IDENTITY
        capabilities = CAPABILITIES

        # 自动预取相关记忆（Hermes 风格）
        memory_context = ""
        if do_prefetch and task_description:
            memory_context = self._prefetch_memories(task_description)

        # 构建历史消息字符串
        history_msg_count = 0
        history_str = "(无历史记录)"
        if conversation_history:
            recent = conversation_history[-4:]
            history_msg_count = len(recent)
            history_lines = []
            for msg in recent:
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')[:200]
                history_lines.append(f"- {role}: {content}")
            history_str = "\n".join(history_lines) if history_lines else "(无历史记录)"

        # 构建工具列表
        tools_schema = ""
        if self.tools:
            tools_schema = json.dumps(self.get_tools_schema(), ensure_ascii=False, indent=2)

        # Todo 指南（如果没有提供，使用默认）
        if todo_guide is None:
            todo_guide = self._get_default_todo_guide()

        self.logger.info(
            f"Context Assembly: ReAct decision - "
            f"task={len(task_description)} chars, "
            f"history={history_msg_count} messages, "
            f"tools={len(self.tools)}, "
            f"memory_prefetch={len(memory_context)} chars"
        )

        return f"""{identity}

{capabilities}

## Current Task
{task_description}
{memory_context}

## Recent Conversation
{history_str}

## Available Tools
{tools_schema}

{todo_guide}

Please decide the next action based on the current task and conversation history.

Return JSON format:
{{
    "action": "use_tool" or "direct_response" or "ask_clarification",
    "tool_name": "tool_name" (only when action is use_tool),
    "parameters": {{}} (only when action is use_tool),
    "reasoning": "decision reason",
    "content": "response content" (only when action is direct_response),
    "questions": ["question1", "question2"] (only when action is ask_clarification)
}}

Respond with ONLY the JSON object, no other text."""

    def _get_default_todo_guide(self) -> str:
        """获取默认的 Todo 工具使用指南"""
        return """## Task Management Tools (use when task is complex)
- todo_create: Create task list when starting complex tasks
- todo_add: Add new task to list
- todo_complete: Mark task as complete
- todo_list: View current task list
- todo_cancel: Cancel task

## Rules
- If task requires 3+ steps, use todo_* tools to manage the task
- If multiple operations needed, complete them sequentially
- If encountering problems, try to solve first, ask user only if cannot resolve
- After completing task, provide concise summary"""


__all__ = ["ContextBuilder"]