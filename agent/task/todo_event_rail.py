#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务事件 Rail - Task Event Rail
参考 JiuwenSwarm 的 StreamEventRail 实现

提供功能：
- 任务事件追踪
- Checkpoint 暂停点
- 中断请求处理
- 任务状态实时更新
"""

import asyncio
import threading
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from enum import Enum

from common.logging_manager import get_tool_logger, get_task_logger
from agent.todo_toolkit import (
    TodoToolkit, TaskEvent, TaskEventLog, 
    TaskStatus, get_todo_toolkit
)


class InterruptType(str, Enum):
    """中断类型"""
    PAUSE = "pause"       # 暂停（可恢复）
    RESUME = "resume"      # 恢复
    ABORT = "abort"        # 中止（不可恢复）
    CANCEL = "cancel"     # 取消当前任务


class TaskEventRail:
    """
    任务事件 Rail
    
    功能：
    1. 追踪工具调用事件
    2. 在关键点插入 checkpoint（暂停点）
    3. 处理中断请求（pause/resume/abort）
    4. 发射任务更新事件
    """
    
    _pause_events: Dict[str, asyncio.Event] = {}
    _abort_requested: Dict[str, bool] = {}
    _locks: Dict[str, threading.Lock] = {}
    _lock_for_dicts = threading.Lock()
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self._logger = get_tool_logger("TaskEventRail")
        self._task_logger = get_task_logger("TaskEvent")
        
        self._event_log = TaskEventLog(session_id)
        self._toolkit = get_todo_toolkit(session_id)
        
        self._before_tool_callbacks: List[Callable] = []
        self._after_tool_callbacks: List[Callable] = []
        self._task_updated_callbacks: List[Callable] = []
    
    @classmethod
    def _get_pause_event(cls, session_id: str) -> asyncio.Event:
        """获取 session 的暂停事件"""
        if session_id not in cls._pause_events:
            with cls._lock_for_dicts:
                if session_id not in cls._pause_events:
                    cls._pause_events[session_id] = asyncio.Event()
                    cls._pause_events[session_id].set()
        return cls._pause_events[session_id]
    
    @classmethod
    def _get_abort_flag(cls, session_id: str) -> bool:
        """获取 session 的中止标志"""
        with cls._lock_for_dicts:
            return cls._abort_requested.get(session_id, False)
    
    @classmethod
    def _set_abort_flag(cls, session_id: str, value: bool) -> None:
        """设置 session 的中止标志"""
        with cls._lock_for_dicts:
            cls._abort_requested[session_id] = value
    
    def pause(self) -> None:
        """暂停任务执行"""
        self._logger.info(f"📋 [任务层] 任务执行已暂停")
        self._get_pause_event(self.session_id).clear()
        self._log_event(TaskEvent(
            event_type="agent.paused",
            timestamp=datetime.now().isoformat()
        ))
    
    def resume(self) -> None:
        """恢复任务执行"""
        self._logger.info(f"📋 [任务层] 任务执行已恢复")
        self._set_abort_flag(self.session_id, False)
        self._get_pause_event(self.session_id).set()
        self._log_event(TaskEvent(
            event_type="agent.resumed",
            timestamp=datetime.now().isoformat()
        ))
    
    def abort(self) -> None:
        """中止任务执行（不可恢复）"""
        self._logger.warning(f"📋 [任务层] 任务执行已被中止")
        self._set_abort_flag(self.session_id, True)
        self._get_pause_event(self.session_id).set()
        self._log_event(TaskEvent(
            event_type="agent.aborted",
            timestamp=datetime.now().isoformat()
        ))
    
    def is_paused(self) -> bool:
        """检查是否已暂停"""
        return not self._get_pause_event(self.session_id).is_set()
    
    def is_aborted(self) -> bool:
        """检查是否已中止"""
        return self._get_abort_flag(self.session_id)
    
    async def wait_for_checkpoint(self) -> None:
        """等待 checkpoint（暂停点）"""
        pause_event = self._get_pause_event(self.session_id)
        await pause_event.wait()
        
        if self._get_abort_flag(self.session_id):
            self._logger.warning(f"📋 [任务层] 检测到中止请求，正在终止...")
            raise asyncio.CancelledError("Agent abort requested")
    
    def _log_event(self, event: TaskEvent) -> None:
        """记录事件到日志"""
        self._event_log.log(event)
    
    def log_tool_call(self, tool_name: str, args: Dict[str, Any]) -> None:
        """记录工具调用"""
        if self._is_todo_tool(tool_name):
            self._logger.debug(f"📋 [任务层] 工具调用: {tool_name}({args})")
            
            event_type = self._get_todo_event_type(tool_name)
            self._log_event(TaskEvent(
                event_type=f"tool.{event_type}",
                content=args.get("tasks") or args.get("task") or args.get("title", ""),
                timestamp=datetime.now().isoformat()
            ))
    
    def log_tool_result(self, tool_name: str, result: Any) -> None:
        """记录工具结果"""
        if self._is_todo_tool(tool_name):
            self._logger.debug(f"📋 [任务层] 工具结果: {tool_name} -> {str(result)[:100]}")
            
            event_type = self._get_todo_event_type(tool_name)
            self._log_event(TaskEvent(
                event_type=f"tool.{event_type}.result",
                result=str(result)[:200] if result else None,
                timestamp=datetime.now().isoformat()
            ))
            
            if "list" in tool_name.lower() or "create" in tool_name.lower():
                tasks = self._toolkit.load_tasks()
                self._log_event(TaskEvent(
                    event_type="todo.updated",
                    status="updated",
                    timestamp=datetime.now().isoformat()
                ))
                for task in tasks:
                    self._task_logger.debug(
                        f"📋 [任务层] 任务 #{task.id}: [{task.status.value}] {task.content}"
                    )
    
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
            return "📋 暂无任务"
        
        completed = stats["completed"] + stats["cancelled"]
        progress = (completed / total) * 100
        
        return (
            f"📋 任务进度: {completed}/{total} "
            f"({progress:.0f}%) "
            f"[✅{stats['completed']} ❌{stats['cancelled']} ⏳{stats['waiting']} 🔄{stats['running']}]"
        )


class TaskCheckpoint:
    """
    任务检查点
    
    用于在关键操作前后的 checkpoint 包装
    """
    
    def __init__(self, rail: TaskEventRail, checkpoint_name: str):
        self.rail = rail
        self.checkpoint_name = checkpoint_name
        self._entered = False
    
    async def __aenter__(self) -> "TaskCheckpoint":
        """进入检查点"""
        self._entered = True
        self.rail._logger.debug(f"📋 [任务层] 进入检查点: {self.checkpoint_name}")
        await self.rail.wait_for_checkpoint()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """退出检查点"""
        if exc_type is asyncio.CancelledError:
            self.rail._logger.warning(f"📋 [任务层] 检查点 {self.checkpoint_name} 被中断")
            raise
        self.rail._logger.debug(f"📋 [任务层] 退出检查点: {self.checkpoint_name}")
    
    def checkpoint(self, name: str) -> "TaskCheckpoint":
        """创建子检查点"""
        return TaskCheckpoint(self.rail, f"{self.checkpoint_name}/{name}")


# 全局 Rail 实例管理
_rails: Dict[str, TaskEventRail] = {}
_rails_lock = threading.Lock()


def get_task_rail(session_id: str) -> TaskEventRail:
    """获取 TaskEventRail 实例"""
    if session_id not in _rails:
        with _rails_lock:
            if session_id not in _rails:
                _rails[session_id] = TaskEventRail(session_id)
    return _rails[session_id]


def reset_task_rail(session_id: str) -> None:
    """重置 TaskEventRail 实例"""
    if session_id in _rails:
        with _rails_lock:
            if session_id in _rails:
                rail = _rails[session_id]
                rail.abort()
                del _rails[session_id]
