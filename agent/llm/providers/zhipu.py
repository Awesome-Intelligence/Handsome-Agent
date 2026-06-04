"""
Zhipu Provider 实现
🧠 Decision - 🤖 LLM - 智谱AI GLM
"""

from typing import Optional, List
from .base import BaseProvider, ProviderConfig, ProviderResponse, Message


class ZhipuProvider(BaseProvider):
    """Zhipu LLM Provider

    支持智谱AI GLM系列模型
    """

    provider_name = "zhipu"
    provider_display_name = "智谱AI (GLM)"
    supported_models = [
        "glm-4-plus",
        "glm-4-flash",
        "glm-4",
        "glm-4-long",
        "glm-3-turbo",
    ]
    default_model = "glm-4-flash"

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.base_url = config.base_url or "https://open.bigmodel.cn/api/paas/v4"

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