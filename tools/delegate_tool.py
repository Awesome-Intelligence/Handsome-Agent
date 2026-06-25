#!/usr/bin/env python3
"""
Delegate Tool Module

Provides task delegation functionality:
- Subtask creation and management
- Concurrent task execution
- Task result aggregation

Based on Hermes Agent's delegate_tool.py implementation.

Usage:
    from tools.delegate_tool import delegate_subtask, delegate_batch
"""

import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime

from common.logging_manager import get_execution_logger
from tools.registry import registry

logger = get_execution_logger("DelegateTool")


class SubtaskState:
    """子任务状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class DelegateManager:
    """代理管理器 - 管理子代理任务"""
    
    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
    
    async def create_task(
        self,
        task_description: str,
        context: Optional[str] = None,
        constraints: Optional[str] = None,
        parent_task_id: Optional[str] = None,
    ) -> str:
        """创建新的子代理任务"""
        task_id = str(uuid.uuid4())
        
        async with self._lock:
            self._tasks[task_id] = {
                "id": task_id,
                "description": task_description,
                "context": context or "",
                "constraints": constraints or "",
                "parent_task_id": parent_task_id,
                "state": SubtaskState.PENDING,
                "result": None,
                "error": None,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
        
        logger.info(f"创建子任务: {task_id} - {task_description}")
        return task_id
    
    async def update_task_state(
        self,
        task_id: str,
        state: str,
        result: Optional[Any] = None,
        error: Optional[str] = None,
    ):
        """更新任务状态"""
        async with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id]["state"] = state
                self._tasks[task_id]["updated_at"] = datetime.now().isoformat()
                if result is not None:
                    self._tasks[task_id]["result"] = result
                if error is not None:
                    self._tasks[task_id]["error"] = error
    
    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务详情"""
        async with self._lock:
            return self._tasks.get(task_id)
    
    async def list_tasks(self, parent_task_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出所有任务"""
        async with self._lock:
            if parent_task_id:
                return [
                    t for t in self._tasks.values()
                    if t["parent_task_id"] == parent_task_id
                ]
            return list(self._tasks.values())


# 全局管理器实例
_delegate_manager = DelegateManager()


def _run_async(coro):
    """在同步函数中安全地运行协程，支持已存在事件循环的场景"""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # 没有正在运行的事件循环，使用 asyncio.run()
        return asyncio.run(coro)
    else:
        # 已经在事件循环中，创建 Task
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()


def delegate_subtask(
    task: str,
    context: Optional[str] = None,
    constraints: Optional[str] = None,
) -> str:
    """
    代理单个子任务。
    
    Args:
        task: 子任务描述
        context: 可选的上下文信息
        constraints: 可选的约束条件
    
    Returns:
        JSON 格式的结果字符串
    """
    # 注意：这里只是模拟实现，真实的子代理需要完整的架构支持
    # 当前版本将返回一个模拟的任务创建结果
    
    task_id = asyncio.run(_delegate_manager.create_task(task, context, constraints))
    
    result = {
        "success": True,
        "task_id": task_id,
        "message": "子任务已创建",
        "note": "这是一个模拟实现。完整的子代理功能需要额外的架构支持。",
    }
    
    return json.dumps(result, ensure_ascii=False)


def delegate_batch(
    tasks: List[Dict[str, Any]],
    max_concurrent: int = 3,
) -> str:
    """
    代理批量任务。
    
    Args:
        tasks: 任务列表，每个任务包含 task, context, constraints
        max_concurrent: 最大并发数
    
    Returns:
        JSON 格式的结果字符串
    """
    task_ids = []
    
    for task_info in tasks:
        task_id = asyncio.run(_delegate_manager.create_task(
            task_info.get("task", ""),
            task_info.get("context"),
            task_info.get("constraints"),
        ))
        task_ids.append(task_id)
    
    result = {
        "success": True,
        "task_ids": task_ids,
        "total_tasks": len(task_ids),
        "max_concurrent": max_concurrent,
        "message": "批量任务已创建",
        "note": "这是一个模拟实现。完整的子代理功能需要额外的架构支持。",
    }
    
    return json.dumps(result, ensure_ascii=False)


def get_subtask_status(task_id: str) -> str:
    """
    获取子任务状态。
    
    Args:
        task_id: 任务ID
    
    Returns:
        JSON 格式的结果字符串
    """
    task = asyncio.run(_delegate_manager.get_task(task_id))
    
    if task:
        result = {
            "success": True,
            "task": task,
        }
    else:
        result = {
            "success": False,
            "error": f"任务未找到: {task_id}",
        }
    
    return json.dumps(result, ensure_ascii=False)


def list_subtasks(parent_task_id: Optional[str] = None) -> str:
    """
    列出所有子任务。
    
    Args:
        parent_task_id: 可选的父任务ID
    
    Returns:
        JSON 格式的结果字符串
    """
    tasks = _run_async(_delegate_manager.list_tasks(parent_task_id))
    
    result = {
        "success": True,
        "tasks": tasks,
        "total": len(tasks),
    }
    
    return json.dumps(result, ensure_ascii=False)


def check_delegate_requirements() -> bool:
    """代理工具无外部依赖，始终可用"""
    return True


# 工具定义
DELEGATE_SUBTASK_SCHEMA = {
    "name": "delegate_subtask",
    "description": (
        "Delegate a subtask to a subagent. Use this for breaking down complex tasks "
        "into smaller, independent pieces that can be worked on in parallel or sequentially. "
        "Each subagent operates with its own context and focus."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "The subtask description (what the subagent should do)."
            },
            "context": {
                "type": "string",
                "description": "Optional context information the subagent should know."
            },
            "constraints": {
                "type": "string",
                "description": "Optional constraints or requirements for the subtask."
            },
        },
        "required": ["task"],
    },
}


DELEGATE_BATCH_SCHEMA = {
    "name": "delegate_batch",
    "description": (
        "Delegate multiple subtasks at once for parallel or sequential execution. "
        "This is useful when you have multiple independent tasks that can be worked on concurrently."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "tasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string"},
                        "context": {"type": "string"},
                        "constraints": {"type": "string"},
                    },
                    "required": ["task"],
                },
                "description": "List of subtasks to delegate."
            },
            "max_concurrent": {
                "type": "integer",
                "default": 3,
                "description": "Maximum number of concurrent subagents (default: 3)."
            },
        },
        "required": ["tasks"],
    },
}


GET_SUBTASK_STATUS_SCHEMA = {
    "name": "get_subtask_status",
    "description": "Get the status and result of a subtask.",
    "parameters": {
        "type": "object",
        "properties": {
            "task_id": {
                "type": "string",
                "description": "The ID of the subtask to check."
            },
        },
        "required": ["task_id"],
    },
}


LIST_SUBTASKS_SCHEMA = {
    "name": "list_subtasks",
    "description": "List all subtasks, optionally filtered by parent task ID.",
    "parameters": {
        "type": "object",
        "properties": {
            "parent_task_id": {
                "type": "string",
                "description": "Optional parent task ID to filter by."
            },
        },
    },
}


# 注册工具
registry.register(
    name="delegate_subtask",
    toolset="delegate",
    schema=DELEGATE_SUBTASK_SCHEMA,
    handler=lambda args, **kw: delegate_subtask(
        task=args.get("task", ""),
        context=args.get("context"),
        constraints=args.get("constraints"),
    ),
    check_fn=check_delegate_requirements,
    emoji="🤖",
)


registry.register(
    name="delegate_batch",
    toolset="delegate",
    schema=DELEGATE_BATCH_SCHEMA,
    handler=lambda args, **kw: delegate_batch(
        tasks=args.get("tasks", []),
        max_concurrent=args.get("max_concurrent", 3),
    ),
    check_fn=check_delegate_requirements,
    emoji="📦",
)


registry.register(
    name="get_subtask_status",
    toolset="delegate",
    schema=GET_SUBTASK_STATUS_SCHEMA,
    handler=lambda args, **kw: get_subtask_status(args.get("task_id", "")),
    check_fn=check_delegate_requirements,
    emoji="📊",
)


registry.register(
    name="list_subtasks",
    toolset="delegate",
    schema=LIST_SUBTASKS_SCHEMA,
    handler=lambda args, **kw: list_subtasks(args.get("parent_task_id")),
    check_fn=check_delegate_requirements,
    emoji="📋",
)
