#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory Manager Module - Inspired by Hermes Agent

This module orchestrates memory operations across multiple providers,
including storing, retrieving, and reflecting on memories.

Key Features (from Hermes):
1. Multi-provider orchestration - manage multiple memory providers
2. Prefetch - recall relevant context before each turn
3. Sync - persist completed turns to all providers
4. Lifecycle hooks - on_session_switch, on_pre_compress, etc.
"""

from typing import List, Dict, Optional, Any, TYPE_CHECKING
import logging

from common.logging_manager import get_decision_logger
from .memory_provider import BaseMemoryProvider, MemoryItem

if TYPE_CHECKING:
    from .memory_provider import BuiltinMemoryProvider, InMemoryProvider

logger = get_decision_logger("MemoryManager")


class MemoryManager:
    """
    Memory Manager that orchestrates memory operations across providers.
    
    Inspired by Hermes Agent's memory_manager.py, this class:
    1. Stores memories via the configured provider
    2. Retrieves relevant memories based on queries
    3. Reflects on recent memories to extract long-term knowledge
    4. Manages memory consolidation
    5. Coordinates multiple providers with unified interface
    
    Usage:
        manager = MemoryManager()
        manager.add_provider(BuiltinMemoryProvider())
        
        # System prompt
        prompt_parts.append(manager.build_system_prompt())
        
        # Pre-turn
        context = manager.prefetch_all(user_message, session_id=session_id)
        
        # Post-turn
        manager.sync_all(user_msg, assistant_response, session_id=session_id)
    """
    
    def __init__(self):
        self._providers: List[BaseMemoryProvider] = []
        self._tool_to_provider: Dict[str, BaseMemoryProvider] = {}
        self._session_id: str = ""
        self.logger = get_decision_logger(self.__class__.__name__)
    
    # -- Provider Registration -----------------------------------------------
    
    def add_provider(self, provider: BaseMemoryProvider) -> None:
        """
        Register a memory provider.
        
        Built-in provider (name 'builtin') is always accepted.
        Only ONE external provider is allowed.
        """
        # Check for builtin
        is_builtin = provider.name == "builtin"
        
        # Check for existing external provider
        has_external = any(p.name != "builtin" for p in self._providers)
        if not is_builtin and has_external:
            self.logger.warning(
                f"Rejected memory provider '{provider.name}' — external provider "
                f"already registered. Only one external memory provider is allowed."
            )
            return
        
        self._providers.append(provider)
        
        # Index tool names → provider for routing
        for schema in provider.get_tool_schemas():
            tool_name = schema.get("name", "")
            if tool_name and tool_name not in self._tool_to_provider:
                self._tool_to_provider[tool_name] = provider
            elif tool_name in self._tool_to_provider:
                self.logger.warning(
                    f"Memory tool name conflict: '{tool_name}' already registered"
                )
        
        self.logger.info(
            f"Memory provider '{provider.name}' registered, "
            f"total providers: {len(self._providers)}"
        )
    
    @property
    def providers(self) -> List[BaseMemoryProvider]:
        """All registered providers in order."""
        return list(self._providers)
    
    def get_provider(self, name: str) -> Optional[BaseMemoryProvider]:
        """Get a provider by name, or None if not registered."""
        for p in self._providers:
            if p.name == name:
                return p
        return None
    
    # -- Initialization --------------------------------------------------------
    
    def initialize_all(self, session_id: str, **kwargs) -> None:
        """
        Initialize all providers.
        
        Args:
            session_id: The current session ID
            **kwargs: Additional context (platform, hermes_home, etc.)
        """
        self._session_id = session_id
        for provider in self._providers:
            try:
                provider.initialize(session_id, **kwargs)
            except Exception as e:
                self.logger.warning(
                    f"Memory provider '{provider.name}' initialize failed: {e}"
                )
    
    # -- System Prompt --------------------------------------------------------
    
    def build_system_prompt(self) -> str:
        """
        Collect system prompt blocks from all providers.
        
        Returns combined text, or empty string if no providers contribute.
        Each non-empty block is labeled with the provider name.
        """
        blocks = []
        for provider in self._providers:
            try:
                block = provider.system_prompt_block()
                if block and block.strip():
                    blocks.append(block)
            except Exception as e:
                self.logger.warning(
                    f"Memory provider '{provider.name}' system_prompt_block() failed: {e}"
                )
        return "\n\n".join(blocks)
    
    # -- Prefetch / Recall ---------------------------------------------------
    
    def prefetch_all(self, query: str, session_id: str = "") -> str:
        """
        Collect prefetch context from all providers.
        
        Returns merged context text. Empty providers are skipped.
        Failures in one provider don't block others.
        
        Args:
            query: The user's message or task description
            session_id: The current session ID
            
        Returns:
            Merged context text from all providers
        """
        sid = session_id or self._session_id
        parts = []
        
        for provider in self._providers:
            try:
                result = provider.prefetch(query, session_id=sid)
                if result and result.strip():
                    parts.append(result)
            except Exception as e:
                self.logger.debug(
                    f"Memory provider '{provider.name}' prefetch failed: {e}"
                )
        
        return "\n\n".join(parts)
    
    def queue_prefetch_all(self, query: str, session_id: str = "") -> None:
        """
        Queue background prefetch on all providers for the next turn.
        
        Args:
            query: The query to queue for prefetch
            session_id: The current session ID
        """
        sid = session_id or self._session_id
        for provider in self._providers:
            try:
                provider.queue_prefetch(query, session_id=sid)
            except Exception as e:
                self.logger.debug(
                    f"Memory provider '{provider.name}' queue_prefetch failed: {e}"
                )
    
    # -- Sync ----------------------------------------------------------------
    
    def sync_all(self, user_content: str, assistant_content: str, session_id: str = "") -> None:
        """
        Sync a completed turn to all providers.
        
        Args:
            user_content: The user's message
            assistant_content: The assistant's response
            session_id: The current session ID
        """
        sid = session_id or self._session_id
        for provider in self._providers:
            try:
                provider.sync_turn(user_content, assistant_content, session_id=sid)
            except Exception as e:
                self.logger.warning(
                    f"Memory provider '{provider.name}' sync_turn failed: {e}"
                )
    
    # -- Lifecycle Hooks -----------------------------------------------------
    
    def on_turn_start(self, turn_number: int, message: str, **kwargs) -> None:
        """
        Notify all providers of a new turn.
        
        Args:
            turn_number: The current turn number
            message: The user's message
            **kwargs: Additional context (remaining_tokens, model, etc.)
        """
        for provider in self._providers:
            try:
                provider.on_turn_start(turn_number, message, **kwargs)
            except Exception as e:
                self.logger.debug(
                    f"Memory provider '{provider.name}' on_turn_start failed: {e}"
                )
    
    def on_session_end(self, messages: List[Dict[str, Any]]) -> None:
        """
        Notify all providers of session end.
        
        Args:
            messages: The full conversation history
        """
        for provider in self._providers:
            try:
                provider.on_session_end(messages)
            except Exception as e:
                self.logger.debug(
                    f"Memory provider '{provider.name}' on_session_end failed: {e}"
                )
    
    def on_session_switch(
        self,
        new_session_id: str,
        parent_session_id: str = "",
        reset: bool = False,
        **kwargs
    ) -> None:
        """
        Notify all providers that the agent's session_id has rotated.
        
        Args:
            new_session_id: The new session ID
            parent_session_id: The previous session ID (for lineage)
            reset: True for genuinely new conversation
        """
        if not new_session_id:
            return
        
        self._session_id = new_session_id
        for provider in self._providers:
            try:
                provider.on_session_switch(
                    new_session_id,
                    parent_session_id=parent_session_id,
                    reset=reset,
                    **kwargs
                )
            except Exception as e:
                self.logger.debug(
                    f"Memory provider '{provider.name}' on_session_switch failed: {e}"
                )
    
    def on_pre_compress(self, messages: List[Dict[str, Any]]) -> str:
        """
        Notify all providers before context compression.
        
        Returns combined text from providers to include in the compression
        summary prompt. Empty string if no provider contributes.
        
        Args:
            messages: The messages that will be compressed
            
        Returns:
            Combined text from all providers
        """
        parts = []
        for provider in self._providers:
            try:
                result = provider.on_pre_compress(messages)
                if result and result.strip():
                    parts.append(result)
            except Exception as e:
                self.logger.debug(
                    f"Memory provider '{provider.name}' on_pre_compress failed: {e}"
                )
        return "\n\n".join(parts)
    
    def on_memory_write(
        self,
        action: str,
        target: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Notify external providers when the built-in memory tool writes.
        
        Args:
            action: 'add', 'replace', or 'remove'
            target: 'memory' or 'user'
            content: The entry content
            metadata: Structured provenance for the write
        """
        for provider in self._providers:
            if provider.name == "builtin":
                continue
            try:
                provider.on_memory_write(action, target, content, metadata)
            except Exception as e:
                self.logger.debug(
                    f"Memory provider '{provider.name}' on_memory_write failed: {e}"
                )
    
    def on_delegation(
        self,
        task: str,
        result: str,
        child_session_id: str = "",
        **kwargs
    ) -> None:
        """
        Notify all providers that a subagent completed.
        
        Args:
            task: The delegation prompt
            result: The subagent's final response
            child_session_id: The subagent's session_id
        """
        for provider in self._providers:
            try:
                provider.on_delegation(task, result, child_session_id=child_session_id, **kwargs)
            except Exception as e:
                self.logger.debug(
                    f"Memory provider '{provider.name}' on_delegation failed: {e}"
                )
    
    def shutdown_all(self) -> None:
        """Shut down all providers in reverse order for clean teardown."""
        for provider in reversed(self._providers):
            try:
                provider.shutdown()
            except Exception as e:
                self.logger.warning(
                    f"Memory provider '{provider.name}' shutdown failed: {e}"
                )
    
    # -- Tool Routing --------------------------------------------------------
    
    def get_all_tool_schemas(self) -> List[Dict[str, Any]]:
        """Collect tool schemas from all providers."""
        schemas = []
        seen = set()
        for provider in self._providers:
            try:
                for schema in provider.get_tool_schemas():
                    name = schema.get("name", "")
                    if name and name not in seen:
                        schemas.append(schema)
                        seen.add(name)
            except Exception as e:
                self.logger.warning(
                    f"Memory provider '{provider.name}' get_tool_schemas failed: {e}"
                )
        return schemas
    
    def get_all_tool_names(self) -> set:
        """Return set of all tool names across all providers."""
        return set(self._tool_to_provider.keys())
    
    def has_tool(self, tool_name: str) -> bool:
        """Check if any provider handles this tool."""
        return tool_name in self._tool_to_provider
    
    def handle_tool_call(
        self,
        tool_name: str,
        args: Dict[str, Any],
        **kwargs
    ) -> str:
        """
        Route a tool call to the correct provider.
        
        Args:
            tool_name: The tool name to handle
            args: The tool arguments
            **kwargs: Additional context
            
        Returns:
            JSON string result
        """
        from tools.registry import tool_error
        
        provider = self._tool_to_provider.get(tool_name)
        if provider is None:
            return tool_error(f"No memory provider handles tool '{tool_name}'")
        
        try:
            return provider.handle_tool_call(tool_name, args, **kwargs)
        except Exception as e:
            self.logger.error(
                f"Memory provider '{provider.name}' handle_tool_call({tool_name}) failed: {e}"
            )
            return tool_error(f"Memory tool '{tool_name}' failed: {e}")
    
    # -- Convenience Methods (delegate to first provider) --------------------
    
    async def add_memory(
        self,
        session_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a new memory to the store.
        
        Delegates to the first provider.
        """
        if not self._providers:
            return ""
        
        memory_id = await self._providers[0].store(session_id, content, metadata)
        self.logger.debug(f"Added memory {memory_id} for session {session_id}")
        return memory_id
    
    async def retrieve_memories(
        self,
        session_id: str,
        query: str,
        limit: int = 5
    ) -> List[MemoryItem]:
        """
        Retrieve memories relevant to a query.
        
        Delegates to the first provider.
        """
        if not self._providers:
            return []
        
        memories = await self._providers[0].retrieve(session_id, query, limit)
        self.logger.debug(f"Retrieved {len(memories)} memories for query: {query[:30]}...")
        return memories
    
    async def get_all_memories(self, session_id: str) -> List[MemoryItem]:
        """Get all memories for a session. Delegates to the first provider."""
        if not self._providers:
            return []
        return await self._providers[0].get_all(session_id)
    
    async def delete_memory(self, session_id: str, memory_id: str) -> bool:
        """Delete a specific memory. Delegates to the first provider."""
        if not self._providers:
            return False
        
        success = await self._providers[0].delete(session_id, memory_id)
        if success:
            self.logger.debug(f"Deleted memory {memory_id} from session {session_id}")
        return success
    
    async def clear_memories(self, session_id: str):
        """Clear all memories for a session. Delegates to the first provider."""
        if not self._providers:
            return
        await self._providers[0].clear(session_id)
        self.logger.debug(f"Cleared all memories for session {session_id}")
    
    async def reflect(
        self,
        session_id: str,
        recent_count: int = 20
    ) -> Optional[str]:
        """
        Reflect on recent memories and extract key insights.
        
        This method summarizes recent memories to identify patterns,
        important facts, and actionable knowledge.
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
            await self.add_memory(session_id, memory.content, memory.metadata)
        
        self.logger.debug(f"Consolidated memories: kept {len(memories_to_keep)} of {len(all_memories)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory manager statistics."""
        return {
            "provider_count": len(self._providers),
            "provider_names": [p.name for p in self._providers],
            "tool_count": len(self._tool_to_provider),
            "current_session": self._session_id,
        }