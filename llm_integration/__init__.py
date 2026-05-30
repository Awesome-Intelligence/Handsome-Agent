#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-Provider LLM Integration Module

Provides unified interface for integrating with 50+ LLM providers.
Supports OpenAI-compatible APIs and custom provider implementations.

Supported Providers (API endpoints verified based on Hermes and official docs):
- OpenAI: GPT-4o, GPT-4 Turbo, GPT-3.5, GPT-5.x series
- Anthropic: Claude 3.5 Sonnet, Opus 4.x, Haiku 4.x
- Google: Gemini 3.x Pro/Flash/Lite, Gemini 1.5 Pro/Flash
- DeepSeek: DeepSeek V4 Pro/Flash, V3.2, R1
- MiniMax: MiniMax-M2.7, M2.5, M2.1
- Moonshot Kimi: kimi-k2.6, kimi-k2.5, kimi-k2-thinking
- Zhipu AI: GLM-5.1, GLM-5, GLM-4.7, GLM-4V
- Qwen: Qwen3.6 Plus, Qwen3.5 Plus, Qwen3-Coder
- Xiaomi MiMo: mimo-v2.5-pro, mimo-v2.5, mimo-v2-flash
- Tencent: hy3-preview
- NVIDIA: Nemotron 3 Super, Llama 3.3 Nemotron
- StepFun: step-3.5-flash
- Arcee: Trinity models
- Grok: grok-4.3, grok-4.20-reasoning
- OpenRouter: 100+ aggregated models
- And many more via OpenAI-compatible API

Author: Handsome Agent Team
Version: 1.1.0
"""

import os
import json
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable, Protocol
from enum import Enum

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from core.logging_manager import get_llm_logger


class AsyncHTTPClient:
    """Async HTTP client using httpx for better async support.
    
    Falls back to urllib if httpx is not available.
    """
    
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self._client = None
    
    async def __aenter__(self):
        if HTTPX_AVAILABLE:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
    
    async def post(self, url: str, headers: Dict[str, str], data: Dict[str, Any]) -> Dict[str, Any]:
        """Make async POST request."""
        if HTTPX_AVAILABLE and self._client:
            response = await self._client.post(url, json=data, headers=headers)
            response.raise_for_status()
            return response.json()
        
        # Fallback to urllib
        import urllib.request
        import urllib.error
        
        data_bytes = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else "{}"
            raise LLMAPIError(f"HTTP {e.code}: {error_body}", e.code)
    
    async def get(self, url: str, headers: Dict[str, str] = None) -> Dict[str, Any]:
        """Make async GET request."""
        if HTTPX_AVAILABLE and self._client:
            response = await self._client.get(url, headers=headers or {})
            response.raise_for_status()
            return response.json()
        
        # Fallback to urllib
        import urllib.request
        req = urllib.request.Request(url, headers=headers or {}, method='GET')
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            return json.loads(response.read().decode('utf-8'))


class LLMProviderType(Enum):
    """Provider types for classification."""
    OPENAI_COMPATIBLE = "openai_compatible"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    COHERE = "cohere"
    MISTRAL = "mistral"
    AZURE = "azure"
    AWS = "aws"
    CUSTOM = "custom"
    MINIMAX = "minimax"
    SPARK = "spark"


@dataclass
class ModelInfo:
    """Information about a specific model."""
    id: str
    name: str
    description: str
    context_length: int
    supports_functions: bool = True
    input_cost_per_1m: float = 0.0
    output_cost_per_1m: float = 0.0
    recommended: bool = False
    free: bool = False


@dataclass
class ProviderEntry:
    """Provider definition for model picker."""
    slug: str
    label: str
    description: str
    base_url: str
    api_key_env_vars: List[str] = field(default_factory=list)
    default_model: str = ""


@dataclass
class LLMConfig:
    """Configuration for LLM integration."""
    provider: str = "none"
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: float = 60.0
    enable_fallback: bool = True
    extra_headers: Dict[str, str] = field(default_factory=dict)
    enable_detailed_logs: bool = True

    def is_enabled(self) -> bool:
        """Check if LLM is configured and enabled."""
        return self.provider != "none" and self.api_key is not None


class LLMProviderProtocol(Protocol):
    """Protocol for LLM provider implementations."""
    async def generate(self, prompt: str, config: LLMConfig) -> str:
        """Generate response from LLM."""
        ...
    
    def get_models(self) -> List[ModelInfo]:
        """Get available models for this provider."""
        ...


# =============================================================================
# Canonical Provider List - Single Source of Truth
# =============================================================================

PROVIDERS: List[ProviderEntry] = [
    # AI Aggregators
    ProviderEntry(
        "openrouter", "OpenRouter", 
        "OpenRouter (100+ models, pay-per-use)",
        "https://openrouter.ai/api/v1",
        ["OPENAI_API_KEY", "OPENROUTER_API_KEY"],
        "anthropic/claude-opus-4.7"
    ),
    ProviderEntry(
        "novita", "NovitaAI",
        "NovitaAI (AI-native cloud: Model API, Agent Sandbox, GPU Cloud)",
        "https://api.novita.ai/v3",
        ["NOVITA_API_KEY"],
        "moonshotai/kimi-k2.5"
    ),
    ProviderEntry(
        "huggingface", "Hugging Face",
        "Hugging Face Inference Providers (20+ open models)",
        "https://api-inference.huggingface.co/models",
        ["HUGGING_FACE_API_KEY"],
        "moonshotai/Kimi-K2.5"
    ),
    ProviderEntry(
        "nvidia", "NVIDIA NIM",
        "NVIDIA NIM (Nemotron models — build.nvidia.com or local NIM)",
        "https://integrate.api.nvidia.com/v1",
        ["NVIDIA_API_KEY"],
        "nvidia/nemotron-3-super-120b-a12b"
    ),
    ProviderEntry(
        "opencode-zen", "OpenCode Zen",
        "OpenCode Zen (35+ curated models, pay-as-you-go)",
        "https://api.opencode.com/v1",
        ["OPENCODE_API_KEY"],
        "kimi-k2.5"
    ),
    ProviderEntry(
        "kilocode", "Kilo Code",
        "Kilo Code (Kilo Gateway API)",
        "https://api.kilocode.com/v1",
        ["KILO_API_KEY"],
        "anthropic/claude-opus-4.6"
    ),
    ProviderEntry(
        "gmi", "GMI Cloud",
        "GMI Cloud (multi-model direct API)",
        "https://api.gmi-serving.com/v1",
        ["GMI_API_KEY"],
        "zai-org/GLM-5.1-FP8"
    ),
    
    # Major Providers
    ProviderEntry(
        "openai", "OpenAI",
        "OpenAI (GPT-4o, GPT-5.x series)",
        "https://api.openai.com/v1",
        ["OPENAI_API_KEY"],
        "gpt-5.4"
    ),
    ProviderEntry(
        "anthropic", "Anthropic",
        "Anthropic (Claude models — API key or Claude Code)",
        "https://api.anthropic.com/v1",
        ["ANTHROPIC_API_KEY", "ANTHROPIC_TOKEN"],
        "claude-opus-4-7"
    ),
    ProviderEntry(
        "gemini", "Google AI Studio",
        "Google AI Studio (Gemini models — native Gemini API)",
        "https://generativelanguage.googleapis.com/v1",
        ["GOOGLE_API_KEY"],
        "gemini-3.1-pro-preview"
    ),
    ProviderEntry(
        "xai", "xAI Grok",
        "xAI (Grok models — direct API)",
        "https://api.x.ai/v1",
        ["XAI_API_KEY"],
        "grok-4.3"
    ),
    
    # Chinese Providers
    ProviderEntry(
        "minimax", "MiniMax",
        "MiniMax (global direct API)",
        "https://api.minimax.chat/v1",
        ["MINIMAX_API_KEY"],
        "MiniMax-M2.7"
    ),
    ProviderEntry(
        "moonshot", "Moonshot Kimi",
        "Kimi / Moonshot (api.moonshot.cn)",
        "https://api.moonshot.cn/v1",
        ["MOONSHOT_API_KEY"],
        "kimi-k2.6"
    ),
    ProviderEntry(
        "deepseek", "DeepSeek",
        "DeepSeek (DeepSeek-V4, R1, coder — direct API)",
        "https://api.deepseek.com/v1",
        ["DEEPSEEK_API_KEY"],
        "deepseek-v4-pro"
    ),
    ProviderEntry(
        "zhipu", "Zhipu AI / GLM",
        "Zhipu AI (GLM-5.x, GLM-4.x series)",
        "https://open.bigmodel.cn/api/paas/v4",
        ["ZHIPU_API_KEY", "GLM_API_KEY", "ZAI_API_KEY"],
        "glm-5.1"
    ),
    ProviderEntry(
        "dashscope", "Qwen Cloud",
        "Qwen Cloud / DashScope (Qwen + multi-provider)",
        "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        ["DASHSCOPE_API_KEY", "ALIYUN_API_KEY"],
        "qwen3.6-plus"
    ),
    ProviderEntry(
        "xiaomi", "Xiaomi MiMo",
        "Xiaomi MiMo (MiMo-V2.5 and V2 models)",
        "https://api.mimo.xiaomi.com/v1",
        ["XIAOMI_API_KEY"],
        "mimo-v2.5-pro"
    ),
    ProviderEntry(
        "tencent", "Tencent TokenHub",
        "Tencent TokenHub (Hy3 Preview)",
        "https://tokenhub.tencentmaas.com/api/text/v1",
        ["TENCENT_API_KEY"],
        "hy3-preview"
    ),
    ProviderEntry(
        "stepfun", "StepFun Step Plan",
        "StepFun Step Plan (agent/coding models)",
        "https://api.stepfun.ai/step_plan/v1",
        ["STEPFUN_API_KEY"],
        "step-3.5-flash"
    ),
    
    # Specialized Providers
    ProviderEntry(
        "arcee", "Arcee AI",
        "Arcee AI (Trinity models)",
        "https://api.arcee.ai/api/v1",
        ["ARCEE_API_KEY"],
        "trinity-large-thinking"
    ),
    ProviderEntry(
        "ollama-cloud", "Ollama Cloud",
        "Ollama Cloud (cloud-hosted open models)",
        "https://ollama.com/v1",
        ["OLLAMA_API_KEY"],
        ""
    ),
    
    # Enterprise Providers
    ProviderEntry(
        "azure", "Azure OpenAI",
        "Azure OpenAI Service",
        "",  # User provides custom URL
        ["AZURE_OPENAI_API_KEY"],
        "gpt-4o"
    ),
    ProviderEntry(
        "bedrock", "AWS Bedrock",
        "AWS Bedrock (Claude, Nova, Llama, DeepSeek)",
        "https://bedrock-runtime.us-east-1.amazonaws.com",
        [],  # Uses AWS SDK credentials
        "us.anthropic.claude-sonnet-4-6"
    ),
    
    # Local Development
    ProviderEntry(
        "lmstudio", "LM Studio",
        "LM Studio (local desktop app with built-in model server)",
        "http://127.0.0.1:1234/v1",
        ["LM_API_KEY"],
        ""
    ),
    ProviderEntry(
        "ollama", "Ollama Local",
        "Ollama (local open models)",
        "http://localhost:11434/v1",
        [],
        ""
    ),
]

# Provider aliases for user-friendly input
PROVIDER_ALIASES: Dict[str, str] = {
    # OpenRouter
    "openrouter": "openrouter",
    
    # OpenAI
    "openai": "openai",
    "gpt": "openai",
    "chatgpt": "openai",
    
    # Anthropic
    "anthropic": "anthropic",
    "claude": "anthropic",
    "claude-code": "anthropic",
    
    # Google
    "gemini": "gemini",
    "google": "gemini",
    "google-ai": "gemini",
    
    # xAI
    "xai": "xai",
    "grok": "xai",
    "x-ai": "xai",
    
    # MiniMax
    "minimax": "minimax",
    "minimax-cn": "minimax",
    "minimax-global": "minimax",
    
    # Moonshot
    "moonshot": "moonshot",
    "kimi": "moonshot",
    "kimi-coding": "moonshot",
    
    # DeepSeek
    "deepseek": "deepseek",
    "deep-seek": "deepseek",
    
    # Zhipu/GLM
    "zhipu": "zhipu",
    "glm": "zhipu",
    "zai": "zhipu",
    "z-ai": "zhipu",
    
    # Qwen/DashScope
    "qwen": "dashscope",
    "dashscope": "dashscope",
    "alibaba": "dashscope",
    "aliyun": "dashscope",
    
    # Xiaomi
    "xiaomi": "xiaomi",
    "mimo": "xiaomi",
    
    # Tencent
    "tencent": "tencent",
    "tokenhub": "tencent",
    
    # StepFun
    "stepfun": "stepfun",
    "step": "stepfun",
    
    # NVIDIA
    "nvidia": "nvidia",
    "nim": "nvidia",
    "nemotron": "nvidia",
    
    # Hugging Face
    "huggingface": "huggingface",
    "hf": "huggingface",
    
    # Novita
    "novita": "novita",
    "novitaai": "novita",
    
    # Arcee
    "arcee": "arcee",
    "arcee-ai": "arcee",
    
    # GMI
    "gmi": "gmi",
    "gmi-cloud": "gmi",
    
    # OpenCode
    "opencode": "opencode-zen",
    "zen": "opencode-zen",
    "opencode-go": "opencode-zen",
    
    # KiloCode
    "kilocode": "kilocode",
    "kilo": "kilocode",
    
    # Ollama
    "ollama": "ollama",
    "ollama-cloud": "ollama-cloud",
    
    # LM Studio
    "lmstudio": "lmstudio",
    
    # Azure
    "azure": "azure",
    "azure-openai": "azure",
    
    # Bedrock
    "bedrock": "bedrock",
    "aws": "bedrock",
    "aws-bedrock": "bedrock",
}


# =============================================================================
# Model Catalog - Updated with latest models from Hermes
# =============================================================================

MODEL_CATALOG: Dict[str, List[ModelInfo]] = {
    # OpenAI
    "openai": [
        ModelInfo("gpt-5.4", "GPT-5.4", "Latest GPT-5 model", 128000, True, 15.0, 45.0, True),
        ModelInfo("gpt-5.4-mini", "GPT-5.4 Mini", "Efficient GPT-5 variant", 128000, True, 1.5, 4.5),
        ModelInfo("gpt-5-mini", "GPT-5 Mini", "Compact GPT-5 model", 128000, True, 1.0, 3.0),
        ModelInfo("gpt-5.3-codex", "GPT-5.3 Codex", "Code-focused model", 128000, True, 30.0, 90.0),
        ModelInfo("gpt-4o", "GPT-4o", "GPT-4 Omni", 128000, True, 5.0, 15.0),
        ModelInfo("gpt-4o-mini", "GPT-4o Mini", "Efficient GPT-4o", 128000, True, 0.15, 0.6),
    ],
    
    # Anthropic
    "anthropic": [
        ModelInfo("claude-opus-4-7", "Claude Opus 4.7", "Latest flagship model", 200000, True, 15.0, 75.0, True),
        ModelInfo("claude-opus-4-6", "Claude Opus 4.6", "Previous flagship", 200000, True, 15.0, 75.0),
        ModelInfo("claude-sonnet-4-6", "Claude Sonnet 4.6", "Balanced performance", 200000, True, 3.0, 15.0),
        ModelInfo("claude-haiku-4-5", "Claude Haiku 4.5", "Fast and efficient", 200000, True, 0.25, 1.25),
    ],
    
    # Google Gemini
    "gemini": [
        ModelInfo("gemini-3.1-pro-preview", "Gemini 3.1 Pro", "Latest Pro model", 1048576, True, 7.0, 21.0, True),
        ModelInfo("gemini-3-pro-preview", "Gemini 3 Pro", "Gemini 3 flagship", 1048576, True, 12.5, 37.5),
        ModelInfo("gemini-3-flash-preview", "Gemini 3 Flash", "Fast and capable", 1048576, True, 0.15, 0.6),
        ModelInfo("gemini-3.1-flash-lite-preview", "Gemini 3.1 Flash Lite", "Most efficient", 1048576, True, 0.075, 0.3),
        ModelInfo("gemini-1.5-pro", "Gemini 1.5 Pro", "Pro model", 1048576, True, 3.5, 10.5),
        ModelInfo("gemini-1.5-flash", "Gemini 1.5 Flash", "Flash model", 1048576, True, 0.125, 0.5),
    ],
    
    # xAI Grok
    "xai": [
        ModelInfo("grok-4.3", "Grok 4.3", "Latest Grok model", 131072, True, 3.0, 9.0, True),
        ModelInfo("grok-4.20-0309-reasoning", "Grok 4.20 Reasoning", "Advanced reasoning", 131072, True, 5.0, 15.0),
        ModelInfo("grok-4.20-0309-non-reasoning", "Grok 4.20 Non-Reasoning", "Standard model", 131072, True, 2.0, 6.0),
    ],
    
    # MiniMax
    "minimax": [
        ModelInfo("MiniMax-M2.7", "MiniMax M2.7", "Latest MiniMax model", 128000, True, 2.0, 6.0, True),
        ModelInfo("MiniMax-M2.5", "MiniMax M2.5", "Previous model", 128000, True, 1.5, 4.5),
        ModelInfo("MiniMax-M2.1", "MiniMax M2.1", "Legacy model", 65536, True, 1.0, 3.0),
    ],
    
    # Moonshot Kimi
    "moonshot": [
        ModelInfo("kimi-k2.6", "Kimi K2.6", "Latest Kimi model", 200000, True, 2.0, 6.0, True),
        ModelInfo("kimi-k2.5", "Kimi K2.5", "Previous model", 200000, True, 1.8, 5.4),
        ModelInfo("kimi-k2-thinking", "Kimi K2 Thinking", "Reasoning-focused", 200000, True, 3.0, 9.0),
        ModelInfo("kimi-k2-turbo-preview", "Kimi K2 Turbo", "Fast variant", 200000, True, 2.5, 7.5),
    ],
    
    # DeepSeek
    "deepseek": [
        ModelInfo("deepseek-v4-pro", "DeepSeek V4 Pro", "Latest flagship", 128000, True, 2.0, 6.0, True),
        ModelInfo("deepseek-v4-flash", "DeepSeek V4 Flash", "Fast and efficient", 128000, True, 0.5, 1.5),
        ModelInfo("deepseek-chat", "DeepSeek Chat", "Standard model", 65536, True, 0.8, 2.4),
        ModelInfo("deepseek-reasoner", "DeepSeek Reasoner", "Reasoning model", 128000, True, 3.0, 9.0),
        ModelInfo("deepseek-v3.2", "DeepSeek V3.2", "Legacy model", 81920, True, 1.5, 4.5),
    ],
    
    # Zhipu GLM
    "zhipu": [
        ModelInfo("glm-5.1", "GLM-5.1", "Latest GLM model", 128000, True, 2.0, 6.0, True),
        ModelInfo("glm-5", "GLM-5", "Previous model", 128000, True, 1.8, 5.4),
        ModelInfo("glm-5v-turbo", "GLM-5V Turbo", "Vision model", 128000, True, 2.5, 7.5),
        ModelInfo("glm-4.7", "GLM-4.7", "Legacy model", 65536, True, 1.5, 4.5),
        ModelInfo("glm-4.5", "GLM-4.5", "Legacy model", 65536, True, 1.2, 3.6),
        ModelInfo("glm-4v", "GLM-4V", "Vision model", 65536, True, 1.8, 5.4),
    ],
    
    # Qwen (DashScope)
    "dashscope": [
        ModelInfo("qwen3.6-plus", "Qwen 3.6 Plus", "Latest Qwen model", 200000, True, 1.5, 4.5, True),
        ModelInfo("qwen3.5-plus", "Qwen 3.5 Plus", "Previous model", 128000, True, 1.2, 3.6),
        ModelInfo("qwen3-coder-plus", "Qwen 3 Coder Plus", "Code model", 128000, True, 2.0, 6.0),
        ModelInfo("qwen3-coder-next", "Qwen 3 Coder Next", "Advanced code", 128000, True, 2.5, 7.5),
        ModelInfo("qwen2.5-max", "Qwen 2.5 Max", "Legacy model", 128000, True, 1.0, 3.0),
    ],
    
    # Xiaomi MiMo
    "xiaomi": [
        ModelInfo("mimo-v2.5-pro", "MiMo V2.5 Pro", "Latest pro model", 128000, True, 1.5, 4.5, True),
        ModelInfo("mimo-v2.5", "MiMo V2.5", "Standard model", 128000, True, 1.0, 3.0),
        ModelInfo("mimo-v2-pro", "MiMo V2 Pro", "Legacy pro", 65536, True, 0.8, 2.4),
        ModelInfo("mimo-v2-flash", "MiMo V2 Flash", "Fast model", 65536, True, 0.3, 0.9),
    ],
    
    # Tencent
    "tencent": [
        ModelInfo("hy3-preview", "Hy3 Preview", "Tencent's LLM", 128000, True, 1.0, 3.0, True),
    ],
    
    # StepFun
    "stepfun": [
        ModelInfo("step-3.5-flash", "Step 3.5 Flash", "Latest model", 128000, True, 0.5, 1.5, True),
        ModelInfo("step-3.5-flash-2603", "Step 3.5 Flash 2603", "Previous version", 128000, True, 0.5, 1.5),
    ],
    
    # NVIDIA
    "nvidia": [
        ModelInfo("nvidia/nemotron-3-super-120b-a12b", "Nemotron 3 Super", "Flagship model", 128000, True, 3.0, 9.0, True),
        ModelInfo("nvidia/nemotron-3-nano-30b-a3b", "Nemotron 3 Nano", "Compact model", 81920, True, 1.0, 3.0),
        ModelInfo("nvidia/llama-3.3-nemotron-super-49b-v1.5", "Llama 3.3 Nemotron", "Llama-based", 81920, True, 2.0, 6.0),
        ModelInfo("qwen/qwen3.5-397b-a17b", "Qwen 3.5 397B", "Large Qwen", 200000, True, 5.0, 15.0),
        ModelInfo("deepseek-ai/deepseek-v3.2", "DeepSeek V3.2", "DeepSeek on NIM", 81920, True, 2.0, 6.0),
    ],
    
    # Arcee
    "arcee": [
        ModelInfo("trinity-large-thinking", "Trinity Large Thinking", "Reasoning model", 128000, True, 2.0, 6.0, True),
        ModelInfo("trinity-large-preview", "Trinity Large", "Standard model", 128000, True, 1.5, 4.5),
        ModelInfo("trinity-mini", "Trinity Mini", "Compact model", 65536, True, 0.5, 1.5),
    ],
    
    # OpenRouter (aggregated)
    "openrouter": [
        ModelInfo("anthropic/claude-opus-4.7", "Claude Opus 4.7", "Anthropic flagship", 200000, True, 18.0, 90.0, True),
        ModelInfo("anthropic/claude-sonnet-4.6", "Claude Sonnet 4.6", "Balanced", 200000, True, 3.6, 18.0),
        ModelInfo("moonshotai/kimi-k2.6", "Kimi K2.6", "Recommended", 200000, True, 2.4, 7.2),
        ModelInfo("qwen/qwen3.6-plus", "Qwen 3.6 Plus", "Open-source", 200000, True, 1.8, 5.4),
        ModelInfo("openai/gpt-5.5", "GPT-5.5", "Latest GPT", 128000, True, 18.0, 54.0),
        ModelInfo("google/gemini-3-pro-preview", "Gemini 3 Pro", "Google flagship", 1048576, True, 15.0, 45.0),
        ModelInfo("x-ai/grok-4.3", "Grok 4.3", "xAI model", 131072, True, 3.6, 10.8),
        ModelInfo("deepseek/deepseek-v4-pro", "DeepSeek V4 Pro", "DeepSeek flagship", 128000, True, 2.4, 7.2),
        ModelInfo("z-ai/glm-5.1", "GLM-5.1", "Zhipu model", 128000, True, 2.4, 7.2),
        # Free tier models
        ModelInfo("openrouter/elephant-alpha", "Elephant Alpha", "Free model", 65536, True, 0.0, 0.0, False, True),
        ModelInfo("openrouter/owl-alpha", "Owl Alpha", "Free model", 65536, True, 0.0, 0.0, False, True),
    ],
    
    # Novita
    "novita": [
        ModelInfo("moonshotai/kimi-k2.5", "Kimi K2.5", "Moonshot on Novita", 200000, True, 2.0, 6.0, True),
        ModelInfo("minimax/minimax-m2.7", "MiniMax M2.7", "MiniMax on Novita", 128000, True, 1.8, 5.4),
        ModelInfo("zai-org/glm-5", "GLM-5", "Zhipu on Novita", 128000, True, 1.8, 5.4),
        ModelInfo("deepseek/deepseek-v3-0324", "DeepSeek V3", "DeepSeek on Novita", 81920, True, 1.5, 4.5),
    ],
    
    # Hugging Face
    "huggingface": [
        ModelInfo("moonshotai/Kimi-K2.5", "Kimi K2.5", "Moonshot on HF", 200000, True, 2.0, 6.0, True),
        ModelInfo("Qwen/Qwen3.5-397B-A17B", "Qwen 3.5 397B", "Large Qwen", 200000, True, 4.0, 12.0),
        ModelInfo("deepseek-ai/DeepSeek-V3.2", "DeepSeek V3.2", "DeepSeek on HF", 81920, True, 1.5, 4.5),
        ModelInfo("MiniMaxAI/MiniMax-M2.5", "MiniMax M2.5", "MiniMax on HF", 128000, True, 1.5, 4.5),
        ModelInfo("zai-org/GLM-5", "GLM-5", "Zhipu on HF", 128000, True, 1.5, 4.5),
    ],
    
    # GMI Cloud
    "gmi": [
        ModelInfo("zai-org/GLM-5.1-FP8", "GLM-5.1 FP8", "FP8 optimized", 128000, True, 1.5, 4.5, True),
        ModelInfo("deepseek-ai/DeepSeek-V3.2", "DeepSeek V3.2", "DeepSeek on GMI", 81920, True, 1.5, 4.5),
        ModelInfo("moonshotai/Kimi-K2.5", "Kimi K2.5", "Kimi on GMI", 200000, True, 1.8, 5.4),
        ModelInfo("google/gemini-3.1-flash-lite-preview", "Gemini 3.1 Flash Lite", "Efficient", 1048576, True, 0.1, 0.4),
    ],
    
    # OpenCode Zen
    "opencode-zen": [
        ModelInfo("kimi-k2.5", "Kimi K2.5", "Main model", 200000, True, 2.0, 6.0, True),
        ModelInfo("gpt-5.4-pro", "GPT-5.4 Pro", "OpenAI on Zen", 128000, True, 18.0, 54.0),
        ModelInfo("gpt-5.4", "GPT-5.4", "GPT-5.4 on Zen", 128000, True, 15.0, 45.0),
        ModelInfo("claude-opus-4-6", "Claude Opus 4.6", "Anthropic on Zen", 200000, True, 18.0, 90.0),
        ModelInfo("claude-sonnet-4-6", "Claude Sonnet 4.6", "Sonnet on Zen", 200000, True, 3.6, 18.0),
        ModelInfo("gemini-3.1-pro", "Gemini 3.1 Pro", "Google on Zen", 1048576, True, 8.4, 25.2),
        ModelInfo("minimax-m2.7", "MiniMax M2.7", "MiniMax on Zen", 128000, True, 1.8, 5.4),
        ModelInfo("glm-5", "GLM-5", "Zhipu on Zen", 128000, True, 1.8, 5.4),
    ],
    
    # KiloCode
    "kilocode": [
        ModelInfo("anthropic/claude-opus-4.6", "Claude Opus 4.6", "Anthropic", 200000, True, 18.0, 90.0, True),
        ModelInfo("anthropic/claude-sonnet-4.6", "Claude Sonnet 4.6", "Sonnet", 200000, True, 3.6, 18.0),
        ModelInfo("openai/gpt-5.4", "GPT-5.4", "OpenAI", 128000, True, 15.0, 45.0),
        ModelInfo("google/gemini-3-pro-preview", "Gemini 3 Pro", "Google", 1048576, True, 15.0, 45.0),
    ],
    
    # AWS Bedrock
    "bedrock": [
        ModelInfo("us.anthropic.claude-sonnet-4-6", "Claude Sonnet 4.6", "Anthropic on Bedrock", 200000, True, 3.0, 15.0, True),
        ModelInfo("us.anthropic.claude-opus-4-6-v1", "Claude Opus 4.6", "Opus on Bedrock", 200000, True, 15.0, 75.0),
        ModelInfo("us.anthropic.claude-haiku-4-5-20251001-v1:0", "Claude Haiku 4.5", "Haiku on Bedrock", 200000, True, 0.25, 1.25),
        ModelInfo("us.amazon.nova-pro-v1:0", "Amazon Nova Pro", "Amazon model", 128000, True, 2.0, 6.0),
        ModelInfo("us.amazon.nova-lite-v1:0", "Amazon Nova Lite", "Lite model", 128000, True, 0.5, 1.5),
        ModelInfo("deepseek.v3.2", "DeepSeek V3.2", "DeepSeek on Bedrock", 81920, True, 1.5, 4.5),
    ],
}


class ProviderRegistry:
    """Registry for LLM providers with automatic provider detection."""
    _providers: Dict[str, Dict[str, Any]] = {}
    _initialized = False
    
    @classmethod
    def get_provider(cls, provider_id: str) -> Optional[ProviderEntry]:
        """Get provider entry by ID or alias."""
        normalized = provider_id.lower().strip()
        # Check aliases first
        if normalized in PROVIDER_ALIASES:
            normalized = PROVIDER_ALIASES[normalized]
        
        for provider in PROVIDERS:
            if provider.slug.lower() == normalized:
                return provider
        return None
    
    @classmethod
    def get_provider_type(cls, provider_id: str) -> LLMProviderType:
        """Determine provider type from ID."""
        provider_lower = provider_id.lower().strip()
        
        if provider_lower in PROVIDER_ALIASES:
            provider_lower = PROVIDER_ALIASES[provider_lower]
        
        if provider_lower in ['openai', 'groq', 'fireworks', 'together', 'mistral',
                             'deepseek', 'moonshot', 'zhipu', 'dashscope', 'xiaomi',
                             'tencent', 'stepfun', 'nvidia', 'arcee', 'gmi', 'novita',
                             'huggingface', 'openrouter', 'opencode-zen', 'kilocode',
                             'ollama', 'ollama-cloud', 'lmstudio']:
            return LLMProviderType.OPENAI_COMPATIBLE
        elif provider_lower == 'anthropic':
            return LLMProviderType.ANTHROPIC
        elif provider_lower in ['google', 'gemini']:
            return LLMProviderType.GOOGLE
        elif provider_lower == 'cohere':
            return LLMProviderType.COHERE
        elif provider_lower == 'minimax':
            return LLMProviderType.MINIMAX
        elif provider_lower == 'azure':
            return LLMProviderType.AZURE
        elif provider_lower == 'bedrock':
            return LLMProviderType.AWS
        else:
            return LLMProviderType.OPENAI_COMPATIBLE
    
    @classmethod
    def get_models(cls, provider_id: str) -> List[ModelInfo]:
        """Get available models for a provider."""
        normalized = provider_id.lower().strip()
        if normalized in PROVIDER_ALIASES:
            normalized = PROVIDER_ALIASES[normalized]
        
        return MODEL_CATALOG.get(normalized, [])


class BaseLLMProvider:
    """Base class for LLM providers."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self._client = None
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._llm_logger = get_llm_logger(self.__class__.__name__)
        self._enable_detailed_logs = config.enable_detailed_logs
        http = self._llm_logger
    
    async def generate(self, prompt: str) -> str:
        """Generate response. Override in subclasses."""
        raise NotImplementedError
    
    async def _make_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP request to provider API."""
        import urllib.request
        import urllib.error
        import ssl
        
        llm = self._llm_logger
        http = self._llm_logger
        
        url = f"{self.config.base_url}{endpoint}"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}"
        }
        headers.update(self.config.extra_headers)
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        
        context = ssl.create_default_context()
        
        provider_class = self.__class__.__name__
        try:
            # 汇总日志（INFO级别）
            llm.info(f"_make_request() 发送请求到 {self.config.provider} API...")
            # 详细日志（DEBUG级别）
            llm.debug(f"   → 调用: urllib.request.urlopen()")
            llm.debug(f"请求 URL: {url}")
            llm.debug(f"🤖 [LLM层] ┌─ LLM 请求:")
            llm.debug(f"🤖 [LLM层] │  Model: {payload.get('model', 'N/A')}")
            llm.debug(f"🤖 [LLM层] │  Temperature: {payload.get('temperature', 'N/A')}")
            if 'messages' in payload:
                llm.debug(f"🤖 [LLM层] │  Messages ({len(payload['messages'])}):")
                for i, msg in enumerate(payload['messages']):
                    role = msg.get('role', 'unknown')
                    content = msg.get('content', '')[:100]
                    ellipsis = "..." if len(msg.get('content', '')) > 100 else ""
                    llm.debug(f"🤖 [LLM层] │    [{i}][{role}]: {content}{ellipsis}")
            elif 'prompt' in payload:
                prompt_text = payload['prompt'][:200]
                llm.debug(f"🤖 [LLM层] │  Prompt: {prompt_text}...")
            
            with urllib.request.urlopen(req, timeout=self.config.timeout, context=context) as response:
                # 汇总日志（INFO级别）
                llm.info(f"请求成功 (状态码: {response.status})")
                # 详细日志（DEBUG级别）
                llm.debug(f"收到响应")
                result = json.loads(response.read().decode('utf-8'))
                
                # 打印响应内容
                llm.debug(f"🤖 [LLM层] ├─ 响应状态: {response.status}")
                if 'choices' in result:
                    choice = result['choices'][0]
                    content = choice.get('message', {}).get('content', '')
                    if content:
                        llm.debug(f"🤖 [LLM层] ├─ 内容摘要: {content[:200]}...")
                    llm.debug(f"🤖 [LLM层] └─ 完整响应已接收")
                elif 'content' in result:
                    content = result.get('content', [])
                    if isinstance(content, list) and len(content) > 0:
                        text = content[0].get('text', '')
                        llm.debug(f"🤖 [LLM层] ├─ 内容摘要: {text[:200]}...")
                    llm.debug(f"🤖 [LLM层] └─ 完整响应已接收")
                
                return result
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else "{}"
            llm.error(f"HTTP 请求失败: {e.code} - {error_body}")
            llm.error(f"HTTP 错误: {e.code}")
            raise LLMAPIError(f"API request failed: {e.code} - {error_body}", e.code)
        except urllib.error.URLError as e:
            llm.error(f"网络错误: {str(e)}")
            llm.error(f"网络连接失败")
            raise LLMAPIError(f"Network error: {str(e)}", 0)


class OpenAICompatibleProvider(BaseLLMProvider):
    """Provider for OpenAI-compatible APIs."""
    
    async def generate(self, prompt: str, messages: Optional[List] = None) -> str:
        """Generate response using OpenAI-compatible API."""
        payload = {
            "model": self.config.model,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens
        }
        
        # Use provided messages or create a single user message
        if messages:
            # Convert messages to dict format if they are objects
            formatted_messages = []
            for msg in messages:
                if isinstance(msg, dict):
                    formatted_messages.append(msg)
                else:
                    # Handle Message objects
                    role = getattr(msg, 'role', 'user')
                    content = getattr(msg, 'content', '')
                    formatted_messages.append({"role": role, "content": content})
            payload["messages"] = formatted_messages
        else:
            payload["messages"] = [{"role": "user", "content": prompt}]
        
        response = await self._make_request("/chat/completions", payload)
        
        # Extract content from response
        # Handle different response formats:
        # 1. Standard OpenAI format: message.content
        # 2. DeepSeek v4 format: message.reasoning_content (content may be empty)
        message = response["choices"][0]["message"]
        content = message.get("content", "").strip()
        
        # If content is empty but reasoning_content exists (DeepSeek v4), use that
        if not content and "reasoning_content" in message:
            content = message["reasoning_content"].strip()
        
        return content


class AnthropicProvider(BaseLLMProvider):
    """Provider for Anthropic Claude API."""
    
    async def generate(self, prompt: str) -> str:
        """Generate response using Anthropic API."""
        payload = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        response = await self._make_request("/messages", payload)
        return response["content"][0]["text"]


class GoogleProvider(BaseLLMProvider):
    """Provider for Google Gemini API."""
    
    async def generate(self, prompt: str) -> str:
        """Generate response using Google Gemini API."""
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": self.config.temperature,
                "maxOutputTokens": self.config.max_tokens
            }
        }
        
        response = await self._make_request(f"/models/{self.config.model}:generateContent", payload)
        return response["candidates"][0]["content"]["parts"][0]["text"]


class MiniMaxProvider(BaseLLMProvider):
    """Provider for MiniMax API."""
    
    async def generate(self, prompt: str) -> str:
        """Generate response using MiniMax API."""
        payload = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens
        }
        
        response = await self._make_request("/chat/completions", payload)
        return response["choices"][0]["message"]["content"]


class CustomProvider(BaseLLMProvider):
    """Provider for custom OpenAI-compatible endpoints."""
    
    async def generate(self, prompt: str) -> str:
        """Generate response using custom API."""
        payload = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens
        }
        
        response = await self._make_request("/chat/completions", payload)
        
        # Handle various response formats
        message = response["choices"][0]["message"]
        content = message.get("content", "").strip()
        
        # Handle DeepSeek v4 format
        if not content and "reasoning_content" in message:
            content = message["reasoning_content"].strip()
        
        return content


class LLMAPIError(Exception):
    """Exception for LLM API errors."""
    
    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code


def setup_llm_integration(config: LLMConfig) -> BaseLLMProvider:
    """Setup LLM integration based on provider type."""
    provider_type = ProviderRegistry.get_provider_type(config.provider)
    
    # Set default base_url if not provided
    if not config.base_url:
        provider_entry = ProviderRegistry.get_provider(config.provider)
        if provider_entry and provider_entry.base_url:
            config.base_url = provider_entry.base_url
    
    if provider_type == LLMProviderType.ANTHROPIC:
        return AnthropicProvider(config)
    elif provider_type == LLMProviderType.GOOGLE:
        return GoogleProvider(config)
    elif provider_type == LLMProviderType.MINIMAX:
        return MiniMaxProvider(config)
    else:
        return OpenAICompatibleProvider(config)


def get_all_providers() -> List[Dict[str, Any]]:
    """Get all available providers with their information."""
    return [
        {
            "id": p.slug,
            "name": p.label,
            "description": p.description,
            "base_url": p.base_url,
            "default_model": p.default_model,
            "env_vars": p.api_key_env_vars
        }
        for p in PROVIDERS
    ]


def get_provider_models(provider_id: str) -> List[Dict[str, Any]]:
    """Get available models for a provider."""
    models = ProviderRegistry.get_models(provider_id)
    return [
        {
            "id": m.id,
            "name": m.name,
            "description": m.description,
            "context_length": m.context_length,
            "supports_functions": m.supports_functions,
            "input_cost_per_1m": m.input_cost_per_1m,
            "output_cost_per_1m": m.output_cost_per_1m,
            "recommended": m.recommended,
            "free": m.free
        }
        for m in models
    ]
