#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-Provider LLM Integration Module

Provides unified interface for integrating with 25+ LLM providers.
Supports OpenAI-compatible APIs and custom provider implementations.

Supported Providers (API endpoints verified based on Hermes and official docs):
- OpenAI: GPT-4o, GPT-4 Turbo, GPT-3.5
- Anthropic: Claude 3.5 Sonnet, Opus, Haiku
- Google: Gemini 1.5 Pro, Flash, 2.0
- DeepSeek: DeepSeek V3, Chat, Coder
- MiniMax: MiniMax-Text-01, Abab series
- Moonshot Kimi: moonshot-v1-8k/32k/128k
- SiliconFlow: Qwen, DeepSeek, Llama series
- StepFun: step-1, step-2, step-3 series
- Zhipu AI: GLM-4, GLM-4V
- DashScope: Qwen series
- And more via OpenAI-compatible API

Author: Handsome Agent Team
Version: 1.0.0
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

from core.layer_logger import get_layer_logger


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


class ProviderRegistry:
    """Registry for LLM providers with automatic provider detection."""
    _providers: Dict[str, Dict[str, Any]] = {}
    _initialized = False
    
    @classmethod
    def get_provider_type(cls, provider_id: str) -> LLMProviderType:
        """Determine provider type from ID."""
        provider_lower = provider_id.lower()
        
        if provider_lower in ['openai', 'groq', 'fireworks', 'together', 'mistral']:
            return LLMProviderType.OPENAI_COMPATIBLE
        elif provider_lower == 'anthropic':
            return LLMProviderType.ANTHROPIC
        elif provider_lower in ['google', 'gemini']:
            return LLMProviderType.GOOGLE
        elif provider_lower == 'cohere':
            return LLMProviderType.COHERE
        elif provider_lower == 'minimax':
            return LLMProviderType.MINIMAX
        else:
            return LLMProviderType.OPENAI_COMPATIBLE


class BaseLLMProvider:
    """Base class for LLM providers."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self._client = None
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._llm_logger = get_layer_logger("llm", self.__class__.__name__)
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
            llm.info(f"_make_request() 发送请求到 {self.config.provider} API...")
            llm.info(f"   → 调用: urllib.request.urlopen()")
            llm.debug(f"请求 URL: {url}")
            with urllib.request.urlopen(req, timeout=self.config.timeout, context=context) as response:
                llm.info(f"请求成功 (状态码: {response.status})")
                llm.info(f"收到响应")
                return json.loads(response.read().decode('utf-8'))
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
    
    async def generate(self, prompt: str) -> str:
        """Generate response using OpenAI-compatible API."""
        payload = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens
        }
        
        response = await self._make_request("/chat/completions", payload)
        return response["choices"][0]["message"]["content"]


class AnthropicProvider(BaseLLMProvider):
    """Provider for Anthropic Claude APIs."""
    
    async def generate(self, prompt: str) -> str:
        """Generate response using Anthropic API."""
        import urllib.request
        import json
        
        url = "https://api.anthropic.com/v1/messages"
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
            "anthropic-dangerous-direct-browser-access": "true"
        }
        
        payload = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens
        }
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        
        with urllib.request.urlopen(req, timeout=self.config.timeout) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result["content"][0]["text"]


class GoogleProvider(BaseLLMProvider):
    """Provider for Google Gemini APIs."""
    
    async def generate(self, prompt: str) -> str:
        """Generate response using Google Gemini API."""
        import urllib.request
        import json
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.config.model}:generateContent"
        url += f"?key={self.config.api_key}"
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": self.config.temperature,
                "maxOutputTokens": self.config.max_tokens
            }
        }
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method='POST')
        
        with urllib.request.urlopen(req, timeout=self.config.timeout) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result["candidates"][0]["content"]["parts"][0]["text"]


class MiniMaxProvider(BaseLLMProvider):
    """Provider for MiniMax APIs."""
    
    async def generate(self, prompt: str) -> str:
        """Generate response using MiniMax API."""
        import urllib.request
        import json
        
        # MiniMax API endpoint
        url = "https://api.minimaxi.com/v1/text/chatcompletion_v2"
        
        payload = {
            "model": self.config.model or "MiniMax-M2.5",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}"
        }
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        
        with urllib.request.urlopen(req, timeout=self.config.timeout) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result["choices"][0]["message"]["content"]


class LLMAPIError(Exception):
    """Exception for LLM API errors."""
    
    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code


def get_provider(config: LLMConfig) -> Optional[BaseLLMProvider]:
    """Get appropriate provider instance based on configuration."""
    if not config.is_enabled():
        return None
    
    provider_type = ProviderRegistry.get_provider_type(config.provider)
    
    if provider_type == LLMProviderType.ANTHROPIC:
        return AnthropicProvider(config)
    elif provider_type == LLMProviderType.GOOGLE:
        return GoogleProvider(config)
    elif provider_type == LLMProviderType.MINIMAX:
        return MiniMaxProvider(config)
    else:
        return OpenAICompatibleProvider(config)


def setup_llm_integration(config: LLMConfig) -> Optional[BaseLLMProvider]:
    """Set up LLM integration based on configuration."""
    if not config.is_enabled():
        return None
    
    try:
        return get_provider(config)
    except Exception as e:
        print(f"Warning: Failed to initialize LLM provider: {e}")
        return None


def fetch_models_from_api(provider: str, api_key: str, base_url: str = None) -> List[ModelInfo]:
    """Fetch available models from provider's API.
    
    Args:
        provider: Provider ID (e.g., 'minimax', 'moonshot')
        api_key: API key for authentication
        base_url: Custom base URL if not using default
        
    Returns:
        List of ModelInfo objects from the API
    """
    if not api_key:
        return []
    
    provider_info = next((p for p in get_all_providers() if p["id"] == provider), None)
    if not provider_info:
        return []
    
    url = base_url or provider_info.get("base_url")
    if not url:
        return []
    
    try:
        import urllib.request
        import json
        import ssl
        
        if provider == "minimax":
            list_url = f"{url}/text/modelslist"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
        else:
            list_url = f"{url}/models"
            headers = {
                "Authorization": f"Bearer {api_key}"
            }
        
        req = urllib.request.Request(list_url, headers=headers, method='GET')
        context = ssl.create_default_context()
        
        with urllib.request.urlopen(req, timeout=10, context=context) as response:
            result = json.loads(response.read().decode('utf-8'))
            
            models = []
            if provider == "minimax" and "data" in result:
                for m in result.get("data", []):
                    models.append(ModelInfo(
                        id=m.get("id", ""),
                        name=m.get("id", ""),
                        description=f"API获取的模型",
                        context_length=m.get("context_length", 32000)
                    ))
            elif "data" in result:
                for m in result.get("data", []):
                    models.append(ModelInfo(
                        id=m.get("id", ""),
                        name=m.get("id", ""),
                        description=m.get("created", ""),
                        context_length=m.get("context_window", 32000)
                    ))
            
            return models
    except Exception as e:
        print(f"Warning: Failed to fetch models from {provider}: {e}")
        return []


def get_default_config() -> LLMConfig:
    """Get default LLM configuration from environment variables."""
    api_key = None
    provider = "none"
    base_url = None
    
    env_mappings = {
        "OPENAI_API_KEY": ("openai", "https://api.openai.com/v1"),
        "ANTHROPIC_API_KEY": ("anthropic", None),
        "GOOGLE_API_KEY": ("google", "https://generativelanguage.googleapis.com/v1beta"),
        "DEEPSEEK_API_KEY": ("deepseek", "https://api.deepseek.com/v1"),
        "MINIMAX_API_KEY": ("minimax", "https://api.minimaxi.com/v1"),
        "KIMI_API_KEY": ("moonshot", "https://api.moonshot.cn/v1"),
        "KIMI_CN_API_KEY": ("moonshot", "https://api.moonshot.cn/v1"),
        "SILICONFLOW_API_KEY": ("siliconflow", "https://api.siliconflow.cn/v1"),
        "STEP_API_KEY": ("leapai", "https://api.stepfun.com/v1"),
        "GLM_API_KEY": ("zhipu", "https://open.bigmodel.cn/api/paas/v4"),
        "DASHSCOPE_API_KEY": ("dashscope", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        "GROQ_API_KEY": ("groq", "https://api.groq.com/openai/v1"),
        "TOGETHER_API_KEY": ("together", "https://api.together.xyz/v1"),
        "FIREWORKS_API_KEY": ("fireworks", "https://api.fireworks.ai/inference/v1"),
        "COHERE_API_KEY": ("cohere", "https://api.cohere.ai/v1"),
        "MISTRAL_API_KEY": ("mistral", "https://api.mistral.ai/v1"),
        "NOVITA_API_KEY": ("novita", "https://api.novita.ai/v3"),
        "HYPERBOLIC_API_KEY": ("hyperbolic", "https://api.hyperbolic.xyz/v1"),
    }
    
    for env_var, (prov, url) in env_mappings.items():
        if os.environ.get(env_var):
            api_key = os.environ[env_var]
            provider = prov
            base_url = url
            break
    
    return LLMConfig(provider=provider, api_key=api_key, base_url=base_url)


PROVIDER_MODELS = {
    "openai": [
        ModelInfo("gpt-4o", "GPT-4o", "最强能力，多模态", 128000, True, 5.0, 15.0),
        ModelInfo("gpt-4o-mini", "GPT-4o Mini", "轻量快速", 128000, True, 0.15, 0.6),
        ModelInfo("gpt-4-turbo", "GPT-4 Turbo", "快速强能力", 128000, True, 10.0, 30.0),
        ModelInfo("gpt-4", "GPT-4", "强推理", 8192, True, 30.0, 60.0),
        ModelInfo("gpt-3.5-turbo", "GPT-3.5 Turbo", "快速经济", 16385, True, 0.5, 1.5),
    ],
    "anthropic": [
        ModelInfo("claude-3-5-sonnet-latest", "Claude 3.5 Sonnet", "最佳平衡", 200000, True, 3.0, 15.0),
        ModelInfo("claude-3-opus", "Claude 3 Opus", "最强能力", 200000, True, 15.0, 75.0),
        ModelInfo("claude-3-sonnet", "Claude 3 Sonnet", "平衡型", 200000, True, 3.0, 15.0),
        ModelInfo("claude-3-haiku", "Claude 3 Haiku", "快速实惠", 200000, True, 0.25, 1.25),
    ],
    "google": [
        ModelInfo("gemini-2.0-flash", "Gemini 2.0 Flash", "最新快速", 1000000, True, 0.0, 0.0),
        ModelInfo("gemini-1.5-pro", "Gemini 1.5 Pro", "超长上下文", 1000000, True, 1.25, 5.0),
        ModelInfo("gemini-1.5-flash", "Gemini 1.5 Flash", "快速", 1000000, True, 0.0, 0.0),
    ],
    "deepseek": [
        ModelInfo("deepseek-v3", "DeepSeek V3", "最新最强", 64000, True, 0.0, 0.0),
        ModelInfo("deepseek-chat", "DeepSeek Chat", "平衡型", 64000, True, 0.1, 0.3),
        ModelInfo("deepseek-coder", "DeepSeek Coder", "代码专用", 64000, True, 0.1, 0.3),
    ],
    "minimax": [
        ModelInfo("MiniMax-M2", "MiniMax-M2", "Agent工作流和代码", 128000, True, 0.5, 1.5),
        ModelInfo("MiniMax-M2.1", "MiniMax-M2.1", "多语言开发和原生应用", 128000, True, 0.5, 1.5),
        ModelInfo("MiniMax-M2.5", "MiniMax-M2.5", "复杂Agent任务", 200000, True, 0.5, 1.5),
        ModelInfo("MiniMax-Text-01", "MiniMax-Text-01", "超长上下文开源模型", 1000000, True, 0.2, 1.1),
    ],
    "moonshot": [
        ModelInfo("moonshot-v1-128k", "Kimi 128K", "超长上下文", 128000, True, 0.0, 0.0),
        ModelInfo("moonshot-v1-32k", "Kimi 32K", "长上下文", 32000, True, 0.0, 0.0),
        ModelInfo("moonshot-v1-8k", "Kimi 8K", "标准上下文", 8000, True, 0.0, 0.0),
    ],
    "siliconflow": [
        ModelInfo("deepseek-ai/DeepSeek-V3", "DeepSeek V3", "高性价比", 64000, True, 0.0, 0.0),
        ModelInfo("Qwen/Qwen2.5-72B-Instruct", "Qwen2.5 72B", "大参数开源", 32768, True, 0.0, 0.0),
        ModelInfo("deepseek-ai/DeepSeek-V2.5", "DeepSeek V2.5", "高性价比", 32768, True, 0.0, 0.0),
    ],
    "novita": [
        ModelInfo("meta-llama/Llama-3.3-70B-Instruct", "Llama 3.3 70B", "最强开源", 128000, True, 0.0, 0.0),
        ModelInfo("deepseek-ai/DeepSeek-V2.5", "DeepSeek V2.5", "高性价比", 128000, True, 0.0, 0.0),
    ],
    "hyperbolic": [
        ModelInfo("meta-llama/Llama-3.3-70B-Instruct", "Llama 3.3 70B", "最强开源", 128000, True, 0.0, 0.0),
        ModelInfo("mistralai/Mistral-7B-Instruct-v0.3", "Mistral 7B", "轻量开源", 32768, True, 0.0, 0.0),
    ],
    "leapai": [
        ModelInfo("step-3", "Step-3", "最新强能力", 32000, True, 0.0, 0.0),
        ModelInfo("step-2-16k", "Step-2 16K", "强能力", 16000, True, 0.0, 0.0),
        ModelInfo("step-1.5v-8k", "Step-1.5V 8K", "多模态", 8000, True, 0.0, 0.0),
        ModelInfo("step-1v-8k", "Step-1V 8K", "标准", 8000, True, 0.0, 0.0),
    ],
    "yi": [
        ModelInfo("yi-large", "Yi Large", "最强能力", 16000, True, 0.0, 0.0),
        ModelInfo("yi-medium", "Yi Medium", "平衡型", 32000, True, 0.0, 0.0),
    ],
    "mistral": [
        ModelInfo("mistral-large", "Mistral Large", "最强能力", 128000, True, 2.0, 6.0),
        ModelInfo("mistral-small", "Mistral Small", "快速经济", 32000, True, 0.1, 0.3),
    ],
    "cohere": [
        ModelInfo("command-r-plus", "Command R+", "最强能力", 128000, True, 3.0, 15.0),
        ModelInfo("command-r", "Command R", "平衡型", 128000, True, 0.5, 1.5),
    ],
    "groq": [
        ModelInfo("llama-3.1-70b-versatile", "Llama 3.1 70B", "免费高速", 8192, True, 0.0, 0.0),
        ModelInfo("llama-3.1-8b-instant", "Llama 3.1 8B", "免费轻量", 8192, True, 0.0, 0.0),
        ModelInfo("mixtral-8x7b-32768", "Mixtral 8x7B", "免费MoE", 32768, True, 0.0, 0.0),
    ],
    "fireworks": [
        ModelInfo("fireworks-llama-v3-70b-instruct", "Llama 3 70B", "高质量", 8192, True, 0.0, 0.0),
        ModelInfo("fireworks-llama-v3-8b-instruct", "Llama 3 8B", "快速", 8192, True, 0.0, 0.0),
    ],
    "together": [
        ModelInfo("meta-llama/Llama-3-70b-chat-hf", "Llama 3 70B", "高质量开源", 8192, True, 0.0, 0.0),
        ModelInfo("deepseek-ai/DeepSeek-V2.5", "DeepSeek V2.5", "高性价比", 32768, True, 0.0, 0.0),
    ],
    "zhipu": [
        ModelInfo("glm-4", "GLM-4", "最强能力", 128000, True, 1.0, 1.0),
        ModelInfo("glm-4-flash", "GLM-4 Flash", "快速", 128000, True, 0.0, 0.0),
        ModelInfo("glm-3-turbo", "GLM-3 Turbo", "经济实惠", 128000, True, 0.0, 0.0),
    ],
    "dashscope": [
        ModelInfo("qwen-max", "Qwen Max", "最强能力", 128000, True, 20.0, 60.0),
        ModelInfo("qwen-plus", "Qwen Plus", "平衡型", 128000, True, 2.0, 8.0),
        ModelInfo("qwen-turbo", "Qwen Turbo", "快速经济", 128000, True, 0.5, 1.5),
    ],
    "perplexity": [
        ModelInfo("sonar", "Sonar", "搜索增强", 128000, True, 0.0, 0.0),
        ModelInfo("sonar-pro", "Sonar Pro", "搜索增强专业版", 128000, True, 0.0, 0.0),
    ],
}


def get_provider_models(provider: str) -> List[ModelInfo]:
    """Get available models for a provider."""
    return PROVIDER_MODELS.get(provider, [])


def get_all_providers() -> List[Dict[str, Any]]:
    """Get all supported providers with their metadata (verified API endpoints based on Hermes and official docs)."""
    return [
        {
            "id": "openai",
            "name": "OpenAI",
            "description": "GPT-4o, GPT-4 Turbo, GPT-3.5",
            "website": "https://platform.openai.com",
            "api_key_url": "https://platform.openai.com/api-keys",
            "requires_api_key": True,
            "default_model": "gpt-4o",
            "base_url": "https://api.openai.com/v1",
        },
        {
            "id": "anthropic",
            "name": "Anthropic Claude",
            "description": "Claude 3.5 Sonnet, Opus, Haiku",
            "website": "https://anthropic.com",
            "api_key_url": "https://console.anthropic.com/",
            "requires_api_key": True,
            "default_model": "claude-3-5-sonnet-latest",
            "base_url": None,
        },
        {
            "id": "google",
            "name": "Google Gemini",
            "description": "Gemini 2.0, 1.5 Pro, Flash",
            "website": "https://ai.google.dev",
            "api_key_url": "https://makersuite.google.com/app/apikey",
            "requires_api_key": True,
            "default_model": "gemini-2.0-flash",
            "base_url": "https://generativelanguage.googleapis.com/v1beta",
        },
        {
            "id": "deepseek",
            "name": "DeepSeek",
            "description": "DeepSeek V3, Chat, Coder (性价比之王)",
            "website": "https://platform.deepseek.com",
            "api_key_url": "https://platform.deepseek.com/api_keys",
            "requires_api_key": True,
            "default_model": "deepseek-v3",
            "base_url": "https://api.deepseek.com/v1",
        },
        {
            "id": "minimax",
            "name": "MiniMax 大模型",
            "description": "MiniMax-Text-01, Abab (国产高性能)",
            "website": "https://www.minimax.io",
            "api_key_url": "https://platform.minimaxi.com/apiKeys",
            "requires_api_key": True,
            "default_model": "MiniMax-Text-01",
            "base_url": "https://api.minimaxi.com/anthropic",
        },
        {
            "id": "moonshot",
            "name": "Moonshot Kimi",
            "description": "Kimi Chat (超长上下文128K/256K)",
            "website": "https://platform.moonshot.cn",
            "api_key_url": "https://platform.moonshot.cn/console/api-keys",
            "requires_api_key": True,
            "default_model": "moonshot-v1-128k",
            "base_url": "https://api.moonshot.cn/v1",
        },
        {
            "id": "siliconflow",
            "name": "SiliconFlow (SiliconCloud)",
            "description": "聚合多种开源模型 (DeepSeek, Qwen, Llama)",
            "website": "https://www.siliconflow.cn",
            "api_key_url": "https://www.siliconflow.cn/api-keys",
            "requires_api_key": True,
            "default_model": "deepseek-ai/DeepSeek-V3",
            "base_url": "https://api.siliconflow.cn/v1",
        },
        {
            "id": "novita",
            "name": "Novita AI",
            "description": "Llama, Qwen, DeepSeek 等开源模型",
            "website": "https://novita.ai",
            "api_key_url": "https://console.novita.ai/api-keys",
            "requires_api_key": True,
            "default_model": "meta-llama/Llama-3.3-70B-Instruct",
            "base_url": "https://api.novita.ai/v3",
        },
        {
            "id": "hyperbolic",
            "name": "Hyperbolic",
            "description": "高性价比开源模型 (Llama, Mistral)",
            "website": "https://app.hyperbolic.xyz",
            "api_key_url": "https://app.hyperbolic.xyz/settings/api-keys",
            "requires_api_key": True,
            "default_model": "meta-llama/Llama-3.3-70B-Instruct",
            "base_url": "https://api.hyperbolic.xyz/v1",
        },
        {
            "id": "leapai",
            "name": "阶跃星辰 StepFun",
            "description": "Step-1/2/3 系列 (国产)",
            "website": "https://platform.stepfun.com",
            "api_key_url": "https://platform.stepfun.com/interface-key",
            "requires_api_key": True,
            "default_model": "step-3",
            "base_url": "https://api.stepfun.com/v1",
        },
        {
            "id": "yi",
            "name": "零一万物 Yi",
            "description": "Yi Large, Medium (国产)",
            "website": "https://www.lingyiwanwu.cn",
            "api_key_url": "https://platform.lingyiwanwu.com",
            "requires_api_key": True,
            "default_model": "yi-large",
            "base_url": "https://api.lingyiwanwu.com/v1",
        },
        {
            "id": "mistral",
            "name": "Mistral AI",
            "description": "Mistral Large, Small (欧洲之光)",
            "website": "https://mistral.ai",
            "api_key_url": "https://console.mistral.ai/api-keys/",
            "requires_api_key": True,
            "default_model": "mistral-large",
            "base_url": "https://api.mistral.ai/v1",
        },
        {
            "id": "cohere",
            "name": "Cohere",
            "description": "Command R+, Command R (长上下文)",
            "website": "https://cohere.com",
            "api_key_url": "https://dashboard.cohere.com/api-keys",
            "requires_api_key": True,
            "default_model": "command-r-plus",
            "base_url": "https://api.cohere.ai/v1",
        },
        {
            "id": "groq",
            "name": "Groq",
            "description": "Llama 3.1, Mixtral (免费高速)",
            "website": "https://console.groq.com",
            "api_key_url": "https://console.groq.com/keys",
            "requires_api_key": True,
            "default_model": "llama-3.1-70b-versatile",
            "base_url": "https://api.groq.com/openai/v1",
        },
        {
            "id": "fireworks",
            "name": "Fireworks AI",
            "description": "Llama 3, Mixtral (高质量)",
            "website": "https://fireworks.ai",
            "api_key_url": "https://fireworks.ai/settings/api-keys",
            "requires_api_key": True,
            "default_model": "fireworks-llama-v3-70b-instruct",
            "base_url": "https://api.fireworks.ai/inference/v1",
        },
        {
            "id": "together",
            "name": "Together AI",
            "description": "开源模型集合 (Llama, DeepSeek)",
            "website": "https://together.ai",
            "api_key_url": "https://api.together.xyz/settings/api-keys",
            "requires_api_key": True,
            "default_model": "meta-llama/Llama-3-70b-chat-hf",
            "base_url": "https://api.together.xyz/v1",
        },
        {
            "id": "zhipu",
            "name": "智谱AI (GLM)",
            "description": "GLM-4, GLM-4V (国产中文优化)",
            "website": "https://www.zhipuai.cn",
            "api_key_url": "https://open.bigmodel.cn/",
            "requires_api_key": True,
            "default_model": "glm-4",
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
        },
        {
            "id": "dashscope",
            "name": "阿里百炼 DashScope",
            "description": "通义千问全系列 (国产中文优化)",
            "website": "https://bailian.console.aliyun.com",
            "api_key_url": "https://dashscope.console.aliyun.com/api-key",
            "requires_api_key": True,
            "default_model": "qwen-turbo",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        },
        {
            "id": "perplexity",
            "name": "Perplexity",
            "description": "Sonar (搜索增强)",
            "website": "https://perplexity.ai",
            "api_key_url": "https://www.perplexity.ai/settings/api",
            "requires_api_key": True,
            "default_model": "sonar",
            "base_url": "https://api.perplexity.ai",
        },
        {
            "id": "azure",
            "name": "Azure OpenAI",
            "description": "企业级 GPT-4 (Azure云)",
            "website": "https://azure.microsoft.com/services/cognitive-services/openai/",
            "api_key_url": "https://portal.azure.com",
            "requires_api_key": True,
            "default_model": "gpt-4",
            "base_url": None,
        },
        {
            "id": "custom",
            "name": "自定义 (Custom)",
            "description": "OpenAI兼容API (Ollama, vLLM等本地模型)",
            "website": "https://platform.openai.com",
            "api_key_url": None,
            "requires_api_key": False,
            "default_model": "gpt-3.5-turbo",
            "base_url": "http://localhost:11434/v1",
        },
    ]