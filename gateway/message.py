"""
标准化消息格式定义
统一所有渠道的消息格式
"""

from enum import Enum
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class MessageChannel(str, Enum):
    """消息渠道枚举"""
    HTTP = "http"
    WEIXIN = "weixin"
    WEBSOCKET = "websocket"
    CLI = "cli"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    SLACK = "slack"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    WEBHOOK = "webhook"


class MessageContent(BaseModel):
    """消息内容"""
    type: Literal["text", "image", "file", "audio"] = "text"
    text: Optional[str] = None
    media_url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StandardMessage(BaseModel):
    """标准消息格式 - 所有渠道统一使用此格式"""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    channel: MessageChannel
    user_id: str
    session_id: str
    content: MessageContent
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return self.model_dump_json()
    
    @classmethod
    def from_json(cls, json_str: str) -> "StandardMessage":
        """从 JSON 字符串解析"""
        return cls.model_validate_json(json_str)


class ExecutionResult(BaseModel):
    """执行结果"""
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: Literal["success", "error", "pending"] = "pending"
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    logs: list[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }