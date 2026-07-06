"""
Docker 执行器
Docker 容器隔离执行
"""

import asyncio
from typing import Optional
from .base import BaseExecutor, ExecutorConfig, ExecutionResult
from executor.base import ToolCall, SafetyLevel


class DockerExecutor(BaseExecutor):
    """Docker 容器执行器"""
    
    def __init__(self, config: ExecutorConfig, image: str = "python:3.11-slim"):
        super().__init__(config)
        self.image = image
        self._container_id: Optional[str] = None
    
    async def execute(self, tool_call: ToolCall) -> ExecutionResult:
        """在 Docker 容器中执行"""
        import time
        start_time = time.time()
        
        await self._log_execution(f"Executing in Docker container: {tool_call.tool_name}")
        
        try:
            # 验证
            is_valid, error_msg = await self.validate(tool_call)
            if not is_valid:
                return ExecutionResult(
                    status="error",
                    tool_call=tool_call,
                    error_message=error_msg,
                    safety_level=SafetyLevel.CRITICAL,
                )
            
            # 执行命令
            command = tool_call.parameters.get("command", "")
            result = await self._run_in_container(command)
            
            execution_time = time.time() - start_time
            
            return ExecutionResult(
                status="success",
                tool_call=tool_call,
                output=result,
                logs=[f"Docker execution completed in {execution_time:.2f}s"],
                metrics={
                    "execution_time_ms": int(execution_time * 1000),
                    "container_image": self.image,
                },
                safety_level=SafetyLevel.MEDIUM,
            )
            
        except asyncio.TimeoutError:
            return ExecutionResult(
                status="timeout",
                tool_call=tool_call,
                error_message="Docker execution timed out",
            )
        except Exception as e:
            return ExecutionResult(
                status="error",
                tool_call=tool_call,
                error_message=str(e),
            )
    
    async def validate(self, tool_call: ToolCall) -> tuple[bool, Optional[str]]:
        """验证命令安全性"""
        command = tool_call.parameters.get("command", "")
        
        if not command:
            return False, "Empty command"
        
        # Docker 中不允许的操作
        docker_blocked = [
            "--privileged",
            "--cap-add",
            "--network",
            "docker in docker",
        ]
        
        for pattern in docker_blocked:
            if pattern in command:
                return False, f"Docker: blocked pattern {pattern}"
        
        return True, None
    
    async def _run_in_container(self, command: str) -> str:
        """在容器中运行命令"""
        docker_cmd = [
            "docker", "run", "--rm",
            "--network=none",
            "--pids-limit", "100",
            "--memory", "512m",
            "-i", self.image,
            "sh", "-c", command
        ]
        
        process = await asyncio.create_subprocess_exec(
            *docker_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.config.timeout_seconds
            )
            
            output = stdout.decode() if stdout else ""
            error = stderr.decode() if stderr else ""
            
            if process.returncode != 0:
                return f"Error: {error}"
            
            return output or "Command executed successfully"
            
        except asyncio.TimeoutError:
            process.kill()
            raise
    
    async def _cleanup(self) -> None:
        """清理容器"""
        if self._container_id:
            process = await asyncio.create_subprocess_exec(
                "docker", "rm", "-f", self._container_id
            )
            await process.communicate()
            self._container_id = None