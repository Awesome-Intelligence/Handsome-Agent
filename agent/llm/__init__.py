"""
LLM 模块
🧠 Decision - 🤖 LLM - LLM 提供商管理
"""

from .base import LLMConfig, Message, LLMResponse, StreamChunk, BaseLLMProvider
from .factory import LLMFactory
from .providers import (
    BaseProvider,
    ProviderConfig,
    ProviderResponse,
    OpenAIProvider,
    ClaudeProvider,
    DeepSeekProvider,
    GeminiProvider,
    KimiProvider,
    AzureProvider,
)

__all__ = [
    # 基类
    "BaseLLMProvider",
    "BaseProvider",
    "LLMConfig",
    "ProviderConfig",
    "Message",
    "LLMResponse",
    "ProviderResponse",
    "StreamChunk",
    # 工厂
    "LLMFactory",
    # Providers
    "OpenAIProvider",
    "ClaudeProvider",
    "DeepSeekProvider",
    "GeminiProvider",
    "KimiProvider",
    "AzureProvider",
]


def get_all_providers() -> list[dict]:
    """获取所有 Provider 信息"""
    return LLMFactory.list_all_providers_info()
