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
import json
import uuid


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
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


@dataclass
class ToolCallRecord:
    """工具调用记录（用于生成 tool_call_id）"""
    id: str
    name: str
    arguments: str


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
        
        # 初始化 _messages，从 conversation_history 合并历史消息
        self._messages: List[Message] = [
            Message(role=msg['role'], content=msg['content'])
            for msg in (conversation_history or [])
        ]
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
    ) -> str:
        """
        记录工具调用
        
        同时将调用记录为消息列表中的 assistant 消息，
        并返回生成的 tool_call_id 供 add_tool_result() 使用。
        
        Returns:
            tool_call_id: 用于标识此次工具调用的唯一 ID
        """
        # 生成唯一的 tool_call_id
        tool_call_id = f"call_{uuid.uuid4().hex[:24]}"
        
        # 将调用记录添加到 tool_calls 列表
        self._tool_calls.append(ToolCall(
            tool_name=tool_name,
            parameters=parameters,
            result=result,
            is_error=is_error
        ))
        
        # 将调用记录为 assistant 消息（包含 tool_calls）
        import json
        tool_calls = [{
            "id": tool_call_id,
            "type": "function",
            "function": {
                "name": tool_name,
                "arguments": json.dumps(parameters) if isinstance(parameters, dict) else str(parameters)
            }
        }]
        self._messages.append(Message(
            role="assistant",
            content="",
            tool_calls=tool_calls
        ))
        
        return tool_call_id

    def add_tool_result(
        self,
        tool_call_id: str,
        tool_name: str,
        result: Any
    ) -> None:
        """
        添加工具结果消息
        
        将工具执行结果作为 tool 角色消息添加到消息历史中。
        
        Args:
            tool_call_id: 工具调用 ID（由 add_tool_call 返回）
            tool_name: 工具名称
            result: 工具执行结果
        """
        # 将结果格式化为字符串
        if isinstance(result, dict):
            content = json.dumps(result, ensure_ascii=False, indent=2)
        elif isinstance(result, str):
            content = result
        else:
            content = str(result)
        
        # 添加 tool 角色消息
        self._messages.append(Message(
            role="tool",
            content=content,
            tool_call_id=tool_call_id
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
        """获取工具 Schema

        使用统一的 schema_registry 生成 OpenAI 格式的工具 Schema。
        """
        from tools.schema_registry import generate_openai_tools_schema
        return generate_openai_tools_schema(self.tools)
    
    def get_recent_messages(self, count: int = 6) -> List[Dict[str, str]]:
        """获取最近的对话历史"""
        return [
            {"role": m.role, "content": m.content[:200]}
            for m in self._messages[-count:]
        ]
    
    def to_messages_dict(self) -> List[Dict[str, Any]]:
        """
        将消息列表转换为标准字典格式
        
        用于传递给 LLM 的消息列表格式。
        
        Returns:
            标准消息列表格式
        """
        result = []
        for msg in self._messages:
            msg_dict = {"role": msg.role}
            if msg.content:
                msg_dict["content"] = msg.content
            if msg.tool_calls:
                msg_dict["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                msg_dict["tool_call_id"] = msg.tool_call_id
            result.append(msg_dict)
        return result
    
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


__all__ = ["ReActContext", "ToolDefinition", "Message", "ToolCall", "ToolCallRecord"]