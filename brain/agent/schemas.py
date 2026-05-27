"""schemas - 工具调用和数据模型定义"""

from enum import Enum
from typing import Optional, Any, Literal, Dict, List
from pydantic import BaseModel, Field
from datetime import datetime
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


class Thought(BaseModel):
    """思考步骤"""
    reasoning: str
    action: Optional["Action"] = None
    is_final: bool = False
    confidence: float = 1.0


class Action(BaseModel):
    """行动"""
    tool_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class Observation(BaseModel):
    """观察结果"""
    observation: str
    success: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ToolSchema(BaseModel):
    """工具 Schema 定义"""
    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    returns: Optional[Dict[str, Any]] = None
    examples: List["ToolCallExample"] = Field(default_factory=list)
    safety_level: SafetyLevel = SafetyLevel.MEDIUM
    category: str = "general"


class ToolCallExample(BaseModel):
    """工具调用示例"""
    description: str
    parameters: Dict[str, Any]
    expected_output: str


class ExecutionRequest(BaseModel):
    """执行请求"""
    tool_call: ToolCall
    executor_type: Literal["shell", "docker", "ssh", "computer_use"] = "shell"
    safety_policy: Literal["relaxed", "standard", "strict"] = "standard"
    timeout_seconds: float = 30.0


class ExecutionResponse(BaseModel):
    """执行响应"""
    execution_id: str
    status: Literal["pending", "success", "error", "timeout"]
    tool_call: ToolCall
    result: Optional[Any] = None
    error_message: Optional[str] = None
    logs: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self._tools: Dict[str, ToolSchema] = {}
        self._adapters: Dict[str, Any] = {}
    
    def register(self, schema: ToolSchema) -> None:
        """注册工具"""
        self._tools[schema.name] = schema
    
    def register_adapter(self, name: str, adapter: Any) -> None:
        """注册工具适配器"""
        self._adapters[name] = adapter
    
    def get(self, name: str) -> Optional[ToolSchema]:
        """获取工具 Schema"""
        return self._tools.get(name)
    
    def list_all(self) -> List[ToolSchema]:
        """列出所有工具"""
        return list(self._tools.values())
    
    def list_by_category(self, category: str) -> List[ToolSchema]:
        """按类别列出工具"""
        return [t for t in self._tools.values() if t.category == category]
    
    def validate_tool_call(self, tool_call: ToolCall) -> bool:
        """验证工具调用"""
        schema = self.get(tool_call.tool_name)
        if not schema:
            return False
        # TODO: 实现参数验证
        return True