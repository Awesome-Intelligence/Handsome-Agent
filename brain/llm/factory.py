"""
LLM Factory - LLM Provider 工厂
"""

from typing import Optional, Dict
from .base import BaseLLMProvider, LLMConfig
from .openai_provider import OpenAIProvider
from .claude_provider import ClaudeProvider


class LLMFactory:
    """LLM Provider 工厂"""
    
    _providers: Dict[str, type] = {
        "openai": OpenAIProvider,
        "gpt": OpenAIProvider,
        "claude": ClaudeProvider,
        "anthropic": ClaudeProvider,
    }
    
    _default_models: Dict[str, str] = {
        "openai": "gpt-4",
        "gpt": "gpt-4",
        "claude": "claude-3-sonnet",
        "anthropic": "claude-3-sonnet",
    }
    
    @classmethod
    def create(
        cls,
        provider: str,
        api_key: str,
        model: Optional[str] = None,
        **kwargs
    ) -> BaseLLMProvider:
        """
        创建 LLM Provider
        
        Args:
            provider: 提供商名称 (openai/gpt/claude/anthropic)
            api_key: API 密钥
            model: 模型名称（可选）
            **kwargs: 其他配置参数
            
        Returns:
            BaseLLMProvider: LLM Provider 实例
        """
        provider_lower = provider.lower()
        
        if provider_lower not in cls._providers:
            raise ValueError(
                f"Unknown provider: {provider}. "
                f"Available: {list(cls._providers.keys())}"
            )
        
        provider_class = cls._providers[provider_lower]
        
        config = LLMConfig(
            api_key=api_key,
            model=model or cls._default_models.get(provider_lower, "gpt-4"),
            **{k: v for k, v in kwargs.items() if k in LLMConfig.model_fields}
        )
        
        return provider_class(config)
    
    @classmethod
    def list_providers(cls) -> list[str]:
        """列出支持的提供商"""
        return list(cls._providers.keys())
    
    @classmethod
    def list_models(cls, provider: str) -> list[str]:
        """列出提供商支持的模型"""
        models = {
            "openai": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
            "claude": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
        }
        return models.get(provider.lower(), [])
    
    @classmethod
    def register_provider(cls, name: str, provider_class: type) -> None:
        """注册新的 Provider"""
        cls._providers[name.lower()] = provider_class