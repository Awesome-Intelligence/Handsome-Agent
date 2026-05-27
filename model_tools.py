#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Model Tools Module - Inspired by Hermes Agent

This module handles tool discovery, schema collection, and dispatch.
It provides utilities for working with tools in the agent system.
"""

import inspect
from typing import Dict, List, Optional, Any, Callable, Type
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import json


@dataclass
class ToolSchema:
    """JSON Schema definition for a tool."""
    name: str
    description: str
    parameters: Dict[str, Any]
    returns: Optional[Dict[str, Any]] = None
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        result = {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }
        if self.returns:
            result["returns"] = self.returns
        return result


@dataclass
class ToolInfo:
    """Information about a registered tool."""
    name: str
    func: Callable
    description: str
    parameters: List[Dict[str, Any]]
    schema: ToolSchema
    requires_permission: bool = False
    category: str = "general"


class ToolRegistry:
    """
    Registry for managing tools.
    
    Inspired by Hermes Agent's model_tools.py and registry.py
    """
    
    def __init__(self):
        self.tools: Dict[str, ToolInfo] = {}
        self.categories: Dict[str, List[str]] = {}
    
    def register_tool(self, name: str, func: Callable, description: str, 
                      parameters: List[Dict[str, Any]], requires_permission: bool = False,
                      category: str = "general"):
        """
        Register a tool.
        
        Args:
            name: Tool name
            func: Tool function
            description: Tool description
            parameters: List of parameter dictionaries
            requires_permission: Whether permission is required
            category: Tool category
        """
        # Build schema
        params_schema = {}
        for param in parameters:
            param_name = param.get("name")
            if param_name:
                params_schema[param_name] = {
                    "type": param.get("type", "string"),
                    "description": param.get("description", ""),
                    "required": param.get("required", False)
                }
        
        schema = ToolSchema(
            name=name,
            description=description,
            parameters=params_schema
        )
        
        tool_info = ToolInfo(
            name=name,
            func=func,
            description=description,
            parameters=parameters,
            schema=schema,
            requires_permission=requires_permission,
            category=category
        )
        
        self.tools[name] = tool_info
        
        # Add to category
        if category not in self.categories:
            self.categories[category] = []
        if name not in self.categories[category]:
            self.categories[category].append(name)
    
    def get_tool(self, name: str) -> Optional[ToolInfo]:
        """Get tool information by name."""
        return self.tools.get(name)
    
    def get_tools_by_category(self, category: str) -> List[ToolInfo]:
        """Get all tools in a category."""
        tool_names = self.categories.get(category, [])
        return [self.tools[name] for name in tool_names if name in self.tools]
    
    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self.tools.keys())
    
    def get_all_schemas(self) -> List[ToolSchema]:
        """Get schemas for all tools."""
        return [tool.schema for tool in self.tools.values()]
    
    def get_tool_descriptions(self) -> List[Dict[str, str]]:
        """Get descriptions for all tools in simple format."""
        return [
            {"name": name, "description": tool.description}
            for name, tool in self.tools.items()
        ]


class ToolDispatcher:
    """
    Dispatches tool execution requests.
    
    Handles:
    - Parameter validation
    - Permission checks
    - Error handling
    - Result formatting
    """
    
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
    
    async def dispatch(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        Dispatch a tool call.
        
        Args:
            tool_name: Name of the tool to execute
            **kwargs: Tool parameters
        
        Returns:
            Dictionary with 'success', 'output', and optionally 'error'
        """
        tool_info = self.registry.get_tool(tool_name)
        
        if not tool_info:
            return {
                "success": False,
                "error": f"Tool not found: {tool_name}"
            }
        
        # Check permission (stub implementation)
        if tool_info.requires_permission:
            # In production, this would check user permissions
            pass
        
        # Validate parameters
        validation = self._validate_parameters(tool_info, kwargs)
        if not validation["valid"]:
            return {
                "success": False,
                "error": validation["error"]
            }
        
        # Execute tool
        try:
            # Support both sync and async functions
            if inspect.iscoroutinefunction(tool_info.func):
                result = await tool_info.func(**kwargs)
            else:
                result = tool_info.func(**kwargs)
            
            return {
                "success": True,
                "output": result
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _validate_parameters(self, tool_info: ToolInfo, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate tool parameters.
        
        Returns:
            Dict with 'valid' (bool) and 'error' (str if invalid)
        """
        for param in tool_info.parameters:
            param_name = param.get("name")
            required = param.get("required", False)
            
            if required and param_name not in kwargs:
                return {
                    "valid": False,
                    "error": f"Missing required parameter: {param_name}"
                }
            
            if param_name in kwargs:
                # Type validation (simplified)
                expected_type = param.get("type", "string")
                value = kwargs[param_name]
                
                if expected_type == "integer" and not isinstance(value, int):
                    return {
                        "valid": False,
                        "error": f"Parameter {param_name} must be an integer"
                    }
                elif expected_type == "boolean" and not isinstance(value, bool):
                    return {
                        "valid": False,
                        "error": f"Parameter {param_name} must be a boolean"
                    }
        
        return {"valid": True, "error": None}


# Global registry instance
tool_registry = ToolRegistry()


def register_tool(name: str, description: str, parameters: List[Dict[str, Any]],
                  requires_permission: bool = False, category: str = "general"):
    """
    Decorator to register a tool.
    
    Example:
        @register_tool(
            name="file_write",
            description="Write content to a file",
            parameters=[
                {"name": "path", "type": "string", "description": "File path", "required": True},
                {"name": "content", "type": "string", "description": "Content to write", "required": True}
            ],
            category="files"
        )
        def file_write(path: str, content: str) -> str:
            # implementation
    """
    def decorator(func):
        tool_registry.register_tool(
            name=name,
            func=func,
            description=description,
            parameters=parameters,
            requires_permission=requires_permission,
            category=category
        )
        return func
    return decorator
