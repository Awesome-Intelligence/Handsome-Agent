#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plugins Module - Inspired by Hermes Agent's plugin system.

This module provides a framework for loading and managing plugins.
Plugins can register tools, hooks, and CLI commands.
"""

import importlib
import os
import sys
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging


@dataclass
class PluginInfo:
    """Information about a plugin."""
    id: str
    name: str
    description: str
    version: str
    author: str
    module_path: str
    enabled: bool = True


@dataclass
class HookRegistration:
    """Registration for a hook."""
    hook_name: str
    callback: Callable
    priority: int = 0


class BasePlugin(ABC):
    """
    Abstract base class for all plugins.
    
    Plugins should inherit from this class and implement the required methods.
    """
    
    @abstractmethod
    def get_info(self) -> PluginInfo:
        """Return plugin information."""
        pass
    
    @abstractmethod
    def initialize(self, context: Dict[str, Any]):
        """Initialize the plugin with the given context."""
        pass
    
    @abstractmethod
    def register_tools(self, tool_registry):
        """Register tools with the tool registry."""
        pass
    
    @abstractmethod
    def register_hooks(self, hook_manager):
        """Register hooks with the hook manager."""
        pass


class PluginManager:
    """
    Manages loading and lifecycle of plugins.
    
    Inspired by Hermes Agent's plugin system.
    """
    
    def __init__(self):
        self.plugins: Dict[str, BasePlugin] = {}
        self.hook_manager = HookManager()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def load_plugin(self, plugin_module: str) -> bool:
        """
        Load a plugin by module path.
        
        Args:
            plugin_module: Module path (e.g., 'plugins.memory.sqlite')
        
        Returns:
            True if successful
        """
        try:
            # Import the module
            module = importlib.import_module(plugin_module)
            
            # Find the plugin class
            plugin_class = None
            for name in dir(module):
                obj = getattr(module, name)
                if isinstance(obj, type) and issubclass(obj, BasePlugin) and obj != BasePlugin:
                    plugin_class = obj
                    break
            
            if not plugin_class:
                self.logger.error(f"No plugin class found in {plugin_module}")
                return False
            
            # Instantiate the plugin
            plugin = plugin_class()
            info = plugin.get_info()
            
            # Store the plugin
            self.plugins[info.id] = plugin
            self.logger.info(f"Loaded plugin: {info.name} ({info.version})")
            
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to load plugin {plugin_module}: {e}")
            return False
    
    def load_plugins_from_directory(self, directory: str):
        """
        Load all plugins from a directory.
        
        Args:
            directory: Path to plugins directory
        """
        if not os.path.exists(directory):
            self.logger.warning(f"Plugins directory not found: {directory}")
            return
        
        for entry in os.listdir(directory):
            entry_path = os.path.join(directory, entry)
            
            # Check for package (directory with __init__.py)
            if os.path.isdir(entry_path) and os.path.exists(os.path.join(entry_path, "__init__.py")):
                module_path = f"plugins.{entry}"
                self.load_plugin(module_path)
            
            # Check for single file module
            elif entry.endswith(".py") and entry != "__init__.py":
                module_name = entry[:-3]
                module_path = f"plugins.{module_name}"
                self.load_plugin(module_path)
    
    def initialize_plugins(self, context: Optional[Dict[str, Any]] = None):
        """
        Initialize all loaded plugins.
        
        Args:
            context: Context dictionary to pass to plugins
        """
        context = context or {}
        
        for plugin_id, plugin in self.plugins.items():
            try:
                plugin.initialize(context)
                self.logger.debug(f"Initialized plugin: {plugin_id}")
            except Exception as e:
                self.logger.error(f"Failed to initialize plugin {plugin_id}: {e}")
    
    def register_plugin_tools(self, tool_registry):
        """Register tools from all plugins."""
        for plugin in self.plugins.values():
            try:
                plugin.register_tools(tool_registry)
            except Exception as e:
                self.logger.error(f"Failed to register tools for plugin {plugin.get_info().id}: {e}")
    
    def register_plugin_hooks(self):
        """Register hooks from all plugins."""
        for plugin in self.plugins.values():
            try:
                plugin.register_hooks(self.hook_manager)
            except Exception as e:
                self.logger.error(f"Failed to register hooks for plugin {plugin.get_info().id}: {e}")
    
    def get_plugin(self, plugin_id: str) -> Optional[BasePlugin]:
        """Get a plugin by ID."""
        return self.plugins.get(plugin_id)
    
    def list_plugins(self) -> List[PluginInfo]:
        """List all loaded plugins."""
        return [plugin.get_info() for plugin in self.plugins.values()]
    
    def enable_plugin(self, plugin_id: str):
        """Enable a plugin."""
        plugin = self.plugins.get(plugin_id)
        if plugin:
            plugin.get_info().enabled = True
            self.logger.info(f"Enabled plugin: {plugin_id}")
    
    def disable_plugin(self, plugin_id: str):
        """Disable a plugin."""
        plugin = self.plugins.get(plugin_id)
        if plugin:
            plugin.get_info().enabled = False
            self.logger.info(f"Disabled plugin: {plugin_id}")


class HookManager:
    """
    Manages hooks and hook callbacks.
    
    Hooks allow plugins to intercept and modify agent behavior.
    """
    
    def __init__(self):
        self.hooks: Dict[str, List[HookRegistration]] = {}
    
    def register_hook(self, hook_name: str, callback: Callable, priority: int = 0):
        """
        Register a hook callback.
        
        Args:
            hook_name: Name of the hook
            callback: Callback function
            priority: Priority (higher = called first)
        """
        if hook_name not in self.hooks:
            self.hooks[hook_name] = []
        
        self.hooks[hook_name].append(HookRegistration(
            hook_name=hook_name,
            callback=callback,
            priority=priority
        ))
        
        # Sort by priority (descending)
        self.hooks[hook_name].sort(key=lambda x: -x.priority)
    
    def trigger_hook(self, hook_name: str, **kwargs) -> List[Any]:
        """
        Trigger a hook and call all registered callbacks.
        
        Args:
            hook_name: Name of the hook to trigger
            **kwargs: Arguments to pass to callbacks
        
        Returns:
            List of results from each callback
        """
        results = []
        
        if hook_name not in self.hooks:
            return results
        
        for registration in self.hooks[hook_name]:
            try:
                result = registration.callback(**kwargs)
                results.append(result)
            except Exception as e:
                logging.error(f"Hook callback failed for {hook_name}: {e}")
        
        return results
    
    def list_hooks(self) -> List[str]:
        """List all registered hook names."""
        return list(self.hooks.keys())


# Global plugin manager instance
plugin_manager = PluginManager()


# Common hook names
class HookNames:
    """Common hook names used throughout the agent."""
    AGENT_INITIALIZED = "agent_initialized"
    BEFORE_PROMPT_BUILD = "before_prompt_build"
    AFTER_PROMPT_BUILD = "after_prompt_build"
    BEFORE_LLM_CALL = "before_llm_call"
    AFTER_LLM_CALL = "after_llm_call"
    BEFORE_TOOL_CALL = "before_tool_call"
    AFTER_TOOL_CALL = "after_tool_call"
    MESSAGE_RECEIVED = "message_received"
    RESPONSE_GENERATED = "response_generated"
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"
