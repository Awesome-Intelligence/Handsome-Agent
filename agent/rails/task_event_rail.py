# 🧠 Decision - 🔧 Rail - 任务事件 Rail

"""
TaskEventRail - 任务事件追踪和 Checkpoint 控制

参考 jiuwenswarm 的 StreamEventRail 实现

功能：
1. 追踪工具调用事件
2. 在关键点插入 checkpoint（暂停点）
3. 处理中断请求（pause/resume/abort）
4. 发射任务更新事件

子层标识：📋 Task
主层：🧠 Decision
"""

import asyncio
from typing import Dict, Any, Optional, List, Callable

from common.logging_manager import get_task_logger
from agent.rails.rail import (
    Rail,
    RailPriority,
    RailResult,
    InterruptType as BaseInterruptType,
)
from agent.task.todo_toolkit import (
    TodoToolkit,
    TaskEvent,
    TaskEventLog,
    TaskStatus,
    get_todo_toolkit,
)


class TaskEventRail(Rail):
    """
    任务事件 Rail
    
    继承自 Rail 基类，提供：
    1. 任务事件追踪
    2. Checkpoint 暂停控制
    3. 中断处理
    """
    
    name = "task_event"
    description = "Task event tracking and checkpoint control"
    priority = RailPriority.NORMAL
    
    _pause_events: Dict[str, asyncio.Event] = {}
    _abort_requested: Dict[str, bool] = {}
    _lock_for_dicts = asyncio.Lock()
    
    def __init__(self, session_id: str):
        super().__init__(session_id)
        self._logger = get_task_logger("TaskEventRail")
        
        self._event_log = TaskEventLog(session_id)
        self._toolkit = get_todo_toolkit(session_id)
        
        self._before_tool_callbacks: List[Callable] = []
        self._after_tool_callbacks: List[Callable] = []
        self._task_updated_callbacks: List[Callable] = []
    
    @classmethod
    async def _get_pause_event(cls, session_id: str) -> asyncio.Event:
        """获取 session 的暂停事件"""
        async with cls._lock_for_dicts:
            if session_id not in cls._pause_events:
                cls._pause_events[session_id] = asyncio.Event()
                cls._pause_events[session_id].set()
        return cls._pause_events[session_id]
    
    @classmethod
    async def _get_abort_flag(cls, session_id: str) -> bool:
        """获取 session 的中止标志"""
        async with cls._lock_for_dicts:
            return cls._abort_requested.get(session_id, False)
    
    @classmethod
    async def _set_abort_flag(cls, session_id: str, value: bool) -> None:
        """设置 session 的中止标志"""
        async with cls._lock_for_dicts:
            cls._abort_requested[session_id] = value
    
    def pause(self) -> None:
        """暂停任务执行"""
        self._logger.info("📋 Task: Task execution paused")
        self._get_pause_event_sync().clear()
        self._log_event(TaskEvent(
            event_type="agent.paused",
            timestamp=asyncio.get_event_loop().time.__str__()
        ))
    
    def _get_pause_event_sync(self) -> asyncio.Event:
        """同步获取暂停事件"""
        import threading
        lock = threading.Lock()
        with lock:
            if self.session_id not in TaskEventRail._pause_events:
                TaskEventRail._pause_events[self.session_id] = asyncio.Event()
                TaskEventRail._pause_events[self.session_id].set()
        return TaskEventRail._pause_events[self.session_id]
    
    async def resume(self) -> None:
        """恢复任务执行"""
        await self._set_abort_flag(self.session_id, False)
        event = await self._get_pause_event(self.session_id)
        event.set()
        self._logger.info("📋 Task: Task execution resumed")
        self._log_event(TaskEvent(
            event_type="agent.resumed",
            timestamp=asyncio.get_event_loop().time.__str__()
        ))
    
    async def abort(self) -> None:
        """中止任务执行（不可恢复）"""
        await self._set_abort_flag(self.session_id, True)
        event = await self._get_pause_event(self.session_id)
        event.set()
        self._logger.warning("📋 Task: Task execution aborted")
        self._log_event(TaskEvent(
            event_type="agent.aborted",
            timestamp=asyncio.get_event_loop().time.__str__()
        ))
    
    async def is_paused(self) -> bool:
        """检查是否已暂停"""
        event = await self._get_pause_event(self.session_id)
        return not event.is_set()
    
    async def is_aborted(self) -> bool:
        """检查是否已中止"""
        return await self._get_abort_flag(self.session_id)
    
    async def wait_for_checkpoint(self) -> None:
        """等待 checkpoint（暂停点）"""
        event = await self._get_pause_event(self.session_id)
        await event.wait()
        
        if await self._get_abort_flag(self.session_id):
            self._logger.warning("📋 Task: Abort requested, raising CancelledError")
            raise asyncio.CancelledError("Agent abort requested")
    
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
            
            event_type = self._get_todo_event_type(tool_name)
            self._log_event(TaskEvent(
                event_type=f"tool.{event_type}",
                content=args.get("tasks") or args.get("task") or args.get("title", ""),
            ))
        
        for callback in self._before_tool_callbacks:
            try:
                callback(tool_name, args)
            except Exception as e:
                self._logger.error(f"Callback error: {e}")
        
        return None
    
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
            
            event_type = self._get_todo_event_type(tool_name)
            self._log_event(TaskEvent(
                event_type=f"tool.{event_type}.result",
                result=str(result)[:200] if result else None,
            ))
            
            if "list" in tool_name.lower() or "create" in tool_name.lower():
                tasks = self._toolkit.load_tasks()
                self._log_event(TaskEvent(
                    event_type="todo.updated",
                    status="updated",
                ))
                for task in tasks:
                    self._logger.debug(
                        f"📋 Task: Task #{task.id}: [{task.status.value}] {task.content}"
                    )
        
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
        """判断是否为任务工具"""
        todo_tools = ["todo", "task", "任务"]
        return any(t in tool_name.lower() for t in todo_tools)
    
    def _get_todo_event_type(self, tool_name: str) -> str:
        """获取任务事件类型"""
        name = tool_name.lower()
        if "create" in name or "add" in name or "insert" in name:
            return "created"
        elif "complete" in name or "done" in name:
            return "completed"
        elif "cancel" in name:
            return "cancelled"
        elif "remove" in name or "delete" in name:
            return "removed"
        elif "list" in name:
            return "listed"
        elif "clear" in name:
            return "cleared"
        return "updated"
    
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
        """获取任务统计"""
        tasks = self._toolkit.load_tasks()
        return {
            "total": len(tasks),
            "waiting": len([t for t in tasks if t.status == TaskStatus.WAITING]),
            "running": len([t for t in tasks if t.status == TaskStatus.RUNNING]),
            "completed": len([t for t in tasks if t.status == TaskStatus.COMPLETED]),
            "cancelled": len([t for t in tasks if t.status == TaskStatus.CANCELLED]),
        }
    
    def format_task_progress(self) -> str:
        """格式化任务进度"""
        stats = self.get_task_summary()
        total = stats["total"]
        if total == 0:
            return "📋 Task: No tasks"
        
        completed = stats["completed"] + stats["cancelled"]
        progress = (completed / total) * 100
        
        return (
            f"📋 Task Progress: {completed}/{total} "
            f"({progress:.0f}%) "
            f"[✅{stats['completed']} ❌{stats['cancelled']} ⏳{stats['waiting']} 🔄{stats['running']}]"
        )


__all__ = ["TaskEventRail"]