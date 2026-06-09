#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACP Session Manager.

Manages ACP sessions, which are independent of the underlying agent's session.
Sessions are persisted to survive process restarts.
"""

# 🧠 Decision - 💾 Memory - ACP Session Management

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

from common.logging_manager import get_decision_logger

logger = get_decision_logger(__name__)


class SessionStatus(Enum):
    """Session status enumeration."""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"


@dataclass
class SessionState:
    """Represents the state of an ACP session."""
    session_id: str
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    status: SessionStatus = SessionStatus.PENDING
    title: str = ""
    cwd: Optional[str] = None
    history: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    model: Optional[str] = None
    toolsets: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status.value,
            "title": self.title,
            "cwd": self.cwd,
            "history": self.history,
            "metadata": self.metadata,
            "model": self.model,
            "toolsets": self.toolsets,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionState":
        """Create from dictionary."""
        status = SessionStatus(data.get("status", "pending"))
        return cls(
            session_id=data["session_id"],
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            status=status,
            title=data.get("title", ""),
            cwd=data.get("cwd"),
            history=data.get("history", []),
            metadata=data.get("metadata", {}),
            model=data.get("model"),
            toolsets=data.get("toolsets", []),
        )


class SessionManager:
    """
    Manages ACP sessions with persistence.

    Sessions are stored in a JSON file and survive process restarts.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize session manager."""
        if storage_path is None:
            # Try to find a suitable storage location
            home = Path.home()
            storage_path = home / ".handsome_agent" / "acp_sessions.json"

        self._storage_path = storage_path
        self._sessions: Dict[str, SessionState] = {}
        self._lock = Lock()
        self._load_sessions()

    def _load_sessions(self) -> None:
        """Load sessions from storage."""
        if not self._storage_path.exists():
            return

        try:
            with open(self._storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for session_data in data.get("sessions", []):
                    session = SessionState.from_dict(session_data)
                    self._sessions[session.session_id] = session
            logger.info(f"Loaded {len(self._sessions)} sessions from {self._storage_path}")
        except Exception as e:
            logger.warning(f"Failed to load sessions: {e}")

    def _save_sessions(self) -> None:
        """Save sessions to storage."""
        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "sessions": [s.to_dict() for s in self._sessions.values()]
            }
            with open(self._storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save sessions: {e}")

    def create_session(
        self,
        cwd: Optional[str] = None,
        model: Optional[str] = None,
        toolsets: Optional[List[str]] = None,
        title: Optional[str] = None,
    ) -> SessionState:
        """Create a new session."""
        session_id = f"sess_{uuid.uuid4().hex[:16]}"

        # Build title from first message or cwd
        if title:
            session_title = title
        elif cwd:
            session_title = Path(cwd).name or "New session"
        else:
            session_title = "New session"

        session = SessionState(
            session_id=session_id,
            cwd=cwd,
            model=model,
            toolsets=toolsets or [],
            title=session_title,
            status=SessionStatus.ACTIVE,
        )

        with self._lock:
            self._sessions[session_id] = session
            self._save_sessions()

        logger.info(f"Created session: {session_id}")
        return session

    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    def update_session(
        self,
        session_id: str,
        history: Optional[List[Dict[str, Any]]] = None,
        status: Optional[SessionStatus] = None,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Update a session."""
        session = self._sessions.get(session_id)
        if not session:
            return False

        with self._lock:
            if history is not None:
                session.history = history
            if status is not None:
                session.status = status
            if title is not None:
                session.title = title
            if metadata is not None:
                session.metadata.update(metadata)
            session.updated_at = time.time()
            self._save_sessions()

        return True

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Add a message to session history."""
        session = self._sessions.get(session_id)
        if not session:
            return False

        message = {
            "role": role,
            "content": content,
            "timestamp": time.time(),
        }
        if metadata:
            message["metadata"] = metadata

        with self._lock:
            session.history.append(message)
            session.updated_at = time.time()
            # Auto-update title from first user message if not set
            if not session.title and role == "user":
                preview = content[:50] + ("..." if len(content) > 50 else "")
                session.title = preview
            self._save_sessions()

        return True

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id not in self._sessions:
            return False

        with self._lock:
            del self._sessions[session_id]
            self._save_sessions()

        logger.info(f"Deleted session: {session_id}")
        return True

    def list_sessions(
        self,
        limit: int = 50,
        cursor: Optional[str] = None,
    ) -> List[SessionState]:
        """List sessions with pagination."""
        sessions = sorted(
            self._sessions.values(),
            key=lambda s: s.updated_at,
            reverse=True,
        )

        # Apply cursor-based pagination
        if cursor:
            cutoff = float(cursor)
            sessions = [s for s in sessions if s.updated_at < cutoff]

        return sessions[:limit]

    def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get conversation history for a session."""
        session = self._sessions.get(session_id)
        if not session:
            return []
        return session.history

    def clear_old_sessions(self, max_age_seconds: int = 30 * 24 * 3600) -> int:
        """Clear sessions older than max_age_seconds."""
        now = time.time()
        to_delete = [
            sid for sid, s in self._sessions.items()
            if now - s.updated_at > max_age_seconds
        ]

        with self._lock:
            for sid in to_delete:
                del self._sessions[sid]
            if to_delete:
                self._save_sessions()

        if to_delete:
            logger.info(f"Cleared {len(to_delete)} old sessions")

        return len(to_delete)
