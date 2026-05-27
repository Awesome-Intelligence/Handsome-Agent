#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tool module for the Handsome Agent.
Provides unified tool system with backend abstraction.
Inspired by Hermes Agent's tool system and PI Agent's minimal tools philosophy.
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from abc import ABC, abstractmethod


logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Result of tool execution."""
    success: bool
    output: str = ""
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ToolBackend(ABC):
    """Abstract base class for tool backends - inspired by Hermes/PI tool system."""
    
    @abstractmethod
    def get_name(self) -> str:
        """Return backend name."""
        pass
    
    @abstractmethod
    async def execute(self, tool_name: str, params: Dict[str, Any]) -> ToolResult:
        """Execute a tool."""
        pass
    
    @abstractmethod
    def list_tools(self) -> List[str]:
        """List available tools in this backend."""
        pass


class ToolDispatcher:
    """Dispatches tool calls to appropriate backends - inspired by PI Agent."""
    
    def __init__(self):
        self.backends: Dict[str, ToolBackend] = {}
        self.tools: Dict[str, Dict[str, Any]] = {}
    
    def register_backend(self, backend: ToolBackend):
        """Register a tool backend."""
        self.backends[backend.get_name()] = backend
        for tool_name in backend.list_tools():
            self.tools[tool_name] = {
                "backend": backend.get_name(),
                "name": tool_name
            }
        logger.info(f"Registered backend: {backend.get_name()} with {len(backend.list_tools())} tools")
    
    async def dispatch(self, tool_name: str, params: Dict[str, Any]) -> ToolResult:
        """Dispatch a tool call to the appropriate backend."""
        if tool_name not in self.tools:
            return ToolResult(success=False, error=f"Unknown tool: {tool_name}")
        
        backend_name = self.tools[tool_name]["backend"]
        backend = self.backends.get(backend_name)
        
        if not backend:
            return ToolResult(success=False, error=f"Backend not found: {backend_name}")
        
        return await backend.execute(tool_name, params)
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get all tool definitions."""
        return [
            {
                "name": name,
                "backend": meta["backend"]
            }
            for name, meta in self.tools.items()
        ]


class ToolRegistry:
    """Registry for available tools."""
    
    def __init__(self):
        self.tools: Dict[str, dict] = {}
    
    def register(self, name: str, func, description: str, parameters: List[dict]):
        """Register a tool."""
        self.tools[name] = {
            'func': func,
            'description': description,
            'parameters': parameters
        }
    
    def get(self, name: str) -> Optional[dict]:
        """Get a registered tool."""
        return self.tools.get(name)
    
    def list_tools(self) -> List[dict]:
        """List all registered tools."""
        return [
            {
                'name': name,
                'description': tool['description'],
                'parameters': tool['parameters']
            }
            for name, tool in self.tools.items()
        ]


tool_registry = ToolRegistry()
tool_dispatcher = ToolDispatcher()


def register_tool(name: str, description: str, parameters: List[dict]):
    """Decorator to register a tool."""
    def decorator(func):
        tool_registry.register(name, func, description, parameters)
        return func
    return decorator


from .file_tools import (
    read_file, write_file, search_files, 
    list_directory, patch_file
)
from .terminal_tools import (
    execute_terminal, run_python, get_system_info,
    detect_browsers, open_browser, list_browsers
)
from .web_tools import (
    web_search, web_extract, fetch_url
)
from .code_tools import (
    execute_code, analyze_code, format_json, validate_syntax
)
from .tool_calling import ToolCallingAgent, create_tool_calling_agent


terminal = execute_terminal


__all__ = [
    'ToolResult',
    'ToolBackend',
    'ToolDispatcher',
    'tool_dispatcher',
    'ToolRegistry',
    'tool_registry',
    'register_tool',
    'ToolCallingAgent',
    'create_tool_calling_agent',
    'read_file',
    'write_file',
    'search_files',
    'list_directory',
    'patch_file',
    'execute_terminal',
    'terminal',
    'run_python',
    'get_system_info',
    'detect_browsers',
    'open_browser',
    'list_browsers',
    'web_search',
    'web_extract',
    'fetch_url',
    'execute_code',
    'analyze_code',
    'format_json',
    'validate_syntax',
]