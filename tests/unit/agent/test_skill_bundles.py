#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""技能包（Skill Bundle）单元测试

测试 agent.skills.skill_command_bundle 模块的兼容性函数。
"""

import pytest
from pathlib import Path
from unittest.mock import patch


@pytest.fixture
def temp_bundles_dir(tmp_path):
    """创建临时 bundles 目录"""
    bundles_dir = tmp_path / "skill-bundles"
    bundles_dir.mkdir()
    return bundles_dir


class TestSkillBundleManager:
    """SkillBundleManager 类测试"""

    def test_skill_bundle_class(self):
        """测试 SkillBundle 数据类"""
        from agent.skills.skill_command_bundle import SkillBundle

        bundle = SkillBundle(
            name="Test Bundle",
            slug="test-bundle",
            description="A test bundle",
            skills=["skill1", "skill2"],
            instruction="Test instruction",
        )

        assert bundle.name == "Test Bundle"
        assert bundle.slug == "test-bundle"
        assert len(bundle.skills) == 2

    def test_bundle_manager_create(self, temp_bundles_dir):
        """测试 SkillBundleManager 创建"""
        from agent.skills.skill_command_bundle import SkillBundleManager

        manager = SkillBundleManager(bundles_dir=str(temp_bundles_dir))
        assert manager._bundles_dir == temp_bundles_dir

    def test_atomic_replace(self, temp_bundles_dir):
        """测试原子替换函数"""
        from agent.skills.skill_command_bundle import atomic_replace

        # 创建目标文件
        target = temp_bundles_dir / "test.txt"
        target.write_text("original")

        # 创建临时文件
        tmp = temp_bundles_dir / "test.txt.tmp"
        tmp.write_text("updated")

        # 执行原子替换
        atomic_replace(tmp, target)

        assert target.read_text() == "updated"
        assert not tmp.exists()
