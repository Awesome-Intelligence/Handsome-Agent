#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Skill History module.

Tests cover:
- HistoryEntry dataclass
- SkillSnapshot dataclass
- SkillHistory class
- History management functions
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from agent.skill_history import (
    HistoryEntry,
    SkillSnapshot,
    SkillHistory,
    get_history,
    get_skill_history,
)


class TestHistoryEntry:
    """Tests for HistoryEntry dataclass."""

    def test_history_entry_required_fields(self):
        """HistoryEntry creates with required fields."""
        entry = HistoryEntry(
            version="v1",
            timestamp="2024-01-01T00:00:00Z",
            action="create",
            content_hash="abc123",
            diff_summary="Initial version",
        )

        assert entry.version == "v1"
        assert entry.timestamp == "2024-01-01T00:00:00Z"
        assert entry.action == "create"
        assert entry.content_hash == "abc123"
        assert entry.diff_summary == "Initial version"

    def test_history_entry_action_types(self):
        """HistoryEntry accepts all action types."""
        for action in ["create", "edit", "patch", "delete"]:
            entry = HistoryEntry(
                version="v1",
                timestamp="2024-01-01T00:00:00Z",
                action=action,
                content_hash="abc123",
                diff_summary="",
            )
            assert entry.action == action


class TestSkillSnapshot:
    """Tests for SkillSnapshot dataclass."""

    def test_skill_snapshot_creation(self):
        """SkillSnapshot creates with required fields."""
        snapshot = SkillSnapshot(
            version="v1",
            timestamp="2024-01-01T00:00:00Z",
            content="skill content",
        )

        assert snapshot.version == "v1"
        assert snapshot.content == "skill content"
        assert snapshot.timestamp == "2024-01-01T00:00:00Z"


class TestGetHistory:
    """Tests for get_history() function."""

    def test_get_history_returns_skill_history(self):
        """get_history() returns a SkillHistory instance."""
        result = get_history()
        assert isinstance(result, SkillHistory)


class TestGetSkillHistory:
    """Tests for get_skill_history() function."""

    def test_get_skill_history_returns_list(self):
        """get_skill_history() returns a list of HistoryEntry."""
        result = get_skill_history("nonexistent_skill_12345")
        assert isinstance(result, list)


class TestSkillHistory:
    """Tests for SkillHistory class."""

    def test_skill_history_has_history_dir(self):
        """SkillHistory has _history_dir attribute."""
        history = SkillHistory()
        assert hasattr(history, '_history_dir')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
