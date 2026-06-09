#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Session Search Tool Module

Provides functionality for searching through conversation history.

Based on Hermes Agent's session_search_tool.py implementation.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

from common.logging_manager import get_execution_logger
from tools.registry import registry

logger = get_execution_logger("SessionSearchTool")


def _get_session_db_path() -> Optional[Path]:
    """获取会话数据库路径"""
    try:
        from common.config import settings
        # 尝试从配置获取数据库路径
        db_path = getattr(settings, 'SESSION_DB_PATH', None)
        if db_path:
            path = Path(db_path)
            if path.exists():
                return path
        
        # 尝试常见位置
        default_paths = [
            Path.home() / ".handsome_agent" / "sessions.db",
            Path.home() / ".hermes" / "sessions.db",
        ]
        for p in default_paths:
            if p.exists():
                return p
    except Exception as e:
        logger.debug(f"Could not find session db path: {e}")
    return None


def session_search(
    query: str,
    limit: int = 5,
    session_id: Optional[str] = None,
    role_filter: Optional[str] = None,
    sort: str = "desc",
    **kwargs
) -> str:
    """
    Search through conversation history.

    Args:
        query: Search query string
        limit: Maximum number of results to return
        session_id: Filter by specific session ID
        role_filter: Filter by role (user/assistant/system)
        sort: Sort order (asc/desc)
        **kwargs: Additional parameters (db, current_session_id, etc.)

    Returns:
        JSON string with search results
    """
    db_path = kwargs.get('db') or _get_session_db_path()
    
    if not db_path:
        return json.dumps({
            "success": False,
            "error": "Session database not found",
            "results": []
        }, ensure_ascii=False)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 构建查询
        sql_parts = ["SELECT id, session_id, role, content, timestamp FROM messages"]
        params: List[Any] = []
        conditions = []
        
        if query:
            conditions.append("content LIKE ?")
            params.append(f"%{query}%")
        
        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)
        
        if role_filter:
            conditions.append("role = ?")
            params.append(role_filter)
        
        if conditions:
            sql_parts.append("WHERE " + " AND ".join(conditions))
        
        # 排序
        order = "DESC" if sort == "desc" else "ASC"
        sql_parts.append(f"ORDER BY timestamp {order}")
        
        # 限制
        sql_parts.append("LIMIT ?")
        params.append(limit)
        
        sql = " ".join(sql_parts)
        cursor.execute(sql, params)
        
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            results.append({
                "id": row[0],
                "session_id": row[1],
                "role": row[2],
                "content": row[3][:500] if row[3] else "",  # 截断长内容
                "timestamp": row[4]
            })
        
        return json.dumps({
            "success": True,
            "query": query,
            "count": len(results),
            "results": results
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Session search error: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "results": []
        }, ensure_ascii=False)


def check_session_search_requirements() -> bool:
    """检查会话搜索工具是否可用"""
    db_path = _get_session_db_path()
    return db_path is not None


# Schema definition
SESSION_SEARCH_SCHEMA = {
    "name": "session_search",
    "description": "Search through conversation history in current and past sessions.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query string to match in conversation content"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results to return",
                "default": 5
            },
            "session_id": {
                "type": "string",
                "description": "Filter by specific session ID (optional)"
            },
            "role_filter": {
                "type": "string",
                "description": "Filter by role: user, assistant, or system",
                "enum": ["user", "assistant", "system"]
            },
            "sort": {
                "type": "string",
                "description": "Sort order: asc (oldest first) or desc (newest first)",
                "enum": ["asc", "desc"],
                "default": "desc"
            }
        },
        "required": ["query"]
    },
}


# Register the tool
registry.register(
    name="session_search",
    toolset="session_search",
    schema=SESSION_SEARCH_SCHEMA,
    handler=lambda args, **kw: session_search(
        query=args.get("query", ""),
        limit=args.get("limit", 5),
        session_id=args.get("session_id"),
        role_filter=args.get("role_filter"),
        sort=args.get("sort", "desc"),
        **kw
    ),
    check_fn=check_session_search_requirements,
    emoji="🔍",
)
