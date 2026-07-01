#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Pinned Skill functionality in SkillManager.

Tests cover:
- pin_skill: pinning a skill
- unpin_skill: unpinning a skill
- delete_pinned_skill_fails: preventing deletion of pinned skills without force
- delete_pinned_skill_with_force: forcing deletion of pinned skills
- list_pinned_skills: listing all pinned skills
- is_pinned: checking if a skill is pinned
"""

import pytest


class MockMetadata:
    """Mock metadata that persists state changes."""

    def __init__(self, skill_id: str, name: str):
        self.id = skill_id
        self.name = name
        self.description = "A mock skill for testing"
        self.category = "test"
        self.pinned = False
        self.pinned_at = None
        self.pinned_by = ""
        self.tags = []
        self.aliases = []
        self.related_skills = []


class MockSkill:
    """Mock skill for testing."""

    def __init__(self, skill_id: str = "test_skill", name: str = "Test Skill"):
        self._skill_id = skill_id
        self._name = name
        self._metadata = MockMetadata(skill_id, name)

    def get_metadata(self):
        return self._metadata


class TestPinSkill:
    """Test pin_skill functionality."""

    def test_pin_skill(self):
        """Test pinning a skill sets pinned=True and pinned_at."""
        from agent.skills.skill_manager import SkillManager
        manager = SkillManager()

        skill = MockSkill("test_skill", "Test Skill")
        manager.register_skill(skill)

        result = manager.pin_skill("test_skill", pinned_by="test_user")

        assert result is True
        metadata = manager.get_skill("test_skill").get_metadata()
        assert metadata.pinned is True
        assert metadata.pinned_at is not None
        assert metadata.pinned_by == "test_user"

    def test_pin_skill_nonexistent(self):
        """Test pinning a nonexistent skill returns False."""
        from agent.skills.skill_manager import SkillManager
        manager = SkillManager()

        result = manager.pin_skill("nonexistent_skill")

        assert result is False

    def test_pin_skill_default_pinned_by(self):
        """Test pinning uses default 'user' pinned_by."""
        from agent.skills.skill_manager import SkillManager
        manager = SkillManager()

        skill = MockSkill("test_skill", "Test Skill")
        manager.register_skill(skill)

        manager.pin_skill("test_skill")

        metadata = manager.get_skill("test_skill").get_metadata()
        assert metadata.pinned_by == "user"


class TestUnpinSkill:
    """Test unpin_skill functionality."""

    def test_unpin_skill(self):
        """Test unpinning a skill sets pinned=False."""
        from agent.skills.skill_manager import SkillManager
        manager = SkillManager()

        skill = MockSkill("test_skill", "Test Skill")
        manager.register_skill(skill)

        manager.pin_skill("test_skill")
        result = manager.unpin_skill("test_skill")

        assert result is True
        metadata = manager.get_skill("test_skill").get_metadata()
        assert metadata.pinned is False
        assert metadata.pinned_at is None
        assert metadata.pinned_by == ""

    def test_unpin_skill_not_pinned(self):
        """Test unpinning a skill that is not pinned returns False."""
        from agent.skills.skill_manager import SkillManager
        manager = SkillManager()

        skill = MockSkill("test_skill", "Test Skill")
        manager.register_skill(skill)

        result = manager.unpin_skill("test_skill")

        assert result is False

    def test_unpin_skill_nonexistent(self):
        """Test unpinning a nonexistent skill returns False."""
        from agent.skills.skill_manager import SkillManager
        manager = SkillManager()

        result = manager.unpin_skill("nonexistent_skill")

        assert result is False


class TestDeletePinnedSkillFails:
    """Test preventing deletion of pinned skills."""

    def test_delete_pinned_skill_fails(self):
        """Test deleting a pinned skill without force raises PermissionError."""
        from agent.skills.skill_manager import SkillManager
        manager = SkillManager()

        skill = MockSkill("pinned_skill", "Pinned Skill")
        manager.register_skill(skill)

        manager.pin_skill("pinned_skill")

        with pytest.raises(PermissionError) as exc_info:
            manager.unregister_skill("pinned_skill", force=False)

        assert "pinned_skill" in str(exc_info.value)

    def test_delete_pinned_skill_without_force_flag(self):
        """Test deleting a pinned skill with default force=False raises PermissionError."""
        from agent.skills.skill_manager import SkillManager
        manager = SkillManager()

        skill = MockSkill("pinned_skill", "Pinned Skill")
        manager.register_skill(skill)

        manager.pin_skill("pinned_skill")

        with pytest.raises(PermissionError):
            manager.unregister_skill("pinned_skill")

    def test_delete_unpinned_skill_succeeds(self):
        """Test deleting an unpinned skill succeeds."""
        from agent.skills.skill_manager import SkillManager
        manager = SkillManager()

        skill = MockSkill("unpinned_skill", "Unpinned Skill")
        manager.register_skill(skill)

        manager.unregister_skill("unpinned_skill")

        assert manager.get_skill("unpinned_skill") is None


class TestDeletePinnedSkillWithForce:
    """Test forcing deletion of pinned skills."""

    def test_delete_pinned_skill_with_force(self):
        """Test force deleting a pinned skill succeeds."""
        from agent.skills.skill_manager import SkillManager
        manager = SkillManager()

        skill = MockSkill("pinned_skill", "Pinned Skill")
        manager.register_skill(skill)

        manager.pin_skill("pinned_skill")
        manager.unregister_skill("pinned_skill", force=True)

        assert manager.get_skill("pinned_skill") is None

    def test_force_delete_nonexistent_skill(self):
        """Test force deleting a nonexistent skill is handled gracefully."""
        from agent.skills.skill_manager import SkillManager
        manager = SkillManager()

        manager.unregister_skill("nonexistent_skill", force=True)

        assert manager.get_skill("nonexistent_skill") is None


class TestListPinnedSkills:
    """Test listing pinned skills."""

    def test_list_pinned_skills(self):
        """Test listing pinned skills returns correct count."""
        from agent.skills.skill_manager import SkillManager
        manager = SkillManager()

        skill1 = MockSkill("skill_1", "Skill 1")
        skill2 = MockSkill("skill_2", "Skill 2")
        skill3 = MockSkill("skill_3", "Skill 3")

        manager.register_skill(skill1)
        manager.register_skill(skill2)
        manager.register_skill(skill3)

        manager.pin_skill("skill_1")
        manager.pin_skill("skill_3")

        pinned_skills = manager.list_pinned_skills()

        assert len(pinned_skills) == 2
        pinned_ids = [m.id for m in pinned_skills]
        assert "skill_1" in pinned_ids
        assert "skill_3" in pinned_ids

    def test_list_pinned_skills_empty(self):
        """Test listing pinned skills when none are pinned."""
        from agent.skills.skill_manager import SkillManager
        manager = SkillManager()

        skill = MockSkill("test_skill", "Test Skill")
        manager.register_skill(skill)

        pinned_skills = manager.list_pinned_skills()

        assert len(pinned_skills) == 0

    def test_list_pinned_skills_only_returns_original(self):
        """Test list_pinned_skills only returns original skills, not aliases."""
        from agent.skills.skill_manager import SkillManager
        manager = SkillManager()

        skill = MockSkill("original_skill", "Original Skill")
        manager.register_skill(skill)

        # Set up alias manually
        manager.skills["alias_skill"] = skill

        manager.pin_skill("original_skill")

        pinned_skills = manager.list_pinned_skills()

        assert len(pinned_skills) == 1
        assert pinned_skills[0].id == "original_skill"


class TestIsPinned:
    """Test is_pinned functionality."""

    def test_is_pinned_true(self):
        """Test is_pinned returns True for pinned skill."""
        from agent.skills.skill_manager import SkillManager
        manager = SkillManager()

        skill = MockSkill("test_skill", "Test Skill")
        manager.register_skill(skill)

        manager.pin_skill("test_skill")

        assert manager.is_pinned("test_skill") is True

    def test_is_pinned_false(self):
        """Test is_pinned returns False for unpinned skill."""
        from agent.skills.skill_manager import SkillManager
        manager = SkillManager()

        skill = MockSkill("test_skill", "Test Skill")
        manager.register_skill(skill)

        assert manager.is_pinned("test_skill") is False

    def test_is_pinned_after_unpin(self):
        """Test is_pinned returns False after unpinning."""
        from agent.skills.skill_manager import SkillManager
        manager = SkillManager()

        skill = MockSkill("test_skill", "Test Skill")
        manager.register_skill(skill)

        manager.pin_skill("test_skill")
        manager.unpin_skill("test_skill")

        assert manager.is_pinned("test_skill") is False

    def test_is_pinned_nonexistent(self):
        """Test is_pinned returns False for nonexistent skill."""
        from agent.skills.skill_manager import SkillManager
        manager = SkillManager()

        assert manager.is_pinned("nonexistent_skill") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
