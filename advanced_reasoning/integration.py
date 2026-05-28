#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration utilities for the Advanced Reasoning module.

This module provides functions to integrate the advanced reasoning capabilities
with the core agent system.
"""

from typing import Optional
from core import CustomAgent, AgentConfig
from .module import AdvancedReasoningModule


def enhance_agent_with_advanced_reasoning(agent_config: Optional[AgentConfig] = None, 
                                          llm_provider=None) -> 'CustomAgent':
    """Create an enhanced agent with advanced reasoning capabilities.
    
    This function creates a CustomAgent instance and replaces its explanation
    module with the AdvancedReasoningModule to provide intelligent, knowledge-based
    responses instead of basic template-based responses.
    
    Args:
        agent_config: Optional AgentConfig instance. If not provided, uses default configuration.
        llm_provider: Optional LLM provider instance for AI-powered responses.
        
    Returns:
        CustomAgent: Enhanced agent instance with advanced reasoning capabilities.
        
    Examples:
        >>> from advanced_reasoning.integration import enhance_agent_with_advanced_reasoning
        >>> agent = enhance_agent_with_advanced_reasoning()
        >>> response = await agent.respond("How do I optimize Python code?")
    """
    config = agent_config or AgentConfig()
    agent = CustomAgent(config)
    
    # Create advanced reasoning module with LLM provider
    advanced_module = AdvancedReasoningModule(config)
    
    # Pass LLM provider to the module if available
    if llm_provider is not None:
        advanced_module.set_llm_provider(llm_provider)
        # Also store LLM provider on agent for router context
        agent.llm_provider = llm_provider
        # Update IntentClassifier with LLM provider for intent classification
        agent._intent_classifier.set_llm_provider(llm_provider)
    
    # Replace the explanation module with advanced reasoning module
    agent.explanation_module = advanced_module
    
    return agent