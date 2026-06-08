#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Context Engine Module - Inspired by Hermes Agent

This module provides pluggable context management with support for
context compression, summarization, and retrieval.

Usage:
    from agent.context.context_engine import ContextEngine, ContextMessage
    
    class MyContextEngine(ContextEngine):
        def compress(self, messages, max_tokens):
            ...
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

from common.logging_manager import get_decision_logger


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
    
    See Also:
        ContextCompressor: Default implementation with LLM-driven summarization.
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
