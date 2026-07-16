#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hermes State Module - SQLite Session/State Database

This module provides persistent session management using SQLite
with FTS5 for full-text search capabilities.

Enhanced features (inspired by Hermes Agent):
- Lineage deduplication (parent_session_id support)
- Bookends view (anchored message context)
- Three search modes: DISCOVERY / SCROLL / BROWSE
- Trigram FTS5 for CJK support
"""

import sqlite3
import json
import os
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from common.config import AGENT_Z_HOME, ensure_workspace_dirs
from common.logging_manager import get_system_logger


@dataclass
class SessionData:
    """Data structure for session information."""
    id: str
    created_at: float
    updated_at: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_session_id: Optional[str] = None  # 血缘关系
    source: str = "cli"  # cli, tool, gateway


@dataclass
class MessageData:
    """Data structure for message information."""
    id: str
    session_id: str
    role: str
    content: str
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    tool_call_id: Optional[str] = None
    tool_result: Optional[Dict[str, Any]] = None


@dataclass
class SearchHit:
    """Search result with snippet and context."""
    session_id: str
    message_id: str
    role: str
    content: str
    timestamp: float
    snippet: str
    bookend_start: List[Dict] = field(default_factory=list)
    bookend_end: List[Dict] = field(default_factory=list)
    messages: List[Dict] = field(default_factory=list)  # Window around match
    lineage_root: Optional[str] = None


class HermesState:
    """
    SQLite-based session and state management with FTS5 support.
    
    Key features:
    - Session persistence
    - Full-text search across messages
    - Message history management
    - Metadata storage
    """
    
    def __init__(self, db_path: Optional[str] = None):
        ensure_workspace_dirs()
        self.db_path = db_path or str(AGENT_Z_HOME / "hermes_state.db")
        self._ensure_directory()
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self._init_schema()
        self.logger = get_system_logger(self.__class__.__name__)
    
    def _ensure_directory(self):
        """Ensure the directory for the database exists."""
        directory = os.path.dirname(self.db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
    
    def _init_schema(self):
        """Initialize database schema with lineage support."""
        cursor = self.conn.cursor()
        
        # Sessions table with lineage support
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                parent_session_id TEXT,
                source TEXT DEFAULT 'cli'
            )
        """)
        
        # Create parent index for lineage traversal
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_parent 
            ON sessions(parent_session_id)
        """)
        
        # Messages table with FTS5 for full-text search
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS messages 
            USING fts5(
                id UNINDEXED,
                session_id,
                role,
                content,
                timestamp UNINDEXED,
                metadata UNINDEXED,
                tool_call_id UNINDEXED,
                tool_result UNINDEXED
            )
        """)
        
        # Trigram FTS5 for CJK substring search
        try:
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts_trigram 
                USING fts5(
                    id UNINDEXED,
                    content,
                    tokenize='trigram'
                )
            """)
        except sqlite3.Error:
            pass  # Trigram may not be available on all SQLite versions
        
        # Index on session_id for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_session_id 
            ON messages(session_id)
        """)
        
        # Index on timestamp for ordering
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_timestamp 
            ON messages(timestamp)
        """)
        
        self.conn.commit()
    
    def _serialize_metadata(self, metadata: Dict[str, Any]) -> str:
        """Serialize metadata to JSON string."""
        return json.dumps(metadata, ensure_ascii=False)
    
    def _deserialize_metadata(self, metadata_str: Optional[str]) -> Dict[str, Any]:
        """Deserialize metadata from JSON string."""
        if not metadata_str:
            return {}
        try:
            return json.loads(metadata_str)
        except json.JSONDecodeError:
            return {}
    
    # Session operations
    def create_session(
        self,
        session_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        parent_session_id: Optional[str] = None,
        source: str = "cli"
    ) -> bool:
        """
        Create a new session with optional lineage.
        
        Args:
            session_id: Unique session ID
            metadata: Optional session metadata
            parent_session_id: Parent session for lineage tracking
            source: Session source (cli, tool, gateway)
        
        Returns:
            True if created successfully
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (id, created_at, updated_at, metadata, parent_session_id, source)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                datetime.now().timestamp(),
                datetime.now().timestamp(),
                self._serialize_metadata(metadata),
                parent_session_id,
                source
            ))
            self.conn.commit()
            self.logger.debug(f"Created session: {session_id} (parent={parent_session_id})")
            return True
        except sqlite3.Error as e:
            self.logger.error(f"Error creating session: {e}")
            return False
    
    def get_session(self, session_id: str) -> Optional[SessionData]:
        """
        Get session by ID.
        
        Args:
            session_id: The session ID
        
        Returns:
            SessionData or None if not found
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        return SessionData(
            id=row[0],
            created_at=row[1],
            updated_at=row[2],
            metadata=self._deserialize_metadata(row[3])
        )
    
    def update_session(self, session_id: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update session metadata.
        
        Args:
            session_id: The session ID
            metadata: New metadata to set
        
        Returns:
            True if updated successfully
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                UPDATE sessions 
                SET updated_at = ?, metadata = ? 
                WHERE id = ?
            """, (datetime.now().timestamp(), self._serialize_metadata(metadata), session_id))
            self.conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            self.logger.error(f"Error updating session: {e}")
            return False
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and all its messages.
        
        Args:
            session_id: The session ID
        
        Returns:
            True if deleted successfully
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            self.conn.commit()
            self.logger.debug(f"Deleted session: {session_id}")
            return True
        except sqlite3.Error as e:
            self.logger.error(f"Error deleting session: {e}")
            return False
    
    def list_sessions(self) -> List[str]:
        """
        List all session IDs.
        
        Returns:
            List of session IDs
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM sessions ORDER BY created_at DESC")
        return [row[0] for row in cursor.fetchall()]
    
    # Message operations
    def add_message(self, session_id: str, role: str, content: str, 
                    metadata: Optional[Dict[str, Any]] = None,
                    tool_call_id: Optional[str] = None,
                    tool_result: Optional[Dict[str, Any]] = None) -> bool:
        """
        Add a message to a session.
        
        Args:
            session_id: The session ID
            role: Message role (user, assistant, system, tool)
            content: Message content
            metadata: Optional metadata
            tool_call_id: Optional tool call ID
            tool_result: Optional tool result
        
        Returns:
            True if added successfully
        """
        try:
            cursor = self.conn.cursor()
            message_id = f"msg_{datetime.now().timestamp()}"
            
            cursor.execute("""
                INSERT INTO messages 
                (id, session_id, role, content, timestamp, metadata, tool_call_id, tool_result)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (message_id, session_id, role, content, datetime.now().timestamp(),
                  self._serialize_metadata(metadata), tool_call_id, 
                  self._serialize_metadata(tool_result)))
            
            # Update session's updated_at
            cursor.execute("""
                UPDATE sessions SET updated_at = ? WHERE id = ?
            """, (datetime.now().timestamp(), session_id))
            
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            self.logger.error(f"Error adding message: {e}")
            return False
    
    def get_messages(self, session_id: str, limit: Optional[int] = None) -> List[MessageData]:
        """
        Get messages for a session.
        
        Args:
            session_id: The session ID
            limit: Maximum number of messages to return
        
        Returns:
            List of MessageData objects
        """
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp ASC"
        params = [session_id]
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor.execute(query, params)
        
        messages = []
        for row in cursor.fetchall():
            messages.append(MessageData(
                id=row[0],
                session_id=row[1],
                role=row[2],
                content=row[3],
                timestamp=row[4],
                metadata=self._deserialize_metadata(row[5]),
                tool_call_id=row[6],
                tool_result=self._deserialize_metadata(row[7])
            ))
        
        return messages
    
    def search_messages(self, query: str, session_id: Optional[str] = None, 
                       limit: int = 20) -> List[MessageData]:
        """
        Search messages using full-text search.
        
        Args:
            query: Search query string
            session_id: Optional session filter
            limit: Maximum number of results
        
        Returns:
            List of matching MessageData objects
        """
        cursor = self.conn.cursor()
        
        if session_id:
            cursor.execute("""
                SELECT * FROM messages 
                WHERE session_id = ? AND content MATCH ? 
                ORDER BY rank 
                LIMIT ?
            """, (session_id, query, limit))
        else:
            cursor.execute("""
                SELECT * FROM messages 
                WHERE content MATCH ? 
                ORDER BY rank 
                LIMIT ?
            """, (query, limit))
        
        messages = []
        for row in cursor.fetchall():
            messages.append(MessageData(
                id=row[0],
                session_id=row[1],
                role=row[2],
                content=row[3],
                timestamp=row[4],
                metadata=self._deserialize_metadata(row[5]),
                tool_call_id=row[6],
                tool_result=self._deserialize_metadata(row[7])
            ))
        
        return messages
    
    def delete_messages(self, session_id: str) -> bool:
        """
        Delete all messages for a session.
        
        Args:
            session_id: The session ID
        
        Returns:
            True if deleted successfully
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            self.logger.error(f"Error deleting messages: {e}")
            return False
    
    def get_message_count(self, session_id: str) -> int:
        """
        Get the number of messages in a session.
        
        Args:
            session_id: The session ID
        
        Returns:
            Number of messages
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM messages WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        return row[0] if row else 0
    
    # =============================================================================
    # Lineage & Advanced Search Methods
    # =============================================================================
    
    def resolve_lineage_root(self, session_id: str) -> str:
        """
        Resolve session to its lineage root by following parent_session_id chain.
        
        Args:
            session_id: Starting session ID
        
        Returns:
            Root session ID (the one with no parent)
        """
        visited = set()
        cur = session_id
        while cur and cur not in visited:
            visited.add(cur)
            session = self.get_session(cur)
            if not session:
                break
            parent = session.parent_session_id
            if not parent:
                break
            cur = parent
        return cur
    
    def get_lineage_sessions(self, session_id: str) -> List[SessionData]:
        """
        Get all sessions in the lineage (root + all children).
        
        Args:
            session_id: Root or child session ID
        
        Returns:
            List of SessionData in the lineage
        """
        root = self.resolve_lineage_root(session_id)
        cursor = self.conn.cursor()
        
        # Get all sessions that eventually trace back to this root
        cursor.execute("""
            WITH RECURSIVE lineage AS (
                SELECT * FROM sessions WHERE id = ?
                UNION ALL
                SELECT s.* FROM sessions s
                JOIN lineage l ON s.parent_session_id = l.id
            )
            SELECT * FROM lineage
        """, (root,))
        
        sessions = []
        for row in cursor.fetchall():
            sessions.append(SessionData(
                id=row[0],
                created_at=row[1],
                updated_at=row[2],
                metadata=self._deserialize_metadata(row[3]),
                parent_session_id=row[4] if len(row) > 4 else None,
                source=row[5] if len(row) > 5 else "cli"
            ))
        return sessions
    
    def get_anchored_view(
        self,
        session_id: str,
        around_message_id: int,
        window: int = 5,
        bookend: int = 3
    ) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        Get anchored view with bookends and window around a message.
        
        Args:
            session_id: Session to view
            around_message_id: Message ID to anchor on
            window: Number of messages around the anchor (±window)
            bookend: Number of messages at session start/end
        
        Returns:
            Tuple of (bookend_start, messages_window, bookend_end)
        """
        cursor = self.conn.cursor()
        
        # Get anchor message timestamp
        cursor.execute("SELECT timestamp FROM messages WHERE id = ?", (around_message_id,))
        row = cursor.fetchone()
        if not row:
            return [], [], []
        anchor_ts = row[0]
        
        # Bookend start: first N user/assistant messages at session beginning
        cursor.execute("""
            SELECT id, session_id, role, content, timestamp
            FROM messages
            WHERE session_id = ? AND length(content) > 0
            ORDER BY timestamp ASC
            LIMIT ?
        """, (session_id, bookend))
        bookend_start = [
            {"id": r[0], "session_id": r[1], "role": r[2], "content": r[3], "timestamp": r[4]}
            for r in cursor.fetchall()
            if r[2] in ("user", "assistant")
        ]
        
        # Window: messages around anchor (filter tool noise)
        cursor.execute("""
            SELECT id, session_id, role, content, timestamp
            FROM messages
            WHERE session_id = ?
            ORDER BY timestamp ASC
        """, (session_id,))
        
        all_msgs = [
            {"id": r[0], "session_id": r[1], "role": r[2], "content": r[3], "timestamp": r[4]}
            for r in cursor.fetchall()
        ]
        
        # Find anchor index and extract window
        anchor_idx = -1
        for i, msg in enumerate(all_msgs):
            if msg["id"] == around_message_id:
                anchor_idx = i
                break
        
        if anchor_idx >= 0:
            start_idx = max(0, anchor_idx - window)
            end_idx = min(len(all_msgs), anchor_idx + window + 1)
            messages_window = all_msgs[start_idx:end_idx]
        else:
            messages_window = []
        
        # Bookend end: last N user/assistant messages
        cursor.execute("""
            SELECT id, session_id, role, content, timestamp
            FROM messages
            WHERE session_id = ? AND length(content) > 0
            ORDER BY timestamp DESC
            LIMIT ?
        """, (session_id, bookend))
        bookend_end = [
            {"id": r[0], "session_id": r[1], "role": r[2], "content": r[3], "timestamp": r[4]}
            for r in cursor.fetchall()
            if r[2] in ("user", "assistant")
        ]
        bookend_end.reverse()  # Restore chronological order
        
        return bookend_start, messages_window, bookend_end
    
    def search_messages_advanced(
        self,
        query: str,
        exclude_sources: Optional[List[str]] = None,
        role_filter: Optional[str] = None,
        current_lineage_root: Optional[str] = None,
        limit: int = 5,
        sort: str = "rank"
    ) -> List[SearchHit]:
        """
        Advanced FTS5 search with lineage deduplication.
        
        Args:
            query: FTS5 query string
            exclude_sources: Sources to exclude (e.g., ["tool"])
            role_filter: Filter by role
            current_lineage_root: Current session lineage root to skip
            limit: Number of results
            sort: Sort order (rank, newest, oldest)
        
        Returns:
            List of SearchHit with bookends and window context
        """
        cursor = self.conn.cursor()
        
        # Build FTS5 query with optional role filter
        fts_query = query
        if role_filter:
            fts_query = f'{query} AND role:{role_filter}'
        
        # Determine sort order
        order_clause = "rank"
        if sort == "newest":
            order_clause = "m.timestamp DESC"
        elif sort == "oldest":
            order_clause = "m.timestamp ASC"
        
        # Search with lineage info
        sql = f"""
            SELECT
                m.id, m.session_id, m.role, m.content, m.timestamp,
                snippet(messages, 0, '>>>', '<<<', '...', 40) AS snippet,
                s.parent_session_id
            FROM messages
            JOIN messages m ON messages.rowid = m.id
            JOIN sessions s ON s.id = m.session_id
            WHERE messages MATCH ?
        """
        
        params = [fts_query]
        
        if exclude_sources:
            placeholders = ",".join(["?"] * len(exclude_sources))
            sql += f" AND s.source NOT IN ({placeholders})"
            params.extend(exclude_sources)
        
        sql += f" ORDER BY {order_clause} LIMIT ?"
        params.append(limit * 3)  # Fetch more for deduplication
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        # Lineage deduplication
        seen_lineages = {}
        results = []
        
        for row in rows:
            msg_id, sid, role, content, ts, snippet, parent_sid = row
            
            # Resolve to lineage root
            lineage_root = self.resolve_lineage_root(sid)
            
            # Skip current session lineage
            if current_lineage_root and lineage_root == current_lineage_root:
                continue
            
            # Skip tool sources for cleaner results
            if role == "tool":
                continue
            
            # Deduplicate by lineage root
            if lineage_root not in seen_lineages:
                seen_lineages[lineage_root] = {
                    "session_id": sid,
                    "message_id": msg_id,
                    "role": role,
                    "content": content,
                    "timestamp": ts,
                    "snippet": snippet,
                    "lineage_root": lineage_root
                }
                
                if len(seen_lineages) >= limit:
                    break
        
        # Build SearchHit with bookends
        for lineage_info in seen_lineages.values():
            sid = lineage_info["session_id"]
            msg_id = lineage_info["message_id"]
            
            # Convert msg_id to integer for get_anchored_view
            try:
                msg_id_int = int(msg_id.split("_")[-1]) if "_" in msg_id else int(msg_id)
            except (ValueError, IndexError):
                msg_id_int = 0
            
            bookend_start, messages_window, bookend_end = self.get_anchored_view(
                sid, msg_id_int, window=3, bookend=2
            )
            
            results.append(SearchHit(
                session_id=sid,
                message_id=msg_id,
                role=lineage_info["role"],
                content=lineage_info["content"],
                timestamp=lineage_info["timestamp"],
                snippet=lineage_info["snippet"],
                bookend_start=bookend_start,
                bookend_end=bookend_end,
                messages=messages_window,
                lineage_root=lineage_info["lineage_root"]
            ))
        
        return results
    
    def list_recent_sessions(
        self,
        limit: int = 10,
        exclude_sources: Optional[List[str]] = None,
        current_lineage_root: Optional[str] = None
    ) -> List[Dict]:
        """
        List recent sessions for BROWSE mode.
        
        Args:
            limit: Number of sessions to return
            exclude_sources: Sources to exclude
            current_lineage_root: Current session lineage to skip
        
        Returns:
            List of session info dicts
        """
        cursor = self.conn.cursor()
        
        sql = """
            SELECT s.id, s.created_at, s.updated_at, s.metadata, s.parent_session_id,
                   COUNT(m.id) as msg_count
            FROM sessions s
            LEFT JOIN messages m ON m.session_id = s.id
            WHERE s.parent_session_id IS NULL
        """
        
        params = []
        
        if exclude_sources:
            placeholders = ",".join(["?"] * len(exclude_sources))
            sql += f" AND s.source NOT IN ({placeholders})"
            params.extend(exclude_sources)
        
        sql += " GROUP BY s.id ORDER BY s.updated_at DESC LIMIT ?"
        params.append(limit + 5)
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            sid, created, updated, metadata, parent, msg_count = row
            lineage_root = self.resolve_lineage_root(sid)
            
            # Skip current session lineage
            if current_lineage_root and lineage_root == current_lineage_root:
                continue
            
            # Skip child sessions (they appear under their parent)
            if parent is not None:
                continue
            
            # Get preview from first message
            cursor.execute("""
                SELECT content FROM messages
                WHERE session_id = ? AND length(content) > 0 AND role IN ('user', 'assistant')
                ORDER BY timestamp ASC LIMIT 1
            """, (sid,))
            preview_row = cursor.fetchone()
            preview = preview_row[0][:100] if preview_row else ""
            
            results.append({
                "session_id": sid,
                "title": self._get_session_title(sid, metadata),
                "preview": preview,
                "last_active": updated,
                "message_count": msg_count,
                "created_at": created
            })
            
            if len(results) >= limit:
                break
        
        return results
    
    def _get_session_title(self, session_id: str, metadata: Optional[Dict]) -> str:
        """Extract or generate session title."""
        if metadata and "title" in metadata:
            return metadata["title"]
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT content FROM messages
            WHERE session_id = ? AND role = 'user'
            ORDER BY timestamp ASC LIMIT 1
        """, (session_id,))
        row = cursor.fetchone()
        if row:
            title = row[0][:50]
            if len(row[0]) > 50:
                title += "..."
            return title
        return f"Session {session_id[:8]}"
    
    def close(self):
        """Close the database connection."""
        self.conn.close()
