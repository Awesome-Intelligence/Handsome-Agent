#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Skill Commands module.

Tests cover:
- Skill name sanitization
- Command patterns
- Module constants
"""

import pytest
import re
from unittest.mock import patch, MagicMock

from agent.skill_commands import (
    _sanitize_skill_name,
    _SKILL_INVALID_CHARS,
    _SKILL_MULTI_HYPHEN,
)

# ─────────────────────────────────────────────────────────────────────────────
# Test Skill Name Sanitization
# ─────────────────────────────────────────────────────────────────────────────


class TestSanitizeSkillName:
    """Tests for _sanitize_skill_name() function."""

    def test_sanitize_lowercases(self):
        """_sanitize_skill_name() converts to lowercase."""
        assert _sanitize_skill_name("MY-SKILL") == "my-skill"
        assert _sanitize_skill_name("TestSkill") == "testskill"

    def test_sanitize_replaces_spaces(self):
        """_sanitize_skill_name() replaces spaces with hyphens."""
        assert _sanitize_skill_name("my skill") == "my-skill"
        assert _sanitize_skill_name("hello world test") == "hello-world-test"

    def test_sanitize_removes_special_chars(self):
        """_sanitize_skill_name() removes invalid characters."""
        assert _sanitize_skill_name("test@skill!") == "test-skill"
        assert _sanitize_skill_name("skill#123") == "skill-123"

    def test_sanitize_collapses_multiple_hyphens(self):
        """_sanitize_skill_name() collapses multiple hyphens."""
        assert _sanitize_skill_name("my---skill") == "my-skill"
        assert _sanitize_skill_name("a--b--c") == "a-b-c"

    def test_sanitize_trims_hyphens_from_ends(self):
        """_sanitize_skill_name() removes leading/trailing hyphens."""
        assert _sanitize_skill_name("-my-skill-") == "my-skill"
        assert _sanitize_skill_name("--skill--") == "skill"

    def test_sanitize_preserves_valid_names(self):
        """_sanitize_skill_name() keeps valid skill names unchanged."""
        assert _sanitize_skill_name("my-skill") == "my-skill"
        assert _sanitize_skill_name("test-123") == "test-123"

    def test_sanitize_handles_empty_string(self):
        """_sanitize_skill_name() handles empty string."""
        assert _sanitize_skill_name("") == ""

    def test_sanitize_handles_already_clean(self):
        """_sanitize_skill_name() handles already clean names."""
        assert _sanitize_skill_name("valid-skill-name") == "valid-skill-name"


# ─────────────────────────────────────────────────────────────────────────────
# Test Patterns
# ─────────────────────────────────────────────────────────────────────────────


class TestSkillPatterns:
    """Tests for skill command patterns."""

    def test_skill_invalid_chars_pattern(self):
        """_SKILL_INVALID_CHARS matches invalid characters."""
        pattern = _SKILL_INVALID_CHARS

        # Should match invalid characters
        assert pattern.search("@skill") is not None
        assert pattern.search("skill!") is not None
        assert pattern.search("#test") is not None

        # Should not match valid characters
        assert pattern.search("my-skill") is None
        assert pattern.search("test123") is None

    def test_skill_multi_hyphen_pattern(self):
        """_SKILL_MULTI_HYPHEN matches multiple hyphens."""
        pattern = _SKILL_MULTI_HYPHEN

        assert pattern.search("--") is not None
        assert pattern.search("---") is not None
        assert pattern.search("-") is None

    def test_pattern_types(self):
        """Patterns are compiled regular expressions."""
        assert isinstance(_SKILL_INVALID_CHARS, type(re.compile("")))
        assert isinstance(_SKILL_MULTI_HYPHEN, type(re.compile("")))
