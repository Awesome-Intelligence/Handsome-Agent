"""
MiniMax Provider 实现
🧠 Decision - 🤖 LLM - MiniMax 海螺AI
"""

from typing import Optional, List
from .base import BaseProvider, ProviderConfig, ProviderResponse, Message


class MiniMaxProvider(BaseProvider):
    """MiniMax LLM Provider

    支持 MiniMax 海螺AI服务
    """

    provider_name = "minimax"
    provider_display_name = "MiniMax"
    supported_models = [
        "MiniMax-M2.7",
        "MiniMax-M2.5",
        "MiniMax-M2.1",
        "MiniMax-M2",
    ]
    default_model = "MiniMax-M2.7"

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.base_url = config.base_url or "https://api.minimax.chat/v"

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