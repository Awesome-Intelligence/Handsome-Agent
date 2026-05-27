#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Toolsets Module - Inspired by Hermes Agent

This module defines tool groupings and platform presets.
Toolsets are collections of tools that are commonly used together.
"""

from typing import List, Dict, Optional, Any, Set
from dataclasses import dataclass, field
from model_tools import ToolRegistry, ToolInfo


@dataclass
class Toolset:
    """A collection of related tools."""
    name: str
    description: str
    tools: List[str]  # List of tool names
    platforms: List[str] = field(default_factory=list)  # Supported platforms
    requires_permission: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "tools": self.tools,
            "platforms": self.platforms,
            "requires_permission": self.requires_permission
        }


class ToolsetManager:
    """
    Manages toolsets - collections of related tools.
    
    Inspired by Hermes Agent's toolsets.py
    """
    
    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
        self.toolsets: Dict[str, Toolset] = {}
        self._register_default_toolsets()
    
    def _register_default_toolsets(self):
        """Register default toolsets."""
        # File operations toolset
        self.register_toolset(Toolset(
            name="files",
            description="File system operations",
            tools=["file_write", "file_read", "file_delete", "file_list", "file_rename"],
            platforms=["linux", "windows", "macos"]
        ))
        
        # Terminal operations toolset
        self.register_toolset(Toolset(
            name="terminal",
            description="Terminal and shell commands",
            tools=["shell_exec", "shell_exec_interactive", "cd", "pwd"],
            platforms=["linux", "windows", "macos"],
            requires_permission=True
        ))
        
        # Web operations toolset
        self.register_toolset(Toolset(
            name="web",
            description="Web browsing and search",
            tools=["web_search", "web_extract", "url_open", "download_file"],
            platforms=["linux", "windows", "macos"]
        ))
        
        # Code operations toolset
        self.register_toolset(Toolset(
            name="code",
            description="Code execution and analysis",
            tools=["python_run", "code_analyze", "code_format", "git_clone", "git_status"],
            platforms=["linux", "windows", "macos"]
        ))
        
        # System operations toolset
        self.register_toolset(Toolset(
            name="system",
            description="System information and management",
            tools=["system_info", "process_list", "kill_process", "restart_service"],
            platforms=["linux", "windows", "macos"],
            requires_permission=True
        ))
        
        # AI operations toolset
        self.register_toolset(Toolset(
            name="ai",
            description="AI and machine learning tools",
            tools=["image_generate", "text_summarize", "sentiment_analysis", "translate"],
            platforms=["linux", "windows", "macos"]
        ))
    
    def register_toolset(self, toolset: Toolset):
        """Register a toolset."""
        self.toolsets[toolset.name] = toolset
    
    def get_toolset(self, name: str) -> Optional[Toolset]:
        """Get a toolset by name."""
        return self.toolsets.get(name)
    
    def list_toolsets(self) -> List[str]:
        """List all toolset names."""
        return list(self.toolsets.keys())
    
    def get_toolset_tools(self, toolset_name: str) -> List[ToolInfo]:
        """
        Get all tools in a toolset.
        
        Args:
            toolset_name: Name of the toolset
        
        Returns:
            List of ToolInfo objects
        """
        toolset = self.get_toolset(toolset_name)
        if not toolset:
            return []
        
        tools = []
        for tool_name in toolset.tools:
            tool_info = self.tool_registry.get_tool(tool_name)
            if tool_info:
                tools.append(tool_info)
        
        return tools
    
    def get_tools_for_platform(self, platform: str) -> List[str]:
        """
        Get all tools available for a specific platform.
        
        Args:
            platform: Platform name (linux, windows, macos)
        
        Returns:
            List of tool names
        """
        tools: Set[str] = set()
        
        for toolset in self.toolsets.values():
            if platform in toolset.platforms:
                tools.update(toolset.tools)
        
        return list(tools)
    
    def get_toolsets_for_platform(self, platform: str) -> List[Toolset]:
        """
        Get all toolsets available for a specific platform.
        
        Args:
            platform: Platform name
        
        Returns:
            List of toolsets
        """
        return [
            toolset for toolset in self.toolsets.values()
            if platform in toolset.platforms
        ]
    
    def get_permission_required_tools(self) -> List[str]:
        """
        Get all tools that require permission.
        
        Returns:
            List of tool names requiring permission
        """
        tools: Set[str] = set()
        
        for toolset in self.toolsets.values():
            if toolset.requires_permission:
                tools.update(toolset.tools)
        
        return list(tools)


# Platform detection utilities
def detect_platform() -> str:
    """
    Detect the current platform.
    
    Returns:
        Platform name: 'linux', 'windows', or 'macos'
    """
    import sys
    
    if sys.platform.startswith('linux'):
        return 'linux'
    elif sys.platform.startswith('win'):
        return 'windows'
    elif sys.platform.startswith('darwin'):
        return 'macos'
    else:
        return 'linux'  # Default to linux


def get_platform_toolsets(toolset_manager: ToolsetManager) -> List[Toolset]:
    """
    Get toolsets available for the current platform.
    
    Args:
        toolset_manager: The toolset manager instance
    
    Returns:
        List of toolsets available on current platform
    """
    platform = detect_platform()
    return toolset_manager.get_toolsets_for_platform(platform)


def get_platform_tools(toolset_manager: ToolsetManager) -> List[str]:
    """
    Get tools available for the current platform.
    
    Args:
        toolset_manager: The toolset manager instance
    
    Returns:
        List of tool names available on current platform
    """
    platform = detect_platform()
    return toolset_manager.get_tools_for_platform(platform)
