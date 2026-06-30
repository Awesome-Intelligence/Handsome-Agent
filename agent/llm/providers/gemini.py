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
                limits=self._get_default_limits(),
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

                gemini_role = "user" if role in ["user", "system"] else "model"
                parts = []
                if content:
                    parts.append({"text": content})

                tool_calls = msg.get("tool_calls", []) if isinstance(msg, dict) else []
                for tc in tool_calls:
                    func = tc.get("function", {})
                    try:
                        args = json.loads(func.get("arguments", "{}"))
                    except (json.JSONDecodeError, TypeError):
                        args = {}
                    parts.append({
                        "functionCall": {
                            "name": func.get("name", ""),
                            "args": args,
                        }
                    })

                if msg.get("role") == "tool" and isinstance(msg, dict):
                    tool_name = msg.get("name", "tool_result")
                    parts.append({
                        "functionResponse": {
                            "name": tool_name,
                            "response": {"result": content},
                        }
                    })
                    gemini_role = "function"

                if parts:
                    contents.append({"role": gemini_role, "parts": parts})

        if prompt:
            contents.append({"role": "user", "parts": [{"text": prompt}]})

        return {"contents": contents}

    def _convert_tools_to_gemini(self, tools: List[Any]) -> List[Dict[str, Any]]:
        """将工具列表转换为 Gemini 格式"""
        from tools.schema_registry import generate_openai_tools_schema

        if not tools:
            return []

        oai_tools = generate_openai_tools_schema(tools)
        if not oai_tools:
            return []

        function_declarations = []
        for tool in oai_tools:
            func = tool.get("function", {})
            function_declarations.append({
                "name": func.get("name", ""),
                "description": func.get("description", ""),
                "parameters": func.get("parameters", {}),
            })

        return [{"functionDeclarations": function_declarations}]

    def _extract_function_call_from_gemini(self, candidate: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """从 Gemini 响应中提取函数调用"""
        content = candidate.get("content", {})
        parts = content.get("parts", [])

        for part in parts:
            if "functionCall" in part:
                fc = part["functionCall"]
                name = fc.get("name", "")
                args = fc.get("args", {})
                try:
                    arguments_str = json.dumps(args, ensure_ascii=False)
                except (TypeError, ValueError):
                    arguments_str = str(args)
                return {
                    "name": name,
                    "arguments": arguments_str,
                }

        return None

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

        tools = kwargs.get("tools")
        if tools:
            gemini_tools = self._convert_tools_to_gemini(tools)
            if gemini_tools:
                body["tools"] = gemini_tools

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

            candidate = data.get("candidates", [{}])[0]
            usage = data.get("usageMetadata", {})

            function_call = self._extract_function_call_from_gemini(candidate)
            if function_call:
                self._log_response_debug({"role": "assistant"}, function_call)
                self._log_request_completed(latency_ms)
                return ProviderResponse(
                    content=json.dumps(function_call),
                    model=self.config.model,
                    finish_reason=candidate.get("finishReason", "stop"),
                    usage={
                        "prompt_tokens": usage.get("promptTokenCount", 0),
                        "completion_tokens": usage.get("candidatesTokenCount", 0),
                        "total_tokens": usage.get("totalTokenCount", 0),
                    },
                    latency_ms=latency_ms,
                    function_call=function_call,
                )

            parts = candidate.get("content", {}).get("parts", [])
            content = parts[0].get("text", "") if parts else ""

            self._log_output_content(content)
            self._log_request_completed(latency_ms)

            return ProviderResponse(
                content=content,
                model=self.config.model,
                finish_reason=candidate.get("finishReason", "stop"),
                usage={
                    "prompt_tokens": usage.get("promptTokenCount", 0),
                    "completion_tokens": usage.get("candidatesTokenCount", 0),
                    "total_tokens": usage.get("totalTokenCount", 0),
                },
                latency_ms=latency_ms,
            )

        except httpx.HTTPError as e:
            detailed_error = self._log_request_error(e, "request")
            raise Exception(f"Failed to call Gemini API: {detailed_error}")

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
            detailed_error = self._log_request_error(e, "streaming")
            yield StreamChunk(content=f"Error: {detailed_error}", finish=True)

    async def count_tokens(self, text: str) -> int:
        """估算 token 数量"""
        return self._estimate_tokens(text)
