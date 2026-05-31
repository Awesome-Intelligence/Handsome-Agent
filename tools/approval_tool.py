#!/usr/bin/env python3
"""
Approval Tool Module - 审批工具

提供请求用户审批的功能，用于危险操作。

参考 Hermes Agent 的 approval_tool.py 实现。
"""

import json
import logging
from typing import Dict, Any, Optional
from tools.registry import registry

logger = logging.getLogger(__name__)


def request_approval(
    action: str,
    description: str,
    details: Optional[str] = None,
) -> str:
    """
    请求用户审批。

    Args:
        action: 要执行的操作
        description: 操作描述
        details: 可选的详细信息

    Returns:
        JSON 格式的结果字符串
    """
    # 这里实现请求审批的逻辑
    # 由于是简化版本，我们直接返回一个模拟的响应
    # 在实际实现中，这应该与终端 UI 或其他交互系统集成
    
    return json.dumps({
        "success": True,
        "approved": False,
        "message": "Approval tool requires user interaction. This is a placeholder implementation.",
        "action": action,
        "description": description,
        "details": details,
    }, ensure_ascii=False)


def check_approval_requirements() -> bool:
    """审批工具无外部依赖，始终可用"""
    return True


# 工具定义
APPROVAL_SCHEMA = {
    "name": "request_approval",
    "description": "Request user approval for potentially dangerous actions. Use this before executing commands that modify system state, delete files, or perform other irreversible operations.",
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "The action to be performed (e.g., 'delete_file', 'execute_command')."
            },
            "description": {
                "type": "string",
                "description": "A clear description of what the action will do."
            },
            "details": {
                "type": "string",
                "description": "Optional additional details about the action (e.g., the full command to be executed)."
            },
        },
        "required": ["action", "description"],
    },
}


# 注册工具
registry.register(
    name="request_approval",
    toolset="approval",
    schema=APPROVAL_SCHEMA,
    handler=lambda args, **kw: request_approval(
        action=args.get("action", ""),
        description=args.get("description", ""),
        details=args.get("details"),
    ),
    check_fn=check_approval_requirements,
    emoji="✅",
)
