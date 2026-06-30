"""
DeepSeek Provider 实现
🧠 Decision - 🤖 LLM - DeepSeek 系列模型支持
"""

import os
import httpx
import json
import time
from typing import Optional, List, Dict, Any, AsyncIterator
from .base import BaseProvider, ProviderConfig, ProviderResponse, StreamChunk, Message
from common.logging_manager import get_llm_logger
from common.config import DEFAULT_LLM_BASE_URLS


class DeepSeekProvider(BaseProvider):
    """DeepSeek LLM Provider

    支持 DeepSeek V3, DeepSeek Coder 等模型
    """

    provider_name = "deepseek"
    provider_display_name = "DeepSeek"
    supported_models = [
        "deepseek-chat",
        "deepseek-coder",
        "deepseek-v3",
        "deepseek-v3-base",
    ]

    API_URL = "https://api.deepseek.com/chat"

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.base_url = (
            config.base_url
            or os.getenv("DEEPSEEK_BASE_URL")
            or DEFAULT_LLM_BASE_URLS.get("deepseek")
        )
        self.api_key = config.api_key
        self._client: Optional[httpx.AsyncClient] = None
        self.logger = get_llm_logger(self.__class__.__name__)

    def _get_request_body_extra(self, kwargs):
        """获取额外的请求体参数"""
        tools = kwargs.get("tools")
        if tools:
            return {"tools": tools}
        return {}

    def _should_handle_function_call(self, message):
        """检查是否有 tool_calls 或 function_call"""
        return message.get("tool_calls") or message.get("function_call")

    async def _get_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.API_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self.config.timeout,
                limits=self._get_default_limits(),
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

        system, msg_list, prompt_meta = self._build_messages(prompt, messages, system_prompt)
        if system:
            system_msg = {"role": "system", "content": system}
            # 附加 _prompt_meta 以便日志分层显示
            if prompt_meta:
                system_msg["_prompt_meta"] = prompt_meta
            msg_list.insert(0, system_msg)

        self._log_input_messages(msg_list, prompt_meta)

        request_body = {
            "model": self.config.model,
            "messages": msg_list,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "stream": False,
        }
        request_body.update(self._get_request_body_extra(kwargs))

        try:
            client = await self._get_client()
            response = await client.post("/completions", json=request_body)

            if response.status_code != 200:
                self.logger.error(f"DeepSeek API error - status: {response.status_code}")
                raise Exception(f"DeepSeek API error: {response.status_code}")

            data = response.json()
            latency_ms = (time.time() - start_time) * 1000

            message = data["choices"][0]["message"]
            content = message.get("content", "")
            usage = data.get("usage", {})

            function_call = self._should_handle_function_call(message)
            if function_call:
                self._log_output_content(json.dumps(function_call))
                self._log_response_debug(message, function_call)
                self.logger.debug(f"LLM Usage - prompt_tokens: {usage.get('prompt_tokens', 0)}, "
                                  f"completion_tokens: {usage.get('completion_tokens', 0)}, "
                                  f"total_tokens: {usage.get('total_tokens', 0)}")
                self._log_request_completed(latency_ms)
                return ProviderResponse(
                    content=json.dumps(function_call),
                    model=data.get("model", self.config.model),
                    finish_reason=data["choices"][0].get("finish_reason", "stop"),
                    usage=usage,
                    latency_ms=latency_ms,
                    function_call=function_call[0] if isinstance(function_call, list) else function_call,
                )

            self._log_output_content(content)
            self.logger.debug(f"LLM Usage - prompt_tokens: {usage.get('prompt_tokens', 0)}, "
                              f"completion_tokens: {usage.get('completion_tokens', 0)}, "
                              f"total_tokens: {usage.get('total_tokens', 0)}")

            self._log_request_completed(latency_ms)

            return ProviderResponse(
                content=content if content is not None else "",
                model=data.get("model", self.config.model),
                finish_reason=data["choices"][0].get("finish_reason", "stop"),
                usage=usage,
                latency_ms=latency_ms,
            )

        except httpx.HTTPError as e:
            self.logger.error(f"DeepSeek request failed - {e}")
            raise Exception(f"Failed to call DeepSeek API: {e}")

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

        system, msg_list, _ = self._build_messages(prompt, messages, system_prompt)
        if system:
            msg_list.insert(0, {"role": "system", "content": system})

        request_body = {
            "model": self.config.model,
            "messages": msg_list,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "stream": True,
        }

        try:
            client = await self._get_client()
            async with client.stream("POST", "/completions", json=request_body) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise Exception(f"DeepSeek API error: {response.status_code}")

                self._log_streaming_started()

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
                self._log_streaming_output(accumulated_content)
                self._log_request_completed(latency_ms)

        except Exception as e:
            detailed_error = self._log_request_error(e, "streaming")
            yield StreamChunk(content=f"Error: {detailed_error}", finish=True)

    async def count_tokens(self, text: str) -> int:
        """估算 token 数量"""
        return self._estimate_tokens(text)
