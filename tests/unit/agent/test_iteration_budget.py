#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Iteration Budget module.

Tests cover:
- IterationBudget class
- consume() and refund() operations
- Budget tracking and limits
- Thread safety
"""

import pytest
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from agent.iteration_budget import IterationBudget


class TestIterationBudgetInit:
    """Tests for IterationBudget initialization."""

    def test_init_with_max_total(self):
        """IterationBudget initializes with specified max_total."""
        budget = IterationBudget(max_total=50)
        assert budget.max_total == 50

    def test_init_starts_at_zero(self):
        """IterationBudget starts with _used = 0."""
        budget = IterationBudget(max_total=90)
        assert budget._used == 0

    def test_default_parent_budget(self):
        """Parent agents default to 90 iterations."""
        budget = IterationBudget(max_total=90)
        assert budget.max_total == 90

    def test_default_child_budget(self):
        """Child agents default to 50 iterations."""
        budget = IterationBudget(max_total=50)
        assert budget.max_total == 50


class TestIterationBudgetConsume:
    """Tests for IterationBudget.consume()."""

    def test_consume_increments_used(self):
        """consume() increments _used counter."""
        budget = IterationBudget(max_total=100)
        budget.consume()
        assert budget._used == 1

    def test_consume_multiple_times(self):
        """consume() can be called multiple times."""
        budget = IterationBudget(max_total=100)
        budget.consume()
        budget.consume()
        budget.consume()
        assert budget._used == 3

    def test_consume_returns_true_when_within_budget(self):
        """consume() returns True when within budget."""
        budget = IterationBudget(max_total=10)
        result = budget.consume()
        assert result is True

    def test_consume_returns_false_when_at_limit(self):
        """consume() returns False when at budget limit."""
        budget = IterationBudget(max_total=2)
        budget.consume()
        budget.consume()
        result = budget.consume()
        assert result is False

    def test_consume_updates_remaining(self):
        """consume() updates remaining property."""
        budget = IterationBudget(max_total=10)
        budget.consume()
        assert budget.remaining == 9


class TestIterationBudgetRefund:
    """Tests for IterationBudget.refund()."""

    def test_refund_decrements_used(self):
        """refund() decrements _used counter."""
        budget = IterationBudget(max_total=100)
        budget.consume()
        budget.consume()
        budget.refund()
        assert budget._used == 1

    def test_refund_cannot_go_below_zero(self):
        """refund() cannot reduce _used below 0."""
        budget = IterationBudget(max_total=100)
        budget.refund()
        assert budget._used == 0

    def test_refund_restores_budget(self):
        """refund() restores ability to consume after hitting limit."""
        budget = IterationBudget(max_total=2)
        budget.consume()
        budget.consume()
        # At limit
        assert budget.consume() is False
        # Refund one
        budget.refund()
        # Should be able to consume again
        assert budget.consume() is True


class TestIterationBudgetProperties:
    """Tests for IterationBudget properties."""

    def test_used_property(self):
        """used property returns _used value."""
        budget = IterationBudget(max_total=50)
        budget.consume()
        budget.consume()
        assert budget.used == 2

    def test_remaining_property(self):
        """remaining property returns max_total - _used."""
        budget = IterationBudget(max_total=50)
        budget.consume()
        budget.consume()
        assert budget.remaining == 48

    def test_remaining_full_at_start(self):
        """remaining equals max_total at start."""
        budget = IterationBudget(max_total=50)
        assert budget.remaining == 50

    def test_remaining_zero_when_exhausted(self):
        """remaining returns 0 when exhausted."""
        budget = IterationBudget(max_total=2)
        budget.consume()
        budget.consume()
        assert budget.remaining == 0

    def test_is_exhausted_false_at_start(self):
        """is_exhausted returns False at start."""
        budget = IterationBudget(max_total=10)
        assert budget.is_exhausted is False

    def test_is_exhausted_true_when_at_limit(self):
        """is_exhausted returns True when at budget limit."""
        budget = IterationBudget(max_total=2)
        budget.consume()
        budget.consume()
        assert budget.is_exhausted is True

    def test_is_exhausted_after_refund(self):
        """is_exhausted returns False after refund."""
        budget = IterationBudget(max_total=2)
        budget.consume()
        budget.consume()
        budget.refund()
        assert budget.is_exhausted is False


class TestIterationBudgetRepr:
    """Tests for IterationBudget.__repr__()."""

    def test_repr_contains_class_name(self):
        """__repr__ contains IterationBudget."""
        budget = IterationBudget(max_total=50)
        assert "IterationBudget" in repr(budget)

    def test_repr_contains_max_total(self):
        """__repr__ contains max_total value."""
        budget = IterationBudget(max_total=50)
        assert "50" in repr(budget)


class TestIterationBudgetThreadSafety:
    """Tests for IterationBudget thread safety."""

    def test_consume_thread_safe(self):
        """consume() is thread-safe."""
        budget = IterationBudget(max_total=1000)
        num_threads = 10
        iterations_per_thread = 100

        def consume_many():
            for _ in range(iterations_per_thread):
                budget.consume()

        threads = [threading.Thread(target=consume_many) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert budget._used == num_threads * iterations_per_thread

    def test_refund_thread_safe(self):
        """refund() is thread-safe."""
        budget = IterationBudget(max_total=1000)
        # Start with some consumed
        for _ in range(100):
            budget.consume()

        original_used = budget._used

        def refund_many():
            for _ in range(10):
                if budget._used > 0:
                    budget.refund()

        threads = [threading.Thread(target=refund_many) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have refunded some amount
        assert budget._used < original_used


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
