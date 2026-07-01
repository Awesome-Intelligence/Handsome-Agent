#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
渐进式披露模块测试
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from agent.progressive_disclosure import (
    ProgressiveDisclosureManager,
    SkillsIndexCache,
    SkillLoader,
    SupportFileLoader,
    build_skills_index_for_prompt,
    get_progressive_disclosure_manager,
    invalidate_skills_cache,
    load_skill_full,
)


@pytest.fixture
def temp_skills_dir():
    """创建临时技能目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        yield tmp_path


@pytest.fixture
def sample_skills(temp_skills_dir):
    """创建示例技能"""
    skill_dir = temp_skills_dir / "general" / "test-skill"
    skill_dir.mkdir(parents=True)

    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("""---
name: Test Skill
description: A test skill for unit testing
category: general
tags: [test, unit]
---

# Test Skill

This is a test skill content.

## Examples

- Example 1
- Example 2
""", encoding="utf-8")

    # 创建脚本目录
    scripts_dir = skill_dir / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "helper.sh").write_text("#!/bin/bash\necho 'test'", encoding="utf-8")

    # 创建资源目录
    assets_dir = skill_dir / "assets"
    assets_dir.mkdir()
    (assets_dir / "readme.txt").write_text("Asset file", encoding="utf-8")

    return temp_skills_dir


class TestSkillsIndexCache:
    """SkillsIndexCache 测试"""

    def test_init(self, temp_skills_dir):
        cache = SkillsIndexCache(temp_skills_dir)
        assert cache.skills_dir == temp_skills_dir

    def test_cache_invalidation(self, temp_skills_dir):
        cache = SkillsIndexCache(temp_skills_dir)
        cache.invalidate()
        # 应该不抛出异常


class TestSkillLoader:
    """SkillLoader 测试"""

    def test_load_skill(self, sample_skills):
        loader = SkillLoader(sample_skills)
        result = loader.load_skill("Test Skill")
        assert result is not None
        assert result["name"] == "Test Skill"
        assert "test skill content" in result["content"].lower()
        assert result["category"] == "general"

    def test_load_skill_by_directory_name(self, sample_skills):
        loader = SkillLoader(sample_skills)
        result = loader.load_skill("test-skill")
        assert result is not None

    def test_load_nonexistent_skill(self, sample_skills):
        loader = SkillLoader(sample_skills)
        result = loader.load_skill("NonExistent")
        assert result is None

    def test_get_skill_metadata(self, sample_skills):
        loader = SkillLoader(sample_skills)
        metadata = loader.get_skill_metadata("Test Skill")
        assert metadata is not None
        assert metadata["name"] == "Test Skill"
        assert metadata["description"] == "A test skill for unit testing"


class TestSupportFileLoader:
    """SupportFileLoader 测试"""

    def test_list_support_files(self, sample_skills):
        loader = SupportFileLoader()
        skill_dir = sample_skills / "general" / "test-skill"
        files = loader.list_support_files(skill_dir)
        assert len(files) > 0

    def test_load_skill_scripts(self, sample_skills):
        loader = SupportFileLoader()
        skill_dir = sample_skills / "general" / "test-skill"
        scripts = loader.load_skill_scripts(skill_dir)
        assert "helper.sh" in scripts
        assert "#!/bin/bash" in scripts["helper.sh"]


class TestBuildSkillsIndex:
    """技能索引构建测试"""

    def test_build_empty_index(self, temp_skills_dir):
        prompt = build_skills_index_for_prompt(temp_skills_dir)
        assert prompt == ""

    def test_build_index_with_skills(self, sample_skills):
        prompt = build_skills_index_for_prompt(sample_skills)
        assert "Test Skill" in prompt
        assert "A test skill for unit testing" in prompt
        assert "<available_skills>" in prompt
        assert "</available_skills>" in prompt


class TestProgressiveDisclosureManager:
    """渐进式披露管理器测试"""

    def test_get_system_prompt_index(self, sample_skills):
        manager = ProgressiveDisclosureManager(sample_skills)
        prompt = manager.get_system_prompt_index()
        assert "Test Skill" in prompt

    def test_load_skill_content(self, sample_skills):
        manager = ProgressiveDisclosureManager(sample_skills)
        content = manager.load_skill_content("Test Skill")
        assert content is not None
        assert content["name"] == "Test Skill"

    def test_load_support_files(self, sample_skills):
        manager = ProgressiveDisclosureManager(sample_skills)
        support = manager.load_support_files("test-skill")
        assert "files" in support
        assert len(support["files"]) > 0

    def test_get_skill_tier_info(self, sample_skills):
        manager = ProgressiveDisclosureManager(sample_skills)
        tier_info = manager.get_skill_tier_info("Test Skill")
        assert tier_info["tier1"] is True
        assert tier_info["tier2"] is True
        assert tier_info["tier3"] is True


class TestCacheMechanism:
    """缓存机制测试"""

    def test_cache_invalidation(self, sample_skills):
        # 第一次构建
        prompt1 = build_skills_index_for_prompt(sample_skills)
        assert "Test Skill" in prompt1

        # 使缓存失效
        invalidate_skills_cache()

        # 第二次构建应该仍能正常工作
        prompt2 = build_skills_index_for_prompt(sample_skills)
        assert "Test Skill" in prompt2
