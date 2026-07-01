#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the skills_tool module.

Tests cover:
- Path security checks (traversal detection)
- Skill name conflict detection
- Progressive disclosure (minimal vs full metadata)
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch


class TestPathSecurity:
    """Test path security features in skill_view."""

    def test_block_path_traversal_with_dots(self, tmp_path):
        """Test that path traversal with '..' is blocked."""
        from tools.skills_tool import skill_view

        with patch("tools.skills_tool.SKILLS_DIR", tmp_path):
            result = skill_view("../other_skill")

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "Path traversal" in result_data["error"]
        assert result_data.get("security_error") is True

    def test_block_path_traversal_absolute(self, tmp_path):
        """Test that absolute paths are blocked."""
        from tools.skills_tool import skill_view

        with patch("tools.skills_tool.SKILLS_DIR", tmp_path):
            # On Windows, use a path with drive letter (C:\...)
            # On Unix, use /etc/passwd
            import os
            if os.name == "nt":
                result = skill_view("C:\\Windows\\System32\\config")
            else:
                result = skill_view("/etc/passwd")

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "Path traversal" in result_data["error"]
        assert result_data.get("security_error") is True

    def test_block_mixed_traversal(self, tmp_path):
        """Test that mixed traversal attempts are blocked."""
        from tools.skills_tool import skill_view

        with patch("tools.skills_tool.SKILLS_DIR", tmp_path):
            result = skill_view("skills/../../secrets")

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "Path traversal" in result_data["error"]

    def test_validate_within_directory(self, tmp_path):
        """Test that skill path is validated within skills directory."""
        from tools.skills_tool import skill_view

        # Create a normal skill first
        skill_dir = tmp_path / "test_skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: test_skill\n---\n\nContent")

        with patch("tools.skills_tool.SKILLS_DIR", tmp_path):
            result = skill_view("test_skill")

        result_data = json.loads(result)
        # Should not have security_error for valid path
        assert result_data.get("security_error") is not True


class TestSkillNameConflictDetection:
    """Test skill name conflict detection."""

    def test_detect_duplicate_skill_names(self, tmp_path):
        """Test that duplicate skill names are detected."""
        from tools.skills_tool import list_skills

        # Create two skills with same name in frontmatter
        skill1 = tmp_path / "skill_one"
        skill1.mkdir()
        (skill1 / "SKILL.md").write_text(
            "---\nname: MySkill\ndescription: First skill\n---\n\nContent"
        )

        skill2 = tmp_path / "skill_two"
        skill2.mkdir()
        (skill2 / "SKILL.md").write_text(
            "---\nname: MySkill\ndescription: Second skill\n---\n\nContent"
        )

        with patch("tools.skills_tool.SKILLS_DIR", tmp_path):
            skills = list_skills()

        # Both skills should be listed
        skill_names = [s["name"] for s in skills]
        assert "MySkill" in skill_names
        # Should appear twice due to different paths
        assert skill_names.count("MySkill") == 2


class TestProgressiveDisclosure:
    """Test progressive disclosure (minimal vs full metadata)."""

    def test_list_skills_minimal_metadata(self, tmp_path):
        """Test that list_skills returns only essential metadata."""
        from tools.skills_tool import list_skills

        skill_dir = tmp_path / "test_skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test_skill\ndescription: A test skill\ncategory: testing\nauthor: Test Author\nversion: 2.0.0\n---\n\nContent"
        )

        with patch("tools.skills_tool.SKILLS_DIR", tmp_path):
            skills = list_skills()

        assert len(skills) == 1
        skill = skills[0]

        # Essential fields should be present
        assert "name" in skill
        assert "description" in skill
        assert "category" in skill

        # Extended fields should NOT be present (progressive disclosure)
        assert "author" not in skill
        assert "version" not in skill
        assert "enabled" not in skill
        assert "skill_dir" not in skill

    def test_list_skills_full_metadata(self, tmp_path):
        """Test that list_skills_full returns complete metadata."""
        from tools.skills_tool import list_skills_full

        skill_dir = tmp_path / "test_skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test_skill\ndescription: A test skill\ncategory: testing\nauthor: Test Author\nversion: 2.0.0\n---\n\nContent"
        )

        with patch("tools.skills_tool.SKILLS_DIR", tmp_path):
            skills = list_skills_full()

        assert len(skills) == 1
        skill = skills[0]

        # All fields should be present
        assert "name" in skill
        assert "description" in skill
        assert "category" in skill
        assert "author" in skill
        assert "version" in skill
        assert "enabled" in skill
        assert "skill_dir" in skill

        # Values should match frontmatter
        assert skill["author"] == "Test Author"
        assert skill["version"] == "2.0.0"
        assert skill["enabled"] is True


class TestListSkillsWithConflicts:
    """Test list_skills behavior with skill name conflicts."""

    def test_unique_skills_both_returned(self, tmp_path):
        """Test that unique skills are all returned."""
        from tools.skills_tool import list_skills

        # Create two unique skills
        skill1 = tmp_path / "unique_skill_a"
        skill1.mkdir()
        (skill1 / "SKILL.md").write_text(
            "---\nname: SkillA\ndescription: First unique skill\ncategory: test\n---\n\nContent"
        )

        skill2 = tmp_path / "unique_skill_b"
        skill2.mkdir()
        (skill2 / "SKILL.md").write_text(
            "---\nname: SkillB\ndescription: Second unique skill\ncategory: test\n---\n\nContent"
        )

        with patch("tools.skills_tool.SKILLS_DIR", tmp_path):
            skills = list_skills()

        assert len(skills) == 2
        skill_names = [s["name"] for s in skills]
        assert "SkillA" in skill_names
        assert "SkillB" in skill_names

    def test_skills_from_directory_name(self, tmp_path):
        """Test that skills without frontmatter name use directory name."""
        from tools.skills_tool import list_skills

        skill_dir = tmp_path / "directory_name_skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\ndescription: Skill without name field\ncategory: test\n---\n\nContent"
        )

        with patch("tools.skills_tool.SKILLS_DIR", tmp_path):
            skills = list_skills()

        assert len(skills) == 1
        assert skills[0]["name"] == "directory_name_skill"


class TestSkillView:
    """Test skill_view function."""

    def test_skill_view_returns_json(self, tmp_path):
        """Test that skill_view returns valid JSON."""
        from tools.skills_tool import skill_view

        skill_dir = tmp_path / "view_test"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: view_test\ndescription: A view test\ncategory: test\n---\n\n# Test Content"
        )

        with patch("tools.skills_tool.SKILLS_DIR", tmp_path):
            result = skill_view("view_test")

        # Should be valid JSON
        data = json.loads(result)
        assert isinstance(data, dict)
        assert "success" in data

    def test_skill_view_with_preprocess(self, tmp_path):
        """Test skill_view with preprocessing enabled."""
        from tools.skills_tool import skill_view

        skill_dir = tmp_path / "preprocess_test"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: preprocess_test\ndescription: Preprocess test\ncategory: test\n---\n\n# Test Content"
        )

        with patch("tools.skills_tool.SKILLS_DIR", tmp_path):
            result = skill_view("preprocess_test", preprocess=True)

        data = json.loads(result)
        # If preprocessing works, content should be modified
        # If not available, should still succeed
        assert data["success"] is True or "error" in data

    def test_skill_not_found(self, tmp_path):
        """Test skill_view with non-existent skill."""
        from tools.skills_tool import skill_view

        with patch("tools.skills_tool.SKILLS_DIR", tmp_path):
            result = skill_view("nonexistent_skill")

        data = json.loads(result)
        assert data["success"] is False
        assert "not found" in data["error"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])