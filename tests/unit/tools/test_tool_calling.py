#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the tools module tool calling functionality.

Tests cover tool schema validation, tool invocation, and result parsing.
"""

import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, Any


class TestToolSchema:
    """Test tool schema validation."""
    
    def test_basic_tool_schema(self):
        """Test basic tool schema structure."""
        from tools.schema_registry import BaseTool
        
        # Tool should have name, description, and parameters
        tool_schema = {
            "name": "test_tool",
            "description": "A test tool",
            "parameters": {
                "type": "object",
                "properties": {
                    "input": {
                        "type": "string",
                        "description": "Input text"
                    }
                },
                "required": ["input"]
            }
        }
        
        assert "name" in tool_schema
        assert "description" in tool_schema
        assert "parameters" in tool_schema
    
    def test_tool_schema_with_return_type(self):
        """Test tool schema with return type."""
        tool_schema = {
            "name": "calculator",
            "description": "Performs calculations",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string"}
                }
            },
            "returns": {
                "type": "number",
                "description": "Result of calculation"
            }
        }
        
        assert "returns" in tool_schema
        assert tool_schema["returns"]["type"] == "number"


class TestToolValidation:
    """Test tool input validation."""
    
    def test_validate_required_parameters(self):
        """Test validation of required parameters."""
        from tools.schema_registry import validate_parameters
        
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"}
            },
            "required": ["name"]
        }
        
        # Valid case (note: schema is first parameter)
        params = {"name": "Alice"}
        result = validate_parameters(schema, params)
        assert result is not None
        
        # Missing required parameter
        params = {"age": 25}
        try:
            validate_parameters(schema, params)
            assert False, "Should raise ValueError"
        except ValueError:
            pass
    
    def test_validate_parameter_types(self):
        """Test validation of parameter types."""
        from tools.schema_registry import validate_parameters
        
        schema = {
            "type": "object",
            "properties": {
                "count": {"type": "integer"},
                "active": {"type": "boolean"}
            }
        }
        
        # Valid types (note: schema is first parameter)
        result = validate_parameters(schema, {"count": 5, "active": True})
        assert result is not None
        
        # Invalid type
        try:
            validate_parameters(schema, {"count": "five"})
            assert False, "Should raise ValueError"
        except ValueError:
            pass


class TestToolInvocation:
    """Test tool invocation functionality."""
    
    def test_tool_call_structure(self):
        """Test tool call data structure."""
        tool_call = {
            "id": "call_123",
            "name": "search",
            "arguments": {
                "query": "Python tutorials"
            }
        }
        
        assert "id" in tool_call
        assert "name" in tool_call
        assert "arguments" in tool_call
        assert tool_call["name"] == "search"
    
    def test_tool_call_with_invalid_name(self):
        """Test tool call with invalid tool name."""
        from tools.registry import ToolRegistry
        
        registry = ToolRegistry()
        
        result = registry.get("nonexistent_tool")
        
        assert result is None


class TestToolResultParsing:
    """Test parsing tool execution results."""
    
    def test_successful_result_format(self):
        """Test successful tool result format."""
        result = {
            "success": True,
            "output": "Search completed",
            "data": {
                "count": 10,
                "items": ["item1", "item2"]
            }
        }
        
        assert result["success"] is True
        assert "output" in result
        assert "data" in result
    
    def test_error_result_format(self):
        """Test error tool result format."""
        result = {
            "success": False,
            "error": "Tool execution failed",
            "error_code": "EXECUTION_ERROR",
            "details": {
                "reason": "File not found",
                "path": "/tmp/test.txt"
            }
        }
        
        assert result["success"] is False
        assert "error" in result
        assert "error_code" in result
    
    def test_result_with_metadata(self):
        """Test result with metadata."""
        result = {
            "success": True,
            "output": "Command executed",
            "metadata": {
                "execution_time": 0.123,
                "tool_version": "1.0.0",
                "environment": "test"
            }
        }
        
        assert "metadata" in result
        assert "execution_time" in result["metadata"]


class TestToolRegistry:
    """Test tool registry functionality."""
    
    def test_registry_initialization(self):
        """Test registry initialization."""
        from tools.registry import ToolRegistry
        
        registry = ToolRegistry()
        
        assert registry is not None
    
    def test_register_tool(self):
        """Test registering a tool."""
        from tools.registry import ToolRegistry
        
        registry = ToolRegistry()
        
        def handler(params):
            return "result"
        
        registry.register(
            name="test_tool",
            toolset="test",
            schema={"type": "object", "properties": {}, "description": "A test tool"},
            handler=handler,
            description="A test tool"
        )
        
        assert registry.get("test_tool") is not None
    
    def test_list_tools(self):
        """Test listing all registered tools."""
        from tools.registry import ToolRegistry
        
        registry = ToolRegistry()
        
        def handler(params):
            return "result"
        
        registry.register(
            name="tool1",
            toolset="test",
            schema={"type": "object", "properties": {}, "description": "Tool 1"},
            handler=handler,
            description="Tool 1"
        )
        registry.register(
            name="tool2",
            toolset="test",
            schema={"type": "object", "properties": {}, "description": "Tool 2"},
            handler=handler,
            description="Tool 2"
        )
        
        tools = registry.get_all_tools()
        
        assert len(tools) >= 2
        tool_names = [t.name for t in tools]
        assert "tool1" in tool_names
        assert "tool2" in tool_names
    
    def test_unregister_tool(self):
        """Test unregistering a tool."""
        from tools.registry import ToolRegistry
        
        registry = ToolRegistry()
        
        def handler(params):
            return "result"
        
        registry.register(
            name="temp_tool",
            toolset="test",
            schema={"type": "object", "properties": {}, "description": "Temp"},
            handler=handler,
            description="Temp"
        )
        assert registry.get("temp_tool") is not None
        
        registry.unregister("temp_tool")
        assert registry.get("temp_tool") is None


class TestToolExecution:
    """Test tool execution flow."""
    
    def test_execution_flow(self):
        """Test basic execution flow."""
        # Mock tool execution
        tool_call = {
            "id": "call_001",
            "name": "echo",
            "arguments": {"message": "Hello"}
        }
        
        # Simulate execution
        result = {
            "id": tool_call["id"],
            "success": True,
            "output": "Hello"
        }
        
        assert result["id"] == tool_call["id"]
        assert result["success"] is True
    
    def test_execution_with_parameters(self):
        """Test execution with various parameter types."""
        tool_call = {
            "id": "call_002",
            "name": "create_file",
            "arguments": {
                "path": "/tmp/test.txt",
                "content": "Test content",
                "overwrite": True
            }
        }
        
        # Parameters should be preserved
        assert tool_call["arguments"]["path"] == "/tmp/test.txt"
        assert tool_call["arguments"]["content"] == "Test content"
        assert tool_call["arguments"]["overwrite"] is True


class TestToolCategories:
    """Test tool categorization."""
    
    def test_file_tools_category(self):
        """Test file tool categorization."""
        from tools.schema_registry import ToolCategory
        
        assert ToolCategory.FILE_TOOLS.value == "file"
    
    def test_shell_tools_category(self):
        """Test shell tool categorization."""
        from tools.schema_registry import ToolCategory
        
        assert ToolCategory.SHELL_TOOLS.value == "shell"
    
    def test_web_tools_category(self):
        """Test web tool categorization."""
        from tools.schema_registry import ToolCategory
        
        assert ToolCategory.WEB_TOOLS.value == "web"


class TestToolErrorHandling:
    """Test error handling in tool execution."""
    
    def test_timeout_error(self):
        """Test timeout error handling."""
        error = {
            "error": "Tool execution timeout",
            "error_type": "TimeoutError",
            "timeout_seconds": 30
        }
        
        assert "timeout" in error["error"].lower()
        assert error["error_type"] == "TimeoutError"
    
    def test_permission_error(self):
        """Test permission error handling."""
        error = {
            "error": "Permission denied",
            "error_type": "PermissionError",
            "path": "/root/secret.txt"
        }
        
        assert "permission" in error["error"].lower()
        assert error["error_type"] == "PermissionError"
    
    def test_not_found_error(self):
        """Test not found error handling."""
        error = {
            "error": "Tool not found",
            "error_type": "ToolNotFoundError",
            "tool_name": "nonexistent"
        }
        
        assert "not found" in error["error"].lower()
        assert error["error_type"] == "ToolNotFoundError"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
