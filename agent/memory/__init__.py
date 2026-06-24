"""
Memory module for Handsome Agent

🧠 Decision - 💾 Memory

Provides:
- MemoryStore: 持久化记忆存储
- MemoryProvider: Provider 抽象基类
- BuiltinMemoryProvider: 内置 Provider（真正的插件实现，参考 Hermes）
- MemoryManager: 记忆管理器（通过 BuiltinMemoryProvider 访问 MemoryStore）
- MemoryCurator: 自动记忆总结器（参考 Hermes curator 架构）
- StreamingContextScrubber: 流式输出清理器
- build_memory_context_block(): 记忆上下文块构建
- sanitize_context(): 上下文清理工具函数

架构说明 (v8.0.0+):
- 内置记忆通过 BuiltinMemoryProvider 处理
- MemoryStore 由 BuiltinMemoryProvider 持有
- MemoryManager 仅负责 Provider 编排
- 参考 Hermes Agent 的 Provider 插件化架构

快照机制 (v10.1.0+):
- 使用与 Hermes 一致的 _system_prompt_snapshot 设计
- load_from_disk() 时初始化快照
- freeze_snapshot() 更新快照
- format_for_system_prompt() 返回指定目标的格式化快照
- 移除了复杂的 _snapshot_dirty 脏标记机制

自动记忆总结 (v10.0.0+):
- MemoryCurator: 会话结束时自动总结用户偏好和环境信息
- 参考 Hermes 的 HonchoSessionManager 用户建模
- 支持配置触发条件和总结策略

Provider 禁用机制 (v9.2.0+):
- 通过 MemoryConfig.builtin_enabled 控制内置 Provider
- 通过 MemoryConfig.external_provider 配置外部 Provider
- 禁用后 has_tool("memory") 返回 False
- handle_tool_call() 禁用时返回明确错误

使用示例:
    # 禁用内置 Provider，使用外部 Provider
    config = MemoryConfig(
        builtin_enabled=False,
        external_provider="mem0"
    )
    manager = MemoryManager.from_config(config)
    
    # 使用自动记忆总结
    from agent.memory import MemoryCurator, curator_on_session_end
    curator = MemoryCurator()
    result = curator_on_session_end(session)
"""

from .memory_store import (
    MemoryStore,
    memory_tool,
    tool_error,
    MEMORY_SCHEMA,
    check_memory_requirements,
    get_memory_dir,
)
from .memory_provider import (
    # Base class (与 Hermes 一致)
    MemoryProvider,
    # Providers
    BuiltinMemoryProvider,
    # Streaming utilities
    ScrubberStats,
    StreamingContextScrubber,
    sanitize_context,
    build_memory_context_block,
)
from .memory_manager import MemoryManager
from .memory_curator import (
    MemoryCurator,
    CuratorConfig,
    curator_on_session_end,
    curator_on_message,
    get_default_curator,
    load_curator_state,
)

__all__ = [
    # MemoryStore
    'MemoryStore',
    'memory_tool',
    'tool_error',
    'MEMORY_SCHEMA',
    'check_memory_requirements',
    'get_memory_dir',
    # Base class (与 Hermes 一致)
    'MemoryProvider',
    # Providers
    'BuiltinMemoryProvider',
    # Streaming utilities
    'ScrubberStats',
    'StreamingContextScrubber',
    'sanitize_context',
    'build_memory_context_block',
    # Manager
    'MemoryManager',
    # Curator (自动记忆总结)
    'MemoryCurator',
    'CuratorConfig',
    'curator_on_session_end',
    'curator_on_message',
    'get_default_curator',
    'load_curator_state',
]
