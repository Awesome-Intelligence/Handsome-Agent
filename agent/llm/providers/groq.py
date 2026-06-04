"""
Groq Provider 实现
🧠 Decision - 🤖 LLM - Groq 快速推理服务
"""

from typing import Optional, List, Dict, Any
from .base import BaseProvider, ProviderConfig, ProviderResponse, Message


class GroqProvider(BaseProvider):
    """Groq LLM Provider

    支持 Groq 云端推理服务，高速低延迟
    """

    provider_name = "groq"
    provider_display_name = "Groq"
    supported_models = [
        "llama-3.3-70b-versatile",
        "llama-3.1-70b-versatile",
        "llama-3.2-90b-versatile",
        "llama-3.2-3b-preview",
        "mixtral-8x7b-32768",
        "gemma2-9b-it",
    ]
    default_model = "llama-3.3-70b-versatile"

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.base_url = config.base_url or "https://api.groq.com/openai/v1"

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