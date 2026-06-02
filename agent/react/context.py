# 🧠 Decision - ✅ Task - ReAct 执行上下文

"""
ReActContext - ReAct 循环执行上下文

用于在 ReAct 循环中传递状态和共享数据。

子层标识：✅ Task
主层：🧠 Decision
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime


@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Optional[Callable] = None
    category: str = "general"


@dataclass
class Message:
    """消息定义"""
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ToolCall:
    """工具调用记录"""
    tool_name: str
    parameters: Dict[str, Any]
    result: Any = None
    is_error: bool = False
    timestamp: datetime = field(default_factory=datetime.now)


class ReActContext:
    """
    ReAct 执行上下文
    
    在整个 ReAct 循环中共享状态。
    
    Attributes:
        task_description: 任务描述
        tools: 工具列表
        tool_handlers: 工具处理器映射
        conversation_history: 对话历史
        tool_calls: 已执行的工具调用记录
        custom_data: 自定义数据
    """
    
    def __init__(
        self,
        task_description: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_handlers: Optional[Dict[str, Callable]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        max_iterations: int = 20,
        **kwargs
    ):
        self.task_description = task_description
        self.tools = tools or []
        self.tool_handlers = tool_handlers or {}
        self.conversation_history = conversation_history or []
        self.max_iterations = max_iterations
        
        self._messages: List[Message] = []
        self._tool_calls: List[ToolCall] = []
        self._custom_data: Dict[str, Any] = kwargs
        
        self._current_iteration = 0
    
    @property
    def messages(self) -> List[Message]:
        """获取消息列表"""
        return self._messages
    
    @property
    def tool_calls(self) -> List[ToolCall]:
        """获取工具调用记录"""
        return self._tool_calls
    
    @property
    def current_iteration(self) -> int:
        """当前迭代次数"""
        return self._current_iteration
    
    @property
    def remaining_iterations(self) -> int:
        """剩余迭代次数"""
        return max(0, self.max_iterations - self._current_iteration)
    
    def add_message(self, role: str, content: str) -> None:
        """添加消息"""
        self._messages.append(Message(role=role, content=content))
    
    def add_tool_call(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        result: Any = None,
        is_error: bool = False
    ) -> None:
        """记录工具调用"""
        self._tool_calls.append(ToolCall(
            tool_name=tool_name,
            parameters=parameters,
            result=result,
            is_error=is_error
        ))
    
    def increment_iteration(self) -> None:
        """迭代次数 +1"""
        self._current_iteration += 1
    
    def set(self, key: str, value: Any) -> None:
        """设置自定义数据"""
        self._custom_data[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取自定义数据"""
        return self._custom_data.get(key, default)
    
    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """获取工具 Schema"""
        return [
            {
                "name": t["name"] if isinstance(t, dict) else t.name,
                "description": t["description"] if isinstance(t, dict) else t.description,
                "parameters": t["parameters"] if isinstance(t, dict) else t.parameters
            }
            for t in self.tools
        ]
    
    def get_recent_messages(self, count: int = 6) -> List[Dict[str, str]]:
        """获取最近的对话历史"""
        return [
            {"role": m.role, "content": m.content[:200]}
            for m in self._messages[-count:]
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于调试）"""
        return {
            "task_description": self.task_description,
            "current_iteration": self._current_iteration,
            "max_iterations": self.max_iterations,
            "message_count": len(self._messages),
            "tool_call_count": len(self._tool_calls),
            "recent_tool_calls": [
                {
                    "tool": tc.tool_name,
                    "is_error": tc.is_error,
                    "timestamp": tc.timestamp.isoformat()
                }
                for tc in self._tool_calls[-5:]
            ]
        }


__all__ = ["ReActContext", "ToolDefinition", "Message", "ToolCall"]