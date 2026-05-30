#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the CLI module UI functions.

Tests cover colors, themes, printing functions, and status bar.
"""

import pytest
from unittest.mock import patch, MagicMock
import sys


class TestColors:
    """Test color constants."""
    
    def test_color_constants_exist(self):
        """Test that all color constants are defined."""
        from cli.ui import Colors
        
        assert hasattr(Colors, 'RESET')
        assert hasattr(Colors, 'GREEN')
        assert hasattr(Colors, 'GREEN_BRIGHT')
        assert hasattr(Colors, 'GREEN_DIM')
        assert hasattr(Colors, 'GRAY')
        assert hasattr(Colors, 'RED')
        assert hasattr(Colors, 'YELLOW')
        assert hasattr(Colors, 'BLUE')
        assert hasattr(Colors, 'BOLD')
    
    def test_ansi_format(self):
        """Test that colors use ANSI escape codes."""
        from cli.ui import Colors
        
        # All colors should start with escape character
        assert Colors.RESET.startswith('\033')
        assert Colors.GREEN.startswith('\033')
        assert Colors.RED.startswith('\033')
    
    def test_color_reset(self):
        """Test that RESET is the reset code."""
        from cli.ui import Colors
        
        assert Colors.RESET == "\033[0m"


class TestTheme:
    """Test theme constants."""
    
    def test_theme_colors_exist(self):
        """Test that all theme colors are defined."""
        from cli.ui import Theme
        
        assert hasattr(Theme, 'BORDER')
        assert hasattr(Theme, 'PRIMARY')
        assert hasattr(Theme, 'SECONDARY')
        assert hasattr(Theme, 'ACCENT')
        assert hasattr(Theme, 'SUCCESS')
        assert hasattr(Theme, 'ERROR')
        assert hasattr(Theme, 'WARNING')
        assert hasattr(Theme, 'INFO')
    
    def test_theme_uses_colors(self):
        """Test that theme uses color constants."""
        from cli.ui import Theme, Colors
        
        # Theme should reference Colors
        assert Theme.BORDER == Colors.GREEN or Theme.BORDER == Colors.GRAY_DIM
        assert Theme.SUCCESS == Colors.GREEN or Theme.SUCCESS == Colors.GREEN_BRIGHT


class TestPrintFunctions:
    """Test print utility functions."""
    
    def test_get_terminal_width(self):
        """Test getting terminal width."""
        from cli.ui import get_terminal_width
        
        width = get_terminal_width()
        
        assert isinstance(width, int)
        assert width > 0
    
    def test_strip_ansi(self):
        """Test stripping ANSI codes from text."""
        from cli.ui import strip_ansi
        
        text_with_ansi = "\033[1m\033[38;2;139;154;70mBold Green\033[0m"
        stripped = strip_ansi(text_with_ansi)
        
        assert "Bold Green" in stripped
        assert "\033" not in stripped
    
    def test_supports_color(self):
        """Test color support detection."""
        from cli.ui import supports_color
        
        # Should return boolean
        result = supports_color()
        assert isinstance(result, bool)
    
    def test_enable_ansi_support(self):
        """Test enabling ANSI support."""
        from cli.ui import enable_ansi_support
        
        # Should not raise
        enable_ansi_support()


class TestBorderFunctions:
    """Test border and divider functions."""
    
    @patch('sys.stdout')
    def test_print_top_border(self, mock_stdout):
        """Test printing top border."""
        from cli.ui import print_top_border
        
        print_top_border(width=50)
        
        # Should print border line
        assert mock_stdout.write.called
    
    @patch('sys.stdout')
    def test_print_bottom_border(self, mock_stdout):
        """Test printing bottom border."""
        from cli.ui import print_bottom_border
        
        print_bottom_border(width=50)
        
        assert mock_stdout.write.called
    
    @patch('sys.stdout')
    def test_print_divider(self, mock_stdout):
        """Test printing divider."""
        from cli.ui import print_divider
        
        print_divider()
        
        assert mock_stdout.write.called


class TestMessageFunctions:
    """Test message printing functions."""
    
    @patch('sys.stdout')
    def test_print_success(self, mock_stdout):
        """Test printing success message."""
        from cli.ui import print_success
        
        print_success("Operation completed")
        
        assert mock_stdout.write.called
    
    @patch('sys.stdout')
    def test_print_error(self, mock_stdout):
        """Test printing error message."""
        from cli.ui import print_error
        
        print_error("Something went wrong")
        
        assert mock_stdout.write.called
    
    @patch('sys.stdout')
    def test_print_warning(self, mock_stdout):
        """Test printing warning message."""
        from cli.ui import print_warning
        
        print_warning("Be careful")
        
        assert mock_stdout.write.called
    
    @patch('sys.stdout')
    def test_print_info(self, mock_stdout):
        """Test printing info message."""
        from cli.ui import print_info
        
        print_info("Here is some information")
        
        assert mock_stdout.write.called


class TestHeaderFunctions:
    """Test header printing functions."""
    
    @patch('sys.stdout')
    def test_print_header(self, mock_stdout):
        """Test printing header."""
        from cli.ui import print_header
        
        print_header("Test Header")
        
        assert mock_stdout.write.called
    
    @patch('sys.stdout')
    def test_print_header_with_subtitle(self, mock_stdout):
        """Test printing header with subtitle."""
        from cli.ui import print_header
        
        print_header("Test Header", subtitle="Test Subtitle")
        
        assert mock_stdout.write.called
    
    @patch('sys.stdout')
    def test_print_header_text(self, mock_stdout):
        """Test printing header text."""
        from cli.ui import print_header_text
        
        print_header_text("Header Text")
        
        assert mock_stdout.write.called


class TestMenuFunctions:
    """Test menu printing functions."""
    
    @patch('sys.stdout')
    def test_print_menu(self, mock_stdout):
        """Test printing menu."""
        from cli.ui import print_menu
        
        options = [
            ("option1", "First Option"),
            ("option2", "Second Option"),
            ("option3", "Third Option")
        ]
        
        print_menu(options, selected=1)
        
        assert mock_stdout.write.called
    
    @patch('sys.stdout')
    def test_print_config_item(self, mock_stdout):
        """Test printing config item."""
        from cli.ui import print_config_item
        
        print_config_item("Key", "Value")
        
        assert mock_stdout.write.called
    
    @patch('sys.stdout')
    def test_print_list(self, mock_stdout):
        """Test printing list."""
        from cli.ui import print_list
        
        items = ["Item 1", "Item 2", "Item 3"]
        print_list(items, title="Test List")
        
        assert mock_stdout.write.called


class TestStepFunctions:
    """Test step indicator functions."""
    
    @patch('sys.stdout')
    def test_print_step(self, mock_stdout):
        """Test printing step indicator."""
        from cli.ui import print_step
        
        print_step(1, 3, "Test Step")
        
        assert mock_stdout.write.called
    
    @patch('sys.stdout')
    def test_print_substep(self, mock_stdout):
        """Test printing substep."""
        from cli.ui import print_substep
        
        print_substep("Substep content")
        
        assert mock_stdout.write.called
    
    @patch('sys.stdout')
    def test_print_end_step(self, mock_stdout):
        """Test printing end step."""
        from cli.ui import print_end_step
        
        print_end_step()
        
        assert mock_stdout.write.called


class TestPromptFunctions:
    """Test prompt functions."""
    
    @patch('sys.stdout')
    def test_print_prompt(self, mock_stdout):
        """Test printing prompt."""
        from cli.ui import print_prompt
        
        result = print_prompt()
        
        assert isinstance(result, str)
        assert mock_stdout.write.called
    
    @patch('sys.stdout')
    def test_print_user_input(self, mock_stdout):
        """Test printing user input prompt."""
        from cli.ui import print_user_input
        
        print_user_input("Enter your name")
        
        assert mock_stdout.write.called


class TestBannerFunctions:
    """Test banner printing functions."""
    
    @patch('sys.stdout')
    def test_print_banner(self, mock_stdout):
        """Test printing banner."""
        from cli.ui import print_banner
        
        print_banner()
        
        assert mock_stdout.write.called


class TestStatusBar:
    """Test StatusBar class."""
    
    def test_status_bar_creation(self):
        """Test creating a status bar."""
        from cli.ui import StatusBar
        
        status = StatusBar()
        
        assert status.model == "Unknown"
        assert status.provider == ""
        assert status.token_count == 0
    
    def test_update_model(self):
        """Test updating model name."""
        from cli.ui import StatusBar
        
        status = StatusBar()
        status.update_model("GPT-4", "OpenAI")
        
        assert status.model == "GPT-4"
        assert status.provider == "OpenAI"
    
    def test_add_tokens(self):
        """Test adding tokens."""
        from cli.ui import StatusBar
        
        status = StatusBar()
        status.add_tokens(100)
        status.add_tokens(50)
        
        assert status.token_count == 150
    
    def test_add_cost(self):
        """Test adding cost."""
        from cli.ui import StatusBar
        
        status = StatusBar()
        status.add_cost(0.01)
        status.add_cost(0.02)
        
        assert status.cost == 0.03
    
    def test_set_tools(self):
        """Test setting enabled tools."""
        from cli.ui import StatusBar
        
        status = StatusBar()
        status.set_tools(["search", "calculator"])
        
        assert len(status.tools_enabled) == 2
        assert "search" in status.tools_enabled
    
    def test_toggle_yolo_mode(self):
        """Test toggling YOLO mode."""
        from cli.ui import StatusBar
        
        status = StatusBar()
        status.toggle_yolo(True)
        
        assert status.yolo_mode is True
    
    def test_set_connected(self):
        """Test setting connection status."""
        from cli.ui import StatusBar
        
        status = StatusBar()
        status.set_connected(True)
        
        assert status.connected is True
    
    def test_get_duration(self):
        """Test getting session duration."""
        from cli.ui import StatusBar
        
        status = StatusBar()
        duration = status.get_duration()
        
        assert isinstance(duration, str)
        assert "m" in duration or "s" in duration
    
    def test_render_status_bar(self):
        """Test rendering status bar."""
        from cli.ui import StatusBar
        
        status = StatusBar()
        status.update_model("GPT-4", "OpenAI")
        status.add_tokens(1000)
        
        rendered = status.render()
        
        assert isinstance(rendered, str)
        assert len(rendered) > 0


class TestSpinner:
    """Test Spinner class."""
    
    def test_spinner_creation(self):
        """Test creating a spinner."""
        from cli.ui import Spinner
        
        spinner = Spinner("Loading")
        
        assert spinner.message == "Loading"
        assert spinner.running is False
    
    @patch('sys.stdout')
    def test_spinner_start(self, mock_stdout):
        """Test starting spinner."""
        from cli.ui import Spinner
        
        spinner = Spinner("Loading")
        spinner.start()
        
        assert spinner.running is True
        assert mock_stdout.write.called
    
    @patch('sys.stdout')
    def test_spinner_stop_success(self, mock_stdout):
        """Test stopping spinner with success."""
        from cli.ui import Spinner
        
        spinner = Spinner("Loading")
        spinner.running = True
        spinner.stop(success=True)
        
        assert spinner.running is False
    
    @patch('sys.stdout')
    def test_spinner_stop_failure(self, mock_stdout):
        """Test stopping spinner with failure."""
        from cli.ui import Spinner
        
        spinner = Spinner("Loading")
        spinner.running = True
        spinner.stop(success=False)
        
        assert spinner.running is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
