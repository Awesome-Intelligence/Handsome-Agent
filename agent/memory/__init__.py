"""
Memory module for Handsome Agent

🧠 Decision - 💾 Memory

Provides:
- BaseMemoryProvider: Abstract base class for memory providers
- BuiltinMemoryProvider: Built-in provider using MemoryStore
- InMemoryProvider: In-memory provider for testing
- FileMemoryProvider: File-based JSON provider
- MemoryManager: Orchestrates multiple memory providers
- EnhancedMemorySystem: Multi-layered memory system
- MemoryItem: Memory data structure
"""

from .memory_provider import (
    BaseMemoryProvider,
    MemoryItem,
    BuiltinMemoryProvider,
    InMemoryProvider,
    FileMemoryProvider,
    ProviderBaseClass,
)
from .memory_manager import MemoryManager
from .memory_system import EnhancedMemorySystem
from .markdown_memory import MarkdownMemoryStore, MemoryCurator, MemoryEntry

__all__ = [
    # Base classes
    'BaseMemoryProvider',
    'ProviderBaseClass',
    'MemoryItem',
    # Providers
    'BuiltinMemoryProvider',
    'InMemoryProvider',
    'FileMemoryProvider',
    # Managers
    'MemoryManager',
    'EnhancedMemorySystem',
    # Stores
    'MarkdownMemoryStore',
    'MemoryCurator',
    'MemoryEntry',
]