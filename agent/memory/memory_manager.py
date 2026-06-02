#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory Manager Module - Inspired by Hermes Agent

This module orchestrates memory operations, including storing,
retrieving, and reflecting on memories.
"""

from typing import List, Dict, Optional, Any
from .memory_provider import BaseMemoryProvider, MemoryItem

from common.logging_manager import get_decision_logger


class MemoryManager:
    """
    Memory Manager that orchestrates memory operations.
    
    Inspired by Hermes Agent's memory_manager.py, this class:
    1. Stores memories via the configured provider
    2. Retrieves relevant memories based on queries
    3. Reflects on recent memories to extract long-term knowledge
    4. Manages memory consolidation
    """
    
    def __init__(self, provider: BaseMemoryProvider):
        self.provider = provider
        self.logger = get_decision_logger(self.__class__.__name__)
    
    async def add_memory(self, session_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Add a new memory to the store.
        
        Args:
            session_id: The session ID
            content: The memory content
            metadata: Optional metadata (tags, context, etc.)
        
        Returns:
            The ID of the stored memory
        """
        memory_id = await self.provider.store(session_id, content, metadata)
        self.logger.debug(f"Added memory {memory_id} for session {session_id}")
        return memory_id
    
    async def retrieve_memories(self, session_id: str, query: str, limit: int = 5) -> List[MemoryItem]:
        """
        Retrieve memories relevant to a query.
        
        Args:
            session_id: The session ID
            query: The search query
            limit: Maximum number of results
        
        Returns:
            List of matching memories sorted by relevance
        """
        memories = await self.provider.retrieve(session_id, query, limit)
        self.logger.debug(f"Retrieved {len(memories)} memories for query: {query[:30]}...")
        return memories
    
    async def get_all_memories(self, session_id: str) -> List[MemoryItem]:
        """
        Get all memories for a session.
        
        Args:
            session_id: The session ID
        
        Returns:
            List of all memory items
        """
        return await self.provider.get_all(session_id)
    
    async def delete_memory(self, session_id: str, memory_id: str) -> bool:
        """
        Delete a specific memory.
        
        Args:
            session_id: The session ID
            memory_id: The memory ID to delete
        
        Returns:
            True if deletion was successful
        """
        success = await self.provider.delete(session_id, memory_id)
        if success:
            self.logger.debug(f"Deleted memory {memory_id} from session {session_id}")
        return success
    
    async def clear_memories(self, session_id: str):
        """
        Clear all memories for a session.
        
        Args:
            session_id: The session ID
        """
        await self.provider.clear(session_id)
        self.logger.debug(f"Cleared all memories for session {session_id}")
    
    async def reflect(self, session_id: str, recent_count: int = 20) -> Optional[str]:
        """
        Reflect on recent memories and extract key insights.
        
        This method summarizes recent memories to identify patterns,
        important facts, and actionable knowledge that can be stored
        as long-term memory.
        
        Args:
            session_id: The session ID
            recent_count: Number of recent memories to consider
        
        Returns:
            A summary string of key insights (or None if no memories)
        """
        all_memories = await self.get_all_memories(session_id)
        
        if not all_memories:
            self.logger.debug("No memories to reflect on")
            return None
        
        # Get most recent memories
        recent_memories = sorted(all_memories, key=lambda x: x.timestamp, reverse=True)[:recent_count]
        
        # Extract key information
        insights = []
        user_intents = []
        important_facts = []
        
        for memory in recent_memories:
            content = memory.content
            
            # Simple pattern recognition
            if "learned" in content.lower() or "discovered" in content.lower():
                important_facts.append(content)
            
            if "want" in content.lower() or "need" in content.lower():
                user_intents.append(content)
        
        # Build reflection summary
        summary_parts = []
        
        if user_intents:
            summary_parts.append(f"User intents observed: {', '.join(user_intents[:3])}")
        
        if important_facts:
            summary_parts.append(f"Important facts learned: {', '.join(important_facts[:3])}")
        
        if summary_parts:
            summary = " | ".join(summary_parts)
            self.logger.debug(f"Generated reflection: {summary[:100]}...")
            return summary
        
        return None
    
    async def consolidate_memories(self, session_id: str, max_memories: int = 100):
        """
        Consolidate memories by merging similar ones and removing duplicates.
        
        Args:
            session_id: The session ID
            max_memories: Maximum number of memories to keep
        """
        all_memories = await self.get_all_memories(session_id)
        
        if len(all_memories) <= max_memories:
            return
        
        # Sort by timestamp (newest first)
        sorted_memories = sorted(all_memories, key=lambda x: x.timestamp, reverse=True)
        
        # Keep only the most recent memories
        memories_to_keep = sorted_memories[:max_memories]
        
        # Clear and re-store only the ones we want to keep
        await self.clear_memories(session_id)
        
        for memory in memories_to_keep:
            await self.add_memory(
                session_id,
                memory.content,
                memory.metadata
            )
        
        self.logger.debug(f"Consolidated memories: kept {len(memories_to_keep)} of {len(all_memories)}")
