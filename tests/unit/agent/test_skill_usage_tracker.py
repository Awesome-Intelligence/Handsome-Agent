#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Skill Usage Tracker module.

Tests cover:
- Lifecycle state constants
- bump_use, bump_view, bump_patch operations
- Usage data loading and saving
- State transitions
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

from agent.skill_usage_tracker import (
    STATE_ACTIVE,
    STATE_STALE,
    STATE_ARCHIVED,
    VALID_STATES,
    load_usage,
    bump_use,
    bump_view,
    bump_patch,
    set_state,
    set_pinned,
    latest_activity_at,
    activity_count,
)


class TestStateConstants:
    """Tests for lifecycle state constants."""

    def test_state_values(self):
        """State constants have expected string values."""
        assert STATE_ACTIVE == "active"
        assert STATE_STALE == "stale"
        assert STATE_ARCHIVED == "archived"

    def test_valid_states_set(self):
        """VALID_STATES contains all state constants."""
        assert STATE_ACTIVE in VALID_STATES
        assert STATE_STALE in VALID_STATES
        assert STATE_ARCHIVED in VALID_STATES


class TestLoadUsage:
    """Tests for load_usage() function."""

    def test_load_usage_returns_dict(self):
        """load_usage() returns a dictionary."""
        result = load_usage()
        assert isinstance(result, dict)

    def test_load_usage_empty_when_no_file(self):
        """load_usage() returns empty dict when no usage file exists."""
        with patch("agent.skill_usage_tracker._usage_file", return_value=Path("/nonexistent/.usage.json")):
            result = load_usage()
            assert result == {}


class TestBumpUse:
    """Tests for bump_use() function."""

    def test_bump_use_accepts_skill_name(self):
        """bump_use() accepts a skill_name parameter."""
        # Should not raise
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("agent.skill_usage_tracker._skills_dir", return_value=Path(tmpdir)):
                bump_use("test_skill")

    def test_bump_use_updates_file(self):
        """bump_use() updates the usage file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir)
            with patch("agent.skill_usage_tracker._skills_dir", return_value=skills_dir):
                bump_use("test_skill")
                usage = load_usage()
                assert "test_skill" in usage


class TestBumpView:
    """Tests for bump_view() function."""

    def test_bump_view_accepts_skill_name(self):
        """bump_view() accepts a skill_name parameter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("agent.skill_usage_tracker._skills_dir", return_value=Path(tmpdir)):
                bump_view("test_skill")


class TestBumpPatch:
    """Tests for bump_patch() function."""

    def test_bump_patch_accepts_skill_name(self):
        """bump_patch() accepts a skill_name parameter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("agent.skill_usage_tracker._skills_dir", return_value=Path(tmpdir)):
                bump_patch("test_skill")


class TestSetState:
    """Tests for set_state() function."""

    def test_set_state_to_stale(self):
        """set_state() can set state to stale."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir)
            with patch("agent.skill_usage_tracker._skills_dir", return_value=skills_dir):
                bump_use("stale_skill")
                set_state("stale_skill", STATE_STALE)
                usage = load_usage()
                assert usage.get("stale_skill", {}).get("state") == STATE_STALE

    def test_set_state_to_active(self):
        """set_state() can set state back to active."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir)
            with patch("agent.skill_usage_tracker._skills_dir", return_value=skills_dir):
                bump_use("active_skill")
                set_state("active_skill", STATE_STALE)
                set_state("active_skill", STATE_ACTIVE)
                usage = load_usage()
                assert usage.get("active_skill", {}).get("state") == STATE_ACTIVE

    def test_set_state_invalid_state(self):
        """set_state() ignores invalid state values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir)
            with patch("agent.skill_usage_tracker._skills_dir", return_value=skills_dir):
                bump_use("test_skill")
                set_state("test_skill", "invalid_state")
                usage = load_usage()
                # Should not have changed from default
                assert usage.get("test_skill", {}).get("state", STATE_ACTIVE) in VALID_STATES


class TestSetPinned:
    """Tests for set_pinned() function."""

    def test_set_pinned_true(self):
        """set_pinned() can set pinned to True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir)
            with patch("agent.skill_usage_tracker._skills_dir", return_value=skills_dir):
                bump_use("pinned_skill")
                set_pinned("pinned_skill", True)
                usage = load_usage()
                assert usage.get("pinned_skill", {}).get("pinned") is True

    def test_set_pinned_false(self):
        """set_pinned() can set pinned to False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir)
            with patch("agent.skill_usage_tracker._skills_dir", return_value=skills_dir):
                bump_use("unpinned_skill")
                set_pinned("unpinned_skill", True)
                set_pinned("unpinned_skill", False)
                usage = load_usage()
                assert usage.get("unpinned_skill", {}).get("pinned") is False


class TestLatestActivityAt:
    """Tests for latest_activity_at() function."""

    def test_latest_activity_at_empty_record(self):
        """latest_activity_at() returns None for empty record."""
        record = {}
        result = latest_activity_at(record)
        assert result is None

    def test_latest_activity_at_with_data(self):
        """latest_activity_at() returns the most recent activity."""
        now = datetime.now(timezone.utc)
        record = {
            "last_used_at": (now - timedelta(days=2)).isoformat(),
            "last_viewed_at": now.isoformat(),
            "last_patched_at": (now - timedelta(days=1)).isoformat(),
        }
        result = latest_activity_at(record)
        # The function should return the most recent timestamp string
        assert result is not None
        assert isinstance(result, str)
        # The returned value should be the most recent (last_viewed_at)
        assert result == now.isoformat()


class TestActivityCount:
    """Tests for activity_count() function."""

    def test_activity_count_empty_record(self):
        """activity_count() returns 0 for empty record."""
        record = {}
        assert activity_count(record) == 0

    def test_activity_count_sums_all(self):
        """activity_count() returns sum of use + view + patch."""
        record = {
            "use_count": 3,
            "view_count": 7,
            "patch_count": 2,
        }
        assert activity_count(record) == 12


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
