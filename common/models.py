"""公共数据模型"""

from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class SessionInfo(BaseModel):
    """会话信息"""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    last_active: datetime = Field(default_factory=datetime.now)
    metadata: dict = Field(default_factory=dict)
