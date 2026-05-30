#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hermes State Module - SQLite Session/State Database

This module provides persistent session management using SQLite
with FTS5 for full-text search capabilities.

Inspired by Hermes Agent's hermes_state.py
"""

import sqlite3
import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging
from shared.config import HANDSOME_HOME, ensure_workspace_dirs


@dataclass
class SessionData:
    """Data structure for session information."""
    id: str
    created_at: float
    updated_at: float
    metadata: Dict[str, Any] = field(default_factory=dict)


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
        self.db_path = db_path or str(HANDSOME_HOME / "hermes_state.db")
        self._ensure_directory()
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self._init_schema()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _ensure_directory(self):
        """Ensure the directory for the database exists."""
        directory = os.path.dirname(self.db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
    
    def _init_schema(self):
        """Initialize database schema."""
        cursor = self.conn.cursor()
        
        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
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
    def create_session(self, session_id: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Create a new session.
        
        Args:
            session_id: Unique session ID
            metadata: Optional session metadata
        
        Returns:
            True if created successfully
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (id, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?)
            """, (session_id, datetime.now().timestamp(), datetime.now().timestamp(),
                  self._serialize_metadata(metadata)))
            self.conn.commit()
            self.logger.debug(f"Created session: {session_id}")
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
    
    def close(self):
        """Close the database connection."""
        self.conn.close()
