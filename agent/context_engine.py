#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Context Engine Module - Inspired by Hermes Agent

This module provides pluggable context management with support for
context compression, summarization, and retrieval.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging


@dataclass
class ContextMessage:
    """Represents a message in the context."""
    role: str  # 'user', 'assistant', 'system', 'tool'
    content: str
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    token_count: int = 0


class ContextEngine(ABC):
    """
    Abstract base class for context engines.
    
    Context engines are responsible for:
    1. Managing conversation history
    2. Compressing context to fit within model limits
    3. Summarizing long conversations
    4. Retrieving relevant context
    """
    
    @abstractmethod
    def compress(self, messages: List[ContextMessage], max_tokens: int) -> List[ContextMessage]:
        """
        Compress messages to fit within the specified token limit.
        
        Args:
            messages: List of messages to compress
            max_tokens: Maximum allowed tokens after compression
        
        Returns:
            Compressed list of messages
        """
        pass
    
    @abstractmethod
    def summarize(self, messages: List[ContextMessage]) -> str:
        """
        Generate a summary of the messages.
        
        Args:
            messages: List of messages to summarize
        
        Returns:
            Summary string
        """
        pass
    
    @abstractmethod
    def add_message(self, message: ContextMessage):
        """Add a new message to the context."""
        pass
    
    @abstractmethod
    def get_context(self, max_tokens: Optional[int] = None) -> List[ContextMessage]:
        """
        Get the current context.
        
        Args:
            max_tokens: Optional token limit for the returned context
        
        Returns:
            List of context messages
        """
        pass
    
    @abstractmethod
    def clear(self):
        """Clear all context."""
        pass


class SimpleContextEngine(ContextEngine):
    """
    A simple context engine that keeps all messages without compression.
    Suitable for short conversations or debugging.
    """
    
    def __init__(self):
        self.messages: List[ContextMessage] = []
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def compress(self, messages: List[ContextMessage], max_tokens: int) -> List[ContextMessage]:
        """Return messages as-is without compression."""
        return messages
    
    def summarize(self, messages: List[ContextMessage]) -> str:
        """Generate a simple summary."""
        if not messages:
            return "No conversation history."
        
        user_messages = [m for m in messages if m.role == 'user']
        assistant_messages = [m for m in messages if m.role == 'assistant']
        
        summary = f"Conversation with {len(user_messages)} user messages and {len(assistant_messages)} assistant responses."
        
        if user_messages:
            summary += f" Last user message: {user_messages[-1].content[:100]}..."
        
        return summary
    
    def add_message(self, message: ContextMessage):
        """Add a new message."""
        self.messages.append(message)
    
    def get_context(self, max_tokens: Optional[int] = None) -> List[ContextMessage]:
        """Get all messages."""
        return self.messages
    
    def clear(self):
        """Clear all messages."""
        self.messages = []


class TruncatingContextEngine(ContextEngine):
    """
    Context engine that truncates older messages when limit is reached.
    Keeps recent messages intact while discarding older ones.
    """
    
    def __init__(self, default_max_tokens: int = 8192):
        self.messages: List[ContextMessage] = []
        self.default_max_tokens = default_max_tokens
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _count_tokens(self, messages: List[ContextMessage]) -> int:
        """Count total tokens in messages."""
        return sum(m.token_count for m in messages)
    
    def compress(self, messages: List[ContextMessage], max_tokens: int) -> List[ContextMessage]:
        """Truncate older messages to fit within token limit."""
        if not messages:
            return []
        
        # Start from the end and accumulate until we reach the limit
        total = 0
        compressed = []
        
        for message in reversed(messages):
            if total + message.token_count <= max_tokens:
                compressed.insert(0, message)
                total += message.token_count
            else:
                # Try to summarize the remaining messages
                remaining = messages[:len(messages) - len(compressed)]
                summary = self.summarize(remaining)
                summary_msg = ContextMessage(
                    role='system',
                    content=f"Previous conversation summary: {summary}",
                    timestamp=remaining[0].timestamp if remaining else 0.0,
                    metadata={'type': 'summary'}
                )
                compressed.insert(0, summary_msg)
                break
        
        return compressed
    
    def summarize(self, messages: List[ContextMessage]) -> str:
        """Generate a concise summary of the conversation."""
        if not messages:
            return ""
        
        user_inputs = [m.content for m in messages if m.role == 'user']
        assistant_responses = [m.content for m in messages if m.role == 'assistant']
        
        summary_parts = []
        
        if user_inputs:
            summary_parts.append(f"User asked about: {', '.join(user_inputs[-3:])}")
        
        if assistant_responses:
            summary_parts.append(f"Assistant provided information and assistance.")
        
        return " ".join(summary_parts)
    
    def add_message(self, message: ContextMessage):
        """Add a new message and compress if needed."""
        self.messages.append(message)
        
        # Auto-compress if over limit
        total_tokens = self._count_tokens(self.messages)
        if total_tokens > self.default_max_tokens:
            self.messages = self.compress(self.messages, self.default_max_tokens)
            self.logger.debug(f"Auto-compressed context from {total_tokens} to ~{self.default_max_tokens} tokens")
    
    def get_context(self, max_tokens: Optional[int] = None) -> List[ContextMessage]:
        """Get context, optionally compressed to token limit."""
        if max_tokens is None:
            return self.messages
        return self.compress(self.messages, max_tokens)
    
    def clear(self):
        """Clear all messages."""
        self.messages = []
