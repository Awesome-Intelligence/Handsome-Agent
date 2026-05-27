"""
Claude Provider 实现
支持 Claude 3 Opus, Sonnet, Haiku 等模型
"""

import httpx
import json
from typing import Optional, List, Dict, Any, AsyncIterator
from .base import BaseLLMProvider, LLMResponse, LLMConfig, Message, StreamChunk


class ClaudeProvider(BaseLLMProvider):
    """Claude LLM Provider"""
    
    API_URL = "https://api.anthropic.com/v1"
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.api_key = config.api_key
        self._client: Optional[httpx.AsyncClient] = None
        
        # Claude 模型映射
        self.model_map = {
            "claude-opus": "claude-3-opus-20240229",
            "claude-sonnet": "claude-3-sonnet-20240229",
            "claude-haiku": "claude-3-haiku-20240307",
            "claude-3-opus": "claude-3-opus-20240229",
            "claude-3-sonnet": "claude-3-sonnet-20240229",
            "claude-3-haiku": "claude-3-haiku-20240307",
        }
    
    def _get_model_name(self) -> str:
        """获取实际的模型名称"""
        return self.model_map.get(self.config.model, self.config.model)
    
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
    
    async def generate(
        self,
        prompt: str,
        messages: Optional[List[Message]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """生成文本响应"""
        import time
        start_time = time.time()
        
        # 构建消息列表（Claude 格式）
        msg_list = []
        
        if system_prompt:
            # Claude 使用 system 参数
            pass
        
        if messages:
            for msg in messages:
                if msg.role == "system":
                    system_prompt = (system_prompt or "") + "\n" + msg.content
                else:
                    msg_list.append({
                        "role": msg.role,
                        "content": msg.content
                    })
        
        msg_list.append({"role": "user", "content": prompt})
        
        # 构建请求
        request_body = {
            "model": self._get_model_name(),
            "messages": msg_list,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "top_p": kwargs.get("top_p", self.config.top_p),
        }
        
        if system_prompt:
            request_body["system"] = system_prompt
        
        try:
            client = await self._get_client()
            response = await client.post("/messages", json=request_body)
            
            if response.status_code != 200:
                raise Exception(f"Claude API error: {response.status_code} - {response.text}")
            
            data = response.json()
            
            latency_ms = (time.time() - start_time) * 1000
            
            return LLMResponse(
                content=data["content"][0]["text"],
                model=data.get("model", self.config.model),
                finish_reason=data.get("stop_reason", "stop"),
                usage={
                    "input_tokens": data.get("usage", {}).get("input_tokens", 0),
                    "output_tokens": data.get("usage", {}).get("output_tokens", 0),
                },
                latency_ms=latency_ms,
            )
            
        except httpx.HTTPError as e:
            raise Exception(f"Failed to call Claude API: {str(e)}")
    
    async def generate_stream(
        self,
        prompt: str,
        messages: Optional[List[Message]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[StreamChunk]:
        """生成流式响应"""
        import time
        start_time = time.time()
        
        msg_list = []
        if messages:
            for msg in messages:
                if msg.role == "system":
                    system_prompt = (system_prompt or "") + "\n" + msg.content
                else:
                    msg_list.append({"role": msg.role, "content": msg.content})
        
        msg_list.append({"role": "user", "content": prompt})
        
        request_body = {
            "model": self._get_model_name(),
            "messages": msg_list,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "stream": True,
        }
        
        if system_prompt:
            request_body["system"] = system_prompt
        
        try:
            client = await self._get_client()
            async with client.stream("POST", "/messages", json=request_body) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise Exception(f"Claude API error: {response.status_code} - {error_text}")
                
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
                            
        except Exception as e:
            yield StreamChunk(content=f"Error: {str(e)}", finish=True)
    
    async def count_tokens(self, text: str) -> int:
        """估算 token 数量（简化实现）"""
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        english_chars = len(text) - chinese_chars
        return int(chinese_chars * 2 + english_chars * 0.25)