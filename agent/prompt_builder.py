#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prompt Builder Module - Inspired by Hermes Agent

This module handles the assembly of system prompts for the AI agent,
including tool definitions, context, and personality settings.
"""

import json
import os
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from abc import ABC, abstractmethod


logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    """Definition of a tool for prompt inclusion."""
    name: str
    description: str
    parameters: List[Dict[str, Any]]
    returns: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for JSON serialization."""
        result = {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }
        if self.returns:
            result["returns"] = self.returns
        return result


@dataclass
class PromptSection:
    """A section of the system prompt."""
    name: str
    content: str
    priority: int = 0


class BasePromptBuilder(ABC):
    """Abstract base class for prompt builders."""
    
    @abstractmethod
    def build(self) -> str:
        """Build and return the complete system prompt."""
        pass
    
    @abstractmethod
    def add_tool(self, tool: ToolDefinition):
        """Add a tool definition to the prompt."""
        pass


class PromptBuilder(BasePromptBuilder):
    """
    System prompt assembler that constructs comprehensive prompts
    with tools, context, personality, and instructions.
    
    Inspired by Hermes Agent's prompt_builder.py
    
    **Harness Architecture Integration**:
    This PromptBuilder loads agent definitions from markdown files:
    - agent.md: Agent role and identity
    - memory.md: Memory system specification
    - tools.md: Tool usage specifications
    - capabilities.md: Complete capability list
    
    All definitions are loaded at initialization and included
    in the system prompt for LLM context.
    """
    
    def __init__(self):
        self.sections: List[PromptSection] = []
        self.tools: List[ToolDefinition] = []
        self.personality = ""
        self.instructions = ""
        self._load_agent_definitions()
    
    def _load_agent_definitions(self):
        """Load agent definition markdown files for context."""
        agent_dir = os.path.dirname(os.path.abspath(__file__))
        definition_files = {
            'Agent Identity': 'agent.md',
            'Memory System': 'memory.md',
            'Tool Specifications': 'tools.md',
            'Capabilities': 'capabilities.md'
        }
        
        for section_name, filename in definition_files.items():
            file_path = os.path.join(agent_dir, filename)
            try:
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        self.add_section(section_name, content, priority=100)
                        logger.info(f"Loaded agent definition: {filename}")
                else:
                    logger.warning(f"Agent definition file not found: {filename}")
            except Exception as e:
                logger.error(f"Failed to load {filename}: {e}")
    
    def set_personality(self, personality: str):
        """Set the agent's personality/profile."""
        self.personality = personality
    
    def set_instructions(self, instructions: str):
        """Set core instructions for the agent."""
        self.instructions = instructions
    
    def add_section(self, name: str, content: str, priority: int = 0):
        """Add a custom section to the prompt."""
        self.sections.append(PromptSection(name=name, content=content, priority=priority))
    
    def add_tool(self, tool: ToolDefinition):
        """Add a tool to the prompt's tool list."""
        self.tools.append(tool)
    
    def add_tools(self, tools: List[ToolDefinition]):
        """Add multiple tools at once."""
        self.tools.extend(tools)
    
    def build(self) -> str:
        """Construct the complete system prompt."""
        parts = []
        
        # Core instructions
        if self.instructions:
            parts.append(f"## Instructions\n{self.instructions}")
        
        # Personality
        if self.personality:
            parts.append(f"## Personality\n{self.personality}")
        
        # Custom sections (sorted by priority)
        sorted_sections = sorted(self.sections, key=lambda x: -x.priority)
        for section in sorted_sections:
            parts.append(f"## {section.name}\n{section.content}")
        
        # Tools
        if self.tools:
            tools_json = json.dumps([t.to_dict() for t in self.tools], indent=2, ensure_ascii=False)
            parts.append(f"## Available Tools\n{tools_json}")
        
        # Tool usage instructions
        if self.tools:
            tool_usage = """## Tool Usage
When you need to use a tool, format your response as:
<function name="tool_name">
<parameter name="param1">value1
</parameter>
</function>

IMPORTANT: Always wrap tool calls in the XML tags exactly as shown above.
"""
            parts.append(tool_usage)
        
        return "\n\n".join(parts)
    
    def build_json(self) -> Dict[str, Any]:
        """Build prompt as a structured dictionary."""
        return {
            "prompt": self.build(),
            "sections": [
                {"name": s.name, "content": s.content, "priority": s.priority}
                for s in self.sections
            ],
            "tools": [t.to_dict() for t in self.tools],
            "personality": self.personality,
            "instructions": self.instructions
        }