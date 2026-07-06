#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite Session Store for Handsome Agent.

Provides persistent session storage with FTS5 full-text search.
Stores session metadata, full message history, and model configuration.

Key design decisions:
- WAL mode for concurrent readers + one writer
- FTS5 virtual table for fast text search across all session messages
- Session source tagging ('cli', 'http', 'openai', etc.) for filtering
- Declarative schema with column reconciliation (add columns automatically)
"""

import json
import logging
import random
import re
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar

from common.config import get_sessions_dir

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _get_default_db_path() -> Path:
    """Get the default database path from config or home directory."""
    try:
        sessions_dir = get_sessions_dir()
        if sessions_dir:
            return Path(sessions_dir) / "sessions.db"
    except Exception:
        pass
    home = Path.home() / ".handsome_agent"
    return home / "sessions.db"


SCHEMA_VERSION = 1

_WAL_INCOMPAT_MARKERS = (
    "locking protocol",
    "not authorized",
    "disk i/o error",
)

_wal_fallback_warned_paths: set = set()
_wal_fallback_warned_lock = threading.Lock()


def apply_wal_with_fallback(
    conn: sqlite3.Connection,
    *,
    db_label: str = "sessions.db",
) -> str:
    """Set journal_mode=WAL, falling back to DELETE on failure.

    Returns the journal mode actually set ("wal" or "delete").

    On WAL-incompatible filesystems (NFS, SMB, some FUSE), SQLite raises
    OperationalError("locking protocol") when setting WAL. We fall back to DELETE
    mode and log one WARNING.
    """
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        return "wal"
    except sqlite3.OperationalError as exc:
        msg = str(exc).lower()
        if not any(marker in msg for marker in _WAL_INCOMPAT_MARKERS):
            raise
        _log_wal_fallback_once(db_label, exc)
        conn.execute("PRAGMA journal_mode=DELETE")
        return "delete"


def _log_wal_fallback_once(db_label: str, exc: Exception) -> None:
    """Log a single WARNING per (process, db_label) about WAL fallback."""
    with _wal_fallback_warned_lock:
        if db_label in _wal_fallback_warned_paths:
            return
        _wal_fallback_warned_paths.add(db_label)
    logger.warning(
            "%s: WAL journal_mode unsupported on this filesystem (%s) — "
            "falling back to journal_mode=DELETE. "
            "See https://www.sqlite.org/wal.html for details.",
            db_label,
            exc,
        )


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    user_id TEXT,
    model TEXT,
    model_config TEXT,
    system_prompt TEXT,
    parent_session_id TEXT,
    started_at REAL NOT NULL,
    ended_at REAL,
    end_reason TEXT,
    message_count INTEGER DEFAULT 0,
    tool_call_count INTEGER DEFAULT 0,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    title TEXT,
    FOREIGN KEY (parent_session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    role TEXT NOT NULL,
    content TEXT,
    tool_call_id TEXT,
    tool_calls TEXT,
    tool_name TEXT,
    timestamp REAL NOT NULL,
    token_count INTEGER,
    finish_reason TEXT,
    reasoning TEXT
);

CREATE INDEX IF NOT EXISTS idx_sessions_source ON sessions(source);
CREATE INDEX IF NOT EXISTS idx_sessions_parent ON sessions(parent_session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, timestamp);
"""

FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    content
);

CREATE TRIGGER IF NOT EXISTS messages_fts_insert AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts(rowid, content) VALUES (
        new.id,
        COALESCE(new.content, '') || ' ' || COALESCE(new.tool_name, '') || ' ' || COALESCE(new.tool_calls, '')
    );
END;

CREATE TRIGGER IF NOT EXISTS messages_fts_delete AFTER DELETE ON messages BEGIN
    DELETE FROM messages_fts WHERE rowid = old.id;
END;

CREATE TRIGGER IF NOT EXISTS messages_fts_update AFTER UPDATE ON messages BEGIN
    DELETE FROM messages_fts WHERE rowid = old.id;
    INSERT INTO messages_fts(rowid, content) VALUES (
        new.id,
        COALESCE(new.content, '') || ' ' || COALESCE(new.tool_name, '') || ' ' || COALESCE(new.tool_calls, '')
    );
END;
"""

FTS_TRIGRAM_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts_trigram USING fts5(
    content,
    tokenize='trigram'
);

CREATE TRIGGER IF NOT EXISTS messages_fts_trigram_insert AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts_trigram(rowid, content) VALUES (
        new.id,
        COALESCE(new.content, '') || ' ' || COALESCE(new.tool_name, '') || ' ' || COALESCE(new.tool_calls, '')
    );
END;

CREATE TRIGGER IF NOT EXISTS messages_fts_trigram_delete AFTER DELETE ON messages BEGIN
    DELETE FROM messages_fts_trigram WHERE rowid = old.id;
END;

CREATE TRIGGER IF NOT EXISTS messages_fts_trigram_update AFTER UPDATE ON messages BEGIN
    DELETE FROM messages_fts_trigram WHERE rowid = old.id;
    INSERT INTO messages_fts_trigram(rowid, content) VALUES (
        new.id,
        COALESCE(new.content, '') || ' ' || COALESCE(new.tool_name, '') || ' ' || COALESCE(new.tool_calls, '')
    );
END;
"""


class SessionStore:
    """
    SQLite-backed session storage with FTS5 search.

    Thread-safe for the common pattern (multiple reader threads,
    single writer via WAL mode). Each method opens its own cursor.
    """

    _WRITE_MAX_RETRIES = 15
    _WRITE_RETRY_MIN_S = 0.020
    _WRITE_RETRY_MAX_S = 0.150
    _CHECKPOINT_EVERY_N_WRITES = 50

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else _get_default_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._write_count = 0
        self._conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            timeout=1.0,
            isolation_level=None,
        )
        self._conn.row_factory = sqlite3.Row
        apply_wal_with_fallback(self._conn, db_label="sessions.db")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    def _execute_write(self, fn: Callable[[sqlite3.Connection], T]) -> T:
        """Execute a write transaction with BEGIN IMMEDIATE and jitter retry.

        *fn* receives the connection and should perform INSERT/UPDATE/DELETE
        statements. The caller must NOT call commit() — that's handled here.
        """
        last_err: Optional[Exception] = None
        for attempt in range(self._WRITE_MAX_RETRIES):
            try:
                with self._lock:
                    self._conn.execute("BEGIN IMMEDIATE")
                    try:
                        result = fn(self._conn)
                        self._conn.commit()
                    except BaseException:
                        try:
                            self._conn.rollback()
                        except Exception:
                            pass
                        raise
                self._write_count += 1
                if self._write_count % self._CHECKPOINT_EVERY_N_WRITES == 0:
                    self._try_wal_checkpoint()
                return result
            except sqlite3.OperationalError as exc:
                err_msg = str(exc).lower()
                if "locked" in err_msg or "busy" in err_msg:
                    last_err = exc
                    if attempt < self._WRITE_MAX_RETRIES - 1:
                        jitter = random.uniform(
                            self._WRITE_RETRY_MIN_S,
                            self._WRITE_RETRY_MAX_S,
                        )
                        time.sleep(jitter)
                        continue
                raise
        raise last_err or sqlite3.OperationalError(
            "database is locked after max retries"
        )

    def _try_wal_checkpoint(self) -> None:
        """Best-effort PASSIVE WAL checkpoint."""
        try:
            with self._lock:
                result = self._conn.execute(
                    "PRAGMA wal_checkpoint(PASSIVE)"
                ).fetchone()
                if result and result[1] > 0:
                    logger.debug(
                        "WAL checkpoint: %d/%d pages checkpointed",
                        result[2], result[1],
                    )
        except Exception:
            pass

    def close(self):
        """Close the database connection."""
        with self._lock:
            if self._conn:
                try:
                    self._conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
                except Exception:
                    pass
                self._conn.close()
                self._conn = None

    @staticmethod
    def _parse_schema_columns(schema_sql: str) -> Dict[str, Dict[str, str]]:
        """Extract expected columns per table from SCHEMA_SQL."""
        ref = sqlite3.connect(":memory:")
        try:
            ref.executescript(schema_sql)
            table_columns: Dict[str, Dict[str, str]] = {}
            for (tbl,) in ref.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall():
                cols: Dict[str, str] = {}
                for row in ref.execute(
                    f'PRAGMA table_info("{tbl}")'
                ).fetchall():
                    col_name = row[1]
                    col_type = row[2] or ""
                    notnull = row[3]
                    default = row[4]
                    pk = row[5]
                    parts = [col_type] if col_type else []
                    if notnull and not pk:
                        parts.append("NOT NULL")
                    if default is not None:
                        parts.append(f"DEFAULT {default}")
                    cols[col_name] = " ".join(parts)
                table_columns[tbl] = cols
            return table_columns
        finally:
            ref.close()

    def _reconcile_columns(self, cursor: sqlite3.Cursor) -> None:
        """Ensure live tables have every column declared in SCHEMA_SQL."""
        expected = self._parse_schema_columns(SCHEMA_SQL)
        for table_name, declared_cols in expected.items():
            try:
                rows = cursor.execute(
                    f'PRAGMA table_info("{table_name}")'
                ).fetchall()
            except sqlite3.OperationalError:
                continue
            live_cols = set()
            for row in rows:
                name = row[1] if isinstance(row, (tuple, list)) else row["name"]
                live_cols.add(name)

            for col_name, col_type in declared_cols.items():
                if col_name not in live_cols:
                    safe_name = col_name.replace('"', '""')
                    try:
                        cursor.execute(
                            f'ALTER TABLE "{table_name}" ADD COLUMN "{safe_name}" {col_type}'
                        )
                    except sqlite3.OperationalError as exc:
                        logger.debug(
                            "reconcile %s.%s: %s", table_name, col_name, exc,
                        )

    def _init_schema(self):
        """Create tables and FTS if they don't exist, reconcile columns."""
        cursor = self._conn.cursor()

        tables_sql = "\n".join(
            line for line in SCHEMA_SQL.split("\n")
            if not line.strip().startswith("CREATE INDEX")
        )
        cursor.executescript(tables_sql)
        self._reconcile_columns(cursor)

        indexes_sql = "\n".join(
            line for line in SCHEMA_SQL.split("\n")
            if line.strip().startswith("CREATE INDEX")
        )
        try:
            cursor.executescript(indexes_sql)
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("SELECT version FROM schema_version LIMIT 1")
            row = cursor.fetchone()
            if row is None:
                cursor.execute(
                    "INSERT INTO schema_version (version) VALUES (?)",
                    (SCHEMA_VERSION,),
                )
            else:
                current_version = row["version"] if isinstance(row, sqlite3.Row) else row[0]
                if current_version < SCHEMA_VERSION:
                    cursor.execute(
                        "UPDATE schema_version SET version = ?",
                        (SCHEMA_VERSION,),
                    )
        except Exception:
            pass

        try:
            cursor.execute("SELECT * FROM messages_fts LIMIT 0")
        except sqlite3.OperationalError:
            cursor.executescript(FTS_SQL)

        try:
            cursor.execute("SELECT * FROM messages_fts_trigram LIMIT 0")
        except sqlite3.OperationalError:
            cursor.executescript(FTS_TRIGRAM_SQL)

        self._conn.commit()

    # =========================================================================
    # Session lifecycle
    # =========================================================================

    def create_session(
        self,
        session_id: str,
        source: str,
        model: str = None,
        model_config: Dict[str, Any] = None,
        system_prompt: str = None,
        user_id: str = None,
        parent_session_id: str = None,
    ) -> str:
        """Create a new session record. Returns the session_id."""
        def _do(conn):
            conn.execute(
                """INSERT OR IGNORE INTO sessions (
                    id, source, user_id, model, model_config,
                    system_prompt, parent_session_id, started_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    source,
                    user_id,
                    model,
                    json.dumps(model_config) if model_config else None,
                    system_prompt,
                    parent_session_id,
                    time.time(),
                ),
            )
        self._execute_write(_do)
        return session_id

    def end_session(self, session_id: str, end_reason: str) -> None:
        """Mark a session as ended."""
        def _do(conn):
            conn.execute(
                "UPDATE sessions SET ended_at = ?, end_reason = ? "
                "WHERE id = ? AND ended_at IS NULL",
                (time.time(), end_reason, session_id),
            )
        self._execute_write(_do)

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a session by ID."""
        with self._lock:
            cursor = self._conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            )
            row = cursor.fetchone()
        return dict(row) if row else None

    def list_sessions(
        self,
        source: str = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List sessions with pagination."""
        where_clauses = []
        params = []
        if source:
            where_clauses.append("source = ?")
            params.append(source)

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        with self._lock:
            cursor = self._conn.execute(
                f"""SELECT s.*,
                    (SELECT content FROM messages m
                     WHERE m.session_id = s.id AND m.role = 'user'
                     ORDER BY m.timestamp ASC LIMIT 1) as preview
                    FROM sessions s
                    {where_sql}
                    ORDER BY started_at DESC
                    LIMIT ? OFFSET ?""",
                params + [limit, offset],
            )
            rows = cursor.fetchall()
        return [dict(r) for r in rows]

    def set_session_title(self, session_id: str, title: str) -> bool:
        """Set or update a session's title. Returns True if successful."""
        def _do(conn):
            cursor = conn.execute(
                "UPDATE sessions SET title = ? WHERE id = ?",
                (title, session_id),
            )
            return cursor.rowcount
        rowcount = self._execute_write(_do)
        return rowcount > 0

    def get_session_title(self, session_id: str) -> Optional[str]:
        """Get the title for a session, or None."""
        with self._lock:
            cursor = self._conn.execute(
                "SELECT title FROM sessions WHERE id = ?", (session_id,)
            )
            row = cursor.fetchone()
        return row["title"] if row else None

    def update_token_counts(
        self,
        session_id: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        model: str = None,
    ) -> None:
        """Increment token counters for a session."""
        self.ensure_session(session_id, "unknown", model=model)
        def _do(conn):
            conn.execute(
                """UPDATE sessions SET
                   input_tokens = input_tokens + ?,
                   output_tokens = output_tokens + ?,
                   model = COALESCE(model, ?)
                   WHERE id = ?""",
                (input_tokens, output_tokens, model, session_id),
            )
        self._execute_write(_do)

    def ensure_session(
        self,
        session_id: str,
        source: str = "unknown",
        model: str = None,
        **kwargs,
    ) -> str:
        """Ensure a session row exists (INSERT OR IGNORE)."""
        self.create_session(session_id, source, model=model, **kwargs)
        return session_id

    # =========================================================================
    # Message management
    # =========================================================================

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str = None,
        tool_call_id: str = None,
        tool_calls: List[Dict[str, Any]] = None,
        tool_name: str = None,
        token_count: int = None,
        finish_reason: str = None,
        reasoning: str = None,
    ) -> int:
        """Add a message to a session. Returns the message ID."""
        tool_calls_json = json.dumps(tool_calls) if tool_calls else None
        ts = time.time()

        def _do(conn):
            cursor = conn.execute(
                """INSERT INTO messages (
                    session_id, role, content, tool_call_id, tool_calls,
                    tool_name, timestamp, token_count, finish_reason, reasoning
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id, role, content, tool_call_id, tool_calls_json,
                    tool_name, ts, token_count, finish_reason, reasoning,
                ),
            )
            msg_id = cursor.lastrowid
            conn.execute(
                "UPDATE sessions SET message_count = message_count + 1 WHERE id = ?",
                (session_id,),
            )
            return msg_id
        return self._execute_write(_do)

    def get_messages(
        self,
        session_id: str,
        limit: int = None,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get messages for a session."""
        limit_sql = ""
        params = [session_id]
        if limit is not None:
            limit_sql = "LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        with self._lock:
            cursor = self._conn.execute(
                f"""SELECT * FROM messages
                    WHERE session_id = ?
                    ORDER BY timestamp ASC
                    {limit_sql}""",
                params,
            )
            rows = cursor.fetchall()
        return [dict(r) for r in rows]

    def get_message_count(self, session_id: str) -> int:
        """Get the number of messages in a session."""
        with self._lock:
            cursor = self._conn.execute(
                "SELECT message_count FROM sessions WHERE id = ?",
                (session_id,),
            )
            row = cursor.fetchone()
        return row["message_count"] if row else 0

    # =========================================================================
    # Full-text search
    # =========================================================================

    def search_messages(
        self,
        query: str,
        session_id: str = None,
        limit: int = 20,
        use_trigram: bool = True,
    ) -> List[Dict[str, Any]]:
        """Search messages using FTS5.

        Args:
            query: Search query string
            session_id: Optional session_id to limit search to
            limit: Maximum number of results
            use_trigram: Use trigram tokenizer for CJK/substring search

        Returns:
            List of matching message dicts with session_id, content, role, bm25 rank
        """
        table = "messages_fts_trigram" if use_trigram else "messages_fts"
        where_clauses = []
        params = []

        where_clauses.append(f"{table} MATCH ?")
        params.append(query)

        if session_id:
            where_clauses.append("m.session_id = ?")
            params.append(session_id)

        where_sql = " AND ".join(where_clauses)

        with self._lock:
            cursor = self._conn.execute(
                f"""SELECT m.*, bm25({table}) as rank
                    FROM messages m
                    JOIN {table} ON {table}.rowid = m.id
                    WHERE {where_sql}
                    ORDER BY rank
                    LIMIT ?""",
                params + [limit],
            )
            rows = cursor.fetchall()
        return [dict(r) for r in rows]

    def search_sessions(
        self,
        query: str,
        source: str = None,
        limit: int = 20,
        use_trigram: bool = True,
    ) -> List[Dict[str, Any]]:
        """Search sessions by message content.

        Returns distinct sessions with matching messages, ordered by relevance.
        """
        table = "messages_fts_trigram" if use_trigram else "messages_fts"
        where_clauses = []
        params = []

        where_clauses.append(f"{table} MATCH ?")
        params.append(query)

        if source:
            where_clauses.append("s.source = ?")
            params.append(source)

        where_sql = " AND ".join(where_clauses)

        with self._lock:
            cursor = self._conn.execute(
                f"""SELECT s.*
                    FROM sessions s
                    WHERE s.id IN (
                        SELECT m.session_id
                        FROM messages m
                        JOIN {table} ON {table}.rowid = m.id
                        WHERE {where_sql}
                    )
                    ORDER BY started_at DESC
                    LIMIT ?""",
                params + [limit],
            )
            rows = cursor.fetchall()
        return [dict(r) for r in rows]
