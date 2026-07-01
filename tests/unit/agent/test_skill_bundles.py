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


class TestSkillBundlesCompat:
    """SkillBundle 兼容性函数测试"""

    def test_slugify(self):
        """测试名称转 slug"""
        from agent.skills.skill_command_bundle import _slugify

        assert _slugify("Backend Dev") == "backend-dev"
        assert _slugify("my_skill") == "my-skill"
        assert _slugify("UpperCase") == "uppercase"

    def test_save_and_load_bundle(self, temp_bundles_dir):
        """测试保存和加载 bundle"""
        from agent.skills.skill_command_bundle import save_bundle, get_skill_bundles, delete_bundle

        # 保存 bundle 到临时目录
        temp_config_dir = temp_bundles_dir.parent.parent  # tmp_path 的父级

        with patch('common.config.get_config_dir', return_value=temp_config_dir):
            # 保存 bundle
            path = save_bundle(
                name="backend-dev",
                skills=["code-review", "testing", "pr-workflow"],
                description="Backend development skills",
                instruction="Focus on code quality",
            )

            assert path.exists()
            assert path.name == "backend-dev.yaml"

            # 加载 bundle
            bundles = get_skill_bundles()
            assert "/backend-dev" in bundles
            assert bundles["/backend-dev"]["skills"] == ["code-review", "testing", "pr-workflow"]
            assert bundles["/backend-dev"]["description"] == "Backend development skills"

            # 删除 bundle
            delete_bundle("backend-dev")
            assert not path.exists()

    def test_resolve_bundle_command_key(self, temp_bundles_dir):
        """测试命令解析"""
        from agent.skills.skill_command_bundle import save_bundle, resolve_bundle_command_key

        temp_config_dir = temp_bundles_dir.parent.parent

        with patch('common.config.get_config_dir', return_value=temp_config_dir):
            save_bundle(name="My Bundle", skills=["skill1"])

            assert resolve_bundle_command_key("my-bundle") == "/my-bundle"
            assert resolve_bundle_command_key("my_bundle") == "/my-bundle"
            assert resolve_bundle_command_key("unknown") is None

    def test_get_bundle(self, temp_bundles_dir):
        """测试获取单个 bundle"""
        from agent.skills.skill_command_bundle import save_bundle, get_bundle

        temp_config_dir = temp_bundles_dir.parent.parent

        with patch('common.config.get_config_dir', return_value=temp_config_dir):
            save_bundle(name="test-get", skills=["skill1", "skill2"])

            bundle = get_bundle("test-get")
            assert bundle is not None
            assert bundle["name"] == "test-get"
            assert bundle["skills"] == ["skill1", "skill2"]

            # 不存在的 bundle
            assert get_bundle("nonexistent") is None


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
