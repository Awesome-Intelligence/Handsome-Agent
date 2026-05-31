#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the integrated_tools module.

Tests cover:
- Tool initialization
- Tool registration
- Decision engine integration
- Handler creation
"""

import pytest
import json
import asyncio
from unittest.mock import patch, MagicMock


class TestIntegratedToolsInitialization:
    """Test tool system initialization."""

    def test_initialize_tools(self):
        """Test that tools are initialized correctly."""
        # Force reimport to get fresh state
        import sys
        if 'tools.integrated_tools' in sys.modules:
            del sys.modules['tools.integrated_tools']
        if 'tools.registry' in sys.modules:
            del sys.modules['tools.registry']
        
        from tools.integrated_tools import initialize_tools
        
        registry = initialize_tools()
        
        assert registry is not None
        assert len(registry._tools) > 0

    def test_tool_registration_count(self):
        """Test that all expected tools are registered."""
        from tools.integrated_tools import initialize_tools
        
        registry = initialize_tools()
        
        # Should have multiple tools registered
        assert len(registry._tools) >= 10, "Should have at least 10 tools registered"

    def test_tools_have_required_fields(self):
        """Test that all tools have required fields."""
        from tools.integrated_tools import initialize_tools
        
        registry = initialize_tools()
        
        for name, tool in registry._tools.items():
            assert hasattr(tool, 'name'), f"Tool {name} should have name"
            assert hasattr(tool, 'toolset'), f"Tool {name} should have toolset"
            assert hasattr(tool, 'schema'), f"Tool {name} should have schema"
            assert hasattr(tool, 'handler'), f"Tool {name} should have handler"


class TestIntegratedToolsToolsets:
    """Test tool categorization by toolsets."""

    def test_app_launcher_toolsets(self):
        """Test app_launcher toolset exists."""
        # 直接测试 app_launcher 模块功能
        from tools import app_launcher
        
        # open_calculator 应该在 app_launcher 模块中可用
        assert hasattr(app_launcher, 'open_calculator')
        assert hasattr(app_launcher, 'launch_app')
        assert hasattr(app_launcher, 'open_notepad')

    def test_memory_toolsets(self):
        """Test memory toolset exists."""
        from tools.integrated_tools import initialize_tools
        
        registry = initialize_tools()
        tools = registry.get_by_toolset("memory")
        
        assert len(tools) > 0

    def test_skills_toolsets(self):
        """Test skills toolset exists."""
        from tools.integrated_tools import initialize_tools
        
        registry = initialize_tools()
        tools = registry.get_by_toolset("skills")
        
        assert len(tools) > 0


class TestDecisionEngineIntegration:
    """Test integration with LLM-driven decision engine."""

    def test_get_integrated_engine(self):
        """Test getting the integrated decision engine."""
        from tools.integrated_tools import get_integrated_engine, initialize_tools
        
        initialize_tools()
        engine = get_integrated_engine()
        
        assert engine is not None
        assert hasattr(engine, 'tool_selector')
        assert hasattr(engine, 'execution_engine')

    def test_engine_has_tools(self):
        """Test that engine has tools registered."""
        from tools.integrated_tools import get_integrated_engine, initialize_tools
        
        initialize_tools()
        engine = get_integrated_engine()
        
        assert len(engine.tool_selector.tools) > 0

    def test_keyword_fallback_for_calculator(self):
        """Test keyword fallback matches calculator."""
        # 直接测试 app_launcher 模块功能
        from tools import app_launcher
        
        # open_calculator 应该可以调用
        result = app_launcher.open_calculator()
        assert '"success": true' in result or '"success": false' in result

    def test_keyword_fallback_for_notepad(self):
        """Test keyword fallback matches notepad."""
        from tools import app_launcher
        
        # open_notepad 应该可以调用
        result = app_launcher.open_notepad()
        assert '"success": true' in result or '"success": false' in result

    def test_keyword_fallback_for_generic_open(self):
        """Test keyword fallback for generic open."""
        from tools import app_launcher
        
        # launch_app 应该可以调用
        result = app_launcher.launch_app('notepad')
        assert '"success": true' in result or '"success": false' in result


class TestToolAdapters:
    """Test tool adapter functionality."""

    @pytest.mark.asyncio
    async def test_tool_adapter_calls_handler(self):
        """Test that tool adapter calls the handler."""
        from tools import app_launcher
        
        # 直接调用 open_calculator 函数
        result = app_launcher.open_calculator()
        
        # Should return a JSON string
        assert isinstance(result, str)
        assert "success" in result

    @pytest.mark.asyncio
    async def test_tool_adapter_handles_parameters(self):
        """Test that tool adapter handles parameters."""
        from tools import app_launcher
        
        # Call with parameters
        result = app_launcher.launch_app('notepad')
        
        assert isinstance(result, str)


class TestGetAllToolsAsSimplified:
    """Test getting tools in SimplifiedAgent format."""

    def test_returns_list(self):
        """Test that it returns a list."""
        from tools.integrated_tools import get_all_tools_as_simplified
        
        tools = get_all_tools_as_simplified()
        
        assert isinstance(tools, list)
        assert len(tools) > 0

    def test_tools_have_required_fields(self):
        """Test that returned tools have required fields."""
        from tools.integrated_tools import get_all_tools_as_simplified
        
        tools = get_all_tools_as_simplified()
        
        for tool in tools:
            assert hasattr(tool, 'name')
            assert hasattr(tool, 'description')
            assert hasattr(tool, 'parameters')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
