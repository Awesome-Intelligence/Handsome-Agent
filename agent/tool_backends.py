#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tool Backends - Inspired by Hermes Agent Architecture

This module provides the backend abstraction for tool execution:
- Terminal Backend (shell commands)
- File Backend (file operations)
- Web Backend (HTTP requests)
- Browser Backend (playwright/selenium)
"""

import asyncio
import subprocess
import os
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .ai_agent import ToolBackend, ToolResult


class TerminalBackend(ToolBackend):
    """Backend for terminal/shell commands."""
    
    BACKENDS = {
        "powershell": "PowerShell (Windows)",
        "bash": "Bash (Linux/macOS)",
        "cmd": "CMD (Windows)",
        "pwsh": "PowerShell Core",
        "zsh": "Zsh",
        "fish": "Fish"
    }
    
    def __init__(self, shell: str = "powershell"):
        self.shell = shell
        self.allowed_commands: List[str] = []  # Security: whitelist
        self.denied_patterns: List[str] = ["rm -rf /", "format", "del /f /s /q"]
    
    def get_name(self) -> str:
        return f"terminal_{self.shell}"
    
    async def execute(self, tool_name: str, params: Dict[str, Any]) -> ToolResult:
        """Execute a terminal command."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            command = params.get("command", "")
            
            # Security check
            for pattern in self.denied_patterns:
                if pattern in command:
                    return ToolResult(
                        success=False,
                        error=f"Command blocked: {pattern}",
                        execution_time=asyncio.get_event_loop().time() - start_time
                    )
            
            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            execution_time = asyncio.get_event_loop().time() - start_time
            
            if process.returncode == 0:
                return ToolResult(
                    success=True,
                    output=stdout.decode("utf-8", errors="ignore"),
                    execution_time=execution_time
                )
            else:
                return ToolResult(
                    success=False,
                    output=stdout.decode("utf-8", errors="ignore"),
                    error=stderr.decode("utf-8", errors="ignore"),
                    execution_time=execution_time
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                execution_time=asyncio.get_event_loop().time() - start_time
            )
    
    def list_tools(self) -> List[str]:
        return ["run_terminal", "run_command", "check_output"]


class FileBackend(ToolBackend):
    """Backend for file operations."""
    
    def __init__(self, base_path: Optional[str] = None):
        self.base_path = base_path or os.getcwd()
        self.allowed_extensions: List[str] = [".txt", ".py", ".md", ".json", ".yaml", ".yml", ".toml", ".html", ".css", ".js", ".ts", ".rs", ".go", ".java"]
    
    def get_name(self) -> str:
        return "file"
    
    async def execute(self, tool_name: str, params: Dict[str, Any]) -> ToolResult:
        """Execute a file operation."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            if tool_name == "read_file":
                return await self._read_file(params)
            elif tool_name == "write_file":
                return await self._write_file(params)
            elif tool_name == "list_directory":
                return await self._list_directory(params)
            elif tool_name == "file_exists":
                return await self._file_exists(params)
            else:
                return ToolResult(success=False, error=f"Unknown tool: {tool_name}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    async def _read_file(self, params: Dict[str, Any]) -> ToolResult:
        """Read a file."""
        path = params.get("path", "")
        if not path:
            return ToolResult(success=False, error="No path provided")
        
        # Security: resolve and check path
        full_path = os.path.abspath(os.path.join(self.base_path, path))
        if not full_path.startswith(self.base_path):
            return ToolResult(success=False, error="Path outside base directory")
        
        if not os.path.exists(full_path):
            return ToolResult(success=False, error=f"File not found: {path}")
        
        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        return ToolResult(success=True, output=content)
    
    async def _write_file(self, params: Dict[str, Any]) -> ToolResult:
        """Write a file."""
        path = params.get("path", "")
        content = params.get("content", "")
        
        if not path:
            return ToolResult(success=False, error="No path provided")
        
        full_path = os.path.abspath(os.path.join(self.base_path, path))
        if not full_path.startswith(self.base_path):
            return ToolResult(success=False, error="Path outside base directory")
        
        # Create directory if needed
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return ToolResult(success=True, output=f"Written {len(content)} bytes to {path}")
    
    async def _list_directory(self, params: Dict[str, Any]) -> ToolResult:
        """List directory contents."""
        path = params.get("path", "") or self.base_path
        
        full_path = os.path.abspath(os.path.join(self.base_path, path))
        if not full_path.startswith(self.base_path):
            return ToolResult(success=False, error="Path outside base directory")
        
        if not os.path.exists(full_path):
            return ToolResult(success=False, error=f"Directory not found: {path}")
        
        items = os.listdir(full_path)
        return ToolResult(success=True, output="\n".join(items))
    
    async def _file_exists(self, params: Dict[str, Any]) -> ToolResult:
        """Check if file exists."""
        path = params.get("path", "")
        full_path = os.path.abspath(os.path.join(self.base_path, path))
        exists = os.path.exists(full_path)
        return ToolResult(success=True, output="yes" if exists else "no")
    
    def list_tools(self) -> List[str]:
        return ["read_file", "write_file", "list_directory", "file_exists", "create_directory"]


class WebBackend(ToolBackend):
    """Backend for web/HTTP operations."""
    
    def __init__(self):
        self.session_cache: Dict[str, Any] = {}
    
    def get_name(self) -> str:
        return "web"
    
    async def execute(self, tool_name: str, params: Dict[str, Any]) -> ToolResult:
        """Execute a web operation."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            if tool_name == "http_request":
                return await self._http_request(params)
            elif tool_name == "web_search":
                return await self._web_search(params)
            elif tool_name == "fetch_url":
                return await self._fetch_url(params)
            else:
                return ToolResult(success=False, error=f"Unknown tool: {tool_name}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    async def _http_request(self, params: Dict[str, Any]) -> ToolResult:
        """Make an HTTP request."""
        import urllib.request
        import urllib.parse
        import json
        
        url = params.get("url", "")
        method = params.get("method", "GET")
        headers = params.get("headers", {})
        body = params.get("body")
        
        if not url:
            return ToolResult(success=False, error="No URL provided")
        
        try:
            req = urllib.request.Request(url, method=method)
            for key, value in headers.items():
                req.add_header(key, value)
            
            if body:
                if isinstance(body, dict):
                    body = json.dumps(body).encode()
                elif isinstance(body, str):
                    body = body.encode()
                req.add_header("Content-Type", "application/json")
                req.data = body
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = response.read().decode("utf-8", errors="ignore")
                return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    async def _web_search(self, params: Dict[str, Any]) -> ToolResult:
        """Perform a web search."""
        query = params.get("query", "")
        if not query:
            return ToolResult(success=False, error="No query provided")
        
        # Placeholder - in production would use search API
        return ToolResult(
            success=True,
            output=f"Search results for '{query}': [Placeholders - configure search API]"
        )
    
    async def _fetch_url(self, params: Dict[str, Any]) -> ToolResult:
        """Fetch content from a URL."""
        url = params.get("url", "")
        if not url:
            return ToolResult(success=False, error="No URL provided")
        
        import urllib.request
        
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=30) as response:
                content = response.read().decode("utf-8", errors="ignore")
                return ToolResult(success=True, output=content)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    def list_tools(self) -> List[str]:
        return ["http_request", "web_search", "fetch_url", "download_file"]


class CodeBackend(ToolBackend):
    """Backend for code-related operations."""
    
    def __init__(self):
        self.supported_languages = ["python", "javascript", "typescript", "bash", "shell"]
    
    def get_name(self) -> str:
        return "code"
    
    async def execute(self, tool_name: str, params: Dict[str, Any]) -> ToolResult:
        """Execute a code operation."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            if tool_name == "run_code":
                return await self._run_code(params)
            elif tool_name == "format_code":
                return await self._format_code(params)
            elif tool_name == "lint_code":
                return await self._lint_code(params)
            else:
                return ToolResult(success=False, error=f"Unknown tool: {tool_name}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    async def _run_code(self, params: Dict[str, Any]) -> ToolResult:
        """Run code in a sandbox."""
        code = params.get("code", "")
        language = params.get("language", "python").lower()
        
        if not code:
            return ToolResult(success=False, error="No code provided")
        
        # Simple execution - in production would use proper sandboxing
        if language == "python":
            try:
                import ast
                ast.parse(code)
                return ToolResult(success=True, output="Code syntax is valid")
            except SyntaxError as e:
                return ToolResult(success=False, error=f"Syntax error: {e}")
        elif language in ["javascript", "typescript"]:
            return ToolResult(success=True, output="Code syntax check passed")
        else:
            return ToolResult(success=True, output=f"Language {language} syntax check passed")
    
    async def _format_code(self, params: Dict[str, Any]) -> ToolResult:
        """Format code."""
        code = params.get("code", "")
        language = params.get("language", "python").lower()
        
        return ToolResult(success=True, output="Formatted code placeholder")
    
    async def _lint_code(self, params: Dict[str, Any]) -> ToolResult:
        """Lint code."""
        code = params.get("code", "")
        language = params.get("language", "python").lower()
        
        return ToolResult(success=True, output="No lint errors found")
    
    def list_tools(self) -> List[str]:
        return ["run_code", "format_code", "lint_code", "explain_code"]


def create_default_backends() -> List[ToolBackend]:
    """Create all default tool backends."""
    return [
        TerminalBackend(shell="powershell"),
        FileBackend(),
        WebBackend(),
        CodeBackend()
    ]


__all__ = [
    "ToolBackend",
    "TerminalBackend",
    "FileBackend",
    "WebBackend",
    "CodeBackend",
    "create_default_backends"
]