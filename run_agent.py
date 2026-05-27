#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AIAgent Core Conversation Loop - Inspired by Hermes Agent

This is the main entry point for the agent's conversation logic,
handling prompt building, provider resolution, tool dispatch,
and response generation.
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field

# Import internal modules
from agent.prompt_builder import PromptBuilder, ToolDefinition
from agent.context_engine import ContextEngine, ContextMessage, TruncatingContextEngine
from agent.memory_manager import MemoryManager
from agent.memory_provider import FileMemoryProvider
from agent.trajectory import TrajectoryManager, Trajectory, TrajectoryStep

# Import core modules
from core.router import TaskRouter, RouteMatch
from core.skill_manager import SkillManager, SkillResult, SkillMetadata
from core.session import SessionManager, Session, Message
from llm_integration import ProviderRegistry, LLMConfig, ModelInfo
from tools import tool_registry


@dataclass
class AgentResponse:
    """Structured response from the agent."""
    content: str
    is_tool_call: bool = False
    tool_name: Optional[str] = None
    tool_params: Optional[Dict[str, Any]] = None
    reasoning: List[str] = field(default_factory=list)
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentConfig:
    """Configuration for the AIAgent."""
    name: str = "AwesomeAgent"
    version: str = "1.0.0"
    max_context_tokens: int = 8192
    enable_routing: bool = True
    enable_skills: bool = True
    enable_memory: bool = True
    enable_trajectory: bool = True
    default_provider: str = "openai"
    default_model: str = "gpt-4o"


class AIAgent:
    """
    Core AI Agent implementation inspired by Hermes Agent.
    
    This class orchestrates:
    1. Prompt building and context management
    2. Provider resolution and LLM communication
    3. Tool discovery and dispatch
    4. Memory management
    5. Session management
    6. Response generation
    """
    
    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize core components
        self._init_components()
    
    def _init_components(self):
        """Initialize all agent components."""
        self.logger.info("Initializing AIAgent components...")
        
        # Session management
        self.session_manager = SessionManager()
        
        # Task routing
        self.task_router = TaskRouter()
        
        # Skill management
        self.skill_manager = SkillManager()
        
        # Context engine
        self.context_engine: ContextEngine = TruncatingContextEngine(
            default_max_tokens=self.config.max_context_tokens
        )
        
        # Memory management
        if self.config.enable_memory:
            memory_provider = FileMemoryProvider()
            self.memory_manager = MemoryManager(memory_provider)
        
        # Trajectory management
        if self.config.enable_trajectory:
            self.trajectory_manager = TrajectoryManager()
        
        # LLM provider
        self.provider_registry = ProviderRegistry()
        self.current_provider = None
        
        # Prompt builder
        self.prompt_builder = PromptBuilder()
        
        # Initialize tools
        self._init_tools()
        
        self.logger.info("AIAgent initialized successfully")
    
    def _init_tools(self):
        """Initialize available tools."""
        # Register all tools from tool_registry
        for tool_name, tool_info in tool_registry.tools.items():
            tool_def = ToolDefinition(
                name=tool_name,
                description=tool_info['description'],
                parameters=tool_info['parameters']
            )
            self.prompt_builder.add_tool(tool_def)
        
        self.logger.debug(f"Registered {len(tool_registry.tools)} tools")
    
    async def set_provider(self, provider_id: str, api_key: str, model: str = None):
        """Set the active LLM provider."""
        config = LLMConfig(
            provider_id=provider_id,
            api_key=api_key,
            model=model or self.config.default_model
        )
        self.current_provider = self.provider_registry.get_provider(config)
        self.logger.info(f"Set LLM provider to: {provider_id}")
    
    async def _build_prompt(self, session: Session, user_input: str) -> str:
        """Build the complete prompt for the LLM."""
        # Set core instructions
        self.prompt_builder.set_instructions("""
You are a helpful AI assistant. Use the available tools to accomplish tasks.
When calling a tool, use the proper format. If you can answer directly without tools, do so.

## Rules:
1. Always check available tools before answering
2. Format tool calls correctly
3. Summarize tool results for the user
4. Be concise but helpful
        """)
        
        # Set personality
        self.prompt_builder.set_personality("""
You are AwesomeAgent, a helpful and capable AI assistant.
You have access to various tools to help users accomplish their goals.
        """)
        
        # Add context from conversation history
        context_messages = []
        for msg in session.messages:
            context_msg = ContextMessage(
                role=msg.role,
                content=msg.content,
                timestamp=msg.timestamp,
                metadata=msg.metadata
            )
            context_messages.append(context_msg)
        
        # Compress context if needed
        compressed_context = self.context_engine.compress(
            context_messages,
            self.config.max_context_tokens - 2048  # Reserve tokens for new input
        )
        
        # Add context summary
        context_summary = self.context_engine.summarize(compressed_context)
        if context_summary:
            self.prompt_builder.add_section("Conversation History", context_summary)
        
        # Add current user input
        self.prompt_builder.add_section("Current Request", user_input)
        
        return self.prompt_builder.build()
    
    async def _call_llm(self, prompt: str) -> str:
        """Call the LLM provider and get response."""
        if not self.current_provider:
            raise ValueError("No LLM provider configured")
        
        response = await self.current_provider.generate(prompt)
        return response.content
    
    async def _handle_tool_call(self, tool_call: Dict[str, Any]) -> SkillResult:
        """Execute a tool call."""
        tool_name = tool_call.get("name")
        params = tool_call.get("parameters", {})
        
        if not tool_name:
            return SkillResult(success=False, output="Invalid tool call format")
        
        # Execute via skill manager
        result = await self.skill_manager.execute_skill(tool_name, **params)
        return result
    
    async def _parse_tool_call(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse tool call from LLM response."""
        # Look for tool call format
        if "<function" in response and "</function>" in response:
            try:
                # Simple parsing - extract tool name and parameters
                import re
                match = re.search(r'<function name="([^"]+)">(.*?)</function>', response, re.DOTALL)
                if match:
                    tool_name = match.group(1)
                    params_content = match.group(2)
                    
                    # Parse parameters
                    params = {}
                    param_matches = re.findall(r'<parameter name="([^"]+)">(.*?)