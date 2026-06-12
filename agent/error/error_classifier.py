"""API 错误分类器

提供结构化的 LLM API 错误分类能力，包含多种错误类型的模式匹配和恢复建议。
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# ── Error taxonomy ──────────────────────────────────────────────────────

class FailoverReason(enum.Enum):
    """错误原因枚举 - 决定恢复策略"""

    # 认证/授权
    auth = "auth"                        # 临时认证问题 - 刷新/轮换
    auth_permanent = "auth_permanent"    # 永久认证失败 - 中止

    # 计费/配额
    billing = "billing"                  # 402 或额度耗尽 - 立即轮换
    rate_limit = "rate_limit"            # 429 或限流 - 退避后轮换

    # 服务端
    overloaded = "overloaded"            # 503/529 - 退避
    server_error = "server_error"        # 500/502 - 重试

    # 传输
    timeout = "timeout"                  # 连接/读取超时 - 重建客户端

    # 上下文/负载
    context_overflow = "context_overflow"  # 上下文过长 - 压缩
    payload_too_large = "payload_too_large"  # 413 - 压缩
    image_too_large = "image_too_large"   # 图片过大 - 缩小重试

    # 模型
    model_not_found = "model_not_found"  # 404 或无效模型 - 回退
    provider_policy_blocked = "provider_policy_blocked"  # 聚合器阻止

    # 请求格式
    format_error = "format_error"        # 400 坏请求 - 中止或精简重试
    multimodal_tool_content_unsupported = "multimodal_tool_content_unsupported"  # 不支持多模态工具内容

    # 工具执行
    tool_error = "tool_error"            # 工具执行错误

    # Rails
    rail_blocked = "rail_blocked"       # Rails 拦截

    # 未知
    unknown = "unknown"                  # 不可分类 - 退避重试


# ── Classification result ───────────────────────────────────────────────

@dataclass
class ClassifiedError:
    """结构化错误分类结果，包含恢复建议"""

    reason: FailoverReason
    status_code: Optional[int] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    message: str = ""
    error_context: Dict[str, Any] = field(default_factory=dict)

    # 恢复建议
    retryable: bool = True
    should_compress: bool = False
    should_rotate_credential: bool = False
    should_fallback: bool = False

    @property
    def is_auth(self) -> bool:
        return self.reason in {FailoverReason.auth, FailoverReason.auth_permanent}


# ── Error patterns ──────────────────────────────────────────────────────

# 计费/配额耗尽模式
_BILLING_PATTERNS = [
    "insufficient credits",
    "insufficient_quota",
    "insufficient balance",
    "credit balance",
    "credits have been exhausted",
    "top up your credits",
    "payment required",
    "billing hard limit",
    "exceeded your current quota",
    "account is deactivated",
    "plan does not include",
    # 中文
    "额度不足",
    "配额不足",
    "余额不足",
    "账户已停用",
    "套餐不支持",
]

# 速率限制模式
_RATE_LIMIT_PATTERNS = [
    "rate limit",
    "rate_limit",
    "too many requests",
    "throttled",
    "requests per minute",
    "tokens per minute",
    "requests per day",
    "try again in",
    "please retry after",
    "resource_exhausted",
    "too many concurrent requests",
    # 中文
    "请求过于频繁",
    "限流",
    "稍后重试",
    "请稍后再试",
]

# 上下文溢出模式
_CONTEXT_OVERFLOW_PATTERNS = [
    "context length",
    "context size",
    "maximum context",
    "token limit",
    "too many tokens",
    "reduce the length",
    "exceeds the limit",
    "context window",
    "prompt is too long",
    "prompt exceeds max length",
    "max_tokens",
    "maximum number of tokens",
    "max_model_len",
    "prompt length",
    "input is too long",
    # 中文
    "上下文长度",
    "超过最大长度",
    "上下文溢出",
    "token 超出限制",
    "上下文过长",
    "消息太长",
]

# 认证失败模式
_AUTH_PATTERNS = [
    "invalid api key",
    "invalid_api_key",
    "authentication",
    "unauthorized",
    "forbidden",
    "invalid token",
    "token expired",
    "token revoked",
    "access denied",
    # 中文
    "认证失败",
    "授权失败",
    "无效的密钥",
    "密钥无效",
]

# 超时消息模式
_TIMEOUT_MESSAGE_PATTERNS = [
    "timed out",
    "turn timed out",
    "request timed out",
    "deadline exceeded",
    "operation timed out",
    "upstream timed out",
    "timeout",
    # 中文
    "超时",
    "连接超时",
]

# 传输错误类型
_TRANSPORT_ERROR_TYPES = frozenset({
    "ReadTimeout", "ConnectTimeout", "PoolTimeout",
    "ConnectError", "RemoteProtocolError",
    "ConnectionError", "ConnectionResetError",
    "ConnectionAbortedError", "BrokenPipeError",
    "TimeoutError", "ReadError",
    "ServerDisconnectedError",
    "SSLError", "SSLZeroReturnError",
})

# 图片过大模式
_IMAGE_TOO_LARGE_PATTERNS = [
    "image exceeds",
    "image too large",
    "image_too_large",
    "image size exceeds",
    # 中文
    "图片过大",
    "图片尺寸超出",
]

# 模型未找到模式
_MODEL_NOT_FOUND_PATTERNS = [
    "is not a valid model",
    "invalid model",
    "model not found",
    "model_not_found",
    "does not exist",
    "no such model",
    "unknown model",
    "unsupported model",
    # 中文
    "模型不存在",
    "模型未找到",
    "不支持的模型",
]


# ── Classification pipeline ─────────────────────────────────────────────

def classify_api_error(
    error: Exception,
    *,
    provider: str = "",
    model: str = "",
    approx_tokens: int = 0,
    context_length: int = 200000,
    num_messages: int = 0,
) -> ClassifiedError:
    """分类 API 错误为结构化的恢复建议

    Args:
        error: API 调用抛出的异常
        provider: 当前 provider 名称
        model: 当前模型名称
        approx_tokens: 当前上下文的大致 token 数
        context_length: 当前模型的最大上下文长度

    Returns:
        ClassifiedError: 包含原因和恢复建议的结构化分类结果
    """
    status_code = _extract_status_code(error)
    error_type = type(error).__name__
    
    # 强制 429 处理 RateLimitError
    if status_code is None and error_type == "RateLimitError":
        status_code = 429
        
    body = _extract_error_body(error)
    error_code = _extract_error_code(body)

    # 构建错误消息字符串用于模式匹配
    _raw_msg = str(error).lower()
    _body_msg = ""
    if isinstance(body, dict):
        _err_obj = body.get("error", {})
        if isinstance(_err_obj, dict):
            _body_msg = str(_err_obj.get("message") or "").lower()
        if not _body_msg:
            _body_msg = str(body.get("message") or "").lower()
    
    parts = [_raw_msg]
    if _body_msg and _body_msg not in _raw_msg:
        parts.append(_body_msg)
    error_msg = " ".join(parts)

    def _result(reason: FailoverReason, **overrides) -> ClassifiedError:
        defaults = {
            "reason": reason,
            "status_code": status_code,
            "provider": provider,
            "model": model,
            "message": _extract_message(error, body),
        }
        defaults.update(overrides)
        return ClassifiedError(**defaults)

    # ── 1. HTTP 状态码分类 ──────────────────────────────

    if status_code is not None:
        classified = _classify_by_status(
            status_code, error_msg, error_code, body,
            provider=provider, model=model,
            approx_tokens=approx_tokens, context_length=context_length,
            result_fn=_result,
        )
        if classified is not None:
            return classified

    # ── 2. 错误码分类 ───────────────────────────────

    if error_code:
        classified = _classify_by_error_code(error_code, error_msg, _result)
        if classified is not None:
            return classified

    # ── 3. 消息模式匹配 ─────────────────────────────

    classified = _classify_by_message(
        error_msg, error_type,
        approx_tokens=approx_tokens,
        context_length=context_length,
        result_fn=_result,
    )
    if classified is not None:
        return classified

    # ── 4. 传输/超时启发式 ─────────────────────────

    if error_type in _TRANSPORT_ERROR_TYPES or isinstance(error, (TimeoutError, ConnectionError, OSError)):
        return _result(FailoverReason.timeout, retryable=True)

    # ── 5. 回退：未知 ───────────────────────────────

    return _result(FailoverReason.unknown, retryable=True)


# ── Status code classification ─────────────────────────────────────────

def _classify_by_status(
    status_code: int,
    error_msg: str,
    error_code: str,
    body: dict,
    *,
    provider: str,
    model: str,
    approx_tokens: int,
    context_length: int,
    result_fn,
) -> Optional[ClassifiedError]:
    """基于 HTTP 状态码分类"""

    if status_code == 401:
        return result_fn(
            FailoverReason.auth,
            retryable=False,
            should_rotate_credential=True,
            should_fallback=True,
        )

    if status_code == 403:
        if "key limit exceeded" in error_msg or "spending limit" in error_msg:
            return result_fn(
                FailoverReason.billing,
                retryable=False,
                should_rotate_credential=True,
                should_fallback=True,
            )
        return result_fn(
            FailoverReason.auth,
            retryable=False,
            should_fallback=True,
        )

    if status_code == 402:
        return result_fn(
            FailoverReason.billing,
            retryable=False,
            should_rotate_credential=True,
            should_fallback=True,
        )

    if status_code == 404:
        if any(p in error_msg for p in _MODEL_NOT_FOUND_PATTERNS):
            return result_fn(
                FailoverReason.model_not_found,
                retryable=False,
                should_fallback=True,
            )
        return result_fn(FailoverReason.unknown, retryable=True)

    if status_code == 413:
        return result_fn(
            FailoverReason.payload_too_large,
            retryable=True,
            should_compress=True,
        )

    if status_code == 429:
        return result_fn(
            FailoverReason.rate_limit,
            retryable=True,
            should_rotate_credential=True,
            should_fallback=True,
        )

    if status_code == 400:
        return _classify_400(
            error_msg, error_code, body,
            provider=provider, model=model,
            approx_tokens=approx_tokens,
            context_length=context_length,
            result_fn=result_fn,
        )

    if status_code in {500, 502}:
        return result_fn(FailoverReason.server_error, retryable=True)

    if status_code in {503, 529}:
        return result_fn(FailoverReason.overloaded, retryable=True)

    # 其他 4xx - 不可重试
    if 400 <= status_code < 500:
        return result_fn(
            FailoverReason.format_error,
            retryable=False,
            should_fallback=True,
        )

    # 其他 5xx - 可重试
    if 500 <= status_code < 600:
        return result_fn(FailoverReason.server_error, retryable=True)

    return None


def _classify_400(
    error_msg: str,
    error_code: str,
    body: dict,
    *,
    provider: str,
    model: str,
    approx_tokens: int,
    context_length: int,
    result_fn,
) -> ClassifiedError:
    """分类 400 错误"""

    # 图片过大
    if any(p in error_msg for p in _IMAGE_TOO_LARGE_PATTERNS):
        return result_fn(
            FailoverReason.image_too_large,
            retryable=True,
        )

    # 上下文溢出
    if any(p in error_msg for p in _CONTEXT_OVERFLOW_PATTERNS):
        return result_fn(
            FailoverReason.context_overflow,
            retryable=True,
            should_compress=True,
        )

    # 模型未找到
    if any(p in error_msg for p in _MODEL_NOT_FOUND_PATTERNS):
        return result_fn(
            FailoverReason.model_not_found,
            retryable=False,
            should_fallback=True,
        )

    # 速率限制
    if any(p in error_msg for p in _RATE_LIMIT_PATTERNS):
        return result_fn(
            FailoverReason.rate_limit,
            retryable=True,
            should_rotate_credential=True,
            should_fallback=True,
        )

    # 计费问题
    if any(p in error_msg for p in _BILLING_PATTERNS):
        return result_fn(
            FailoverReason.billing,
            retryable=False,
            should_rotate_credential=True,
            should_fallback=True,
        )

    # 大上下文 + 通用错误消息 → 可能是上下文溢出
    is_large = approx_tokens > context_length * 0.4
    if is_large:
        return result_fn(
            FailoverReason.context_overflow,
            retryable=True,
            should_compress=True,
        )

    # 不可重试的格式错误
    return result_fn(
        FailoverReason.format_error,
        retryable=False,
        should_fallback=True,
    )


# ── Error code classification ───────────────────────────────────────────

def _classify_by_error_code(
    error_code: str, error_msg: str, result_fn,
) -> Optional[ClassifiedError]:
    """基于错误码分类"""
    code_lower = error_code.lower()

    if code_lower in {"resource_exhausted", "throttled", "rate_limit_exceeded"}:
        return result_fn(
            FailoverReason.rate_limit,
            retryable=True,
            should_rotate_credential=True,
        )

    if code_lower in {"insufficient_quota", "billing_not_active", "payment_required"}:
        return result_fn(
            FailoverReason.billing,
            retryable=False,
            should_rotate_credential=True,
            should_fallback=True,
        )

    if code_lower in {"model_not_found", "model_not_available", "invalid_model"}:
        return result_fn(
            FailoverReason.model_not_found,
            retryable=False,
            should_fallback=True,
        )

    if code_lower in {"context_length_exceeded", "max_tokens_exceeded"}:
        return result_fn(
            FailoverReason.context_overflow,
            retryable=True,
            should_compress=True,
        )

    return None


# ── Message pattern classification ──────────────────────────────────────

def _classify_by_message(
    error_msg: str,
    error_type: str,
    *,
    approx_tokens: int,
    context_length: int,
    result_fn,
) -> Optional[ClassifiedError]:
    """基于错误消息模式分类"""

    # 计费问题
    if any(p in error_msg for p in _BILLING_PATTERNS):
        return result_fn(
            FailoverReason.billing,
            retryable=False,
            should_rotate_credential=True,
            should_fallback=True,
        )

    # 速率限制
    if any(p in error_msg for p in _RATE_LIMIT_PATTERNS):
        return result_fn(
            FailoverReason.rate_limit,
            retryable=True,
            should_rotate_credential=True,
            should_fallback=True,
        )

    # 上下文溢出
    if any(p in error_msg for p in _CONTEXT_OVERFLOW_PATTERNS):
        return result_fn(
            FailoverReason.context_overflow,
            retryable=True,
            should_compress=True,
        )

    # 认证问题
    if any(p in error_msg for p in _AUTH_PATTERNS):
        return result_fn(
            FailoverReason.auth,
            retryable=False,
            should_rotate_credential=True,
            should_fallback=True,
        )

    # 超时消息
    if any(p in error_msg for p in _TIMEOUT_MESSAGE_PATTERNS):
        return result_fn(FailoverReason.timeout, retryable=True)

    # 图片过大
    if any(p in error_msg for p in _IMAGE_TOO_LARGE_PATTERNS):
        return result_fn(
            FailoverReason.image_too_large,
            retryable=True,
        )

    return None


# ── Helpers ─────────────────────────────────────────────────────────────

def _extract_status_code(error: Exception) -> Optional[int]:
    """从异常及其原因链中提取 HTTP 状态码"""
    current = error
    for _ in range(5):
        code = getattr(current, "status_code", None)
        if isinstance(code, int):
            return code
        code = getattr(current, "status", None)
        if isinstance(code, int) and 100 <= code < 600:
            return code
        cause = getattr(current, "__cause__", None) or getattr(current, "__context__", None)
        if cause is None or cause is current:
            break
        current = cause
    return None


def _extract_error_body(error: Exception) -> dict:
    """从 SDK 异常中提取结构化错误体"""
    body = getattr(error, "body", None)
    if isinstance(body, dict):
        return body
    response = getattr(error, "response", None)
    if response is not None:
        try:
            json_body = response.json()
            if isinstance(json_body, dict):
                return json_body
        except Exception:
            pass
    return {}


def _extract_error_code(body: dict) -> str:
    """从响应体中提取错误码字符串"""
    if not body:
        return ""
    error_obj = body.get("error", {})
    if isinstance(error_obj, dict):
        code = error_obj.get("code") or error_obj.get("type") or ""
        if isinstance(code, str) and code.strip():
            return code.strip()
    code = body.get("code") or body.get("error_code") or ""
    if isinstance(code, (str, int)):
        return str(code).strip()
    return ""


def _extract_message(error: Exception, body: dict) -> str:
    """提取最有信息量的错误消息"""
    if body:
        error_obj = body.get("error", {})
        if isinstance(error_obj, dict):
            msg = error_obj.get("message", "")
            if isinstance(msg, str) and msg.strip():
                return msg.strip()[:500]
        msg = body.get("message", "")
        if isinstance(msg, str) and msg.strip():
            return msg.strip()[:500]
    return str(error)[:500]