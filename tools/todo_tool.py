#!/usr/bin/env python3
"""
Todo Tool Module - Planning & Task Management

Layer 1: Todo（工具层）- 会话级任务管理

提供内存任务列表，用于：
- 分解复杂任务
- 跟踪进度
- 会话压缩时保持上下文

状态: pending | in_progress | completed | cancelled

Usage:
    from tools.todo_tool import todo_tool, SessionTodoStore, check_todo_requirements

    store = SessionTodoStore()
    result = todo_tool(todos=[{"id": "1", "content": "Task", "status": "pending"}], store=store)

With Kanban persistence:
    from tools.todo_tool import SessionTodoStore
    from tools.kanban_tool import KanbanManager

    kanban = KanbanManager()
    store = SessionTodoStore(kanban_manager=kanban)
    store.write(todos, persist=True)  # Also persists to Kanban

See also:
- agent/task/__init__.py: 三层任务架构说明
- tools/kanban_tool.py: Layer 2 - 持久化任务管理
- agent/a2a/models.py: Layer 3 - A2A 协议任务
"""

import json
from typing import Dict, Any, List, Optional, TYPE_CHECKING

from common.logging_manager import get_execution_logger

logger = get_execution_logger("todo")

if TYPE_CHECKING:
    from tools.kanban_tool import KanbanManager

VALID_STATUSES = {"pending", "in_progress", "completed", "cancelled"}

# 状态映射：Todo 状态 → Kanban 状态
TODO_TO_KANBAN_STATUS = {
    "pending": "todo",
    "in_progress": "running",
    "completed": "done",
    "cancelled": "done",
}

# 状态映射：Kanban 状态 → Todo 状态
KANBAN_TO_TODO_STATUS = {
    "triage": "pending",
    "todo": "pending",
    "ready": "pending",
    "running": "in_progress",
    "done": "completed",
    "blocked": "in_progress",
}


def tool_error(message: str, success: bool = False) -> str:
    return json.dumps({"success": success, "error": message}, ensure_ascii=False)


class SessionTodoStore:
    def __init__(self, kanban_manager: Optional["KanbanManager"] = None):
        """
        Args:
            kanban_manager: 可选的 KanbanManager 实例，用于持久化
        """
        self._items: List[Dict[str, str]] = []
        self._kanban_manager = kanban_manager
        self._kanban_task_ids: Dict[str, str] = {}  # todo_id -> kanban_task_id

    def set_kanban_manager(self, kanban_manager: "KanbanManager") -> None:
        """设置 KanbanManager 实例"""
        self._kanban_manager = kanban_manager

    def write(
        self,
        todos: List[Dict[str, Any]],
        merge: bool = False,
        persist: bool = False,
    ) -> List[Dict[str, str]]:
        """
        写入任务列表

        Args:
            todos: 任务列表
            merge: 是否合并到现有列表
            persist: 是否同时持久化到 Kanban

        Returns:
            当前任务列表
        """
        if not merge:
            self._items = [self._validate(t) for t in self._dedupe_by_id(todos)]
        else:
            existing = {item["id"]: item for item in self._items}
            for t in self._dedupe_by_id(todos):
                item_id = str(t.get("id", "")).strip()
                if not item_id:
                    continue

                if item_id in existing:
                    if "content" in t and t["content"]:
                        existing[item_id]["content"] = str(t["content"]).strip()
                    if "status" in t and t["status"]:
                        status = str(t["status"]).strip().lower()
                        if status in VALID_STATUSES:
                            existing[item_id]["status"] = status
                else:
                    validated = self._validate(t)
                    existing[validated["id"]] = validated
                    self._items.append(validated)
            seen = set()
            rebuilt = []
            for item in self._items:
                current = existing.get(item["id"], item)
                if current["id"] not in seen:
                    rebuilt.append(current)
                    seen.add(current["id"])
            self._items = rebuilt

        # 持久化到 Kanban
        if persist and self._kanban_manager:
            self._sync_to_kanban()

        final_items = self.read()
        pending = sum(1 for i in final_items if i["status"] == "pending")
        in_progress = sum(1 for i in final_items if i["status"] == "in_progress")
        completed = sum(1 for i in final_items if i["status"] == "completed")
        cancelled = sum(1 for i in final_items if i["status"] == "cancelled")
        
        logger.info(
            f"写入 {len(todos)} 个任务, merge={merge}, persist={persist} | "
            f"结果: {len(final_items)} 个任务 ({completed} 已完成, {in_progress} 进行中, {pending} 待处理, {cancelled} 已取消)"
        )
        logger.debug(f"任务列表: {final_items}")

        return final_items

    def _sync_to_kanban(self) -> None:
        """同步 Todo 到 Kanban"""
        if not self._kanban_manager:
            return

        try:
            board_id = self._kanban_manager.get_default_board_id()
            if not board_id:
                return

            for item in self._items:
                todo_id = item["id"]
                kanban_task_id = self._kanban_task_ids.get(todo_id)

                if kanban_task_id:
                    # 更新现有任务
                    kanban_status = TODO_TO_KANBAN_STATUS.get(item["status"], "todo")
                    self._kanban_manager.update_task(
                        kanban_task_id,
                        title=item["content"],
                        status=kanban_status,
                    )
                else:
                    # 创建新任务
                    kanban_status = TODO_TO_KANBAN_STATUS.get(item["status"], "todo")
                    new_id = self._kanban_manager.create_task(
                        board_id=board_id,
                        title=item["content"],
                        body=f"From Todo: {todo_id}",
                        status=kanban_status,
                        initial_status=kanban_status,
                    )
                    self._kanban_task_ids[todo_id] = new_id
        except Exception:
            # 静默处理持久化错误，避免影响主流程
            pass

    def read(self) -> List[Dict[str, str]]:
        return [item.copy() for item in self._items]

    def has_items(self) -> bool:
        return bool(self._items)

    def format_for_injection(self) -> Optional[str]:
        if not self._items:
            return None

        markers = {
            "completed": "[x]",
            "in_progress": "[>]",
            "pending": "[ ]",
            "cancelled": "[~]",
        }

        active_items = [
            item for item in self._items
            if item["status"] in {"pending", "in_progress"}
        ]
        if not active_items:
            return None

        lines = ["[Your active task list was preserved across context compression]"]
        for item in active_items:
            marker = markers.get(item["status"], "[?]")
            lines.append(f"- {marker} {item['id']}. {item['content']} ({item['status']})")

        return "\n".join(lines)

    def format_for_llm_context(self) -> Optional[str]:
        """
        格式化任务列表用于 LLM 上下文注入。
        
        包含完整的任务状态信息，让 LLM 能够感知任务进度。
        
        Returns:
            格式化的任务列表字符串，或 None（无任务时）
        """
        if not self._items:
            return None

        markers = {
            "completed": "[x]",
            "in_progress": "[>]",
            "pending": "[ ]",
            "cancelled": "[~]",
        }

        completed = []
        in_progress = []
        pending = []
        cancelled = []

        for item in self._items:
            marker = markers.get(item["status"], "[?]")
            line = f"- {marker} {item['id']}. {item['content']}"
            if item["status"] == "completed":
                completed.append(line)
            elif item["status"] == "in_progress":
                in_progress.append(line)
            elif item["status"] == "pending":
                pending.append(line)
            elif item["status"] == "cancelled":
                cancelled.append(line)

        parts = []

        if in_progress:
            parts.append(f"⏳ In Progress ({len(in_progress)}):")
            parts.extend(in_progress)

        if pending:
            parts.append(f"\n📋 Pending ({len(pending)}):")
            parts.extend(pending)

        if completed:
            parts.append(f"\n✅ Completed ({len(completed)}):")
            parts.extend(completed)

        if cancelled:
            parts.append(f"\n❌ Cancelled ({len(cancelled)}):")
            parts.extend(cancelled)

        total = len(self._items)
        done_count = len(completed)
        progress = int((done_count / total) * 100) if total > 0 else 0

        header = f"📊 Task Progress: {done_count}/{total} ({progress}%)\n"
        header += "──────────────────────────────────────────────────────────────\n"

        return header + "\n".join(parts)

    @staticmethod
    def _validate(item: Dict[str, Any]) -> Dict[str, str]:
        item_id = str(item.get("id", "")).strip()
        if not item_id:
            item_id = "?"

        content = str(item.get("content", "")).strip()
        if not content:
            content = "(no description)"

        status = str(item.get("status", "pending")).strip().lower()
        if status not in VALID_STATUSES:
            status = "pending"

        return {"id": item_id, "content": content, "status": status}

    @staticmethod
    def _dedupe_by_id(todos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        last_index: Dict[str, int] = {}
        for i, item in enumerate(todos):
            item_id = str(item.get("id", "")).strip() or "?"
            last_index[item_id] = i
        return [todos[i] for i in sorted(last_index.values())]

    @staticmethod
    def map_todo_to_kanban_status(todo_status: str) -> str:
        """将 Todo 状态映射到 Kanban 状态"""
        return TODO_TO_KANBAN_STATUS.get(todo_status, "todo")

    @staticmethod
    def map_kanban_to_todo_status(kanban_status: str) -> str:
        """将 Kanban 状态映射到 Todo 状态"""
        return KANBAN_TO_TODO_STATUS.get(kanban_status, "pending")


def todo_tool(
    todos: Optional[List[Dict[str, Any]]] = None,
    merge: bool = False,
    store: Optional[SessionTodoStore] = None,
    persist: bool = False,
) -> str:
    """
    Todo 工具主函数

    Args:
        todos: 要写入的任务列表
        merge: 是否合并到现有列表
        store: SessionTodoStore 实例
        persist: 是否同时持久化到 Kanban
    """
    if store is None:
        return tool_error("SessionTodoStore not initialized")

    if todos is not None:
        items = store.write(todos, merge, persist=persist)
        logger.info(f"规划任务: {len(items)} 个任务")
    else:
        items = store.read()
        logger.info(f"查询任务列表: {len(items)} 个任务")

    pending = sum(1 for i in items if i["status"] == "pending")
    in_progress = sum(1 for i in items if i["status"] == "in_progress")
    completed = sum(1 for i in items if i["status"] == "completed")
    cancelled = sum(1 for i in items if i["status"] == "cancelled")

    return json.dumps({
        "todos": items,
        "summary": {
            "total": len(items),
            "pending": pending,
            "in_progress": in_progress,
            "completed": completed,
            "cancelled": cancelled,
        },
    }, ensure_ascii=False)


def check_todo_requirements() -> bool:
    return True


TODO_SCHEMA = {
    "name": "todo",
    "description": (
        "Manage your task list for the current session. Use for complex tasks "
        "with 3+ steps or when the user provides multiple tasks. "
        "Call with no parameters to read the current list.\n\n"
        "Writing:\n"
        "- Provide 'todos' array to create/update items\n"
        "- merge=false (default): replace the entire list with a fresh plan\n"
        "- merge=true: update existing items by id, add new ones\n\n"
        "Each item: {id: string, content: string, "
        "status: pending|in_progress|completed|cancelled}\n"
        "List order is priority. Only ONE item in_progress at a time.\n"
        "Mark items completed immediately when done. If something fails, "
        "cancel it and add a revised item.\n\n"
        "Always returns the full current list."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "todos": {
                "type": "array",
                "description": "Task items to write. Omit to read current list.",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Unique item identifier"
                        },
                        "content": {
                            "type": "string",
                            "description": "Task description"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "completed", "cancelled"],
                            "description": "Current status"
                        }
                    },
                    "required": ["id", "content", "status"]
                }
            },
            "merge": {
                "type": "boolean",
                "description": (
                    "true: update existing items by id, add new ones. "
                    "false (default): replace the entire list."
                ),
                "default": False
            }
        },
        "required": []
    }
}


from tools.registry import registry

def _todo_handler(args, **kw):
    """todo 工具的包装 handler，添加调试日志"""
    from common.logging_manager import get_logger
    logger = get_logger("todo_handler")
    store = kw.get("store")
    todos = args.get("todos")
    logger.debug(f"todo handler called: todos={todos}, store={id(store) if store else None}")
    return todo_tool(
        todos=todos,
        merge=args.get("merge", False),
        store=store,
        persist=args.get("persist", False),
    )

registry.register(
    name="todo",
    toolset="todo",
    schema=TODO_SCHEMA,
    handler=_todo_handler,
    check_fn=check_todo_requirements,
    emoji="📋",
)


# =============================================================================
# 全局 SessionTodoStore 实例（供 TUI 任务面板使用）
# =============================================================================

def get_session_todo_store() -> SessionTodoStore:
    """
    获取全局 SessionTodoStore 实例。
    
    TUI 任务面板通过此函数获取当前会话的任务列表。
    每次会话（Agent 重启）应该调用 reset_session_todo_store() 重置。
    
    Returns:
        SessionTodoStore 实例
    """
    global _session_todo_store
    if _session_todo_store is None:
        _session_todo_store = SessionTodoStore()
    return _session_todo_store


def reset_session_todo_store() -> SessionTodoStore:
    """
    重置全局 SessionTodoStore 实例（用于新会话开始时）。
    
    Returns:
        新的 SessionTodoStore 实例
    """
    global _session_todo_store
    _session_todo_store = SessionTodoStore()
    return _session_todo_store


# 全局实例（懒加载）
_session_todo_store: Optional[SessionTodoStore] = None
