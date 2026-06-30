#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TUI 层 Textual 消息定义

🚪 Access - 💬 CLI - TUI Messages

定义 TUI 面板订阅的内部消息类型。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

# 降级机制：如果 textual 不可用，提供友好提示
try:
    from textual.message import Message
except ImportError:
    class Message:
        """Message 基类 - textual 不可用时的降级实现."""
        pass


# ============================================================================
# 数据结构
# ============================================================================


@dataclass
class TaskItem:
    """任务项数据结构
    
    Attributes:
        task_id: 任务 ID
        subtask_id: 子任务 ID
        title: 任务标题
        description: 任务描述
        status: 任务状态 (pending, running, completed, failed, cancelled)
        progress: 进度百分比 (0-100)
        result: 任务结果
        error: 错误信息
        created_at: 创建时间
        started_at: 开始时间
        completed_at: 完成时间
        duration_ms: 执行时长（毫秒）
        depends_on: 依赖的子任务 ID 列表
    """
    
    task_id: str
    subtask_id: int
    title: str
    description: str = ""
    status: str = "pending"
    progress: int = 0
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    depends_on: List[int] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典.
        
        Returns:
            字典表示
        """
        return {
            "task_id": self.task_id,
            "subtask_id": self.subtask_id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "progress": self.progress,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "depends_on": self.depends_on,
        }


# ============================================================================
# Textual 消息类
# ============================================================================


class UpdatedReason:
    """任务面板更新原因常量"""
    
    TASK_CREATED = "task_created"
    SUBTASKS_UPDATED = "subtasks_updated"
    SUBTASK_STARTED = "subtask_started"
    SUBTASK_PROGRESS = "subtask_progress"
    SUBTASK_COMPLETED = "subtask_completed"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETED = "task_completed"
    CLEAR = "clear"


@dataclass
class TaskPanelToggled(Message):
    """任务面板展开/折叠消息
    
    当任务面板的展开/折叠状态发生变更时发布此消息。
    
    Attributes:
        expanded: 是否展开
        task_id: 任务 ID
    """
    
    def __init__(self, sender: Any, expanded: bool, task_id: str) -> None:
        """初始化任务面板切换消息.
        
        Args:
            sender: 消息发送者
            expanded: 是否展开
            task_id: 任务 ID
        """
        super().__init__()
        self.expanded = expanded
        self.task_id = task_id


# ============================================================================
# 模块导出
# ============================================================================

__all__ = [
    "TaskItem",
    "UpdatedReason",
    "TaskPanelToggled",
]
