# 🧠 Decision - 🔧 Rail - 任务事件 Rail

"""
TaskEventRail - 任务事件追踪和 Checkpoint 控制

功能：
1. 追踪工具调用事件
2. 在关键点插入 checkpoint（暂停点）
3. 处理中断请求（pause/resume/abort）
4. 发射任务更新事件

子层标识：📋 Task
主层：🧠 Decision

注意：此 Rail 不再依赖 TodoToolkit，直接使用 Kanban 管理任务状态
注意：pause/abort 管理已统一到 RailRegistry，此 Rail 不再维护独立状态
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
from dataclasses import dataclass, asdict

from common.logging_manager import get_task_logger
from agent.rails.rail import (
    Rail,
    RailPriority,
    RailResult,
    InterruptType as BaseInterruptType,
)
# 统一状态枚举
from agent.state import TaskEventType, TodoStatus
# 统一管理
from agent.rails.registry import get_rail_registry


@dataclass
class TaskEvent:
    """任务事件"""
    event_type: str
    task_id: Optional[int] = None
    content: Optional[str] = None
    status: Optional[str] = None
    result: Optional[str] = None
    timestamp: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


class TaskEventLog:
    """任务事件日志"""

    def __init__(self, session_id: str, workspace_dir: Optional[str] = None):
        self.session_id = session_id
        self.workspace_dir = workspace_dir or str(Path.home() / ".agent_z")
        self._log_path = Path(self.workspace_dir) / "sessions" / session_id / "task_events.jsonl"
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event: TaskEvent) -> None:
        """记录事件"""
        with open(self._log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")

    def get_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取最近的日志"""
        if not self._log_path.exists():
            return []

        logs = []
        with open(self._log_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    logs.append(json.loads(line))

        return logs[-limit:]


class TaskEventRail(Rail):
    """
    任务事件 Rail
    
    继承自 Rail 基类，提供：
    1. 任务事件追踪
    2. Checkpoint 暂停控制（委托给 RailRegistry）
    3. 中断处理（委托给 RailRegistry）
    
    注意：pause/abort/pause_event/abort_flag 等状态管理已统一到 RailRegistry
    """
    
    name = "task_event"
    description = "Task event tracking and checkpoint control"
    priority = RailPriority.NORMAL
    
    def __init__(self, session_id: str):
        super().__init__(session_id)
        self._logger = get_task_logger("TaskEventRail")

        self._event_log = TaskEventLog(session_id)
        self._session_id = session_id
        self._kanban_manager = None  # 懒加载

        self._before_tool_callbacks: List[Callable] = []
        self._after_tool_callbacks: List[Callable] = []
        self._task_updated_callbacks: List[Callable] = []

    def _get_kanban_manager(self):
        """懒加载 Kanban 管理器"""
        if self._kanban_manager is None:
            try:
                from tools.kanban_tool import _kanban_manager
                self._kanban_manager = _kanban_manager
            except Exception as e:
                self._logger.warning(f"Failed to load Kanban manager: {e}")
        return self._kanban_manager
    
    @property
    def _registry(self):
        """获取 RailRegistry 单例"""
        return get_rail_registry()
    
    def pause(self) -> None:
        """暂停任务执行（委托给 RailRegistry）"""
        self._registry.pause(self.session_id)
        self._logger.info("📋 Task: Task execution paused")
        self._log_event(TaskEvent(
            event_type="agent.paused",
            timestamp=asyncio.get_event_loop().time.__str__()
        ))
    
    async def resume(self) -> None:
        """恢复任务执行（委托给 RailRegistry）"""
        self._registry.resume(self.session_id)
        self._logger.info("📋 Task: Task execution resumed")
        self._log_event(TaskEvent(
            event_type="agent.resumed",
            timestamp=asyncio.get_event_loop().time.__str__()
        ))
    
    async def abort(self) -> None:
        """中止任务执行（委托给 RailRegistry）"""
        self._registry.abort(self.session_id)
        self._logger.warning("📋 Task: Task execution aborted")
        self._log_event(TaskEvent(
            event_type="agent.aborted",
            timestamp=asyncio.get_event_loop().time.__str__()
        ))
    
    async def is_paused(self) -> bool:
        """检查是否已暂停（委托给 RailRegistry）"""
        return self._registry.is_paused(self.session_id)
    
    async def is_aborted(self) -> bool:
        """检查是否已中止（委托给 RailRegistry）"""
        return self._registry.is_aborted(self.session_id)
    
    async def wait_for_checkpoint(self) -> None:
        """等待 checkpoint（暂停点）（委托给 RailRegistry）"""
        await self._registry.wait_for_checkpoint(self.session_id)
    
    def _log_event(self, event: TaskEvent) -> None:
        """记录事件到日志"""
        self._event_log.log(event)
    
    async def before_tool_call(
        self,
        tool_name: str,
        args: Dict[str, Any],
        **kwargs
    ) -> Optional[RailResult]:
        """工具调用前触发"""
        if self._is_todo_tool(tool_name):
            self._logger.debug(f"📋 Task: Tool call: {tool_name}({args})")

            # 确定事件类型
            event_type = self._determine_event_type(tool_name)
            self._current_event_type = event_type

            self._log_event(TaskEvent(
                event_type=str(event_type),
                content=args.get("tasks") or args.get("task") or args.get("title", ""),
            ))

        for callback in self._before_tool_callbacks:
            try:
                callback(tool_name, args)
            except Exception as e:
                self._logger.error(f"Callback error: {e}")

        return None

    def _determine_event_type(self, tool_name: str) -> TaskEventType:
        """确定任务事件类型"""
        name = tool_name.lower()
        if "create" in name or "add" in name or "insert" in name:
            return TaskEventType.CREATED
        elif "complete" in name or "done" in name:
            return TaskEventType.COMPLETED
        elif "cancel" in name:
            return TaskEventType.CANCELLED
        elif "remove" in name or "delete" in name:
            return TaskEventType.REMOVED
        elif "list" in name:
            return TaskEventType.LISTED
        elif "clear" in name:
            return TaskEventType.CLEARED
        return TaskEventType.UPDATED
    
    async def after_tool_call(
        self,
        tool_name: str,
        args: Dict[str, Any],
        result: Any,
        **kwargs
    ) -> Optional[RailResult]:
        """工具调用后触发"""
        if self._is_todo_tool(tool_name):
            self._logger.debug(f"📋 Task: Tool result: {tool_name} -> {str(result)[:100]}")

            event_type = getattr(self, "_current_event_type", TaskEventType.UPDATED)
            self._log_event(TaskEvent(
                event_type=f"tool.{event_type.value}.result",
                result=str(result)[:200] if result else None,
            ))

            if "list" in tool_name.lower() or "create" in tool_name.lower():
                # 使用 Kanban 获取任务列表
                kanban = self._get_kanban_manager()
                if kanban:
                    try:
                        board_id = kanban.get_default_board_id()
                        if board_id:
                            tasks = kanban.list_tasks(board_id=board_id, tenant=self._session_id)
                            self._log_event(TaskEvent(
                                event_type="todo.updated",
                                status="updated",
                            ))
                            for task in tasks:
                                self._logger.debug(
                                    f"📋 Task: Task #{task.id}: [{task.status}] {task.title}"
                                )
                    except Exception as e:
                        self._logger.debug(f"Failed to load Kanban tasks: {e}")

        for callback in self._after_tool_callbacks:
            try:
                callback(tool_name, args, result)
            except Exception as e:
                self._logger.error(f"Callback error: {e}")

        return None
    
    async def on_checkpoint(self, checkpoint_name: str) -> Optional[RailResult]:
        """Checkpoint 点触发"""
        await self.wait_for_checkpoint()
        self._logger.debug(f"📋 Task: Checkpoint reached: {checkpoint_name}")
        return None
    
    async def on_interrupt(self, interrupt_type: str) -> Optional[RailResult]:
        """中断请求时触发"""
        if interrupt_type == BaseInterruptType.PAUSE.value:
            self.pause()
        elif interrupt_type == BaseInterruptType.RESUME.value:
            await self.resume()
        elif interrupt_type == BaseInterruptType.ABORT.value:
            await self.abort()
        
        return RailResult(allowed=True)
    
    def _is_todo_tool(self, tool_name: str) -> bool:
        """判断是否为 Todo 工具（Layer 1）"""
        # 只监听 todo 工具，不包括 kanban_* 或 a2a task 相关工具
        todo_tool_names = ["todo"]
        return any(t in tool_name.lower() for t in todo_tool_names)
    
    def _get_todo_event_type(self) -> TaskEventType:
        """获取任务事件类型 - 由 before_tool_call 设置"""
        return getattr(self, "_current_event_type", TaskEventType.UPDATED)
    
    def on_before_tool_call(self, callback: Callable) -> None:
        """注册工具调用前回调"""
        self._before_tool_callbacks.append(callback)
    
    def on_after_tool_call(self, callback: Callable) -> None:
        """注册工具调用后回调"""
        self._after_tool_callbacks.append(callback)
    
    def on_task_updated(self, callback: Callable) -> None:
        """注册任务更新回调"""
        self._task_updated_callbacks.append(callback)
    
    def get_task_summary(self) -> Dict[str, int]:
        """获取任务统计（使用 Kanban）"""
        kanban = self._get_kanban_manager()
        if not kanban:
            return {
                "total": 0,
                "waiting": 0,
                "running": 0,
                "completed": 0,
                "cancelled": 0,
            }

        try:
            board_id = kanban.get_default_board_id()
            if not board_id:
                return {"total": 0, "waiting": 0, "running": 0, "completed": 0, "cancelled": 0}

            tasks = kanban.list_tasks(board_id=board_id, tenant=self._session_id)

            return {
                "total": len(tasks),
                "waiting": len([t for t in tasks if t.status in ("triage", "todo", "ready")]),
                "running": len([t for t in tasks if t.status in ("running", "blocked")]),
                "completed": len([t for t in tasks if t.status == str(TodoStatus.COMPLETED)]),
                "cancelled": len([t for t in tasks if t.status == str(TodoStatus.CANCELLED)]),
            }
        except Exception as e:
            self._logger.debug(f"Failed to get task summary: {e}")
            return {"total": 0, "waiting": 0, "running": 0, "completed": 0, "cancelled": 0}

    def format_task_progress(self) -> str:
        """格式化任务进度"""
        stats = self.get_task_summary()
        total = stats["total"]
        if total == 0:
            return "📋 Task: No tasks"

        completed = stats["completed"] + stats["cancelled"]
        progress = (completed / total) * 100 if total > 0 else 0

        return (
            f"📋 Task Progress: {completed}/{total} "
            f"({progress:.0f}%) "
            f"[✅{stats['completed']} ❌{stats['cancelled']} ⏳{stats['waiting']} 🔄{stats['running']}]"
        )


__all__ = ["TaskEventRail"]