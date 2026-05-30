#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the Core module session management.

Tests cover Session, SessionManager, Message, and FileSessionStore.
"""

import pytest
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile


class TestMessage:
    """Test Message dataclass."""
    
    def test_message_creation(self):
        """Test creating a Message."""
        from core.session import Message
        
        msg = Message(
            role="user",
            content="Hello, world!"
        )
        
        assert msg.role == "user"
        assert msg.content == "Hello, world!"
        assert msg.timestamp is not None
        assert msg.metadata == {}
        assert msg.tool_call_id is None
        assert msg.tool_result is None
    
    def test_message_with_metadata(self):
        """Test Message with metadata."""
        from core.session import Message
        
        msg = Message(
            role="assistant",
            content="Response text",
            metadata={"intent": "greeting"}
        )
        
        assert msg.metadata["intent"] == "greeting"
    
    def test_message_with_tool_call(self):
        """Test Message with tool call information."""
        from core.session import Message
        
        msg = Message(
            role="assistant",
            content="Using tool...",
            tool_call_id="call_123",
            tool_result={"result": "success"}
        )
        
        assert msg.tool_call_id == "call_123"
        assert msg.tool_result == {"result": "success"}
    
    def test_message_timestamp_auto_generated(self):
        """Test that timestamp is auto-generated."""
        from core.session import Message
        import time
        
        before = time.time()
        msg = Message(role="user", content="test")
        after = time.time()
        
        assert before <= msg.timestamp <= after


class TestSessionConfig:
    """Test SessionConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        from core.session import SessionConfig
        
        config = SessionConfig()
        
        assert config.max_history_length == 50
        assert config.auto_save_interval == 300
        assert config.enable_persistence is True
        assert config.enable_detailed_logs is True
    
    def test_custom_config(self):
        """Test custom configuration values."""
        from core.session import SessionConfig
        
        config = SessionConfig(
            max_history_length=100,
            auto_save_interval=60,
            enable_persistence=False,
            enable_detailed_logs=False
        )
        
        assert config.max_history_length == 100
        assert config.auto_save_interval == 60
        assert config.enable_persistence is False
        assert config.enable_detailed_logs is False


class TestFileSessionStore:
    """Test FileSessionStore implementation."""
    
    def test_store_creation_with_temp_dir(self):
        """Test creating store with temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from core.session import FileSessionStore
            
            store = FileSessionStore(base_path=tmpdir)
            
            assert store.base_path == tmpdir
    
    def test_save_and_load_session(self):
        """Test saving and loading a session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from core.session import FileSessionStore
            
            store = FileSessionStore(base_path=tmpdir)
            
            # Save session data
            data = {
                "messages": [
                    {"role": "user", "content": "Hello"}
                ],
                "context": {"user_id": "user_001"}
            }
            store.save("session_001", data)
            
            # Load session data
            loaded = store.load("session_001")
            
            assert loaded is not None
            assert len(loaded["messages"]) == 1
            assert loaded["context"]["user_id"] == "user_001"
    
    def test_load_nonexistent_session(self):
        """Test loading a session that doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from core.session import FileSessionStore
            
            store = FileSessionStore(base_path=tmpdir)
            
            result = store.load("nonexistent")
            
            assert result is None
    
    def test_delete_session(self):
        """Test deleting a session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from core.session import FileSessionStore
            
            store = FileSessionStore(base_path=tmpdir)
            
            # Create session
            store.save("session_001", {"test": "data"})
            
            # Delete session
            store.delete("session_001")
            
            # Verify deleted
            assert store.load("session_001") is None
    
    def test_list_sessions(self):
        """Test listing all sessions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from core.session import FileSessionStore
            
            store = FileSessionStore(base_path=tmpdir)
            
            # Create multiple sessions
            store.save("session_001", {"test": "data1"})
            store.save("session_002", {"test": "data2"})
            store.save("session_003", {"test": "data3"})
            
            sessions = store.list_sessions()
            
            assert len(sessions) == 3
            assert "session_001" in sessions
            assert "session_002" in sessions
            assert "session_003" in sessions


class TestSession:
    """Test Session class."""
    
    def test_create_session(self):
        """Test creating a new session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from core.session import Session, SessionConfig
            
            config = SessionConfig(
                history_path=tmpdir,
                enable_persistence=False
            )
            session = Session("test_session", config=config)
            
            assert session.session_id == "test_session"
            assert len(session.messages) == 0
    
    def test_add_message(self):
        """Test adding messages to session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from core.session import Session, SessionConfig
            
            config = SessionConfig(
                history_path=tmpdir,
                enable_persistence=False
            )
            session = Session("test_session", config=config)
            
            session.add_message("user", "Hello")
            session.add_message("assistant", "Hi there!")
            
            assert len(session.messages) == 2
            assert session.messages[0].role == "user"
            assert session.messages[0].content == "Hello"
            assert session.messages[1].role == "assistant"
            assert session.messages[1].content == "Hi there!"
    
    def test_message_count(self):
        """Test getting message count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from core.session import Session, SessionConfig
            
            config = SessionConfig(
                history_path=tmpdir,
                enable_persistence=False
            )
            session = Session("test_session", config=config)
            
            session.add_message("user", "Message 1")
            session.add_message("user", "Message 2")
            session.add_message("user", "Message 3")
            
            assert session.get_message_count() == 3
    
    def test_get_history(self):
        """Test getting message history."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from core.session import Session, SessionConfig
            
            config = SessionConfig(
                history_path=tmpdir,
                enable_persistence=False
            )
            session = Session("test_session", config=config)
            
            for i in range(5):
                session.add_message("user", f"Message {i}")
            
            history = session.get_history()
            assert len(history) == 5
            
            # Test with limit
            recent = session.get_history(limit=2)
            assert len(recent) == 2
    
    def test_get_last_message(self):
        """Test getting the last message."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from core.session import Session, SessionConfig
            
            config = SessionConfig(
                history_path=tmpdir,
                enable_persistence=False
            )
            session = Session("test_session", config=config)
            
            assert session.get_last_message() is None
            
            session.add_message("user", "First")
            session.add_message("user", "Last")
            
            last = session.get_last_message()
            assert last.content == "Last"
    
    def test_context_management(self):
        """Test session context management."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from core.session import Session, SessionConfig
            
            config = SessionConfig(
                history_path=tmpdir,
                enable_persistence=False
            )
            session = Session("test_session", config=config)
            
            # Set context
            session.set_context("user_name", "Alice")
            session.set_context("theme", "dark")
            
            # Update context
            session.update_context({"language": "en", "timezone": "UTC"})
            
            context = session.get_context()
            
            assert context["user_name"] == "Alice"
            assert context["theme"] == "dark"
            assert context["language"] == "en"
            assert context["timezone"] == "UTC"
    
    def test_history_trimming(self):
        """Test that old messages are trimmed when exceeding max."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from core.session import Session, SessionConfig
            
            config = SessionConfig(
                history_path=tmpdir,
                max_history_length=3,
                enable_persistence=False
            )
            session = Session("test_session", config=config)
            
            # Add more messages than max
            for i in range(5):
                session.add_message("user", f"Message {i}")
            
            # Should be trimmed to max_history_length
            assert len(session.messages) == 3
            # First messages should be removed
            assert session.messages[0].content == "Message 2"
            assert session.messages[2].content == "Message 4"
    
    def test_clear_session(self):
        """Test clearing session messages and context."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from core.session import Session, SessionConfig
            
            config = SessionConfig(
                history_path=tmpdir,
                enable_persistence=False
            )
            session = Session("test_session", config=config)
            
            session.add_message("user", "Hello")
            session.set_context("test", "value")
            
            session.clear()
            
            assert len(session.messages) == 0
            assert len(session.context) == 0
    
    def test_formatted_history(self):
        """Test getting formatted history for API calls."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from core.session import Session, SessionConfig
            
            config = SessionConfig(
                history_path=tmpdir,
                enable_persistence=False
            )
            session = Session("test_session", config=config)
            
            session.add_message("system", "You are a helpful assistant")
            session.add_message("user", "Hello")
            session.add_message("assistant", "Hi!")
            
            # Without system messages
            formatted = session.get_formatted_history(include_system=False)
            assert len(formatted) == 2
            assert formatted[0]["role"] == "user"
            assert formatted[1]["role"] == "assistant"
            
            # With system messages
            formatted_with_system = session.get_formatted_history(include_system=True)
            assert len(formatted_with_system) == 3
    
    def test_session_stats(self):
        """Test getting session statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from core.session import Session, SessionConfig
            
            config = SessionConfig(
                history_path=tmpdir,
                enable_persistence=False
            )
            session = Session("test_session", config=config)
            
            session.add_message("user", "Hello")
            session.add_message("assistant", "Hi!")
            session.add_message("tool", "Tool result")
            
            stats = session.get_stats()
            
            assert stats["session_id"] == "test_session"
            assert stats["message_count"] == 3
            assert stats["user_messages"] == 1
            assert stats["assistant_messages"] == 1
            assert stats["tool_calls"] == 1
            assert stats["context_keys"] == 0


class TestSessionManager:
    """Test SessionManager class."""
    
    def test_create_session_manager(self):
        """Test creating a session manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from core.session import SessionManager, SessionConfig
            
            config = SessionConfig(history_path=tmpdir)
            manager = SessionManager(config=config)
            
            assert manager is not None
            assert len(manager.sessions) == 0
    
    def test_create_new_session(self):
        """Test creating a new session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from core.session import SessionManager, SessionConfig
            
            config = SessionConfig(history_path=tmpdir)
            manager = SessionManager(config=config)
            
            session = manager.create_session("new_session")
            
            assert session is not None
            assert session.session_id == "new_session"
            assert len(manager.sessions) == 1
    
    def test_create_duplicate_session(self):
        """Test creating a session that already exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from core.session import SessionManager, SessionConfig
            
            config = SessionConfig(history_path=tmpdir)
            manager = SessionManager(config=config)
            
            session1 = manager.create_session("existing_session")
            session2 = manager.create_session("existing_session")
            
            # Should return the same session
            assert session1 is session2
            assert len(manager.sessions) == 1
    
    def test_get_session(self):
        """Test getting an existing session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from core.session import SessionManager, SessionConfig
            
            config = SessionConfig(history_path=tmpdir)
            manager = SessionManager(config=config)
            
            manager.create_session("test_session")
            
            session = manager.get_session("test_session")
            
            assert session is not None
            assert session.session_id == "test_session"
    
    def test_get_nonexistent_session(self):
        """Test getting a session that doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from core.session import SessionManager, SessionConfig
            
            config = SessionConfig(history_path=tmpdir)
            manager = SessionManager(config=config)
            
            session = manager.get_session("nonexistent")
            
            assert session is None
    
    def test_delete_session(self):
        """Test deleting a session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from core.session import SessionManager, SessionConfig
            
            config = SessionConfig(history_path=tmpdir)
            manager = SessionManager(config=config)
            
            manager.create_session("session_to_delete")
            assert len(manager.sessions) == 1
            
            manager.delete_session("session_to_delete")
            assert len(manager.sessions) == 0
    
    def test_list_sessions(self):
        """Test listing all sessions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from core.session import SessionManager, SessionConfig
            
            config = SessionConfig(history_path=tmpdir)
            manager = SessionManager(config=config)
            
            manager.create_session("session_1")
            manager.create_session("session_2")
            manager.create_session("session_3")
            
            sessions = manager.list_sessions()
            
            assert len(sessions) >= 3
            assert "session_1" in sessions
            assert "session_2" in sessions
            assert "session_3" in sessions
    
    def test_get_active_sessions(self):
        """Test getting all active sessions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from core.session import SessionManager, SessionConfig
            
            config = SessionConfig(history_path=tmpdir)
            manager = SessionManager(config=config)
            
            manager.create_session("active_1")
            manager.create_session("active_2")
            
            active = manager.get_active_sessions()
            
            assert len(active) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
