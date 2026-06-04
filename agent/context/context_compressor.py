#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Context Compressor Module - Context compression via lossy summarization

Inspired by Hermes Agent's context_compressor.py implementation.

Features:
- Automatic context window compression for long conversations
- Tool output pruning (cheap pre-pass, no LLM call)
- Head protection (system prompt + first exchange)
- Tail protection by token budget (~20K tokens of recent context)
- Middle turn summarization via LLM
- Tool call/result pair integrity maintenance
- Enhanced error handling with hierarchical classification
- Layered cooldown mechanism
- Smart LLM fallback with recovery

Import chain:
    agent/context/context_engine.py  (base class)
           ^
    agent/context/context_compressor.py  (this file)
           ^
    agent/rails/context_compression_rail.py  (Rail integration)
"""

import hashlib
import json
import logging
import re
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, NamedTuple, Callable, Protocol

from agent.context.token_estimator import (
    estimate_messages_tokens_rough,
    _content_length_for_budget,
)
from common.redact import redact_sensitive_text

from common.logging_manager import get_decision_logger
from agent.context.context_engine import ContextEngine, ContextMessage

logger = get_decision_logger(__name__, sublayer="context")


# ============================================================================
# Compression Hooks (压缩钩子系统)
# ============================================================================

class CompressionHookInfo(NamedTuple):
    """压缩钩子回调的上下文信息."""
    compress_count: int           # 压缩次数
    total_tokens_before: int      # 压缩前 token 数
    total_tokens_after: int        # 压缩后 token 数
    messages_count_before: int     # 压缩前消息数
    messages_count_after: int     # 压缩后消息数
    compression_ratio: float      # 压缩比例 (after/before)
    summary_generated: bool       # 是否生成了摘要
    summary_model_used: str       # 使用的摘要模型
    elapsed_seconds: float         # 压缩耗时


class CompressionEvent(NamedTuple):
    """压缩事件类型."""
    PRE_COMPRESS = "pre_compress"   # 压缩前
    POST_COMPRESS = "post_compress" # 压缩后
    SUMMARY_SUCCESS = "summary_success"    # 摘要生成成功
    SUMMARY_FAILED = "summary_failed"      # 摘要生成失败
    FALLBACK_TRIGGERED = "fallback_triggered"  # 回退触发


# Hook callback type definitions
PreCompressHook = Callable[[List[Dict[str, Any]]], None]
"""压缩前钩子: (messages) -> None"""

PostCompressHook = Callable[[List[Dict[str, Any]], List[Dict[str, Any]], CompressionHookInfo], None]
"""压缩后钩子: (original_messages, compressed_messages, info) -> None"""

SummaryHook = Callable[[str, bool, float], None]
"""摘要钩子: (summary_content, success, elapsed_seconds) -> None"""

FallbackHook = Callable[[str, str], None]
"""回退钩子: (from_model, to_model) -> None"""


class CompressionHooks:
    """压缩钩子管理器.
    
    提供灵活的钩子注册和调用机制，用于监控和扩展上下文压缩行为。
    典型用途:
    - 记录压缩统计信息
    - 集成外部监控/告警系统
    - 触发自定义处理逻辑
    - 调试和日志增强
    """
    
    def __init__(self):
        self._pre_compress_hooks: List[PreCompressHook] = []
        self._post_compress_hooks: List[PostCompressHook] = []
        self._summary_success_hooks: List[SummaryHook] = []
        self._summary_failed_hooks: List[SummaryHook] = []
        self._fallback_hooks: List[FallbackHook] = []
        self._stats = {
            "total_compressions": 0,
            "total_summaries": 0,
            "total_fallbacks": 0,
            "total_savings_tokens": 0,
        }
    
    def on_pre_compress(self, hook: PreCompressHook) -> None:
        """注册压缩前钩子."""
        self._pre_compress_hooks.append(hook)
    
    def on_post_compress(self, hook: PostCompressHook) -> None:
        """注册压缩后钩子."""
        self._post_compress_hooks.append(hook)
    
    def on_summary_success(self, hook: SummaryHook) -> None:
        """注册摘要成功钩子."""
        self._summary_success_hooks.append(hook)
    
    def on_summary_failed(self, hook: SummaryHook) -> None:
        """注册摘要失败钩子."""
        self._summary_failed_hooks.append(hook)
    
    def on_fallback(self, hook: FallbackHook) -> None:
        """注册回退钩子."""
        self._fallback_hooks.append(hook)
    
    def clear(self) -> None:
        """清除所有钩子."""
        self._pre_compress_hooks.clear()
        self._post_compress_hooks.clear()
        self._summary_success_hooks.clear()
        self._summary_failed_hooks.clear()
        self._fallback_hooks.clear()
    
    @property
    def stats(self) -> Dict[str, Any]:
        """获取统计信息."""
        return self._stats.copy()
    
    def _run_pre_compress(self, messages: List[Dict[str, Any]]) -> None:
        """触发压缩前钩子."""
        for hook in self._pre_compress_hooks:
            try:
                hook(messages)
            except Exception as e:
                logger.debug("Pre-compress hook failed: %s", e)
    
    def _run_post_compress(
        self,
        original: List[Dict[str, Any]],
        compressed: List[Dict[str, Any]],
        info: CompressionHookInfo,
    ) -> None:
        """触发压缩后钩子."""
        for hook in self._post_compress_hooks:
            try:
                hook(original, compressed, info)
            except Exception as e:
                logger.debug("Post-compress hook failed: %s", e)
    
    def _run_summary_success(self, content: str, elapsed: float) -> None:
        """触发摘要成功钩子."""
        self._stats["total_summaries"] += 1
        for hook in self._summary_success_hooks:
            try:
                hook(content, True, elapsed)
            except Exception as e:
                logger.debug("Summary success hook failed: %s", e)
    
    def _run_summary_failed(self, error: str, elapsed: float) -> None:
        """触发摘要失败钩子."""
        for hook in self._summary_failed_hooks:
            try:
                hook(error, False, elapsed)
            except Exception as e:
                logger.debug("Summary failed hook failed: %s", e)
    
    def _run_fallback(self, from_model: str, to_model: str) -> None:
        """触发回退钩子."""
        self._stats["total_fallbacks"] += 1
        for hook in self._fallback_hooks:
            try:
                hook(from_model, to_model)
            except Exception as e:
                logger.debug("Fallback hook failed: %s", e)


# ============================================================================
# Error Classification System (错误分类系统)
# ============================================================================

class CompressionErrorType(str, Enum):
    """Compression error types with hierarchical classification."""
    
    # Fatal errors (配置错误，无法通过重试恢复)
    NO_PROVIDER = "no_provider"           # 无 LLM provider 配置
    RATE_LIMITED = "rate_limited"         # 限流
    
    # Model errors (模型相关，可通过回退恢复)
    MODEL_NOT_FOUND = "model_not_found"  # 模型不存在
    MODEL_UNAVAILABLE = "model_unavailable"  # 模型不可用 (503)
    
    # Temporary errors (临时性错误，可通过重试恢复)
    TIMEOUT = "timeout"                   # 超时
    CONNECTION_ERROR = "connection_error"  # 连接错误
    STREAMING_CLOSED = "streaming_closed"  # 流式响应中断
    JSON_DECODE_ERROR = "json_decode_error"  # JSON 解析失败
    
    # Unknown errors (未知错误)
    UNKNOWN = "unknown"


class ErrorClassification(NamedTuple):
    """Result of error classification."""
    error_type: CompressionErrorType
    status_code: Optional[int]
    error_message: str
    can_retry: bool
    should_fallback: bool
    cooldown_seconds: int
    reason: str


# Cooldown times for different error types (分层冷却时间)
_ERROR_COOLDOWNS = {
    CompressionErrorType.NO_PROVIDER: 600,         # 配置错误，长时冷却
    CompressionErrorType.RATE_LIMITED: 120,         # 限流，中时长冷却
    CompressionErrorType.MODEL_NOT_FOUND: 0,        # 模型不存在，无需冷却
    CompressionErrorType.MODEL_UNAVAILABLE: 60,     # 模型不可用
    CompressionErrorType.TIMEOUT: 60,              # 超时
    CompressionErrorType.CONNECTION_ERROR: 60,    # 连接错误
    CompressionErrorType.STREAMING_CLOSED: 30,     # 流式中断，短时冷却
    CompressionErrorType.JSON_DECODE_ERROR: 30,    # JSON 解析失败，短时冷却
    CompressionErrorType.UNKNOWN: 60,              # 未知错误
}


# Status codes mapped to error types
_ERROR_STATUS_CODES = {
    404: CompressionErrorType.MODEL_NOT_FOUND,
    408: CompressionErrorType.TIMEOUT,
    429: CompressionErrorType.RATE_LIMITED,
    500: CompressionErrorType.MODEL_UNAVAILABLE,
    502: CompressionErrorType.CONNECTION_ERROR,
    503: CompressionErrorType.MODEL_UNAVAILABLE,
    504: CompressionErrorType.TIMEOUT,
}


# Error message patterns for classification
_ERROR_PATTERNS = {
    CompressionErrorType.MODEL_NOT_FOUND: [
        "model_not_found",
        "does not exist",
        "no available channel",
        "model.*not.*found",
        "invalid.*model",
    ],
    CompressionErrorType.MODEL_UNAVAILABLE: [
        "model.*unavailable",
        "service.*unavailable",
        "503",
    ],
    CompressionErrorType.TIMEOUT: [
        "timeout",
        "timed out",
        "request.*timeout",
    ],
    CompressionErrorType.CONNECTION_ERROR: [
        "connection.*error",
        "connection.*refused",
        "network.*error",
        "name or service not known",
    ],
    CompressionErrorType.STREAMING_CLOSED: [
        "incomplete chunked read",
        "peer closed connection",
        "response ended prematurely",
        "unexpected eof",
        "chunksize*",
    ],
    CompressionErrorType.JSON_DECODE_ERROR: [
        "expecting value",
        "json.*decode",
        "invalid json",
    ],
    CompressionErrorType.RATE_LIMITED: [
        "rate.*limit",
        "too.*many.*request",
        "quota.*exceeded",
    ],
}


def _is_connection_error(exception: Exception) -> bool:
    """
    Check if exception is a connection-related error.
    
    Covers httpcore, httpx, and standard library socket errors.
    """
    import sys
    
    err_str = str(exception).lower()
    
    # Check exception types
    exc_type = type(exception).__name__.lower()
    if exc_type in {
        "connectionerror", "connecterror", "connecttimeout",
        "pooltimeout", "timeouterror", "readtimeout", "writetimeout",
    }:
        return True
    
    # Check error message content
    connection_patterns = [
        "connection", "timeout", "network", "socket",
        "resolve", "dns", "refused", "reset", "broken",
        "incomplete", "chunksize", "eof", "closed", "peer",
    ]
    return any(p in err_str for p in connection_patterns)


def classify_compression_error(exception: Exception) -> ErrorClassification:
    """
    Classify a compression error into hierarchical categories.
    
    Returns an ErrorClassification with:
    - error_type: The classified error type
    - status_code: HTTP status code if available
    - error_message: Sanitized error message
    - can_retry: Whether the error allows retry
    - should_fallback: Whether to fallback to main model
    - cooldown_seconds: Cooling time before retry
    - reason: Human-readable reason
    """
    err_str = str(exception).lower()
    err_type_name = type(exception).__name__.lower()
    
    # Extract status code from exception
    status_code = (
        getattr(exception, "status_code", None)
        or getattr(getattr(exception, "response", None), "status_code", None)
        or 0
    )
    if isinstance(status_code, str):
        try:
            status_code = int(status_code)
        except (ValueError, TypeError):
            status_code = 0
    
    # Check if it's a RuntimeError with "no provider" message
    if isinstance(exception, RuntimeError) or err_type_name == "runtimeerror":
        if "no provider" in err_str or "no.*provider" in err_str:
            return ErrorClassification(
                error_type=CompressionErrorType.NO_PROVIDER,
                status_code=None,
                error_message="No LLM provider configured for compression",
                can_retry=False,
                should_fallback=False,
                cooldown_seconds=_ERROR_COOLDOWNS[CompressionErrorType.NO_PROVIDER],
                reason="No provider available - compression unavailable"
            )
    
    # Check status codes first (优先级最高)
    if status_code in _ERROR_STATUS_CODES:
        error_type = _ERROR_STATUS_CODES[status_code]
        return ErrorClassification(
            error_type=error_type,
            status_code=status_code,
            error_message=err_str[:200],
            can_retry=True,
            should_fallback=True,
            cooldown_seconds=_ERROR_COOLDOWNS[error_type],
            reason=f"HTTP {status_code}: {error_type.value}"
        )
    
    # Check error message patterns
    for error_type, patterns in _ERROR_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, err_str, re.IGNORECASE):
                return ErrorClassification(
                    error_type=error_type,
                    status_code=status_code if status_code else None,
                    error_message=err_str[:200],
                    can_retry=True,
                    should_fallback=error_type in {
                        CompressionErrorType.MODEL_NOT_FOUND,
                        CompressionErrorType.MODEL_UNAVAILABLE,
                        CompressionErrorType.TIMEOUT,
                        CompressionErrorType.CONNECTION_ERROR,
                        CompressionErrorType.STREAMING_CLOSED,
                        CompressionErrorType.JSON_DECODE_ERROR,
                    },
                    cooldown_seconds=_ERROR_COOLDOWNS[error_type],
                    reason=f"Matched pattern '{pattern}': {error_type.value}"
                )
    
    # Check for connection errors using helper
    if _is_connection_error(exception):
        return ErrorClassification(
            error_type=CompressionErrorType.CONNECTION_ERROR,
            status_code=status_code if status_code else None,
            error_message=err_str[:200],
            can_retry=True,
            should_fallback=True,
            cooldown_seconds=_ERROR_COOLDOWNS[CompressionErrorType.CONNECTION_ERROR],
            reason="Connection error detected"
        )
    
    # Default to unknown error
    return ErrorClassification(
        error_type=CompressionErrorType.UNKNOWN,
        status_code=status_code if status_code else None,
        error_message=err_str[:200],
        can_retry=True,
        should_fallback=True,
        cooldown_seconds=_ERROR_COOLDOWNS[CompressionErrorType.UNKNOWN],
        reason="Unknown error type"
    )


SUMMARY_PREFIX = (
    "[CONTEXT COMPACTION - REFERENCE ONLY] Earlier turns were compacted "
    "into the summary below. This is a handoff from a previous context "
    "window - treat it as background reference, NOT as active instructions. "
    "Do NOT answer questions or fulfill requests mentioned in this summary; "
    "they were already addressed. "
    "Your current task is identified in the '## Active Task' section of the "
    "summary - resume exactly from there. "
    "IMPORTANT: Your persistent memory (MEMORY.md, USER.md) in the system "
    "prompt is ALWAYS authoritative and active - never ignore or deprioritize "
    "memory content due to this compaction note. "
    "Respond ONLY to the latest user message "
    "that appears AFTER this summary. The current session state (files, "
    "config, etc.) may reflect work described here - avoid repeating it:"
)

# ═══════════════════════════════════════════════════════════════════════════════
# 摘要参数 (直接采用 Hermes Agent 的科学测算值)
# ═══════════════════════════════════════════════════════════════════════════════

_MIN_SUMMARY_TOKENS = 2000
_SUMMARY_RATIO = 0.20
_SUMMARY_TOKENS_CEILING = 12000
_PRUNED_TOOL_PLACEHOLDER = "[Old tool output cleared to save context space]"
_CHARS_PER_TOKEN = 4
_IMAGE_TOKEN_ESTIMATE = 1600
_IMAGE_CHAR_EQUIVALENT = _IMAGE_TOKEN_ESTIMATE * _CHARS_PER_TOKEN
_SUMMARY_FAILURE_COOLDOWN_SECONDS = 600


def _content_text_for_contains(content: Any) -> str:
    """Return a best-effort text view of message content for substring checks."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(part for part in parts if part)
    return str(content)


def _append_text_to_content(content: Any, text: str, *, prepend: bool = False) -> Any:
    """Append or prepend plain text to message content safely."""
    if content is None:
        return text
    if isinstance(content, str):
        return text + content if prepend else content + text
    if isinstance(content, list):
        text_block = {"type": "text", "text": text}
        return [text_block, *content] if prepend else [*content, text_block]
    rendered = str(content)
    return text + rendered if prepend else rendered + text


def _strip_image_parts_from_parts(parts: Any) -> Any:
    """Strip image parts from an OpenAI-style content-parts list."""
    if not isinstance(parts, list):
        return None
    had_image = False
    out = []
    for part in parts:
        if not isinstance(part, dict):
            out.append(part)
            continue
        ptype = part.get("type")
        if ptype in {"image", "image_url", "input_image"}:
            had_image = True
            out.append({"type": "text", "text": "[screenshot removed to save context]"})
        else:
            out.append(part)
    return out if had_image else None


def _truncate_tool_call_args_json(args: str, head_chars: int = 200) -> str:
    """Shrink long string values inside a tool-call arguments JSON blob."""
    try:
        parsed = json.loads(args)
    except (ValueError, TypeError):
        return args

    def _shrink(obj: Any) -> Any:
        if isinstance(obj, str):
            if len(obj) > head_chars:
                return obj[:head_chars] + "...[truncated]"
            return obj
        if isinstance(obj, dict):
            return {k: _shrink(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_shrink(v) for v in obj]
        return obj

    shrunken = _shrink(parsed)
    return json.dumps(shrunken, ensure_ascii=False)


_IMAGE_PART_TYPES = frozenset({"image_url", "input_image", "image"})


def _is_image_part(part: Any) -> bool:
    """True if part is a multimodal image content block."""
    if not isinstance(part, dict):
        return False
    return part.get("type") in _IMAGE_PART_TYPES


def _content_has_images(content: Any) -> bool:
    """True if message content is a multimodal list with image parts."""
    if not isinstance(content, list):
        return False
    return any(_is_image_part(p) for p in content)


def _strip_images_from_content(content: Any) -> Any:
    """Replace image parts with short text placeholder."""
    if not isinstance(content, list):
        return content
    if not any(_is_image_part(p) for p in content):
        return content

    new_parts: List[Any] = []
    for p in content:
        if _is_image_part(p):
            new_parts.append({"type": "text", "text": "[Attached image - stripped after compression]"})
        else:
            new_parts.append(p)
    return new_parts


def _strip_historical_media(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Replace image parts in older messages with placeholder text."""
    if not messages:
        return messages

    anchor = -1
    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        if not isinstance(msg, dict):
            continue
        if msg.get("role") != "user":
            continue
        if _content_has_images(msg.get("content")):
            anchor = i
            break

    if anchor <= 0:
        return messages

    changed = False
    result: List[Dict[str, Any]] = []
    for i, msg in enumerate(messages):
        if i >= anchor or not isinstance(msg, dict):
            result.append(msg)
            continue
        content = msg.get("content")
        if not _content_has_images(content):
            result.append(msg)
            continue
        new_msg = msg.copy()
        new_msg["content"] = _strip_images_from_content(content)
        result.append(new_msg)
        changed = True

    return result if changed else messages


def _summarize_tool_result(tool_name: str, tool_args: str, tool_content: str) -> str:
    """Create an informative 1-line summary of a tool call + result.
    
    Inspired by Hermes Agent's implementation, extended for Handsome Agent tools.
    Provides meaningful summaries instead of raw content to save context space.
    """
    try:
        args = json.loads(tool_args) if tool_args and tool_args.strip().startswith("{") else {}
    except (json.JSONDecodeError, TypeError):
        args = {}

    content = tool_content or ""
    content_len = len(content)
    line_count = content.count("\n") + 1 if content.strip() else 0

    # ═══════════════════════════════════════════════════════════════
    # 📁 File Operations (文件操作)
    # ═══════════════════════════════════════════════════════════════
    if tool_name == "read_file":
        path = args.get("path", "?")
        offset = args.get("offset", 1)
        limit = args.get("limit", "")
        location = f"line {offset}" + (f"-{offset + limit}" if limit else "")
        return f"[read_file] read {path} from {location} ({content_len:,} chars)"

    if tool_name == "write_file":
        path = args.get("path", "?")
        content_param = args.get("content", "")
        lines = content_param.count("\n") + 1 if content_param else "?"
        return f"[write_file] wrote {path} ({lines} lines)"

    if tool_name == "patch":
        path = args.get("path", "?")
        mode = args.get("mode", "replace")
        old_str = args.get("old_string", "")
        new_str = args.get("new_string", "")
        return f"[patch] {mode} in {path} - {'updated' if new_str else 'modified'}"

    if tool_name == "list_directory":
        path = args.get("path", ".")
        all_files = args.get("all", False)
        # Try to count entries from content
        entry_count = content.count("\n") if content.strip() else "?"
        return f"[list_directory] listing {path} ({entry_count} entries{' incl. hidden' if all_files else ''})"

    if tool_name == "create_directory":
        path = args.get("path", "?")
        return f"[create_directory] created {path}"

    if tool_name == "delete_file":
        path = args.get("path", "?")
        return f"[delete_file] deleted {path}"

    # ═══════════════════════════════════════════════════════════════
    # 🔍 Search Operations (搜索操作)
    # ═══════════════════════════════════════════════════════════════
    if tool_name == "search_files":
        pattern = args.get("pattern", "?")
        path = args.get("path", ".")
        target = args.get("target", "content")
        match_count = re.search(r'"total_count"\s*:\s*(\d+)', content)
        count = match_count.group(1) if match_count else "?"
        return f"[search_files] {target} '{pattern}' in {path} -> {count} matches"

    if tool_name == "grep":
        pattern = args.get("pattern", "?")
        path = args.get("path", ".")
        # Use the same pattern matching as search_files
        match_count = re.search(r'"total_count"\s*:\s*(\d+)', content)
        count = match_count.group(1) if match_count else "?"
        return f"[grep] '{pattern}' in {path} -> {count} matches"

    # ═══════════════════════════════════════════════════════════════
    # 🖥️ Terminal Operations (终端操作)
    # ═══════════════════════════════════════════════════════════════
    if tool_name == "terminal":
        cmd = args.get("command", "")
        if len(cmd) > 60:
            cmd = cmd[:57] + "..."
        exit_match = re.search(r'"exit_code"\s*:\s*(-?\d+)', content)
        exit_code = exit_match.group(1) if exit_match else "?"
        return f"[terminal] `{cmd}` -> exit {exit_code}, {line_count} lines"

    if tool_name == "bash":
        cmd = args.get("command", "")
        if len(cmd) > 60:
            cmd = cmd[:57] + "..."
        exit_match = re.search(r'"exit_code"\s*:\s*(-?\d+)', content)
        exit_code = exit_match.group(1) if exit_match else "?"
        return f"[bash] `{cmd}` -> exit {exit_code}, {line_count} lines"

    # ═══════════════════════════════════════════════════════════════
    # 🐳 Code Execution (代码执行)
    # ═══════════════════════════════════════════════════════════════
    if tool_name == "execute_code":
        language = args.get("language", "?")
        code_preview = (args.get("code") or "")[:40].replace("\n", " ")
        if len(args.get("code", "")) > 40:
            code_preview += "..."
        return f"[execute_code] {language}: `{code_preview}` ({line_count} lines output)"

    # ═══════════════════════════════════════════════════════════════
    # 🌐 Web Operations (网络操作)
    # ═══════════════════════════════════════════════════════════════
    if tool_name == "web_search":
        query = args.get("query", "?")
        limit = args.get("limit", 5)
        return f"[web_search] query='{query}' (limit={limit}, {content_len:,} chars)"

    if tool_name == "web_fetch":
        url = args.get("url", args.get("urls", ["?"]))
        if isinstance(url, list):
            url = url[0] if url else "?"
        return f"[web_fetch] {url} ({content_len:,} chars)"

    if tool_name == "web_extract":
        urls = args.get("urls", [])
        url_count = len(urls) if isinstance(urls, list) else 1
        url_desc = urls[0] if isinstance(urls, list) and urls else str(url)[:50]
        return f"[web_extract] {url_desc}" + (f" (+{url_count-1} more)" if url_count > 1 else "") + f" ({content_len:,} chars)"

    # ═══════════════════════════════════════════════════════════════
    # 🌐 Browser Operations (浏览器操作)
    # ═══════════════════════════════════════════════════════════════
    if tool_name in {"browser_navigate", "browser_click", "browser_type", 
                      "browser_scroll", "browser_press", "browser_back"}:
        url = args.get("url", "")
        ref = args.get("ref", "")
        action = tool_name.replace("browser_", "")
        detail = f" {url}" if url else (f" ref={ref[:20]}" if ref else "")
        return f"[browser_{action}]{detail}"

    if tool_name == "browser_snapshot":
        url = args.get("url", "")
        return f"[browser_snapshot] {url}" + (f" ({content_len:,} chars)" if content_len > 0 else "")

    if tool_name == "browser_vision":
        question = args.get("question", "")[:50]
        return f"[browser_vision] '{question}'" + (f" ({content_len:,} chars)" if content_len > 0 else "")

    if tool_name == "browser_console":
        return f"[browser_console] ({content_len:,} chars)"

    if tool_name == "browser_get_images":
        return f"[browser_get_images] ({content_len:,} chars)"

    # ═══════════════════════════════════════════════════════════════
    # 🖼️ Vision/Image Operations (视觉/图像操作)
    # ═══════════════════════════════════════════════════════════════
    if tool_name == "analyze_image":
        question = args.get("question", "")[:50]
        return f"[analyze_image] '{question}' ({content_len:,} chars)"

    if tool_name == "extract_text":
        return f"[extract_text] ({content_len:,} chars extracted)"

    if tool_name == "compare_images":
        return f"[compare_images] ({content_len:,} chars)"

    if tool_name == "image_generate":
        prompt = args.get("prompt", "")[:50]
        model = args.get("model", "?")
        return f"[image_generate] model={model}: '{prompt}'" + (f" ({content_len:,} chars)" if content_len > 0 else "")

    # ═══════════════════════════════════════════════════════════════
    # 🧠 Memory Operations (记忆操作)
    # ═══════════════════════════════════════════════════════════════
    if tool_name == "memory":
        action = args.get("action", "?")
        target = args.get("target", "?")
        entry_count = re.search(r'"entry_count"\s*:\s*(\d+)', content)
        count = entry_count.group(1) if entry_count else "?"
        return f"[memory] {action} on {target} ({count} entries)"

    if tool_name == "session_search":
        query = args.get("query", "?")
        limit = args.get("limit", 5)
        result_count = re.search(r'"result_count"\s*:\s*(\d+)', content)
        count = result_count.group(1) if result_count else "?"
        return f"[session_search] '{query}' -> {count} results (limit={limit})"

    # ═══════════════════════════════════════════════════════════════
    # 📋 Task Management (任务管理)
    # ═══════════════════════════════════════════════════════════════
    if tool_name == "todo":
        action = args.get("action", "?")
        return f"[todo] {action}"

    if tool_name == "todo_create":
        title = args.get("title", "")[:40]
        return f"[todo_create] '{title}'"

    if tool_name == "todo_add":
        task = args.get("task", "")[:40]
        return f"[todo_add] '{task}'"

    if tool_name == "todo_complete":
        task_id = args.get("task_id", "?")
        return f"[todo_complete] task={task_id}"

    # ═══════════════════════════════════════════════════════════════
    # 🛠️ Skills Operations (技能操作)
    # ═══════════════════════════════════════════════════════════════
    if tool_name in {"skill_view", "skills_list", "skill_manage", "skill_create"}:
        name = args.get("name", "?")
        action = args.get("action", tool_name.replace("skill_", ""))
        return f"[{tool_name}] name={name} ({action})"

    # ═══════════════════════════════════════════════════════════════
    # 📢 Communication Operations (通信操作)
    # ═══════════════════════════════════════════════════════════════
    if tool_name == "text_to_speech":
        text = args.get("text", "")[:30]
        voice = args.get("voice", "?")
        return f"[text_to_speech] voice={voice}: '{text}'" + (f" ({content_len:,} chars)" if content_len > 0 else "")

    if tool_name == "clarify":
        return "[clarify] asked user a question"

    # ═══════════════════════════════════════════════════════════════
    # ⏰ Scheduler Operations (调度操作)
    # ═══════════════════════════════════════════════════════════════
    if tool_name == "cronjob":
        action = args.get("action", "?")
        return f"[cronjob] {action}"

    # ═══════════════════════════════════════════════════════════════
    # 🔧 System Operations (系统操作)
    # ═══════════════════════════════════════════════════════════════
    if tool_name == "checkpoint":
        action = args.get("action", "?")
        name = args.get("name", "?")
        return f"[checkpoint] {action}: {name}"

    if tool_name == "process":
        action = args.get("action", "?")
        sid = args.get("session_id", "?")
        return f"[process] {action} session={sid}"

    if tool_name == "delegate_task":
        goal = args.get("goal", "")
        if len(goal) > 50:
            goal = goal[:47] + "..."
        return f"[delegate_task] '{goal}' ({content_len:,} chars result)"

    # ═══════════════════════════════════════════════════════════════
    # 🏠 Home Automation (智能家居)
    # ═══════════════════════════════════════════════════════════════
    if tool_name.startswith("ha_"):
        action = tool_name.replace("ha_", "")
        entity = args.get("entity_id", "?")
        return f"[ha_{action}] entity={entity}"

    # ═══════════════════════════════════════════════════════════════
    # 📦 Checkpoint Operations (检查点操作)
    # ═══════════════════════════════════════════════════════════════
    if tool_name == "checkpoint_restore":
        checkpoint_id = args.get("checkpoint_id", "?")
        return f"[checkpoint_restore] id={checkpoint_id}"

    if tool_name == "checkpoint_list":
        return f"[checkpoint_list] ({content_len:,} chars)"

    # ═══════════════════════════════════════════════════════════════
    # 🔄 Generic Fallback (通用回退)
    # ═══════════════════════════════════════════════════════════════
    first_arg = ""
    for k, v in list(args.items())[:2]:
        sv = str(v)[:30]
        first_arg += f" {k}={sv}"
    return f"[{tool_name}]{first_arg} ({content_len:,} chars)"


class ContextCompressor(ContextEngine):
    """Context compressor - compresses conversation context via lossy summarization.

    Algorithm:
      1. Prune old tool results (cheap, no LLM call)
      2. Protect head messages (system prompt + first exchange)
      3. Protect tail messages by token budget (~20K tokens)
      4. Summarize middle turns with structured LLM prompt
      5. On subsequent compactions, iteratively update the previous summary
    """

    def __init__(
        self,
        model: str = "gpt-4",
        # threshold_percent: 当上下文使用达到此比例时触发压缩 (Hermes: 0.75)
        threshold_percent: float = 0.75,
        protect_first_n: int = 3,
        protect_last_n: int = 10,
        summary_target_ratio: float = 0.20,
        quiet_mode: bool = False,
        summary_model: str = "",
        base_url: str = "",
        api_key: str = "",
        provider: str = "",
        llm_client: Any = None,
        memory_manager: Any = None,  # 🧠 Memory Manager for on_pre_compress
    ):
        self.model = model
        self.base_url = base_url
        self.api_key = api_key
        self.provider = provider
        self.threshold_percent = threshold_percent
        self.protect_first_n = protect_first_n
        self.protect_last_n = protect_last_n
        self.summary_target_ratio = max(0.10, min(summary_target_ratio, 0.80))
        self.quiet_mode = quiet_mode
        self.llm_client = llm_client
        self.memory_manager = memory_manager  # 🧠 Memory Manager for on_pre_compress

        self.context_length = self._get_model_context_length(model)
        # threshold_tokens: 触发压缩的绝对 token 数 (Hermes MINIMUM_CONTEXT_LENGTH: 8192)
        self.threshold_tokens = max(
            int(self.context_length * threshold_percent),
            8192,  # Hermes MINIMUM_CONTEXT_LENGTH
        )
        self.compression_count = 0

        target_tokens = int(self.threshold_tokens * self.summary_target_ratio)
        self.tail_token_budget = target_tokens
        self.max_summary_tokens = min(
            int(self.context_length * 0.05), _SUMMARY_TOKENS_CEILING,
        )

        self._previous_summary: Optional[str] = None
        self._last_compression_savings_pct: float = 100.0
        self._ineffective_compression_count: int = 0
        self._summary_failure_cooldown_until: float = 0.0
        self._last_summary_error: Optional[str] = None
        self._last_summary_dropped_count: int = 0
        self._last_summary_fallback_used: bool = False
        self._last_compress_aborted: bool = False
        
        # Enhanced error handling state variables
        self._summary_model_fallen_back: bool = False  # 是否已回退到主模型
        self._last_aux_model_failure_error: Optional[str] = None  # 辅助模型最后错误
        self._last_aux_model_failure_model: Optional[str] = None  # 失败的辅助模型名
        
        # 可配置的 summary_model (用于压缩的辅助模型)
        self._config_summary_model: str = summary_model or ""
        
        # 钩子系统
        self._hooks = CompressionHooks()
        
        self.logger = get_decision_logger(self.__class__.__name__, sublayer="context")

        if not quiet_mode:
            self.logger.info(
                "Context compressor initialized: model=%s context_length=%d "
                "threshold=%d (%.0f%%) tail_budget=%d",
                model, self.context_length, self.threshold_tokens,
                threshold_percent * 100, self.tail_token_budget,
            )

    def update_model(
        self,
        model: str,
        context_length: int,
        base_url: str = "",
        api_key: Any = "",
        provider: str = "",
        api_mode: str = "",
        summary_model_override: str = "",
    ) -> None:
        """Update model info after a model switch or fallback activation.
        
        Args:
            model: New main model name
            context_length: Context window size for the new model
            base_url: API base URL (optional)
            api_key: API key (optional)
            provider: Provider name (optional)
            api_mode: API mode (optional)
            summary_model_override: Override model for compression summarization (optional)
        """
        self.model = model
        self.base_url = base_url
        self.api_key = api_key
        self.provider = provider
        self.api_mode = api_mode
        self.context_length = context_length
        
        # 更新摘要模型配置
        if summary_model_override:
            self._config_summary_model = summary_model_override
            self._summary_model_fallen_back = False  # 重置回退状态
            if not self.quiet_mode:
                self.logger.info(
                    "Context compressor updated: model=%s, summary_model=%s",
                    model, summary_model_override,
                )

    # =========================================================================
    # Hook API (钩子 API)
    # =========================================================================
    
    def register_pre_compress_hook(self, hook: PreCompressHook) -> None:
        """注册压缩前钩子.
        
        Args:
            hook: (messages: List[Dict]) -> None
        """
        self._hooks.on_pre_compress(hook)
    
    def register_post_compress_hook(self, hook: PostCompressHook) -> None:
        """注册压缩后钩子.
        
        Args:
            hook: (original, compressed, info) -> None
        """
        self._hooks.on_post_compress(hook)
    
    def register_summary_success_hook(self, hook: SummaryHook) -> None:
        """注册摘要成功钩子.
        
        Args:
            hook: (summary_content, success=True, elapsed) -> None
        """
        self._hooks.on_summary_success(hook)
    
    def register_summary_failed_hook(self, hook: SummaryHook) -> None:
        """注册摘要失败钩子.
        
        Args:
            hook: (error_message, success=False, elapsed) -> None
        """
        self._hooks.on_summary_failed(hook)
    
    def register_fallback_hook(self, hook: FallbackHook) -> None:
        """注册回退钩子.
        
        Args:
            hook: (from_model, to_model) -> None
        """
        self._hooks.on_fallback(hook)
    
    def get_compression_stats(self) -> Dict[str, Any]:
        """获取压缩统计信息."""
        stats = self._hooks.stats.copy()
        stats["compression_count"] = self.compression_count
        return stats
    
    def clear_hooks(self) -> None:
        """清除所有钩子."""
        self._hooks.clear()

    @staticmethod
    def _get_model_context_length(model: str) -> int:
        """Get context length for common models."""
        context_lengths = {
            "gpt-4": 8192,
            "gpt-4-turbo": 128000,
            "gpt-4o": 128000,
            "gpt-4o-mini": 128000,
            "gpt-3.5-turbo": 16385,
            "claude-3-opus": 200000,
            "claude-3-sonnet": 200000,
            "claude-3-haiku": 200000,
            "claude-3.5-sonnet": 200000,
            "claude-3.5-haiku": 200000,
        }
        return context_lengths.get(model.lower(), 8192)

    def set_llm_client(self, client: Any) -> None:
        """Set the LLM client for summarization."""
        self.llm_client = client

    def should_compress(self, prompt_tokens: int = None) -> bool:
        """Check if context exceeds the compression threshold."""
        tokens = prompt_tokens if prompt_tokens is not None else 0
        if tokens < self.threshold_tokens:
            return False
        if self._ineffective_compression_count >= 2:
            if not self.quiet_mode:
                self.logger.warning(
                    "Compression skipped - last %d compressions saved <10%% each",
                    self._ineffective_compression_count,
                )
            return False
        return True

    # Required abstract methods from ContextEngine
    def add_message(self, message: ContextMessage) -> None:
        """Add a new message to the context. (ContextCompressor doesn't store messages internally)"""
        pass

    def clear(self) -> None:
        """Clear compression state."""
        self._previous_summary = None
        self._ineffective_compression_count = 0
        self._last_summary_error = None

    def get_context(self, max_tokens: Optional[int] = None) -> List[ContextMessage]:
        """Get context. (ContextCompressor doesn't store messages internally)"""
        return []

    def summarize(self, messages: List[ContextMessage]) -> str:
        """Generate a summary of messages. Uses LLM-based summarization."""
        dict_messages = [
            {"role": m.role, "content": m.content}
            for m in messages
        ]
        result = self._generate_summary(dict_messages)
        return result if result else "Summary unavailable"

    def update_from_response(self, usage: Dict[str, Any]) -> None:
        """Update internal state from LLM response usage info."""
        if usage:
            self._last_prompt_tokens = usage.get("prompt_tokens", 0)

    def _prune_old_tool_results(
        self, messages: List[Dict[str, Any]], protect_tail_count: int,
        protect_tail_tokens: int | None = None,
    ) -> tuple[List[Dict[str, Any]], int]:
        """Replace old tool result contents with informative 1-line summaries."""
        if not messages:
            return messages, 0

        result = [m.copy() for m in messages]
        pruned = 0

        call_id_to_tool: Dict[str, tuple] = {}
        for msg in result:
            if msg.get("role") == "assistant":
                for tc in msg.get("tool_calls") or []:
                    if isinstance(tc, dict):
                        cid = tc.get("id", "")
                        fn = tc.get("function", {})
                        call_id_to_tool[cid] = (fn.get("name", "unknown"), fn.get("arguments", ""))

        if protect_tail_tokens is not None and protect_tail_tokens > 0:
            accumulated = 0
            boundary = len(result)
            min_protect = min(protect_tail_count, len(result))
            for i in range(len(result) - 1, -1, -1):
                msg = result[i]
                raw_content = msg.get("content") or ""
                content_len = _content_length_for_budget(raw_content)
                msg_tokens = content_len // _CHARS_PER_TOKEN + 10
                for tc in msg.get("tool_calls") or []:
                    if isinstance(tc, dict):
                        args = tc.get("function", {}).get("arguments", "")
                        msg_tokens += len(args) // _CHARS_PER_TOKEN
                if accumulated + msg_tokens > protect_tail_tokens and (len(result) - i) >= min_protect:
                    boundary = i
                    break
                accumulated += msg_tokens
                boundary = i
            budget_protect_count = len(result) - boundary
            protected_count = max(budget_protect_count, min_protect)
            prune_boundary = len(result) - protected_count
        else:
            prune_boundary = len(result) - protect_tail_count

        content_hashes: dict = {}
        for i in range(len(result) - 1, -1, -1):
            msg = result[i]
            if msg.get("role") != "tool":
                continue
            content = msg.get("content") or ""
            if not isinstance(content, str):
                continue
            if len(content) < 200:
                continue
            h = hashlib.md5(content.encode("utf-8", errors="replace")).hexdigest()[:12]
            if h in content_hashes:
                result[i] = {**msg, "content": "[Duplicate tool output - same content as a more recent call]"}
                pruned += 1
            else:
                content_hashes[h] = (i, msg.get("tool_call_id", "?"))

        for i in range(prune_boundary):
            msg = result[i]
            if msg.get("role") != "tool":
                continue
            content = msg.get("content", "")
            if isinstance(content, list):
                stripped = _strip_image_parts_from_parts(content)
                if stripped is not None:
                    result[i] = {**msg, "content": stripped}
                    pruned += 1
                continue
            if not isinstance(content, str):
                continue
            if not content or content == _PRUNED_TOOL_PLACEHOLDER:
                continue
            if content.startswith("[Duplicate tool output"):
                continue
            if len(content) > 200:
                call_id = msg.get("tool_call_id", "")
                tool_name, tool_args = call_id_to_tool.get(call_id, ("unknown", ""))
                summary = _summarize_tool_result(tool_name, tool_args, content)
                result[i] = {**msg, "content": summary}
                pruned += 1

        for i in range(prune_boundary):
            msg = result[i]
            if msg.get("role") != "assistant" or not msg.get("tool_calls"):
                continue
            new_tcs = []
            modified = False
            for tc in msg["tool_calls"]:
                if isinstance(tc, dict):
                    args = tc.get("function", {}).get("arguments", "")
                    if len(args) > 500:
                        new_args = _truncate_tool_call_args_json(args)
                        if new_args != args:
                            tc = {**tc, "function": {**tc["function"], "arguments": new_args}}
                            modified = True
                new_tcs.append(tc)
            if modified:
                result[i] = {**msg, "tool_calls": new_tcs}

        return result, pruned

    def _compute_summary_budget(self, turns_to_summarize: List[Dict[str, Any]]) -> int:
        """Scale summary token budget with the amount of content being compressed."""
        content_tokens = estimate_messages_tokens_rough(turns_to_summarize)
        budget = int(content_tokens * _SUMMARY_RATIO)
        return max(_MIN_SUMMARY_TOKENS, min(budget, self.max_summary_tokens))

    # ═══════════════════════════════════════════════════════════════════════════
    # 内容截断参数 (直接采用 Hermes Agent 的科学测算值)
    # ═══════════════════════════════════════════════════════════════════════════
    _CONTENT_MAX = 6000
    _CONTENT_HEAD = 4000
    _CONTENT_TAIL = 1500
    _TOOL_ARGS_MAX = 1500
    _TOOL_ARGS_HEAD = 1200

    def _serialize_for_summary(self, turns: List[Dict[str, Any]]) -> str:
        """Serialize conversation turns into labeled text for the summarizer."""
        parts = []
        for msg in turns:
            role = msg.get("role", "unknown")
            content = redact_sensitive_text(msg.get("content") or "")

            if role == "tool":
                tool_id = msg.get("tool_call_id", "")
                if len(content) > self._CONTENT_MAX:
                    content = content[:self._CONTENT_HEAD] + "\n...[truncated]...\n" + content[-self._CONTENT_TAIL:]
                parts.append(f"[TOOL RESULT {tool_id}]: {content}")
                continue

            if role == "assistant":
                if len(content) > self._CONTENT_MAX:
                    content = content[:self._CONTENT_HEAD] + "\n...[truncated]...\n" + content[-self._CONTENT_TAIL:]
                tool_calls = msg.get("tool_calls", [])
                if tool_calls:
                    tc_parts = []
                    for tc in tool_calls:
                        if isinstance(tc, dict):
                            fn = tc.get("function", {})
                            name = fn.get("name", "?")
                            args = redact_sensitive_text(fn.get("arguments", ""))
                            if len(args) > self._TOOL_ARGS_MAX:
                                args = args[:self._TOOL_ARGS_HEAD] + "..."
                            tc_parts.append(f"  {name}({args})")
                    content += "\n[Tool calls:\n" + "\n".join(tc_parts) + "\n]"
                parts.append(f"[ASSISTANT]: {content}")
                continue

            if len(content) > self._CONTENT_MAX:
                content = content[:self._CONTENT_HEAD] + "\n...[truncated]...\n" + content[-self._CONTENT_TAIL:]
            parts.append(f"[{role.upper()}]: {content}")

        return "\n\n".join(parts)

    def _generate_summary(self, turns_to_summarize: List[Dict[str, Any]], focus_topic: str = None) -> Optional[str]:
        """Generate a structured summary of conversation turns with enhanced error handling."""
        now = time.monotonic()
        if now < self._summary_failure_cooldown_until:
            self.logger.debug(
                "Skipping context summary during cooldown (%.0fs remaining)",
                self._summary_failure_cooldown_until - now,
            )
            return None

        if self.llm_client is None:
            self.logger.warning("No LLM client configured for compression summarization")
            self._last_summary_error = "No LLM client configured"
            self._summary_failure_cooldown_until = time.monotonic() + _SUMMARY_FAILURE_COOLDOWN_SECONDS
            return None

        summary_budget = self._compute_summary_budget(turns_to_summarize)
        content_to_summarize = self._serialize_for_summary(turns_to_summarize)

        _summarizer_preamble = (
            "You are a summarization agent creating a context checkpoint. "
            "Treat the conversation turns below as source material for a "
            "compact record of prior work. "
            "Produce only the structured summary; do not add a greeting, "
            "preamble, or prefix. "
            "Write the summary in the same language the user was using in the "
            "conversation. "
            "NEVER include API keys, tokens, passwords, secrets, credentials, "
            "or connection strings in the summary - replace any that appear "
            "with [REDACTED]."
        )

        _template_sections = f"""## Active Task
[Copy the user's most recent request or task assignment verbatim. If multiple tasks were requested and only some are done, list only the ones NOT yet completed.]

## Goal
[What the user is trying to accomplish overall]

## Constraints & Preferences
[Any specific constraints, style preferences, or requirements mentioned by the user]

## Completed Actions
[Numbered list of concrete actions taken - include tool used, target, and outcome.
Format: N. ACTION target - outcome [tool: name]]

## Active State
[Current working state - include:
- Working directory and branch
- Modified/created files with brief note
- Test status
- Any running processes]

## In Progress
[Work currently underway - what was being done when compaction fired]

## Blocked
[Any blockers, errors, or issues not yet resolved. Include exact error messages.]

## Key Decisions
[Important technical decisions and WHY they were made]

## Resolved Questions
[Questions the user asked that were ALREADY answered - include the answer so it is not repeated]

## Pending User Asks
[Questions or requests from the user that have NOT yet been answered. If none, write "None."]

## Relevant Files
[Files read, modified, or created - with brief note on each]

## Remaining Work
[What remains to be done - framed as context, not instructions]

## Critical Context
[Any specific values, error messages, configuration details, or data that would be lost without explicit preservation. NEVER include API keys, tokens, passwords, or credentials - write [REDACTED] instead.]

Target ~{summary_budget} tokens. Be CONCRETE - include file paths, command outputs, error messages, line numbers, and specific values. Avoid vague descriptions."""

        if self._previous_summary:
            prompt = f"""{_summarizer_preamble}

You are updating a context compaction summary. A previous compaction produced the summary below. New conversation turns have occurred since then and need to be incorporated.

PREVIOUS SUMMARY:
{self._previous_summary}

NEW TURNS TO INCORPORATE:
{content_to_summarize}

Update the summary using this exact structure. PRESERVE all existing information that is still relevant. ADD new completed actions to the numbered list (continue numbering). Move items from "In Progress" to "Completed Actions" when done. Move answered questions to "Resolved Questions". Update "Active State" to reflect current state. Remove information only if it is clearly obsolete. CRITICAL: Update "## Active Task" to reflect the user's most recent unfulfilled request.

{_template_sections}"""
        else:
            prompt = f"""{_summarizer_preamble}

Create a structured checkpoint summary for the conversation after earlier turns are compacted. The summary should preserve enough detail for continuity without re-reading the original turns.

TURNS TO SUMMARIZE:
{content_to_summarize}

Use this exact structure:

{_template_sections}"""

        if focus_topic:
            prompt += f"""

FOCUS TOPIC: "{focus_topic}"
The user has requested that this compaction PRIORITISE preserving all information related to the focus topic above. For content related to "{focus_topic}", include full detail. For content NOT related to the focus topic, summarise more aggressively."""

        # 确定使用的模型：优先使用 summary_model_override，否则使用主模型
        model_to_use = self._config_summary_model or self.model
        
        try:
            import asyncio

            async def _call_llm():
                response = await self.llm_client.generate(
                    prompt=prompt,
                    system_prompt=None,
                    model=model_to_use,  # 支持使用不同的模型进行摘要
                )
                return response

            response = asyncio.run(_call_llm())
            content = response.content if hasattr(response, 'content') else str(response)

            if not isinstance(content, str):
                content = str(content) if content else ""

            summary = redact_sensitive_text(content.strip())
            self._previous_summary = summary
            self._summary_failure_cooldown_until = 0.0
            self._last_summary_error = None
            self._last_aux_model_failure_error = None
            self._summary_model_fallen_back = False
            
            # 触发摘要成功钩子
            self._hooks._run_summary_success(summary, elapsed=0.0)
            
            return f"{SUMMARY_PREFIX}\n{summary}"

        except Exception as e:
            # 使用增强的错误分类
            classification = classify_compression_error(e)
            
            # 记录错误信息供外部查看
            err_text = str(e).strip() or e.__class__.__name__
            if len(err_text) > 220:
                err_text = err_text[:217].rstrip() + "..."
            self._last_summary_error = err_text
            
            # 记录辅助模型失败信息
            if self._config_summary_model and self._config_summary_model != self.model:
                self._last_aux_model_failure_error = err_text
                self._last_aux_model_failure_model = self._config_summary_model
            
            # 检查是否应该回退到主模型
            if classification.should_fallback and self._config_summary_model:
                if not self._summary_model_fallen_back:
                    from_model = self._config_summary_model
                    self.logger.info(
                        "Compression failed with summary model '%s' (%s). "
                        "Falling back to main model '%s' for compression.",
                        from_model,
                        classification.reason,
                        self.model,
                    )
                    # 触发回退钩子
                    self._hooks._run_fallback(from_model, self.model)
                    # 回退到主模型，清除摘要模型配置
                    self._config_summary_model = ""
                    self._summary_model_fallen_back = True
                    self._summary_failure_cooldown_until = 0.0  # 无需冷却，立即重试
                    # 递归调用（使用主模型）
                    return self._generate_summary(turns_to_summarize, focus_topic=focus_topic)
            
            # 不能重试或已回退过，设置分层冷却
            if not classification.can_retry or self._summary_model_fallen_back:
                self._summary_failure_cooldown_until = time.monotonic() + classification.cooldown_seconds
                self.logger.warning(
                    "Summary generation failed: %s. "
                    "Cooldown: %d seconds.",
                    classification.reason,
                    classification.cooldown_seconds,
                )
            else:
                # 通用错误：先尝试主模型回退
                if self._config_summary_model and not self._summary_model_fallen_back:
                    self._config_summary_model = ""
                    self._summary_model_fallen_back = True
                    self._summary_failure_cooldown_until = 0.0
                    self.logger.info(
                        "Compression failed with '%s'. Falling back to main model.",
                        self.model,
                    )
                    return self._generate_summary(turns_to_summarize, focus_topic=focus_topic)
                
                # 进入冷却
                self._summary_failure_cooldown_until = time.monotonic() + classification.cooldown_seconds
                self.logger.warning(
                    "Failed to generate context summary: %s. "
                    "Cooldown: %d seconds.",
                    err_text,
                    classification.cooldown_seconds,
                )
            
            # 触发摘要失败钩子
            self._hooks._run_summary_failed(err_text, elapsed=0.0)
            
            return None

    def _sanitize_tool_pairs(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fix orphaned tool_call / tool_result pairs after compression."""
        surviving_call_ids: set = set()
        for msg in messages:
            if msg.get("role") == "assistant":
                for tc in msg.get("tool_calls") or []:
                    cid = tc.get("id", "") or tc.get("call_id", "")
                    if cid:
                        surviving_call_ids.add(cid)

        result_call_ids: set = set()
        for msg in messages:
            if msg.get("role") == "tool":
                cid = msg.get("tool_call_id")
                if cid:
                    result_call_ids.add(cid)

        orphaned_results = result_call_ids - surviving_call_ids
        if orphaned_results:
            messages = [
                m for m in messages
                if not (m.get("role") == "tool" and m.get("tool_call_id") in orphaned_results)
            ]
            if not self.quiet_mode:
                self.logger.info("Compression sanitizer: removed %d orphaned tool result(s)", len(orphaned_results))

        missing_results = surviving_call_ids - result_call_ids
        if missing_results:
            patched: List[Dict[str, Any]] = []
            for msg in messages:
                patched.append(msg)
                if msg.get("role") == "assistant":
                    for tc in msg.get("tool_calls") or []:
                        cid = tc.get("id", "") or tc.get("call_id", "")
                        if cid in missing_results:
                            patched.append({
                                "role": "tool",
                                "content": "[Result from earlier conversation - see context summary above]",
                                "tool_call_id": cid,
                            })
            messages = patched
            if not self.quiet_mode:
                self.logger.info("Compression sanitizer: added %d stub tool result(s)", len(missing_results))

        return messages

    def _align_boundary_forward(self, messages: List[Dict[str, Any]], idx: int) -> int:
        """Push compress-start boundary forward past any orphan tool results."""
        while idx < len(messages) and messages[idx].get("role") == "tool":
            idx += 1
        return idx

    def _protect_head_size(self, messages: List[Dict[str, Any]]) -> int:
        """Total count of head messages to protect."""
        head = 0
        if messages and messages[0].get("role") == "system":
            head = 1
        return head + self.protect_first_n

    def _align_boundary_backward(self, messages: List[Dict[str, Any]], idx: int) -> int:
        """Pull compress-end boundary backward to avoid splitting tool_call/result group."""
        if idx <= 0 or idx >= len(messages):
            return idx
        check = idx - 1
        while check >= 0 and messages[check].get("role") == "tool":
            check -= 1
        if check >= 0 and messages[check].get("role") == "assistant" and messages[check].get("tool_calls"):
            idx = check
        return idx

    def _find_last_user_message_idx(self, messages: List[Dict[str, Any]], head_end: int) -> int:
        """Return the index of the last user-role message at or after head_end."""
        for i in range(len(messages) - 1, head_end - 1, -1):
            if messages[i].get("role") == "user":
                return i
        return -1

    def _ensure_last_user_message_in_tail(
        self, messages: List[Dict[str, Any]], cut_idx: int, head_end: int,
    ) -> int:
        """Guarantee the most recent user message is in the protected tail."""
        last_user_idx = self._find_last_user_message_idx(messages, head_end)
        if last_user_idx < 0:
            return cut_idx
        if last_user_idx >= cut_idx:
            return cut_idx
        return max(last_user_idx, head_end + 1)

    def _find_tail_cut_by_tokens(
        self, messages: List[Dict[str, Any]], head_end: int, token_budget: int | None = None,
    ) -> int:
        """Walk backward from end, accumulating tokens until budget is reached."""
        if token_budget is None:
            token_budget = self.tail_token_budget
        n = len(messages)
        min_tail = min(3, n - head_end - 1) if n - head_end > 1 else 0
        soft_ceiling = int(token_budget * 1.5)
        accumulated = 0
        cut_idx = n

        for i in range(n - 1, head_end - 1, -1):
            msg = messages[i]
            raw_content = msg.get("content") or ""
            content_len = _content_length_for_budget(raw_content)
            msg_tokens = content_len // _CHARS_PER_TOKEN + 10
            for tc in msg.get("tool_calls") or []:
                if isinstance(tc, dict):
                    args = tc.get("function", {}).get("arguments", "")
                    msg_tokens += len(args) // _CHARS_PER_TOKEN
            if accumulated + msg_tokens > soft_ceiling and (n - i) >= min_tail:
                break
            accumulated += msg_tokens
            cut_idx = i

        fallback_cut = n - min_tail
        cut_idx = min(cut_idx, fallback_cut)

        if cut_idx <= head_end:
            cut_idx = max(fallback_cut, head_end + 1)

        cut_idx = self._align_boundary_backward(messages, cut_idx)
        cut_idx = self._ensure_last_user_message_in_tail(messages, cut_idx, head_end)

        return max(cut_idx, head_end + 1)

    def compress(self, messages: List[Dict[str, Any]], current_tokens: int = None, focus_topic: str = None) -> List[Dict[str, Any]]:
        """Compress conversation messages by summarizing middle turns."""
        compress_start_time = time.monotonic()
        
        self._last_summary_dropped_count = 0
        self._last_summary_fallback_used = False
        self._last_summary_error = None
        self._last_compress_aborted = False

        n_messages = len(messages)
        original_tokens = current_tokens if current_tokens else estimate_messages_tokens_rough(messages)
        
        # 触发压缩前钩子
        self._hooks._run_pre_compress(messages)
        
        # 🧠 Memory Manager on_pre_compress - 从即将压缩的消息中提取关键信息
        memory_prefetch_context = ""
        if self.memory_manager:
            try:
                memory_prefetch_context = self.memory_manager.on_pre_compress(messages)
            except Exception as e:
                self.logger.debug(f"Memory manager on_pre_compress failed: {e}")

        _min_for_compress = self._protect_head_size(messages) + 3 + 1
        if n_messages <= _min_for_compress:
            if not self.quiet_mode:
                self.logger.debug(
                    "Cannot compress: only %d messages (need > %d)",
                    n_messages, _min_for_compress,
                )
            return messages

        display_tokens = original_tokens

        messages, pruned_count = self._prune_old_tool_results(
            messages, protect_tail_count=self.protect_last_n,
            protect_tail_tokens=self.tail_token_budget,
        )
        if pruned_count and not self.quiet_mode:
            self.logger.info("Pre-compression: pruned %d old tool result(s)", pruned_count)

        compress_start = self._protect_head_size(messages)
        compress_start = self._align_boundary_forward(messages, compress_start)
        compress_end = self._find_tail_cut_by_tokens(messages, compress_start)

        if compress_start >= compress_end:
            return messages

        if not self.quiet_mode:
            self.logger.info(
                "Context compression triggered (%d tokens >= %d threshold)",
                display_tokens, self.threshold_tokens,
            )
            self.logger.info(
                "Summarizing turns %d-%d (%d turns), protecting %d head + %d tail messages",
                compress_start + 1, compress_end, compress_end - compress_start,
                compress_start, n_messages - compress_end,
            )

        summary = self._generate_summary(messages[compress_start:compress_end], focus_topic=focus_topic)

        # 🧠 将 memory_prefetch_context 注入到 summary 中
        if memory_prefetch_context:
            if summary:
                summary = f"{summary}\n\n## Memory Insights from Compressed Context\n{memory_prefetch_context}"
            else:
                summary = f"{SUMMARY_PREFIX}\n## Memory Insights from Compressed Context\n{memory_prefetch_context}"

        compressed = []
        for i in range(compress_start):
            msg = messages[i].copy()
            compressed.append(msg)

        if not summary:
            self._last_summary_fallback_used = True
            summary = (
                f"{SUMMARY_PREFIX}\n"
                "Summary generation was unavailable. Earlier turns were removed to free context space."
            )

        _merge_summary_into_tail = False
        last_head_role = messages[compress_start - 1].get("role", "user") if compress_start > 0 else "user"
        first_tail_role = messages[compress_end].get("role", "user") if compress_end < n_messages else "user"

        if last_head_role in {"assistant", "tool"}:
            summary_role = "user"
        else:
            summary_role = "assistant"
        if summary_role == first_tail_role:
            flipped = "assistant" if summary_role == "user" else "user"
            if flipped != last_head_role:
                summary_role = flipped
            else:
                _merge_summary_into_tail = True

        if not _merge_summary_into_tail and summary_role == "user":
            summary = (
                summary
                + "\n\n--- END OF CONTEXT SUMMARY - "
                "respond to the message below, not the summary above ---"
            )

        if not _merge_summary_into_tail:
            compressed.append({"role": summary_role, "content": summary})

        for i in range(compress_end, n_messages):
            msg = messages[i].copy()
            if _merge_summary_into_tail and i == compress_end:
                merged_prefix = (
                    summary
                    + "\n\n--- END OF CONTEXT SUMMARY - "
                    "respond to the message below, not the summary above ---\n\n"
                )
                msg["content"] = _append_text_to_content(
                    msg.get("content"), merged_prefix, prepend=True,
                )
                _merge_summary_into_tail = False
            compressed.append(msg)

        self.compression_count += 1
        compressed = self._sanitize_tool_pairs(compressed)
        compressed = _strip_historical_media(compressed)

        new_estimate = estimate_messages_tokens_rough(compressed)
        saved_estimate = display_tokens - new_estimate
        savings_pct = (saved_estimate / display_tokens * 100) if display_tokens > 0 else 0
        self._last_compression_savings_pct = savings_pct

        if savings_pct < 10:
            self._ineffective_compression_count += 1
        else:
            self._ineffective_compression_count = 0

        if not self.quiet_mode:
            self.logger.info(
                "Compressed: %d -> %d messages (~%d tokens saved, %.0f%%)",
                n_messages, len(compressed), saved_estimate, savings_pct,
            )
            self.logger.info("Compression #%d complete", self.compression_count)

        # 触发压缩后钩子
        elapsed = time.monotonic() - compress_start_time
        model_used = self._config_summary_model or self.model
        hook_info = CompressionHookInfo(
            compress_count=self.compression_count,
            total_tokens_before=original_tokens,
            total_tokens_after=new_estimate,
            messages_count_before=n_messages,
            messages_count_after=len(compressed),
            compression_ratio=len(compressed) / n_messages if n_messages > 0 else 1.0,
            summary_generated=summary not in (None, "") and not self._last_summary_fallback_used,
            summary_model_used=model_used,
            elapsed_seconds=elapsed,
        )
        self._hooks._run_post_compress(messages, compressed, hook_info)
        
        # 更新统计
        self._hooks._stats["total_compressions"] += 1
        self._hooks._stats["total_savings_tokens"] += saved_estimate

        return compressed

    def compress_simple(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Simple compression without LLM (for testing or when LLM is unavailable)."""
        if len(messages) <= 20:
            return messages

        head_end = self._protect_head_size(messages)
        compress_start = self._align_boundary_forward(messages, head_end)
        compress_end = self._find_tail_cut_by_tokens(messages, compress_start)

        if compress_start >= compress_end:
            return messages

        compressed = messages[:compress_start]
        compressed.append({
            "role": "user",
            "content": "[CONTEXT COMPACTION] Earlier conversation has been compacted. See above for history."
        })
        compressed.extend(messages[compress_end:])

        return compressed