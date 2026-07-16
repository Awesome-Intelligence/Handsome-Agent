"""
Task module for Agent-Z

🧠 Decision - Task Management

================================================================================
三层任务架构说明
================================================================================

本项目使用三层任务概念，明确划分职责：

┌─────────────────────────────────────────────────────────────────────────────┐
│ Layer 1: Todo（工具层）                                                       │
│ ────────────────────────────                                                │
│ Purpose:  当前会话的"待办清单"，供 LLM 分解复杂任务使用                        │
│ Storage:  内存（SessionTodoStore）                                           │
│ Status:   pending | in_progress | completed | cancelled                     │
│ User:     仅 LLM 使用                                                        │
│ Lifetime: 会话内，会话结束自动清除                                            │
│ Location: tools/todo_tool.py                                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓ 同步
┌─────────────────────────────────────────────────────────────────────────────┐
│ Layer 2: Kanban Task（持久化层）                                             │
│ ──────────────────────────────                                              │
│ Purpose:  长期项目任务管理，支持依赖、评论、运行历史                          │
│ Storage:  SQLite 数据库                                                      │
│ Status:   triage | todo | ready | running | blocked | done | archived       │
│ User:     人类管理员、外部系统                                               │
│ Lifetime: 持久化，可跨会话                                                   │
│ Location: tools/kanban_tool.py, tools/kanban_db.py                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓ 包装
┌─────────────────────────────────────────────────────────────────────────────┐
│ Layer 3: A2A Task（协议层）                                                  │
│ ──────────────────────────                                                  │
│ Purpose:  Agent 间通信协议                                                   │
│ Status:   submitted | working | completed | failed | canceled               │
│ Lifetime: 单次请求响应                                                       │
│ Location: agent/a2a/models.py                                                │
└─────────────────────────────────────────────────────────────────────────────┘

================================================================================
状态映射
================================================================================

状态映射定义在 tools/todo_tool.py 中：

- TODO_TO_KANBAN_STATUS: Todo 状态 → Kanban 状态
  pending     → todo
  in_progress → running
  completed   → done
  cancelled   → done

- KANBAN_TO_TODO_STATUS: Kanban 状态 → Todo 状态
  triage/ready/todo → pending
  running/blocked   → in_progress
  done/archived     → completed

================================================================================
使用场景
================================================================================

1. LLM 分解复杂任务 → 使用 Todo 工具（tools/todo_tool）
2. 需要持久化任务   → Todo 自动同步到 Kanban（通过 SessionTodoStore._sync_to_kanban）
3. 跨 Agent 通信    → 使用 A2A Task（agent/a2a/models.py）
"""

from tools.todo_tool import (
    SessionTodoStore,
    VALID_STATUSES,
    KANBAN_TO_TODO_STATUS,
    TODO_TO_KANBAN_STATUS,
)

__all__ = [
    'SessionTodoStore',
    'VALID_STATUSES',
    'KANBAN_TO_TODO_STATUS',
    'TODO_TO_KANBAN_STATUS',
]