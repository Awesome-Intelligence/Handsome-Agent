"""
Dashscope Provider 实现
🧠 Decision - 🤖 LLM - 阿里通义千问
"""

from typing import Optional, List
from .base import BaseProvider, ProviderConfig, ProviderResponse, Message


class DashscopeProvider(BaseProvider):
    """Dashscope LLM Provider

    支持阿里云通义千问服务
    """

    provider_name = "dashscope"
    provider_display_name = "阿里通义千问"
    supported_models = [
        "qwen-plus",
        "qwen-plus-latest",
        "qwen-turbo",
        "qwen-max",
        "qwen2.5-72b-instruct",
        "qwen2.5-7b-instruct",
        "qwen2.5-3b-instruct",
        "qwq-32b",
        "qwen-coder-plus",
    ]
    default_model = "qwen-plus"

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.base_url = config.base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"

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