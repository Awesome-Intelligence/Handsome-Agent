#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Skill Curator module.

Tests cover:
- CuratorConfig dataclass
- CuratorAction dataclass
- CuratorReport dataclass
- Curator functions
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

from agent.skill_curator import (
    CuratorConfig,
    CuratorAction,
    CuratorReport,
    get_curator_config,
    check_skill_staleness,
    check_skill_archive,
    run_curator,
    list_archived_skills,
    curator_stats,
    pin_skill,
    unpin_skill,
)


class TestCuratorConfig:
    """Tests for CuratorConfig dataclass."""

    def test_curator_config_has_stale_after_days(self):
        """CuratorConfig has stale_after_days attribute."""
        config = CuratorConfig()
        assert hasattr(config, 'stale_after_days')

    def test_curator_config_has_archive_after_days(self):
        """CuratorConfig has archive_after_days attribute."""
        config = CuratorConfig()
        assert hasattr(config, 'archive_after_days')

    def test_curator_config_defaults(self):
        """CuratorConfig initializes with defaults."""
        config = CuratorConfig()
        assert config.stale_after_days > 0
        assert config.archive_after_days > 0


class TestCuratorAction:
    """Tests for CuratorAction dataclass."""

    def test_curator_action_creation(self):
        """CuratorAction creates with required fields."""
        action = CuratorAction(
            skill_name="test_skill",
            action="mark_stale",
            reason="No usage for 30 days",
            before_state="active",
            after_state="stale",
        )
        assert action.skill_name == "test_skill"
        assert action.action == "mark_stale"
        assert action.before_state == "active"
        assert action.after_state == "stale"


class TestCuratorReport:
    """Tests for CuratorReport dataclass."""

    def test_curator_report_requires_fields(self):
        """CuratorReport creates with timestamp and config."""
        config = CuratorConfig()
        report = CuratorReport(
            timestamp="2024-01-01T00:00:00Z",
            config=config,
        )
        assert report.timestamp == "2024-01-01T00:00:00Z"
        assert report.config == config

    def test_curator_report_defaults(self):
        """CuratorReport has correct defaults."""
        config = CuratorConfig()
        report = CuratorReport(
            timestamp="2024-01-01T00:00:00Z",
            config=config,
        )
        assert report.actions == []
        assert report.errors == []


class TestGetCuratorConfig:
    """Tests for get_curator_config() function."""

    def test_get_curator_config_returns_config(self):
        """get_curator_config() returns a CuratorConfig."""
        config = get_curator_config()
        assert isinstance(config, CuratorConfig)


class TestCheckSkillStaleness:
    """Tests for check_skill_staleness() function."""

    def test_check_skill_staleness_signature(self):
        """check_skill_staleness() takes record and config."""
        import inspect
        sig = inspect.signature(check_skill_staleness)
        params = list(sig.parameters.keys())
        assert "record" in params
        assert "config" in params


class TestCheckSkillArchive:
    """Tests for check_skill_archive() function."""

    def test_check_skill_archive_signature(self):
        """check_skill_archive() takes record and config."""
        import inspect
        sig = inspect.signature(check_skill_archive)
        params = list(sig.parameters.keys())
        assert "record" in params
        assert "config" in params


class TestRunCurator:
    """Tests for run_curator() function."""

    def test_run_curator_returns_report(self):
        """run_curator() returns a CuratorReport."""
        result = run_curator()
        assert isinstance(result, CuratorReport)


class TestListArchivedSkills:
    """Tests for list_archived_skills() function."""

    def test_list_archived_skills_returns_list(self):
        """list_archived_skills() returns a list."""
        result = list_archived_skills()
        assert isinstance(result, list)


class TestCuratorStats:
    """Tests for curator_stats() function."""

    def test_curator_stats_returns_dict(self):
        """curator_stats() returns a dictionary."""
        result = curator_stats()
        assert isinstance(result, dict)


class TestPinSkill:
    """Tests for pin_skill() function."""

    def test_pin_skill_returns_bool(self):
        """pin_skill() returns a boolean."""
        result = pin_skill("nonexistent_skill_12345")
        assert isinstance(result, bool)


class TestUnpinSkill:
    """Tests for unpin_skill() function."""

    def test_unpin_skill_returns_bool(self):
        """unpin_skill() returns a boolean."""
        result = unpin_skill("nonexistent_skill_12345")
        assert isinstance(result, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
