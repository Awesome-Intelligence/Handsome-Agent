"""Executor 基础测试"""
import pytest
from unittest.mock import MagicMock
from executor.base import BaseExecutor, ExecutorConfig, ExecutionResult, ToolCall


class TestExecutorConfig:
    """ExecutorConfig 测试"""
    
    def test_default_values(self):
        """测试默认值"""
        config = ExecutorConfig()
        
        assert config.name == "BaseExecutor"
        assert config.timeout_seconds == 30.0
        assert config.allowed_commands == []
        assert config.blocked_patterns == []
        assert config.enable_logging is True
    
    def test_custom_values(self):
        """测试自定义值"""
        config = ExecutorConfig(
            name="TestExecutor",
            timeout_seconds=60.0,
            allowed_commands=["git", "ls"],
            blocked_patterns=["rm -rf /"],
        )
        
        assert config.name == "TestExecutor"
        assert config.timeout_seconds == 60.0
        assert "git" in config.allowed_commands
        assert "rm -rf /" in config.blocked_patterns


class TestExecutionResult:
    """ExecutionResult 测试"""
    
    def test_result_creation(self):
        """测试结果创建"""
        tool_call = ToolCall(tool_name="test_tool", parameters={})
        result = ExecutionResult(
            status="success",
            tool_call=tool_call,
            output="test output",
        )
        
        assert result.status == "success"
        assert result.output == "test output"
        assert result.execution_id is not None
    
    def test_error_result(self):
        """测试错误结果"""
        tool_call = ToolCall(tool_name="test_tool", parameters={})
        result = ExecutionResult(
            status="error",
            tool_call=tool_call,
            error_message="Command failed",
        )
        
        assert result.status == "error"
        assert result.error_message == "Command failed"


class TestBaseExecutor:
    """BaseExecutor 测试"""
    
    def test_check_safety_allowed(self):
        """测试安全检查 - 允许的命令"""
        config = ExecutorConfig(
            allowed_commands=["git", "ls"]
        )
        executor = MagicMock(spec=BaseExecutor)
        executor.config = config
        
        is_safe, error = executor._check_safety("git status")
        assert is_safe is True
        assert error is None
    
    def test_check_safety_not_in_whitelist(self):
        """测试安全检查 - 不在白名单"""
        config = ExecutorConfig(
            allowed_commands=["git", "ls"]
        )
        executor = MagicMock(spec=BaseExecutor)
        executor.config = config
        
        is_safe, error = executor._check_safety("rm file.txt")
        assert is_safe is False
        assert "not in whitelist" in error
    
    def test_check_safety_blocked_pattern(self):
        """测试安全检查 - 阻止模式"""
        config = ExecutorConfig(blocked_patterns=["rm -rf"])
        executor = MagicMock(spec=BaseExecutor)
        executor.config = config
        
        is_safe, error = executor._check_safety("rm -rf /")
        assert is_safe is False
        assert "blocked pattern" in error