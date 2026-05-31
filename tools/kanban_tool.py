#!/usr/bin/env python3
"""
Kanban Tool Module - 看板工具

提供看板/任务管理功能：
- 看板创建和管理
- 任务状态流转
- 任务优先级管理

参考 Hermes Agent 的 kanban_tools.py 实现。

Usage:
    from tools.kanban_tool import kanban_create_board, kanban_add_task
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.registry import registry

logger = logging.getLogger(__name__)


class KanbanBoard:
    """看板类"""
    
    def __init__(self, name: str):
        self.id = str(uuid.uuid4())
        self.name = name
        self.created_at = datetime.now().isoformat()
        self.columns = [
            {"id": "todo", "name": "待办", "tasks": []},
            {"id": "in_progress", "name": "进行中", "tasks": []},
            {"id": "done", "name": "已完成", "tasks": []},
        ]
    
    def add_task(
        self,
        title: str,
        description: Optional[str] = None,
        priority: str = "medium",
        column_id: str = "todo",
    ) -> str:
        """添加任务"""
        task_id = str(uuid.uuid4())
        task = {
            "id": task_id,
            "title": title,
            "description": description or "",
            "priority": priority,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        
        for column in self.columns:
            if column["id"] == column_id:
                column["tasks"].append(task)
                break
        
        return task_id
    
    def move_task(self, task_id: str, target_column_id: str) -> bool:
        """移动任务"""
        task = None
        source_column = None
        
        # 找到任务
        for column in self.columns:
            for i, t in enumerate(column["tasks"]):
                if t["id"] == task_id:
                    task = column["tasks"].pop(i)
                    source_column = column
                    break
            if task:
                break
        
        if not task:
            return False
        
        # 移动到目标列
        for column in self.columns:
            if column["id"] == target_column_id:
                task["updated_at"] = datetime.now().isoformat()
                column["tasks"].append(task)
                return True
        
        return False
    
    def update_task(
        self,
        task_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> bool:
        """更新任务"""
        for column in self.columns:
            for task in column["tasks"]:
                if task["id"] == task_id:
                    if title is not None:
                        task["title"] = title
                    if description is not None:
                        task["description"] = description
                    if priority is not None:
                        task["priority"] = priority
                    task["updated_at"] = datetime.now().isoformat()
                    return True
        return False
    
    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        for column in self.columns:
            for i, task in enumerate(column["tasks"]):
                if task["id"] == task_id:
                    column["tasks"].pop(i)
                    return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at,
            "columns": self.columns,
        }


class KanbanManager:
    """看板管理器"""
    
    def __init__(self):
        self._boards: Dict[str, KanbanBoard] = {}
        self._storage_path = Path.home() / ".handsome_agent" / "kanban_boards.json"
        self._load_boards()
    
    def _load_boards(self):
        """加载看板"""
        if self._storage_path.exists():
            try:
                with open(self._storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for board_data in data.get("boards", []):
                        board = KanbanBoard(board_data["name"])
                        board.id = board_data["id"]
                        board.created_at = board_data["created_at"]
                        board.columns = board_data["columns"]
                        self._boards[board.id] = board
            except Exception as e:
                logger.error(f"加载看板失败: {e}")
    
    def _save_boards(self):
        """保存看板"""
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = {
                "boards": [board.to_dict() for board in self._boards.values()],
            }
            with open(self._storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存看板失败: {e}")
    
    def create_board(self, name: str) -> str:
        """创建看板"""
        board = KanbanBoard(name)
        self._boards[board.id] = board
        self._save_boards()
        logger.info(f"创建看板: {name}")
        return board.id
    
    def delete_board(self, board_id: str) -> bool:
        """删除看板"""
        if board_id in self._boards:
            del self._boards[board_id]
            self._save_boards()
            logger.info(f"删除看板: {board_id}")
            return True
        return False
    
    def get_board(self, board_id: str) -> Optional[KanbanBoard]:
        """获取看板"""
        return self._boards.get(board_id)
    
    def list_boards(self) -> List[Dict[str, Any]]:
        """列出所有看板"""
        return [
            {
                "id": board.id,
                "name": board.name,
                "created_at": board.created_at,
                "task_count": sum(len(col["tasks"]) for col in board.columns),
            }
            for board in self._boards.values()
        ]


# 全局管理器实例
_kanban_manager = KanbanManager()


def kanban_create_board(name: str) -> str:
    """
    创建看板。
    
    Args:
        name: 看板名称
    
    Returns:
        JSON 格式的结果字符串
    """
    board_id = _kanban_manager.create_board(name)
    
    result = {
        "success": True,
        "board_id": board_id,
        "name": name,
        "message": f"看板已创建: {name}",
    }
    
    return json.dumps(result, ensure_ascii=False)


def kanban_delete_board(board_id: str) -> str:
    """
    删除看板。
    
    Args:
        board_id: 看板ID
    
    Returns:
        JSON 格式的结果字符串
    """
    success = _kanban_manager.delete_board(board_id)
    
    if success:
        result = {
            "success": True,
            "message": "看板已删除",
        }
    else:
        result = {
            "success": False,
            "error": f"看板不存在: {board_id}",
        }
    
    return json.dumps(result, ensure_ascii=False)


def kanban_list_boards() -> str:
    """
    列出所有看板。
    
    Returns:
        JSON 格式的结果字符串
    """
    boards = _kanban_manager.list_boards()
    
    result = {
        "success": True,
        "boards": boards,
        "total": len(boards),
    }
    
    return json.dumps(result, ensure_ascii=False)


def kanban_add_task(
    board_id: str,
    title: str,
    description: Optional[str] = None,
    priority: str = "medium",
    column_id: str = "todo",
) -> str:
    """
    添加任务到看板。
    
    Args:
        board_id: 看板ID
        title: 任务标题
        description: 可选的任务描述
        priority: 优先级 (low, medium, high)
        column_id: 目标列ID (todo, in_progress, done)
    
    Returns:
        JSON 格式的结果字符串
    """
    board = _kanban_manager.get_board(board_id)
    
    if not board:
        result = {
            "success": False,
            "error": f"看板不存在: {board_id}",
        }
        return json.dumps(result, ensure_ascii=False)
    
    task_id = board.add_task(title, description, priority, column_id)
    _kanban_manager._save_boards()
    
    result = {
        "success": True,
        "task_id": task_id,
        "title": title,
        "message": f"任务已添加: {title}",
    }
    
    return json.dumps(result, ensure_ascii=False)


def kanban_move_task(
    board_id: str,
    task_id: str,
    target_column_id: str,
) -> str:
    """
    移动任务到另一列。
    
    Args:
        board_id: 看板ID
        task_id: 任务ID
        target_column_id: 目标列ID
    
    Returns:
        JSON 格式的结果字符串
    """
    board = _kanban_manager.get_board(board_id)
    
    if not board:
        result = {
            "success": False,
            "error": f"看板不存在: {board_id}",
        }
        return json.dumps(result, ensure_ascii=False)
    
    success = board.move_task(task_id, target_column_id)
    
    if success:
        _kanban_manager._save_boards()
        result = {
            "success": True,
            "message": f"任务已移动到: {target_column_id}",
        }
    else:
        result = {
            "success": False,
            "error": f"任务不存在: {task_id}",
        }
    
    return json.dumps(result, ensure_ascii=False)


def kanban_update_task(
    board_id: str,
    task_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    priority: Optional[str] = None,
) -> str:
    """
    更新任务。
    
    Args:
        board_id: 看板ID
        task_id: 任务ID
        title: 可选的新标题
        description: 可选的新描述
        priority: 可选的新优先级
    
    Returns:
        JSON 格式的结果字符串
    """
    board = _kanban_manager.get_board(board_id)
    
    if not board:
        result = {
            "success": False,
            "error": f"看板不存在: {board_id}",
        }
        return json.dumps(result, ensure_ascii=False)
    
    success = board.update_task(task_id, title, description, priority)
    
    if success:
        _kanban_manager._save_boards()
        result = {
            "success": True,
            "message": "任务已更新",
        }
    else:
        result = {
            "success": False,
            "error": f"任务不存在: {task_id}",
        }
    
    return json.dumps(result, ensure_ascii=False)


def kanban_delete_task(
    board_id: str,
    task_id: str,
) -> str:
    """
    删除任务。
    
    Args:
        board_id: 看板ID
        task_id: 任务ID
    
    Returns:
        JSON 格式的结果字符串
    """
    board = _kanban_manager.get_board(board_id)
    
    if not board:
        result = {
            "success": False,
            "error": f"看板不存在: {board_id}",
        }
        return json.dumps(result, ensure_ascii=False)
    
    success = board.delete_task(task_id)
    
    if success:
        _kanban_manager._save_boards()
        result = {
            "success": True,
            "message": "任务已删除",
        }
    else:
        result = {
            "success": False,
            "error": f"任务不存在: {task_id}",
        }
    
    return json.dumps(result, ensure_ascii=False)


def kanban_view_board(board_id: str) -> str:
    """
    查看看板详情。
    
    Args:
        board_id: 看板ID
    
    Returns:
        JSON 格式的结果字符串
    """
    board = _kanban_manager.get_board(board_id)
    
    if not board:
        result = {
            "success": False,
            "error": f"看板不存在: {board_id}",
        }
        return json.dumps(result, ensure_ascii=False)
    
    result = {
        "success": True,
        "board": board.to_dict(),
    }
    
    return json.dumps(result, ensure_ascii=False)


def check_kanban_requirements() -> bool:
    """看板工具无外部依赖，始终可用"""
    return True


# 工具定义
KANBAN_CREATE_BOARD_SCHEMA = {
    "name": "kanban_create_board",
    "description": "Create a new kanban board for task management.",
    "parameters": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Name of the kanban board.",
            },
        },
        "required": ["name"],
    },
}


KANBAN_DELETE_BOARD_SCHEMA = {
    "name": "kanban_delete_board",
    "description": "Delete a kanban board.",
    "parameters": {
        "type": "object",
        "properties": {
            "board_id": {
                "type": "string",
                "description": "ID of the board to delete.",
            },
        },
        "required": ["board_id"],
    },
}


KANBAN_LIST_BOARDS_SCHEMA = {
    "name": "kanban_list_boards",
    "description": "List all kanban boards.",
    "parameters": {
        "type": "object",
        "properties": {},
    },
}


KANBAN_ADD_TASK_SCHEMA = {
    "name": "kanban_add_task",
    "description": "Add a task to a kanban board.",
    "parameters": {
        "type": "object",
        "properties": {
            "board_id": {
                "type": "string",
                "description": "ID of the board.",
            },
            "title": {
                "type": "string",
                "description": "Task title.",
            },
            "description": {
                "type": "string",
                "description": "Optional task description.",
            },
            "priority": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "default": "medium",
                "description": "Task priority (low, medium, high).",
            },
            "column_id": {
                "type": "string",
                "enum": ["todo", "in_progress", "done"],
                "default": "todo",
                "description": "Column to add the task to (todo, in_progress, done).",
            },
        },
        "required": ["board_id", "title"],
    },
}


KANBAN_MOVE_TASK_SCHEMA = {
    "name": "kanban_move_task",
    "description": "Move a task to a different column on the board.",
    "parameters": {
        "type": "object",
        "properties": {
            "board_id": {
                "type": "string",
                "description": "ID of the board.",
            },
            "task_id": {
                "type": "string",
                "description": "ID of the task to move.",
            },
            "target_column_id": {
                "type": "string",
                "enum": ["todo", "in_progress", "done"],
                "description": "Target column ID (todo, in_progress, done).",
            },
        },
        "required": ["board_id", "task_id", "target_column_id"],
    },
}


KANBAN_UPDATE_TASK_SCHEMA = {
    "name": "kanban_update_task",
    "description": "Update a task's details.",
    "parameters": {
        "type": "object",
        "properties": {
            "board_id": {
                "type": "string",
                "description": "ID of the board.",
            },
            "task_id": {
                "type": "string",
                "description": "ID of the task to update.",
            },
            "title": {
                "type": "string",
                "description": "Optional new title for the task.",
            },
            "description": {
                "type": "string",
                "description": "Optional new description for the task.",
            },
            "priority": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "description": "Optional new priority for the task.",
            },
        },
        "required": ["board_id", "task_id"],
    },
}


KANBAN_DELETE_TASK_SCHEMA = {
    "name": "kanban_delete_task",
    "description": "Delete a task from the board.",
    "parameters": {
        "type": "object",
        "properties": {
            "board_id": {
                "type": "string",
                "description": "ID of the board.",
            },
            "task_id": {
                "type": "string",
                "description": "ID of the task to delete.",
            },
        },
        "required": ["board_id", "task_id"],
    },
}


KANBAN_VIEW_BOARD_SCHEMA = {
    "name": "kanban_view_board",
    "description": "View the full details of a kanban board.",
    "parameters": {
        "type": "object",
        "properties": {
            "board_id": {
                "type": "string",
                "description": "ID of the board to view.",
            },
        },
        "required": ["board_id"],
    },
}


# 注册工具
registry.register(
    name="kanban_create_board",
    toolset="kanban",
    schema=KANBAN_CREATE_BOARD_SCHEMA,
    handler=lambda args, **kw: kanban_create_board(args.get("name", "")),
    check_fn=check_kanban_requirements,
    emoji="📋",
)


registry.register(
    name="kanban_delete_board",
    toolset="kanban",
    schema=KANBAN_DELETE_BOARD_SCHEMA,
    handler=lambda args, **kw: kanban_delete_board(args.get("board_id", "")),
    check_fn=check_kanban_requirements,
    emoji="🗑️",
)


registry.register(
    name="kanban_list_boards",
    toolset="kanban",
    schema=KANBAN_LIST_BOARDS_SCHEMA,
    handler=lambda args, **kw: kanban_list_boards(),
    check_fn=check_kanban_requirements,
    emoji="📋",
)


registry.register(
    name="kanban_add_task",
    toolset="kanban",
    schema=KANBAN_ADD_TASK_SCHEMA,
    handler=lambda args, **kw: kanban_add_task(
        board_id=args.get("board_id", ""),
        title=args.get("title", ""),
        description=args.get("description"),
        priority=args.get("priority", "medium"),
        column_id=args.get("column_id", "todo"),
    ),
    check_fn=check_kanban_requirements,
    emoji="➕",
)


registry.register(
    name="kanban_move_task",
    toolset="kanban",
    schema=KANBAN_MOVE_TASK_SCHEMA,
    handler=lambda args, **kw: kanban_move_task(
        board_id=args.get("board_id", ""),
        task_id=args.get("task_id", ""),
        target_column_id=args.get("target_column_id", ""),
    ),
    check_fn=check_kanban_requirements,
    emoji="➡️",
)


registry.register(
    name="kanban_update_task",
    toolset="kanban",
    schema=KANBAN_UPDATE_TASK_SCHEMA,
    handler=lambda args, **kw: kanban_update_task(
        board_id=args.get("board_id", ""),
        task_id=args.get("task_id", ""),
        title=args.get("title"),
        description=args.get("description"),
        priority=args.get("priority"),
    ),
    check_fn=check_kanban_requirements,
    emoji="✏️",
)


registry.register(
    name="kanban_delete_task",
    toolset="kanban",
    schema=KANBAN_DELETE_TASK_SCHEMA,
    handler=lambda args, **kw: kanban_delete_task(
        board_id=args.get("board_id", ""),
        task_id=args.get("task_id", ""),
    ),
    check_fn=check_kanban_requirements,
    emoji="🗑️",
)


registry.register(
    name="kanban_view_board",
    toolset="kanban",
    schema=KANBAN_VIEW_BOARD_SCHEMA,
    handler=lambda args, **kw: kanban_view_board(args.get("board_id", "")),
    check_fn=check_kanban_requirements,
    emoji="👁️",
)
