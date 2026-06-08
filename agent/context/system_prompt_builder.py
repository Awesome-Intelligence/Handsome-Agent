#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System Prompt Builder - Hermes 风格的三层系统提示架构

将系统提示分为三层，优化缓存和构建效率：
1. Stable Layer (稳定层) - 会话级缓存，最大化 API Provider 前缀缓存
2. Context Layer (上下文层) - 依赖 cwd，可能变化
3. Volatile Layer (变动层) - 每次请求都变化

参考 Hermes 的 system_prompt.py 实现。

日志子层：💾 Context
"""

import json
import hashlib
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field

from common.logging_manager import get_decision_logger
from agent.workspace import get_workspace_manager
from agent.context.prompt_templates import (
    AGENT_IDENTITY,
    CAPABILITIES,
    MEMORY_GUIDANCE,
    SESSION_SEARCH_GUIDANCE,
    SKILLS_GUIDANCE,
    TOOL_USAGE_GUIDANCE,
    TOOL_USE_ENFORCEMENT,
    TOOL_CALL_FORMAT,
    MANDATORY_TOOL_USE,
    ACT_DONT_ASK,
    DEFAULT_USER_PROFILE,
    OPENAI_MODEL_EXECUTION_GUIDANCE,
)

if True:
    from tools.memory_tool import MemoryStore


@dataclass
class LayerResult:
    """分层构建结果"""
    stable: str = ""           # 稳定层
    context: str = ""          # 上下文层
    volatile: str = ""        # 变动层
    full_prompt: str = ""      # 完整提示词
    cache_hit: bool = False    # 是否命中缓存
    cache_key: str = ""       # 缓存键


class SystemPromptBuilder:
    """
    三层系统提示构建器 - Hermes 风格
    
    架构设计：
    ┌─────────────────────────────────────────────────────────────┐
    │ Layer 1: STABLE (稳定层)                                   │
    │  - Agent 身份定义                                          │
    │  - 能力摘要                                               │
    │  - 工具使用指导                                           │
    │  📌 特点：会话期间不变，每个会话构建一次并缓存            │
    │  📌 作用：最大化 API Provider 的前缀缓存命中             │
    ├─────────────────────────────────────────────────────────────┤
    │ Layer 2: CONTEXT (上下文层)                                │
    │  - 用户画像 (USER.md)                                     │
    │  - 工具列表                                              │
    │  📌 特点：依赖配置，可能变化                             │
    ├─────────────────────────────────────────────────────────────┤
    │ Layer 3: VOLATILE (变动层)                                │
    │  - 记忆预取                                              │
    │  - 对话历史摘要                                           │
    │  📌 特点：每次请求都变化，永不缓存                       │
    └─────────────────────────────────────────────────────────────┘
    
    日志子层：💾 Context
    """
    
    def __init__(
        self,
        tools: Optional[Dict[str, Any]] = None,
        enable_guidance: bool = True,
        enable_memory_prefetch: bool = True,
        session_id: str = None
    ):
        """
        Args:
            tools: 工具字典 {name: ToolDefinition}
            enable_guidance: 是否添加工具使用指导
            enable_memory_prefetch: 是否启用记忆预取
            session_id: 会话 ID（用于缓存管理）
        """
        self.logger = get_decision_logger(self.__class__.__name__, sublayer="context")
        self.tools = tools or {}
        self.enable_guidance = enable_guidance
        self.enable_memory_prefetch = enable_memory_prefetch
        self.session_id = session_id or "default"
        
        # 延迟加载 MemoryStore
        self._memory_store: Optional["MemoryStore"] = None
        
        # 缓存
        self._stable_cache: Optional[str] = None
        self._stable_cache_key: str = ""
        self._user_profile_cache: Optional[str] = None
        self._user_profile_cache_key: str = ""
        
        self.logger.debug(
            f"SystemPromptBuilder initialized (session={self.session_id}, "
            f"memory_prefetch={enable_memory_prefetch})"
        )
    
    @property
    def memory_store(self) -> "MemoryStore":
        """懒加载 MemoryStore"""
        if self._memory_store is None:
            from tools.memory_tool import MemoryStore
            self._memory_store = MemoryStore()
            self._memory_store.load_from_disk()
        return self._memory_store
    
    def set_tools(self, tools: Dict[str, Any]) -> None:
        """设置工具字典"""
        self.tools = tools
        # 工具变化时使上下文层缓存失效
        self._invalidate_context_cache()
        self.logger.debug(f"Tools updated: {len(tools)} tools")
    
    def _invalidate_stable_cache(self) -> None:
        """使稳定层缓存失效"""
        self._stable_cache = None
        self._stable_cache_key = ""
        self.logger.debug("Stable layer cache invalidated")
    
    def _invalidate_context_cache(self) -> None:
        """使上下文层缓存失效"""
        # 用户画像缓存不常失效，只在文件变化时失效
        self.logger.debug("Context layer marked for recheck")
    
    def _make_tools_cache_key(self) -> str:
        """生成工具列表的缓存键"""
        if not self.tools:
            return "no_tools"
        
        # 按工具名排序后生成哈希
        tool_names = sorted(self.tools.keys())
        content = "|".join(tool_names)
        return hashlib.md5(content.encode()).hexdigest()[:8]
    
    # ==================== Stable Layer ====================
    
    def _build_stable_layer(self) -> str:
        """
        构建稳定层（会话级缓存）
        
        包含：Agent 身份、能力摘要、工具使用指导（不含工具列表）
        """
        parts = []
        
        # 1. Agent 身份定义
        parts.append(AGENT_IDENTITY)
        
        # 2. 能力摘要
        parts.append(CAPABILITIES)
        
        # 3. 工具使用指导（不含工具列表和 volatile 内容）
        guidance_parts = []
        
        # 3.1 工具使用强制规范
        guidance_parts.append(TOOL_USE_ENFORCEMENT)
        guidance_parts.append(TOOL_CALL_FORMAT)
        
        # 3.2 必须使用工具的场景
        guidance_parts.append(MANDATORY_TOOL_USE)
        
        # 3.3 行动而非询问
        guidance_parts.append(ACT_DONT_ASK)
        
        # 3.4 记忆使用指导
        guidance_parts.append(MEMORY_GUIDANCE)
        
        # 3.5 跨会话搜索指导
        guidance_parts.append(SESSION_SEARCH_GUIDANCE)
        
        # 3.6 技能保存指导
        guidance_parts.append(SKILLS_GUIDANCE)
        
        parts.append("\n\n".join(guidance_parts))
        
        return "\n\n".join(parts)
    
    def get_stable_layer(self) -> str:
        """
        获取稳定层（带缓存）
        
        稳定层在会话期间不会变化，使用缓存优化。
        """
        cache_key = "stable_v1"  # 版本化的缓存键
        
        if self._stable_cache is not None and self._stable_cache_key == cache_key:
            self.logger.debug("Stable layer: cache hit")
            return self._stable_cache
        
        self.logger.debug("Stable layer: cache miss, building...")
        self._stable_cache = self._build_stable_layer()
        self._stable_cache_key = cache_key
        
        self.logger.info(
            f"Stable layer built: {len(self._stable_cache)} chars"
        )
        
        return self._stable_cache
    
    # ==================== Context Layer ====================
    
    def _build_context_layer(
        self,
        include_tools: bool = True,
        model: str = None
    ) -> str:
        """
        构建上下文层
        
        包含：用户画像、工具列表
        """
        parts = []
        
        # 1. 用户画像（从 USER.md 或默认模板）
        parts.append(self._get_user_profile())
        
        # 2. 工具列表
        if include_tools and self.tools:
            tools_schema = self._build_tools_schema_json()
            parts.append(f"Available tools:\n{tools_schema}")
            parts.append(TOOL_USAGE_GUIDANCE)
        
        # 3. 模型特定指导（DeepSeek/GPT 系列）
        if model:
            model_lower = model.lower()
            if any(p in model_lower for p in ["deepseek", "gpt", "grok", "glm", "qwen"]):
                parts.append(OPENAI_MODEL_EXECUTION_GUIDANCE)
        
        return "\n\n".join(parts)
    
    def _get_user_profile(self) -> str:
        """
        获取用户画像
        
        优先从 USER.md 加载，失败时使用默认模板。
        """
        # 检查缓存
        try:
            from pathlib import Path
            workspace_dir = Path.home() / ".handsome_agent" / "memories"
            user_file = workspace_dir / "USER.md"
            
            if user_file.exists():
                mtime = user_file.stat().st_mtime
                cache_key = f"user_profile_{mtime}"
                
                if self._user_profile_cache is not None and self._user_profile_cache_key == cache_key:
                    return self._user_profile_cache
                
                with open(user_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if content.strip():
                    self._user_profile_cache = f"## 👤 User Profile\n\n{content}"
                    self._user_profile_cache_key = cache_key
                    return self._user_profile_cache
        except Exception as e:
            self.logger.debug(f"User profile file read failed: {e}")
        
        return DEFAULT_USER_PROFILE
    
    def _build_tools_schema_json(self) -> str:
        """构建工具 Schema JSON 字符串"""
        schema = []
        for tool_name, tool in self.tools.items():
            name = tool.name if hasattr(tool, 'name') else tool_name
            desc = tool.description if hasattr(tool, 'description') else ''
            params = getattr(tool, 'parameters', {})
            
            # 提取 properties
            param_props = {}
            if isinstance(params, dict):
                if 'properties' in params:
                    param_props = params['properties']
                elif 'type' not in params:
                    param_props = params
            
            schema.append({
                'name': name,
                'description': desc,
                'parameters': {
                    'type': 'object',
                    'properties': param_props,
                    'required': []
                }
            })
        
        return json.dumps(schema, ensure_ascii=False, indent=2)
    
    def _build_tools_schema_list(self) -> List[Dict]:
        """构建工具 Schema 列表（用于 LLM）"""
        schema = []
        for tool_name, tool in self.tools.items():
            name = tool.name if hasattr(tool, 'name') else tool_name
            desc = tool.description if hasattr(tool, 'description') else ''
            params = getattr(tool, 'parameters', {})
            
            # 提取 properties
            param_props = {}
            if isinstance(params, dict):
                if 'properties' in params:
                    param_props = params['properties']
                elif 'type' not in params:
                    param_props = params
            
            schema.append({
                'name': name,
                'description': desc,
                'parameters': {
                    'type': 'object',
                    'properties': param_props,
                    'required': []
                }
            })
        
        return schema
    
    # ==================== Volatile Layer ====================
    
    def _build_volatile_layer(
        self,
        user_message: str = "",
        conversation_history: Optional[List[Dict]] = None
    ) -> str:
        """
        构建变动层（永不缓存）
        
        包含：记忆预取、对话历史摘要
        """
        parts = []
        
        # 1. 记忆预取
        if self.enable_memory_prefetch and user_message:
            memory_context = self._prefetch_memories(user_message)
            if memory_context:
                parts.append(memory_context)
        
        # 2. 对话历史摘要
        if conversation_history:
            history_context = self._format_history_summary(conversation_history)
            if history_context:
                parts.append(history_context)
        
        return "\n\n".join(parts) if parts else ""
    
    def _prefetch_memories(self, query: str) -> str:
        """预取与查询相关的记忆"""
        try:
            memory_entries = self.memory_store.read("memory")
            user_entries = self.memory_store.read("user")
            
            all_entries = [
                *memory_entries.get("entries", []),
                *user_entries.get("entries", [])
            ]
            
            if not all_entries:
                return ""
            
            # 简单匹配：查询词出现在记忆中的条目
            relevant = []
            query_lower = query.lower()
            
            for entry in all_entries:
                entry_lower = entry.lower()
                if query_lower in entry_lower:
                    relevant.append(entry)
                else:
                    # 字符重叠匹配
                    query_chars = set(query_lower) - set('，。！？、：；')
                    entry_chars = set(entry_lower) - set('，。！？、：；')
                    if query_chars and entry_chars:
                        overlap = len(query_chars & entry_chars) / len(query_chars)
                        if overlap >= 0.3:
                            relevant.append(entry)
            
            if not relevant:
                return ""
            
            # 格式化为记忆块
            content = "\n".join(f"- {entry}" for entry in relevant[:5])
            return f"""<memory-context>
[System note: The following is recalled memory context. Treat as authoritative reference data.]

{content}
</memory-context>"""
        
        except Exception as e:
            self.logger.debug(f"Memory prefetch failed: {e}")
            return ""
    
    def _format_history_summary(self, conversation_history: List[Dict]) -> str:
        """格式化对话历史摘要"""
        if not conversation_history:
            return ""
        
        # 只取最近 6 条，每条截取 200 字符
        recent = conversation_history[-6:]
        lines = []
        
        for msg in recent:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')[:200]
            lines.append(f"- {role}: {content}")
        
        return f"## Recent Conversation\n\n" + "\n".join(lines)
    
    # ==================== 统一构建 ====================
    
    def build(
        self,
        user_message: str = "",
        conversation_history: Optional[List[Dict]] = None,
        include_tools: bool = True,
        model: str = None
    ) -> LayerResult:
        """
        构建完整的系统提示词（三层架构）
        
        Args:
            user_message: 用户消息（用于记忆预取）
            conversation_history: 对话历史
            include_tools: 是否包含工具列表
            model: 模型名称
            
        Returns:
            LayerResult: 包含各层内容和完整提示词
        """
        # 1. 获取稳定层（缓存）
        stable = self.get_stable_layer()
        
        # 2. 构建上下文层
        context = self._build_context_layer(include_tools=include_tools, model=model)
        
        # 3. 构建变动层
        volatile = self._build_volatile_layer(
            user_message=user_message,
            conversation_history=conversation_history
        )
        
        # 4. 组装完整提示词
        parts = [stable]
        if context:
            parts.append(context)
        if volatile:
            parts.append(volatile)
        
        full_prompt = "\n\n".join(parts)
        
        # 计算缓存键
        cache_key = self._make_tools_cache_key()
        
        result = LayerResult(
            stable=stable,
            context=context,
            volatile=volatile,
            full_prompt=full_prompt,
            cache_hit=self._stable_cache is not None,
            cache_key=cache_key
        )
        
        self.logger.info(
            f"System prompt built: "
            f"stable={len(stable)} chars, "
            f"context={len(context)} chars, "
            f"volatile={len(volatile)} chars, "
            f"total={len(full_prompt)} chars"
        )
        
        return result
    
    def invalidate_all_caches(self) -> None:
        """使所有缓存失效"""
        self._stable_cache = None
        self._stable_cache_key = ""
        self._user_profile_cache = None
        self._user_profile_cache_key = ""
        self.logger.debug("All caches invalidated")


__all__ = ["SystemPromptBuilder", "LayerResult"]
