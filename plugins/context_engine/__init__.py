#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Context Engine Plugin - Inspired by Hermes Agent's context engine plugins.

This plugin provides context management capabilities.
"""

from plugins import BasePlugin, PluginInfo, HookNames
from agent.context_engine import TruncatingContextEngine


class ContextEnginePlugin(BasePlugin):
    """Context engine plugin."""
    
    def __init__(self):
        self.context_engine = None
    
    def get_info(self) -> PluginInfo:
        return PluginInfo(
            id="context_engine",
            name="Context Engine Plugin",
            description="Provides context management and compression capabilities",
            version="1.0.0",
            author="Handsome Agent Team",
            module_path="plugins.context_engine"
        )
    
    def initialize(self, context: dict):
        """Initialize the context engine plugin."""
        self.context_engine = TruncatingContextEngine()
        context["context_engine"] = self.context_engine
    
    def register_tools(self, tool_registry):
        """Register context-related tools."""
        pass
    
    def register_hooks(self, hook_manager):
        """Register context-related hooks."""
        # Hook into before prompt build to compress context
        hook_manager.register_hook(
            HookNames.BEFORE_PROMPT_BUILD,
            self._on_before_prompt_build,
            priority=20
        )
    
    def _on_before_prompt_build(self, **kwargs):
        """Handle before prompt build event."""
        messages = kwargs.get("messages", [])
        max_tokens = kwargs.get("max_tokens", 8192)
        
        if self.context_engine and messages:
            compressed = self.context_engine.compress(messages, max_tokens)
            return {"messages": compressed}
