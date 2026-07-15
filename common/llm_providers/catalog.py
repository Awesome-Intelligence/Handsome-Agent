#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LLM Provider 元数据目录（纯数据 + 查询函数）

🚪 Access - 💬 Common - LLM Providers - Catalog

本模块只包含 Provider 元数据字典和纯查询函数，不引入任何 UI 依赖。
CLI（``cli.cli_commands.providers``）与 TUI（``tui.views.settings_screen``）
均通过此模块访问 Provider 列表。
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional


# ============================================================================
# Provider 元数据字典
# ============================================================================

PROVIDERS: Dict[str, Dict[str, Any]] = {
    "openai": {
        "name": "OpenAI",
        "display_name": "OpenAI",
        "website": "https://openai.com",
        "models": [
            "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4",
            "gpt-3.5-turbo", "gpt-3.5-turbo-16k",
        ],
        "default_model": "gpt-4o",
        "capabilities": ["chat", "vision", "function_calling", "json_mode"],
        "pricing": {"input": 5.0, "output": 15.0},
        "context_windows": {"gpt-4o": 128000, "gpt-4o-mini": 128000},
        "status": "active",
        "env_vars": ["OPENAI_API_KEY"],
    },
    "anthropic": {
        "name": "Anthropic",
        "display_name": "Anthropic (Claude)",
        "website": "https://anthropic.com",
        "models": [
            "claude-3-5-sonnet-20241022", "claude-3-5-sonnet-latest",
            "claude-3-opus-20240229", "claude-3-opus-latest",
            "claude-3-sonnet-20240229", "claude-3-sonnet-latest",
            "claude-3-haiku-20240307", "claude-3-haiku-latest",
        ],
        "default_model": "claude-3-5-sonnet-20241022",
        "capabilities": ["chat", "vision", "function_calling", "long_context"],
        "pricing": {"input": 3.0, "output": 15.0},
        "context_windows": {"claude-3-5-sonnet-20241022": 200000},
        "status": "active",
        "env_vars": ["ANTHROPIC_API_KEY"],
    },
    "deepseek": {
        "name": "DeepSeek",
        "display_name": "DeepSeek",
        "website": "https://deepseek.com",
        "models": ["deepseek-chat", "deepseek-coder"],
        "default_model": "deepseek-chat",
        "capabilities": ["chat", "function_calling", "coding"],
        "pricing": {"input": 0.14, "output": 0.28},
        "context_windows": {"deepseek-chat": 64000},
        "status": "active",
        "env_vars": ["DEEPSEEK_API_KEY"],
    },
    "google": {
        "name": "Google",
        "display_name": "Google (Gemini)",
        "website": "https://ai.google.dev",
        "models": [
            "gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash",
            "gemini-1.5-flash-8b", "gemini-pro",
        ],
        "default_model": "gemini-1.5-flash",
        "capabilities": ["chat", "vision", "function_calling"],
        "pricing": {"input": 0.075, "output": 0.3},
        "context_windows": {"gemini-1.5-flash": 1000000},
        "status": "active",
        "env_vars": ["GOOGLE_API_KEY"],
    },
    "minimax": {
        "name": "MiniMax",
        "display_name": "MiniMax",
        "website": "https://www.minimax.io",
        "models": ["MiniMax-Text-01", "abab6.5s-chat", "abab6.5-chat"],
        "default_model": "MiniMax-Text-01",
        "capabilities": ["chat", "function_calling"],
        "pricing": {"input": 0.1, "output": 0.1},
        "context_windows": {"MiniMax-Text-01": 1000000},
        "status": "active",
        "env_vars": ["MINIMAX_API_KEY"],
    },
    "moonshot": {
        "name": "Moonshot",
        "display_name": "Moonshot AI",
        "website": "https://www.moonshot.cn",
        "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
        "default_model": "moonshot-v1-8k",
        "capabilities": ["chat", "long_context"],
        "pricing": {"input": 0.06, "output": 0.06},
        "context_windows": {"moonshot-v1-128k": 128000},
        "status": "active",
        "env_vars": ["MOONSHOT_API_KEY"],
    },
    "groq": {
        "name": "Groq",
        "display_name": "Groq",
        "website": "https://console.groq.com",
        "models": [
            "llama-3.1-70b-versatile", "llama-3.1-8b-instant",
            "mixtral-8x7b-32768", "gemma2-9b-it",
        ],
        "default_model": "llama-3.1-8b-instant",
        "capabilities": ["chat", "fast_inference"],
        "pricing": {"input": 0, "output": 0},
        "context_windows": {"llama-3.1-70b-versatile": 128000},
        "status": "active",
        "env_vars": ["GROQ_API_KEY"],
    },
    "zhipu": {
        "name": "Zhipu",
        "display_name": "Zhipu AI (智谱清言)",
        "website": "https://www.zhipuai.cn",
        "models": ["glm-4", "glm-4-flash", "glm-4-plus", "glm-3-turbo"],
        "default_model": "glm-4-flash",
        "capabilities": ["chat", "function_calling"],
        "pricing": {"input": 0.1, "output": 0.1},
        "context_windows": {"glm-4": 128000},
        "status": "active",
        "env_vars": ["ZHIPU_API_KEY"],
    },
    "dashscope": {
        "name": "DashScope",
        "display_name": "阿里云 DashScope",
        "website": "https://www.aliyun.com/product/dashscope",
        "models": [
            "qwen-turbo", "qwen-plus", "qwen-max",
            "qwen2-72b-instruct", "qwen2-57b-a14b-instruct",
        ],
        "default_model": "qwen-turbo",
        "capabilities": ["chat", "vision", "function_calling"],
        "pricing": {"input": 0.02, "output": 0.06},
        "context_windows": {"qwen-max": 32000},
        "status": "active",
        "env_vars": ["DASHSCOPE_API_KEY"],
    },
    "volcengine": {
        "name": "VolcEngine",
        "display_name": "火山引擎 (豆包)",
        "website": "https://www.volcengine.com",
        "models": ["doubao-pro-32k", "doubao-lite-32k"],
        "default_model": "doubao-pro-32k",
        "capabilities": ["chat", "function_calling"],
        "pricing": {"input": 0.05, "output": 0.05},
        "context_windows": {"doubao-pro-32k": 32000},
        "status": "active",
        "env_vars": ["VOLC_ACCESS_KEY", "VOLC_SECRET_KEY"],
    },
}


# ============================================================================
# 纯查询函数（无 UI 依赖）
# ============================================================================


def get_provider_ids() -> List[str]:
    """获取所有 Provider ID 列表。"""
    return sorted(PROVIDERS.keys())


def get_provider_info(provider_id: str) -> Optional[Dict[str, Any]]:
    """获取 Provider 详细信息。

    Args:
        provider_id: Provider ID（如 'openai'）

    Returns:
        Provider 元数据字典，若不存在则返回 None
    """
    return PROVIDERS.get(provider_id)