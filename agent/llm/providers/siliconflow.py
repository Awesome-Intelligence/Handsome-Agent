"""
SiliconFlow Provider 实现
🧠 Decision - 🤖 LLM - SiliconFlow 聚合API
"""

from typing import Optional, List
from .base import BaseProvider, ProviderConfig, ProviderResponse, Message


class SiliconFlowProvider(BaseProvider):
    """SiliconFlow LLM Provider

    支持 SiliconFlow 聚合API服务
    """

    provider_name = "siliconflow"
    provider_display_name = "SiliconFlow"
    supported_models = [
        "Qwen/Qwen2.5-72B-Instruct",
        "deepseek-ai/DeepSeek-V3",
        "deepseek-ai/DeepSeek-R1",
        "anthropic/claude-3.5-sonnet",
        "anthropic/claude-3-opus",
        "google/gemini-2.0-flash",
        "meta-llama/Llama-3.3-70B-Instruct",
    ]
    default_model = "Qwen/Qwen2.5-72B-Instruct"

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.base_url = config.base_url or "https://api.siliconflow.cn/v1"

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