#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the SQLite Session Store.
"""

import os
import tempfile
import threading
import time
from pathlib import Path

import pytest

from agent.state.session_store import SessionStore, apply_wal_with_fallback


@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database path."""
    return tmp_path / "test_sessions.db"


@pytest.fixture
def store(temp_db_path):
    """Create a SessionStore with a temporary database."""
    s = SessionStore(db_path=temp_db_path)
    yield s
    s.close()


class TestSessionStoreBasic:
    """Basic session store functionality."""

    def test_create_and_get_session(self, store):
        """Test creating and retrieving a session."""
        session_id = "test-session-1"
        store.create_session(
            session_id=session_id,
            source="cli",
            model="gpt-4",
            model_config={"temperature": 0.7},
            system_prompt="You are helpful.",
            user_id="user123",
        )

        session = store.get_session(session_id)
        assert session is not None
        assert session["id"] == "test-session-1"
        assert session["source"] == "cli"
        assert session["model"] == "gpt-4"
        assert session["user_id"] == "user123"
        assert session["started_at"] > 0

    def test_end_session(self, store):
        """Test ending a session."""
        session_id = "test-session-end"
        store.create_session(session_id, source="cli")

        store.end_session(session_id, "completed")

        session = store.get_session(session_id)
        assert session["ended_at"] is not None
        assert session["end_reason"] == "completed"

    def test_list_sessions(self, store):
        """Test listing sessions with pagination."""
        for i in range(5):
            store.create_session(f"session-{i}", source="cli")
            time.sleep(0.001)  # Ensure different timestamps

        sessions = store.list_sessions(limit=3, offset=0)
        assert len(sessions) == 3

        all_sessions = store.list_sessions(limit=100)
        assert len(all_sessions) == 5

    def test_list_sessions_by_source(self, store):
        """Test filtering sessions by source."""
        store.create_session("s1", source="cli")
        store.create_session("s2", source="http")
        store.create_session("s3", source="cli")

        cli_sessions = store.list_sessions(source="cli")
        assert len(cli_sessions) == 2

        http_sessions = store.list_sessions(source="http")
        assert len(http_sessions) == 1

    def test_session_title(self, store):
        """Test setting and getting session titles."""
        session_id = "title-test"
        store.create_session(session_id, source="cli")

        assert store.get_session_title(session_id) is None

        result = store.set_session_title(session_id, "My Test Session")
        assert result is True

        title = store.get_session_title(session_id)
        assert title == "My Test Session"

    def test_ensure_session(self, store):
        """Test ensure_session creates session if not exists."""
        session_id = "ensure-test"

        assert store.get_session(session_id) is None

        store.ensure_session(session_id, source="cli", model="gpt-4")

        session = store.get_session(session_id)
        assert session is not None
        assert session["source"] == "cli"
        assert session["model"] == "gpt-4"

    def test_update_token_counts(self, store):
        """Test updating token counts."""
        session_id = "token-test"
        store.create_session(session_id, source="cli")

        store.update_token_counts(session_id, input_tokens=100, output_tokens=50)

        session = store.get_session(session_id)
        assert session["input_tokens"] == 100
        assert session["output_tokens"] == 50

        store.update_token_counts(session_id, input_tokens=200, output_tokens=100)

        session = store.get_session(session_id)
        assert session["input_tokens"] == 300
        assert session["output_tokens"] == 150


class TestMessageManagement:
    """Message storage and retrieval tests."""

    def test_add_and_get_messages(self, store):
        """Test adding and retrieving messages."""
        session_id = "msg-test"
        store.create_session(session_id, source="cli")

        msg1_id = store.add_message(
            session_id,
            role="user",
            content="Hello, how are you?",
        )
        msg2_id = store.add_message(
            session_id,
            role="assistant",
            content="I'm doing well, thank you!",
        )

        assert msg1_id > 0
        assert msg2_id > msg1_id

        messages = store.get_messages(session_id)
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello, how are you?"
        assert messages[1]["role"] == "assistant"

    def test_message_count(self, store):
        """Test message count tracking."""
        session_id = "count-test"
        store.create_session(session_id, source="cli")

        assert store.get_message_count(session_id) == 0

        store.add_message(session_id, role="user", content="Hi")
        assert store.get_message_count(session_id) == 1

        store.add_message(session_id, role="assistant", content="Hello")
        assert store.get_message_count(session_id) == 2

    def test_tool_calls_in_message(self, store):
        """Test storing tool calls in messages."""
        session_id = "tool-test"
        store.create_session(session_id, source="cli")

        tool_calls = [
            {
                "id": "call_123",
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "arguments": '{"location": "Beijing"}',
                },
            }
        ]

        store.add_message(
            session_id,
            role="assistant",
            content=None,
            tool_calls=tool_calls,
        )

        messages = store.get_messages(session_id)
        assert len(messages) == 1
        assert messages[0]["tool_calls"] is not None

        import json
        stored_calls = json.loads(messages[0]["tool_calls"])
        assert len(stored_calls) == 1
        assert stored_calls[0]["function"]["name"] == "get_weather"

    def test_tool_result_message(self, store):
        """Test storing tool result messages."""
        session_id = "tool-result-test"
        store.create_session(session_id, source="cli")

        store.add_message(
            session_id,
            role="tool",
            content='{"temperature": 25}',
            tool_call_id="call_123",
            tool_name="get_weather",
        )

        messages = store.get_messages(session_id)
        assert len(messages) == 1
        assert messages[0]["role"] == "tool"
        assert messages[0]["tool_call_id"] == "call_123"
        assert messages[0]["tool_name"] == "get_weather"


class TestFullTextSearch:
    """FTS5 full-text search tests."""

    def test_search_messages(self, store):
        """Test searching messages by content."""
        session_id = "search-test"
        store.create_session(session_id, source="cli")

        store.add_message(session_id, role="user", content="How do I install Python?")
        store.add_message(session_id, role="assistant", content="You can download Python from python.org")
        store.add_message(session_id, role="user", content="What about JavaScript?")
        store.add_message(session_id, role="assistant", content="JavaScript runs in the browser")

        # Search for Python-related messages
        results = store.search_messages("Python", session_id=session_id)
        assert len(results) >= 2
        assert any("Python" in r["content"] for r in results)

        # Search for JavaScript
        results = store.search_messages("JavaScript", session_id=session_id)
        assert len(results) >= 2
        assert any("JavaScript" in r["content"] for r in results)

    def test_search_messages_trigram(self, store):
        """Test trigram search for partial matches."""
        session_id = "trigram-test"
        store.create_session(session_id, source="cli")

        store.add_message(session_id, role="user", content="I need help with database optimization")
        store.add_message(session_id, role="assistant", content="Let me help optimize your database queries")

        # Trigram should find partial matches
        results = store.search_messages("optim", session_id=session_id, use_trigram=True)
        assert len(results) >= 1

    def test_search_sessions(self, store):
        """Test searching sessions by message content."""
        store.create_session("s1", source="cli")
        store.add_message("s1", role="user", content="How to bake a cake?")
        store.add_message("s1", role="assistant", content="Here's a cake recipe...")

        store.create_session("s2", source="cli")
        store.add_message("s2", role="user", content="How to fix a leaky faucet?")
        store.add_message("s2", role="assistant", content="To fix a faucet...")

        store.create_session("s3", source="cli")
        store.add_message("s3", role="user", content="Best cake decorating tips")
        store.add_message("s3", role="assistant", content="Try these cake decorations...")

        # Search for cake-related sessions
        results = store.search_sessions("cake")
        assert len(results) == 2
        session_ids = [r["id"] for r in results]
        assert "s1" in session_ids
        assert "s3" in session_ids

    def test_search_sessions_by_source(self, store):
        """Test searching sessions filtered by source."""
        store.create_session("s1", source="cli")
        store.add_message("s1", role="user", content="Python tutorial")

        store.create_session("s2", source="http")
        store.add_message("s2", role="user", content="Python API")

        results = store.search_sessions("Python", source="cli")
        assert len(results) == 1
        assert results[0]["id"] == "s1"


class TestConcurrency:
    """Concurrency and thread safety tests."""

    def test_concurrent_add_messages(self, store):
        """Test adding messages from multiple threads."""
        session_id = "concurrent-test"
        store.create_session(session_id, source="cli")

        num_threads = 5
        messages_per_thread = 10

        def add_messages(thread_id):
            for i in range(messages_per_thread):
                store.add_message(
                    session_id,
                    role="user",
                    content=f"Message from thread {thread_id}: {i}",
                )

        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=add_messages, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        count = store.get_message_count(session_id)
        assert count == num_threads * messages_per_thread

    def test_concurrent_sessions(self, temp_db_path):
        """Test multiple stores with the same database (WAL mode)."""
        store1 = SessionStore(db_path=temp_db_path)
        store2 = SessionStore(db_path=temp_db_path)

        try:
            store1.create_session("session-1", source="cli")
            store1.add_message("session-1", role="user", content="Hello from store1")

            # store2 should see the session
            session = store2.get_session("session-1")
            assert session is not None
            assert session["id"] == "session-1"

            messages = store2.get_messages("session-1")
            assert len(messages) == 1
        finally:
            store1.close()
            store2.close()


class TestSchemaReconciliation:
    """Schema migration and reconciliation tests."""

    def test_schema_reconciliation_adds_columns(self, temp_db_path):
        """Test that missing columns are added automatically."""
        # Create a minimal database without the title column
        import sqlite3
        conn = sqlite3.connect(str(temp_db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                started_at REAL NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT,
                timestamp REAL NOT NULL
            )
        """)
        conn.commit()
        conn.close()

        # Now open with SessionStore - it should reconcile columns
        store = SessionStore(db_path=temp_db_path)
        try:
            session = store.get_session("nonexistent")
            assert session is None

            # Create a session and verify new columns work
            store.create_session("recon-test", source="cli", model="gpt-4")
            store.set_session_title("recon-test", "Reconciled Title")

            session = store.get_session("recon-test")
            assert session["title"] == "Reconciled Title"
            assert session["model"] == "gpt-4"
        finally:
            store.close()


class TestWALFallback:
    """WAL mode fallback tests."""

    def test_apply_wal_with_fallback_success(self):
        """Test WAL mode applies successfully on normal filesystems."""
        import sqlite3
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            conn = sqlite3.connect(db_path)
            mode = apply_wal_with_fallback(conn, db_label="test.db")
            assert mode in ("wal", "delete")  # Either is acceptable
            conn.close()
        finally:
            os.unlink(db_path)
