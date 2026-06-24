#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Context Compression Strategies - 上下文压缩策略模块

提供可扩展的压缩策略基础设施，用于支持多种压缩策略的注册和执行。

Features:
- CompressionStrategy 基类：定义策略接口
- CompressionStrategyType：策略类型枚举
- CompressionContext：传递给策略的上下文数据
- 策略配置类：各策略的默认配置

Usage:
    from agent.context.strategies import (
        CompressionStrategy,
        CompressionStrategyType,
        CompressionContext,
        KeywordPriorityConfig,
    )

    # 使用策略
    context = CompressionContext(messages=[...], current_tokens=25000)
    for strategy in strategies:
        if strategy.should_apply(messages, context):
            messages = strategy.apply(messages, context)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional


# ============================================================================
# CompressionStrategyType - 策略类型枚举
# ============================================================================


class CompressionStrategyType(Enum):
    """压缩策略类型枚举"""

    KEYWORD_PRIORITY = auto()
    TURN_IMPORTANCE = auto()
    TOKEN_LIMIT = auto()
    SEMANTIC_SIMILARITY = auto()
    TIME_DECAY = auto()
    LLM_SUMMARY = auto()
    CODE_BLOCK = auto()
    PATH_PRESERVATION = auto()
    ERROR_PRESERVATION = auto()
    ADAPTIVE_COMPRESSION = auto()
    INSTRUCTION_RESULT = auto()


# ============================================================================
# CompressionContext - 压缩上下文数据类
# ============================================================================


@dataclass
class CompressionContext:
    """压缩上下文数据类.

    包含压缩操作所需的所有上下文信息，供策略决策使用。

    Attributes:
        messages: 消息列表
        current_tokens: 当前 token 数
        max_tokens: 最大 token 限制
        protect_head_size: 保护头部消息数量
        protect_tail_count: 保护尾部消息数量
        summary: 已有摘要（用于迭代压缩）
        config: 额外配置字典
    """

    messages: List[Dict[str, Any]] = field(default_factory=list)
    current_tokens: int = 0
    max_tokens: int = 32000
    protect_head_size: int = 3
    protect_tail_count: int = 5
    summary: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)

    @property
    def needs_compression(self) -> bool:
        """判断是否需要压缩.

        当当前 token 数超过最大值的 80% 时返回 True。
        """
        return self.current_tokens > self.max_tokens * 0.8

    @property
    def compression_ratio(self) -> float:
        """获取压缩比例.

        Returns:
            当前 token 数与最大值的比值。
        """
        return self.current_tokens / self.max_tokens if self.max_tokens > 0 else 0.0


# ============================================================================
# CompressionStrategy - 压缩策略基类
# ============================================================================


class CompressionStrategy(ABC):
    """压缩策略抽象基类.

    所有具体压缩策略必须继承此类并实现相应方法。

    Features:
    - enabled 属性：控制策略是否启用
    - priority 属性：控制策略执行顺序（数字越小越先执行）
    - strategy_type 属性：策略类型枚举

    Example:
        class KeywordPriorityStrategy(CompressionStrategy):
            def __init__(self, config: KeywordPriorityConfig = None):
                cfg = config or KeywordPriorityConfig()
                super().__init__(enabled=cfg.enabled, priority=cfg.priority)
                self.config = cfg

            @property
            def name(self) -> str:
                return "keyword_priority"

            @property
            def strategy_type(self) -> CompressionStrategyType:
                return CompressionStrategyType.KEYWORD_PRIORITY

            def should_apply(self, messages, context):
                return self._enabled and context.needs_compression

            def apply(self, messages, context):
                # 处理消息
                return processed_messages
    """

    def __init__(self, enabled: bool = True, priority: int = 100) -> None:
        """初始化压缩策略.

        Args:
            enabled: 是否启用此策略，默认为 True。
            priority: 策略优先级，数字越小越先执行，默认为 100。
        """
        self._enabled = enabled
        self._priority = priority

    @property
    def enabled(self) -> bool:
        """策略是否启用."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    @property
    def priority(self) -> int:
        """策略优先级，数字越小越先执行."""
        return self._priority

    @priority.setter
    def priority(self, value: int) -> None:
        self._priority = value

    @property
    @abstractmethod
    def name(self) -> str:
        """策略名称.

        Returns:
            策略的唯一标识名称。
        """
        pass

    @property
    def strategy_type(self) -> CompressionStrategyType:
        """策略类型."""
        return CompressionStrategyType.KEYWORD_PRIORITY

    @abstractmethod
    def should_apply(
        self, messages: List[Dict[str, Any]], context: CompressionContext
    ) -> bool:
        """判断是否应该应用此策略.

        Args:
            messages: 消息列表。
            context: 压缩上下文。

        Returns:
            如果应该应用此策略返回 True。
        """
        pass

    @abstractmethod
    def apply(
        self, messages: List[Dict[str, Any]], context: CompressionContext
    ) -> List[Dict[str, Any]]:
        """应用策略处理消息.

        Args:
            messages: 消息列表。
            context: 压缩上下文。

        Returns:
            处理后的消息列表。
        """
        pass

    def score(self, message: Dict[str, Any]) -> float:
        """对单条消息评分.

        用于重要性排序，评分范围 0.0-1.0。
        分数越高表示消息越重要。

        Args:
            message: 单条消息字典。

        Returns:
            重要性评分，默认为 0.5。
        """
        return 0.5

    def should_apply_default(
        self, messages: List[Dict[str, Any]], context: CompressionContext
    ) -> bool:
        """默认的应用判断逻辑.

        策略启用且需要压缩时返回 True。

        Args:
            messages: 消息列表。
            context: 压缩上下文。

        Returns:
            如果应该应用此策略返回 True。
        """
        return self._enabled and context.needs_compression


# ============================================================================
# 向后兼容别名
# ============================================================================

# ============================================================================
# 导入配置类
# ============================================================================

from .config import (
    StrategyConfig,
    KeywordPriorityConfig,
    TurnImportanceConfig,
    CodeBlockConfig,
    PathPreservationConfig,
    SemanticMergeConfig,
    ErrorPreservationConfig,
    InstructionResultConfig,
)


# ============================================================================
# 导入具体策略
# ============================================================================

from .keyword_priority import KeywordPriorityStrategy
from .turn_importance import TurnImportanceStrategy
from .code_block import CodeBlockStrategy
from .path_preservation import PathPreservationStrategy
from .semantic_merge import SemanticMergeStrategy
from .error_preservation import ErrorPreservationStrategy
from .instruction_result import InstructionResultSeparationStrategy


__all__ = [
    # 核心类型
    "CompressionContext",
    "CompressionStrategy",
    "CompressionStrategyType",
    # 配置类
    "StrategyConfig",
    "KeywordPriorityConfig",
    "TurnImportanceConfig",
    "CodeBlockConfig",
    "PathPreservationConfig",
    "SemanticMergeConfig",
    "ErrorPreservationConfig",
    "InstructionResultConfig",
    # 具体策略
    "KeywordPriorityStrategy",
    "TurnImportanceStrategy",
    "CodeBlockStrategy",
    "PathPreservationStrategy",
    "SemanticMergeStrategy",
    "ErrorPreservationStrategy",
    "InstructionResultSeparationStrategy",
]
