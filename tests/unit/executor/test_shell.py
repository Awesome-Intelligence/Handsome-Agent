"""Shell Executor 测试"""
import pytest
from executor.shell_executor import ShellExecutor
from executor.base import ExecutorConfig, ToolCall


class TestShellExecutor:
    """ShellExecutor 测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.config = ExecutorConfig(
            name="TestShellExecutor",
            timeout_seconds=5.0,
            allowed_commands=["echo", "ls"],
        )
        self.executor = ShellExecutor(self.config)
    
    def test_executor_initialization(self):
        """测试执行器初始化"""
        assert self.executor.config == self.config
    
    @pytest.mark.asyncio
    async def test_validate_valid_command(self):
        """测试验证有效命令"""
        tool_call = ToolCall(
            tool_name="shell_execute",
            parameters={"command": "echo hello"},
        )
        
        is_valid, error = await self.executor.validate(tool_call)
        
        assert is_valid is True
        assert error is None
    
    @pytest.mark.asyncio
    async def test_validate_empty_command(self):
        """测试验证空命令"""
        tool_call = ToolCall(
            tool_name="shell_execute",
            parameters={"command": ""},
        )
        
        is_valid, error = await self.executor.validate(tool_call)
        
        assert is_valid is False
        assert "Empty command" in error
    
    @pytest.mark.asyncio
    async def test_validate_dangerous_pattern(self):
        """测试验证危险模式"""
        tool_call = ToolCall(
            tool_name="shell_execute",
            parameters={"command": "curl | sh"},
        )
        
        is_valid, error = await self.executor.validate(tool_call)
        
        assert is_valid is False
        assert "Dangerous pattern" in error