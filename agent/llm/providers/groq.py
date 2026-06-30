"""
Groq Provider 实现
🧠 Decision - 🤖 LLM - Groq 快速推理服务
"""

import os
import httpx
import json
import time
from typing import Optional, List, Dict, Any, AsyncIterator
from .base import BaseProvider, ProviderConfig, ProviderResponse, Message, StreamChunk
from common.logging_manager import get_llm_logger
from common.config import DEFAULT_LLM_BASE_URLS


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
        self.base_url = (
            config.base_url
            or os.getenv("GROQ_BASE_URL")
            or DEFAULT_LLM_BASE_URLS.get("groq")
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
                limits=self._get_default_limits(),
            )
        return self._client

    async def close(self) -> None:
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_request_body_extra(self, kwargs):
        """获取额外的请求体参数"""
        from tools.schema_registry import generate_openai_tools_schema

        extra = {}
        tools = kwargs.get("tools")
        if tools:
            tools_schema = generate_openai_tools_schema(tools)
            if tools_schema:
                extra["tools"] = tools_schema
        return extra

    def _extract_function_call(self, message):
        """从响应消息中提取函数调用"""
        return self._should_handle_function_call(message)

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
            if prompt_meta:
                system_msg["_prompt_meta"] = prompt_meta
            msg_list.insert(0, system_msg)

        self._log_input_messages(msg_list, prompt_meta)

        request_body = {
            "model": self.config.model or self.default_model,
            "messages": msg_list,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "stream": False,
        }
        request_body.update(self._get_request_body_extra(kwargs))

        try:
            client = await self._get_client()
            response = await client.post("/chat/completions", json=request_body)

            if response.status_code != 200:
                self.logger.error(f"Groq API error - status: {response.status_code}")
                raise Exception(f"Groq API error: {response.status_code}")

            data = response.json()
            latency_ms = (time.time() - start_time) * 1000

            message = data["choices"][0]["message"]
            usage = data.get("usage", {})

            function_call = self._extract_function_call(message)
            if function_call:
                self._log_response_debug(message, function_call)
                self._log_request_completed(latency_ms)
                return ProviderResponse(
                    content=json.dumps(function_call),
                    model=data.get("model", self.config.model or self.default_model),
                    finish_reason=data["choices"][0].get("finish_reason", "stop"),
                    usage=usage,
                    latency_ms=latency_ms,
                    function_call=function_call,
                )

            content = message.get("content", "")
            self._log_output_content(content)
            self._log_request_completed(latency_ms)

            return ProviderResponse(
                content=content,
                model=data.get("model", self.config.model or self.default_model),
                finish_reason=data["choices"][0].get("finish_reason", "stop"),
                usage=usage,
                latency_ms=latency_ms,
            )

        except httpx.HTTPError as e:
            self.logger.error(f"Groq request failed - {e}")
            raise Exception(f"Failed to call Groq API: {e}")

    async def generate_stream(
        self,
        prompt: str,
        messages: Optional[List[Message]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[StreamChunk]:
        """生成流式响应"""
        start_time = time.time()
        self.logger.info(f"Groq streaming request started - model: {self.config.model}")

        system, msg_list, prompt_meta = self._build_messages(prompt, messages, system_prompt)
        if system:
            system_msg = {"role": "system", "content": system}
            if prompt_meta:
                system_msg["_prompt_meta"] = prompt_meta
            msg_list.insert(0, system_msg)

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
                    error_text = await response.aread()
                    raise Exception(f"Groq API error: {response.status_code}")

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
            detailed_error = self._log_request_error(e, "streaming")
            yield StreamChunk(content=f"Error: {detailed_error}", finish=True)

    async def count_tokens(self, text: str) -> int:
        """估算 token 数量"""
        return self._estimate_tokens(text)