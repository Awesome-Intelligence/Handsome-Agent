"""
Provider 基类
🧠 Decision - 🤖 LLM - Provider 抽象基类
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, AsyncIterator
from pydantic import BaseModel, Field
from datetime import datetime
import time


@dataclass
class ProviderConfig:
    """Provider 配置"""
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
    role: str
    content: str
    name: Optional[str] = None

    def model_dump(self, **kwargs):
        """兼容 Pydantic v1/v2"""
        try:
            return super().model_dump(**kwargs)
        except AttributeError:
            return self.dict(**kwargs)


class ProviderResponse(BaseModel):
    """Provider 响应"""
    content: str
    model: str
    finish_reason: str = "stop"
    usage: Dict[str, Any] = Field(default_factory=dict)
    latency_ms: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        extra = "allow"

    def model_dump(self, **kwargs):
        """兼容 Pydantic v1/v2"""
        try:
            return super().model_dump(**kwargs)
        except AttributeError:
            return self.dict(**kwargs)


class StreamChunk(BaseModel):
    """流式响应块"""
    content: str = ""
    delta: str = ""
    finish: bool = False
    usage: Optional[Dict[str, int]] = None


class BaseProvider(ABC):
    """Provider 抽象基类"""

    # Provider 标识符
    provider_name: str = "base"
    # Provider 显示名称
    provider_display_name: str = "Base Provider"
    # 支持的模型列表
    supported_models: List[str] = []

    def __init__(self, config: ProviderConfig):
        self.config = config
        self._message_history: List[Message] = []

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        messages: Optional[List[Message]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> ProviderResponse:
        """生成文本响应"""
        pass

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        messages: Optional[List[Message]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[StreamChunk]:
        """生成流式响应"""
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

    def _build_messages(
        self,
        prompt: str,
        messages: Optional[List[Message]] = None,
        system_prompt: Optional[str] = None
    ) -> tuple[Optional[str], List[Dict[str, Any]]]:
        """构建消息列表

        Returns:
            (system_prompt, messages_list)
        """
        system = system_prompt or ""
        msg_list: List[Dict[str, Any]] = []

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
        return (system if system else None, msg_list)

    def _estimate_tokens(self, text: str) -> int:
        """估算 token 数量（简化实现）"""
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        english_chars = len(text) - chinese_chars
        return int(chinese_chars * 2 + english_chars * 0.25)
