#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Skill Scheduler module.

Tests cover:
- ScheduledTask dataclass
- SkillScheduler class
- Task scheduling and execution
- Interval configuration
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from agent.skill_scheduler import (
    ScheduledTask,
    SkillScheduler,
    DEFAULT_CURATOR_INTERVAL_HOURS,
    DEFAULT_UPDATE_CHECK_INTERVAL_HOURS,
)


class TestConstants:
    """Tests for module constants."""

    def test_curator_interval_default(self):
        """DEFAULT_CURATOR_INTERVAL_HOURS is 24."""
        assert DEFAULT_CURATOR_INTERVAL_HOURS == 24

    def test_update_check_interval_default(self):
        """DEFAULT_UPDATE_CHECK_INTERVAL_HOURS is 6."""
        assert DEFAULT_UPDATE_CHECK_INTERVAL_HOURS == 6


class TestScheduledTask:
    """Tests for ScheduledTask dataclass."""

    def test_scheduled_task_creation(self):
        """ScheduledTask creates with required fields."""
        mock_func = MagicMock()
        task = ScheduledTask(name="test_task", func=mock_func, interval_hours=1.0)
        assert task.name == "test_task"
        assert task.func is mock_func
        assert task.interval_hours == 1.0


class TestSkillSchedulerInit:
    """Tests for SkillScheduler initialization."""

    def test_init_creates_scheduler(self):
        """SkillScheduler initializes."""
        scheduler = SkillScheduler()
        assert scheduler is not None

    def test_init_has_tasks_attribute(self):
        """SkillScheduler has _tasks attribute."""
        scheduler = SkillScheduler()
        assert hasattr(scheduler, '_tasks')


class TestSkillSchedulerRegister:
    """Tests for SkillScheduler.register_task()."""

    def test_register_task_adds_task(self):
        """register_task() adds a task to the scheduler."""
        scheduler = SkillScheduler()
        mock_func = MagicMock()

        result = scheduler.register_task(
            name="test_task",
            func=mock_func,
            interval_hours=1.0,
        )

        assert result is True


class TestSkillSchedulerUnregister:
    """Tests for SkillScheduler.unregister_task()."""

    def test_unregister_task_removes_task(self):
        """unregister_task() removes a task by name."""
        scheduler = SkillScheduler()
        mock_func = MagicMock()
        scheduler.register_task("test_task", mock_func, interval_hours=1.0)

        result = scheduler.unregister_task("test_task")

        assert result is True

    def test_unregister_nonexistent_returns_false(self):
        """unregister_task() returns False for unknown task."""
        scheduler = SkillScheduler()

        result = scheduler.unregister_task("nonexistent_task")

        assert result is False


class TestSkillSchedulerEnableDisable:
    """Tests for enable_task and disable_task methods."""

    def test_enable_task_returns_bool(self):
        """enable_task() returns a boolean."""
        scheduler = SkillScheduler()
        result = scheduler.enable_task("nonexistent")
        assert isinstance(result, bool)

    def test_disable_task_returns_bool(self):
        """disable_task() returns a boolean."""
        scheduler = SkillScheduler()
        result = scheduler.disable_task("nonexistent")
        assert isinstance(result, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
