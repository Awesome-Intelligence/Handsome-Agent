"""公共数据模型"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid


class BaseResponse(BaseModel):
    """基础响应"""
    success: bool = True
    message: Optional[str] = None
    error_code: Optional[int] = None


class SessionInfo(BaseModel):
    """会话信息"""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    last_active: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HealthCheck(BaseModel):
    """健康检查"""
    status: str = "healthy"
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.now)
    services: Dict[str, str] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str
    code: int
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)