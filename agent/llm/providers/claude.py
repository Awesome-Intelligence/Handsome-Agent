"""
Claude Provider 实现
🧠 Decision - 🤖 LLM - Anthropic Claude 系列模型支持
"""

import httpx
import json
import time
from typing import Optional, List, Dict, Any, AsyncIterator
from .base import BaseProvider, ProviderConfig, ProviderResponse, StreamChunk, Message
from common.logging_manager import get_llm_logger


class ClaudeProvider(BaseProvider):
    """Claude LLM Provider

    支持 Claude 3 Opus, Sonnet, Haiku 等模型
    """

    provider_name = "claude"
    provider_display_name = "Anthropic Claude"
    supported_models = [
        "claude-3-5-sonnet",
        "claude-3-5-sonnet-20241022",
        "claude-3-opus",
        "claude-3-sonnet",
        "claude-3-haiku",
    ]

    API_URL = "https://api.anthropic.com/v1"

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.api_key = config.api_key
        self._client: Optional[httpx.AsyncClient] = None
        self.logger = get_llm_logger(self.__class__.__name__)

    async def _get_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.API_URL,
                headers={
                    "x-api-key": self.api_key,
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01",
                },
                timeout=self.config.timeout,
            )
        return self._client

    async def close(self) -> None:
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_request_body_extra(self, kwargs):
        """获取额外的请求体参数

        Claude 使用 tools 参数而非 function calling 格式。
        """
        from tools.schema_registry import generate_openai_tools_schema

        extra = {}

        # 处理 tools 参数 (Claude 格式)
        tools = kwargs.get("tools")
        if tools:
            # Claude 使用不同的 tools 格式
            tools_schema = self._convert_to_claude_tools(tools)
            if tools_schema:
                extra["tools"] = tools_schema

        return extra

    def _convert_to_claude_tools(self, tools) -> List[Dict]:
        """将工具转换为 Claude 格式"""
        from tools.schema_registry import generate_openai_tools_schema

        # 先获取 OpenAI 格式
        openai_tools = generate_openai_tools_schema(tools)

        # 转换为 Claude 格式
        claude_tools = []
        for tool in openai_tools:
            func = tool.get("function", tool)
            claude_tools.append({
                "name": func["name"],
                "description": func.get("description", ""),
                "input_schema": func.get("parameters", {"type": "object", "properties": {}})
            })

        return claude_tools

    def _extract_function_call(self, data: Dict) -> Optional[Dict[str, Any]]:
        """从 Claude 响应中提取函数调用"""
        content = data.get("content", [])
        if content and isinstance(content, list):
            for block in content:
                if block.get("type") == "tool_use":
                    return {
                        "name": block.get("name", ""),
                        "arguments": block.get("input", {})
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

        self.logger.info(f"Claude request started - model: {self.config.model}")

        # 构建消息列表
        msg_list = []
        system = system_prompt or ""

        if messages:
            for msg in messages:
                if isinstance(msg, dict):
                    if msg.get("role") == "system":
                        system = (system + "\n" + msg.get("content", "")) if system else msg.get("content", "")
                    else:
                        msg_list.append({"role": msg.get("role"), "content": msg.get("content")})
                else:
                    if msg.role == "system":
                        system = (system + "\n" + msg.content) if system else msg.content
                    else:
                        msg_list.append({"role": msg.role, "content": msg.content})

        msg_list.append({"role": "user", "content": prompt})

        self._log_input_messages(msg_list)

        request_body = {
            "model": self.config.model,
            "messages": msg_list,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
        }

        if system:
            request_body["system"] = system

        # 添加 tools 参数
        request_body.update(self._get_request_body_extra(kwargs))

        try:
            client = await self._get_client()
            response = await client.post("/messages", json=request_body)

            if response.status_code != 200:
                self.logger.error(f"Claude API error - status: {response.status_code}")
                raise Exception(f"Claude API error: {response.status_code}")

            data = response.json()
            latency_ms = (time.time() - start_time) * 1000

            # 检查是否有工具调用
            function_call = self._extract_function_call(data)
            if function_call:
                self._log_response_debug(data, function_call)
                self._log_request_completed(latency_ms)
                return ProviderResponse(
                    content=json.dumps(function_call),
                    model=data.get("model", self.config.model),
                    finish_reason=data.get("stop_reason", "stop"),
                    usage={
                        "input_tokens": data.get("usage", {}).get("input_tokens", 0),
                        "output_tokens": data.get("usage", {}).get("output_tokens", 0),
                    },
                    latency_ms=latency_ms,
                    function_call=function_call,
                )

            content = data["content"][0]["text"]
            usage = data.get("usage", {})

            self._log_output_content(content)
            self._log_request_completed(latency_ms)

            return ProviderResponse(
                content=content,
                model=data.get("model", self.config.model),
                finish_reason=data.get("stop_reason", "stop"),
                usage={
                    "input_tokens": usage.get("input_tokens", 0),
                    "output_tokens": usage.get("output_tokens", 0),
                },
                latency_ms=latency_ms,
            )

        except httpx.HTTPError as e:
            self.logger.error(f"Claude request failed - {e}")
            raise Exception(f"Failed to call Claude API: {e}")

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

        msg_list = []
        system = system_prompt or ""

        if messages:
            for msg in messages:
                if isinstance(msg, dict):
                    if msg.get("role") == "system":
                        system = (system + "\n" + msg.get("content", "")) if system else msg.get("content", "")
                    else:
                        msg_list.append({"role": msg.get("role"), "content": msg.get("content")})
                else:
                    if msg.role == "system":
                        system = (system + "\n" + msg.content) if system else msg.content
                    else:
                        msg_list.append({"role": msg.role, "content": msg.content})

        msg_list.append({"role": "user", "content": prompt})

        request_body = {
            "model": self.config.model,
            "messages": msg_list,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "stream": True,
        }

        if system:
            request_body["system"] = system

        try:
            client = await self._get_client()
            async with client.stream("POST", "/messages", json=request_body) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise Exception(f"Claude API error: {response.status_code}")

                accumulated_content = ""
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            yield StreamChunk(finish=True)
                            break

                        try:
                            data = json.loads(data_str)
                            if data.get("type") == "content_block_delta":
                                delta = data.get("delta", {}).get("text", "")
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
