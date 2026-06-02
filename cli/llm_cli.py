#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM Provider TUI Interface Module

Provides Text User Interface for LLM provider configuration.
"""

import argparse
import os
from typing import Optional
from agent.agent import Agent, AgentResponse
from llm_integration import LLMConfig, setup_llm_integration


def add_llm_arguments(parser: argparse.ArgumentParser):
    """Add LLM-related arguments to the parser."""
    llm_group = parser.add_argument_group('LLM Integration Options (25+ providers)')
    
    llm_group.add_argument(
        '--llm-provider',
        choices=[
            'openai', 'anthropic', 'google', 'deepseek', 'minimax', 'moonshot',
            'siliconflow', 'novita', 'hyperbolic', 'leapai', 'yi',
            'mistral', 'cohere', 'groq', 'fireworks', 'together',
            'zhipu', 'dashscope', 'volcengine', 'tencent', 'spark', '360',
            'perplexity', 'azure', 'custom'
        ],
        default=None,
        help='LLM provider'
    )
    
    llm_group.add_argument(
        '--llm-model',
        type=str,
        default=None,
        help='Specific model to use (e.g., gpt-4, claude-2)'
    )
    
    llm_group.add_argument(
        '--llm-api-key',
        type=str,
        default=None,
        help='API key for LLM provider (or set environment variable)'
    )
    
    llm_group.add_argument(
        '--llm-temperature',
        type=float,
        default=0.7,
        help='Sampling temperature for LLM (0.0 to 1.0)'
    )
    
    llm_group.add_argument(
        '--llm-max-tokens',
        type=int,
        default=1000,
        help='Maximum tokens in LLM response'
    )
    
    llm_group.add_argument(
        '--enable-llm-fallback',
        action='store_true',
        help='Enable fallback to template-based responses if LLM fails'
    )
    
    llm_group.add_argument(
        '--llm-base-url',
        type=str,
        default=None,
        help='Custom API base URL (e.g., https://api.example.com/v1)'
    )


def create_llm_config_from_args(args) -> Optional[LLMConfig]:
    """Create LLM configuration from command line arguments."""
    if not args.llm_provider:
        return None
        
    return LLMConfig(
        provider=args.llm_provider,
        model=args.llm_model,
        api_key=args.llm_api_key,
        base_url=args.llm_base_url,
        temperature=args.llm_temperature,
        max_tokens=args.llm_max_tokens,
        enable_fallback=args.enable_llm_fallback
    )


def setup_environment_variables(args):
    """Set up environment variables for LLM providers."""
    if args.llm_provider == 'openai' and args.llm_api_key:
        os.environ['OPENAI_API_KEY'] = args.llm_api_key
    elif args.llm_provider == 'anthropic' and args.llm_api_key:
        os.environ['ANTHROPIC_API_KEY'] = args.llm_api_key


def get_llm_usage_instructions():
    """Get instructions for LLM usage."""
    return """
LLM Integration Instructions:

1. OpenAI Setup:
   - Get API key from https://platform.openai.com/api-keys
   - Set environment variable: export OPENAI_API_KEY="your-key"
   - Or use --llm-api-key flag

2. Anthropic Setup:
   - Get API key from https://console.anthropic.com/
   - Set environment variable: export ANTHROPIC_API_KEY="your-key"  
   - Or use --llm-api-key flag

3. Example commands:
   # Use OpenAI with environment variable
   export OPENAI_API_KEY="sk-..."
   python main.py --query "Explain quantum computing" --llm-provider openai
   
   # Use Anthropic with API key flag
   python main.py --query "Explain neural networks" --llm-provider anthropic --llm-api-key "your-key"
   
   # Specify custom model
   python main.py --query "Code review" --llm-provider openai --llm-model gpt-4
"""