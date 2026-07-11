#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for MessageList widget.

Tests cover:
- Message rendering
- Scroll behavior
- Markdown rendering
- Uses sample_message_history fixture
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import time


class TestMessageListBasics:
    """Test MessageList basic functionality."""

    def test_message_list_creation(self):
        """Test creating a MessageList instance."""
        from tui.widgets.message_list import TEXTUAL_AVAILABLE
        
        if not TEXTUAL_AVAILABLE:
            pytest.skip("Textual not available")
        
        from tui.widgets.message_list import MessageList
        
        msg_list = MessageList()
        
        assert msg_list.max_messages == 100
        assert msg_list.auto_scroll is True
        assert msg_list.show_timestamps is True
        assert msg_list.show_role_icons is True

    def test_message_list_custom_params(self):
        """Test creating MessageList with custom parameters."""
        from tui.widgets.message_list import TEXTUAL_AVAILABLE
        
        if not TEXTUAL_AVAILABLE:
            pytest.skip("Textual not available")
        
        from tui.widgets.message_list import MessageList
        
        msg_list = MessageList(
            max_messages=50,
            auto_scroll=False,
            show_timestamps=False,
            streaming_buffer_size=50,
        )
        
        assert msg_list.max_messages == 50
        assert msg_list.auto_scroll is False
        assert msg_list.show_timestamps is False
        assert msg_list.streaming_buffer_size == 50

    def test_message_list_initial_state(self):
        """Test MessageList initial state."""
        from tui.widgets.message_list import TEXTUAL_AVAILABLE
        
        if not TEXTUAL_AVAILABLE:
            pytest.skip("Textual not available")
        
        from tui.widgets.message_list import MessageList
        
        msg_list = MessageList()
        
        assert len(msg_list._messages) == 0
        assert len(msg_list._message_index) == 0
        assert msg_list._message_counter == 0
        assert len(msg_list._streaming_active) == 0


class TestMessageRole:
    """Test MessageRole enum."""

    def test_message_role_values(self):
        """Test MessageRole enum values."""
        from tui.widgets.message_list import MessageRole
        
        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"
        assert MessageRole.SYSTEM.value == "system"
        assert MessageRole.TOOL.value == "tool"
        assert MessageRole.ERROR.value == "error"
        assert MessageRole.THINKING.value == "thinking"


class TestMessageItem:
    """Test MessageItem dataclass."""

    def test_message_item_creation(self):
        """Test creating a MessageItem."""
        from tui.widgets.message_list import MessageItem, MessageRole
        
        msg = MessageItem(
            id="test-1",
            role=MessageRole.USER,
            content="Hello, world!",
        )
        
        assert msg.id == "test-1"
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello, world!"
        assert msg.is_streaming is False
        assert msg.is_complete is True

    def test_message_item_time_str(self):
        """Test MessageItem timestamp formatting."""
        from tui.widgets.message_list import MessageItem, MessageRole
        
        msg = MessageItem(
            id="test-1",
            role=MessageRole.USER,
            content="Hello",
            timestamp=1704067200.0,  # 2024-01-01 00:00:00 UTC
        )
        
        # Should return formatted time string
        time_str = msg.time_str
        assert isinstance(time_str, str)
        assert ":" in time_str  # HH:MM:SS format


class TestAddMessages:
    """Test adding messages to MessageList."""

    @patch('tui.widgets.message_list.TEXTUAL_AVAILABLE', True)
    def test_add_user_message(self):
        """Test adding a user message."""
        from tui.widgets.message_list import MessageList, MessageRole
        
        msg_list = MessageList()
        
        msg_id = msg_list.add_user_message("Test user message")
        
        assert msg_id is not None
        assert len(msg_list._messages) == 1
        assert msg_list._messages[0].role == MessageRole.USER
        assert msg_list._messages[0].content == "Test user message"

    @patch('tui.widgets.message_list.TEXTUAL_AVAILABLE', True)
    def test_add_assistant_message(self):
        """Test adding an assistant message."""
        from tui.widgets.message_list import MessageList, MessageRole
        
        msg_list = MessageList()
        
        msg_id = msg_list.add_assistant_message("Test assistant message")
        
        assert msg_id is not None
        assert len(msg_list._messages) == 1
        assert msg_list._messages[0].role == MessageRole.ASSISTANT

    @patch('tui.widgets.message_list.TEXTUAL_AVAILABLE', True)
    def test_add_system_message(self):
        """Test adding a system message."""
        from tui.widgets.message_list import MessageList, MessageRole
        
        msg_list = MessageList()
        
        msg_id = msg_list.add_system_message("System notification")
        
        assert msg_id is not None
        assert msg_list._messages[0].role == MessageRole.SYSTEM

    @patch('tui.widgets.message_list.TEXTUAL_AVAILABLE', True)
    def test_add_tool_message(self):
        """Test adding a tool message."""
        from tui.widgets.message_list import MessageList, MessageRole
        
        msg_list = MessageList()
        
        msg_id = msg_list.add_tool_message("Tool result", "list_files")
        
        assert msg_id is not None
        assert msg_list._messages[0].role == MessageRole.TOOL
        assert msg_list._messages[0].tool_name == "list_files"

    @patch('tui.widgets.message_list.TEXTUAL_AVAILABLE', True)
    def test_add_error_message(self):
        """Test adding an error message."""
        from tui.widgets.message_list import MessageList, MessageRole
        
        msg_list = MessageList()
        
        msg_id = msg_list.add_error_message("Error occurred")
        
        assert msg_id is not None
        assert msg_list._messages[0].role == MessageRole.ERROR

    @patch('tui.widgets.message_list.TEXTUAL_AVAILABLE', True)
    def test_add_thinking_message(self):
        """Test adding a thinking message."""
        from tui.widgets.message_list import MessageList, MessageRole
        
        msg_list = MessageList()
        
        msg_id = msg_list.add_thinking_message("Let me think...")
        
        assert msg_id is not None
        assert msg_list._messages[0].role == MessageRole.THINKING

    @patch('tui.widgets.message_list.TEXTUAL_AVAILABLE', True)
    def test_add_message_with_string_role(self):
        """Test adding message with string role."""
        from tui.widgets.message_list import MessageList, MessageRole
        
        msg_list = MessageList()
        
        msg_id = msg_list.add_message("user", "String role test")
        
        assert msg_id is not None
        assert msg_list._messages[0].role == MessageRole.USER


class TestMessageHistory:
    """Test message history with sample data."""

    @patch('tui.widgets.message_list.TEXTUAL_AVAILABLE', True)
    def test_load_sample_message_history(self, sample_message_history):
        """Test loading sample message history."""
        from tui.widgets.message_list import MessageList
        
        msg_list = MessageList()
        
        # Add messages from sample history
        for msg in sample_message_history:
            msg_list.add_message(msg["role"], msg["content"])
        
        assert len(msg_list._messages) == 3
        assert msg_list._messages[0].content == "Hello, how are you?"
        assert msg_list._messages[1].content == "I'm doing well! How can I help you?"

    @patch('tui.widgets.message_list.TEXTUAL_AVAILABLE', True)
    def test_message_history_timestamps(self, sample_message_history):
        """Test that messages from history have timestamps."""
        from tui.widgets.message_list import MessageList
        
        msg_list = MessageList()
        
        for msg in sample_message_history:
            msg_list.add_message(msg["role"], msg["content"])
        
        # All messages should have timestamps
        for msg in msg_list._messages:
            assert msg.timestamp is not None


class TestRemoveMessages:
    """Test removing messages."""

    @patch('tui.widgets.message_list.TEXTUAL_AVAILABLE', True)
    def test_remove_message(self):
        """Test removing a message by ID."""
        from tui.widgets.message_list import MessageList
        
        msg_list = MessageList()
        
        msg_id = msg_list.add_user_message("Test message")
        assert len(msg_list._messages) == 1
        
        result = msg_list.remove_message(msg_id)
        
        assert result is True
        assert len(msg_list._messages) == 0

    @patch('tui.widgets.message_list.TEXTUAL_AVAILABLE', True)
    def test_remove_nonexistent_message(self):
        """Test removing a non-existent message."""
        from tui.widgets.message_list import MessageList
        
        msg_list = MessageList()
        
        result = msg_list.remove_message("non-existent-id")
        
        assert result is False


class TestClearMessages:
    """Test clearing messages."""

    @patch('tui.widgets.message_list.TEXTUAL_AVAILABLE', True)
    def test_clear_messages(self):
        """Test clearing all messages."""
        from tui.widgets.message_list import MessageList
        
        msg_list = MessageList()
        
        # Add some messages
        msg_list.add_user_message("Message 1")
        msg_list.add_user_message("Message 2")
        msg_list.add_user_message("Message 3")
        
        assert len(msg_list._messages) == 3
        
        msg_list.clear_messages()
        
        assert len(msg_list._messages) == 0
        assert len(msg_list._message_index) == 0

    @patch('tui.widgets.message_list.TEXTUAL_AVAILABLE', True)
    def test_clear_messages_streaming_state(self):
        """Test clearing messages also clears streaming state."""
        from tui.widgets.message_list import MessageList
        
        msg_list = MessageList()
        
        msg_list.add_user_message("Message")
        msg_list._streaming_active["test"] = "user"
        msg_list._streaming_buffer["test"] = "buffer"
        
        msg_list.clear_messages()
        
        assert len(msg_list._streaming_active) == 0
        assert len(msg_list._streaming_buffer) == 0


class TestGetMessages:
    """Test getting messages."""

    @patch('tui.widgets.message_list.TEXTUAL_AVAILABLE', True)
    def test_get_messages_returns_copy(self):
        """Test get_messages returns a copy."""
        from tui.widgets.message_list import MessageList
        
        msg_list = MessageList()
        msg_list.add_user_message("Test")
        
        messages = msg_list.get_messages()
        
        # Should be a copy, not the original
        assert messages is not msg_list._messages
        assert len(messages) == 1

    @patch('tui.widgets.message_list.TEXTUAL_AVAILABLE', True)
    def test_get_messages_empty(self):
        """Test get_messages when empty."""
        from tui.widgets.message_list import MessageList
        
        msg_list = MessageList()
        
        messages = msg_list.get_messages()
        
        assert len(messages) == 0


class TestMessageTrim:
    """Test message trimming."""

    @patch('tui.widgets.message_list.TEXTUAL_AVAILABLE', True)
    def test_trim_excess_messages(self):
        """Test trimming messages beyond max limit."""
        from tui.widgets.message_list import MessageList
        
        msg_list = MessageList(max_messages=5)
        
        # Add more messages than the limit
        for i in range(10):
            msg_list.add_user_message(f"Message {i}")
        
        # Should be trimmed to max
        assert len(msg_list._messages) <= 5


class TestStreaming:
    """Test streaming functionality."""

    @patch('tui.widgets.message_list.TEXTUAL_AVAILABLE', True)
    def test_start_streaming(self):
        """Test starting a streaming message."""
        from tui.widgets.message_list import MessageList
        
        msg_list = MessageList()
        
        msg_id = msg_list.start_streaming("assistant", "")
        
        assert msg_id is not None
        assert msg_id in msg_list._streaming_active
        assert msg_list._messages[-1].is_streaming is True

    @patch('tui.widgets.message_list.TEXTUAL_AVAILABLE', True)
    def test_append_streaming_text(self):
        """Test appending text to streaming message."""
        from tui.widgets.message_list import MessageList
        
        msg_list = MessageList()
        
        msg_id = msg_list.start_streaming("assistant", "")
        msg_list.append_streaming_text(msg_id, "Hello")
        msg_list.append_streaming_text(msg_id, " ")
        msg_list.append_streaming_text(msg_id, "World")
        
        # Text should be accumulated
        assert len(msg_list._messages[-1].content) > 0

    @patch('tui.widgets.message_list.TEXTUAL_AVAILABLE', True)
    def test_complete_streaming(self):
        """Test completing a streaming message."""
        from tui.widgets.message_list import MessageList
        
        msg_list = MessageList()
        
        msg_id = msg_list.start_streaming("assistant", "Initial")
        msg_list.append_streaming_text(msg_id, " more text")
        msg_list.complete_streaming(msg_id)
        
        # Should not be in streaming state anymore
        assert msg_id not in msg_list._streaming_active
        # Message should be complete
        assert msg_list._messages[-1].is_complete is True

    @patch('tui.widgets.message_list.TEXTUAL_AVAILABLE', True)
    def test_append_to_inactive_streaming(self):
        """Test appending to non-existent streaming message."""
        from tui.widgets.message_list import MessageList
        
        msg_list = MessageList()
        
        # Should not raise
        msg_list.append_streaming_text("non-existent", "text")


class TestScrollBehavior:
    """Test scroll behavior."""

    @patch('tui.widgets.message_list.TEXTUAL_AVAILABLE', True)
    def test_auto_scroll_disabled(self):
        """Test auto scroll when disabled."""
        from tui.widgets.message_list import MessageList
        
        msg_list = MessageList(auto_scroll=False)
        
        assert msg_list._should_auto_scroll() is False

    @patch('tui.widgets.message_list.TEXTUAL_AVIVATE', True)
    def test_mark_scrolled_to_bottom(self):
        """Test marking user as scrolled to bottom."""
        from tui.widgets.message_list import MessageList
        
        msg_list = MessageList()
        
        msg_list._mark_scrolled_to_bottom()
        
        assert msg_list._user_scrolled_to_bottom is True

    @patch('tui.widgets.message_list.TEXTUAL_AVAILABLE', True)
    def test_mark_scrolled_away(self):
        """Test marking user as scrolled away from bottom."""
        from tui.widgets.message_list import MessageList
        
        msg_list = MessageList()
        
        msg_list._mark_scrolled_away()
        
        assert msg_list._user_scrolled_to_bottom is False


class TestMarkdownRendering:
    """Test Markdown rendering."""

    @patch('tui.widgets.message_list.TEXTUAL_AVAILABLE', True)
    def test_format_message_header(self):
        """Test message header formatting."""
        from tui.widgets.message_list import MessageList, MessageItem, MessageRole
        
        msg_list = MessageList()
        
        msg = MessageItem(
            id="test-1",
            role=MessageRole.USER,
            content="Test",
        )
        
        header = msg_list._format_message_header(msg)
        
        assert isinstance(header, str)
        assert "USER" in header.upper() or "user" in header.lower()

    @patch('tui.widgets.message_list.TEXTUAL_AVAILABLE', True)
    def test_format_message_content_streaming(self):
        """Test streaming message content formatting."""
        from tui.widgets.message_list import MessageList, MessageItem, MessageRole

        msg_list = MessageList()

        msg = MessageItem(
            id="test-1",
            role=MessageRole.ASSISTANT,
            content="Streaming content",
            is_streaming=True,
        )

        content = msg_list._format_message_content(msg)

        # ponytail: 游标字符已从 content 移除 — 流式期间只用纯文本渲染
        assert content == "Streaming content"
        assert "▌" not in content

    @patch('tui.widgets.message_list.TEXTUAL_AVAILABLE', True)
    def test_format_message_content_not_streaming(self):
        """Test non-streaming message content formatting."""
        from tui.widgets.message_list import MessageList, MessageItem, MessageRole

        msg_list = MessageList()

        msg = MessageItem(
            id="test-1",
            role=MessageRole.ASSISTANT,
            content="Complete content",
            is_streaming=False,
        )

        content = msg_list._format_message_content(msg)

        # Should not include cursor
        assert content == "Complete content"
        assert "▌" not in content


class TestMessageIndex:
    """Test message indexing."""

    @patch('tui.widgets.message_list.TEXTUAL_AVAILABLE', True)
    def test_message_index_creation(self):
        """Test message index is created on add."""
        from tui.widgets.message_list import MessageList
        
        msg_list = MessageList()
        
        msg_id = msg_list.add_user_message("Indexed message")
        
        assert msg_id in msg_list._message_index

    @patch('tui.widgets.message_list.TEXTUAL_AVAILABLE', True)
    def test_message_index_update_on_remove(self):
        """Test index is updated when message is removed."""
        from tui.widgets.message_list import MessageList
        
        msg_list = MessageList()
        
        msg_id = msg_list.add_user_message("Test")
        assert msg_id in msg_list._message_index
        
        msg_list.remove_message(msg_id)
        
        assert msg_id not in msg_list._message_index


class TestMessageListMessages:
    """Test MessageListUpdated message."""

    def test_message_list_updated_init(self):
        """Test MessageListUpdated initialization."""
        from tui.widgets.message_list import MessageListUpdated
        
        sender = MagicMock()
        event = MessageListUpdated(sender, 5)
        
        assert event.message_count == 5


class TestStreamingComplete:
    """Test StreamingComplete message."""

    def test_streaming_complete_init(self):
        """Test StreamingComplete initialization."""
        from tui.widgets.message_list import StreamingComplete
        
        sender = MagicMock()
        event = StreamingComplete(sender, "msg-123")
        
        assert event.message_id == "msg-123"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
