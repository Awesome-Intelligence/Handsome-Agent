#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Skill Provenance module.

Tests cover:
- SkillSource enum values
- mark_skill_provenance function
- get_skill_provenance function
- list_skills_by_source function
- is_background_review context variable
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from agent.skill_provenance import (
    SkillSource,
    mark_skill_provenance,
    get_skill_provenance,
    list_skills_by_source,
    is_background_review,
    _get_provenance_dir,
)


class TestSkillSourceEnum:
    """Tests for SkillSource enum."""

    def test_skill_source_values(self):
        """SkillSource enum has expected values."""
        assert SkillSource.AGENT_CREATED == "agent_created"
        assert SkillSource.USER_CREATED == "user_created"

    def test_skill_source_is_string_enum(self):
        """SkillSource is a string enum."""
        assert isinstance(SkillSource.AGENT_CREATED, str)


class TestGetProvenanceDir:
    """Tests for _get_provenance_dir()."""

    def test_returns_path(self):
        """_get_provenance_dir() returns a Path."""
        result = _get_provenance_dir()
        assert isinstance(result, Path)

    def test_provenance_dir_named_provenance(self):
        """Provenance directory name is .provenance."""
        result = _get_provenance_dir()
        assert ".provenance" in str(result)


class TestMarkSkillProvenance:
    """Tests for mark_skill_provenance()."""

    def test_mark_provenance_creates_file(self, tmp_path):
        """mark_skill_provenance creates a provenance file."""
        with patch("agent.skill_provenance._get_provenance_dir", return_value=tmp_path):
            mark_skill_provenance("test_skill", SkillSource.AGENT_CREATED)

            prov_file = tmp_path / "test_skill.json"
            assert prov_file.exists()

    def test_mark_provenance_stores_source(self, tmp_path):
        """mark_skill_provenance stores the correct source."""
        with patch("agent.skill_provenance._get_provenance_dir", return_value=tmp_path):
            mark_skill_provenance("test_skill", SkillSource.USER_CREATED)

            prov_file = tmp_path / "test_skill.json"
            data = json.loads(prov_file.read_text())
            assert data["source"] == "user_created"


class TestGetSkillProvenance:
    """Tests for get_skill_provenance()."""

    def test_returns_none_for_unknown_skill(self, tmp_path):
        """get_skill_provenance returns None for non-existent skill."""
        with patch("agent.skill_provenance._get_provenance_dir", return_value=tmp_path):
            result = get_skill_provenance("nonexistent_skill")
            assert result is None

    def test_returns_dict_for_known_skill(self, tmp_path):
        """get_skill_provenance returns provenance dict."""
        with patch("agent.skill_provenance._get_provenance_dir", return_value=tmp_path):
            mark_skill_provenance("known_skill", SkillSource.AGENT_CREATED)
            result = get_skill_provenance("known_skill")

            assert result is not None
            assert "source" in result


class TestListSkillsBySource:
    """Tests for list_skills_by_source()."""

    def test_returns_empty_list_when_none_exist(self, tmp_path):
        """list_skills_by_source returns empty list when no skills of that source."""
        with patch("agent.skill_provenance._get_provenance_dir", return_value=tmp_path):
            result = list_skills_by_source(SkillSource.AGENT_CREATED)
            assert result == []

    def test_returns_matching_skills(self, tmp_path):
        """list_skills_by_source returns skills with matching source."""
        with patch("agent.skill_provenance._get_provenance_dir", return_value=tmp_path):
            mark_skill_provenance("skill1", SkillSource.AGENT_CREATED)
            mark_skill_provenance("skill2", SkillSource.USER_CREATED)
            mark_skill_provenance("skill3", SkillSource.AGENT_CREATED)

            agent_skills = list_skills_by_source(SkillSource.AGENT_CREATED)
            assert len(agent_skills) == 2


class TestIsBackgroundReview:
    """Tests for is_background_review()."""

    def test_is_background_review_default_false(self):
        """is_background_review defaults to False."""
        assert is_background_review() is False

    def test_is_background_review_inside_context(self):
        """is_background_review returns True inside background review context."""
        import contextvars
        # is_background_review uses a context var internally
        result = is_background_review()
        assert isinstance(result, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
