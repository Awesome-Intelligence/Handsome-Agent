#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对话轮次重要性评分策略"""

import re
from typing import List, Dict, Any

from . import CompressionStrategy, CompressionStrategyType
from .config import TurnImportanceConfig


class TurnImportanceStrategy(CompressionStrategy):
    """基于多维度评估对话轮次重要性的策略"""

    def __init__(self, config: TurnImportanceConfig = None):
        """初始化轮次重要性策略.

        Args:
            config: 策略配置，默认为 None（使用默认配置）。
        """
        cfg = config or TurnImportanceConfig()
        super().__init__(enabled=cfg.enabled, priority=cfg.priority)
        self.config = cfg
        self._error_pattern = re.compile(
            r"(error|exception|failed|crash|traceback|warning|assert)",
            re.IGNORECASE,
        )
        self._code_block_pattern = re.compile(r"```[\s\S]*?```|`[^`]+`")
        self._function_pattern = re.compile(
            r"def\s+\w+|class\s+\w+|function\s+\w+", re.IGNORECASE
        )

    @property
    def name(self) -> str:
        """策略名称."""
        return "turn_importance"

    @property
    def strategy_type(self) -> CompressionStrategyType:
        return CompressionStrategyType.TURN_IMPORTANCE

    def should_apply(
        self, messages: List[Dict[str, Any]], context: "CompressionContext"
    ) -> bool:
        """判断是否应该应用此策略."""
        return self._enabled and context.needs_compression

    def score(self, message: Dict[str, Any]) -> float:
        """综合评分计算.

        基于多个维度评估消息的重要性：
        - 工具调用数量
        - 错误信息
        - 代码块数量
        - 用户请求
        - 内容长度
        - 函数/类定义

        Args:
            message: 消息字典。

        Returns:
            综合重要性评分（0.0-1.0）。
        """
        content = message.get("content", "") or ""
        role = message.get("role", "")

        score = 0.0

        # 1. 工具调用数量评分
        tool_calls = message.get("tool_calls", [])
        score += len(tool_calls) * self.config.tool_call_weight

        # 2. 错误信息评分
        error_matches = len(self._error_pattern.findall(content))
        score += error_matches * self.config.error_weight

        # 3. 代码块评分
        code_blocks = len(self._code_block_pattern.findall(content))
        score += code_blocks * self.config.code_block_weight

        # 4. 用户请求评分
        if role == "user":
            score += self.config.user_request_weight

        # 5. 内容长度惩罚（太长反而减分）
        if len(content) > self.config.length_penalty_threshold:
            score -= self.config.length_penalty

        # 6. 函数/类定义加分
        func_matches = len(self._function_pattern.findall(content))
        score += func_matches * self.config.function_def_weight

        return max(0.0, min(1.0, score))

    def apply(
        self, messages: List[Dict[str, Any]], context: "CompressionContext"
    ) -> List[Dict[str, Any]]:
        """计算所有消息的重要性分数并排序.

        为每条消息添加轮次重要性评分。

        Args:
            messages: 消息列表。
            context: 压缩上下文。

        Returns:
            处理后的消息列表。
        """
        if not messages:
            return messages

        scored_messages = []
        for msg in messages:
            msg_copy = msg.copy()
            msg_copy["_turn_importance_score"] = self.score(msg)
            scored_messages.append(msg_copy)

        return scored_messages

    def get_top_messages(
        self, messages: List[Dict[str, Any]], n: int
    ) -> List[Dict[str, Any]]:
        """获取最重要的 N 条消息.

        按重要性分数降序排列，返回前 N 条。

        Args:
            messages: 消息列表。
            n: 返回的消息数量。

        Returns:
            最重要的 N 条消息。
        """
        scored = [
            (i, m.get("_turn_importance_score", 0), m) for i, m in enumerate(messages)
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [m for _, _, m in scored[:n]]
