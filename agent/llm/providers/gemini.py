"""
Gemini Provider 实现
🧠 Decision - 🤖 LLM - Google Gemini 系列模型支持
"""

import httpx
import json
import time
from typing import Optional, List, Dict, Any, AsyncIterator
from .base import BaseProvider, ProviderConfig, ProviderResponse, StreamChunk, Message
from common.logging_manager import get_llm_logger


class GeminiProvider(BaseProvider):
    """Gemini LLM Provider

    支持 Gemini Pro, Gemini Ultra 等模型
    """

    provider_name = "gemini"
    provider_display_name = "Google Gemini"
    supported_models = [
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-2.0-flash",
        "gemini-pro",
    ]

    API_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.api_key = config.api_key
        self._client: Optional[httpx.AsyncClient] = None
        self.logger = get_llm_logger(self.__class__.__name__)

    async def _get_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.config.timeout,
            )
        return self._client

    async def close(self) -> None:
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _convert_to_gemini_format(
        self,
        prompt: str,
        messages: Optional[List[Message]] = None,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """转换为 Gemini 格式"""
        contents = []

        if messages:
            for msg in messages:
                if isinstance(msg, dict):
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                else:
                    role = msg.role
                    content = msg.content

                # Gemini 使用 user/model 而不是 user/assistant
                gemini_role = "user" if role in ["user", "system"] else "model"
                contents.append({"role": gemini_role, "parts": [{"text": content}]})

        contents.append({"role": "user", "parts": [{"text": prompt}]})

        return {"contents": contents}

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

        body = self._convert_to_gemini_format(prompt, messages, system_prompt)

        if system_prompt:
            body["system_instruction"] = {"parts": [{"text": system_prompt}]}

        body["generationConfig"] = {
            "temperature": kwargs.get("temperature", self.config.temperature),
            "maxOutputTokens": kwargs.get("max_tokens", self.config.max_tokens),
            "topP": kwargs.get("top_p", self.config.top_p),
        }

        # 记录输入内容（DEBUG级别）
        if self.logger:
            contents = body.get("contents", [])
            self.logger.debug(f"{self.provider_display_name} Input Messages ({len(contents)} messages):")
            for i, msg in enumerate(contents):
                role = msg.get("role", "unknown")
                parts = msg.get("parts", [])
                content = parts[0].get("text", "") if parts else ""
                preview = content[:30] + "..." if len(content) > 30 else content
                self.logger.debug(f"  [{i}] {role}: {preview}")

        try:
            client = await self._get_client()
            url = f"{self.API_URL}/{self.config.model}:generateContent?key={self.api_key}"
            response = await client.post(url, json=body)

            if response.status_code != 200:
                self.logger.error(f"Gemini API error - status: {response.status_code}")
                raise Exception(f"Gemini API error: {response.status_code}")

            data = response.json()
            latency_ms = (time.time() - start_time) * 1000

            content = data["candidates"][0]["content"]["parts"][0]["text"]
            usage = data.get("usageMetadata", {})

            self._log_request_completed(latency_ms)

            return ProviderResponse(
                content=content,
                model=self.config.model,
                finish_reason="stop",
                usage={
                    "prompt_tokens": usage.get("promptTokenCount", 0),
                    "completion_tokens": usage.get("candidatesTokenCount", 0),
                    "total_tokens": usage.get("totalTokenCount", 0),
                },
                latency_ms=latency_ms,
            )

        except httpx.HTTPError as e:
            self.logger.error(f"Gemini request failed - {e}")
            raise Exception(f"Failed to call Gemini API: {e}")

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

        body = self._convert_to_gemini_format(prompt, messages, system_prompt)

        if system_prompt:
            body["system_instruction"] = {"parts": [{"text": system_prompt}]}

        body["generationConfig"] = {
            "temperature": kwargs.get("temperature", self.config.temperature),
            "maxOutputTokens": kwargs.get("max_tokens", self.config.max_tokens),
            "topP": kwargs.get("top_p", self.config.top_p),
        }

        # 记录输入内容（DEBUG级别）
        if self.logger:
            contents = body.get("contents", [])
            self.logger.debug(f"{self.provider_display_name} Input Messages ({len(contents)} messages):")
            for i, msg in enumerate(contents):
                role = msg.get("role", "unknown")
                parts = msg.get("parts", [])
                content = parts[0].get("text", "") if parts else ""
                preview = content[:30] + "..." if len(content) > 30 else content
                self.logger.debug(f"  [{i}] {role}: {preview}")

        try:
            client = await self._get_client()
            url = f"{self.API_URL}/{self.config.model}:streamGenerateContent?key={self.api_key}"
            async with client.stream("POST", url, json=body) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise Exception(f"Gemini API error: {response.status_code}")

                accumulated_content = ""
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if "candidates" in data and data["candidates"]:
                                delta = data["candidates"][0]["content"]["parts"][0].get("text", "")
                                accumulated_content += delta

                                yield StreamChunk(
                                    content=accumulated_content,
                                    delta=delta,
                                    finish=False,
                                )
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue

                latency_ms = (time.time() - start_time) * 1000
                self._log_request_completed(latency_ms)
                yield StreamChunk(finish=True)

        except Exception as e:
            self.logger.error(f"Gemini streaming failed - {e}")
            yield StreamChunk(content=f"Error: {e}", finish=True)

    async def count_tokens(self, text: str) -> int:
        """估算 token 数量"""
        return self._estimate_tokens(text)
