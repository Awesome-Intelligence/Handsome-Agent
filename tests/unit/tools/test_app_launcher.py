#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the app_launcher module.

Tests cover application launching functionality including:
- Calculator launching
- Notepad launching
- Command prompt launching
- File explorer launching
- Generic application launching
"""

import pytest
import json
import subprocess
from unittest.mock import patch, MagicMock
from pathlib import Path


class TestAppLauncher:
    """Test suite for app_launcher module."""

    def test_open_calculator_returns_json(self):
        """Test that open_calculator returns valid JSON."""
        from tools.app_launcher import open_calculator
        
        result = open_calculator()
        assert isinstance(result, str)
        
        # Should be valid JSON
        data = json.loads(result)
        assert isinstance(data, dict)
        assert "success" in data

    def test_open_notepad_returns_json(self):
        """Test that open_notepad returns valid JSON."""
        from tools.app_launcher import open_notepad
        
        result = open_notepad()
        assert isinstance(result, str)
        
        # Should be valid JSON
        data = json.loads(result)
        assert isinstance(data, dict)
        assert "success" in data

    def test_open_cmd_returns_json(self):
        """Test that open_cmd returns valid JSON."""
        from tools.app_launcher import open_cmd
        
        result = open_cmd()
        assert isinstance(result, str)
        
        # Should be valid JSON
        data = json.loads(result)
        assert isinstance(data, dict)
        assert "success" in data

    def test_open_explorer_returns_json(self):
        """Test that open_explorer returns valid JSON."""
        from tools.app_launcher import open_explorer
        
        result = open_explorer()
        assert isinstance(result, str)
        
        # Should be valid JSON
        data = json.loads(result)
        assert isinstance(data, dict)
        assert "success" in data

    def test_open_explorer_with_path(self):
        """Test open_explorer with specific path."""
        from tools.app_launcher import open_explorer
        
        test_path = str(Path.home())
        result = open_explorer(path=test_path)
        
        data = json.loads(result)
        assert data["success"] is True

    def test_open_folder_default(self):
        """Test open_folder with default path (current directory)."""
        from tools.app_launcher import open_folder
        
        result = open_folder()
        assert isinstance(result, str)
        
        data = json.loads(result)
        assert isinstance(data, dict)
        assert "success" in data

    def test_open_folder_with_path(self):
        """Test open_folder with specific path."""
        from tools.app_launcher import open_folder
        
        test_path = str(Path.home())
        result = open_folder(path=test_path)
        
        data = json.loads(result)
        assert data["success"] is True

    def test_open_folder_nonexistent(self):
        """Test open_folder with nonexistent path."""
        from tools.app_launcher import open_folder
        
        result = open_folder(path="C:/nonexistent_folder_xyz")
        
        data = json.loads(result)
        assert data["success"] is False
        assert "error" in data

    @patch('subprocess.Popen')
    def test_launch_app_success(self, mock_popen):
        """Test successful application launch."""
        from tools.app_launcher import launch_app
        
        mock_popen.return_value = MagicMock()
        
        result = launch_app('notepad')
        data = json.loads(result)
        
        assert data["success"] is True
        assert data["app"] == 'notepad'
        mock_popen.assert_called_once()

    def test_launch_app_invalid_name(self):
        """Test launching invalid application name."""
        from tools.app_launcher import launch_app
        
        # Should still return success but may fail to launch
        result = launch_app('nonexistent_app_xyz')
        data = json.loads(result)
        
        # The function should handle this gracefully
        assert "success" in data

    @patch('subprocess.Popen')
    def test_launch_app_with_args(self, mock_popen):
        """Test launching app with arguments."""
        from tools.app_launcher import launch_app
        
        mock_popen.return_value = MagicMock()
        
        result = launch_app('explorer', args=['/home'])
        data = json.loads(result)
        
        assert data["success"] is True

    def test_find_app_path(self):
        """Test finding application path."""
        from tools.app_launcher import find_app_path
        
        # Calculator should be found
        result = find_app_path('calculator')
        assert result is not None
        
        # Direct name should be returned
        result = find_app_path('notepad')
        assert result is not None


class TestAppLauncherSchemas:
    """Test tool schemas for app launcher."""

    def test_launch_app_schema(self):
        """Test launch_app schema structure."""
        from tools.app_launcher import LAUNCH_APP_SCHEMA
        
        assert "name" in LAUNCH_APP_SCHEMA
        assert LAUNCH_APP_SCHEMA["name"] == "launch_app"
        assert "description" in LAUNCH_APP_SCHEMA
        assert "parameters" in LAUNCH_APP_SCHEMA
        
        params = LAUNCH_APP_SCHEMA["parameters"]
        assert "type" in params
        assert params["type"] == "object"
        assert "properties" in params
        assert "app_name" in params["properties"]

    def test_open_calculator_schema(self):
        """Test open_calculator schema structure."""
        from tools.app_launcher import OPEN_CALCULATOR_SCHEMA
        
        assert "name" in OPEN_CALCULATOR_SCHEMA
        assert OPEN_CALCULATOR_SCHEMA["name"] == "open_calculator"
        assert "parameters" in OPEN_CALCULATOR_SCHEMA

    def test_open_notepad_schema(self):
        """Test open_notepad schema structure."""
        from tools.app_launcher import OPEN_NOTEPAD_SCHEMA
        
        assert "name" in OPEN_NOTEPAD_SCHEMA
        assert OPEN_NOTEPAD_SCHEMA["name"] == "open_notepad"

    def test_open_cmd_schema(self):
        """Test open_cmd schema structure."""
        from tools.app_launcher import OPEN_CMD_SCHEMA
        
        assert "name" in OPEN_CMD_SCHEMA
        assert OPEN_CMD_SCHEMA["name"] == "open_cmd"

    def test_open_explorer_schema(self):
        """Test open_explorer schema structure."""
        from tools.app_launcher import OPEN_EXPLORER_SCHEMA
        
        assert "name" in OPEN_EXPLORER_SCHEMA
        assert OPEN_EXPLORER_SCHEMA["name"] == "open_explorer"

    def test_open_folder_schema(self):
        """Test open_folder schema structure."""
        from tools.app_launcher import OPEN_FOLDER_SCHEMA
        
        assert "name" in OPEN_FOLDER_SCHEMA
        assert OPEN_FOLDER_SCHEMA["name"] == "open_folder"
        assert "description" in OPEN_FOLDER_SCHEMA
        assert "parameters" in OPEN_FOLDER_SCHEMA


class TestAppLauncherRegistry:
    """Test tool registry integration."""

    def test_tools_registered(self):
        """Test that all app launcher tools are registered."""
        from tools.registry import registry
        
        expected_tools = [
            "launch_app",
            "open_calculator",
            "open_notepad",
            "open_cmd",
            "open_explorer",
            "open_folder"
        ]
        
        for tool_name in expected_tools:
            tool = registry.get(tool_name)
            assert tool is not None, f"Tool {tool_name} should be registered"

    def test_tools_have_handlers(self):
        """Test that all tools have handlers."""
        from tools.registry import registry
        
        tools = registry.get_by_toolset("app_launcher")
        assert len(tools) > 0
        
        for tool in tools:
            assert tool.handler is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
