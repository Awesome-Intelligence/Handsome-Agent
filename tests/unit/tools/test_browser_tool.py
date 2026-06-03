#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the browser_tool module.

Tests cover browser automation functionality including:
- Browser navigation
- Page snapshots
- Element clicking
- Text input
- Scrolling
- Keyboard actions
"""

import pytest
import json
from unittest.mock import patch, MagicMock


class TestBrowserNavigate:
    """Test suite for browser_navigate."""

    def test_navigate_returns_json(self):
        """Test that navigate returns valid JSON."""
        from tools.browser_tool import browser_navigate
        
        # This will fail without browser CLI, but should return proper error JSON
        result = browser_navigate(url="https://example.com")
        assert isinstance(result, str)
        
        data = json.loads(result)
        assert "success" in data
        assert "task_id" in data

    def test_navigate_with_task_id(self):
        """Test navigate with custom task_id."""
        from tools.browser_tool import browser_navigate
        
        result = browser_navigate(url="https://example.com", task_id="test_task")
        data = json.loads(result)
        
        assert data["task_id"] == "test_task"

    def test_navigate_new_tab(self):
        """Test navigate with new_tab option."""
        from tools.browser_tool import browser_navigate
        
        result = browser_navigate(url="https://example.com", new_tab=True)
        data = json.loads(result)
        
        assert "success" in data


class TestBrowserSnapshot:
    """Test suite for browser_snapshot."""

    def test_snapshot_returns_json(self):
        """Test that snapshot returns valid JSON."""
        from tools.browser_tool import browser_snapshot
        
        result = browser_snapshot(task_id="test_task")
        assert isinstance(result, str)
        
        data = json.loads(result)
        assert "success" in data
        assert "task_id" in data


class TestBrowserClick:
    """Test suite for browser_click."""

    def test_click_returns_json(self):
        """Test that click returns valid JSON."""
        from tools.browser_tool import browser_click
        
        result = browser_click(ref="@e1", task_id="test_task")
        assert isinstance(result, str)
        
        data = json.loads(result)
        assert "success" in data
        assert data["ref"] == "@e1"


class TestBrowserType:
    """Test suite for browser_type."""

    def test_type_returns_json(self):
        """Test that type returns valid JSON."""
        from tools.browser_tool import browser_type
        
        result = browser_type(ref="@e1", text="test input", task_id="test_task")
        assert isinstance(result, str)
        
        data = json.loads(result)
        assert "success" in data


class TestBrowserScroll:
    """Test suite for browser_scroll."""

    def test_scroll_returns_json(self):
        """Test that scroll returns valid JSON."""
        from tools.browser_tool import browser_scroll
        
        result = browser_scroll(task_id="test_task")
        assert isinstance(result, str)
        
        data = json.loads(result)
        assert "success" in data


class TestBrowserPress:
    """Test suite for browser_press."""

    def test_press_returns_json(self):
        """Test that press returns valid JSON."""
        from tools.browser_tool import browser_press
        
        result = browser_press(key="Enter", task_id="test_task")
        assert isinstance(result, str)
        
        data = json.loads(result)
        assert "success" in data


class TestBrowserBack:
    """Test suite for browser_back."""

    def test_back_returns_json(self):
        """Test that back returns valid JSON."""
        from tools.browser_tool import browser_back
        
        result = browser_back(task_id="test_task")
        assert isinstance(result, str)
        
        data = json.loads(result)
        assert "success" in data


class TestBrowserVision:
    """Test suite for browser_vision."""

    def test_vision_returns_json(self):
        """Test that vision returns valid JSON."""
        from tools.browser_tool import browser_vision
        
        result = browser_vision(question="What is on the page?", task_id="test_task")
        assert isinstance(result, str)
        
        data = json.loads(result)
        assert "success" in data


class TestBrowserConsole:
    """Test suite for browser_console."""

    def test_console_returns_json(self):
        """Test that console returns valid JSON."""
        from tools.browser_tool import browser_console
        
        result = browser_console(expression="document.title", task_id="test_task")
        assert isinstance(result, str)
        
        data = json.loads(result)
        assert "success" in data


class TestBrowserSchemas:
    """Test tool schemas for browser."""

    def test_browser_navigate_schema(self):
        """Test browser_navigate schema structure."""
        from tools.browser_tool import BROWSER_NAVIGATE_SCHEMA
        
        assert "name" in BROWSER_NAVIGATE_SCHEMA
        assert BROWSER_NAVIGATE_SCHEMA["name"] == "browser_navigate"
        assert "parameters" in BROWSER_NAVIGATE_SCHEMA

    def test_browser_snapshot_schema(self):
        """Test browser_snapshot schema structure."""
        from tools.browser_tool import BROWSER_SNAPSHOT_SCHEMA
        
        assert "name" in BROWSER_SNAPSHOT_SCHEMA
        assert BROWSER_SNAPSHOT_SCHEMA["name"] == "browser_snapshot"

    def test_browser_click_schema(self):
        """Test browser_click schema structure."""
        from tools.browser_tool import BROWSER_CLICK_SCHEMA
        
        assert "name" in BROWSER_CLICK_SCHEMA
        assert BROWSER_CLICK_SCHEMA["name"] == "browser_click"


class TestBrowserRegistry:
    """Test tool registry integration."""

    def test_tools_registered(self):
        """Test that all browser tools are registered."""
        from tools.registry import registry
        
        expected_tools = [
            "browser_navigate",
            "browser_snapshot",
            "browser_click",
            "browser_type",
            "browser_scroll",
            "browser_press",
            "browser_back",
            "browser_get_images",
            "browser_vision",
            "browser_console"
        ]
        
        for tool_name in expected_tools:
            tool = registry.get(tool_name)
            assert tool is not None, f"Tool {tool_name} should be registered"

    def test_tools_have_handlers(self):
        """Test that all tools have handlers."""
        from tools.registry import registry
        
        tools = registry.get_by_toolset("browser")
        assert len(tools) == 10
        
        for tool in tools:
            assert tool.handler is not None


class TestCheckBrowserRequirements:
    """Test requirement checking functions."""

    def test_check_browser_requirements(self):
        """Test browser requirements check."""
        from tools.browser_tool import check_browser_requirements
        
        # Without agent-browser CLI, should return False
        result = check_browser_requirements()
        assert isinstance(result, bool)

    def test_check_browser_vision_requirements(self):
        """Test browser vision requirements check."""
        from tools.browser_tool import check_browser_vision_requirements
        
        result = check_browser_vision_requirements()
        assert isinstance(result, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
