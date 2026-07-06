#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Skill Share module.

Tests cover:
- ShareMetadata dataclass
- ShareResult dataclass
- SkillShare class
- get_share function
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from agent.skill_share import (
    ShareMetadata,
    ShareResult,
    SkillShare,
    get_share,
    PLATFORMS,
    GIST_API_URL,
)


class TestConstants:
    """Tests for module constants."""

    def test_gist_api_url(self):
        """GIST_API_URL is the GitHub Gists API endpoint."""
        assert GIST_API_URL == "https://api.github.com/gists"

    def test_platforms_list(self):
        """PLATFORMS contains expected sharing platforms."""
        assert "github" in PLATFORMS
        assert "gist" in PLATFORMS
        assert "npm" in PLATFORMS
        assert "local" in PLATFORMS


class TestShareMetadata:
    """Tests for ShareMetadata dataclass."""

    def test_share_metadata_creation(self):
        """ShareMetadata creates with required fields."""
        meta = ShareMetadata(
            skill_name="test_skill",
            version="1.0.0",
            description="Test skill",
            author="test",
        )
        assert meta.skill_name == "test_skill"
        assert meta.version == "1.0.0"


class TestShareResult:
    """Tests for ShareResult dataclass."""

    def test_share_result_success(self):
        """ShareResult with success=True."""
        result = ShareResult(
            success=True,
            url="https://example.com/share",
            platform="gist",
        )

        assert result.success is True
        assert result.url == "https://example.com/share"
        assert result.platform == "gist"

    def test_share_result_failure(self):
        """ShareResult with success=False."""
        result = ShareResult(
            success=False,
            message="Failed to share",
            platform="gist",
        )

        assert result.success is False
        assert result.message == "Failed to share"


class TestGetShare:
    """Tests for get_share() function."""

    def test_get_share_returns_skill_share(self):
        """get_share() returns a SkillShare instance."""
        result = get_share()
        assert isinstance(result, SkillShare)


class TestSkillShare:
    """Tests for SkillShare class."""

    def test_skill_share_init(self):
        """SkillShare initializes correctly."""
        share = SkillShare()
        assert share is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
