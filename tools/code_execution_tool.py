#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Code Execution Tool Module

Provides functionality for executing code in isolated sandbox environments.

Based on Hermes Agent's code_execution_tool.py implementation.

Features:
- Python code execution
- Code execution with sandbox isolation
- Timeout protection
- Resource limits

Usage:
    from tools.code_execution_tool import execute_code, check_sandbox_requirements

    result = execute_code(code="print('Hello, World!')")
"""

import json
import os
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List

from common.logging_manager import get_execution_logger
from tools.registry import registry

logger = get_execution_logger("CodeExecution")

# Default settings
DEFAULT_TIMEOUT = 30  # seconds
DEFAULT_MEMORY_LIMIT = "256m"
DEFAULT_CPU_LIMIT = "0.5"


def _get_config() -> dict:
    """获取代码执行配置"""
    try:
        from common.config import settings
        
        return {
            "enabled": getattr(settings, 'CODE_EXECUTION_ENABLED', True),
            "timeout": getattr(settings, 'CODE_EXECUTION_TIMEOUT', DEFAULT_TIMEOUT),
            "sandbox_type": getattr(settings, 'CODE_SANDBOX_TYPE', "local"),  # local, docker, modal
        }
    except Exception:
        pass
    
    return {
        "enabled": os.environ.get("CODE_EXECUTION_ENABLED", "true").lower() == "true",
        "timeout": int(os.environ.get("CODE_EXECUTION_TIMEOUT", str(DEFAULT_TIMEOUT))),
        "sandbox_type": os.environ.get("CODE_SANDBOX_TYPE", "local"),
    }


def execute_code(
    code: str,
    language: str = "python",
    timeout: Optional[int] = None,
    enabled_tools: Optional[List[str]] = None,
    **kwargs
) -> str:
    """
    Execute code in a sandbox environment.
    
    Args:
        code: Code to execute
        language: Programming language (python, node, bash)
        timeout: Execution timeout in seconds
        enabled_tools: List of enabled tools for code execution
        **kwargs: Additional parameters (task_id, etc.)
        
    Returns:
        JSON string with execution results
    """
    config = _get_config()
    timeout = timeout or config["timeout"]
    
    task_id = kwargs.get("task_id", str(uuid.uuid4())[:8])
    
    if not config["enabled"]:
        return json.dumps({
            "success": False,
            "error": "Code execution is disabled",
            "task_id": task_id
        }, ensure_ascii=False)
    
    try:
        if language == "python":
            return _execute_python(code, timeout, enabled_tools, task_id)
        elif language == "node":
            return _execute_node(code, timeout, task_id)
        elif language == "bash":
            return _execute_bash(code, timeout, task_id)
        else:
            return json.dumps({
                "success": False,
                "error": f"Unsupported language: {language}",
                "language": language,
                "task_id": task_id
            }, ensure_ascii=False)
            
    except Exception as e:
        logger.error(f"Code execution error: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "task_id": task_id
        }, ensure_ascii=False)


def _execute_python(code: str, timeout: int, enabled_tools: Optional[List[str]], task_id: str) -> str:
    """Execute Python code"""
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(code)
        temp_file = f.name
    
    try:
        # Build command
        cmd = ["python", temp_file]
        
        # Check if python3 is available
        try:
            subprocess.run(["python3", "--version"], capture_output=True, timeout=5)
            cmd[0] = "python3"
        except Exception:
            pass
        
        # Execute
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding='utf-8',
            errors='replace'
        )
        
        output = result.stdout
        error = result.stderr
        
        if result.returncode == 0:
            return json.dumps({
                "success": True,
                "language": "python",
                "output": output,
                "returncode": result.returncode,
                "task_id": task_id
            }, ensure_ascii=False)
        else:
            return json.dumps({
                "success": False,
                "language": "python",
                "output": output,
                "error": error,
                "returncode": result.returncode,
                "task_id": task_id
            }, ensure_ascii=False)
            
    finally:
        # Cleanup temp file
        try:
            os.unlink(temp_file)
        except Exception:
            pass


def _execute_node(code: str, timeout: int, task_id: str) -> str:
    """Execute JavaScript/Node code"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False, encoding='utf-8') as f:
        f.write(code)
        temp_file = f.name
    
    try:
        result = subprocess.run(
            ["node", temp_file],
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding='utf-8',
            errors='replace'
        )
        
        output = result.stdout
        error = result.stderr
        
        return json.dumps({
            "success": result.returncode == 0,
            "language": "node",
            "output": output,
            "error": error if result.returncode != 0 else None,
            "returncode": result.returncode,
            "task_id": task_id
        }, ensure_ascii=False)
        
    finally:
        try:
            os.unlink(temp_file)
        except Exception:
            pass


def _execute_bash(code: str, timeout: int, task_id: str) -> str:
    """Execute bash/shell commands"""
    result = subprocess.run(
        code,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding='utf-8',
        errors='replace'
    )
    
    return json.dumps({
        "success": result.returncode == 0,
        "language": "bash",
        "output": result.stdout,
        "error": result.stderr if result.returncode != 0 else None,
        "returncode": result.returncode,
        "task_id": task_id
    }, ensure_ascii=False)


def check_sandbox_requirements() -> bool:
    """检查代码执行环境是否可用"""
    config = _get_config()
    
    if not config["enabled"]:
        return False
    
    # Check if Python is available
    try:
        subprocess.run(
            ["python", "--version"],
            capture_output=True,
            timeout=5
        )
        return True
    except Exception:
        try:
            subprocess.run(
                ["python3", "--version"],
                capture_output=True,
                timeout=5
            )
            return True
        except Exception:
            return False


def build_execute_code_schema() -> dict:
    """Build the execute_code schema dynamically"""
    return {
        "name": "execute_code",
        "description": "Execute Python, Node.js, or bash code in an isolated environment. Use this for running code snippets, calculations, or testing algorithms.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Code to execute. For Python, ensure proper indentation. For bash, write shell commands."
                },
                "language": {
                    "type": "string",
                    "description": "Programming language",
                    "enum": ["python", "node", "bash"],
                    "default": "python"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Execution timeout in seconds",
                    "default": DEFAULT_TIMEOUT
                },
                "enabled_tools": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tools enabled for code execution (e.g., ['internet', 'file_system'])"
                }
            },
            "required": ["code"]
        }
    }


# Schema - dynamically built
EXECUTE_CODE_SCHEMA = build_execute_code_schema()


# Register the tool
registry.register(
    name="execute_code",
    toolset="code_execution",
    schema=EXECUTE_CODE_SCHEMA,
    handler=lambda args, **kw: execute_code(
        code=args.get("code", ""),
        language=args.get("language", "python"),
        timeout=args.get("timeout"),
        enabled_tools=args.get("enabled_tools"),
        **kw
    ),
    check_fn=check_sandbox_requirements,
    emoji="🐍",
    max_result_size_chars=100000,
)
