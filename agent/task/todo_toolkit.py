#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Todo Toolkit - 任务管理工具包
参考 JiuwenSwarm 的 TodoToolkit 实现

提供任务列表管理功能：
- 创建任务列表
- 添加/插入任务
- 完成任务
- 删除任务
- 列出任务
"""

import os
import json
import threading
import re
from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path


class TaskStatus(str, Enum):
    """任务状态枚举"""
    WAITING = "waiting"       # 待执行
    RUNNING = "running"       # 执行中
    COMPLETED = "completed"   # 已完成
    CANCELLED = "cancelled"  # 已取消


@dataclass
class Task:
    """任务数据类"""
    id: int
    content: str
    status: TaskStatus = TaskStatus.WAITING
    result: Optional[str] = None
    created_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "status": self.status.value if isinstance(self.status, TaskStatus) else self.status,
            "result": self.result,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        status = data.get("status", "waiting")
        if isinstance(status, str):
            status = TaskStatus(status)
        return cls(
            id=data["id"],
            content=data["content"],
            status=status,
            result=data.get("result"),
            created_at=data.get("created_at")
        )


class TodoToolkit:
    """
    任务工具包
    将任务列表持久化到 Markdown 文件
    支持按 session 分组的文件锁
    """
    
    TODO_FILENAME = "todo.md"
    TODO_JSON_FILENAME = "todo.json"
    
    _session_locks: Dict[str, threading.Lock] = {}
    _lock_for_locks = threading.Lock()
    
    def __init__(self, workspace_dir: Optional[str] = None):
        self.workspace_dir = workspace_dir or self._get_default_workspace()
        self.session_id: Optional[str] = None
        self._lock = self._get_lock()
    
    @staticmethod
    def _get_default_workspace() -> str:
        """获取默认工作目录"""
        home = os.path.expanduser("~")
        return os.path.join(home, ".handsome-agent")
    
    def _get_lock(self) -> threading.Lock:
        """获取 session 对应的锁"""
        if self.session_id not in TodoToolkit._session_locks:
            with TodoToolkit._lock_for_locks:
                if self.session_id not in TodoToolkit._session_locks:
                    TodoToolkit._session_locks[self.session_id] = threading.Lock()
        return TodoToolkit._session_locks[self.session_id]
    
    def _get_session_dir(self) -> Path:
        """获取 session 对应的目录"""
        if not self.session_id:
            raise ValueError("session_id not set")
        session_dir = Path(self.workspace_dir) / "sessions" / self.session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir
    
    def _get_todo_path(self) -> Path:
        """获取 todo.md 路径"""
        return self._get_session_dir() / self.TODO_FILENAME
    
    def _get_todo_json_path(self) -> Path:
        """获取 todo.json 路径"""
        return self._get_session_dir() / self.TODO_JSON_FILENAME
    
    def set_session(self, session_id: str) -> None:
        """设置当前 session"""
        self.session_id = session_id
        self._lock = self._get_lock()
    
    def load_tasks(self) -> List[Task]:
        """从文件加载任务列表"""
        json_path = self._get_todo_json_path()
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [Task.from_dict(t) for t in data]
        return []
    
    def save_tasks(self, tasks: List[Task]) -> None:
        """保存任务列表到文件"""
        json_path = self._get_todo_json_path()
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump([t.to_dict() for t in tasks], f, ensure_ascii=False, indent=2)
        
        md_path = self._get_todo_path()
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write("# Todo List\n\n")
            for task in tasks:
                status_icon = self._get_status_icon(task.status)
                content = task.content
                if task.result:
                    content += f" | {task.result}"
                f.write(f"- {status_icon} {task.id}. {content}\n")
    
    def _get_status_icon(self, status: TaskStatus) -> str:
        """获取状态图标"""
        icons = {
            TaskStatus.WAITING: "[ ]",
            TaskStatus.RUNNING: "[~]",
            TaskStatus.COMPLETED: "[x]",
            TaskStatus.CANCELLED: "[-]"
        }
        return icons.get(status, "[ ]")
    
    def todo_create(self, tasks: List[str]) -> str:
        """
        创建初始任务列表
        
        Args:
            tasks: 任务描述列表
            
        Returns:
            创建结果描述
        """
        with self._lock:
            existing = self.load_tasks()
            if existing:
                return f"任务列表已存在 ({len(existing)} 个任务)，请使用 todo_add 添加任务"
            
            created_tasks = []
            for i, content in enumerate(tasks, 1):
                task = Task(
                    id=i,
                    content=content,
                    status=TaskStatus.WAITING,
                    created_at=datetime.now().isoformat()
                )
                created_tasks.append(task)
            
            self.save_tasks(created_tasks)
            return f"已创建 {len(created_tasks)} 个任务:\n" + "\n".join(
                f"  {i}. {t}" for i, t in enumerate(tasks, 1)
            )
    
    def todo_add(self, task: str, index: Optional[int] = None) -> str:
        """
        添加任务到列表
        
        Args:
            task: 任务描述
            index: 插入位置，None 表示追加到末尾
            
        Returns:
            添加结果描述
        """
        with self._lock:
            tasks = self.load_tasks()
            
            if index is None or index >= len(tasks):
                new_id = max([t.id for t in tasks], default=0) + 1
                new_task = Task(
                    id=new_id,
                    content=task,
                    status=TaskStatus.WAITING,
                    created_at=datetime.now().isoformat()
                )
                tasks.append(new_task)
            else:
                new_id = max([t.id for t in tasks], default=0) + 1
                new_task = Task(
                    id=new_id,
                    content=task,
                    status=TaskStatus.WAITING,
                    created_at=datetime.now().isoformat()
                )
                tasks.insert(index, new_task)
                for i, t in enumerate(tasks, 1):
                    t.id = i
            
            self.save_tasks(tasks)
            return f"已添加任务 #{new_id}: {task}"
    
    def todo_complete(self, task_id: int, result: Optional[str] = None) -> str:
        """
        完成任务
        
        Args:
            task_id: 任务 ID
            result: 任务结果
            
        Returns:
            完成结果描述
        """
        with self._lock:
            tasks = self.load_tasks()
            
            for task in tasks:
                if task.id == task_id:
                    task.status = TaskStatus.COMPLETED
                    task.result = result
                    self.save_tasks(tasks)
                    
                    pending = [t for t in tasks if t.status == TaskStatus.WAITING]
                    if pending:
                        return f"任务 #{task_id} 已完成！\n当前还有 {len(pending)} 个待处理任务"
                    else:
                        return f"🎉 所有任务已完成！"
            
            return f"任务 #{task_id} 未找到"
    
    def todo_cancel(self, task_id: int, reason: Optional[str] = None) -> str:
        """
        取消任务
        
        Args:
            task_id: 任务 ID
            reason: 取消原因
            
        Returns:
            取消结果描述
        """
        with self._lock:
            tasks = self.load_tasks()
            
            for task in tasks:
                if task.id == task_id:
                    task.status = TaskStatus.CANCELLED
                    task.result = reason or "已取消"
                    self.save_tasks(tasks)
                    
                    pending = [t for t in tasks if t.status == TaskStatus.WAITING]
                    if pending:
                        return f"任务 #{task_id} 已取消\n当前还有 {len(pending)} 个待处理任务"
                    else:
                        return f"任务 #{task_id} 已取消，所有任务已处理完毕"
            
            return f"任务 #{task_id} 未找到"
    
    def todo_remove(self, task_id: int) -> str:
        """
        删除任务
        
        Args:
            task_id: 任务 ID
            
        Returns:
            删除结果描述
        """
        with self._lock:
            tasks = self.load_tasks()
            
            tasks = [t for t in tasks if t.id != task_id]
            for i, t in enumerate(tasks, 1):
                t.id = i
            
            self.save_tasks(tasks)
            return f"任务 #{task_id} 已删除，剩余 {len(tasks)} 个任务"
    
    def todo_list(self) -> str:
        """
        列出所有任务
        
        Returns:
            任务列表格式化字符串
        """
        with self._lock:
            tasks = self.load_tasks()
            
            if not tasks:
                return "暂无任务列表"
            
            lines = [f"# Todo List ({len(tasks)} 个任务)\n"]
            
            waiting = [t for t in tasks if t.status == TaskStatus.WAITING]
            running = [t for t in tasks if t.status == TaskStatus.RUNNING]
            completed = [t for t in tasks if t.status == TaskStatus.COMPLETED]
            cancelled = [t for t in tasks if t.status == TaskStatus.CANCELLED]
            
            if waiting:
                lines.append("## ⏳ 待处理")
                for t in waiting:
                    lines.append(f"- [ ] {t.id}. {t.content}")
            
            if running:
                lines.append("\n## 🔄 进行中")
                for t in running:
                    lines.append(f"- [~] {t.id}. {t.content}")
                    if t.result:
                        lines.append(f"  结果: {t.result}")
            
            if completed:
                lines.append("\n## ✅ 已完成")
                for t in completed:
                    lines.append(f"- [x] {t.id}. {t.content}")
                    if t.result:
                        lines.append(f"  结果: {t.result}")
            
            if cancelled:
                lines.append("\n## ❌ 已取消")
                for t in cancelled:
                    lines.append(f"- [-] {t.id}. {t.content}")
                    if t.result:
                        lines.append(f"  原因: {t.result}")
            
            return "\n".join(lines)
    
    def todo_clear(self) -> str:
        """
        清空任务列表
        
        Returns:
            清空结果描述
        """
        with self._lock:
            tasks = self.load_tasks()
            count = len(tasks)
            self.save_tasks([])
            return f"已清空 {count} 个任务"
    
    def todo_reset(self) -> str:
        """
        重置任务列表（清空已完成的任务）
        
        Returns:
            重置结果描述
        """
        with self._lock:
            tasks = self.load_tasks()
            active = [t for t in tasks if t.status in [TaskStatus.WAITING, TaskStatus.RUNNING]]
            
            completed_count = len(tasks) - len(active)
            
            for i, t in enumerate(active, 1):
                t.id = i
            
            self.save_tasks(active)
            
            if completed_count > 0:
                return f"已重置任务列表，移除了 {completed_count} 个已完成任务，剩余 {len(active)} 个活跃任务"
            else:
                return "任务列表已是最新状态"


class TaskEvent:
    """任务事件"""
    
    def __init__(
        self,
        event_type: str,
        task_id: Optional[int] = None,
        content: Optional[str] = None,
        status: Optional[str] = None,
        result: Optional[str] = None,
        timestamp: Optional[str] = None
    ):
        self.event_type = event_type
        self.task_id = task_id
        self.content = content
        self.status = status
        self.result = result
        self.timestamp = timestamp or datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "type": self.event_type,
            "task_id": self.task_id,
            "content": self.content,
            "status": self.status,
            "result": self.result
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


class TaskEventLog:
    """任务事件日志"""
    
    def __init__(self, session_id: str, workspace_dir: Optional[str] = None):
        self.session_id = session_id
        self.workspace_dir = workspace_dir or TodoToolkit._get_default_workspace()
        self._log_path = Path(self.workspace_dir) / "sessions" / session_id / "task_events.jsonl"
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def log(self, event: TaskEvent) -> None:
        """记录事件"""
        with open(self._log_path, 'a', encoding='utf-8') as f:
            f.write(event.to_json() + "\n")
    
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


# 全局 TodoToolkit 实例（按 session 管理）
_todo_instances: Dict[str, TodoToolkit] = {}
_instance_lock = threading.Lock()


def get_todo_toolkit(session_id: str, workspace_dir: Optional[str] = None) -> TodoToolkit:
    """获取 TodoToolkit 实例"""
    if session_id not in _todo_instances:
        with _instance_lock:
            if session_id not in _todo_instances:
                toolkit = TodoToolkit(workspace_dir)
                toolkit.set_session(session_id)
                _todo_instances[session_id] = toolkit
    return _todo_instances[session_id]


def reset_todo_toolkit(session_id: str) -> None:
    """重置 TodoToolkit 实例"""
    if session_id in _todo_instances:
        with _instance_lock:
            if session_id in _todo_instances:
                del _todo_instances[session_id]
