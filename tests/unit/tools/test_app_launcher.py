#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the app_launcher module.

Tests cover application launching functionality including:
- Generic application launching via launch_app
- Folder opening via open_folder
- File opening via open_file

Note: open_calculator, open_notepad, open_cmd, open_explorer have been
consolidated into the unified launch_app tool (refactored for simplicity).
"""

import pytest
import json
import subprocess
from unittest.mock import patch, MagicMock
from pathlib import Path


class TestAppLauncher:
    """Test suite for app_launcher module."""

    @patch("subprocess.Popen")
    def test_launch_app_calculator(self, mock_popen):
        """Test launching calculator via launch_app."""
        from tools.app_launcher import launch_app

        mock_popen.return_value = MagicMock()

        result = launch_app("calculator")
        data = json.loads(result)

        assert data["success"] is True
        assert data["app"] == "calculator"
        mock_popen.assert_called_once()

    @patch("subprocess.Popen")
    def test_launch_app_notepad(self, mock_popen):
        """Test launching notepad via launch_app."""
        from tools.app_launcher import launch_app

        mock_popen.return_value = MagicMock()

        result = launch_app("notepad")
        data = json.loads(result)

        assert data["success"] is True
        assert data["app"] == "notepad"

    @patch("subprocess.Popen")
    def test_launch_app_cmd(self, mock_popen):
        """Test launching cmd via launch_app."""
        from tools.app_launcher import launch_app

        mock_popen.return_value = MagicMock()

        result = launch_app("cmd")
        data = json.loads(result)

        assert data["success"] is True
        assert data["app"] == "cmd"

    @patch("subprocess.Popen")
    def test_launch_app_explorer(self, mock_popen):
        """Test launching explorer via launch_app."""
        from tools.app_launcher import launch_app

        mock_popen.return_value = MagicMock()

        result = launch_app("explorer")
        data = json.loads(result)

        assert data["success"] is True

    def test_launch_app_invalid_name(self):
        """Test launching invalid application name."""
        from tools.app_launcher import launch_app

        # Should still return success but may fail to launch
        result = launch_app("nonexistent_app_xyz")
        data = json.loads(result)

        # The function should handle this gracefully
        assert "success" in data

    @patch("subprocess.Popen")
    def test_launch_app_with_args(self, mock_popen):
        """Test launching app with arguments."""
        from tools.app_launcher import launch_app

        mock_popen.return_value = MagicMock()

        result = launch_app("explorer", args=["/home"])
        data = json.loads(result)

        assert data["success"] is True

    def test_find_app_path(self):
        """Test finding application path."""
        from tools.app_launcher import find_app_path

        # Calculator should be found
        result = find_app_path("calculator")
        assert result is not None

        # Direct name should be returned
        result = find_app_path("notepad")
        assert result is not None


class TestOpenFolder:
    """Test suite for open_folder function."""

    def test_open_folder_default(self):
        """Test open_folder with default path (current directory)."""
        from tools.app_launcher import open_folder

        result = open_folder()
        assert isinstance(result, str)

        data = json.loads(result)
        assert isinstance(data, dict)
        assert "success" in data

    @patch("subprocess.Popen")
    def test_open_folder_with_path(self, mock_popen):
        """Test open_folder with specific path."""
        from tools.app_launcher import open_folder

        mock_popen.return_value = MagicMock()
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


class TestOpenFile:
    """Test suite for open_file function."""

    @patch("os.startfile" if __import__("platform").system() == "Windows" else "subprocess.Popen")
    def test_open_file_success(self, mock_open):
        """Test successful file opening."""
        from tools.app_launcher import open_file

        # Use a real file that should exist
        test_file = Path(__file__).resolve()
        result = open_file(str(test_file))

        data = json.loads(result)
        assert data["success"] is True

    def test_open_file_nonexistent(self):
        """Test opening nonexistent file."""
        from tools.app_launcher import open_file

        result = open_file("C:/nonexistent_file_xyz.txt")

        data = json.loads(result)
        assert data["success"] is False
        assert "error" in data

    def test_open_file_is_directory(self):
        """Test opening a directory (should fail)."""
        from tools.app_launcher import open_file

        result = open_file(str(Path.home()))

        data = json.loads(result)
        assert data["success"] is False
        assert "error" in data


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

    def test_open_folder_schema(self):
        """Test open_folder schema structure."""
        from tools.app_launcher import OPEN_FOLDER_SCHEMA

        assert "name" in OPEN_FOLDER_SCHEMA
        assert OPEN_FOLDER_SCHEMA["name"] == "open_folder"
        assert "description" in OPEN_FOLDER_SCHEMA
        assert "parameters" in OPEN_FOLDER_SCHEMA

    def test_open_file_schema(self):
        """Test open_file schema structure."""
        from tools.app_launcher import OPEN_FILE_SCHEMA

        assert "name" in OPEN_FILE_SCHEMA
        assert OPEN_FILE_SCHEMA["name"] == "open_file"
        assert "parameters" in OPEN_FILE_SCHEMA


class TestAppLauncherRegistry:
    """Test tool registry integration."""

    def test_tools_registered(self):
        """Test that all app launcher tools are registered."""
        from tools.registry import registry

        # Refactored: only 3 tools remain
        expected_tools = [
            "launch_app",
            "open_folder",
            "open_file",
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