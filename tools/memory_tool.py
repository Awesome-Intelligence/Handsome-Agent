#!/usr/bin/env python3
"""
Memory Tool Module

提供 Agent 记忆管理功能。
核心实现位于 agent.memory.memory_store，此模块仅用于工具注册。

Usage:
    from tools.memory_tool import register_memory_tool
"""

from agent.memory.memory_store import (
    MEMORY_SCHEMA,
    check_memory_requirements,
)

# 注册工具（保持向后兼容）
def register_memory_tool():
    """注册 memory 工具到工具注册表"""
    from tools.registry import registry
    from agent.memory.memory_store import memory_tool

    registry.register(
        name="memory",
        toolset="memory",
        schema=MEMORY_SCHEMA,
        handler=lambda args, **kw: memory_tool(
            action=args.get("action", ""),
            target=args.get("target", "memory"),
            content=args.get("content"),
            old_text=args.get("old_text"),
            store=kw.get("store"),
        ),
        check_fn=check_memory_requirements,
        emoji="🧠",
    )


# 延迟注册（模块导入时自动注册）
register_memory_tool()

# 导出供其他模块使用
__all__ = [
    'MEMORY_SCHEMA',
    'check_memory_requirements',
    'register_memory_tool',
]
