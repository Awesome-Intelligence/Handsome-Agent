#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Error Classifier - API 错误分类器

提供结构化的 API 错误分类，用于智能故障转移和恢复。

功能：
1. 错误原因分类（认证、计费、限流、上下文溢出等）
2. 恢复策略建议（重试、压缩、切换凭证、回退等）
3. 提供详细的错误上下文

参考 Hermes 的 agent/error_classifier.py 实现。

日志子层：🧠 Decision
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from common.logging_manager import get_decision_logger

# ═══════════════════════════════════════════════════════════════════════════════
# 错误原因枚举
# ═══════════════════════════════════════════════════════════════════════════════

class FailoverReason(enum.Enum):
    """API 调用失败的原因 - 决定恢复策略"""

    # 认证/授权
    auth = "auth"                        # 临时认证错误 (401/403) - 刷新/轮换
    auth_permanent = "auth_permanent"    # 刷新后仍失败 - 中止

    # 计费/配额
    billing = "billing"                  # 402 或确认额度耗尽 - 立即轮换
    rate_limit = "rate_limit"            # 429 或基于配额的限流 - 退避后轮换

    # 服务端
    overloaded = "overloaded"            # 503/529 - 提供商过载，退避
    server_error = "server_error"        # 500/502 - 内部服务器错误，重试

    # 传输
    timeout = "timeout"                  # 连接/读取超时 - 重建客户端 + 重试

    # 上下文/负载
    context_overflow = "context_overflow"  # 上下文过大 - 压缩，不是故障转移
    payload_too_large = "payload_too_large"  # 413 - 压缩负载

    # 模型
    model_not_found = "model_not_found"  # 404 或无效模型 - 回退到不同模型

    # 请求格式
    format_error = "format_error"        # 400 错误请求 - 中止或剥离 + 重试

    # 提供商特定
    provider_unavailable = "provider_unavailable"  # 提供商不可用

    # 捕获全部
    unknown = "unknown"                  # 无法分类 - 带退避重试


# ═══════════════════════════════════════════════════════════════════════════════
# 分类结果
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ClassifiedError:
    """结构化的 API 错误分类，包含恢复提示"""

    reason: FailoverReason
    status_code: Optional[int] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    message: str = ""

    # 恢复操作提示 - 重试循环检查这些而不是重新分类错误
    retryable: bool = True  # 是否可重试
    should_compress: bool = False  # 是否应该压缩
    should_rotate_credential: bool = False  # 是否应该轮换凭证
    should_fallback: bool = False  # 是否应该回退

    # 额外上下文信息
    error_context: dict[str, Any] = field(default_factory=dict)

    @property
    def is_auth(self) -> bool:
        """是否是认证错误"""
        return self.reason in {FailoverReason.auth, FailoverReason.auth_permanent}

    @property
    def is_rate_limit(self) -> bool:
        """是否是限流错误"""
        return self.reason == FailoverReason.rate_limit

    @property
    def is_context_overflow(self) -> bool:
        """是否是上下文溢出"""
        return self.reason == FailoverReason.context_overflow

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "reason": self.reason.value,
            "status_code": self.status_code,
            "provider": self.provider,
            "model": self.model,
            "message": self.message,
            "retryable": self.retryable,
            "should_compress": self.should_compress,
            "should_rotate_credential": self.should_rotate_credential,
            "should_fallback": self.should_fallback,
            "error_context": self.error_context,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# 错误模式定义
# ═══════════════════════════════════════════════════════════════════════════════

# 计费耗尽模式（不是临时限流）
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
    "余额不足",
    "额度已用完",
    "请充值",
]

# 限流模式（临时的，会解决）
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
    "限流",
    "请求过于频繁",
    "超出速率限制",
]

# 上下文溢出模式
_CONTEXT_OVERFLOW_PATTERNS = [
    "context length",
    "context size",
    "maximum context",
    "token limit",
    "too many tokens",
    "context window",
    "maximum tokens",
    "context too long",
    "maximum context length",
    "上下文过长",
    "token 超出限制",
]

# 负载过大模式
_PAYLOAD_TOO_LARGE_PATTERNS = [
    "request entity too large",
    "payload too large",
    "error code: 413",
    "too large",
    "文件过大",
]

# 超时模式
_TIMEOUT_PATTERNS = [
    "timeout",
    "timed out",
    "connection timeout",
    "read timeout",
    "deadline exceeded",
    "请求超时",
    "连接超时",
]

# 服务不可用模式
_OVERLOADED_PATTERNS = [
    "service unavailable",
    "503",
    "529",
    "overloaded",
    "internal server error",
    "服务器内部错误",
]

# 认证失败模式
_AUTH_PATTERNS = [
    "401",
    "403",
    "unauthorized",
    "invalid api key",
    "authentication failed",
    "permission denied",
    "认证失败",
    "权限不足",
    "无效的 API 密钥",
]

# 模型未找到模式
_MODEL_NOT_FOUND_PATTERNS = [
    "model not found",
    "404",
    "model not available",
    "invalid model",
    "模型未找到",
    "模型不可用",
]

# ═══════════════════════════════════════════════════════════════════════════════
# 错误分类器
# ═══════════════════════════════════════════════════════════════════════════════

class ErrorClassifier:
    """API 错误分类器"""

    def __init__(self):
        self.logger = get_decision_logger(self.__class__.__name__)

    def classify(
        self,
        error: Exception | str | dict,
        status_code: int | None = None,
        provider: str | None = None,
        model: str | None = None,
    ) -> ClassifiedError:
        """
        分类 API 错误

        Args:
            error: 错误对象（Exception、字符串或字典）
            status_code: HTTP 状态码
            provider: 提供商名称
            model: 模型名称

        Returns:
            ClassifiedError: 分类结果
        """
        # 提取错误消息
        message = self._extract_message(error)

        # 如果有状态码，先按状态码分类
        if status_code is not None:
            result = self._classify_by_status_code(status_code, message, provider, model)
            result.message = message
            self.logger.debug(f"Error classified: {result.reason.value} (status={status_code})")
            return result

        # 按错误消息模式分类
        result = self._classify_by_message(message, provider, model)
        result.message = message
        self.logger.debug(f"Error classified: {result.reason.value}")
        return result

    def _extract_message(self, error: Exception | str | dict) -> str:
        """从错误对象中提取消息"""
        if isinstance(error, Exception):
            return str(error)
        if isinstance(error, dict):
            # 尝试从字典中提取错误消息
            if "error" in error:
                inner = error["error"]
                if isinstance(inner, dict):
                    return inner.get("message", str(error))
                return str(inner)
            if "message" in error:
                return error["message"]
            return str(error)
        return str(error) if error else ""

    def _classify_by_status_code(
        self,
        status_code: int,
        message: str,
        provider: str | None,
        model: str | None,
    ) -> ClassifiedError:
        """根据 HTTP 状态码分类"""
        # 401/403 - 认证错误
        if status_code in {401, 403}:
            # 检查是否是永久性认证失败
            if "invalid" in message.lower() or "expired" in message.lower():
                return ClassifiedError(
                    reason=FailoverReason.auth_permanent,
                    status_code=status_code,
                    provider=provider,
                    model=model,
                    retryable=False,
                    should_rotate_credential=True,
                    message=message,
                )
            return ClassifiedError(
                reason=FailoverReason.auth,
                status_code=status_code,
                provider=provider,
                model=model,
                retryable=True,
                should_rotate_credential=True,
                message=message,
            )

        # 402 - 计费错误
        if status_code == 402:
            return ClassifiedError(
                reason=FailoverReason.billing,
                status_code=status_code,
                provider=provider,
                model=model,
                retryable=False,
                should_rotate_credential=True,
                message=message,
            )

        # 404 - 模型未找到
        if status_code == 404:
            return ClassifiedError(
                reason=FailoverReason.model_not_found,
                status_code=status_code,
                provider=provider,
                model=model,
                retryable=False,
                should_fallback=True,
                message=message,
            )

        # 413 - 负载过大
        if status_code == 413:
            return ClassifiedError(
                reason=FailoverReason.payload_too_large,
                status_code=status_code,
                provider=provider,
                model=model,
                retryable=True,
                should_compress=True,
                message=message,
            )

        # 429 - 限流
        if status_code == 429:
            return ClassifiedError(
                reason=FailoverReason.rate_limit,
                status_code=status_code,
                provider=provider,
                model=model,
                retryable=True,
                should_rotate_credential=True,
                message=message,
            )

        # 500/502 - 服务端错误
        if status_code in {500, 502, 504}:
            return ClassifiedError(
                reason=FailoverReason.server_error,
                status_code=status_code,
                provider=provider,
                model=model,
                retryable=True,
                message=message,
            )

        # 503/529 - 服务过载
        if status_code in {503, 529}:
            return ClassifiedError(
                reason=FailoverReason.overloaded,
                status_code=status_code,
                provider=provider,
                model=model,
                retryable=True,
                message=message,
            )

        # 400 - 格式错误
        if status_code == 400:
            return ClassifiedError(
                reason=FailoverReason.format_error,
                status_code=status_code,
                provider=provider,
                model=model,
                retryable=False,
                message=message,
            )

        return ClassifiedError(
            reason=FailoverReason.unknown,
            status_code=status_code,
            provider=provider,
            model=model,
            retryable=True,
            message=message,
        )

    def _classify_by_message(
        self,
        message: str,
        provider: str | None,
        model: str | None,
    ) -> ClassifiedError:
        """根据错误消息内容分类"""
        message_lower = message.lower()

        # 检查计费模式
        for pattern in _BILLING_PATTERNS:
            if pattern.lower() in message_lower:
                return ClassifiedError(
                    reason=FailoverReason.billing,
                    provider=provider,
                    model=model,
                    retryable=False,
                    should_rotate_credential=True,
                    message=message,
                )

        # 检查限流模式
        for pattern in _RATE_LIMIT_PATTERNS:
            if pattern.lower() in message_lower:
                return ClassifiedError(
                    reason=FailoverReason.rate_limit,
                    provider=provider,
                    model=model,
                    retryable=True,
                    should_rotate_credential=True,
                    message=message,
                )

        # 检查上下文溢出模式
        for pattern in _CONTEXT_OVERFLOW_PATTERNS:
            if pattern.lower() in message_lower:
                return ClassifiedError(
                    reason=FailoverReason.context_overflow,
                    provider=provider,
                    model=model,
                    retryable=True,
                    should_compress=True,
                    message=message,
                )

        # 检查负载过大模式
        for pattern in _PAYLOAD_TOO_LARGE_PATTERNS:
            if pattern.lower() in message_lower:
                return ClassifiedError(
                    reason=FailoverReason.payload_too_large,
                    provider=provider,
                    model=model,
                    retryable=True,
                    should_compress=True,
                    message=message,
                )

        # 检查超时模式
        for pattern in _TIMEOUT_PATTERNS:
            if pattern.lower() in message_lower:
                return ClassifiedError(
                    reason=FailoverReason.timeout,
                    provider=provider,
                    model=model,
                    retryable=True,
                    message=message,
                )

        # 检查服务不可用模式
        for pattern in _OVERLOADED_PATTERNS:
            if pattern.lower() in message_lower:
                return ClassifiedError(
                    reason=FailoverReason.overloaded,
                    provider=provider,
                    model=model,
                    retryable=True,
                    message=message,
                )

        # 检查认证失败模式
        for pattern in _AUTH_PATTERNS:
            if pattern.lower() in message_lower:
                return ClassifiedError(
                    reason=FailoverReason.auth,
                    provider=provider,
                    model=model,
                    retryable=True,
                    should_rotate_credential=True,
                    message=message,
                )

        # 检查模型未找到模式
        for pattern in _MODEL_NOT_FOUND_PATTERNS:
            if pattern.lower() in message_lower:
                return ClassifiedError(
                    reason=FailoverReason.model_not_found,
                    provider=provider,
                    model=model,
                    retryable=False,
                    should_fallback=True,
                    message=message,
                )

        # 无法分类
        return ClassifiedError(
            reason=FailoverReason.unknown,
            provider=provider,
            model=model,
            retryable=True,
            message=message,
        )

    def get_retry_delay(self, classified_error: ClassifiedError, attempt: int) -> float:
        """
        根据错误类型和重试次数计算退避延迟

        Args:
            classified_error: 分类后的错误
            attempt: 当前重试次数（从 1 开始）

        Returns:
            float: 延迟秒数
        """
        base_delay = 1.0
        max_delay = 60.0

        if classified_error.is_rate_limit:
            # 限流错误使用更长延迟
            base_delay = 5.0
            max_delay = 120.0
        elif classified_error.is_auth:
            # 认证错误使用中等延迟
            base_delay = 2.0
            max_delay = 30.0
        elif classified_error.reason == FailoverReason.timeout:
            # 超时错误使用较短延迟
            base_delay = 1.0
            max_delay = 30.0
        elif classified_error.is_context_overflow:
            # 上下文溢出使用较短延迟（需要压缩）
            base_delay = 1.0
            max_delay = 10.0

        # 计算带抖动的指数退避
        import random
        delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
        jitter = random.uniform(0, 0.5 * delay)  # 最多 50% 抖动

        return delay + jitter


# ═══════════════════════════════════════════════════════════════════════════════
# 全局单例
# ═══════════════════════════════════════════════════════════════════════════════

_default_classifier: Optional[ErrorClassifier] = None


def get_error_classifier() -> ErrorClassifier:
    """获取全局错误分类器（单例模式）"""
    global _default_classifier
    if _default_classifier is None:
        _default_classifier = ErrorClassifier()
    return _default_classifier


__all__ = [
    "FailoverReason",
    "ClassifiedError",
    "ErrorClassifier",
    "get_error_classifier",
]