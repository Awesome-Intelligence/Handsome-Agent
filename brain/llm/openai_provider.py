"""
OpenAI Provider 实现
支持 GPT-3.5, GPT-4 等模型
"""

import httpx
import json
from typing import Optional, List, Dict, Any, AsyncIterator
from .base import BaseLLMProvider, LLMResponse, LLMConfig, Message, StreamChunk


class OpenAIProvider(BaseLLMProvider):
    """OpenAI LLM Provider"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.base_url = config.base_url or "https://api.openai.com/v1"
        self.api_key = config.api_key
        self._client: Optional[httpx.AsyncClient] = None
    
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
    ) -> LLMResponse:
        """生成文本响应"""
        import time
        start_time = time.time()
        
        # 构建消息列表
        msg_list = []
        
        if system_prompt:
            msg_list.append(Message(role="system", content=system_prompt))
        
        if messages:
            msg_list.extend(messages)
        
        msg_list.append(Message(role="user", content=prompt))
        
        # 构建请求
        request_body = {
            "model": self.config.model,
            "messages": [m.model_dump() for m in msg_list],
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "top_p": kwargs.get("top_p", self.config.top_p),
            "frequency_penalty": kwargs.get("frequency_penalty", self.config.frequency_penalty),
            "presence_penalty": kwargs.get("presence_penalty", self.config.presence_penalty),
            "stream": False,
        }
        
        try:
            client = await self._get_client()
            response = await client.post("/chat/completions", json=request_body)
            
            if response.status_code != 200:
                raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")
            
            data = response.json()
            
            latency_ms = (time.time() - start_time) * 1000
            
            return LLMResponse(
                content=data["choices"][0]["message"]["content"],
                model=data.get("model", self.config.model),
                finish_reason=data["choices"][0].get("finish_reason", "stop"),
                usage=data.get("usage", {}),
                latency_ms=latency_ms,
            )
            
        except httpx.HTTPError as e:
            raise Exception(f"Failed to call OpenAI API: {str(e)}")
    
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
        if system_prompt:
            msg_list.append(Message(role="system", content=system_prompt))
        if messages:
            msg_list.extend(messages)
        msg_list.append(Message(role="user", content=prompt))
        
        request_body = {
            "model": self.config.model,
            "messages": [m.model_dump() for m in msg_list],
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "stream": True,
        }
        
        try:
            client = await self._get_client()
            async with client.stream("POST", "/chat/completions", json=request_body) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise Exception(f"OpenAI API error: {response.status_code} - {error_text}")
                
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
                            
        except Exception as e:
            yield StreamChunk(content=f"Error: {str(e)}", finish=True)
    
    async def count_tokens(self, text: str) -> int:
        """估算 token 数量（简化实现）"""
        # 简化的估算：中文字符 * 2 + 英文单词 * 1.3
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        english_chars = len(text) - chinese_chars
        return int(chinese_chars * 2 + english_chars * 0.25)
    
    async def get_available_models(self) -> List[Dict[str, Any]]:
        """获取可用模型列表"""
        try:
            client = await self._get_client()
            response = await client.get("/models")
            if response.status_code == 200:
                return response.json().get("data", [])
            return []
        except:
            return []