#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory Provider Module - Inspired by Hermes Agent

This module defines the abstract interface for memory providers
and provides basic implementations.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import json
import os


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
    of agent memories across sessions.
    """
    
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


class InMemoryProvider(BaseMemoryProvider):
    """
    In-memory memory provider for testing and development.
    Not persistent across agent restarts.
    """
    
    def __init__(self):
        self.memories: Dict[str, List[MemoryItem]] = {}
        self.counter = 0
    
    async def store(self, session_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store a memory item in memory."""
        if session_id not in self.memories:
            self.memories[session_id] = []
        
        memory_id = f"mem_{self.counter}"
        self.counter += 1
        
        memory = MemoryItem(
            id=memory_id,
            content=content,
            metadata=metadata or {},
            timestamp=0.0
        )
        
        self.memories[session_id].append(memory)
        return memory_id
    
    async def retrieve(self, session_id: str, query: str, limit: int = 5) -> List[MemoryItem]:
        """Retrieve memories by simple keyword matching."""
        if session_id not in self.memories:
            return []
        
        query_lower = query.lower()
        results = []
        
        for memory in self.memories[session_id]:
            if query_lower in memory.content.lower():
                # Simple relevance based on keyword position
                pos = memory.content.lower().index(query_lower)
                relevance = 1.0 - (pos / len(memory.content))
                memory.relevance_score = relevance
                results.append(memory)
        
        # Sort by relevance and limit
        results.sort(key=lambda x: -x.relevance_score)
        return results[:limit]
    
    async def get_all(self, session_id: str) -> List[MemoryItem]:
        """Get all memories for a session."""
        return self.memories.get(session_id, [])
    
    async def delete(self, session_id: str, memory_id: str) -> bool:
        """Delete a specific memory."""
        if session_id not in self.memories:
            return False
        
        original_count = len(self.memories[session_id])
        self.memories[session_id] = [
            m for m in self.memories[session_id] if m.id != memory_id
        ]
        
        return len(self.memories[session_id]) < original_count
    
    async def clear(self, session_id: str):
        """Clear all memories for a session."""
        if session_id in self.memories:
            del self.memories[session_id]


class FileMemoryProvider(BaseMemoryProvider):
    """
    File-based memory provider using JSON storage.
    Persists memories across agent restarts.
    """
    
    def __init__(self, base_path: str = "./memories"):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
    
    def _get_session_path(self, session_id: str) -> str:
        """Get the file path for a session's memories."""
        return os.path.join(self.base_path, f"{session_id}.json")
    
    async def store(self, session_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store a memory item to file."""
        file_path = self._get_session_path(session_id)
        
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
            "timestamp": 0.0
        }
        
        data["memories"].append(memory)
        
        # Save back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return memory_id
    
    async def retrieve(self, session_id: str, query: str, limit: int = 5) -> List[MemoryItem]:
        """Retrieve memories by keyword matching."""
        file_path = self._get_session_path(session_id)
        
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
        file_path = self._get_session_path(session_id)
        
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
        file_path = self._get_session_path(session_id)
        
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
        file_path = self._get_session_path(session_id)
        if os.path.exists(file_path):
            os.remove(file_path)
