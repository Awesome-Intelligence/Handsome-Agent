"""Stream Events - 流式事件定义

定义流式输出的事件类型和数据结构。
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum


class StreamEventType(Enum):
    """流式事件类型"""
    DELTA = "stream.delta"           # 内容增量
    REASONING = "stream.reasoning"  # 推理过程
    TOOL_START = "stream.tool_start"  # 工具开始
    TOOL_END = "stream.tool_end"      # 工具结束
    COMPLETE = "stream.complete"     # 完成
    ERROR = "stream.error"            # 错误
    # 任务规划事件
    PLAN_START = "stream.plan_start"  # 任务规划开始
    PLAN_PROGRESS = "stream.plan_progress"  # 任务规划进度更新
    PLAN_COMPLETE = "stream.plan_complete"  # 任务规划完成


@dataclass
class StreamEvent:
    """流式事件基类"""
    type: StreamEventType
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0  # 由发射器设置

    @property
    def text(self) -> Optional[str]:
        """获取事件文本内容"""
        return self.data.get("text")

    @property
    def is_final(self) -> bool:
        """是否为最终事件（完成或错误）"""
        return self.type in (StreamEventType.COMPLETE, StreamEventType.ERROR)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp,
        }


@dataclass
class DeltaEvent(StreamEvent):
    """增量事件 - 携带新的内容片段"""
    def __init__(self, text: str, rendered: Optional[str] = None):
        super().__init__(
            type=StreamEventType.DELTA,
            data={
                "text": text,
                "rendered": rendered or text,
            }
        )


@dataclass
class ReasoningEvent(StreamEvent):
    """推理事件 - 携带思考/推理内容"""
    def __init__(self, text: str):
        super().__init__(
            type=StreamEventType.REASONING,
            data={"text": text}
        )


@dataclass
class ToolEvent(StreamEvent):
    """工具事件 - 工具执行开始/结束"""
    def __init__(
        self,
        event_type: StreamEventType,
        tool_name: str,
        tool_input: Optional[Dict] = None,
        tool_output: Optional[Dict] = None,
    ):
        assert event_type in (StreamEventType.TOOL_START, StreamEventType.TOOL_END)
        super().__init__(
            type=event_type,
            data={
                "tool_name": tool_name,
                "tool_input": tool_input or {},
                "tool_output": tool_output or {},
            }
        )

    @property
    def tool_name(self) -> str:
        return self.data.get("tool_name", "")


@dataclass
class CompleteEvent(StreamEvent):
    """完成事件 - 流式结束"""
    def __init__(
        self,
        text: str,
        usage: Optional[Dict[str, Any]] = None,
        reasoning: Optional[str] = None,
    ):
        super().__init__(
            type=StreamEventType.COMPLETE,
            data={
                "text": text,
                "usage": usage or {},
                "reasoning": reasoning,
            }
        )


@dataclass
class ErrorEvent(StreamEvent):
    """错误事件 - 流式出错"""
    def __init__(self, message: str, error_type: Optional[str] = None):
        super().__init__(
            type=StreamEventType.ERROR,
            data={
                "message": message,
                "error_type": error_type or "UnknownError",
            }
        )

    @property
    def message(self) -> str:
        return self.data.get("message", "")

    @property
    def error_type(self) -> str:
        return self.data.get("error_type", "UnknownError")


@dataclass
class PlanStartEvent(StreamEvent):
    """任务规划开始事件"""
    def __init__(
        self,
        main_task: str,
        complexity: Optional[str] = None,
    ):
        super().__init__(
            type=StreamEventType.PLAN_START,
            data={
                "main_task": main_task,
                "complexity": complexity or "unknown",
            }
        )


@dataclass
class PlanProgressEvent(StreamEvent):
    """任务规划进度事件"""
    def __init__(
        self,
        subtasks: List[Dict[str, Any]],
        completed: int,
        total: int,
        current_task: Optional[str] = None,
        progress_percent: int = 0,
    ):
        super().__init__(
            type=StreamEventType.PLAN_PROGRESS,
            data={
                "subtasks": subtasks,
                "completed": completed,
                "total": total,
                "current_task": current_task or "",
                "progress_percent": progress_percent,
            }
        )


@dataclass
class PlanCompleteEvent(StreamEvent):
    """任务规划完成事件"""
    def __init__(
        self,
        subtasks: List[Dict[str, Any]],
        completed: int,
        total: int,
        success: bool = True,
        summary: Optional[str] = None,
    ):
        super().__init__(
            type=StreamEventType.PLAN_COMPLETE,
            data={
                "subtasks": subtasks,
                "completed": completed,
                "total": total,
                "success": success,
                "summary": summary or "",
            }
        )