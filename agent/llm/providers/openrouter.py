"""
OpenRouter Provider 实现
🧠 Decision - 🤖 LLM - OpenRouter 聚合API
"""

from typing import Optional, List
from .base import BaseProvider, ProviderConfig, ProviderResponse, Message


class OpenRouterProvider(BaseProvider):
    """OpenRouter LLM Provider

    支持 OpenRouter 聚合API服务
    """

    provider_name = "openrouter"
    provider_display_name = "OpenRouter"
    supported_models = [
        "anthropic/claude-3.5-sonnet",
        "anthropic/claude-3-opus",
        "openai/gpt-4o",
        "openai/gpt-4o-mini",
        "google/gemini-2.0-flash",
        "google/gemini-1.5-pro",
        "deepseek-ai/deepseek-chat-v3",
        "meta-llama/llama-3.3-70b-instruct",
        "mistralai/mistral-7b-instruct",
    ]
    default_model = "anthropic/claude-3.5-sonnet"

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.base_url = config.base_url or "https://openrouter.ai/api/v1"

    async def generate(
        self,
        prompt: str,
        messages: Optional[List[Message]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> ProviderResponse:
        """生成文本响应"""
        system, msg_list = self._build_messages(prompt, messages, system_prompt)
        if system:
            msg_list.insert(0, {"role": "system", "content": system})

        request_body = {
            "model": self.config.model or self.default_model,
            "messages": msg_list,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
        }

        return await self._make_request(request_body)