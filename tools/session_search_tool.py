#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Session Search Tool Module

Provides functionality for searching through conversation history with three modes:
1. DISCOVERY - FTS5 search with lineage deduplication and bookends
2. SCROLL - Window scrolling around a specific message
3. BROWSE - List recent sessions

Based on Hermes Agent's session_search_tool.py implementation.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from common.logging_manager import get_execution_logger
from common.state import HermesState
from tools.registry import registry

logger = get_execution_logger("SessionSearchTool")


def _get_hermes_state() -> Optional[HermesState]:
    """Get HermesState instance."""
    try:
        return HermesState()
    except Exception as e:
        logger.debug(f"Could not create HermesState: {e}")
        return None


def _format_timestamp(ts: float) -> str:
    """Format timestamp for display."""
    dt = datetime.fromtimestamp(ts)
    return dt.strftime("%B %d, %Y at %I:%M %p")


def _format_hit_for_display(hit: Dict) -> str:
    """Format a search hit for display."""
    lines = []
    lines.append(f"Session: {hit.get('session_id', 'unknown')[:16]}...")
    lines.append(f"When: {hit.get('when', 'unknown')}")
    lines.append(f"Match: {hit.get('snippet', hit.get('content', ''))}")
    lines.append("---")
    return "\n".join(lines)


def session_search(
    query: Optional[str] = None,
    limit: int = 3,
    session_id: Optional[str] = None,
    around_message_id: Optional[int] = None,
    window: int = 5,
    role_filter: Optional[str] = None,
    sort: str = "rank",
    **kwargs
) -> str:
    """
    Session search tool with three calling shapes.

    THREE CALLING SHAPES:

    1) DISCOVERY — pass `query`:
       session_search(query="auth refactor", limit=3)
       Returns: snippet + bookend_start + messages + bookend_end

    2) SCROLL — pass `session_id` + `around_message_id`:
       session_search(session_id="xxx", around_message_id=12345, window=10)
       Forward scroll: pass messages[-1].id
       Backward scroll: pass messages[0].id

    3) BROWSE — no args:
       session_search()
       Returns recent sessions list

    FTS5 SYNTAX: AND (default), OR, NOT, "phrase", prefix*

    Args:
        query: Search query string
        limit: Maximum number of results (default: 3, max: 10)
        session_id: Filter by specific session ID
        around_message_id: Message ID to anchor scroll view
        window: Window size for scroll view (±window messages)
        role_filter: Filter by role (user, assistant, system)
        sort: Sort order (rank, newest, oldest)
        **kwargs: Additional parameters (db, current_session_id, etc.)

    Returns:
        JSON string with search results
    """
    db = kwargs.get('db')
    current_session_id = kwargs.get('current_session_id')

    # Create HermesState from db path or direct instance
    if db and isinstance(db, (str, Path)):
        state = HermesState(str(db))
    else:
        state = _get_hermes_state()

    if not state:
        return json.dumps({
            "success": False,
            "error": "Session database not available",
            "results": []
        }, ensure_ascii=False)

    try:
        # SCROLL mode: session_id + around_message_id
        if session_id and around_message_id is not None:
            return _scroll_mode(state, session_id, around_message_id, window, current_session_id)

        # BROWSE mode: no query
        if not query or not query.strip():
            return _browse_mode(state, limit, current_session_id)

        # DISCOVERY mode: query provided
        return _discovery_mode(state, query, limit, role_filter, sort, current_session_id)

    except Exception as e:
        logger.error(f"Session search error: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "results": []
        }, ensure_ascii=False)
    finally:
        state.close()


def _discovery_mode(
    state: HermesState,
    query: str,
    limit: int,
    role_filter: Optional[str],
    sort: str,
    current_session_id: Optional[str]
) -> str:
    """
    DISCOVERY mode: FTS5 search with lineage deduplication and bookends.
    """
    # Resolve current lineage root to skip
    current_lineage_root = None
    if current_session_id:
        current_lineage_root = state.resolve_lineage_root(current_session_id)

    # Perform advanced search
    hits = state.search_messages_advanced(
        query=query,
        exclude_sources=["tool"],  # Exclude tool sessions for cleaner results
        role_filter=role_filter,
        current_lineage_root=current_lineage_root,
        limit=min(limit, 10),
        sort=sort if sort != "rank" else "rank"
    )

    # Format results
    results = []
    for hit in hits:
        # Get session info
        session = state.get_session(hit.session_id)
        when = _format_timestamp(hit.timestamp) if hit.timestamp else "unknown"

        result = {
            "session_id": hit.session_id,
            "title": f"Session from {when}",
            "when": when,
            "snippet": hit.snippet,
            "match_message_id": hit.message_id,
            "bookend_start": [
                {"role": m["role"], "content": m["content"][:200]}
                for m in hit.bookend_start[:2]
            ],
            "messages": [
                {"role": m["role"], "content": m["content"][:300]}
                for m in hit.messages[:7]
            ],
            "bookend_end": [
                {"role": m["role"], "content": m["content"][:200]}
                for m in hit.bookend_end[:2]
            ]
        }
        results.append(result)

    return json.dumps({
        "success": True,
        "mode": "DISCOVERY",
        "query": query,
        "count": len(results),
        "results": results
    }, ensure_ascii=False)


def _scroll_mode(
    state: HermesState,
    session_id: str,
    around_message_id: int,
    window: int,
    current_session_id: Optional[str]
) -> str:
    """
    SCROLL mode: Get window around a specific message.
    """
    # Verify not in current session lineage
    if current_session_id:
        scroll_root = state.resolve_lineage_root(session_id)
        current_root = state.resolve_lineage_root(current_session_id)
        if scroll_root == current_root:
            return json.dumps({
                "success": False,
                "error": "Cannot scroll within current session lineage. Use /new to start a fresh session.",
                "results": []
            }, ensure_ascii=False)

    # Get anchored view
    bookend_start, messages, bookend_end = state.get_anchored_view(
        session_id, around_message_id, window=window, bookend=3
    )

    if not messages:
        return json.dumps({
            "success": False,
            "error": f"No messages found for session {session_id} around message {around_message_id}",
            "results": []
        }, ensure_ascii=False)

    # Format results
    results = {
        "session_id": session_id,
        "anchor_message_id": around_message_id,
        "window": window,
        "bookend_start": [
            {"id": m["id"], "role": m["role"], "content": m["content"][:200]}
            for m in bookend_start
        ],
        "messages": [
            {
                "id": m["id"],
                "role": m["role"],
                "content": m["content"][:500],
                "is_anchor": m["id"] == around_message_id if isinstance(m["id"], int) else False
            }
            for m in messages
        ],
        "bookend_end": [
            {"id": m["id"], "role": m["role"], "content": m["content"][:200]}
            for m in bookend_end
        ],
        "scroll_hint": {
            "forward": f"Use session_search(session_id='{session_id}', around_message_id={messages[-1]['id']}) to scroll forward",
            "backward": f"Use session_search(session_id='{session_id}', around_message_id={messages[0]['id']}) to scroll backward"
        }
    }

    return json.dumps({
        "success": True,
        "mode": "SCROLL",
        "count": len(messages),
        "results": results
    }, ensure_ascii=False)


def _browse_mode(
    state: HermesState,
    limit: int,
    current_session_id: Optional[str]
) -> str:
    """
    BROWSE mode: List recent sessions.
    """
    # Resolve current lineage root to skip
    current_lineage_root = None
    if current_session_id:
        current_lineage_root = state.resolve_lineage_root(current_session_id)

    # Get recent sessions
    sessions = state.list_recent_sessions(
        limit=min(limit, 10),
        exclude_sources=["tool"],
        current_lineage_root=current_lineage_root
    )

    # Format results
    results = []
    for s in sessions:
        results.append({
            "session_id": s["session_id"],
            "title": s.get("title", "Untitled"),
            "preview": s.get("preview", "")[:150],
            "message_count": s.get("message_count", 0),
            "last_active": _format_timestamp(s["last_active"]) if s.get("last_active") else "unknown",
            "created_at": _format_timestamp(s["created_at"]) if s.get("created_at") else "unknown"
        })

    return json.dumps({
        "success": True,
        "mode": "BROWSE",
        "count": len(results),
        "results": results
    }, ensure_ascii=False)


def check_session_search_requirements() -> bool:
    """Check if session search tool is available."""
    state = _get_hermes_state()
    if state:
        state.close()
        return True
    return False


# Schema definition
SESSION_SEARCH_SCHEMA = {
    "name": "session_search",
    "description": """
Session search with THREE CALLING SHAPES:

1) DISCOVERY — pass `query`:
   session_search(query="auth refactor", limit=3)
   Returns: snippet + bookend_start + messages + bookend_end

2) SCROLL — pass `session_id` + `around_message_id`:
   session_search(session_id="xxx", around_message_id=12345, window=10)
   Forward scroll: pass messages[-1].id
   Backward scroll: pass messages[0].id

3) BROWSE — no args:
   session_search()
   Returns recent sessions list

FTS5 SYNTAX: AND (default), OR, NOT, "phrase", prefix*
""",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query for DISCOVERY mode (FTS5 syntax supported)"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results",
                "default": 3,
                "minimum": 1,
                "maximum": 10
            },
            "session_id": {
                "type": "string",
                "description": "Session ID for SCROLL mode"
            },
            "around_message_id": {
                "type": "integer",
                "description": "Message ID to anchor SCROLL view"
            },
            "window": {
                "type": "integer",
                "description": "Window size for SCROLL (±window messages)",
                "default": 5,
                "minimum": 1,
                "maximum": 20
            },
            "role_filter": {
                "type": "string",
                "description": "Filter by role",
                "enum": ["user", "assistant", "system"]
            },
            "sort": {
                "type": "string",
                "description": "Sort order",
                "enum": ["rank", "newest", "oldest"],
                "default": "rank"
            }
        }
    },
}


# Register the tool
registry.register(
    name="session_search",
    toolset="session_search",
    schema=SESSION_SEARCH_SCHEMA,
    handler=lambda args, **kw: session_search(
        query=args.get("query"),
        limit=args.get("limit", 3),
        session_id=args.get("session_id"),
        around_message_id=args.get("around_message_id"),
        window=args.get("window", 5),
        role_filter=args.get("role_filter"),
        sort=args.get("sort", "rank"),
        **kw
    ),
    check_fn=check_session_search_requirements,
    emoji="🔍",
)
