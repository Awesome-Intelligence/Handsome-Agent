"""
OpenAI Provider 实现
🧠 Decision - 🤖 LLM - OpenAI GPT 系列模型支持
"""

import os
import httpx
import json
import time
from typing import Optional, List, Dict, Any, AsyncIterator
from .base import BaseProvider, ProviderConfig, ProviderResponse, StreamChunk, Message
from common.logging_manager import get_llm_logger
from common.config import DEFAULT_LLM_BASE_URLS


class OpenAIProvider(BaseProvider):
    """OpenAI LLM Provider

    支持 GPT-3.5, GPT-4 及所有 OpenAI 兼容 API（如 Azure, OpenRouter 等）
    """

    provider_name = "openai"
    provider_display_name = "OpenAI"
    supported_models = [
        "gpt-3.5-turbo",
        "gpt-4",
        "gpt-4-turbo",
        "gpt-4o",
        "gpt-4o-mini",
    ]

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        # 优先级: 配置 > 环境变量 > Provider默认URL
        self.base_url = (
            config.base_url
            or os.getenv("OPENAI_BASE_URL")
            or DEFAULT_LLM_BASE_URLS.get("openai")
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

    def _get_request_body_extra(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """获取额外的请求体参数

        统一处理 tools 参数。
        """
        from tools.schema_registry import generate_openai_tools_schema

        extra = {}

        # 处理 tools 参数
        tools = kwargs.get("tools")
        if tools:
            # 统一转换为 OpenAI 格式
            tools_schema = generate_openai_tools_schema(tools)
            if tools_schema:
                extra["tools"] = tools_schema

        return extra

    def _extract_function_call(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """从 OpenAI 响应消息中提取函数调用"""
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

        system, msg_list = self._build_messages(prompt, messages, system_prompt)
        if system:
            msg_list.insert(0, {"role": "system", "content": system})

        self._log_input_messages(msg_list)

        request_body = {
            "model": self.config.model,
            "messages": msg_list,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "top_p": kwargs.get("top_p", self.config.top_p),
            "frequency_penalty": kwargs.get("frequency_penalty", self.config.frequency_penalty),
            "presence_penalty": kwargs.get("presence_penalty", self.config.presence_penalty),
            "stream": False,
        }

        # 添加 tools 参数
        request_body.update(self._get_request_body_extra(kwargs))

        try:
            client = await self._get_client()
            response = await client.post("/chat/completions", json=request_body)

            if response.status_code != 200:
                self.logger.error(f"OpenAI API error - status: {response.status_code}")
                raise Exception(f"OpenAI API error: {response.status_code}")

            data = response.json()
            latency_ms = (time.time() - start_time) * 1000

            message = data["choices"][0]["message"]

            # 检查是否有函数调用
            function_call = self._extract_function_call(message)
            if function_call:
                self._log_response_debug(message, function_call)
                self._log_request_completed(latency_ms)
                return ProviderResponse(
                    content=json.dumps(function_call),
                    model=data.get("model", self.config.model),
                    finish_reason=data["choices"][0].get("finish_reason", "stop"),
                    usage=data.get("usage", {}),
                    latency_ms=latency_ms,
                    function_call=function_call,
                )

            output_content = message.get("content", "")
            usage = data.get("usage", {})

            self._log_output_content(output_content)
            self._log_request_completed(latency_ms)

            return ProviderResponse(
                content=output_content,
                model=data.get("model", self.config.model),
                finish_reason=data["choices"][0].get("finish_reason", "stop"),
                usage=usage,
                latency_ms=latency_ms,
            )

        except httpx.HTTPError as e:
            self.logger.error(f"OpenAI request failed - {e}")
            raise Exception(f"Failed to call OpenAI API: {e}")

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
            "model": self.config.model,
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
                    raise Exception(f"OpenAI API error: {response.status_code}")

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
