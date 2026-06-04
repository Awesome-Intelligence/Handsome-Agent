#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory Provider Module - Inspired by Hermes Agent

This module defines the abstract interface for memory providers
and provides basic implementations.

Memory providers handle persistent storage and retrieval of agent memories
across sessions with a complete lifecycle interface:
- initialize() - Session initialization
- system_prompt_block() - Static text for system prompt
- prefetch() - Background recall before each turn
- sync_turn() - Persist completed turn
- on_pre_compress() - Extract before context compression
- on_session_switch() - Handle session ID rotation
- shutdown() - Clean exit
"""

from typing import List, Dict, Optional, Any, TYPE_CHECKING
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import json
import os
import time

from common.logging_manager import get_decision_logger

if TYPE_CHECKING:
    from tools.memory_tool import MemoryStore

logger = get_decision_logger("MemoryProvider")


@dataclass
class MemoryItem:
    """Represents a single memory item."""
    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0
    relevance_score: float = 0.0


class BaseMemoryProvider(ABC):
    """
    Abstract base class for memory providers.
    
    Memory providers handle persistent storage and retrieval
    of agent memories across sessions with a complete lifecycle.
    
    Lifecycle Methods:
    1. is_available() - Check if provider is ready
    2. initialize() - Initialize for a session
    3. system_prompt_block() - Return static text for system prompt
    4. prefetch() - Recall relevant context before each turn
    5. sync_turn() - Persist completed turn
    6. on_pre_compress() - Extract before context compression
    7. on_session_switch() - Handle session ID rotation
    8. shutdown() - Clean exit
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier for this provider (e.g. 'builtin', 'file', 'vector')."""
        return "base"
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Return True if this provider is configured and ready.
        
        Should not make network calls — just check config and installed deps.
        """
        return True
    
    def initialize(self, session_id: str, **kwargs) -> None:
        """
        Initialize for a session.
        
        Called once at agent startup. May create resources,
        establish connections, start background threads, etc.
        
        Args:
            session_id: The current session ID
            **kwargs: Additional context (hermes_home, platform, etc.)
        """
        pass
    
    def system_prompt_block(self) -> str:
        """
        Return text to include in the system prompt.
        
        Called during system prompt assembly. Return empty string to skip.
        This is for STATIC provider info (instructions, status).
        Prefetched recall context is injected separately via prefetch().
        """
        return ""
    
    def prefetch(self, query: str, session_id: str = "") -> str:
        """
        Recall relevant context for the upcoming turn.
        
        Called before each API call. Return formatted text to inject as
        context, or empty string if nothing relevant.
        
        Args:
            query: The user's message or task description
            session_id: The current session ID
            
        Returns:
            Formatted context string, or empty string if nothing relevant
        """
        return ""
    
    def queue_prefetch(self, query: str, session_id: str = "") -> None:
        """
        Queue a background recall for the NEXT turn.
        
        Called after each turn completes. The result will be consumed
        by prefetch() on the next turn. Default is no-op.
        """
        pass
    
    def sync_turn(self, user_content: str, assistant_content: str, session_id: str = "") -> None:
        """
        Persist a completed turn to the backend.
        
        Called after each turn. Should be non-blocking — queue for
        background processing if the backend has latency.
        
        Args:
            user_content: The user's message
            assistant_content: The assistant's response
            session_id: The current session ID
        """
        pass
    
    # -- Core storage operations (implement these) -------------------------
    
    @abstractmethod
    async def store(self, session_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Store a memory item.
        
        Args:
            session_id: The session ID
            content: The memory content
            metadata: Optional metadata dictionary
        
        Returns:
            The ID of the stored memory
        """
        pass
    
    @abstractmethod
    async def retrieve(self, session_id: str, query: str, limit: int = 5) -> List[MemoryItem]:
        """
        Retrieve memories related to a query.
        
        Args:
            session_id: The session ID
            query: The search query
            limit: Maximum number of results to return
        
        Returns:
            List of matching memory items sorted by relevance
        """
        pass
    
    @abstractmethod
    async def get_all(self, session_id: str) -> List[MemoryItem]:
        """
        Get all memories for a session.
        
        Args:
            session_id: The session ID
        
        Returns:
            List of all memory items for the session
        """
        pass
    
    @abstractmethod
    async def delete(self, session_id: str, memory_id: str) -> bool:
        """
        Delete a specific memory.
        
        Args:
            session_id: The session ID
            memory_id: The memory ID to delete
        
        Returns:
            True if deletion was successful
        """
        pass
    
    @abstractmethod
    async def clear(self, session_id: str):
        """
        Clear all memories for a session.
        
        Args:
            session_id: The session ID
        """
        pass
    
    # -- Optional lifecycle hooks (override to opt in) --------------------
    
    def on_turn_start(self, turn_number: int, message: str, **kwargs) -> None:
        """
        Called at the start of each turn with the user message.
        
        Args:
            turn_number: The current turn number
            message: The user's message
            **kwargs: Additional context (remaining_tokens, model, etc.)
        """
        pass
    
    def on_session_end(self, messages: List[Dict[str, Any]]) -> None:
        """
        Called when a session ends (explicit exit or timeout).
        
        Args:
            messages: The full conversation history
        """
        pass
    
    def on_session_switch(
        self,
        new_session_id: str,
        parent_session_id: str = "",
        reset: bool = False,
        **kwargs
    ) -> None:
        """
        Called when the agent switches session_id mid-process.
        
        Fires on /resume, /branch, /reset, /new and context compression.
        
        Args:
            new_session_id: The session_id the agent just switched to
            parent_session_id: The previous session_id (for lineage tracking)
            reset: True for genuinely new conversation
        """
        pass
    
    def on_pre_compress(self, messages: List[Dict[str, Any]]) -> str:
        """
        Called before context compression discards old messages.
        
        Use to extract insights from messages about to be compressed.
        
        Args:
            messages: The list of messages that will be summarized/discarded
            
        Returns:
            Text to include in the compression summary prompt
        """
        return ""
    
    def on_memory_write(
        self,
        action: str,
        target: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Called when the built-in memory tool writes an entry.
        
        Args:
            action: 'add', 'replace', or 'remove'
            target: 'memory' or 'user'
            content: The entry content
            metadata: Structured provenance for the write
        """
        pass
    
    def on_delegation(
        self,
        task: str,
        result: str,
        child_session_id: str = "",
        **kwargs
    ) -> None:
        """
        Called on the PARENT agent when a subagent completes.
        
        Args:
            task: The delegation prompt
            result: The subagent's final response
            child_session_id: The subagent's session_id
        """
        pass
    
    def shutdown(self) -> None:
        """Clean shutdown — flush queues, close connections."""
        pass


class BuiltinMemoryProvider(BaseMemoryProvider):
    """
    Built-in memory provider using MemoryStore.
    
    Integrates with tools/memory_tool.py's MemoryStore for:
    - MEMORY.md: agent's personal notes
    - USER.md: user profile information
    """
    
    def __init__(self, memory_store: "MemoryStore" = None):
        self._memory_store = memory_store
        self._session_id = ""
        self.logger = get_decision_logger(self.__class__.__name__)
    
    @property
    def name(self) -> str:
        return "builtin"
    
    @property
    def memory_store(self) -> "MemoryStore":
        """Lazy load MemoryStore to avoid circular import."""
        if self._memory_store is None:
            try:
                from tools.memory_tool import MemoryStore
                self._memory_store = MemoryStore()
                self._memory_store.load_from_disk()
            except Exception as e:
                self.logger.warning(f"Failed to load MemoryStore: {e}")
        return self._memory_store
    
    def is_available(self) -> bool:
        """Builtin provider is always available."""
        return True
    
    def initialize(self, session_id: str, **kwargs) -> None:
        """Initialize the memory store."""
        self._session_id = session_id
        try:
            if self._memory_store is None:
                from tools.memory_tool import MemoryStore
                self._memory_store = MemoryStore()
                self._memory_store.load_from_disk()
            self.logger.info(f"Initialized BuiltinMemoryProvider for session {session_id}")
        except Exception as e:
            self.logger.error(f"Failed to initialize: {e}")
    
    def system_prompt_block(self) -> str:
        """Return formatted memory blocks for system prompt."""
        blocks = []
        
        # Memory block
        memory_block = self.memory_store.format_for_system_prompt("memory")
        if memory_block:
            blocks.append(memory_block)
        
        # User profile block
        user_block = self.memory_store.format_for_system_prompt("user")
        if user_block:
            blocks.append(user_block)
        
        return "\n\n".join(blocks) if blocks else ""
    
    def prefetch(self, query: str, session_id: str = "") -> str:
        """
        Prefetch relevant memories based on query.
        
        Returns memories that match keywords in the query.
        """
        try:
            # Get relevant entries by reading all and filtering
            result = self.memory_store.read("memory")
            entries = result.get("entries", [])
            
            if not entries:
                return ""
            
            # Simple keyword matching
            query_lower = query.lower()
            relevant = []
            
            for entry in entries:
                # Check if any significant word from query appears in entry
                query_words = [w for w in query_lower.split() if len(w) > 2]
                entry_lower = entry.lower()
                
                matches = sum(1 for w in query_words if w in entry_lower)
                if matches >= 1:
                    relevant.append(entry)
            
            if not relevant:
                return ""
            
            # Format as context block
            context = "\n".join(f"- {e}" for e in relevant[:5])
            return f"<relevant_memory>\n{context}\n</relevant_memory>"
            
        except Exception as e:
            self.logger.warning(f"Prefetch failed: {e}")
            return ""
    
    def sync_turn(self, user_content: str, assistant_content: str, session_id: str = "") -> None:
        """
        Sync a completed turn.
        
        Builtin provider doesn't auto-sync — relies on explicit memory writes.
        """
        pass
    
    async def store(self, session_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store a memory item."""
        memory_id = f"mem_{int(time.time() * 1000)}"
        return memory_id
    
    async def retrieve(self, session_id: str, query: str, limit: int = 5) -> List[MemoryItem]:
        """Retrieve memories by keyword matching."""
        items = []
        
        try:
            result = self.memory_store.read("memory")
            entries = result.get("entries", [])
            
            query_lower = query.lower()
            for entry in entries:
                if query_lower in entry.lower():
                    items.append(MemoryItem(
                        id=f"mem_{len(items)}",
                        content=entry,
                        relevance_score=0.8
                    ))
            
            return items[:limit]
        except Exception:
            return items
    
    async def get_all(self, session_id: str) -> List[MemoryItem]:
        """Get all memories."""
        items = []
        
        try:
            result = self.memory_store.read("memory")
            entries = result.get("entries", [])
            
            for i, entry in enumerate(entries):
                items.append(MemoryItem(
                    id=f"mem_{i}",
                    content=entry,
                    timestamp=0.0
                ))
        except Exception:
            pass
        
        return items
    
    async def delete(self, session_id: str, memory_id: str) -> bool:
        """Delete not supported for built-in provider via this interface."""
        return False
    
    async def clear(self, session_id: str):
        """Clear not supported for built-in provider."""
        pass
    
    def on_memory_write(
        self,
        action: str,
        target: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Mirror built-in memory writes for external providers.
        """
        self.logger.debug(f"Memory write: {action} on {target}")


class InMemoryProvider(BaseMemoryProvider):
    """
    In-memory memory provider for testing and development.
    Not persistent across agent restarts.
    """
    
    def __init__(self):
        self.memories: Dict[str, List[MemoryItem]] = {}
        self.counter = 0
        self._turn_cache: Dict[str, List] = {}
    
    @property
    def name(self) -> str:
        return "memory"
    
    def is_available(self) -> bool:
        return True
    
    def initialize(self, session_id: str, **kwargs) -> None:
        self._session_id = session_id
        if session_id not in self.memories:
            self.memories[session_id] = []
        self._turn_cache[session_id] = []
    
    def prefetch(self, query: str, session_id: str = "") -> str:
        """Retrieve relevant memories."""
        items = self.memories.get(session_id or self._session_id, [])
        query_lower = query.lower()
        
        relevant = [m for m in items if query_lower in m.content.lower()]
        if not relevant:
            return ""
        
        context = "\n".join(f"- {m.content}" for m in relevant[:5])
        return f"<relevant_memory>\n{context}\n</relevant_memory>"
    
    def sync_turn(self, user_content: str, assistant_content: str, session_id: str = "") -> None:
        """Cache the turn for potential reflection."""
        sid = session_id or self._session_id
        if sid in self._turn_cache:
            self._turn_cache[sid].append({
                "user": user_content,
                "assistant": assistant_content,
                "timestamp": time.time()
            })
    
    def on_pre_compress(self, messages: List[Dict[str, Any]]) -> str:
        """Extract key points from messages about to be compressed."""
        if not messages:
            return ""
        
        # Extract user intents and key facts
        insights = []
        
        for msg in messages[-10:]:  # Last 10 messages
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role == "user" and len(content) < 200:
                # Small user messages are likely task descriptions
                if any(kw in content.lower() for kw in ["帮我", "请", "want", "need", "帮我"]):
                    insights.append(content[:100])
        
        if not insights:
            return ""
        
        return f"<memory_insights>\n- " + "\n- ".join(insights[:3]) + "\n</memory_insights>"
    
    async def store(self, session_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store a memory item in memory."""
        sid = session_id or self._session_id
        if sid not in self.memories:
            self.memories[sid] = []
        
        memory_id = f"mem_{self.counter}"
        self.counter += 1
        
        memory = MemoryItem(
            id=memory_id,
            content=content,
            metadata=metadata or {},
            timestamp=time.time()
        )
        
        self.memories[sid].append(memory)
        return memory_id
    
    async def retrieve(self, session_id: str, query: str, limit: int = 5) -> List[MemoryItem]:
        """Retrieve memories by simple keyword matching."""
        sid = session_id or self._session_id
        if sid not in self.memories:
            return []
        
        query_lower = query.lower()
        results = []
        
        for memory in self.memories[sid]:
            if query_lower in memory.content.lower():
                pos = memory.content.lower().index(query_lower)
                relevance = 1.0 - (pos / len(memory.content))
                memory.relevance_score = relevance
                results.append(memory)
        
        results.sort(key=lambda x: -x.relevance_score)
        return results[:limit]
    
    async def get_all(self, session_id: str) -> List[MemoryItem]:
        """Get all memories for a session."""
        sid = session_id or self._session_id
        return self.memories.get(sid, [])
    
    async def delete(self, session_id: str, memory_id: str) -> bool:
        """Delete a specific memory."""
        sid = session_id or self._session_id
        if sid not in self.memories:
            return False
        
        original_count = len(self.memories[sid])
        self.memories[sid] = [
            m for m in self.memories[sid] if m.id != memory_id
        ]
        
        return len(self.memories[sid]) < original_count
    
    async def clear(self, session_id: str):
        """Clear all memories for a session."""
        sid = session_id or self._session_id
        if sid in self.memories:
            del self.memories[sid]


class FileMemoryProvider(BaseMemoryProvider):
    """
    File-based memory provider using JSON storage.
    Persists memories across agent restarts.
    """
    
    def __init__(self, base_path: str = "./memories"):
        self.base_path = base_path
        self._session_id = ""
        os.makedirs(base_path, exist_ok=True)
    
    @property
    def name(self) -> str:
        return "file"
    
    def is_available(self) -> bool:
        return os.path.exists(self.base_path) or os.access(os.path.dirname(self.base_path), os.W_OK)
    
    def initialize(self, session_id: str, **kwargs) -> None:
        self._session_id = session_id
        os.makedirs(self.base_path, exist_ok=True)
    
    def _get_session_path(self, session_id: str) -> str:
        """Get the file path for a session's memories."""
        return os.path.join(self.base_path, f"{session_id}.json")
    
    def prefetch(self, query: str, session_id: str = "") -> str:
        """Retrieve relevant memories from file."""
        sid = session_id or self._session_id
        if not sid:
            return ""
        
        file_path = self._get_session_path(sid)
        if not os.path.exists(file_path):
            return ""
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            query_lower = query.lower()
            relevant = []
            
            for mem in data.get("memories", []):
                content = mem.get("content", "")
                if query_lower in content.lower():
                    relevant.append(content)
            
            if not relevant:
                return ""
            
            context = "\n".join(f"- {e}" for e in relevant[:5])
            return f"<relevant_memory>\n{context}\n</relevant_memory>"
        except Exception:
            return ""
    
    def on_pre_compress(self, messages: List[Dict[str, Any]]) -> str:
        """Extract key points before compression."""
        if not messages:
            return ""
        
        insights = []
        for msg in messages[-10:]:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role == "user" and len(content) < 200:
                if any(kw in content.lower() for kw in ["帮我", "请", "want", "need"]):
                    insights.append(content[:100])
        
        if not insights:
            return ""
        
        return f"<memory_insights>\n- " + "\n- ".join(insights[:3]) + "\n</memory_insights>"
    
    async def store(self, session_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store a memory item to file."""
        sid = session_id or self._session_id
        file_path = self._get_session_path(sid)
        
        # Load existing memories
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {"memories": [], "counter": 0}
        
        # Create new memory
        memory_id = f"mem_{data['counter']}"
        data["counter"] += 1
        
        memory = {
            "id": memory_id,
            "content": content,
            "metadata": metadata or {},
            "timestamp": time.time()
        }
        
        data["memories"].append(memory)
        
        # Save back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return memory_id
    
    async def retrieve(self, session_id: str, query: str, limit: int = 5) -> List[MemoryItem]:
        """Retrieve memories by keyword matching."""
        sid = session_id or self._session_id
        file_path = self._get_session_path(sid)
        
        if not os.path.exists(file_path):
            return []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        query_lower = query.lower()
        results = []
        
        for mem_dict in data.get("memories", []):
            if query_lower in mem_dict["content"].lower():
                pos = mem_dict["content"].lower().index(query_lower)
                relevance = 1.0 - (pos / len(mem_dict["content"]))
                
                memory = MemoryItem(
                    id=mem_dict["id"],
                    content=mem_dict["content"],
                    metadata=mem_dict.get("metadata", {}),
                    timestamp=mem_dict.get("timestamp", 0.0),
                    relevance_score=relevance
                )
                results.append(memory)
        
        results.sort(key=lambda x: -x.relevance_score)
        return results[:limit]
    
    async def get_all(self, session_id: str) -> List[MemoryItem]:
        """Get all memories for a session."""
        sid = session_id or self._session_id
        file_path = self._get_session_path(sid)
        
        if not os.path.exists(file_path):
            return []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return [
            MemoryItem(
                id=mem["id"],
                content=mem["content"],
                metadata=mem.get("metadata", {}),
                timestamp=mem.get("timestamp", 0.0)
            )
            for mem in data.get("memories", [])
        ]
    
    async def delete(self, session_id: str, memory_id: str) -> bool:
        """Delete a specific memory."""
        sid = session_id or self._session_id
        file_path = self._get_session_path(sid)
        
        if not os.path.exists(file_path):
            return False
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        original_count = len(data.get("memories", []))
        data["memories"] = [
            mem for mem in data["memories"] if mem["id"] != memory_id
        ]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return len(data["memories"]) < original_count
    
    async def clear(self, session_id: str):
        """Clear all memories for a session."""
        sid = session_id or self._session_id
        file_path = self._get_session_path(sid)
        if os.path.exists(file_path):
            os.remove(file_path)


# Alias for backward compatibility
ProviderBaseClass = BaseMemoryProvider