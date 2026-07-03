#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Skill Utils module.

Tests cover:
- NAMESPACE_PATTERN regex
- EXCLUDED_PATTERNS list
- skill_matches_platform function
- parse_frontmatter function
- iter_skill_index_files function
"""

import pytest
import re
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from agent.skill_utils import (
    NAMESPACE_PATTERN,
    EXCLUDED_PATTERNS,
    skill_matches_platform,
    parse_frontmatter,
    iter_skill_index_files,
)


class TestNamespacePattern:
    """Tests for NAMESPACE_PATTERN regex."""

    def test_valid_namespace_matches(self):
        """Valid namespace patterns match."""
        assert NAMESPACE_PATTERN.match("mynamespace") is not None
        assert NAMESPACE_PATTERN.match("my_namespace") is not None
        assert NAMESPACE_PATTERN.match("Namespace123") is not None

    def test_namespace_starting_with_number_fails(self):
        """Namespace starting with number does not match."""
        assert NAMESPACE_PATTERN.match("123namespace") is None

    def test_namespace_with_invalid_chars_fails(self):
        """Namespace with invalid characters does not match."""
        assert NAMESPACE_PATTERN.match("my-namespace") is None
        assert NAMESPACE_PATTERN.match("my namespace") is None


class TestExcludedPatterns:
    """Tests for EXCLUDED_PATTERNS list."""

    def test_excluded_patterns_is_list(self):
        """EXCLUDED_PATTERNS is a list."""
        assert isinstance(EXCLUDED_PATTERNS, list)

    def test_excluded_patterns_not_empty(self):
        """EXCLUDED_PATTERNS is not empty."""
        assert len(EXCLUDED_PATTERNS) > 0

    def test_contains_hidden_dir_pattern(self):
        """EXCLUDED_PATTERNS includes hidden directory pattern."""
        hidden_patterns = [p for p in EXCLUDED_PATTERNS if hasattr(p, 'pattern') and p.pattern.startswith('^\\.')]
        assert len(hidden_patterns) > 0

    def test_contains_git_pattern(self):
        """EXCLUDED_PATTERNS includes .git pattern."""
        git_patterns = [p for p in EXCLUDED_PATTERNS if hasattr(p, 'pattern') and '.git' in p.pattern]
        assert len(git_patterns) > 0


class TestParseFrontmatter:
    """Tests for parse_frontmatter() function."""

    def test_parse_empty_frontmatter(self):
        """parse_frontmatter handles empty content."""
        fm, body = parse_frontmatter("")
        assert fm == {}
        assert body == ""

    def test_parse_only_body_no_frontmatter(self):
        """parse_frontmatter returns empty dict when no frontmatter."""
        content = "This is just body text."
        fm, body = parse_frontmatter(content)
        assert fm == {}
        assert body == content

    def test_parse_yaml_frontmatter(self):
        """parse_frontmatter extracts YAML frontmatter."""
        content = """---
name: test-skill
description: A test skill
platforms: [linux, macos]
---
This is the body."""
        fm, body = parse_frontmatter(content)

        assert fm["name"] == "test-skill"
        assert fm["description"] == "A test skill"
        assert fm["platforms"] == ["linux", "macos"]
        assert "This is the body" in body

    def test_parse_frontmatter_with_no_body(self):
        """parse_frontmatter handles content with only frontmatter."""
        content = """---
name: frontmatter-only
---
"""
        fm, body = parse_frontmatter(content)
        assert fm["name"] == "frontmatter-only"

    def test_parse_invalid_yaml_in_frontmatter(self):
        """parse_frontmatter handles invalid YAML gracefully."""
        content = """---
name: test
invalid: [unclosed
---
Body text."""
        fm, body = parse_frontmatter(content)
        # Should return empty dict and full content as body on parse failure
        assert isinstance(fm, dict)


class TestIterSkillIndexFiles:
    """Tests for iter_skill_index_files() function."""

    def test_returns_iterator(self):
        """iter_skill_index_files returns an iterator."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = iter_skill_index_files(Path(tmpdir))
            assert hasattr(result, '__iter__')

    def test_returns_empty_for_empty_dir(self, tmp_path):
        """iter_skill_index_files returns empty for directory with no skills."""
        result = list(iter_skill_index_files(tmp_path))
        assert result == []


class TestSkillMatchesPlatform:
    """Tests for skill_matches_platform function from skill_utils."""

    def test_no_platforms_returns_true(self):
        """skill_matches_platform returns True when no platforms specified."""
        fm = {}
        result = skill_matches_platform(fm)
        assert result is True

    def test_empty_platforms_returns_true(self):
        """skill_matches_platform returns True for empty platforms list."""
        fm = {"platforms": []}
        result = skill_matches_platform(fm)
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
