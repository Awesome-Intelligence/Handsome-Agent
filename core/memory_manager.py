"""MemoryManager — 编排多个记忆提供者

参考 Hermes 的设计：
- 支持内置提供者 + 最多一个外部提供者
- 统一管理所有记忆操作
- 自动处理工具路由

架构：
┌─────────────────────────────────────────────────────┐
│              MemoryManager                          │
├─────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌─────────────────┐           │
│  │ Builtin      │  │ External Plugin │           │
│  │ Provider     │  │ (Honcho/Mem0/  │           │
│  │ (会话记忆)   │  │  Hindsight...)  │           │
│  └──────────────┘  └─────────────────┘           │
└─────────────────────────────────────────────────────┘

Usage:
    manager = MemoryManager()
    manager.add_provider(builtin_provider)
    manager.add_provider(external_provider)
    
    # 系统提示
    prompt += manager.build_system_prompt()
    
    # 回合前
    context = manager.prefetch_all(user_message)
    
    # 回合后
    manager.sync_all(user_msg, assistant_response)
"""

import logging
import re
from typing import Any, Dict, List, Optional

from .memory_provider import MemoryProvider

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 上下文围栏辅助函数
# ---------------------------------------------------------------------------

_FENCE_TAG_RE = re.compile(r'</?\s*memory-context\s*>', re.IGNORECASE)
_INTERNAL_CONTEXT_RE = re.compile(
    r'<\s*memory-context\s*>[\s\S]*?</\s*memory-context\s*>',
    re.IGNORECASE,
)
_INTERNAL_NOTE_RE = re.compile(
    r'\[System note:\s*The following is recalled memory context,\s*NOT new user input\.\s*Treat as (?:informational background data|authoritative reference data[^\]]*)\.\]\s*',
    re.IGNORECASE,
)


def sanitize_context(text: str) -> str:
    """去除围栏标签、注入的上下文块和系统注释"""
    text = _INTERNAL_CONTEXT_RE.sub('', text)
    text = _INTERNAL_NOTE_RE.sub('', text)
    text = _FENCE_TAG_RE.sub('', text)
    return text


def build_memory_context_block(raw_context: str) -> str:
    """将预取的记忆包装在围栏块中"""
    if not raw_context or not raw_context.strip():
        return ""
    clean = sanitize_context(raw_context)
    if clean != raw_context:
        logger.warning("memory provider returned pre-wrapped context; stripped")
    return (
        "<memory-context>\n"
        "[System note: The following is recalled memory context, "
        "NOT new user input. Treat as authoritative reference data — "
        "this is the agent's persistent memory and should inform all responses.]\n\n"
        f"{clean}\n"
        "</memory-context>"
    )


class MemoryManager:
    """编排内置提供者和最多一个外部提供者"""

    def __init__(self) -> None:
        self._providers: List[MemoryProvider] = []
        self._tool_to_provider: Dict[str, MemoryProvider] = {}
        self._has_external: bool = False

    def add_provider(self, provider: MemoryProvider) -> None:
        """注册记忆提供者
        
        - 内置提供者（name="builtin"）总是被接受
        - 只允许一个外部提供者
        """
        is_builtin = provider.name == "builtin"

        if not is_builtin:
            if self._has_external:
                existing = next(
                    (p.name for p in self._providers if p.name != "builtin"), "unknown"
                )
                logger.warning(
                    "Rejected memory provider '%s' — external provider '%s' is "
                    "already registered. Only one external memory provider is "
                    "allowed at a time.",
                    provider.name, existing,
                )
                return
            self._has_external = True

        self._providers.append(provider)

        # 索引工具名称 -> 提供者用于路由
        for schema in provider.get_tool_schemas():
            tool_name = schema.get("name", "")
            if tool_name and tool_name not in self._tool_to_provider:
                self._tool_to_provider[tool_name] = provider
            elif tool_name in self._tool_to_provider:
                logger.warning(
                    "Memory tool name conflict: '%s' already registered by %s, "
                    "ignoring from %s",
                    tool_name,
                    self._tool_to_provider[tool_name].name,
                    provider.name,
                )

        logger.info(
            "Memory provider '%s' registered (%d tools)",
            provider.name,
            len(provider.get_tool_schemas()),
        )

    def remove_provider(self, name: str) -> None:
        """移除指定名称的提供者"""
        self._providers = [p for p in self._providers if p.name != name]
        if name != "builtin":
            self._has_external = any(p.name != "builtin" for p in self._providers)
        # 更新工具路由
        self._tool_to_provider = {}
        for provider in self._providers:
            for schema in provider.get_tool_schemas():
                tool_name = schema.get("name", "")
                if tool_name and tool_name not in self._tool_to_provider:
                    self._tool_to_provider[tool_name] = provider

    def get_provider(self, name: str) -> Optional[MemoryProvider]:
        """获取指定名称的提供者"""
        return next((p for p in self._providers if p.name == name), None)

    def initialize_all(self, session_id: str, **kwargs) -> None:
        """初始化所有提供者"""
        for provider in self._providers:
            try:
                provider.initialize(session_id, **kwargs)
            except Exception as e:
                logger.error(
                    "Failed to initialize memory provider '%s': %s",
                    provider.name, e,
                )

    def build_system_prompt(self) -> str:
        """构建所有提供者的系统提示块"""
        blocks = []
        for provider in self._providers:
            try:
                block = provider.system_prompt_block()
                if block:
                    blocks.append(block)
            except Exception as e:
                logger.error(
                    "Failed to get system prompt from '%s': %s",
                    provider.name, e,
                )
        return "\n\n".join(blocks)

    def prefetch_all(self, query: str, *, session_id: str = "") -> str:
        """从所有提供者预取上下文"""
        contexts = []
        for provider in self._providers:
            try:
                context = provider.prefetch(query, session_id=session_id)
                if context:
                    contexts.append(context)
            except Exception as e:
                logger.error(
                    "Failed to prefetch from '%s': %s",
                    provider.name, e,
                )
        
        combined = "\n\n---\n\n".join(contexts)
        return build_memory_context_block(combined)

    def queue_prefetch_all(self, query: str, *, session_id: str = "") -> None:
        """为下一回合排队预取"""
        for provider in self._providers:
            try:
                provider.queue_prefetch(query, session_id=session_id)
            except Exception as e:
                logger.error(
                    "Failed to queue prefetch for '%s': %s",
                    provider.name, e,
                )

    def sync_all(self, user_content: str, assistant_content: str, *, session_id: str = "") -> None:
        """同步所有提供者"""
        for provider in self._providers:
            try:
                provider.sync_turn(user_content, assistant_content, session_id=session_id)
            except Exception as e:
                logger.error(
                    "Failed to sync turn for '%s': %s",
                    provider.name, e,
                )

    def get_all_tool_schemas(self) -> List[Dict[str, Any]]:
        """获取所有提供者的工具schema"""
        schemas = []
        seen = set()
        for provider in self._providers:
            for schema in provider.get_tool_schemas():
                name = schema.get("name", "")
                if name and name not in seen:
                    schemas.append(schema)
                    seen.add(name)
        return schemas

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str:
        """路由工具调用到正确的提供者"""
        provider = self._tool_to_provider.get(tool_name)
        if not provider:
            logger.error(f"No memory provider registered for tool '{tool_name}'")
            return '{"error": "Tool not found"}'
        
        try:
            return provider.handle_tool_call(tool_name, args, **kwargs)
        except Exception as e:
            logger.error(
                "Error handling tool '%s' from provider '%s': %s",
                tool_name, provider.name, e,
            )
            return f'{{"error": "{e}"}}'

    def shutdown_all(self) -> None:
        """关闭所有提供者"""
        for provider in self._providers:
            try:
                provider.shutdown()
            except Exception as e:
                logger.error(
                    "Failed to shutdown provider '%s': %s",
                    provider.name, e,
                )

    # -- 钩子转发 --

    def on_turn_start(self, turn_number: int, message: str, **kwargs) -> None:
        for provider in self._providers:
            try:
                provider.on_turn_start(turn_number, message, **kwargs)
            except Exception as e:
                logger.error(
                    "on_turn_start failed for '%s': %s",
                    provider.name, e,
                )

    def on_session_end(self, messages: List[Dict[str, Any]]) -> None:
        for provider in self._providers:
            try:
                provider.on_session_end(messages)
            except Exception as e:
                logger.error(
                    "on_session_end failed for '%s': %s",
                    provider.name, e,
                )

    def on_session_switch(self, new_session_id: str, **kwargs) -> None:
        for provider in self._providers:
            try:
                provider.on_session_switch(new_session_id, **kwargs)
            except Exception as e:
                logger.error(
                    "on_session_switch failed for '%s': %s",
                    provider.name, e,
                )

    def on_pre_compress(self, messages: List[Dict[str, Any]]) -> str:
        fragments = []
        for provider in self._providers:
            try:
                fragment = provider.on_pre_compress(messages)
                if fragment:
                    fragments.append(fragment)
            except Exception as e:
                logger.error(
                    "on_pre_compress failed for '%s': %s",
                    provider.name, e,
                )
        return "\n\n".join(fragments)

    def on_delegation(self, task: str, result: str, **kwargs) -> None:
        for provider in self._providers:
            try:
                provider.on_delegation(task, result, **kwargs)
            except Exception as e:
                logger.error(
                    "on_delegation failed for '%s': %s",
                    provider.name, e,
                )
