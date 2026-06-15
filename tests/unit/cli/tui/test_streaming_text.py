#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for StreamingText widget.

Tests cover:
- Streaming text initialization
- Text appending with throttling
- Thinking content handling
- Streaming completion
- Callbacks
"""

import pytest
import time


class TestStreamingTextImports:
    """Test StreamingText imports."""
    
    def test_import_streaming_text(self):
        """Test importing StreamingText."""
        try:
            from cli.tui.widgets.streaming_text import (
                StreamingText,
                StreamingState,
                TextType,
            )
            assert StreamingText is not None
            assert StreamingState is not None
            assert TextType is not None
        except ImportError as e:
            pytest.skip(f"Textual not available: {e}")
    
    def test_import_streaming_events(self):
        """Test importing streaming events."""
        try:
            from cli.tui.widgets.streaming_text import (
                StreamingStarted,
                StreamingUpdate,
                StreamingEnded,
                ThinkingToggled,
            )
            assert StreamingStarted is not None
            assert StreamingUpdate is not None
            assert StreamingEnded is not None
            assert ThinkingToggled is not None
        except ImportError as e:
            pytest.skip(f"Textual not available: {e}")


class TestTextType:
    """Test TextType enum."""
    
    def test_text_type_enum_values(self):
        """Test TextType enum has expected values."""
        try:
            from cli.tui.widgets.streaming_text import TextType
            assert hasattr(TextType, 'OUTPUT')
            assert hasattr(TextType, 'THINKING')
            assert hasattr(TextType, 'TOOL')
            assert hasattr(TextType, 'ERROR')
        except ImportError:
            pytest.skip("Textual not available")


class TestStreamingState:
    """Test StreamingState dataclass."""
    
    def test_streaming_state_creation(self):
        """Test creating a StreamingState."""
        try:
            from cli.tui.widgets.streaming_text import StreamingState, TextType
            
            state = StreamingState(
                text="Hello",
                text_type=TextType.OUTPUT,
            )
            
            assert state.text == "Hello"
            assert state.text_type == TextType.OUTPUT
            assert state.is_streaming is False
        except ImportError:
            pytest.skip("Textual not available")
    
    def test_streaming_state_defaults(self):
        """Test StreamingState default values."""
        try:
            from cli.tui.widgets.streaming_text import StreamingState, TextType
            
            state = StreamingState()
            
            assert state.text == ""
            assert state.text_type == TextType.OUTPUT
            assert state.is_streaming is False
            assert state.start_time > 0
            assert state.last_update > 0
        except ImportError:
            pytest.skip("Textual not available")


class TestStreamingTextBasics:
    """Test StreamingText basic functionality."""
    
    def test_streaming_text_creation(self):
        """Test creating a StreamingText."""
        try:
            from cli.tui.widgets.streaming_text import StreamingText
            
            st = StreamingText(show_thinking=True)
            assert st.show_thinking is True
            assert st.thinking_expanded is False
            assert st.throttle_ms == 50
            assert st.buffer_size == 100
        except ImportError:
            pytest.skip("Textual not available")
    
    def test_start_streaming_output(self):
        """Test starting output streaming."""
        try:
            from cli.tui.widgets.streaming_text import StreamingText, TextType
            
            st = StreamingText()
            st.start_streaming(TextType.OUTPUT)
            
            # State should be streaming
            assert st._output_state.is_streaming is True
        except ImportError:
            pytest.skip("Textual not available")
    
    def test_start_streaming_with_initial_text(self):
        """Test starting streaming with initial text."""
        try:
            from cli.tui.widgets.streaming_text import StreamingText, TextType
            
            st = StreamingText()
            st.start_streaming(TextType.OUTPUT, initial_text="Initial ")
            
            assert st.get_output() == "Initial "
        except ImportError:
            pytest.skip("Textual not available")
    
    def test_start_streaming_thinking(self):
        """Test starting thinking streaming."""
        try:
            from cli.tui.widgets.streaming_text import StreamingText, TextType
            
            st = StreamingText()
            st.start_streaming(TextType.THINKING)
            
            assert st._thinking_state.is_streaming is True
        except ImportError:
            pytest.skip("Textual not available")


class TestTextAppending:
    """Test text appending functionality."""
    
    def test_append_text(self):
        """Test appending text."""
        try:
            from cli.tui.widgets.streaming_text import StreamingText, TextType
            
            st = StreamingText(throttle_ms=0)  # Disable throttling for testing
            st.start_streaming(TextType.OUTPUT)
            st.append_text("Hello", TextType.OUTPUT)
            st.append_text(" world", TextType.OUTPUT)
            
            assert st.get_output() == "Hello world"
        except ImportError:
            pytest.skip("Textual not available")
    
    def test_append_text_thinking(self):
        """Test appending thinking text."""
        try:
            from cli.tui.widgets.streaming_text import StreamingText, TextType
            
            st = StreamingText(throttle_ms=0)
            st.start_streaming(TextType.THINKING)
            st.append_text("Let me think", TextType.THINKING)
            
            assert st.get_thinking() == "Let me think"
        except ImportError:
            pytest.skip("Textual not available")
    
    def test_append_multiple_types(self):
        """Test appending text of different types."""
        try:
            from cli.tui.widgets.streaming_text import StreamingText, TextType
            
            st = StreamingText(throttle_ms=0)
            st.start_streaming(TextType.OUTPUT)
            st.start_streaming(TextType.THINKING)
            
            st.append_text("Output text", TextType.OUTPUT)
            st.append_text("Thinking text", TextType.THINKING)
            
            assert st.get_output() == "Output text"
            assert st.get_thinking() == "Thinking text"
        except ImportError:
            pytest.skip("Textual not available")


class TestStreamingEnd:
    """Test streaming end functionality."""
    
    def test_end_streaming(self):
        """Test ending streaming."""
        try:
            from cli.tui.widgets.streaming_text import StreamingText, TextType
            
            st = StreamingText(throttle_ms=0)
            st.start_streaming(TextType.OUTPUT)
            st.append_text("Complete", TextType.OUTPUT)
            result = st.end_streaming(TextType.OUTPUT)
            
            assert result == "Complete"
            assert st._output_state.is_streaming is False
        except ImportError:
            pytest.skip("Textual not available")
    
    def test_end_streaming_flushes_buffer(self):
        """Test that ending streaming flushes buffer."""
        try:
            from cli.tui.widgets.streaming_text import StreamingText, TextType
            
            st = StreamingText(throttle_ms=1000)  # Long throttle
            st.start_streaming(TextType.OUTPUT)
            st.append_text("Buffered", TextType.OUTPUT)
            result = st.end_streaming(TextType.OUTPUT)
            
            # Should include buffered text
            assert "Buffered" in result
        except ImportError:
            pytest.skip("Textual not available")
    
    def test_complete_streaming(self):
        """Test completing all streaming."""
        try:
            from cli.tui.widgets.streaming_text import StreamingText, TextType
            
            st = StreamingText(throttle_ms=0)
            st.start_streaming(TextType.OUTPUT)
            st.start_streaming(TextType.THINKING)
            
            st.append_text("Output", TextType.OUTPUT)
            st.append_text("Thinking", TextType.THINKING)
            
            output, thinking = st.complete_streaming()
            
            assert output == "Output"
            assert thinking == "Thinking"
            assert st._output_state.is_streaming is False
            assert st._thinking_state.is_streaming is False
        except ImportError:
            pytest.skip("Textual not available")


class TestContentAccess:
    """Test content access methods."""
    
    def test_get_output(self):
        """Test getting output text."""
        try:
            from cli.tui.widgets.streaming_text import StreamingText, TextType
            
            st = StreamingText()
            st.start_streaming(TextType.OUTPUT)
            st.append_text("Output text", TextType.OUTPUT)
            st.end_streaming(TextType.OUTPUT)
            
            assert st.get_output() == "Output text"
        except ImportError:
            pytest.skip("Textual not available")
    
    def test_get_thinking(self):
        """Test getting thinking text."""
        try:
            from cli.tui.widgets.streaming_text import StreamingText, TextType
            
            st = StreamingText()
            st.start_streaming(TextType.THINKING)
            st.append_text("Thinking text", TextType.THINKING)
            st.end_streaming(TextType.THINKING)
            
            assert st.get_thinking() == "Thinking text"
        except ImportError:
            pytest.skip("Textual not available")
    
    def test_get_all_text(self):
        """Test getting all text."""
        try:
            from cli.tui.widgets.streaming_text import StreamingText, TextType
            
            st = StreamingText(show_thinking=True)
            st.start_streaming(TextType.OUTPUT)
            st.start_streaming(TextType.THINKING)
            
            st.append_text("Output", TextType.OUTPUT)
            st.append_text("Thinking", TextType.THINKING)
            
            st.complete_streaming()
            
            all_text = st.get_all_text()
            assert "Output" in all_text
            assert "Thinking" in all_text
        except ImportError:
            pytest.skip("Textual not available")


class TestThinkingControl:
    """Test thinking content control."""
    
    def test_toggle_thinking(self):
        """Test toggling thinking expanded state."""
        try:
            from cli.tui.widgets.streaming_text import StreamingText
            
            st = StreamingText()
            assert st.thinking_expanded is False
            
            st.toggle_thinking()
            assert st.thinking_expanded is True
            
            st.toggle_thinking()
            assert st.thinking_expanded is False
        except ImportError:
            pytest.skip("Textual not available")
    
    def test_set_show_thinking(self):
        """Test setting show_thinking flag."""
        try:
            from cli.tui.widgets.streaming_text import StreamingText
            
            st = StreamingText()
            assert st.show_thinking is True
            
            st.set_show_thinking(False)
            assert st.show_thinking is False
            
            st.set_show_thinking(True)
            assert st.show_thinking is True
        except ImportError:
            pytest.skip("Textual not available")


class TestClear:
    """Test clear functionality."""
    
    def test_clear(self):
        """Test clearing all text."""
        try:
            from cli.tui.widgets.streaming_text import StreamingText, TextType
            
            st = StreamingText()
            st.start_streaming(TextType.OUTPUT)
            st.append_text("Some text", TextType.OUTPUT)
            st.start_streaming(TextType.THINKING)
            st.append_text("Thinking", TextType.THINKING)
            
            st.clear()
            
            assert st.get_output() == ""
            assert st.get_thinking() == ""
        except ImportError:
            pytest.skip("Textual not available")


class TestCallbacks:
    """Test callback functionality."""
    
    def test_set_on_streaming_end_callback(self):
        """Test setting streaming end callback."""
        try:
            from cli.tui.widgets.streaming_text import StreamingText
            
            callback_called = []
            
            def callback(text_type, text):
                callback_called.append((text_type, text))
            
            st = StreamingText()
            st.set_on_streaming_end(callback)
            
            assert st._on_streaming_end is callback
        except ImportError:
            pytest.skip("Textual not available")


class TestRender:
    """Test rendering functionality."""
    
    def test_render_returns_string(self):
        """Test that render returns a string."""
        try:
            from cli.tui.widgets.streaming_text import StreamingText, TextType
            
            st = StreamingText()
            st.start_streaming(TextType.OUTPUT)
            st.append_text("Rendered text", TextType.OUTPUT)
            st.end_streaming(TextType.OUTPUT)
            
            rendered = st.render()
            assert isinstance(rendered, str)
        except ImportError:
            pytest.skip("Textual not available")
    
    def test_render_includes_output(self):
        """Test that rendered output includes output text."""
        try:
            from cli.tui.widgets.streaming_text import StreamingText, TextType
            
            st = StreamingText(show_thinking=False)
            st.start_streaming(TextType.OUTPUT)
            st.append_text("Output content", TextType.OUTPUT)
            st.end_streaming(TextType.OUTPUT)
            
            rendered = st.render()
            assert "Output content" in rendered
        except ImportError:
            pytest.skip("Textual not available")


class TestCreateStreamingText:
    """Test create_streaming_text convenience function."""
    
    def test_create_streaming_text(self):
        """Test create_streaming_text convenience function."""
        try:
            from cli.tui.widgets.streaming_text import create_streaming_text
            
            st = create_streaming_text(show_thinking=False, thinking_expanded=True)
            assert st.show_thinking is False
            assert st.thinking_expanded is True
        except ImportError:
            pytest.skip("Textual not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])