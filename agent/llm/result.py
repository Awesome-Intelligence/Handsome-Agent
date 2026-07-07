"""LLM 调用结果包装器

🧠 Decision - 🤖 LLM - 结构化响应包装
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from agent.error import ClassifiedError


@dataclass
class LLMResult:
    """Provider generate() 的结构化返回结果

    替代原来的 ProviderResponse + 异常上抛模式，
    让调用方可以根据错误分类结果做决策（重试、fallback、压缩）。

    Attributes:
        content: 成功时的响应内容
        error: 失败时的 ClassifiedError，非 None 表示失败
        retryable: 是否可重试
        should_fallback: 是否应触发 fallback chain
        should_compress: 是否应先压缩上下文再重试
        should_rotate_credential: 是否应轮换凭证（第二阶段）
    """

    content: str = ""
    error: Optional["ClassifiedError"] = None
    retryable: bool = False
    should_fallback: bool = False
    should_compress: bool = False
    should_rotate_credential: bool = False

    @property
    def ok(self) -> bool:
        """是否有内容且无错误"""
        return self.error is None and bool(self.content)
