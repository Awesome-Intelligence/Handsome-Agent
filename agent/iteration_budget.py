#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IterationBudget - 迭代预算管理

参考 Hermes Agent 的 iteration_budget.py 实现：
- 线程安全的 consume/refund 计数器
- 父代理默认 90 次，子代理默认 50 次
- execute_code 等纯计算操作不消耗预算（通过 refund）

子层标识：✅ Task
主层：🧠 Decision
"""

from __future__ import annotations

import threading
from typing import Optional


class IterationBudget:
    """
    线程安全的迭代预算计数器

    每个代理（父代理或子代理）都有独立的预算。
    父代理默认上限为 90 次，子代理默认上限为 50 次。

    使用 refund() 可以退还迭代（如 execute_code 操作），
    这样纯计算操作不会消耗预算。
    """

    def __init__(self, max_total: int):
        """
        初始化迭代预算

        Args:
            max_total: 最大迭代次数
        """
        self.max_total = max_total
        self._used = 0
        self._lock = threading.Lock()

    def consume(self) -> bool:
        """
        尝试消耗一次迭代

        Returns:
            True 如果允许消耗（还有剩余预算），False 如果已耗尽
        """
        with self._lock:
            if self._used >= self.max_total:
                return False
            self._used += 1
            return True

    def refund(self) -> None:
        """
        退还一次迭代（例如用于 execute_code 回合）
        """
        with self._lock:
            if self._used > 0:
                self._used -= 1

    @property
    def used(self) -> int:
        """已使用的迭代次数"""
        with self._lock:
            return self._used

    @property
    def remaining(self) -> int:
        """剩余迭代次数"""
        with self._lock:
            return max(0, self.max_total - self._used)

    @property
    def is_exhausted(self) -> bool:
        """预算是否已耗尽"""
        with self._lock:
            return self._used >= self.max_total

    def __repr__(self) -> str:
        return f"IterationBudget(used={self.used}, remaining={self.remaining}, max={self.max_total})"


class SubagentBudgetFactory:
    """
    子代理预算工厂

    参考 Hermes 的设计，子代理使用独立的预算上限。
    """

    # 子代理默认最大迭代次数（比父代理少）
    DEFAULT_SUBAGENT_MAX_ITERATIONS = 50

    @classmethod
    def create_subagent_budget(
        cls,
        max_turns: Optional[int] = None,
    ) -> IterationBudget:
        """
        创建子代理的迭代预算

        Args:
            max_turns: 最大迭代次数（可选，默认 50）

        Returns:
            新的 IterationBudget 实例
        """
        max_iterations = max_turns or cls.DEFAULT_SUBAGENT_MAX_ITERATIONS
        return IterationBudget(max_iterations)


__all__ = ["IterationBudget", "SubagentBudgetFactory"]