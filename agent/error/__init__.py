"""Agent 错误处理模块

提供统一的错误分类、异常定义和辅助函数。
"""

from agent.error.exceptions import (
    AgentError,
    LLMError,
    LLMAuthError,
    LLMBillingError,
    LLMRateLimitError,
    LLMContextOverflowError,
    LLMServerError,
    ToolExecutionError,
    RailBlockedError,
)

from agent.error.error_classifier import (
    FailoverReason,
    ClassifiedError,
    classify_api_error,
)

from agent.error.helpers import (
    summarize_api_error,
    extract_api_error_context,
    mask_api_key_for_logs,
    classify_tool_error,
)

from agent.error.retry_utils import (
    jittered_backoff,
)

__all__ = [
    # 异常类
    "AgentError",
    "LLMError",
    "LLMAuthError",
    "LLMBillingError",
    "LLMRateLimitError",
    "LLMContextOverflowError",
    "LLMServerError",
    "ToolExecutionError",
    "RailBlockedError",
    # 分类器
    "FailoverReason",
    "ClassifiedError",
    "classify_api_error",
    # 辅助函数
    "summarize_api_error",
    "extract_api_error_context",
    "mask_api_key_for_logs",
    "classify_tool_error",
    # 重试工具
    "jittered_backoff",
]
