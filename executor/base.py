"""
执行器基类和通用定义
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
import uuid


class SafetyLevel(str, Enum):
    """安全级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ToolCall(BaseModel):
    """工具调用"""
    tool_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    reasoning: Optional[str] = None
    confidence: float = 1.0
    safety_level: SafetyLevel = SafetyLevel.MEDIUM
    execution_id: Optional[str] = None


@dataclass
class ExecutorConfig:
    """执行器配置"""
    name: str = "BaseExecutor"
    timeout_seconds: float = 30.0
    allowed_commands: List[str] = field(default_factory=list)
    blocked_patterns: List[str] = field(default_factory=list)
    enable_logging: bool = True
    work_dir: Optional[str] = None


class ExecutionResult(BaseModel):
    """执行结果"""
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: Literal["pending", "success", "error", "timeout"] = "pending"
    tool_call: ToolCall
    output: Optional[str] = None
    error_message: Optional[str] = None
    logs: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    safety_level: SafetyLevel = SafetyLevel.MEDIUM
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class BaseExecutor(ABC):
    """执行器抽象基类"""
    
    def __init__(self, config: ExecutorConfig):
        self.config = config
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """设置日志"""
        import logging
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    async def execute(self, tool_call: ToolCall) -> ExecutionResult:
        """
        执行工具调用
        
        Args:
            tool_call: 工具调用请求
            
        Returns:
            ExecutionResult: 执行结果
        """
        pass
    
    @abstractmethod
    async def validate(self, tool_call: ToolCall) -> tuple[bool, Optional[str]]:
        """
        验证工具调用的安全性
        
        Args:
            tool_call: 工具调用请求
            
        Returns:
            (is_valid, error_message): 是否有效及错误信息
        """
        pass
    
    def _check_safety(self, command: str) -> tuple[bool, Optional[str]]:
        """检查命令安全性"""
        # 检查是否在白名单中
        if self.config.allowed_commands:
            first_word = command.split()[0] if command.split() else ""
            if first_word not in self.config.allowed_commands:
                return False, f"Command '{first_word}' not in whitelist"
        
        # 检查黑名单模式
        for pattern in self.config.blocked_patterns:
            if pattern in command:
                return False, f"Command contains blocked pattern: {pattern}"
        
        return True, None
    
    async def _log_execution(self, message: str) -> None:
        """记录执行日志"""
        if self.config.enable_logging:
            self.logger.info(message)