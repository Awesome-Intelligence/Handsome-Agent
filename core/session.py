#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Session Management Module - Inspired by Hermes Agent's session handling.

This module provides persistent session management with context retention,
history tracking, and state management across multiple interactions.
"""

import json
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging

from .layer_logger import get_layer_logger


@dataclass
class Message:
    """Represents a single message in the conversation."""
    role: str  # 'user', 'assistant', 'system', 'tool'
    content: str
    timestamp: float = field(default_factory=lambda: time.time())
    metadata: Dict[str, Any] = field(default_factory=dict)
    tool_call_id: Optional[str] = None
    tool_result: Optional[Dict[str, Any]] = None


@dataclass
class SessionConfig:
    """Configuration for session behavior."""
    max_history_length: int = 50
    auto_save_interval: int = 300  # seconds
    enable_persistence: bool = True
    history_path: str = "./sessions/"


class BaseSessionStore(ABC):
    """Abstract base class for session storage backends."""
    
    @abstractmethod
    def save(self, session_id: str, data: Dict[str, Any]):
        """Save session data."""
        pass
    
    @abstractmethod
    def load(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session data."""
        pass
    
    @abstractmethod
    def delete(self, session_id: str):
        """Delete session data."""
        pass
    
    @abstractmethod
    def list_sessions(self) -> List[str]:
        """List all session IDs."""
        pass


class FileSessionStore(BaseSessionStore):
    """File-based session storage."""
    
    def __init__(self, base_path: str = "./sessions"):
        self.base_path = base_path
        import os
        os.makedirs(base_path, exist_ok=True)
    
    def _get_file_path(self, session_id: str) -> str:
        """Get the file path for a session."""
        import os
        return os.path.join(self.base_path, f"{session_id}.json")
    
    def save(self, session_id: str, data: Dict[str, Any]):
        """Save session data to file."""
        file_path = self._get_file_path(session_id)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session data from file."""
        file_path = self._get_file_path(session_id)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except json.JSONDecodeError:
            return None
    
    def delete(self, session_id: str):
        """Delete session file."""
        import os
        file_path = self._get_file_path(session_id)
        if os.path.exists(file_path):
            os.remove(file_path)
    
    def list_sessions(self) -> List[str]:
        """List all session IDs."""
        import os
        sessions = []
        for filename in os.listdir(self.base_path):
            if filename.endswith('.json'):
                sessions.append(filename[:-5])
        return sessions


class Session:
    """
    Represents a conversation session with context and history.
    
    Inspired by Hermes Agent's session management with:
    - Message history tracking
    - Context retention
    - Automatic persistence
    - Tool call tracking
    """
    
    def __init__(self, session_id: str, config: Optional[SessionConfig] = None):
        self.session_id = session_id
        self.config = config or SessionConfig()
        self.messages: List[Message] = []
        self.context: Dict[str, Any] = {}
        self.last_save_time = 0.0
        self.store = FileSessionStore(self.config.history_path)
        self.logger = logging.getLogger(f"Session.{session_id}")
        self._storage_logger = get_layer_logger("storage", "SessionManager")
        
        if self.config.enable_persistence:
            self._load_session()
    
    def _load_session(self):
        """Load session from storage."""
        data = self.store.load(self.session_id)
        if data:
            try:
                # Load messages
                self.messages = [
                    Message(**msg) for msg in data.get('messages', [])
                ]
                
                # Load context
                self.context = data.get('context', {})
                
                self.logger.info(f"Loaded session with {len(self.messages)} messages")
            except Exception as e:
                self.logger.error(f"Failed to load session: {e}")
    
    def _save_session(self):
        """Save session to storage."""
        if not self.config.enable_persistence:
            return
        
        try:
            data = {
                'messages': [
                    {
                        'role': msg.role,
                        'content': msg.content,
                        'timestamp': msg.timestamp,
                        'metadata': msg.metadata,
                        'tool_call_id': msg.tool_call_id,
                        'tool_result': msg.tool_result
                    }
                    for msg in self.messages
                ],
                'context': self.context,
                'updated_at': time.time()
            }
            
            self.store.save(self.session_id, data)
            self.last_save_time = time.time()
            self.logger.debug("Session saved")
        except Exception as e:
            self.logger.error(f"Failed to save session: {e}")
    
    def add_message(self, role: str, content: str, **kwargs):
        """
        Add a message to the session.
        
        Args:
            role: Message role ('user', 'assistant', 'system', 'tool')
            content: Message content
            **kwargs: Additional metadata, tool_call_id, or tool_result
        """
        message = Message(
            role=role,
            content=content,
            metadata=kwargs.get('metadata', {}),
            tool_call_id=kwargs.get('tool_call_id'),
            tool_result=kwargs.get('tool_result')
        )
        
        self.messages.append(message)
        
        storage = self._storage_logger
        storage.info(f"💾 [存储层] 添加消息:")
        storage.info(f"  ├─ 角色: {role}")
        storage.info(f"  ├─ 内容: {content[:50]}...")
        storage.info(f"  └─ 消息数: {len(self.messages)}")
        
        if len(self.messages) > self.config.max_history_length:
            self.messages = self.messages[-self.config.max_history_length:]
            storage.info(f"✂️ [存储层] 历史记录已修剪，当前保留 {self.config.max_history_length} 条消息")
        
        if time.time() - self.last_save_time > self.config.auto_save_interval:
            self._save_session()
    
    def get_history(self, limit: Optional[int] = None) -> List[Message]:
        """
        Get message history.
        
        Args:
            limit: Maximum number of messages to return
            
        Returns:
            List of messages (most recent first if limit is specified)
        """
        if limit:
            return self.messages[-limit:]
        return self.messages
    
    def get_context(self) -> Dict[str, Any]:
        """Get current session context."""
        return self.context.copy()
    
    def set_context(self, key: str, value: Any):
        """Set a context value."""
        self.context[key] = value
    
    def update_context(self, updates: Dict[str, Any]):
        """Update multiple context values."""
        self.context.update(updates)
    
    def get_message_count(self) -> int:
        """Get total number of messages in session."""
        return len(self.messages)
    
    def get_last_message(self) -> Optional[Message]:
        """Get the most recent message."""
        if self.messages:
            return self.messages[-1]
        return None
    
    def get_formatted_history(self, include_system: bool = False) -> List[Dict[str, str]]:
        """
        Get history formatted for LLM API calls.
        
        Args:
            include_system: Whether to include system messages
            
        Returns:
            List of message dictionaries in LLM API format
        """
        formatted = []
        
        for msg in self.messages:
            if msg.role == 'system' and not include_system:
                continue
            
            formatted_msg = {
                'role': msg.role,
                'content': msg.content
            }
            
            # Handle tool calls and results
            if msg.role == 'assistant' and msg.tool_call_id:
                formatted_msg['tool_call_id'] = msg.tool_call_id
            
            if msg.role == 'tool' and msg.tool_result:
                formatted_msg['tool_result'] = msg.tool_result
            
            formatted.append(formatted_msg)
        
        return formatted
    
    def clear(self):
        """Clear all messages and context."""
        self.messages = []
        self.context = {}
        self._save_session()
        self.logger.info("Session cleared")
    
    def end(self):
        """End the session and persist final state."""
        self._save_session()
        self.logger.info("Session ended")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        stats = {
            'session_id': self.session_id,
            'message_count': len(self.messages),
            'user_messages': sum(1 for m in self.messages if m.role == 'user'),
            'assistant_messages': sum(1 for m in self.messages if m.role == 'assistant'),
            'tool_calls': sum(1 for m in self.messages if m.role == 'tool'),
            'context_keys': len(self.context),
            'created_at': self.messages[0].timestamp if self.messages else None,
            'last_activity': self.messages[-1].timestamp if self.messages else None
        }
        return stats


class SessionManager:
    """
    Manages multiple sessions.
    
    Provides session creation, retrieval, and lifecycle management.
    """
    
    def __init__(self, config: Optional[SessionConfig] = None):
        self.config = config or SessionConfig()
        self.sessions: Dict[str, Session] = {}
        self.store = FileSessionStore(self.config.history_path)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def create_session(self, session_id: Optional[str] = None) -> Session:
        """
        Create a new session.
        
        Args:
            session_id: Optional session ID. If not provided, generates a unique ID.
            
        Returns:
            New session instance
        """
        if session_id is None:
            session_id = self._generate_session_id()
        
        if session_id in self.sessions:
            self.logger.warning(f"Session {session_id} already exists, returning existing")
            return self.sessions[session_id]
        
        session = Session(session_id, self.config)
        self.sessions[session_id] = session
        self.logger.info(f"Created new session: {session_id}")
        
        return session
    
    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get an existing session.
        
        Args:
            session_id: Session ID to retrieve
            
        Returns:
            Session instance or None if not found
        """
        # Check in-memory first
        if session_id in self.sessions:
            return self.sessions[session_id]
        
        # Try to load from storage
        data = self.store.load(session_id)
        if data:
            session = self.create_session(session_id)
            return session
        
        return None
    
    def delete_session(self, session_id: str):
        """
        Delete a session.
        
        Args:
            session_id: Session ID to delete
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
        
        self.store.delete(session_id)
        self.logger.info(f"Deleted session: {session_id}")
    
    def list_sessions(self) -> List[str]:
        """List all available session IDs."""
        # Combine in-memory and stored sessions
        in_memory = set(self.sessions.keys())
        stored = set(self.store.list_sessions())
        return list(in_memory.union(stored))
    
    def get_active_sessions(self) -> List[Session]:
        """Get all currently active sessions."""
        return list(self.sessions.values())
    
    def cleanup_inactive(self, timeout_seconds: int = 3600):
        """Clean up inactive sessions."""
        now = time.time()
        to_remove = []
        
        for session_id, session in self.sessions.items():
            last_activity = session.get_last_message().timestamp if session.get_last_message() else 0
            if now - last_activity > timeout_seconds:
                to_remove.append(session_id)
        
        for session_id in to_remove:
            self.delete_session(session_id)
            self.logger.info(f"Cleaned up inactive session: {session_id}")


# Global session manager instance
session_manager = SessionManager()
