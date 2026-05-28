"""任务管理工具定义 - Todo 和 Memory"""
from tools.schema_registry import UnifiedToolSchema, ToolSource


TASK_TOOLS = [
    UnifiedToolSchema(
        name="todo",
        description="任务管理：创建、列表、更新、完成任务",
        source=ToolSource.HERMES,
        source_name="todo",
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create", "list", "update", "complete", "delete"],
                    "description": "操作类型"
                },
                "title": {
                    "type": "string",
                    "description": "任务标题"
                },
                "description": {
                    "type": "string",
                    "description": "任务描述"
                },
                "task_id": {
                    "type": "string",
                    "description": "任务 ID"
                },
                "status": {
                    "type": "string",
                    "enum": ["pending", "in_progress", "completed", "cancelled"],
                    "description": "任务状态"
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "urgent"],
                    "description": "优先级",
                    "default": "medium"
                },
                "due_date": {
                    "type": "string",
                    "description": "截止日期 (YYYY-MM-DD)"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "任务标签"
                }
            },
            "required": ["action"]
        },
        returns={
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "tasks": {
                    "type": "array",
                    "items": {"type": "object"}
                },
                "task_id": {"type": "string"}
            }
        },
        safety_level="low",
        category="task",
    ),
    UnifiedToolSchema(
        name="memory",
        description="持久化记忆：保存和检索用户信息、偏好设置和历史记录",
        source=ToolSource.HERMES,
        source_name="memory",
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["save", "retrieve", "search", "list", "delete"],
                    "description": "操作类型"
                },
                "key": {
                    "type": "string",
                    "description": "记忆键名"
                },
                "value": {
                    "type": "string",
                    "description": "要保存的记忆内容"
                },
                "category": {
                    "type": "string",
                    "description": "记忆分类: user_profile, preferences, facts, history",
                    "default": "general"
                },
                "query": {
                    "type": "string",
                    "description": "搜索查询"
                },
                "limit": {
                    "type": "integer",
                    "description": "返回数量限制",
                    "default": 10
                }
            },
            "required": ["action"]
        },
        returns={
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "value": {"type": "string"},
                "results": {"type": "array"}
            }
        },
        safety_level="low",
        category="task",
    ),
    UnifiedToolSchema(
        name="session_search",
        description="搜索历史会话内容",
        source=ToolSource.HERMES,
        source_name="session_search",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词"
                },
                "session_id": {
                    "type": "string",
                    "description": "指定会话 ID，不填则搜索所有"
                },
                "limit": {
                    "type": "integer",
                    "description": "返回结果数量",
                    "default": 5
                },
                "include_summary": {
                    "type": "boolean",
                    "description": "是否包含摘要",
                    "default": True
                }
            },
            "required": ["query"]
        },
        returns={
            "type": "object",
            "properties": {
                "sessions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"},
                            "summary": {"type": "string"},
                            "relevance": {"type": "number"}
                        }
                    }
                }
            }
        },
        safety_level="low",
        category="task",
    ),
]
