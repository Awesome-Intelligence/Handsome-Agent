#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the Skill Bundle module.

Tests cover:
- SkillBundleManager initialization
- Bundle creation (create_bundle)
- Bundle loading (load_bundle)
- Bundle deletion (delete_bundle)
- Bundle listing (list_bundles)
- Name slugification (_slugify)
- Bundle info retrieval (get_bundle_info)
"""

import pytest
import os
import sys
from pathlib import Path

# 直接从 skill_bundle.py 导入，避免触发 agent.skills 模块的完整初始化
import importlib.util
spec = importlib.util.spec_from_file_location(
    "skill_bundle", 
    Path(__file__).parent.parent.parent.parent / "agent" / "skills" / "skill_bundle.py"
)
skill_bundle_module = importlib.util.module_from_spec(spec)
sys.modules["skill_bundle"] = skill_bundle_module
spec.loader.exec_module(skill_bundle_module)

SkillBundleManager = skill_bundle_module.SkillBundleManager
SkillBundle = skill_bundle_module.SkillBundle


class TestSkillBundleManagerInit:
    """Test SkillBundleManager initialization."""

    def test_init_default_dir(self):
        """Test default initialization uses correct directory."""
        manager = SkillBundleManager()
        expected = Path.home() / ".handsome_agent" / "skill-bundles"
        assert manager._bundles_dir == expected

    def test_init_custom_dir(self, tmp_path):
        """Test initialization with custom directory."""
        manager = SkillBundleManager(bundles_dir=str(tmp_path))
        assert manager._bundles_dir == tmp_path

    def test_ensure_bundles_dir_creates_directory(self, tmp_path):
        """Test that _ensure_bundles_dir creates the directory."""
        subdir = tmp_path / "subdir" / "bundles"
        manager = SkillBundleManager(bundles_dir=str(subdir))
        assert subdir.exists()

    def test_cache_initialized_empty(self):
        """Test that cache is initialized empty."""
        manager = SkillBundleManager()
        assert manager._cache == {}


class TestSlugify:
    """Test _slugify method for name conversion."""

    def test_slugify_basic(self):
        """Test basic slugification."""
        manager = SkillBundleManager()
        assert manager._slugify("My Bundle") == "my-bundle"

    def test_slugify_with_underscore(self):
        """Test slugify with underscore."""
        manager = SkillBundleManager()
        assert manager._slugify("test_bundle") == "test-bundle"

    def test_slugify_mixed_case(self):
        """Test slugify with mixed case."""
        manager = SkillBundleManager()
        assert manager._slugify("TestBundle") == "testbundle"

    def test_slugify_with_spaces(self):
        """Test slugify with multiple spaces."""
        manager = SkillBundleManager()
        assert manager._slugify("hello   world") == "hello-world"

    def test_slugify_strips_whitespace(self):
        """Test slugify strips leading/trailing whitespace."""
        manager = SkillBundleManager()
        assert manager._slugify("  hello  ") == "hello"

    def test_slugify_removes_special_chars(self):
        """Test slugify removes special characters."""
        manager = SkillBundleManager()
        assert manager._slugify("test@#$%bundle") == "testbundle"

    def test_slugify_alphanumeric(self):
        """Test slugify with alphanumeric characters."""
        manager = SkillBundleManager()
        assert manager._slugify("Test123Bundle") == "test123bundle"


class TestCreateBundle:
    """Test create_bundle method."""

    def test_create_bundle(self, tmp_path):
        """Test creating a new bundle."""
        manager = SkillBundleManager(bundles_dir=str(tmp_path))
        result = manager.create_bundle(
            name="test-bundle",
            skills=["skill1", "skill2"],
            description="Test bundle"
        )
        assert result is True
        assert (tmp_path / "test-bundle.yaml").exists()

    def test_create_bundle_with_instruction(self, tmp_path):
        """Test creating a bundle with instruction."""
        manager = SkillBundleManager(bundles_dir=str(tmp_path))
        result = manager.create_bundle(
            name="test-bundle",
            skills=["skill1"],
            description="Test bundle",
            instruction="Custom instruction"
        )
        assert result is True
        assert (tmp_path / "test-bundle.yaml").exists()

    def test_create_bundle_duplicate_returns_false(self, tmp_path):
        """Test creating duplicate bundle returns False."""
        manager = SkillBundleManager(bundles_dir=str(tmp_path))
        manager.create_bundle(name="test-bundle", skills=["skill1"])
        result = manager.create_bundle(name="test-bundle", skills=["skill2"])
        assert result is False

    def test_create_bundle_updates_cache(self, tmp_path):
        """Test creating bundle also updates cache."""
        manager = SkillBundleManager(bundles_dir=str(tmp_path))
        manager.create_bundle(name="test-bundle", skills=["skill1"])
        assert "test-bundle" in manager._cache

    def test_create_bundle_without_description(self, tmp_path):
        """Test creating bundle without description."""
        manager = SkillBundleManager(bundles_dir=str(tmp_path))
        result = manager.create_bundle(
            name="simple-bundle",
            skills=["skill1", "skill2"]
        )
        assert result is True


class TestLoadBundle:
    """Test load_bundle method."""

    def test_load_bundle(self, tmp_path):
        """Test loading an existing bundle."""
        manager = SkillBundleManager(bundles_dir=str(tmp_path))
        manager.create_bundle(
            name="test-bundle",
            skills=["skill1", "skill2"],
            description="Test bundle"
        )

        bundle = manager.load_bundle("test-bundle")

        assert bundle is not None
        assert bundle.name == "test-bundle"
        assert bundle.slug == "test-bundle"
        assert bundle.skills == ["skill1", "skill2"]
        assert bundle.description == "Test bundle"

    def test_load_bundle_with_instruction(self, tmp_path):
        """Test loading bundle with instruction."""
        manager = SkillBundleManager(bundles_dir=str(tmp_path))
        manager.create_bundle(
            name="test-bundle",
            skills=["skill1"],
            instruction="Custom instruction"
        )

        bundle = manager.load_bundle("test-bundle")

        assert bundle is not None
        assert bundle.instruction == "Custom instruction"

    def test_load_nonexistent_bundle_returns_none(self, tmp_path):
        """Test loading non-existent bundle returns None."""
        manager = SkillBundleManager(bundles_dir=str(tmp_path))
        bundle = manager.load_bundle("nonexistent")
        assert bundle is None

    def test_load_bundle_uses_cache(self, tmp_path):
        """Test loading bundle uses cached value."""
        manager = SkillBundleManager(bundles_dir=str(tmp_path))
        manager.create_bundle(name="test-bundle", skills=["skill1"])

        bundle1 = manager.load_bundle("test-bundle")
        bundle2 = manager.load_bundle("test-bundle")

        assert bundle1 is bundle2

    def test_load_bundle_different_names_same_slug(self, tmp_path):
        """Test loading with different name formats that result in same slug."""
        manager = SkillBundleManager(bundles_dir=str(tmp_path))
        manager.create_bundle(name="test-bundle", skills=["skill1"])

        bundle1 = manager.load_bundle("test-bundle")
        bundle2 = manager.load_bundle("Test Bundle")
        bundle3 = manager.load_bundle("TEST_BUNDLE")

        assert bundle1 is not None
        assert bundle2 is not None
        assert bundle3 is not None
        assert bundle1.slug == bundle2.slug == bundle3.slug


class TestDeleteBundle:
    """Test delete_bundle method."""

    def test_delete_bundle(self, tmp_path):
        """Test deleting an existing bundle."""
        manager = SkillBundleManager(bundles_dir=str(tmp_path))
        manager.create_bundle(name="del-bundle", skills=["skill1"])
        result = manager.delete_bundle("del-bundle")

        assert result is True
        assert not (tmp_path / "del-bundle.yaml").exists()

    def test_delete_bundle_removes_from_cache(self, tmp_path):
        """Test deleting bundle removes it from cache."""
        manager = SkillBundleManager(bundles_dir=str(tmp_path))
        manager.create_bundle(name="del-bundle", skills=["skill1"])
        assert "del-bundle" in manager._cache

        manager.delete_bundle("del-bundle")

        assert "del-bundle" not in manager._cache

    def test_delete_nonexistent_bundle_returns_false(self, tmp_path):
        """Test deleting non-existent bundle returns False."""
        manager = SkillBundleManager(bundles_dir=str(tmp_path))
        result = manager.delete_bundle("nonexistent")
        assert result is False

    def test_delete_bundle_by_different_name(self, tmp_path):
        """Test deleting bundle using different name format."""
        manager = SkillBundleManager(bundles_dir=str(tmp_path))
        manager.create_bundle(name="del-bundle", skills=["skill1"])

        result = manager.delete_bundle("Del Bundle")

        assert result is True
        assert not (tmp_path / "del-bundle.yaml").exists()


class TestListBundles:
    """Test list_bundles method."""

    def test_list_bundles(self, tmp_path):
        """Test listing all bundles."""
        manager = SkillBundleManager(bundles_dir=str(tmp_path))
        manager.create_bundle("bundle1", ["skill1"])
        manager.create_bundle("bundle2", ["skill2"])

        bundles = manager.list_bundles()

        assert len(bundles) == 2
        bundle_names = {b.slug for b in bundles}
        assert "bundle1" in bundle_names
        assert "bundle2" in bundle_names

    def test_list_bundles_empty_directory(self, tmp_path):
        """Test listing when no bundles exist."""
        manager = SkillBundleManager(bundles_dir=str(tmp_path))
        bundles = manager.list_bundles()
        assert len(bundles) == 0

    def test_list_bundles_returns_cached(self, tmp_path):
        """Test list_bundles returns cached bundles."""
        manager = SkillBundleManager(bundles_dir=str(tmp_path))
        manager.create_bundle("bundle1", ["skill1"])

        manager.load_bundle("bundle1")
        bundles = manager.list_bundles()

        assert len(bundles) == 1

    def test_list_bundles_excludes_non_yaml_files(self, tmp_path):
        """Test list_bundles excludes non-YAML files."""
        manager = SkillBundleManager(bundles_dir=str(tmp_path))
        manager.create_bundle("valid-bundle", ["skill1"])

        (tmp_path / "readme.txt").write_text("README")
        (tmp_path / "invalid.yaml.bak").write_text("backup")

        bundles = manager.list_bundles()

        assert len(bundles) == 1
        assert bundles[0].slug == "valid-bundle"


class TestGetBundleInfo:
    """Test get_bundle_info method."""

    def test_get_bundle_info(self, tmp_path):
        """Test getting bundle info."""
        manager = SkillBundleManager(bundles_dir=str(tmp_path))
        manager.create_bundle(
            name="info-bundle",
            skills=["skill1", "skill2"],
            description="Test bundle"
        )

        info = manager.get_bundle_info("info-bundle")

        assert info is not None
        assert info['name'] == "info-bundle"
        assert info['slug'] == "info-bundle"
        assert info['description'] == "Test bundle"
        assert info['skills'] == ["skill1", "skill2"]
        assert info['skills_count'] == 2
        assert info['path'] == str(tmp_path / "info-bundle.yaml")

    def test_get_bundle_info_nonexistent(self, tmp_path):
        """Test getting info for non-existent bundle."""
        manager = SkillBundleManager(bundles_dir=str(tmp_path))
        info = manager.get_bundle_info("nonexistent")
        assert info is None


class TestSkillBundleModel:
    """Test SkillBundle dataclass."""

    def test_bundle_creation(self):
        """Test creating a SkillBundle."""
        bundle = SkillBundle(
            name="test-bundle",
            slug="test-bundle",
            skills=["skill1", "skill2"]
        )
        assert bundle.name == "test-bundle"
        assert bundle.slug == "test-bundle"
        assert bundle.skills == ["skill1", "skill2"]
        assert bundle.description == ""
        assert bundle.instruction == ""

    def test_bundle_with_all_fields(self):
        """Test creating bundle with all fields."""
        bundle = SkillBundle(
            name="test-bundle",
            slug="test-bundle",
            description="Test",
            skills=["skill1"],
            instruction="Instructions",
            path="/path/to/bundle.yaml"
        )
        assert bundle.description == "Test"
        assert bundle.instruction == "Instructions"
        assert bundle.path == "/path/to/bundle.yaml"


class TestBundleIntegration:
    """Integration tests for bundle operations."""

    def test_create_load_delete_workflow(self, tmp_path):
        """Test full create-load-delete workflow."""
        manager = SkillBundleManager(bundles_dir=str(tmp_path))

        create_result = manager.create_bundle(
            name="workflow-bundle",
            skills=["skill1", "skill2", "skill3"]
        )
        assert create_result is True

        bundle = manager.load_bundle("workflow-bundle")
        assert bundle is not None
        assert len(bundle.skills) == 3

        delete_result = manager.delete_bundle("workflow-bundle")
        assert delete_result is True

        loaded_after_delete = manager.load_bundle("workflow-bundle")
        assert loaded_after_delete is None

    def test_multiple_bundles_independent(self, tmp_path):
        """Test multiple bundles operate independently."""
        manager = SkillBundleManager(bundles_dir=str(tmp_path))

        manager.create_bundle("bundle-a", ["skill1"], description="Bundle A")
        manager.create_bundle("bundle-b", ["skill2"], description="Bundle B")

        bundle_a = manager.load_bundle("bundle-a")
        bundle_b = manager.load_bundle("bundle-b")

        assert bundle_a.description == "Bundle A"
        assert bundle_b.description == "Bundle B"
        assert bundle_a.skills != bundle_b.skills

        manager.delete_bundle("bundle-a")
        assert manager.load_bundle("bundle-b") is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
