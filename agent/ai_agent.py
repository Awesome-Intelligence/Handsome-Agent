#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AIAgent Module - Legacy wrapper for backwards compatibility.

This module provides backwards compatibility with code that imports AIAgent.
The core implementation is now in core/agent.py (CustomAgent).
"""

from core.agent import (
    CustomAgent,
    AgentConfig,
    AgentResponse,
)

AIAgent = CustomAgent
ToolResult = None

__all__ = [
    'AIAgent',
    'CustomAgent',
    'AgentConfig', 
    'AgentResponse',
]
