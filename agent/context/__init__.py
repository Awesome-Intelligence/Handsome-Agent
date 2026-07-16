"""
Context module for Agent-Z

🧠 Decision - 📊 Context

模块架构：
- ContextEngine: 抽象基类，定义压缩引擎接口（与 Hermes 兼容）
- ContextCompressor: 内置压缩实现
- ContextBuilder: 上下文构建器（三层架构）
- ContextManager: 协调器，统一上下文构建入口
"""

from .context_builder import ContextBuilder
from .context_manager import ContextManager, ContextPurpose, BuildPartsResult, BuildMessagesResult
from .context_engine import ContextEngine
from .context_compressor import ContextCompressor

__all__ = [
    # 核心组件
    'ContextEngine',
    'ContextCompressor',
    'ContextBuilder',
    'ContextManager',
    # 枚举和类型
    'ContextPurpose',
    'BuildPartsResult',
    'BuildMessagesResult',
]
