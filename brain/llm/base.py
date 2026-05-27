"""
LLM Provider 基类和通用定义
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, AsyncIterator, Literal
from pydantic import BaseModel, Field
from datetime import datetime
import time


@dataclass
class LLMConfig:
    """LLM 配置"""
    model: str = "gpt-4"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4000
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    timeout: float = 60.0
    stream: bool = False


class Message(BaseModel):
    """对话消息"""
    role: Literal["system", "user", "assistant", "function"]
    content: str
    name: Optional[str] = None


class LLMResponse(BaseModel):
    """LLM 响应"""
    content: str
    model: str
    finish_reason: str = "stop"
    usage: Dict[str, int] = Field(default_factory=dict)
    latency_ms: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class StreamChunk(BaseModel):
    """流式响应块"""
    content: str = ""
    delta: str = ""
    finish: bool = False
    usage: Optional[Dict[str, int]] = None


class BaseLLMProvider(ABC):
    """LLM Provider 抽象基类"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self._message_history: List[Message] = []
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        messages: Optional[List[Message]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        生成文本响应
        
        Args:
            prompt: 用户提示
            messages: 对话历史
            system_prompt: 系统提示
            
        Returns:
            LLMResponse: 响应结果
        """
        pass
    
    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        messages: Optional[List[Message]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[StreamChunk]:
        """
        生成流式响应
        
        Args:
            prompt: 用户提示
            messages: 对话历史
            system_prompt: 系统提示
            
        Yields:
            StreamChunk: 流式响应块
        """
        pass
    
    @abstractmethod
    async def count_tokens(self, text: str) -> int:
        """计算 token 数量"""
        pass
    
    def add_message(self, role: str, content: str) -> None:
        """添加消息到历史"""
        self._message_history.append(Message(role=role, content=content))
    
    def clear_history(self) -> None:
        """清空历史"""
        self._message_history.clear()
    
    def get_history(self) -> List[Message]:
        """获取历史"""
        return self._message_history.copy()
    
    def set_history(self, messages: List[Message]) -> None:
        """设置历史"""
        self._message_history = messages.copy()