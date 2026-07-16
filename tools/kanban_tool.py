#!/usr/bin/env python3
"""
Kanban Tool Module

Layer 2: Kanban Task（持久化层）- 项目任务管理

提供基于 SQLite 数据库的看板/任务管理功能：
- 看板创建和管理
- 任务 CRUD 操作
- 任务状态流转（triage → todo → ready → running → done）
- 依赖关系和评论
- 运行历史记录
- 完整 Hermes 风格 API 支持

状态: triage | todo | ready | running | blocked | done | archived

Usage:
    from tools.kanban_tool import kanban_create, kanban_show, kanban_list

See also:
- agent/task/__init__.py: 三层任务架构说明
- tools/todo_tool.py: Layer 1 - 会话级任务管理
- agent/a2a/models.py: Layer 3 - A2A 协议任务
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from common.logging_manager import get_execution_logger
from tools.registry import registry

logger = get_execution_logger("kanban")

from tools.kanban_db import (
    KanbanDB,
    board_create,
    board_delete,
    board_get,
    board_list,
    task_create,
    task_get,
    task_list,
    task_update,
    task_delete,
    task_complete,
    task_block,
    task_unblock,
    dep_link,
    dep_unlink,
    dep_parent_ids,
    dep_child_ids,
    comment_add,
    comment_list,
    event_list,
    run_list,
)

logger = get_execution_logger("KanbanTool")

# Database path
DB_PATH = Path.home() / ".agent_z" / "kanban.db"


class KanbanManager:
    """看板管理器，使用 SQLite 数据库"""

    def __init__(self):
        self._db = KanbanDB(DB_PATH)
        self._db.init_schema()
        # 确保默认看板存在
        self._ensure_default_board()

    def _ensure_default_board(self) -> None:
        """确保存在默认看板"""
        conn = self._db.connect()
        try:
            boards = board_list(conn)
            if not boards:
                board_create(conn, "Default Board", tenant="default")
                logger.info("Created default board")
        finally:
            self._db.close()

    @property
    def db(self) -> KanbanDB:
        """获取数据库实例"""
        return self._db

    def get_default_board_id(self) -> Optional[str]:
        """获取默认看板ID"""
        conn = self._db.connect()
        try:
            boards = board_list(conn)
            if boards:
                return boards[0].id
            return None
        finally:
            self._db.close()

    def create_board(self, name: str, tenant: Optional[str] = None) -> str:
        """创建看板"""
        conn = self._db.connect()
        try:
            board = board_create(conn, name, tenant)
            conn.commit()  # 提交事务
            logger.info(f"Created board: {name} ({board.id})")
            return board.id
        finally:
            self._db.close()

    def delete_board(self, board_id: str) -> bool:
        """删除看板"""
        conn = self._db.connect()
        try:
            result = board_delete(conn, board_id)
            conn.commit()  # 提交事务
            logger.info(f"Deleted board: {board_id}")
            return result
        finally:
            self._db.close()

    def get_board(self, board_id: str) -> Optional[Any]:
        """获取看板"""
        conn = self._db.connect()
        try:
            return board_get(conn, board_id)
        finally:
            self._db.close()

    def list_boards(self) -> List[Dict[str, Any]]:
        """列出所有看板"""
        conn = self._db.connect()
        try:
            boards = board_list(conn)
            result = []
            for board in boards:
                # 获取任务数量
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) as count FROM tasks WHERE board_id = ?",
                    (board.id,),
                )
                task_count = cursor.fetchone()["count"]
                result.append(
                    {
                        "id": board.id,
                        "name": board.name,
                        "created_at": board.created_at,
                        "tenant": board.tenant,
                        "task_count": task_count,
                    }
                )
            return result
        finally:
            self._db.close()

    def create_task(
        self,
        board_id: str,
        title: str,
        body: Optional[str] = None,
        status: str = "todo",
        priority: int = 0,
        assignee: Optional[str] = None,
        created_by: Optional[str] = None,
        workspace_kind: str = "scratch",
        workspace_path: Optional[str] = None,
        max_runtime_seconds: Optional[int] = None,
        idempotency_key: Optional[str] = None,
        initial_status: str = "running",
        skills: Optional[List[str]] = None,
        tenant: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> str:
        """创建任务"""
        conn = self._db.connect()
        try:
            result = task_create(
                conn=conn,
                board_id=board_id,
                title=title,
                body=body,
                status=status,
                priority=priority,
                assignee=assignee,
                created_by=created_by,
                workspace_kind=workspace_kind,
                workspace_path=workspace_path,
                max_runtime_seconds=max_runtime_seconds,
                idempotency_key=idempotency_key,
                initial_status=initial_status,
                skills=skills,
                tenant=tenant,
                session_id=session_id,
            )
            conn.commit()  # 提交事务
            logger.info(f"Created task: {title} ({result})")
            return result if isinstance(result, str) else result.id
        finally:
            self._db.close()

    def get_task(self, task_id: str) -> Optional[Any]:
        """获取任务"""
        conn = self._db.connect()
        try:
            return task_get(conn, task_id)
        finally:
            self._db.close()

    def list_tasks(
        self,
        board_id: Optional[str] = None,
        assignee: Optional[str] = None,
        status: Optional[str] = None,
        tenant: Optional[str] = None,
        include_archived: bool = False,
        limit: int = 50,
    ) -> List[Any]:
        """列出任务"""
        conn = self._db.connect()
        try:
            return task_list(
                conn,
                board_id=board_id,
                assignee=assignee,
                status=status,
                tenant=tenant,
                include_archived=include_archived,
                limit=limit,
            )
        finally:
            self._db.close()

    def update_task(
        self,
        task_id: str,
        title: Optional[str] = None,
        body: Optional[str] = None,
        priority: Optional[int] = None,
        assignee: Optional[str] = None,
        status: Optional[str] = None,
        **kwargs,
    ) -> Optional[Any]:
        """更新任务"""
        conn = self._db.connect()
        try:
            updates = {}
            if title is not None:
                updates["title"] = title
            if body is not None:
                updates["body"] = body
            if priority is not None:
                updates["priority"] = priority
            if assignee is not None:
                updates["assignee"] = assignee
            if status is not None:
                updates["status"] = status
            updates.update(kwargs)

            result = task_update(conn, task_id, **updates)
            conn.commit()  # 提交事务
            logger.info(f"Updated task: {task_id}")
            return result
        finally:
            self._db.close()

    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        conn = self._db.connect()
        try:
            result = task_delete(conn, task_id)
            conn.commit()  # 提交事务
            logger.info(f"Deleted task: {task_id}")
            return result
        finally:
            self._db.close()

    def complete_task(
        self,
        task_id: str,
        result: Optional[str] = None,
        summary: Optional[str] = None,
        metadata: Optional[Dict] = None,
        created_cards: Optional[List[str]] = None,
        artifacts: Optional[List[str]] = None,
    ) -> Optional[Any]:
        """完成任务"""
        conn = self._db.connect()
        try:
            result_task = task_complete(
                conn=conn,
                task_id=task_id,
                result=result,
                summary=summary,
                metadata=metadata,
                created_cards=created_cards,
                artifacts=artifacts,
            )
            conn.commit()  # 提交事务
            logger.info(f"Completed task: {task_id}")
            return result_task
        finally:
            self._db.close()

    def block_task(self, task_id: str, reason: str) -> Optional[Any]:
        """阻塞任务"""
        conn = self._db.connect()
        try:
            result = task_block(conn, task_id, reason)
            conn.commit()  # 提交事务
            logger.info(f"Blocked task: {task_id} - {reason}")
            return result
        finally:
            self._db.close()

    def unblock_task(self, task_id: str) -> Optional[Any]:
        """解阻塞任务"""
        conn = self._db.connect()
        try:
            result = task_unblock(conn, task_id)
            conn.commit()  # 提交事务
            logger.info(f"Unblocked task: {task_id}")
            return result
        finally:
            self._db.close()

    def link_tasks(self, parent_id: str, child_id: str) -> bool:
        """链接任务依赖"""
        conn = self._db.connect()
        try:
            result = dep_link(conn, parent_id, child_id)
            conn.commit()  # 提交事务
            logger.info(f"Linked tasks: {parent_id} -> {child_id}")
            return result
        finally:
            self._db.close()

    def unlink_tasks(self, parent_id: str, child_id: str) -> bool:
        """取消链接任务依赖"""
        conn = self._db.connect()
        try:
            result = dep_unlink(conn, parent_id, child_id)
            conn.commit()  # 提交事务
            logger.info(f"Unlinked tasks: {parent_id} -> {child_id}")
            return result
        finally:
            self._db.close()

    def get_dependencies(self, task_id: str) -> Dict[str, List[str]]:
        """获取任务依赖"""
        conn = self._db.connect()
        try:
            return {
                "parents": dep_parent_ids(conn, task_id),
                "children": dep_child_ids(conn, task_id),
            }
        finally:
            self._db.close()

    def add_comment(self, task_id: str, author: str, body: str) -> Any:
        """添加评论"""
        conn = self._db.connect()
        try:
            comment = comment_add(conn, task_id, author, body)
            conn.commit()  # 提交事务
            logger.info(f"Added comment to task: {task_id}")
            return comment
        finally:
            self._db.close()

    def get_comments(self, task_id: str) -> List[Any]:
        """获取任务评论"""
        conn = self._db.connect()
        try:
            return comment_list(conn, task_id)
        finally:
            self._db.close()

    def get_events(self, task_id: str, limit: int = 50) -> List[Any]:
        """获取任务事件"""
        conn = self._db.connect()
        try:
            return event_list(conn, task_id, limit)
        finally:
            self._db.close()

    def get_runs(self, task_id: str) -> List[Any]:
        """获取任务运行记录"""
        conn = self._db.connect()
        try:
            return run_list(conn, task_id)
        finally:
            self._db.close()


# 全局管理器实例
_kanban_manager = KanbanManager()


def _get_author() -> str:
    """获取当前用户标识"""
    return os.environ.get("HERMES_PROFILE", "unknown")


def _task_to_dict(task: Any) -> Dict[str, Any]:
    """将任务对象转换为字典"""
    if task is None:
        return {}
    return {
        "id": task.id,
        "board_id": task.board_id,
        "title": task.title,
        "body": task.body,
        "status": task.status,
        "priority": task.priority,
        "assignee": task.assignee,
        "created_by": task.created_by,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "started_at": task.started_at,
        "completed_at": task.completed_at,
        "blocked_reason": task.blocked_reason,
        "workspace_kind": task.workspace_kind,
        "workspace_path": task.workspace_path,
        "max_runtime_seconds": task.max_runtime_seconds,
        "idempotency_key": task.idempotency_key,
    }


def _comment_to_dict(comment: Any) -> Dict[str, Any]:
    """将评论对象转换为字典"""
    if comment is None:
        return {}
    return {
        "id": comment.id,
        "task_id": comment.task_id,
        "author": comment.author,
        "body": comment.body,
        "created_at": comment.created_at,
    }


def _event_to_dict(event: Any) -> Dict[str, Any]:
    """将事件对象转换为字典"""
    if event is None:
        return {}
    return {
        "id": event.id,
        "task_id": event.task_id,
        "kind": event.kind,
        "payload": event.payload,
        "created_at": event.created_at,
        "run_id": event.run_id,
    }


def _run_to_dict(run: Any) -> Dict[str, Any]:
    """将运行记录转换为字典"""
    if run is None:
        return {}
    return {
        "id": run.id,
        "task_id": run.task_id,
        "profile": run.profile,
        "status": run.status,
        "outcome": run.outcome,
        "summary": run.summary,
        "error": run.error,
        "metadata": run.metadata,
        "started_at": run.started_at,
        "ended_at": run.ended_at,
    }


# =============================================================================
# Worker 保护机制（参考 Hermes）
# =============================================================================

def _default_task_id(arg: Optional[str]) -> Optional[str]:
    """解析 task_id 参数，回退到环境变量"""
    if arg:
        return arg
    return os.environ.get("HERMES_KANBAN_TASK") or None


def _enforce_worker_task_ownership(tid: str) -> Optional[str]:
    """
    拒绝 Worker 对外部任务 ID 的破坏性调用。

    当进程由 dispatcher 启动时，环境变量 HERMES_KANBAN_TASK 被设置为
    自身的任务 ID。像 kanban_complete/block/heartbeat 这样的工具会修改
    运行生命周期状态，因此存在 bug 或 prompt 注入的 worker 可能传入
    显式 task_id 来修改其他任务，从而污染同级或跨租户的运行。

    Orchestrator profiles（启用了 kanban toolset 但环境中没有
    HERMES_KANBAN_TASK）不受此检查限制——他们的工作是路由，
    有时需要合理地关闭子任务或重新打开被阻塞的任务。
    Workers 被严格限制在其一个任务上。

    Returns:
        None 表示允许调用，或工具错误字符串表示必须拒绝
    """
    env_tid = os.environ.get("HERMES_KANBAN_TASK")
    if not env_tid:
        # Orchestrator 或 CLI 上下文 — 无任务范围限制
        return None
    if tid != env_tid:
        return json.dumps({
            "success": False,
            "error": (
                f"worker is scoped to task {env_tid}; refusing to mutate "
                f"{tid}. Use kanban_comment to hand off information to other "
                f"tasks, or kanban_create to spawn follow-up work."
            )
        }, ensure_ascii=False)
    return None


def _require_orchestrator_tool(tool_name: str) -> Optional[str]:
    """
    Orchestrator 专用工具的运行时保护。

    check_fn 会在 worker schema 中排除这些工具，但为了防止
    陈旧注册或测试工具链路由 worker 到这些工具，返回结构化的
    工具错误让模型获得清晰的拒绝而不是静默修改 board 状态。
    """
    if os.environ.get("HERMES_KANBAN_TASK"):
        return json.dumps({
            "success": False,
            "error": (
                f"{tool_name} is orchestrator-only; dispatcher-spawned workers "
                "must use kanban_complete, kanban_block, kanban_heartbeat, or "
                "kanban_comment for their assigned task."
            )
        }, ensure_ascii=False)
    return None

# =============================================================================
# 工具函数（参考 Hermes 设计）
# =============================================================================


def kanban_create(
    board_id: Optional[str] = None,
    title: str = "",
    assignee: str = "",
    body: Optional[str] = None,
    parents: Optional[List[str]] = None,
    tenant: Optional[str] = None,
    priority: int = 0,
    workspace_kind: str = "scratch",
    workspace_path: Optional[str] = None,
    triage: bool = False,
    idempotency_key: Optional[str] = None,
    max_runtime_seconds: Optional[int] = None,
    initial_status: str = "running",
    skills: Optional[List[str]] = None,
    session_id: Optional[str] = None,
) -> str:
    """
    创建任务，支持完整参数。

    Args:
        board_id: 看板ID（可选，默认使用第一个看板）
        title: 任务标题
        assignee: 负责人
        body: 任务描述
        parents: 父任务ID列表
        tenant: 租户标识
        priority: 优先级（0-2）
        workspace_kind: 工作区类型
        workspace_path: 工作区路径
        triage: 是否在 triage 状态
        idempotency_key: 幂等键
        max_runtime_seconds: 最大运行时间
        initial_status: 初始状态
        skills: 技能列表
        session_id: 会话ID

    Returns:
        JSON 格式的结果字符串
    """
    try:
        # 使用默认看板如果没有指定
        if not board_id:
            board_id = _kanban_manager.get_default_board_id()
            if not board_id:
                result = {"success": False, "error": "没有可用的看板"}
                return json.dumps(result, ensure_ascii=False)

        # 设置初始状态
        if triage:
            initial_status = "triage"

        task_id = _kanban_manager.create_task(
            board_id=board_id,
            title=title,
            body=body,
            status=initial_status,  # 使用 initial_status 而不是硬编码 "todo"
            priority=priority,
            assignee=assignee if assignee else None,
            created_by=_get_author(),
            workspace_kind=workspace_kind,
            workspace_path=workspace_path,
            max_runtime_seconds=max_runtime_seconds,
            idempotency_key=idempotency_key,
            initial_status=initial_status,
            skills=skills,
            tenant=tenant,
            session_id=session_id,
        )

        # 添加父任务依赖
        if parents:
            for parent_id in parents:
                _kanban_manager.link_tasks(parent_id, task_id)

        result = {
            "success": True,
            "task_id": task_id,
            "title": title,
            "message": f"任务已创建: {title}",
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)


def kanban_show(
    task_id: str,
    board: Optional[str] = None,
) -> str:
    """
    查看任务详情，返回完整信息（含评论/事件/运行历史/依赖）。

    Args:
        task_id: 任务ID
        board: 看板ID（可选，用于兼容）

    Returns:
        JSON 格式的结果字符串
    """
    try:
        task = _kanban_manager.get_task(task_id)
        if not task:
            result = {"success": False, "error": f"任务不存在: {task_id}"}
            return json.dumps(result, ensure_ascii=False)

        # 获取关联数据
        comments = _kanban_manager.get_comments(task_id)
        events = _kanban_manager.get_events(task_id)
        runs = _kanban_manager.get_runs(task_id)
        deps = _kanban_manager.get_dependencies(task_id)

        result = {
            "success": True,
            "task": _task_to_dict(task),
            "comments": [_comment_to_dict(c) for c in comments],
            "events": [_event_to_dict(e) for e in events],
            "runs": [_run_to_dict(r) for r in runs],
            "dependencies": deps,
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to show task: {e}")
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)


def kanban_list(
    assignee: Optional[str] = None,
    status: Optional[str] = None,
    tenant: Optional[str] = None,
    include_archived: bool = False,
    limit: int = 50,
    board: Optional[str] = None,
) -> str:
    """
    列出任务，支持筛选器。

    注意: 此工具仅限 Orchestrator 使用，Worker 无法访问。

    Args:
        assignee: 负责人筛选
        status: 状态筛选
        tenant: 租户筛选
        include_archived: 包含已归档任务
        limit: 返回数量限制
        board: 看板ID筛选

    Returns:
        JSON 格式的结果字符串
    """
    # Orchestrator 检查
    guard = _require_orchestrator_tool("kanban_list")
    if guard:
        return guard

    try:
        tasks = _kanban_manager.list_tasks(
            board_id=board,
            assignee=assignee,
            status=status,
            tenant=tenant,
            include_archived=include_archived,
            limit=limit,
        )

        result = {
            "success": True,
            "tasks": [_task_to_dict(t) for t in tasks],
            "total": len(tasks),
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)


def kanban_update(
    task_id: str,
    title: Optional[str] = None,
    body: Optional[str] = None,
    priority: Optional[int] = None,
    assignee: Optional[str] = None,
    board: Optional[str] = None,
) -> str:
    """
    更新任务（非状态）。

    Args:
        task_id: 任务ID
        title: 新标题
        body: 新描述
        priority: 新优先级
        assignee: 新负责人
        board: 看板ID（可选，用于兼容）

    Returns:
        JSON 格式的结果字符串
    """
    try:
        updates = {}
        if title is not None:
            updates["title"] = title
        if body is not None:
            updates["body"] = body
        if priority is not None:
            updates["priority"] = priority
        if assignee is not None:
            updates["assignee"] = assignee

        task = _kanban_manager.update_task(task_id, **updates)
        if task:
            result = {
                "success": True,
                "task": _task_to_dict(task),
                "message": "任务已更新",
            }
        else:
            result = {"success": False, "error": f"任务不存在: {task_id}"}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to update task: {e}")
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)


def kanban_complete(
    task_id: Optional[str] = None,
    summary: Optional[str] = None,
    metadata: Optional[Dict] = None,
    result: Optional[str] = None,
    created_cards: Optional[List[str]] = None,
    artifacts: Optional[List[str]] = None,
    board: Optional[str] = None,
) -> str:
    """
    完成任务，支持 handoff 信息。

    Args:
        task_id: 任务ID（可选，默认使用当前 Worker 的任务）
        summary: 完成摘要
        metadata: 元数据
        result: 结果
        created_cards: 创建的卡片ID列表
        artifacts: 产出物列表
        board: 看板ID（可选，用于兼容）

    Returns:
        JSON 格式的结果字符串
    """
    try:
        # 解析 task_id，支持从环境变量回退
        tid = _default_task_id(task_id)
        if not tid:
            result = {"success": False, "error": "task_id 是必填的"}
            return json.dumps(result, ensure_ascii=False)

        # Worker 所有权检查
        ownership_err = _enforce_worker_task_ownership(tid)
        if ownership_err:
            return ownership_err

        task = _kanban_manager.complete_task(
            task_id=tid,
            result=result,
            summary=summary,
            metadata=metadata,
            created_cards=created_cards,
            artifacts=artifacts,
        )

        if task:
            result = {
                "success": True,
                "task": _task_to_dict(task),
                "message": "任务已完成",
            }
        else:
            result = {"success": False, "error": f"任务不存在或无法完成: {tid}"}
        return json.dumps(result, ensure_ascii=False)
    except ValueError as e:
        # 状态转换错误
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to complete task: {e}")
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)


def kanban_block(
    task_id: Optional[str] = None,
    reason: str = "",
    board: Optional[str] = None,
) -> str:
    """
    阻塞任务。

    Args:
        task_id: 任务ID（可选，默认使用当前 Worker 的任务）
        reason: 阻塞原因
        board: 看板ID（可选，用于兼容）

    Returns:
        JSON 格式的结果字符串
    """
    try:
        if not reason or not str(reason).strip():
            result = {"success": False, "error": "reason 是必填的 — 说明你需要什么输入才能继续"}
            return json.dumps(result, ensure_ascii=False)

        # 解析 task_id，支持从环境变量回退
        tid = _default_task_id(task_id)
        if not tid:
            result = {"success": False, "error": "task_id 是必填的"}
            return json.dumps(result, ensure_ascii=False)

        # Worker 所有权检查
        ownership_err = _enforce_worker_task_ownership(tid)
        if ownership_err:
            return ownership_err

        task = _kanban_manager.block_task(tid, reason)
        if task:
            result = {
                "success": True,
                "task": _task_to_dict(task),
                "message": f"任务已阻塞: {reason}",
            }
        else:
            result = {"success": False, "error": f"任务不存在: {tid}"}
        return json.dumps(result, ensure_ascii=False)
    except ValueError as e:
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to block task: {e}")
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)


def kanban_unblock(
    task_id: str,
    board: Optional[str] = None,
) -> str:
    """
    解阻塞任务（仅限 orchestrator）。

    Args:
        task_id: 任务ID
        board: 看板ID（可选，用于兼容）

    Returns:
        JSON 格式的结果字符串
    """
    # Orchestrator 检查
    guard = _require_orchestrator_tool("kanban_unblock")
    if guard:
        return guard

    try:
        task = _kanban_manager.unblock_task(task_id)
        if task:
            result = {
                "success": True,
                "task": _task_to_dict(task),
                "message": "任务已解除阻塞",
            }
        else:
            result = {"success": False, "error": f"任务不存在: {task_id}"}
        return json.dumps(result, ensure_ascii=False)
    except ValueError as e:
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to unblock task: {e}")
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)


def kanban_heartbeat(
    task_id: Optional[str] = None,
    note: Optional[str] = None,
    board: Optional[str] = None,
) -> str:
    """
    心跳保活。

    Args:
        task_id: 任务ID（可选，默认使用当前 Worker 的任务）
        note: 心跳备注
        board: 看板ID（可选，用于兼容）

    Returns:
        JSON 格式的结果字符串
    """
    try:
        # 解析 task_id，支持从环境变量回退
        tid = _default_task_id(task_id)
        if not tid:
            result = {"success": False, "error": "task_id 是必填的"}
            return json.dumps(result, ensure_ascii=False)

        # Worker 所有权检查
        ownership_err = _enforce_worker_task_ownership(tid)
        if ownership_err:
            return ownership_err

        task = _kanban_manager.get_task(tid)
        if not task:
            result = {"success": False, "error": f"任务不存在: {tid}"}
            return json.dumps(result, ensure_ascii=False)

        # 添加心跳事件
        author = _get_author()
        if note:
            _kanban_manager.add_comment(tid, author, f"[心跳] {note}")
        else:
            _kanban_manager.add_comment(tid, author, "[心跳]")

        result = {
            "success": True,
            "task_id": tid,
            "message": "心跳已记录",
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to heartbeat: {e}")
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)


def kanban_comment(
    task_id: str,
    body: str,
    board: Optional[str] = None,
) -> str:
    """
    添加评论。

    Args:
        task_id: 任务ID
        body: 评论内容
        board: 看板ID（可选，用于兼容）

    Returns:
        JSON 格式的结果字符串
    """
    try:
        task = _kanban_manager.get_task(task_id)
        if not task:
            result = {"success": False, "error": f"任务不存在: {task_id}"}
            return json.dumps(result, ensure_ascii=False)

        author = _get_author()
        comment = _kanban_manager.add_comment(task_id, author, body)

        result = {
            "success": True,
            "comment": _comment_to_dict(comment),
            "message": "评论已添加",
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to add comment: {e}")
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)


def kanban_link(
    parent_id: str,
    child_id: str,
    board: Optional[str] = None,
) -> str:
    """
    链接依赖关系（父任务完成后子任务变为 ready）。

    Args:
        parent_id: 父任务ID
        child_id: 子任务ID
        board: 看板ID（可选，用于兼容）

    Returns:
        JSON 格式的结果字符串
    """
    try:
        success = _kanban_manager.link_tasks(parent_id, child_id)
        if success:
            result = {
                "success": True,
                "message": f"已链接: {parent_id} -> {child_id}",
            }
        else:
            result = {"success": False, "error": "依赖关系已存在"}
        return json.dumps(result, ensure_ascii=False)
    except ValueError as e:
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to link tasks: {e}")
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)


def kanban_unlink(
    parent_id: str,
    child_id: str,
    board: Optional[str] = None,
) -> str:
    """
    取消链接依赖关系。

    Args:
        parent_id: 父任务ID
        child_id: 子任务ID
        board: 看板ID（可选，用于兼容）

    Returns:
        JSON 格式的结果字符串
    """
    try:
        success = _kanban_manager.unlink_tasks(parent_id, child_id)
        if success:
            result = {
                "success": True,
                "message": f"已取消链接: {parent_id} -> {child_id}",
            }
        else:
            result = {"success": False, "error": "依赖关系不存在"}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to unlink tasks: {e}")
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)


def kanban_delete(
    task_id: str,
    board: Optional[str] = None,
) -> str:
    """
    删除任务（新版实现）。

    Args:
        task_id: 任务ID
        board: 看板ID（可选，用于兼容）

    Returns:
        JSON 格式的结果字符串
    """
    try:
        success = _kanban_manager.delete_task(task_id)
        if success:
            result = {"success": True, "message": "任务已删除"}
        else:
            result = {"success": False, "error": f"任务不存在: {task_id}"}
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to delete task: {e}")
        result = {"success": False, "error": str(e)}
        return json.dumps(result, ensure_ascii=False)


def check_kanban_requirements() -> bool:
    """
    检查是否启用 Kanban 工具

    参考 Hermes 的设计，Kanban 工具默认不加载，仅在以下条件之一满足时启用：
    1. 环境变量 AGENTZ_KANBAN_ENABLED 设置为 "1" 或 "true"
    2. 环境变量 HERMES_KANBAN_TASK 已设置（兼容 Hermes）
    3. 当前正在运行 Kanban 任务（通过 kanban_manager 检测）

    Returns:
        bool: 是否启用 Kanban 工具
    """
    enabled_flag = os.environ.get("AGENTZ_KANBAN_ENABLED", "").lower()
    hermes_task = os.environ.get("HERMES_KANBAN_TASK", "")

    if enabled_flag in ("1", "true", "yes") or hermes_task:
        logger.debug("Kanban tools enabled via environment variable")
        return True

    return False


# =============================================================================
# 工具 Schema 定义（参考 Hermes 设计）
# =============================================================================

KANBAN_CREATE_SCHEMA = {
    "name": "kanban_create",
    "description": "创建任务，支持完整参数。",
    "parameters": {
        "type": "object",
        "properties": {
            "board_id": {
                "type": "string",
                "description": "看板ID（可选，默认使用第一个看板）",
            },
            "title": {"type": "string", "description": "任务标题"},
            "assignee": {"type": "string", "description": "负责人"},
            "body": {"type": "string", "description": "任务描述"},
            "parents": {
                "type": "array",
                "items": {"type": "string"},
                "description": "父任务ID列表",
            },
            "tenant": {"type": "string", "description": "租户标识"},
            "priority": {
                "type": "integer",
                "default": 0,
                "description": "优先级（0-2）",
            },
            "workspace_kind": {
                "type": "string",
                "default": "scratch",
                "description": "工作区类型",
            },
            "workspace_path": {"type": "string", "description": "工作区路径"},
            "triage": {
                "type": "boolean",
                "default": False,
                "description": "是否在 triage 状态",
            },
            "idempotency_key": {"type": "string", "description": "幂等键"},
            "max_runtime_seconds": {"type": "integer", "description": "最大运行时间"},
            "initial_status": {
                "type": "string",
                "default": "running",
                "description": "初始状态",
            },
            "skills": {
                "type": "array",
                "items": {"type": "string"},
                "description": "技能列表",
            },
            "session_id": {"type": "string", "description": "会话ID"},
        },
        "required": ["title"],
    },
}

KANBAN_SHOW_SCHEMA = {
    "name": "kanban_show",
    "description": "查看任务详情，返回完整信息（含评论/事件/运行历史/依赖）。",
    "parameters": {
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "任务ID"},
            "board": {"type": "string", "description": "看板ID（可选）"},
        },
        "required": ["task_id"],
    },
}

KANBAN_LIST_SCHEMA = {
    "name": "kanban_list",
    "description": "列出任务，支持筛选器。",
    "parameters": {
        "type": "object",
        "properties": {
            "assignee": {"type": "string", "description": "负责人筛选"},
            "status": {"type": "string", "description": "状态筛选"},
            "tenant": {"type": "string", "description": "租户筛选"},
            "include_archived": {
                "type": "boolean",
                "default": False,
                "description": "包含已归档任务",
            },
            "limit": {"type": "integer", "default": 50, "description": "返回数量限制"},
            "board": {"type": "string", "description": "看板ID筛选"},
        },
    },
}

KANBAN_UPDATE_SCHEMA = {
    "name": "kanban_update",
    "description": "更新任务（非状态）。",
    "parameters": {
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "任务ID"},
            "title": {"type": "string", "description": "新标题"},
            "body": {"type": "string", "description": "新描述"},
            "priority": {"type": "integer", "description": "新优先级"},
            "assignee": {"type": "string", "description": "新负责人"},
            "board": {"type": "string", "description": "看板ID（可选）"},
        },
        "required": ["task_id"],
    },
}

KANBAN_COMPLETE_SCHEMA = {
    "name": "kanban_complete",
    "description": "完成任务，支持 handoff 信息。",
    "parameters": {
        "type": "object",
        "properties": {
            "task_id": {
                "type": "string",
                "description": "任务ID（可选，默认使用当前 Worker 的任务）"
            },
            "summary": {"type": "string", "description": "完成摘要"},
            "metadata": {"type": "object", "description": "元数据"},
            "result": {"type": "string", "description": "结果"},
            "created_cards": {
                "type": "array",
                "items": {"type": "string"},
                "description": "创建的卡片ID列表",
            },
            "artifacts": {
                "type": "array",
                "items": {"type": "string"},
                "description": "产出物列表",
            },
            "board": {"type": "string", "description": "看板ID（可选）"},
        },
    },
}

KANBAN_BLOCK_SCHEMA = {
    "name": "kanban_block",
    "description": "阻塞任务。",
    "parameters": {
        "type": "object",
        "properties": {
            "task_id": {
                "type": "string",
                "description": "任务ID（可选，默认使用当前 Worker 的任务）"
            },
            "reason": {"type": "string", "description": "阻塞原因"},
            "board": {"type": "string", "description": "看板ID（可选）"},
        },
        "required": ["reason"],
    },
}

KANBAN_UNBLOCK_SCHEMA = {
    "name": "kanban_unblock",
    "description": "解阻塞任务（仅限 orchestrator）。",
    "parameters": {
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "任务ID"},
            "board": {"type": "string", "description": "看板ID（可选）"},
        },
        "required": ["task_id"],
    },
}

KANBAN_HEARTBEAT_SCHEMA = {
    "name": "kanban_heartbeat",
    "description": "心跳保活。",
    "parameters": {
        "type": "object",
        "properties": {
            "task_id": {
                "type": "string",
                "description": "任务ID（可选，默认使用运行中的任务）",
            },
            "note": {"type": "string", "description": "心跳备注"},
            "board": {"type": "string", "description": "看板ID（可选）"},
        },
    },
}

KANBAN_COMMENT_SCHEMA = {
    "name": "kanban_comment",
    "description": "添加评论。",
    "parameters": {
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "任务ID"},
            "body": {"type": "string", "description": "评论内容"},
            "board": {"type": "string", "description": "看板ID（可选）"},
        },
        "required": ["task_id", "body"],
    },
}

KANBAN_LINK_SCHEMA = {
    "name": "kanban_link",
    "description": "链接依赖关系（父任务完成后子任务变为 ready）。",
    "parameters": {
        "type": "object",
        "properties": {
            "parent_id": {"type": "string", "description": "父任务ID"},
            "child_id": {"type": "string", "description": "子任务ID"},
            "board": {"type": "string", "description": "看板ID（可选）"},
        },
        "required": ["parent_id", "child_id"],
    },
}

KANBAN_UNLINK_SCHEMA = {
    "name": "kanban_unlink",
    "description": "取消链接依赖关系。",
    "parameters": {
        "type": "object",
        "properties": {
            "parent_id": {"type": "string", "description": "父任务ID"},
            "child_id": {"type": "string", "description": "子任务ID"},
            "board": {"type": "string", "description": "看板ID（可选）"},
        },
        "required": ["parent_id", "child_id"],
    },
}

KANBAN_DELETE_SCHEMA = {
    "name": "kanban_delete",
    "description": "删除任务（新版实现）。",
    "parameters": {
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "任务ID"},
            "board": {"type": "string", "description": "看板ID（可选）"},
        },
        "required": ["task_id"],
    },
}


# =============================================================================
# 工具注册
# =============================================================================

registry.register(
    name="kanban_create",
    toolset="kanban",
    schema=KANBAN_CREATE_SCHEMA,
    handler=lambda args, **kw: kanban_create(
        board_id=args.get("board_id"),
        title=args.get("title", ""),
        assignee=args.get("assignee", ""),
        body=args.get("body"),
        parents=args.get("parents"),
        tenant=args.get("tenant"),
        priority=args.get("priority", 0),
        workspace_kind=args.get("workspace_kind", "scratch"),
        workspace_path=args.get("workspace_path"),
        triage=args.get("triage", False),
        idempotency_key=args.get("idempotency_key"),
        max_runtime_seconds=args.get("max_runtime_seconds"),
        initial_status=args.get("initial_status", "running"),
        skills=args.get("skills"),
        session_id=args.get("session_id"),
    ),
    check_fn=check_kanban_requirements,
    emoji="✨",
)

registry.register(
    name="kanban_show",
    toolset="kanban",
    schema=KANBAN_SHOW_SCHEMA,
    handler=lambda args, **kw: kanban_show(
        task_id=args.get("task_id", ""),
        board=args.get("board"),
    ),
    check_fn=check_kanban_requirements,
    emoji="🔍",
)

registry.register(
    name="kanban_list",
    toolset="kanban",
    schema=KANBAN_LIST_SCHEMA,
    handler=lambda args, **kw: kanban_list(
        assignee=args.get("assignee"),
        status=args.get("status"),
        tenant=args.get("tenant"),
        include_archived=args.get("include_archived", False),
        limit=args.get("limit", 50),
        board=args.get("board"),
    ),
    check_fn=check_kanban_requirements,
    emoji="📝",
)

registry.register(
    name="kanban_update",
    toolset="kanban",
    schema=KANBAN_UPDATE_SCHEMA,
    handler=lambda args, **kw: kanban_update(
        task_id=args.get("task_id", ""),
        title=args.get("title"),
        body=args.get("body"),
        priority=args.get("priority"),
        assignee=args.get("assignee"),
        board=args.get("board"),
    ),
    check_fn=check_kanban_requirements,
    emoji="✏️",
)

registry.register(
    name="kanban_complete",
    toolset="kanban",
    schema=KANBAN_COMPLETE_SCHEMA,
    handler=lambda args, **kw: kanban_complete(
        task_id=args.get("task_id"),
        summary=args.get("summary"),
        metadata=args.get("metadata"),
        result=args.get("result"),
        created_cards=args.get("created_cards"),
        artifacts=args.get("artifacts"),
        board=args.get("board"),
    ),
    check_fn=check_kanban_requirements,
    emoji="✅",
)

registry.register(
    name="kanban_block",
    toolset="kanban",
    schema=KANBAN_BLOCK_SCHEMA,
    handler=lambda args, **kw: kanban_block(
        task_id=args.get("task_id", ""),
        reason=args.get("reason", ""),
        board=args.get("board"),
    ),
    check_fn=check_kanban_requirements,
    emoji="🚫",
)

registry.register(
    name="kanban_unblock",
    toolset="kanban",
    schema=KANBAN_UNBLOCK_SCHEMA,
    handler=lambda args, **kw: kanban_unblock(
        task_id=args.get("task_id", ""),
        board=args.get("board"),
    ),
    check_fn=check_kanban_requirements,
    emoji="🔓",
)

registry.register(
    name="kanban_heartbeat",
    toolset="kanban",
    schema=KANBAN_HEARTBEAT_SCHEMA,
    handler=lambda args, **kw: kanban_heartbeat(
        task_id=args.get("task_id"),
        note=args.get("note"),
        board=args.get("board"),
    ),
    check_fn=check_kanban_requirements,
    emoji="💓",
)

registry.register(
    name="kanban_comment",
    toolset="kanban",
    schema=KANBAN_COMMENT_SCHEMA,
    handler=lambda args, **kw: kanban_comment(
        task_id=args.get("task_id", ""),
        body=args.get("body", ""),
        board=args.get("board"),
    ),
    check_fn=check_kanban_requirements,
    emoji="💬",
)

registry.register(
    name="kanban_link",
    toolset="kanban",
    schema=KANBAN_LINK_SCHEMA,
    handler=lambda args, **kw: kanban_link(
        parent_id=args.get("parent_id", ""),
        child_id=args.get("child_id", ""),
        board=args.get("board"),
    ),
    check_fn=check_kanban_requirements,
    emoji="🔗",
)

registry.register(
    name="kanban_unlink",
    toolset="kanban",
    schema=KANBAN_UNLINK_SCHEMA,
    handler=lambda args, **kw: kanban_unlink(
        parent_id=args.get("parent_id", ""),
        child_id=args.get("child_id", ""),
        board=args.get("board"),
    ),
    check_fn=check_kanban_requirements,
    emoji="✂️",
)

registry.register(
    name="kanban_delete",
    toolset="kanban",
    schema=KANBAN_DELETE_SCHEMA,
    handler=lambda args, **kw: kanban_delete(
        task_id=args.get("task_id", ""),
        board=args.get("board"),
    ),
    check_fn=check_kanban_requirements,
    emoji="🗑️",
)
