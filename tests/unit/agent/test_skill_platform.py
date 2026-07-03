#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Skill Platform Filter module.

Tests cover:
- Platform identification (PLATFORM_MAP)
- Termux detection
- Platform matching logic
- Skill exclusion by path
- Disabled skill filtering
- Platform info collection
"""

import pytest
import sys
from unittest.mock import patch, MagicMock

from agent.skill_platform import (
    PLATFORM_MAP,
    is_termux,
    get_current_platform,
    skill_matches_platform,
    is_excluded_skill_path,
    get_disabled_skill_names,
    get_platform_info,
)


class TestPlatformMap:
    """Tests for PLATFORM_MAP constant."""

    def test_platform_map_contains_expected_keys(self):
        """PLATFORM_MAP has expected platform keys."""
        assert "macos" in PLATFORM_MAP
        assert "linux" in PLATFORM_MAP
        assert "windows" in PLATFORM_MAP
        assert "termux" in PLATFORM_MAP
        assert "android" in PLATFORM_MAP

    def test_platform_map_values(self):
        """PLATFORM_MAP maps to correct sys.platform values."""
        assert PLATFORM_MAP["macos"] == "darwin"
        assert PLATFORM_MAP["linux"] == "linux"
        assert PLATFORM_MAP["windows"] == "win32"
        assert PLATFORM_MAP["termux"] == "android"
        assert PLATFORM_MAP["android"] == "android"


class TestGetCurrentPlatform:
    """Tests for get_current_platform()."""

    def test_returns_sys_platform(self):
        """get_current_platform() returns sys.platform."""
        result = get_current_platform()
        assert result == sys.platform


class TestIsTermux:
    """Tests for is_termux()."""

    def test_is_termux_returns_bool(self):
        """is_termux() returns a boolean."""
        result = is_termux()
        assert isinstance(result, bool)


class TestSkillMatchesPlatform:
    """Tests for skill_matches_platform()."""

    def test_no_platforms_field_returns_true(self):
        """Skill with no platforms field matches all platforms."""
        assert skill_matches_platform({}) is True

    def test_empty_platforms_list_returns_true(self):
        """Skill with empty platforms list matches all platforms."""
        assert skill_matches_platform({"platforms": []}) is True

    def test_none_platforms_returns_true(self):
        """Skill with platforms: null matches all platforms."""
        assert skill_matches_platform({"platforms": None}) is True

    def test_single_matching_platform(self):
        """Skill with matching single platform returns True."""
        fm = {"platforms": ["linux"]}
        with patch("agent.skill_platform.get_current_platform", return_value="linux"):
            assert skill_matches_platform(fm) is True

    def test_single_non_matching_platform(self):
        """Skill with non-matching platform returns False."""
        fm = {"platforms": ["windows"]}
        with patch("agent.skill_platform.get_current_platform", return_value="linux"):
            assert skill_matches_platform(fm) is False

    def test_multiple_platforms_one_matches(self):
        """Skill with multiple platforms matches if any one matches."""
        fm = {"platforms": ["macos", "linux", "windows"]}
        with patch("agent.skill_platform.get_current_platform", return_value="darwin"):
            assert skill_matches_platform(fm) is True

    def test_platform_case_insensitive(self):
        """Platform matching is case-insensitive."""
        fm = {"platforms": ["LINUX"]}
        with patch("agent.skill_platform.get_current_platform", return_value="linux"):
            assert skill_matches_platform(fm) is True

    def test_platform_normalizes_whitespace(self):
        """Platform values with whitespace are normalized."""
        fm = {"platforms": [" linux "]}
        with patch("agent.skill_platform.get_current_platform", return_value="linux"):
            assert skill_matches_platform(fm) is True

    def test_platform_string_instead_of_list(self):
        """Platform as string instead of list is handled."""
        fm = {"platforms": "linux"}
        with patch("agent.skill_platform.get_current_platform", return_value="linux"):
            assert skill_matches_platform(fm) is True

    @patch("agent.skill_platform.is_termux", return_value=True)
    def test_termux_accepts_linux_skills(self, mock_termux):
        """Termux returns True for linux-tagged skills."""
        fm = {"platforms": ["linux"]}
        with patch("agent.skill_platform.get_current_platform", return_value="android"):
            assert skill_matches_platform(fm) is True

    @patch("agent.skill_platform.is_termux", return_value=True)
    def test_termux_accepts_termux_tagged_skills(self, mock_termux):
        """Termux returns True for termux-tagged skills."""
        fm = {"platforms": ["termux"]}
        with patch("agent.skill_platform.get_current_platform", return_value="android"):
            assert skill_matches_platform(fm) is True


class TestIsExcludedSkillPath:
    """Tests for is_excluded_skill_path()."""

    def test_excluded_node_modules(self):
        """node_modules directories are excluded."""
        assert is_excluded_skill_path("skill/node_modules/package/index.js") is True

    def test_not_excluded_normal_path(self):
        """Normal skill paths are not excluded."""
        assert is_excluded_skill_path("my_skill/SKILL.md") is False
        assert is_excluded_skill_path("category/skill_name/scripts/helper.sh") is False

    def test_handles_string_input(self):
        """Handles string input (not just Path)."""
        assert is_excluded_skill_path("node_modules/package") is True
        assert is_excluded_skill_path("valid_skill") is False


class TestGetDisabledSkillNames:
    """Tests for get_disabled_skill_names()."""

    def test_returns_set(self):
        """get_disabled_skill_names() returns a set."""
        result = get_disabled_skill_names()
        assert isinstance(result, set)


class TestGetPlatformInfo:
    """Tests for get_platform_info()."""

    def test_returns_dict(self):
        """get_platform_info() returns a dictionary."""
        result = get_platform_info()
        assert isinstance(result, dict)

    def test_contains_expected_keys(self):
        """get_platform_info() contains expected keys."""
        result = get_platform_info()
        assert "platform" in result
        assert "is_termux" in result
        assert "excluded_dirs" in result

    def test_platform_value_is_sys_platform(self):
        """platform field matches sys.platform."""
        result = get_platform_info()
        assert result["platform"] == sys.platform


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
