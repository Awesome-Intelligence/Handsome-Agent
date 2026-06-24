#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example Memory Provider Plugin - 示例记忆 Provider 插件

这个插件展示如何创建外部记忆 Provider。

功能：
- 简单的内存存储（不持久化）
- 自动同步对话
- 关键词检索

Usage:
    from plugins.memory import load_memory_provider
    
    provider = load_memory_provider("example")
    provider.initialize("session-123")
    provider.sync_turn("Hello", "Hi there!")
"""

from typing import Dict, List, Optional, Any
from pathlib import Path

from agent.memory.memory_provider import MemoryProvider, MemoryItem


class ExampleMemoryProvider(MemoryProvider):
    """
    示例记忆 Provider - 展示 Provider 插件开发。
    
    这是一个简单的内存存储 Provider，用于演示插件系统。
    实际使用时应该使用 honcho, mem0, hindsight 等更强大的 Provider。
    
    特性：
    - 内存存储（不持久化，重启后丢失）
    - 自动同步对话
    - 关键词检索
    """
    
    def __init__(self):
        self._session_id: Optional[str] = None
        self._entries: List[str] = []
        self._prefetch_cache: str = ""
    
    @property
    def name(self) -> str:
        return "example"
    
    def is_available(self) -> bool:
        """始终可用（无外部依赖）"""
        return True
    
    def initialize(self, session_id: str, **kwargs) -> None:
        """初始化 Provider"""
        self._session_id = session_id
        self._entries = []
        self._prefetch_cache = ""
    
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """返回工具 schema（无额外工具）"""
        return []
    
    def system_prompt_block(self) -> str:
        """返回格式化的记忆块"""
        if not self._entries:
            return ""
        
        lines = ["[Example Memory]"]
        for entry in self._entries[:5]:
            lines.append(f"- {entry[:100]}")
        return "\n".join(lines)
    
    def prefetch(self, query: str, *, session_id: str = "") -> str:
        """预取相关记忆"""
        if not query or not self._entries:
            return ""
        
        # 简单关键词匹配
        query_lower = query.lower()
        relevant = [
            e for e in self._entries
            if query_lower in e.lower()
        ][:3]
        
        if not relevant:
            return ""
        
        return "<memory_context>\n- " + "\n- ".join(r[:100] for r in relevant) + "\n</memory_context>"
    
    def sync_turn(self, user_content: str, assistant_content: str, *, session_id: str = "") -> None:
        """
        自动同步对话到记忆。
        
        简化实现：将用户消息添加到记忆。
        """
        # 提取关键词（简化实现）
        words = user_content.split()[:5]
        if words:
            self._entries.append(" ".join(words))
    
    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str:
        """处理工具调用（示例 Provider 不支持工具）"""
        return '{"success": false, "error": "Example provider does not support tools"}'
    
    def on_pre_compress(self, messages: List[Dict[str, Any]]) -> str:
        """压缩前提取洞察"""
        if not messages:
            return ""
        
        # 简单实现：提取最后的用户消息
        insights = []
        for msg in reversed(messages[-5:]):
            if msg.get("role") == "user":
                content = msg.get("content", "")[:100]
                if len(content) > 20:
                    insights.append(content)
        
        if insights:
            return "<memory_insights>\n- " + "\n- ".join(insights[:3]) + "\n</memory_insights>"
        return ""
    
    def on_session_end(self, messages: List[Dict[str, Any]]) -> None:
        """会话结束时清理"""
        self._entries = []
        self._session_id = None
    
    def shutdown(self) -> None:
        """关闭 Provider"""
        self._entries = []
        self._session_id = None
    
    def get_config_schema(self) -> List[Dict[str, Any]]:
        """
        返回配置 schema（示例 Provider 不需要配置）。
        
        返回空列表表示不需要配置。
        """
        return []


# ============================================================================
# Plugin Registration (插件注册入口点)
# ============================================================================

def register(ctx: "PluginContext") -> None:
    """
    注册 ExampleMemoryProvider 插件。
    
    这是插件的入口点，由插件系统调用。
    """
    ctx.register_memory_provider(ExampleMemoryProvider())


# ============================================================================
# CLI Commands (可选 - CLI 命令)
# ============================================================================

def register_cli() -> Optional[Dict]:
    """
    注册 CLI 命令（可选）。
    
    如果插件需要 CLI 命令，实现此函数。
    """
    return None  # 示例 Provider 不需要 CLI 命令
