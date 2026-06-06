"""
MiniMax Provider 实现
🧠 Decision - 🤖 LLM - MiniMax 海螺AI
"""

import os
import httpx
import json
import time
from typing import Optional, List, AsyncIterator
from .base import BaseProvider, ProviderConfig, ProviderResponse, Message, StreamChunk
from common.logging_manager import get_llm_logger
from common.config import DEFAULT_LLM_BASE_URLS


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
        # 优先级: 配置 > 环境变量 > Provider默认URL
        self.base_url = (
            config.base_url
            or os.getenv("MINIMAX_BASE_URL")
            or DEFAULT_LLM_BASE_URLS.get("minimax")
        )
        self.api_key = config.api_key
        self._client: Optional[httpx.AsyncClient] = None
        self.logger = get_llm_logger(self.__class__.__name__)

    async def _get_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
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
        # 检查 API Key 是否配置
        if not self.api_key:
            raise Exception(
                "MiniMax API Key 未配置。请设置环境变量 MINIMAX_API_KEY 或在配置中指定。\n"
                "获取方式: https://platform.minimaxi.com/"
            )

        start_time = time.time()

        self._log_request_started()

        system, msg_list = self._build_messages(prompt, messages, system_prompt)
        if system:
            msg_list.insert(0, {"role": "system", "content": system})

        request_body = {
            "model": self.config.model or self.default_model,
            "messages": msg_list,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
        }

        try:
            client = await self._get_client()
            self._log_request_body(request_body)
            self._log_input_messages(msg_list)
            response = await client.post("/chat/completions", json=request_body)

            if response.status_code != 200:
                self.logger.error(f"MiniMax API error - status: {response.status_code}")
                if response.status_code == 401:
                    raise Exception(
                        "MiniMax API Key 无效或已过期。请检查环境变量 MINIMAX_API_KEY 是否正确。\n"
                        "获取方式: https://platform.minimaxi.com/"
                    )
                raise Exception(f"MiniMax API error: {response.status_code}")

            data = response.json()
            latency_ms = (time.time() - start_time) * 1000

            output_content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})

            self._log_request_completed(latency_ms)

            return ProviderResponse(
                content=output_content,
                model=data.get("model", self.config.model or self.default_model),
                finish_reason=data["choices"][0].get("finish_reason", "stop"),
                usage=usage,
                latency_ms=latency_ms,
            )

        except httpx.HTTPError as e:
            self.logger.error(f"MiniMax request failed - {e}")
            raise Exception(f"Failed to call MiniMax API: {e}")

    async def generate_stream(
        self,
        prompt: str,
        messages: Optional[List[Message]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[StreamChunk]:
        """生成流式响应"""
        # 检查 API Key 是否配置
        if not self.api_key:
            yield StreamChunk(
                content="MiniMax API Key 未配置。请设置环境变量 MINIMAX_API_KEY 或在配置中指定。\n获取方式: https://platform.minimaxi.com/",
                finish=True
            )
            return

        start_time = time.time()
        self._log_request_started()

        system, msg_list = self._build_messages(prompt, messages, system_prompt)
        if system:
            msg_list.insert(0, {"role": "system", "content": system})

        request_body = {
            "model": self.config.model or self.default_model,
            "messages": msg_list,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "stream": True,
        }

        try:
            client = await self._get_client()
            async with client.stream("POST", "/chat/completions", json=request_body) as response:
                if response.status_code != 200:
                    if response.status_code == 401:
                        yield StreamChunk(
                            content="MiniMax API Key 无效或已过期。请检查环境变量 MINIMAX_API_KEY 是否正确。\n获取方式: https://platform.minimaxi.com/",
                            finish=True
                        )
                        return
                    raise Exception(f"MiniMax API error: {response.status_code}")

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
            self.logger.error(f"MiniMax streaming failed - {e}")
            yield StreamChunk(content=f"Error: {e}", finish=True)

    async def count_tokens(self, text: str) -> int:
        """估算 token 数量"""
        return self._estimate_tokens(text)