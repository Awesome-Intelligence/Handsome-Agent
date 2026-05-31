#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the modern_agent module.

Tests cover:
- ModernAgent initialization
- Chat functionality
- Tool integration
- Response generation
"""

import pytest
import json
import asyncio
from unittest.mock import patch, MagicMock
from dataclasses import asdict


class TestModernAgent:
    """Test suite for ModernAgent."""

    def test_agent_initialization(self):
        """Test agent initializes correctly."""
        from core.modern_agent import ModernAgent
        
        agent = ModernAgent(llm_provider=None)
        
        assert agent is not None
        assert hasattr(agent, 'engine')
        assert hasattr(agent, '_session')

    def test_agent_with_llm_provider(self):
        """Test agent initialization with LLM provider."""
        from core.modern_agent import ModernAgent
        
        mock_llm = MagicMock()
        agent = ModernAgent(llm_provider=mock_llm)
        
        assert agent.llm_provider is mock_llm

    def test_agent_without_session(self):
        """Test agent initialization without session."""
        from core.modern_agent import ModernAgent
        
        agent = ModernAgent(llm_provider=None, enable_session=False)
        
        assert agent._session is None


class TestModernAgentChat:
    """Test chat functionality."""

    @pytest.mark.asyncio
    async def test_chat_returns_response(self):
        """Test that chat returns a response."""
        from core.modern_agent import ModernAgent
        
        agent = ModernAgent(llm_provider=None)
        
        response = await agent.chat("打开计算器")
        
        assert response is not None
        assert hasattr(response, 'content')
        assert hasattr(response, 'tool_used')
        assert hasattr(response, 'confidence_score')

    @pytest.mark.asyncio
    async def test_chat_with_tool_execution(self):
        """Test chat with tool execution."""
        from core.modern_agent import ModernAgent
        
        agent = ModernAgent(llm_provider=None)
        
        response = await agent.chat("打开计算器")
        
        # Should have executed a tool
        assert response.tool_used is not None or len(response.content) > 0

    @pytest.mark.asyncio
    async def test_chat_empty_input(self):
        """Test chat with empty input."""
        from core.modern_agent import ModernAgent
        
        agent = ModernAgent(llm_provider=None)
        
        # Should handle empty input gracefully
        response = await agent.chat("")
        
        assert response is not None

    @pytest.mark.asyncio
    async def test_chat_records_to_session(self):
        """Test that chat records to session."""
        from core.modern_agent import ModernAgent
        
        agent = ModernAgent(llm_provider=None, enable_session=True)
        
        await agent.chat("打开计算器")
        
        # Session should have messages
        if agent._session:
            assert len(agent._session.messages) > 0


class TestModernAgentToolList:
    """Test tool listing functionality."""

    def test_get_tool_list(self):
        """Test getting list of tools."""
        from core.modern_agent import ModernAgent
        
        agent = ModernAgent(llm_provider=None)
        tools = agent.get_tool_list()
        
        assert isinstance(tools, list)
        assert len(tools) > 0

    def test_tool_list_has_required_fields(self):
        """Test that tool list has required fields."""
        from core.modern_agent import ModernAgent
        
        agent = ModernAgent(llm_provider=None)
        tools = agent.get_tool_list()
        
        for tool in tools:
            assert 'name' in tool
            assert 'description' in tool


class TestModernAgentResponse:
    """Test response structure."""

    def test_response_has_required_fields(self):
        """Test that response has required fields."""
        from core.modern_agent import ModernAgentResponse
        
        response = ModernAgentResponse(
            content="Test response",
            tool_used="open_calculator",
            confidence_score=0.9
        )
        
        assert response.content == "Test response"
        assert response.tool_used == "open_calculator"
        assert response.confidence_score == 0.9

    def test_response_defaults(self):
        """Test response default values."""
        from core.modern_agent import ModernAgentResponse
        
        response = ModernAgentResponse(content="Test")
        
        assert response.tool_used is None
        assert response.tool_result is None
        assert response.confidence_score == 1.0


class TestModernAgentIntegration:
    """Test integration with other modules."""

    def test_agent_uses_integrated_engine(self):
        """Test that agent uses integrated engine."""
        from core.modern_agent import ModernAgent
        from tools.integrated_tools import get_integrated_engine
        
        agent = ModernAgent(llm_provider=None)
        
        # Agent should have the integrated engine
        assert agent.engine is not None
        
        # Engine should be the same as get_integrated_engine
        expected_engine = get_integrated_engine()
        assert agent.engine is expected_engine

    def test_agent_initializes_tools(self):
        """Test that agent initializes tools."""
        from core.modern_agent import ModernAgent
        from tools.integrated_tools import initialize_tools
        
        initialize_tools()
        
        agent = ModernAgent(llm_provider=None)
        
        # Should have tools registered
        assert len(agent.engine.tool_selector.tools) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
