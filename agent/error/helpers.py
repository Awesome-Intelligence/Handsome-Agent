"""错误处理辅助函数

提供错误摘要生成、错误上下文提取和 API Key 脱敏功能。
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional


def summarize_api_error(error: Exception) -> str:
    """生成用户友好的错误摘要

    Handles Cloudflare HTML error pages (502, 503, etc.) by pulling the
    <title> tag instead of dumping raw HTML. Falls back to a truncated
    str(error) for everything else.

    Args:
        error: API 错误异常

    Returns:
        str: 用户友好的错误摘要
    """
    raw = str(error)

    if (
        isinstance(error, ValueError)
        and "expected ident at line" in raw.lower()
    ):
        return f"Malformed provider streaming response: {raw[:300]}"

    # Cloudflare / proxy HTML pages: grab the <title> for a clean summary
    if "<!DOCTYPE" in raw or "<html" in raw:
        m = re.search(r"<title[^>]*>([^<]+)</title>", raw, re.IGNORECASE)
        title = m.group(1).strip() if m else "HTML error page (title not found)"
        ray = re.search(r"Cloudflare Ray ID:\s*<strong[^>]*>([^<]+)</strong>", raw)
        ray_id = ray.group(1).strip() if ray else None
        status_code = getattr(error, "status_code", None)
        parts = []
        if status_code:
            parts.append(f"HTTP {status_code}")
        parts.append(title)
        if ray_id:
            parts.append(f"Ray {ray_id}")
        return " — ".join(parts)

    # JSON body errors from OpenAI/Anthropic SDKs
    body = getattr(error, "body", None)
    if isinstance(body, dict):
        msg = body.get("error", {}).get("message") if isinstance(body.get("error"), dict) else body.get("message")
        if msg:
            status_code = getattr(error, "status_code", None)
            prefix = f"HTTP {status_code}: " if status_code else ""
            return f"{prefix}{msg[:300]}"

    # Fallback: truncate the raw string but give more room than 200 chars
    status_code = getattr(error, "status_code", None)
    prefix = f"HTTP {status_code}: " if status_code else ""
    return f"{prefix}{raw[:500]}"


def extract_api_error_context(error: Exception) -> Dict[str, Any]:
    """提取错误上下文信息

    Args:
        error: API 错误异常

    Returns:
        Dict[str, Any]: 包含错误上下文字典
    """
    context: Dict[str, Any] = {
        "error_type": type(error).__name__,
        "status_code": None,
        "message": str(error)[:500],
        "provider": "",
        "model": "",
    }

    # 提取状态码
    current = error
    for _ in range(5):
        code = getattr(current, "status_code", None)
        if isinstance(code, int):
            context["status_code"] = code
            break
        cause = getattr(current, "__cause__", None) or getattr(current, "__context__", None)
        if cause is None or cause is current:
            break
        current = cause

    # 提取 body
    body = getattr(error, "body", None)
    if isinstance(body, dict):
        error_obj = body.get("error", {})
        if isinstance(error_obj, dict):
            context["message"] = str(error_obj.get("message") or error_obj)[:500]
            context["error_code"] = error_obj.get("code") or error_obj.get("type") or ""
        else:
            context["message"] = str(body.get("message") or body)[:500]

    return context


def mask_api_key_for_logs(key: Any) -> Optional[str]:
    """对 API Key 进行脱敏处理

    Args:
        key: API Key 或可调用对象

    Returns:
        Optional[str]: 脱敏后的字符串
    """
    if callable(key) and not isinstance(key, str):
        return "<entra-id-bearer>"
    if not key:
        return None
    
    key_str = str(key)
    if len(key_str) <= 8:
        return "*" * len(key_str)
    
    return f"{key_str[:4]}...{key_str[-4:]}"


def classify_tool_error(error: Exception) -> Dict[str, Any]:
    """分类工具执行错误

    Args:
        error: 工具执行时抛出的异常

    Returns:
        Dict[str, Any]: 包含错误分类结果
    """
    error_type = type(error).__name__
    error_msg = str(error)

    return {
        "error_type": error_type,
        "message": error_msg,
        "retryable": False,
        "fallback": False,
    }
