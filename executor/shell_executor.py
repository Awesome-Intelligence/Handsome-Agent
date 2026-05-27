"""
Shell 执行器
本地命令执行
"""

import subprocess
import asyncio
from typing import Optional
from .base import BaseExecutor, ExecutorConfig, ExecutionResult
from brain.agent.schemas import ToolCall, SafetyLevel


class ShellExecutor(BaseExecutor):
    """本地 Shell 执行器"""
    
    def __init__(self, config: ExecutorConfig):
        super().__init__(config)
        self._shell_process: Optional[subprocess.Popen] = None
    
    async def execute(self, tool_call: ToolCall) -> ExecutionResult:
        """执行 Shell 命令"""
        import time
        start_time = time.time()
        
        # 验证安全性
        is_valid, error_msg = await self.validate(tool_call)
        if not is_valid:
            return ExecutionResult(
                status="error",
                tool_call=tool_call,
                error_message=error_msg,
                safety_level=SafetyLevel.CRITICAL,
            )
        
        await self._log_execution(f"Executing: {tool_call.tool_name}")
        
        try:
            # 根据工具类型执行
            if tool_call.tool_name == "shell_execute":
                result = await self._execute_shell(tool_call.parameters.get("command", ""))
            elif tool_call.tool_name == "file_read":
                result = await self._execute_file_read(tool_call.parameters.get("path", ""))
            elif tool_call.tool_name == "file_write":
                result = await self._execute_file_write(
                    tool_call.parameters.get("path", ""),
                    tool_call.parameters.get("content", "")
                )
            else:
                result = await self._execute_generic(tool_call)
            
            execution_time = time.time() - start_time
            
            return ExecutionResult(
                status="success",
                tool_call=tool_call,
                output=result,
                logs=[f"Command executed in {execution_time:.2f}s"],
                metrics={"execution_time_ms": int(execution_time * 1000)},
            )
            
        except asyncio.TimeoutError:
            return ExecutionResult(
                status="timeout",
                tool_call=tool_call,
                error_message=f"Execution timed out after {self.config.timeout_seconds}s",
            )
        except Exception as e:
            return ExecutionResult(
                status="error",
                tool_call=tool_call,
                error_message=str(e),
                logs=[f"Error: {str(e)}"],
            )
    
    async def validate(self, tool_call: ToolCall) -> tuple[bool, Optional[str]]:
        """验证命令安全性"""
        command = tool_call.parameters.get("command", "")
        
        if not command:
            return False, "Empty command"
        
        # 基本安全检查
        dangerous_patterns = [
            "rm -rf /",
            "rm -rf /*",
            ":(){:|:&};:",
            "curl | sh",
            "wget | sh",
        ]
        
        for pattern in dangerous_patterns:
            if pattern in command:
                return False, f"Dangerous pattern detected: {pattern}"
        
        # 白名单检查
        is_safe, error = self._check_safety(command)
        if not is_safe:
            return False, error
        
        return True, None
    
    async def _execute_shell(self, command: str) -> str:
        """执行 Shell 命令"""
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.config.work_dir,
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.config.timeout_seconds
            )
            
            output = stdout.decode() if stdout else ""
            error = stderr.decode() if stderr else ""
            
            if process.returncode != 0:
                return f"Error: {error}\nOutput: {output}"
            
            return output or error or "Command executed successfully"
            
        except asyncio.TimeoutError:
            process.kill()
            raise
    
    async def _execute_file_read(self, path: str) -> str:
        """读取文件"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return f"File not found: {path}"
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    async def _execute_file_write(self, path: str, content: str) -> str:
        """写入文件"""
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"File written successfully: {path}"
        except Exception as e:
            return f"Error writing file: {str(e)}"
    
    async def _execute_generic(self, tool_call: ToolCall) -> str:
        """执行通用工具调用"""
        return f"Executed {tool_call.tool_name} with params: {tool_call.parameters}"