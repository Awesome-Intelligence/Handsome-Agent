#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for MessageList widget.

Tests cover:
- Message addition
- Streaming text appending
- Message role styling
- History limit enforcement
- Scroll performance
"""

import pytest
import time


class TestMessageListImports:
    """Test MessageList imports."""
    
    def test_import_message_list(self):
        """Test importing MessageList."""
        try:
            from cli.tui.widgets.message_list import MessageList, MessageRole, MessageItem
            assert MessageList is not None
            assert MessageRole is not None
            assert MessageItem is not None
        except ImportError as e:
            pytest.skip(f"Textual not available: {e}")
    
    def test_import_message_events(self):
        """Test importing message events."""
        try:
            from cli.tui.widgets.message_list import (
                MessageListUpdated,
                StreamingComplete,
                MessageClicked,
            )
            assert MessageListUpdated is not None
            assert StreamingComplete is not None
            assert MessageClicked is not None
        except ImportError as e:
            pytest.skip(f"Textual not available: {e}")


class TestMessageRole:
    """Test MessageRole enum."""
    
    def test_role_enum_values(self):
        """Test MessageRole enum has expected values."""
        try:
            from cli.tui.widgets.message_list import MessageRole
            assert hasattr(MessageRole, 'USER')
            assert hasattr(MessageRole, 'ASSISTANT')
            assert hasattr(MessageRole, 'SYSTEM')
            assert hasattr(MessageRole, 'TOOL')
            assert hasattr(MessageRole, 'ERROR')
            assert hasattr(MessageRole, 'THINKING')
        except ImportError:
            pytest.skip("Textual not available")


class TestMessageItem:
    """Test MessageItem dataclass."""
    
    def test_message_item_creation(self):
        """Test creating a MessageItem."""
        try:
            from cli.tui.widgets.message_list import MessageItem, MessageRole
            
            msg = MessageItem(
                id="test-1",
                role=MessageRole.USER,
                content="Hello world",
            )
            
            assert msg.id == "test-1"
            assert msg.role == MessageRole.USER
            assert msg.content == "Hello world"
            assert msg.is_complete is True
            assert msg.is_streaming is False
        except ImportError:
            pytest.skip("Textual not available")
    
    def test_message_item_time_str(self):
        """Test MessageItem time_str property."""
        try:
            from cli.tui.widgets.message_list import MessageItem, MessageRole
            
            msg = MessageItem(
                id="test-1",
                role=MessageRole.USER,
                content="Test",
                timestamp=1700000000.0,
            )
            
            # Should return formatted time string
            assert isinstance(msg.time_str, str)
            assert ":" in msg.time_str  # Format: HH:MM:SS
        except ImportError:
            pytest.skip("Textual not available")
    
    def test_message_item_is_thinking(self):
        """Test MessageItem is_thinking property."""
        try:
            from cli.tui.widgets.message_list import MessageItem, MessageRole
            
            msg_thinking = MessageItem(
                id="test-1",
                role=MessageRole.THINKING,
                content="Thinking...",
            )
            assert msg_thinking.is_thinking is True
            
            msg_normal = MessageItem(
                id="test-2",
                role=MessageRole.ASSISTANT,
                content="Response",
            )
            assert msg_normal.is_thinking is False
        except ImportError:
            pytest.skip("Textual not available")
    
    def test_message_item_is_error(self):
        """Test MessageItem is_error property."""
        try:
            from cli.tui.widgets.message_list import MessageItem, MessageRole
            
            msg_error = MessageItem(
                id="test-1",
                role=MessageRole.ERROR,
                content="Error message",
            )
            assert msg_error.is_error is True
            
            msg_normal = MessageItem(
                id="test-2",
                role=MessageRole.USER,
                content="Hello",
            )
            assert msg_normal.is_error is False
        except ImportError:
            pytest.skip("Textual not available")


class TestMessageListBasics:
    """Test MessageList basic functionality."""
    
    def test_message_list_creation(self):
        """Test creating a MessageList."""
        try:
            from cli.tui.widgets.message_list import MessageList
            
            ml = MessageList(max_messages=50)
            assert ml.max_messages == 50
            assert ml.auto_scroll is True
            assert ml.show_timestamps is True
        except ImportError:
            pytest.skip("Textual not available")
    
    def test_add_message_returns_id(self):
        """Test add_message returns a message ID."""
        try:
            from cli.tui.widgets.message_list import MessageList
            
            ml = MessageList()
            msg_id = ml.add_message("user", "Hello")
            
            assert isinstance(msg_id, str)
            assert msg_id.startswith("msg-")
        except ImportError:
            pytest.skip("Textual not available")
    
    def test_add_user_message(self):
        """Test adding a user message."""
        try:
            from cli.tui.widgets.message_list import MessageList
            
            ml = MessageList()
            msg_id = ml.add_user_message("Test message")
            
            assert msg_id is not None
            messages = ml.get_messages()
            assert len(messages) == 1
            assert messages[0].content == "Test message"
        except ImportError:
            pytest.skip("Textual not available")
    
    def test_add_assistant_message(self):
        """Test adding an assistant message."""
        try:
            from cli.tui.widgets.message_list import MessageList
            
            ml = MessageList()
            msg_id = ml.add_assistant_message("Response content")
            
            assert msg_id is not None
            messages = ml.get_messages()
            assert len(messages) == 1
            assert messages[0].content == "Response content"
        except ImportError:
            pytest.skip("Textual not available")
    
    def test_add_system_message(self):
        """Test adding a system message."""
        try:
            from cli.tui.widgets.message_list import MessageList
            
            ml = MessageList()
            msg_id = ml.add_system_message("System notice")
            
            messages = ml.get_messages()
            assert len(messages) == 1
            assert messages[0].content == "System notice"
        except ImportError:
            pytest.skip("Textual not available")
    
    def test_add_tool_message(self):
        """Test adding a tool message."""
        try:
            from cli.tui.widgets.message_list import MessageList
            
            ml = MessageList()
            msg_id = ml.add_tool_message("Tool output", tool_name="read_file")
            
            messages = ml.get_messages()
            assert len(messages) == 1
            assert messages[0].tool_name == "read_file"
        except ImportError:
            pytest.skip("Textual not available")
    
    def test_add_error_message(self):
        """Test adding an error message."""
        try:
            from cli.tui.widgets.message_list import MessageList
            
            ml = MessageList()
            msg_id = ml.add_error_message("Something went wrong")
            
            messages = ml.get_messages()
            assert len(messages) == 1
            assert "wrong" in messages[0].content
        except ImportError:
            pytest.skip("Textual not available")


class TestStreamingText:
    """Test streaming text functionality."""
    
    def test_start_streaming(self):
        """Test starting streaming."""
        try:
            from cli.tui.widgets.message_list import MessageList
            
            ml = MessageList()
            msg_id = ml.start_streaming("assistant")
            
            assert msg_id is not None
            messages = ml.get_messages()
            assert len(messages) == 1
            assert messages[0].is_streaming is True
        except ImportError:
            pytest.skip("Textual not available")
    
    def test_append_streaming_text(self):
        """Test appending streaming text."""
        try:
            from cli.tui.widgets.message_list import MessageList
            
            ml = MessageList(streaming_throttle_ms=0)  # Disable throttling for testing
            msg_id = ml.start_streaming("assistant")
            ml.append_streaming_text(msg_id, "Hello")
            ml.append_streaming_text(msg_id, " world")
            
            message = ml.get_message(msg_id)
            assert "Hello world" in message.content
        except ImportError:
            pytest.skip("Textual not available")
    
    def test_complete_streaming(self):
        """Test completing streaming."""
        try:
            from cli.tui.widgets.message_list import MessageList
            
            ml = MessageList()
            msg_id = ml.start_streaming("assistant")
            ml.append_streaming_text(msg_id, "Complete")
            ml.complete_streaming(msg_id)
            
            message = ml.get_message(msg_id)
            assert message.is_streaming is False
            assert message.is_complete is True
        except ImportError:
            pytest.skip("Textual not available")


class TestMessageManagement:
    """Test message management operations."""
    
    def test_clear_messages(self):
        """Test clearing all messages."""
        try:
            from cli.tui.widgets.message_list import MessageList
            
            ml = MessageList()
            ml.add_message("user", "Message 1")
            ml.add_message("assistant", "Message 2")
            
            assert len(ml.get_messages()) == 2
            
            ml.clear_messages()
            assert len(ml.get_messages()) == 0
        except ImportError:
            pytest.skip("Textual not available")
    
    def test_remove_message(self):
        """Test removing a message."""
        try:
            from cli.tui.widgets.message_list import MessageList
            
            ml = MessageList()
            msg_id = ml.add_message("user", "To remove")
            ml.add_message("assistant", "To keep")
            
            result = ml.remove_message(msg_id)
            assert result is True
            assert len(ml.get_messages()) == 1
        except ImportError:
            pytest.skip("Textual not available")
    
    def test_get_message(self):
        """Test getting a specific message."""
        try:
            from cli.tui.widgets.message_list import MessageList
            
            ml = MessageList()
            msg_id = ml.add_message("user", "Specific message")
            
            message = ml.get_message(msg_id)
            assert message is not None
            assert message.content == "Specific message"
        except ImportError:
            pytest.skip("Textual not available")
    
    def test_get_nonexistent_message(self):
        """Test getting a message that doesn't exist."""
        try:
            from cli.tui.widgets.message_list import MessageList
            
            ml = MessageList()
            message = ml.get_message("nonexistent-id")
            assert message is None
        except ImportError:
            pytest.skip("Textual not available")


class TestHistoryLimit:
    """Test message history limit enforcement."""
    
    def test_max_messages_limit(self):
        """Test that messages are trimmed when exceeding limit."""
        try:
            from cli.tui.widgets.message_list import MessageList
            
            ml = MessageList(max_messages=5)
            
            # Add more messages than the limit
            for i in range(10):
                ml.add_message("user", f"Message {i}")
            
            # Should be trimmed to max_messages
            assert len(ml.get_messages()) <= 5
        except ImportError:
            pytest.skip("Textual not available")


class TestRender:
    """Test rendering functionality."""
    
    def test_render_returns_string(self):
        """Test that render returns a string."""
        try:
            from cli.tui.widgets.message_list import MessageList
            
            ml = MessageList()
            ml.add_message("user", "Hello")
            ml.add_message("assistant", "Hi there")
            
            rendered = ml.render()
            assert isinstance(rendered, str)
            assert len(rendered) > 0
        except ImportError:
            pytest.skip("Textual not available")
    
    def test_render_includes_content(self):
        """Test that rendered output includes message content."""
        try:
            from cli.tui.widgets.message_list import MessageList
            
            ml = MessageList()
            ml.add_message("user", "Test content")
            
            rendered = ml.render()
            assert "Test content" in rendered
        except ImportError:
            pytest.skip("Textual not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])