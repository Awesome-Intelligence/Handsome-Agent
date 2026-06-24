#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Session Management Module - 会话管理

提供跨会话的上下文保留、历史追踪和状态管理。

架构说明：
- Session: 单个对话会话，管理消息历史
- SessionManager: 多会话管理，创建/获取/切换会话

职责边界（与 MemoryStore 的区分）：
┌─────────────────────────────────────────────────────────────────────┐
│                         用户可见记忆                                   │
├─────────────────────────────────────────────────────────────────────┤
│  MemoryStore (agent/memory/memory_store.py)                          │
│  - 用途: 用户显式添加/管理的长期记忆                                   │
│  - 存储: ~/.handsome_agent/memories/MEMORY.md                       │
│  - 管理: 通过 memory_tool (add/replace/remove)                        │
│  - 特点: 跨会话持久，用户完全控制                                      │
├─────────────────────────────────────────────────────────────────────┤
│  Session (本模块)                                                    │
│  - 用途: 自动生成的会话摘要，用于跨会话上下文                          │
│  - 存储: ~/.handsome_agent/sessions/daily_summary.md                │
│  - 管理: sync_to_daily_summary() 自动生成                            │
│  - 特点: 自动摘要，Agent 可读取但不直接修改                            │
└─────────────────────────────────────────────────────────────────────┘

参考 Hermes Agent 的 session handling 设计。
"""

import json
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from common.config import get_sessions_dir, ensure_workspace_dirs
from common.logging_manager import get_decision_logger


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
class CompressionRecord:
    """Compression record - tracks session compression history"""
    timestamp: float
    original_count: int
    compressed_count: int
    summary: str
    parent_messages: List[Dict[str, Any]]
    compression_ratio: float


@dataclass
class SessionConfig:
    """Configuration for session behavior."""
    max_history_length: int = 50
    auto_save_interval: int = 300
    enable_persistence: bool = True
    history_path: str = field(default_factory=lambda: str(get_sessions_dir()))
    enable_detailed_logs: bool = True
    enable_compression: bool = True  # 启用上下文压缩
    compression_threshold: int = 30  # 触发压缩的消息数阈值
    preserve_compressed_history: bool = True  # 保留压缩历史用于追踪


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
    """File-based session storage with date-based organization."""
    
    def __init__(self, base_path: str = "./sessions"):
        self.base_path = base_path
        import os
        os.makedirs(base_path, exist_ok=True)
    
    def _get_date_dir(self, session_id: str = None) -> str:
        """Get or extract date directory path from session_id or current date."""
        if session_id and len(session_id) >= 8:
            date_str = session_id[:8]  # YYYYMMDD format
            return date_str
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d")
    
    def _get_file_path(self, session_id: str) -> str:
        """Get the file path for a session."""
        import os
        date_dir = self._get_date_dir(session_id)
        full_path = os.path.join(self.base_path, date_dir)
        os.makedirs(full_path, exist_ok=True)
        return os.path.join(full_path, f"{session_id}.json")
    
    def save(self, session_id: str, data: Dict[str, Any]):
        """Save session data to file."""
        import os
        file_path = self._get_file_path(session_id)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
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
        """List all session IDs (flat list)."""
        import os
        sessions = []
        for root, dirs, files in os.walk(self.base_path):
            for filename in files:
                if filename.endswith('.json'):
                    session_id = filename[:-5]
                    sessions.append(session_id)
        return sessions
    
    def list_today_sessions(self) -> List[str]:
        """List sessions from today."""
        import os
        from datetime import datetime
        today_dir = datetime.now().strftime("%Y-%m-%d")
        today_path = os.path.join(self.base_path, today_dir)
        
        if not os.path.exists(today_path):
            return []
        
        sessions = []
        for filename in os.listdir(today_path):
            if filename.endswith('.json'):
                sessions.append(filename[:-5])
        return sorted(sessions, reverse=True)
    
    def list_sessions_by_date(self) -> Dict[str, List[str]]:
        """List all sessions grouped by date."""
        import os
        result = {}
        for root, dirs, files in os.walk(self.base_path):
            date_dir = os.path.basename(root)
            if date_dir and '-' in date_dir:
                sessions = [f[:-5] for f in files if f.endswith('.json')]
                if sessions:
                    result[date_dir] = sorted(sessions, reverse=True)
        return result
    
    def get_latest_session(self) -> Optional[str]:
        """Get the most recent session ID."""
        sessions = self.list_sessions()
        if sessions:
            return sorted(sessions, reverse=True)[0]
        return None
    
    def get_latest_today_session(self) -> Optional[str]:
        """Get the most recent session ID from today."""
        sessions = self.list_today_sessions()
        if sessions:
            return sessions[0]
        return None


class Session:
    """
    Represents a conversation session with context and history.
    
    Inspired by Hermes Agent's session management with:
    - Message history tracking
    - Context retention
    - Automatic persistence
    - Tool call tracking
    - Session compression with lineage tracking (压缩传承追踪)
    """
    
    def __init__(self, session_id: str, config: Optional[SessionConfig] = None):
        ensure_workspace_dirs()
        self.session_id = session_id
        self.config = config or SessionConfig()
        self.messages: List[Message] = []
        self.context: Dict[str, Any] = {}
        self.last_save_time = 0.0
        self.store = FileSessionStore(self.config.history_path)
        self.logger = get_decision_logger(f"Session.{session_id}")
        self.logger.propagate = False
        self._enable_detailed_logs = self.config.enable_detailed_logs
        
        # Session compression inheritance tracking
        self._compression_records: List[CompressionRecord] = []
        self._parent_session_id: Optional[str] = None  # Parent session ID (from compression)
        self._child_session_ids: List[str] = []  # Child session ID list
        
        if self.config.enable_persistence:
            self._load_session()
    
    def _load_session(self):
        """Load session from storage."""
        data = self.store.load(self.session_id)
        if data:
            try:
                self.messages = [
                    Message(**msg) for msg in data.get('messages', [])
                ]
                
                self.context = data.get('context', {})
                
                if self.config.preserve_compressed_history:
                    compression_data = data.get('compression_records', [])
                    self._compression_records = [
                        CompressionRecord(**record) for record in compression_data
                    ]
                
                self._parent_session_id = data.get('parent_session_id')
                self._child_session_ids = data.get('child_session_ids', [])
                
                self.logger.info(f"Loaded session with {len(self.messages)} messages")
                if self._compression_records:
                    self.logger.info(f"Session has {len(self._compression_records)} compression records")
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
                'updated_at': time.time(),
                'compression_records': [
                    {
                        'timestamp': record.timestamp,
                        'original_count': record.original_count,
                        'compressed_count': record.compressed_count,
                        'summary': record.summary,
                        'parent_messages': record.parent_messages,
                        'compression_ratio': record.compression_ratio
                    }
                    for record in self._compression_records
                ] if self.config.preserve_compressed_history else [],
                'parent_session_id': self._parent_session_id,
                'child_session_ids': self._child_session_ids
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
        
        self.logger.info(f"（SessionManager） 添加消息: 角色={role}, 内容={content[:50]}..., 消息数={len(self.messages)}")
        
        if len(self.messages) > self.config.max_history_length:
            self.messages = self.messages[-self.config.max_history_length:]
            self.logger.debug(f"✂️ [执行层] 历史记录已修剪，当前保留 {self.config.max_history_length} 条消息")
        
        if time.time() - self.last_save_time > self.config.auto_save_interval:
            self._save_session()
    
    def record_compression(
        self,
        original_count: int,
        compressed_count: int,
        summary: str,
        parent_messages: List[Dict[str, Any]],
        compression_ratio: float
    ):
        """
        记录一次压缩操作
        
        Args:
            original_count: 原始消息数
            compressed_count: 压缩后消息数
            summary: 压缩摘要
            parent_messages: 被压缩的原始消息
            compression_ratio: 压缩率
        """
        record = CompressionRecord(
            timestamp=time.time(),
            original_count=original_count,
            compressed_count=compressed_count,
            summary=summary,
            parent_messages=parent_messages,
            compression_ratio=compression_ratio
        )
        self._compression_records.append(record)
        self.logger.info(
            f"Recorded compression: {original_count} -> {compressed_count} messages "
            f"(ratio: {compression_ratio:.2%})"
        )
        
        # 限制压缩记录数量
        if len(self._compression_records) > 50:
            self._compression_records = self._compression_records[-50:]
        
        self._save_session()
    
    def get_compression_history(self) -> List[CompressionRecord]:
        """获取压缩历史"""
        return self._compression_records.copy()
    
    def get_lineage_info(self) -> Dict[str, Any]:
        """获取会话传承信息"""
        return {
            'session_id': self.session_id,
            'parent_session_id': self._parent_session_id,
            'has_parent': self._parent_session_id is not None,
            'child_session_ids': self._child_session_ids.copy(),
            'child_count': len(self._child_session_ids),
            'compression_count': len(self._compression_records),
            'total_messages_preserved': sum(
                r.original_count - r.compressed_count
                for r in self._compression_records
            )
        }
    
    def set_parent_session(self, parent_id: str):
        """设置父会话（压缩产生的新会话）"""
        self._parent_session_id = parent_id
        self._save_session()
    
    def add_child_session(self, child_id: str):
        """添加子会话"""
        if child_id not in self._child_session_ids:
            self._child_session_ids.append(child_id)
            self._save_session()
    
    def expand_compressed_message(self, summary_content: str) -> List[Dict[str, Any]]:
        """
        展开压缩消息，恢复原始内容
        
        Args:
            summary_content: 摘要消息的内容
            
        Returns:
            被压缩的原始消息列表
        """
        for record in self._compression_records:
            if summary_content in record.summary:
                return record.parent_messages
        return []
    
    def get_full_history_with_lineage(self) -> Dict[str, Any]:
        """
        获取完整的会话历史（包括传承追踪信息）
        
        Returns:
            包含消息和传承信息的字典
        """
        return {
            'session_id': self.session_id,
            'messages': [
                {
                    'role': msg.role,
                    'content': msg.content,
                    'timestamp': msg.timestamp,
                    'metadata': msg.metadata
                }
                for msg in self.messages
            ],
            'context': self.context.copy(),
            'lineage': self.get_lineage_info(),
            'compression_history': [
                {
                    'timestamp': r.timestamp,
                    'original_count': r.original_count,
                    'compressed_count': r.compressed_count,
                    'summary': r.summary[:200],
                    'compression_ratio': r.compression_ratio
                }
                for r in self._compression_records
            ]
        }
    
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
    
    def end(self, trigger_curator: bool = True):
        """
        End the session and persist final state.
        
        Args:
            trigger_curator: Whether to trigger automatic memory summarization.
                            Set to False to skip curator (e.g., for brief sessions).
        """
        self._save_session()
        self.logger.info("Session ended")
        
        # 自动记忆总结 (参考 Hermes)
        if trigger_curator:
            self._trigger_memory_curator()
    
    def _trigger_memory_curator(self):
        """
        Trigger automatic memory summarization via MemoryCurator.
        
        This is called automatically at session end if curator is enabled.
        Reference: Hermes Agent's HonchoSessionManager for user preference modeling.
        """
        try:
            from agent.memory import curator_on_session_end, get_default_curator
            
            # 检查是否需要总结（基于消息数）
            user_message_count = sum(1 for m in self.messages if m.role == 'user')
            
            if user_message_count < 5:
                self.logger.debug(f"Session has only {user_message_count} user messages, skipping curator")
                return
            
            # 调用 curator
            curator = get_default_curator()
            result = curator.on_session_end(self)
            
            if result.get("status") == "success":
                self.logger.info(
                    f"MemoryCurator: added {result.get('user_entries_added', 0)} user, "
                    f"{result.get('memory_entries_added', 0)} memory entries"
                )
            elif result.get("status") == "below_threshold":
                self.logger.debug("MemoryCurator: below threshold, skipped")
            elif result.get("status") == "disabled":
                self.logger.debug("MemoryCurator: disabled")
            else:
                if result.get("errors"):
                    self.logger.warning(f"MemoryCurator errors: {result.get('errors')}")
                    
        except ImportError:
            self.logger.debug("MemoryCurator not available, skipping")
        except Exception as e:
            self.logger.warning(f"MemoryCurator error: {e}")
    
    def get_summary(self, max_messages: int = 10) -> str:
        """
        Generate a summary of the session for memory purposes.
        
        Args:
            max_messages: Maximum number of recent messages to include in summary
            
        Returns:
            Summary string describing the session
        """
        if not self.messages:
            return "Empty session"
        
        recent_msgs = self.messages[-max_messages:]
        
        summary_parts = []
        user_count = 0
        assistant_count = 0
        
        for msg in recent_msgs:
            if msg.role == 'user':
                user_count += 1
                content_preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                summary_parts.append(f"User: {content_preview}")
            elif msg.role == 'assistant':
                assistant_count += 1
                content_preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                summary_parts.append(f"Assistant: {content_preview}")
        
        total_msgs = len(self.messages)
        return f"Session {self.session_id} ({total_msgs} messages: {user_count} user, {assistant_count} assistant):\n" + "\n".join(summary_parts)
    
    def get_memory_content(self) -> str:
        """
        Generate memory content for this session.
        
        Returns:
            Markdown-formatted string for memory.md
        """
        from datetime import datetime
        
        date = datetime.fromtimestamp(self.messages[0].timestamp if self.messages else time.time())
        date_str = date.strftime("%Y-%m-%d")
        
        topics = []
        for msg in self.messages:
            if msg.role == 'user':
                content_preview = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
                topics.append(content_preview)
        
        topics_str = "; ".join(topics[:5]) if topics else "General conversation"
        
        return f"""### {date_str}

- Session ID: `{self.session_id}`
- Messages: {len(self.messages)} ({sum(1 for m in self.messages if m.role == 'user')} user, {sum(1 for m in self.messages if m.role == 'assistant')} assistant)
- Topics: {topics_str}
"""
    
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
            'last_activity': self.messages[-1].timestamp if self.messages else None,
            # 压缩统计
            'compression_enabled': self.config.enable_compression,
            'compression_records': len(self._compression_records),
            'total_messages_preserved': sum(
                r.original_count - r.compressed_count
                for r in self._compression_records
            ) if self.config.preserve_compressed_history else 0,
            'lineage': {
                'has_parent': self._parent_session_id is not None,
                'parent_session_id': self._parent_session_id,
                'child_count': len(self._child_session_ids)
            }
        }
        return stats


class SessionManager:
    """
    Manages multiple sessions.
    
    Provides session creation, retrieval, and lifecycle management.
    """
    
    def __init__(self, config: Optional[SessionConfig] = None):
        ensure_workspace_dirs()
        self.config = config or SessionConfig()
        self.sessions: Dict[str, Session] = {}
        self.store = FileSessionStore(self.config.history_path)
        self.logger = get_decision_logger(self.__class__.__name__)
        self._enable_detailed_logs = self.config.enable_detailed_logs
    
    def create_session(self, session_id: Optional[str] = None, enable_detailed_logs: Optional[bool] = None) -> Session:
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
        
        if enable_detailed_logs is not None:
            session_config = SessionConfig(
                max_history_length=self.config.max_history_length,
                auto_save_interval=self.config.auto_save_interval,
                enable_persistence=self.config.enable_persistence,
                history_path=self.config.history_path,
                enable_detailed_logs=enable_detailed_logs
            )
        else:
            session_config = self.config
        
        session = Session(session_id, session_config)
        self.sessions[session_id] = session
        self.logger.info(f"Created new session: {session_id}")
        
        return session
    
    def _generate_session_id(self) -> str:
        """Generate a date-based session ID: YYYYMMDD_HHMMSS_<random>"""
        import uuid
        from datetime import datetime
        now = datetime.now()
        date_part = now.strftime("%Y%m%d_%H%M%S")
        random_part = str(uuid.uuid4())[:6]
        return f"{date_part}_{random_part}"
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get an existing session.
        
        Args:
            session_id: Session ID to retrieve
            
        Returns:
            Session instance or None if not found
        """
        if session_id in self.sessions:
            return self.sessions[session_id]
        
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
        in_memory = set(self.sessions.keys())
        stored = set(self.store.list_sessions())
        return list(in_memory.union(stored))
    
    def list_sessions_by_date(self) -> Dict[str, List[str]]:
        """List all sessions grouped by date."""
        return self.store.list_sessions_by_date()
    
    def get_today_sessions(self) -> List[str]:
        """List sessions from today."""
        return self.store.list_today_sessions()
    
    def get_latest_today_session(self) -> Optional[Session]:
        """
        Get the most recent session from today.
        
        Returns:
            Session instance or None if no session exists today
        """
        latest_session_id = self.store.get_latest_today_session()
        if latest_session_id:
            return self.get_session(latest_session_id)
        return None
    
    def get_or_create_today_session(self) -> Session:
        """
        Get today's session or create a new one.
        
        If a session from today exists, return it.
        Otherwise, create a new session for today.
        
        Returns:
            Session instance
        """
        existing = self.get_latest_today_session()
        if existing:
            self.logger.info(f"Continuing today's session: {existing.session_id}")
            return existing
        
        session = self.create_session()
        self.logger.info(f"Created new session for today: {session.session_id}")
        return session
    
    def sync_to_daily_summary(self, workspace_path: str = None):
        """
        生成并同步最近会话的每日摘要。

        会话摘要与 MemoryStore 的用户记忆分离：
        - MemoryStore (MEMORY.md): 用户显式添加的记忆
        - Session (daily_summary.md): 自动生成的会话摘要

        Args:
            workspace_path: 摘要文件路径。如果为 None，使用默认位置。

        Returns:
            摘要文件路径
        """
        import os
        from datetime import datetime, timedelta

        if workspace_path is None:
            # 写入独立文件，避免与 MemoryStore 冲突
            workspace_path = os.path.join(
                os.path.expanduser("~"),
                ".handsome_agent",
                "sessions",
                "daily_summary.md"
            )

        sessions_by_date = self.list_sessions_by_date()

        summary_lines = ["# 会话每日摘要", "", "## 最近 7 天会话", ""]

        today = datetime.now()
        for i in range(7):
            date = today - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")

            if date_str in sessions_by_date:
                sessions = sessions_by_date[date_str]
                for session_id in sessions[:3]:  # 每天最多 3 个会话
                    session = self.get_session(session_id)
                    if session and session.messages:
                        summary_lines.append(session.get_memory_content())
                        summary_lines.append("")

        summary_content = "\n".join(summary_lines)

        os.makedirs(os.path.dirname(workspace_path), exist_ok=True)
        with open(workspace_path, 'w', encoding='utf-8') as f:
            f.write(summary_content)

        self.logger.info(f"Synced sessions to daily_summary.md: {workspace_path}")
        return workspace_path

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
            if self._enable_detailed_logs:
                self.logger.info(f"Cleaned up inactive session: {session_id}")


session_manager = SessionManager()