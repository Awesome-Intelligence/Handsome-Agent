#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for TUI application boot and initialization.

Tests cover:
- Normal boot flow
- Skip onboarding (--skip-onboarding)
- Configuration detection
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import sys


class TestTextualAvailability:
    """Test Textual library availability detection."""

    def test_check_textual_available(self):
        """Test checking if Textual is available."""
        from tui.textual_app.app import check_textual_available
        
        # Should return a boolean
        result = check_textual_available()
        assert isinstance(result, bool)

    def test_get_textual_import_error_no_error(self):
        """Test getting import error when Textual is available."""
        from tui.textual_app.app import (
            get_textual_import_error,
            TEXTUAL_AVAILABLE
        )
        
        if TEXTUAL_AVAILABLE:
            result = get_textual_import_error()
            assert result is None

    def test_get_textual_install_hint(self):
        """Test getting Textual install hint."""
        from tui.textual_app.app import get_textual_install_hint
        
        hint = get_textual_install_hint()
        assert isinstance(hint, str)
        assert len(hint) > 0
        assert "Textual" in hint or "textual" in hint.lower()


class TestTextualCompatibility:
    """Test Textual compatibility checks."""

    def test_is_textual_compatible_returns_tuple(self):
        """Test that is_textual_compatible returns a tuple."""
        from tui.textual_app.app import is_textual_compatible
        
        result = is_textual_compatible()
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert result[1] is None or isinstance(result[1], str)

    @patch('sys.stdout.isatty', return_value=True)
    def test_is_textual_compatible_narrow_terminal(self, mock_isatty):
        """Test compatibility check with narrow terminal."""
        from tui.textual_app.app import is_textual_compatible
        
        with patch('shutil.get_terminal_size') as mock_size:
            mock_size.return_value = MagicMock(columns=30)
            result = is_textual_compatible()
            
            assert result[0] is False
            assert "narrow" in result[1].lower() or "terminal" in result[1].lower()

    @patch('sys.stdout.isatty', return_value=False)
    def test_is_textual_compatible_non_tty(self, mock_isatty):
        """Test compatibility check in non-TTY environment."""
        from tui.textual_app.app import is_textual_compatible
        
        result = is_textual_compatible()
        
        assert result[0] is False


class TestAppInitialization:
    """Test HandsomeAgentApp initialization."""

    def test_app_creation_basic(self):
        """Test basic app creation with minimal parameters."""
        from tui.textual_app.app import TEXTUAL_AVAILABLE
        
        if not TEXTUAL_AVAILABLE:
            pytest.skip("Textual not available")
        
        from tui.textual_app.app import HandsomeAgentApp
        
        app = HandsomeAgentApp()
        
        assert app.model_name == "Handsome Agent"
        assert app.provider is None
        assert app.session_id is None

    def test_app_creation_with_params(self):
        """Test app creation with custom parameters."""
        from tui.textual_app.app import TEXTUAL_AVAILABLE
        
        if not TEXTUAL_AVAILABLE:
            pytest.skip("Textual not available")
        
        from tui.textual_app.app import HandsomeAgentApp
        
        app = HandsomeAgentApp(
            model_name="gpt-4o",
            provider="OpenAI",
            cwd="/test/path",
            session_id="test-session-123",
            context_length=128000,
        )
        
        assert app.model_name == "gpt-4o"
        assert app.provider == "OpenAI"
        assert app.cwd == "/test/path"
        assert app.session_id == "test-session-123"
        assert app.context_length == 128000

    def test_app_initial_state(self):
        """Test app initial state properties."""
        from tui.textual_app.app import TEXTUAL_AVAILABLE
        
        if not TEXTUAL_AVAILABLE:
            pytest.skip("Textual not available")
        
        from tui.textual_app.app import HandsomeAgentApp
        
        app = HandsomeAgentApp()
        
        # Check initial state
        assert app._is_loading is False
        assert app._is_streaming is False
        assert app._streaming_text == ""

    def test_app_theme_attributes(self):
        """Test app theme-related attributes."""
        from tui.textual_app.app import TEXTUAL_AVAILABLE
        
        if not TEXTUAL_AVAILABLE:
            pytest.skip("Textual not available")
        
        from tui.textual_app.app import HandsomeAgentApp
        
        app = HandsomeAgentApp()
        
        # Theme should be initialized
        assert hasattr(app, 'theme_id')
        assert app.theme_id == "default"
        
        # Markdown should be enabled by default
        assert app._markdown_enabled is True

    def test_app_loading_styles(self):
        """Test app loading animation styles."""
        from tui.textual_app.app import TEXTUAL_AVAILABLE
        
        if not TEXTUAL_AVAILABLE:
            pytest.skip("Textual not available")
        
        from tui.textual_app.app import HandsomeAgentApp
        
        app = HandsomeAgentApp()
        
        # Check loading frames are defined
        assert "dots" in app._LOADING_FRAMES
        assert "circle" in app._LOADING_FRAMES
        assert "braille" in app._LOADING_FRAMES
        assert "pulse" in app._LOADING_FRAMES
        
        # Default style should be dots
        assert app._loading_style == "dots"

    def test_app_builtin_models(self):
        """Test app builtin models list."""
        from tui.textual_app.app import TEXTUAL_AVAILABLE
        
        if not TEXTUAL_AVAILABLE:
            pytest.skip("Textual not available")
        
        from tui.textual_app.app import HandsomeAgentApp
        
        app = HandsomeAgentApp()
        
        # Check builtin models are defined
        assert len(app._builtin_models) > 0
        
        # First model should be Handsome Agent
        model_values = [m[0] for m in app._builtin_models]
        assert "Handsome Agent" in model_values
        assert "custom" in model_values


class TestAppMethods:
    """Test HandsomeAgentApp methods."""

    def test_set_loading_style_valid(self):
        """Test setting valid loading style."""
        from tui.textual_app.app import TEXTUAL_AVAILABLE
        
        if not TEXTUAL_AVAILABLE:
            pytest.skip("Textual not available")
        
        from tui.textual_app.app import HandsomeAgentApp
        
        app = HandsomeAgentApp()
        
        result = app.set_loading_style("circle")
        assert result is True
        assert app._loading_style == "circle"

    def test_set_loading_style_invalid(self):
        """Test setting invalid loading style."""
        from tui.textual_app.app import TEXTUAL_AVAILABLE
        
        if not TEXTUAL_AVAILABLE:
            pytest.skip("Textual not available")
        
        from tui.textual_app.app import HandsomeAgentApp
        
        app = HandsomeAgentApp()
        
        result = app.set_loading_style("invalid_style")
        assert result is False

    def test_cycle_loading_style(self):
        """Test cycling through loading styles."""
        from tui.textual_app.app import TEXTUAL_AVAILABLE
        
        if not TEXTUAL_AVAILABLE:
            pytest.skip("Textual not available")
        
        from tui.textual_app.app import HandsomeAgentApp
        
        app = HandsomeAgentApp()
        
        initial_style = app._loading_style
        next_style = app.cycle_loading_style()
        
        # Should return a different style
        assert next_style != initial_style

    def test_is_streaming(self):
        """Test streaming state check."""
        from tui.textual_app.app import TEXTUAL_AVAILABLE
        
        if not TEXTUAL_AVAILABLE:
            pytest.skip("Textual not available")
        
        from tui.textual_app.app import HandsomeAgentApp
        
        app = HandsomeAgentApp()
        
        # Initially not streaming
        assert app.is_streaming() is False
        
        # After starting streaming
        app._is_streaming = True
        assert app.is_streaming() is True

    def test_cancel_streaming(self):
        """Test cancelling streaming."""
        from tui.textual_app.app import TEXTUAL_AVAILABLE
        
        if not TEXTUAL_AVAILABLE:
            pytest.skip("Textual not available")
        
        from tui.textual_app.app import HandsomeAgentApp
        
        app = HandsomeAgentApp()
        
        # Set streaming state
        app._is_streaming = True
        app._streaming_text = "Some text"
        app._streaming_widget_id = "test-widget"
        
        # Cancel streaming
        app.cancel_streaming()
        
        # Check state is reset
        assert app._is_streaming is False
        assert app._streaming_text == ""
        assert app._streaming_widget_id is None

    def test_format_context_tokens(self):
        """Test context token formatting."""
        from tui.textual_app.app import TEXTUAL_AVAILABLE
        
        if not TEXTUAL_AVAILABLE:
            pytest.skip("Textual not available")
        
        from tui.textual_app.app import HandsomeAgentApp
        
        app = HandsomeAgentApp()
        
        # Test millions
        assert app._format_context(2000000) == "2M"
        assert app._format_context(1500000) == "1.5M"
        
        # Test thousands
        assert app._format_context(128000) == "128K"
        assert app._format_context(64500) == "64.5K"
        
        # Test small numbers
        assert app._format_context(500) == "500"
        
        # Test None
        assert app._format_context(None) == "?"


class TestRunTextualApp:
    """Test run_textual_app function."""

    @patch('tui.textual_app.app.TEXTUAL_AVAILABLE', False)
    def test_run_textual_app_not_available(self):
        """Test run_textual_app when Textual is not available."""
        from tui.textual_app.app import run_textual_app
        
        with patch('builtins.print') as mock_print:
            result = run_textual_app()
            assert result == 1
            mock_print.assert_called()

    @patch('tui.textual_app.app.TEXTUAL_AVAILABLE', True)
    @patch('tui.textual_app.app.is_textual_compatible')
    @patch('tui.textual_app.app.HandsomeAgentApp')
    def test_run_textual_app_not_compatible(self, mock_app_class, mock_compatible):
        """Test run_textual_app when environment is not compatible."""
        from tui.textual_app.app import run_textual_app
        
        mock_compatible.return_value = (False, "Non-TTY environment")
        
        with patch('builtins.print') as mock_print:
            result = run_textual_app()
            assert result == 1

    @patch('tui.textual_app.app.TEXTUAL_AVAILABLE', True)
    @patch('tui.textual_app.app.is_textual_compatible')
    def test_run_textual_app_returns_app_exit_code(self, mock_compatible):
        """Test that run_textual_app returns the app's exit code."""
        from tui.textual_app.app import run_textual_app, HandsomeAgentApp
        
        mock_compatible.return_value = (True, None)
        
        mock_app = MagicMock()
        mock_app.run.return_value = 0
        HandsomeAgentApp.return_value = mock_app
        
        result = run_textual_app()
        
        # Should return the exit code from app.run()
        assert result == 0


class TestCreateFallbackApp:
    """Test create_fallback_app function."""

    def test_create_fallback_app_basic(self):
        """Test create_fallback_app basic functionality."""
        from tui.textual_app.app import create_fallback_app
        
        # Should not raise
        with patch('builtins.print'):
            create_fallback_app(
                model_name="test-model",
                provider="test-provider",
                cwd="/test/path"
            )

    def test_create_fallback_app_with_session(self):
        """Test create_fallback_app with session ID."""
        from tui.textual_app.app import create_fallback_app
        
        with patch('builtins.print'):
            create_fallback_app(
                model_name="test-model",
                session_id="test-session"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
