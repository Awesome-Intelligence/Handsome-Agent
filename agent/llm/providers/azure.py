"""
Azure OpenAI Provider 实现
🧠 Decision - 🤖 LLM - Azure OpenAI 系列模型支持
"""

import httpx
import json
import time
from typing import Optional, List, Dict, Any, AsyncIterator
from .base import BaseProvider, ProviderConfig, ProviderResponse, StreamChunk, Message
from common.logging_manager import get_llm_logger


class AzureProvider(BaseProvider):
    """Azure OpenAI LLM Provider

    支持 Azure OpenAI Service 上的 GPT 模型
    """

    provider_name = "azure"
    provider_display_name = "Azure OpenAI"
    supported_models = [
        "gpt-35-turbo",
        "gpt-4",
        "gpt-4-turbo",
        "gpt-4o",
    ]

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        # Azure 需要特定格式的 base_url
        # 例如: https://{resource}.openai.azure.com/openai/deployments/{deployment}
        self.base_url = config.base_url.rstrip("/") if config.base_url else ""
        self.api_key = config.api_key
        self._client: Optional[httpx.AsyncClient] = None
        self.logger = get_llm_logger(self.__class__.__name__)

    async def _get_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "api-key": self.api_key,
                    "Content-Type": "application/json",
                },
                timeout=self.config.timeout,
            )
        return self._client

    async def close(self) -> None:
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def generate(
        self,
        prompt: str,
        messages: Optional[List[Message]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> ProviderResponse:
        """生成文本响应"""
        start_time = time.time()

        self._log_request_started()

        system, msg_list = self._build_messages(prompt, messages, system_prompt)
        if system:
            msg_list.insert(0, {"role": "system", "content": system})

        self._log_input_messages(msg_list)

        request_body = {
            "messages": msg_list,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "top_p": kwargs.get("top_p", self.config.top_p),
            "stream": False,
        }

        try:
            client = await self._get_client()
            response = await client.post(f"/chat/completions?api-version=2024-02-01", json=request_body)

            if response.status_code != 200:
                self.logger.error(f"Azure API error - status: {response.status_code}")
                raise Exception(f"Azure API error: {response.status_code}")

            data = response.json()
            latency_ms = (time.time() - start_time) * 1000

            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})

            self.logger.info(f"Azure request completed - latency: {latency_ms:.2f}ms")

            return ProviderResponse(
                content=content,
                model=data.get("model", self.config.model),
                finish_reason=data["choices"][0].get("finish_reason", "stop"),
                usage=usage,
                latency_ms=latency_ms,
            )

        except httpx.HTTPError as e:
            self.logger.error(f"Azure request failed - {e}")
            raise Exception(f"Failed to call Azure API: {e}")

    async def generate_stream(
        self,
        prompt: str,
        messages: Optional[List[Message]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[StreamChunk]:
        """生成流式响应"""
        start_time = time.time()

        self._log_request_started()

        system, msg_list = self._build_messages(prompt, messages, system_prompt)
        if system:
            msg_list.insert(0, {"role": "system", "content": system})

        self._log_input_messages(msg_list)

        request_body = {
            "messages": msg_list,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "stream": True,
        }

        try:
            client = await self._get_client()
            async with client.stream("POST", f"/chat/completions?api-version=2024-02-01", json=request_body) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise Exception(f"Azure API error: {response.status_code}")

                accumulated_content = ""
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            yield StreamChunk(finish=True)
                            break

                        try:
                            data = json.loads(data_str)
                            delta = data["choices"][0]["delta"].get("content", "")
                            accumulated_content += delta

                            yield StreamChunk(
                                content=accumulated_content,
                                delta=delta,
                                finish=False,
                            )
                        except json.JSONDecodeError:
                            continue

                latency_ms = (time.time() - start_time) * 1000
                self._log_request_completed(latency_ms)

        except Exception as e:
            self.logger.error(f"Azure streaming failed - {e}")
            yield StreamChunk(content=f"Error: {e}", finish=True)

    async def count_tokens(self, text: str) -> int:
        """估算 token 数量"""
        return self._estimate_tokens(text)
