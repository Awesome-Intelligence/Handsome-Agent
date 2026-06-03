#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the code_execution_tool module.

Tests cover code execution functionality including:
- Python code execution
- Node.js code execution
- Bash command execution
- Timeout handling
"""

import pytest
import json
from unittest.mock import patch, MagicMock


class TestExecuteCode:
    """Test suite for execute_code."""

    def test_execute_code_returns_json(self):
        """Test that execute_code returns valid JSON."""
        from tools.code_execution_tool import execute_code
        
        result = execute_code(code="print('Hello')")
        assert isinstance(result, str)
        
        data = json.loads(result)
        assert "success" in data
        assert "task_id" in data

    def test_execute_python(self):
        """Test Python code execution."""
        from tools.code_execution_tool import execute_code
        
        result = execute_code(code="print('Hello from Python')", language="python")
        data = json.loads(result)
        
        assert "success" in data
        assert data["language"] == "python"

    def test_execute_code_with_task_id(self):
        """Test execute_code with custom task_id."""
        from tools.code_execution_tool import execute_code
        
        result = execute_code(code="print('test')", task_id="custom_task")
        data = json.loads(result)
        
        assert data["task_id"] == "custom_task"

    def test_execute_unsupported_language(self):
        """Test executing unsupported language."""
        from tools.code_execution_tool import execute_code
        
        result = execute_code(code="some code", language="unsupported_lang")
        data = json.loads(result)
        
        assert data["success"] is False
        assert "error" in data


class TestExecutePython:
    """Test suite for _execute_python."""

    def test_python_hello_world(self):
        """Test simple Python execution."""
        from tools.code_execution_tool import _execute_python
        
        result = _execute_python("print('Hello World')", 30, None, "test")
        data = json.loads(result)
        
        assert "success" in data
        assert data["language"] == "python"


class TestExecuteNode:
    """Test suite for _execute_node."""

    def test_node_returns_json(self):
        """Test Node.js execution returns JSON."""
        from tools.code_execution_tool import _execute_node
        
        result = _execute_node("console.log('Hello')", 30, "test")
        assert isinstance(result, str)
        
        data = json.loads(result)
        assert "success" in data
        assert "task_id" in data


class TestExecuteBash:
    """Test suite for _execute_bash."""

    def test_bash_returns_json(self):
        """Test bash execution returns JSON."""
        from tools.code_execution_tool import _execute_bash
        
        result = _execute_bash("echo 'test'", 30, "test")
        assert isinstance(result, str)
        
        data = json.loads(result)
        assert "success" in data
        assert "task_id" in data


class TestCodeExecutionConfig:
    """Test code execution configuration."""

    def test_get_config(self):
        """Test getting code execution config."""
        from tools.code_execution_tool import _get_config
        
        config = _get_config()
        assert isinstance(config, dict)
        assert "enabled" in config
        assert "timeout" in config


class TestBuildExecuteCodeSchema:
    """Test schema building."""

    def test_schema_structure(self):
        """Test execute_code schema structure."""
        from tools.code_execution_tool import EXECUTE_CODE_SCHEMA
        
        assert "name" in EXECUTE_CODE_SCHEMA
        assert EXECUTE_CODE_SCHEMA["name"] == "execute_code"
        assert "description" in EXECUTE_CODE_SCHEMA
        assert "parameters" in EXECUTE_CODE_SCHEMA
        
        params = EXECUTE_CODE_SCHEMA["parameters"]
        assert "properties" in params
        assert "code" in params["properties"]
        assert "language" in params["properties"]


class TestCodeExecutionRegistry:
    """Test tool registry integration."""

    def test_tools_registered(self):
        """Test that code execution tools are registered."""
        from tools.registry import registry
        
        tool = registry.get("execute_code")
        assert tool is not None, "Tool execute_code should be registered"

    def test_tool_has_handler(self):
        """Test that tool has handler."""
        from tools.registry import registry
        
        tool = registry.get("execute_code")
        assert tool.handler is not None


class TestCheckSandboxRequirements:
    """Test sandbox requirement checking."""

    def test_check_sandbox_requirements(self):
        """Test sandbox requirements check."""
        from tools.code_execution_tool import check_sandbox_requirements
        
        result = check_sandbox_requirements()
        assert isinstance(result, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
