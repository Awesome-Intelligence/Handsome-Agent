"""
OpenAI Provider Implementation
Supports GPT-3.5, GPT-4 and other models
"""

import httpx
import json
import time
from typing import Optional, List, Dict, Any, AsyncIterator
from .base import BaseLLMProvider, LLMResponse, LLMConfig, Message, StreamChunk
from common.logging_manager import get_llm_logger


class OpenAIProvider(BaseLLMProvider):
    """OpenAI LLM Provider"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.base_url = config.base_url or "https://api.openai.com/v1"
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
    ) -> LLMResponse:
        """Generate text response"""
        import time
        start_time = time.time()
        
        self.logger.info(f"LLM request started - model: {self.config.model}, base_url: {self.base_url}")
        
        # Build message list
        msg_list = []
        
        if system_prompt:
            msg_list.append(Message(role="system", content=system_prompt))
        
        if messages:
            # 兼容字典和 Message 对象
            for msg in messages:
                if isinstance(msg, dict):
                    msg_list.append(Message(**msg))
                else:
                    msg_list.append(msg)
        
        msg_list.append(Message(role="user", content=prompt))
        
        # Log detailed input (using INFO level for visibility)
        self.logger.info(f"LLM Input - {len(msg_list)} messages:")
        for i, msg in enumerate(msg_list):
            content_preview = msg.content[:300] + "..." if len(msg.content) > 300 else msg.content
            self.logger.info(f"  [{i}] {msg.role}: {content_preview}")
        
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
        
        # Log request body
        self.logger.info(f"LLM Request: model={request_body['model']}, temperature={request_body['temperature']}, max_tokens={request_body['max_tokens']}")
        
        try:
            client = await self._get_client()
            response = await client.post("/chat/completions", json=request_body)
            
            if response.status_code != 200:
                self.logger.error(f"LLM API error - status: {response.status_code}, response: {response.text}")
                raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")
            
            data = response.json()
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Log detailed output
            output_content = data["choices"][0]["message"]["content"]
            content_preview = output_content[:500] + "..." if len(output_content) > 500 else output_content
            self.logger.info(f"LLM request completed - latency: {latency_ms:.2f}ms, model: {data.get('model', self.config.model)}")
            self.logger.info(f"LLM Output (preview): {content_preview}")
            
            # Log usage stats
            usage = data.get("usage", {})
            if usage:
                self.logger.info(f"LLM Usage: prompt_tokens={usage.get('prompt_tokens', 'N/A')}, completion_tokens={usage.get('completion_tokens', 'N/A')}, total_tokens={usage.get('total_tokens', 'N/A')}")
            
            return LLMResponse(
                content=output_content,
                model=data.get("model", self.config.model),
                finish_reason=data["choices"][0].get("finish_reason", "stop"),
                usage=usage,
                latency_ms=latency_ms,
            )
            
        except httpx.HTTPError as e:
            self.logger.error(f"LLM request failed - error: {str(e)}")
            raise Exception(f"Failed to call OpenAI API: {str(e)}")
    
    async def generate_stream(
        self,
        prompt: str,
        messages: Optional[List[Message]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[StreamChunk]:
        """Generate streaming response"""
        import time
        start_time = time.time()
        
        self.logger.info(f"LLM streaming request started - model: {self.config.model}")
        
        msg_list = []
        if system_prompt:
            msg_list.append(Message(role="system", content=system_prompt))
        if messages:
            msg_list.extend(messages)
        msg_list.append(Message(role="user", content=prompt))
        
        # Log detailed input
        self.logger.info(f"LLM Streaming Input - {len(msg_list)} messages:")
        for i, msg in enumerate(msg_list):
            content_preview = msg.content[:300] + "..." if len(msg.content) > 300 else msg.content
            self.logger.info(f"  [{i}] {msg.role}: {content_preview}")
        
        request_body = {
            "model": self.config.model,
            "messages": [m.model_dump() for m in msg_list],
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "stream": True,
        }
        
        # Log request body
        self.logger.info(f"LLM Streaming Request: model={request_body['model']}, temperature={request_body['temperature']}, max_tokens={request_body['max_tokens']}")
        
        try:
            client = await self._get_client()
            async with client.stream("POST", "/chat/completions", json=request_body) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    self.logger.error(f"LLM Streaming API error - status: {response.status_code}, response: {error_text}")
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
                            
                            # Log streaming chunks (only for significant content)
                            if len(delta) > 0:
                                self.logger.info(f"LLM Streaming delta: {delta[:150]}")
                            
                            yield StreamChunk(
                                content=accumulated_content,
                                delta=delta,
                                finish=False,
                            )
                        except json.JSONDecodeError:
                            continue
                
                # Log final accumulated content
                content_preview = accumulated_content[:500] + "..." if len(accumulated_content) > 500 else accumulated_content
                latency_ms = (time.time() - start_time) * 1000
                self.logger.info(f"LLM streaming completed - latency: {latency_ms:.2f}ms, total_chars: {len(accumulated_content)}")
                self.logger.info(f"LLM Streaming Final Output (preview): {content_preview}")
                            
        except Exception as e:
            self.logger.error(f"LLM streaming failed - error: {str(e)}")
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