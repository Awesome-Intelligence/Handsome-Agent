#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""关键词重要性分级压缩策略"""

import re
from typing import List, Dict, Any

from . import CompressionStrategy, CompressionStrategyType
from .config import KeywordPriorityConfig


class KeywordPriorityStrategy(CompressionStrategy):
    """基于关键词优先级的内容保护策略"""

    def __init__(self, config: KeywordPriorityConfig = None):
        """初始化关键词优先级策略.

        Args:
            config: 策略配置，默认为 None（使用默认配置）。
        """
        cfg = config or KeywordPriorityConfig()
        super().__init__(enabled=cfg.enabled, priority=cfg.priority)
        self.config = cfg
        self._compile_patterns()

    def _compile_patterns(self):
        """预编译关键词模式."""
        self._high_pattern = self._build_pattern(self.config.high_priority_keywords)
        self._medium_pattern = self._build_pattern(self.config.medium_priority_keywords)
        self._low_pattern = self._build_pattern(self.config.low_priority_keywords)

    def _build_pattern(self, keywords: List[str]) -> re.Pattern:
        """构建关键词正则模式.

        Args:
            keywords: 关键词列表。

        Returns:
            编译后的正则表达式模式。
        """
        escaped = [re.escape(k) for k in keywords]
        return re.compile("|".join(escaped), re.IGNORECASE)

    @property
    def name(self) -> str:
        """策略名称."""
        return "keyword_priority"

    @property
    def strategy_type(self) -> CompressionStrategyType:
        return CompressionStrategyType.KEYWORD_PRIORITY

    def should_apply(
        self, messages: List[Dict[str, Any]], context: "CompressionContext"
    ) -> bool:
        """判断是否应该应用此策略."""
        return self._enabled and context.needs_compression

    def score(self, message: Dict[str, Any]) -> float:
        """计算消息的重要性分数.

        基于关键词匹配情况计算重要性评分（0.0-1.0）。

        Args:
            message: 消息字典。

        Returns:
            重要性评分。
        """
        content = message.get("content", "") or ""
        content_lower = content.lower()

        # 高优先级关键词匹配
        high_matches = len(self._high_pattern.findall(content_lower))
        if high_matches > 0:
            return min(1.0, 0.8 + high_matches * 0.05)

        # 中优先级关键词匹配
        medium_matches = len(self._medium_pattern.findall(content_lower))
        if medium_matches > 0:
            return min(0.7, 0.4 + medium_matches * 0.05)

        # 低优先级关键词匹配
        low_matches = len(self._low_pattern.findall(content_lower))
        if low_matches > 0:
            return max(0.1, 0.5 - low_matches * 0.1)

        return 0.5  # 默认分数

    def apply(
        self, messages: List[Dict[str, Any]], context: "CompressionContext"
    ) -> List[Dict[str, Any]]:
        """基于关键词优先级标记消息.

        为每条消息添加关键词优先级相关的元数据标记。

        Args:
            messages: 消息列表。
            context: 压缩上下文。

        Returns:
            处理后的消息列表。
        """
        if not messages:
            return messages

        result = []
        for msg in messages:
            msg_copy = msg.copy()
            score = self.score(msg)
            msg_copy["_keyword_priority_score"] = score
            msg_copy["_keyword_priority_level"] = self._get_level(score)
            result.append(msg_copy)

        return result

    def _get_level(self, score: float) -> str:
        """根据分数确定优先级级别.

        Args:
            score: 重要性评分。

        Returns:
            优先级级别：high、medium 或 low。
        """
        if score >= 0.8:
            return "high"
        elif score >= 0.4:
            return "medium"
        else:
            return "low"
