"""
LLM Factory - LLM Provider 工厂
🧠 Decision - 🤖 LLM - Provider 工厂类
"""

from typing import Optional, Dict, List, Type
from .providers.base import BaseProvider, ProviderConfig


class LLMFactory:
    """LLM Provider 工厂

    管理所有 Provider 类的注册和创建
    """

    # Provider 注册表
    _providers: Dict[str, Type[BaseProvider]] = {}

    # 默认模型映射
    _default_models: Dict[str, str] = {
        "openai": "gpt-4o-mini",
        "claude": "claude-3-5-sonnet",
        "deepseek": "deepseek-chat",
        "gemini": "gemini-1.5-flash",
        "kimi": "moonshot-v1-32k",
        "azure": "gpt-4o",
        "groq": "llama-3.3-70b-versatile",
        "minimax": "MiniMax-M3",
        "zhipu": "glm-4-flash",
        "dashscope": "qwen-plus",
        "siliconflow": "Qwen/Qwen2.5-72B-Instruct",
        "openrouter": "anthropic/claude-3.5-sonnet",
    }

    # 别名映射
    _aliases: Dict[str, str] = {
        "gpt": "openai",
        "anthropic": "claude",
        "nvidia": "openai",
        "custom": "openai",
        "kimi-cn": "kimi",
        "moonshot": "kimi",
        "aliyun": "dashscope",
        "qwen": "dashscope",
    }

    @classmethod
    def register(cls, name: str, provider_class: Type[BaseProvider]) -> None:
        """注册 Provider

        Args:
            name: Provider 名称
            provider_class: Provider 类
        """
        cls._providers[name.lower()] = provider_class

    @classmethod
    def create(
        cls,
        provider: str,
        api_key: str,
        model: Optional[str] = None,
        **kwargs
    ) -> BaseProvider:
        """创建 Provider 实例

        Args:
            provider: Provider 名称
            api_key: API 密钥
            model: 模型名称（可选）
            **kwargs: 其他配置参数

        Returns:
            BaseProvider: Provider 实例
        """
        provider_lower = provider.lower()

        # 处理别名
        if provider_lower in cls._aliases:
            provider_lower = cls._aliases[provider_lower]

        if provider_lower not in cls._providers:
            available = list(cls._providers.keys())
            raise ValueError(
                f"Unknown provider: {provider}. "
                f"Available: {available}"
            )

        provider_class = cls._providers[provider_lower]

        config = ProviderConfig(
            api_key=api_key,
            model=model or cls._default_models.get(provider_lower, "gpt-4"),
            **kwargs
        )

        return provider_class(config)

    @classmethod
    def list_providers(cls) -> List[str]:
        """列出所有注册的 Provider"""
        return list(cls._providers.keys())

    @classmethod
    def get_provider_info(cls, name: str) -> Optional[Dict[str, any]]:
        """获取 Provider 信息

        Args:
            name: Provider 名称

        Returns:
            Provider 信息字典
        """
        name_lower = name.lower()
        if name_lower in cls._aliases:
            name_lower = cls._aliases[name_lower]

        if name_lower not in cls._providers:
            return None

        provider_class = cls._providers[name_lower]
        return {
            "name": provider_class.provider_name,
            "display_name": provider_class.provider_display_name,
            "supported_models": provider_class.supported_models,
            "default_model": cls._default_models.get(name_lower, ""),
        }

    @classmethod
    def list_all_providers_info(cls) -> List[Dict[str, any]]:
        """列出所有 Provider 的信息"""
        result = []
        for name in cls._providers:
            info = cls.get_provider_info(name)
            if info:
                result.append(info)
        return result


# 自动注册所有 Provider
def _register_providers():
    """自动注册所有 Provider"""
    from .providers.openai import OpenAIProvider
    from .providers.claude import ClaudeProvider
    from .providers.deepseek import DeepSeekProvider
    from .providers.gemini import GeminiProvider
    from .providers.kimi import KimiProvider
    from .providers.azure import AzureProvider
    from .providers.groq import GroqProvider
    from .providers.minimax import MiniMaxProvider
    from .providers.zhipu import ZhipuProvider
    from .providers.dashscope import DashscopeProvider
    from .providers.siliconflow import SiliconFlowProvider
    from .providers.openrouter import OpenRouterProvider

    LLMFactory.register("openai", OpenAIProvider)
    LLMFactory.register("claude", ClaudeProvider)
    LLMFactory.register("deepseek", DeepSeekProvider)
    LLMFactory.register("gemini", GeminiProvider)
    LLMFactory.register("kimi", KimiProvider)
    LLMFactory.register("azure", AzureProvider)
    LLMFactory.register("groq", GroqProvider)
    LLMFactory.register("minimax", MiniMaxProvider)
    LLMFactory.register("zhipu", ZhipuProvider)
    LLMFactory.register("dashscope", DashscopeProvider)
    LLMFactory.register("siliconflow", SiliconFlowProvider)
    LLMFactory.register("openrouter", OpenRouterProvider)


# 自动注册
_register_providers()
