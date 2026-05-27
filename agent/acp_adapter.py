#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACP Adapter - Agent Communication Protocol

This module provides an adapter that allows external programs to
communicate with the AIAgent using the ACP (Agent Communication Protocol).

Inspired by Hermes Agent's ACP adapter design.
"""

import json
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from abc import ABC, abstractmethod

from .ai_agent import AIAgent, AgentResponse


@dataclass
class ACPMessage:
    """Message in ACP format."""
    version: str = "1.0"
    message_id: str = ""
    sender: str = ""
    recipient: str = ""
    action: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0


@dataclass
class ACPResponse:
    """Response in ACP format."""
    version: str = "1.0"
    message_id: str = ""
    status: str = "success"
    payload: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class ACPAdapter:
    """
    ACP (Agent Communication Protocol) Adapter
    
    Allows external programs to communicate with AIAgent using
    a standardized message format.
    
    ACP Message Format:
    {
        "version": "1.0",
        "message_id": "uuid",
        "sender": "external_program",
        "action": "respond|register_tool|get_stats",
        "payload": {...}
    }
    
    ACP Response Format:
    {
        "version": "1.0",
        "message_id": "uuid",
        "status": "success|error",
        "payload": {...},
        "error": null
    }
    """
    
    def __init__(self, agent: Optional[AIAgent] = None):
        self.agent = agent
        self.handlers: Dict[str, Callable] = {}
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default action handlers."""
        self.handlers["respond"] = self._handle_respond
        self.handlers["register_tool"] = self._handle_register_tool
        self.handlers["register_provider"] = self._handle_register_provider
        self.handlers["get_stats"] = self._handle_get_stats
        self.handlers["list_tools"] = self._handle_list_tools
        self.handlers["list_providers"] = self._handle_list_providers
        self.handlers["set_config"] = self._handle_set_config
        self.handlers["health_check"] = self._handle_health_check
    
    async def process_message(self, message: ACPMessage) -> ACPResponse:
        """Process an ACP message and return a response."""
        try:
            handler = self.handlers.get(message.action)
            if not handler:
                return ACPResponse(
                    message_id=message.message_id,
                    status="error",
                    error=f"Unknown action: {message.action}"
                )
            
            result = await handler(message.payload)
            
            return ACPResponse(
                message_id=message.message_id,
                status="success",
                payload=result
            )
        except Exception as e:
            return ACPResponse(
                message_id=message.message_id,
                status="error",
                error=str(e)
            )
    
    def process_message_sync(self, message: ACPMessage) -> ACPResponse:
        """Synchronous version of process_message."""
        return asyncio.run(self.process_message(message))
    
    async def _handle_respond(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle respond action."""
        query = payload.get("query", "")
        context = payload.get("context")
        
        if not self.agent:
            return {"error": "Agent not initialized"}
        
        response = await self.agent.respond(query, context)
        
        return {
            "content": response.content,
            "confidence": response.confidence,
            "execution_time": response.execution_time,
            "reasoning_steps": response.reasoning_steps,
            "tool_calls": response.tool_calls
        }
    
    async def _handle_register_tool(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle register_tool action."""
        tool_name = payload.get("name")
        tool_func = payload.get("func")
        tool_description = payload.get("description", "")
        
        if not self.agent or not tool_name:
            return {"error": "Invalid parameters"}
        
        # Register the tool with the dispatcher
        from .ai_agent import ToolBackend, ToolResult
        
        class UserDefinedBackend(ToolBackend):
            def get_name(self) -> str:
                return f"user_{tool_name}"
            
            async def execute(self, tool_name: str, params: Dict[str, Any]) -> ToolResult:
                if tool_func:
                    result = tool_func(params)
                    return ToolResult(success=True, output=str(result))
                return ToolResult(success=False, error="No function provided")
            
            def list_tools(self) -> List[str]:
                return [tool_name]
        
        self.agent.register_tool_backend(UserDefinedBackend())
        
        return {"message": f"Tool {tool_name} registered successfully"}
    
    async def _handle_register_provider(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle register_provider action."""
        provider_name = payload.get("name")
        provider = payload.get("provider")
        
        if not self.agent or not provider_name or not provider:
            return {"error": "Invalid parameters"}
        
        self.agent.register_provider(provider_name, provider)
        
        return {"message": f"Provider {provider_name} registered successfully"}
    
    async def _handle_get_stats(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_stats action."""
        if not self.agent:
            return {"error": "Agent not initialized"}
        
        return self.agent.get_stats()
    
    async def _handle_list_tools(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle list_tools action."""
        if not self.agent:
            return {"error": "Agent not initialized"}
        
        return {
            "tools": list(self.agent.tool_dispatcher.tools.keys()),
            "backends": list(self.agent.tool_dispatcher.backends.keys())
        }
    
    async def _handle_list_providers(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle list_providers action."""
        if not self.agent:
            return {"error": "Agent not initialized"}
        
        return {
            "providers": list(self.agent.provider_resolver.providers.keys()),
            "primary": self.agent.provider_resolver.primary_provider
        }
    
    async def _handle_set_config(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle set_config action."""
        if not self.agent:
            return {"error": "Agent not initialized"}
        
        for key, value in payload.items():
            self.agent.config[key] = value
        
        return {"message": "Configuration updated"}
    
    async def _handle_health_check(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle health_check action."""
        return {
            "status": "healthy" if self.agent else "unhealthy",
            "agent_initialized": self.agent is not None,
            "providers": len(self.agent.provider_resolver.providers) if self.agent else 0,
            "tools": len(self.agent.tool_dispatcher.tools) if self.agent else 0
        }
    
    def create_message(self, action: str, payload: Dict[str, Any], 
                      sender: str = "external", message_id: str = "") -> ACPMessage:
        """Create a new ACP message."""
        import uuid
        import time
        
        return ACPMessage(
            version="1.0",
            message_id=message_id or str(uuid.uuid4()),
            sender=sender,
            action=action,
            payload=payload,
            timestamp=time.time()
        )
    
    def create_response(self, message_id: str, payload: Dict[str, Any],
                        status: str = "success", error: Optional[str] = None) -> ACPResponse:
        """Create a new ACP response."""
        return ACPResponse(
            version="1.0",
            message_id=message_id,
            status=status,
            payload=payload,
            error=error
        )


class ACPClient:
    """
    ACP Client for making requests to ACP-enabled agents.
    
    Can be used by external programs to communicate with AIAgent.
    """
    
    def __init__(self, adapter: ACPAdapter):
        self.adapter = adapter
    
    async def send(self, action: str, payload: Dict[str, Any], 
                   sender: str = "client") -> ACPResponse:
        """Send an ACP message and get response."""
        message = self.adapter.create_message(action, payload, sender)
        return await self.adapter.process_message(message)
    
    def send_sync(self, action: str, payload: Dict[str, Any],
                  sender: str = "client") -> ACPResponse:
        """Synchronous version of send."""
        message = self.adapter.create_message(action, payload, sender)
        return self.adapter.process_message_sync(message)
    
    async def respond(self, query: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Send a respond request."""
        response = await self.send("respond", {"query": query, "context": context})
        return AgentResponse(
            content=response.payload.get("content", ""),
            confidence=response.payload.get("confidence", 0.0),
            execution_time=response.payload.get("execution_time", 0.0),
            reasoning_steps=response.payload.get("reasoning_steps", [])
        )


__all__ = [
    "ACPAdapter",
    "ACPClient",
    "ACPMessage",
    "ACPResponse"
]