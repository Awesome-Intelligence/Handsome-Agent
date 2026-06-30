#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一状态枚举定义

此模块提供所有状态的统一枚举定义，避免多处定义造成的重复和语义不一致。

状态分类：
1. AgentStatus - Agent 整体生命周期状态
2. TaskStatus - A2A 任务生命周期状态
3. TodoStatus - Todo 任务状态
4. ExitReason - 执行退出原因
5. BudgetMode - 预算控制模式
"""

from enum import Enum


# ============================================================================
# Agent 整体状态
# ============================================================================

class AgentStatus(str, Enum):
    """Agent 整体状态枚举

    状态转换规则：
    - IDLE → RUNNING: start()
    - RUNNING → PAUSED: pause()
    - RUNNING → COMPLETED: complete() / should_exit()
    - RUNNING → ABORTED: abort()
    - PAUSED → RUNNING: resume()
    - PAUSED → ABORTED: abort()
    - COMPLETED/ABORTED → IDLE: reset()

    任何状态都可以转换到 ABORTED（紧急中止）。
    """

    IDLE = "idle"           # 空闲，未开始或已重置
    RUNNING = "running"     # 运行中，正在执行任务
    PAUSED = "paused"       # 暂停，等待恢复（可恢复）
    COMPLETED = "completed" # 完成，正常结束
    ABORTED = "aborted"     # 中止，异常结束（不可恢复）

    def is_active(self) -> bool:
        """是否为活跃状态（可继续执行）"""
        return self in (AgentStatus.IDLE, AgentStatus.RUNNING, AgentStatus.PAUSED)

    def is_terminal(self) -> bool:
        """是否为终止状态（需要重置）"""
        return self in (AgentStatus.COMPLETED, AgentStatus.ABORTED)

    def __str__(self) -> str:
        return self.value


# ============================================================================
# Task 任务状态 (A2A Protocol)
# ============================================================================

class TaskStatus(str, Enum):
    """Task 生命周期状态枚举（匹配 A2A 规范）

    状态转换：
    submitted → working → completed/failed/canceled

    或需要用户输入的情况：
    submitted → working → input-required → working → completed
    """

    SUBMITTED = "submitted"       # 任务已提交，未开始处理
    WORKING = "working"           # 任务正在处理中
    INPUT_REQUIRED = "input-required"  # 需要更多输入（用户或 Agent）
    COMPLETED = "completed"       # 任务成功完成
    FAILED = "failed"            # 任务执行失败
    CANCELED = "canceled"        # 任务被取消

    def is_terminal(self) -> bool:
        """是否为终止状态"""
        return self in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELED)

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_string(cls, value: str) -> "TaskStatus":
        """从字符串创建枚举，处理未知值"""
        try:
            return cls(value)
        except ValueError:
            return cls.SUBMITTED


# ============================================================================
# Todo 任务状态
# ============================================================================

class TodoStatus(str, Enum):
    """Todo 任务状态枚举

    用于 TodoToolkit 和 Kanban 管理的任务状态
    """

    PENDING = "pending"       # 待处理
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed"   # 已完成
    CANCELLED = "cancelled"   # 已取消

    # Kanban 映射
    KANBAN_MAPPING = {
        "todo": PENDING,
        "ready": PENDING,
        "triage": PENDING,
        "running": IN_PROGRESS,
        "blocked": IN_PROGRESS,
        "done": COMPLETED,
        "archived": CANCELLED,
    }

    @classmethod
    def from_kanban(cls, kanban_status: str) -> "TodoStatus":
        """从 Kanban 状态转换为 TodoStatus"""
        return cls.KANBAN_MAPPING.get(kanban_status, cls.PENDING)

    def to_kanban(self) -> str:
        """转换为 Kanban 状态"""
        mapping = {
            TodoStatus.PENDING: "todo",
            TodoStatus.IN_PROGRESS: "running",
            TodoStatus.COMPLETED: "done",
            TodoStatus.CANCELLED: "archived",
        }
        return mapping.get(self, "todo")

    def __str__(self) -> str:
        return self.value


# ============================================================================
# 任务事件类型（用于 TaskEventRail）
# ============================================================================

class TaskEventType(str, Enum):
    """任务事件类型枚举

    统一的事件类型定义，替代 TaskEventRail 中的字符串常量
    """

    # 生命周期事件
    CREATED = "created"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REMOVED = "removed"
    LISTED = "listed"
    CLEARED = "cleared"
    UPDATED = "updated"

    # Agent 事件
    AGENT_STARTED = "agent.started"
    AGENT_PAUSED = "agent.paused"
    AGENT_RESUMED = "agent.resumed"
    AGENT_ABORTED = "agent.aborted"

    # 工具事件
    TOOL_STARTED = "tool.started"
    TOOL_COMPLETED = "tool.completed"

    def __str__(self) -> str:
        return self.value


# ============================================================================
# 退出原因
# ============================================================================

class ExitReason(str, Enum):
    """执行退出原因枚举"""

    DIRECT_RESPONSE = "direct_response"  # LLM 直接响应
    ASK_CLARIFICATION = "ask_clarification"  # 需要澄清
    ERROR = "error"  # 执行错误
    GOAL_COMPLETED = "goal_completed"  # Goal 完成
    GOAL_PAUSED = "goal_paused"  # Goal 暂停
    BUDGET_EXHAUSTED = "budget_exhausted"  # 预算耗尽
    INTERRUPTED = "interrupted"  # 中断
    COMPLETED = "completed"  # 任务完成
    ABORTED = "aborted"  # 被中止
    TOOL_LOOP_HALT = "tool_loop_halt"  # Tool Loop 检测到循环，强制停止
    UNKNOWN = "unknown"  # 未知原因

    def __str__(self) -> str:
        return self.value


# ============================================================================
# 预算模式
# ============================================================================

class BudgetMode(str, Enum):
    """预算控制模式"""

    ITERATION = "iteration"  # 非 Goal 模式（按迭代）
    TURN = "turn"           # Goal 模式（按轮次）

    def __str__(self) -> str:
        return self.value


# ============================================================================
# Exit Decision（统一退出决策）
# ============================================================================

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class ExitDecision:
    """统一的退出决策

    用于 AgentState 和 GoalManager 的退出判断。
    """
    should_exit: bool
    reason: "ExitReason"
    message: str = ""
    continuation_prompt: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "should_exit": self.should_exit,
            "reason": self.reason.value if hasattr(self.reason, 'value') else str(self.reason),
            "message": self.message,
            "continuation_prompt": self.continuation_prompt,
            "metadata": self.metadata,
        }


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    # Agent 状态
    "AgentStatus",
    # Task 状态
    "TaskStatus",
    # Todo 状态
    "TodoStatus",
    # 事件类型
    "TaskEventType",
    # 退出原因
    "ExitReason",
    # 预算模式
    "BudgetMode",
    # 退出决策
    "ExitDecision",
]