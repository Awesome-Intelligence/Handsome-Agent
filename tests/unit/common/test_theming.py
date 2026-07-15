#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for common.theming (跨 tui/cli 共享的主题层)

🚪 Access - 💬 Tests - Common - Theming

覆盖：
- common.theming 顶层导入
- Theme dataclass 字段完整性
- _PRESET_THEMES 字典结构
- ThemeManager 单例、回调、透明度
- styles.transparency 动态 CSS 生成
- styles.loader 加载器
- tui.theming 向后兼容 shim
"""

from __future__ import annotations

import importlib
import os
import tempfile
from pathlib import Path
from unittest.mock import patch


class TestCommonThemingImports:
    """公共导入测试。"""

    def test_top_level_exports(self):
        from common.theming import Theme, _PRESET_THEMES, ThemeManager, get_theme_manager

        assert Theme is not None
        assert _PRESET_THEMES is not None
        assert ThemeManager is not None
        assert callable(get_theme_manager)

    def test_theme_dataclass_defaults(self):
        from common.theming import Theme

        t = Theme(theme_id="x", display_name_key="x")
        assert t.primary == "#B180D7"
        assert t.background == "#1a1a1a"


class TestPresetThemes:
    """预设主题测试。"""

    def test_preset_themes_keys(self):
        from common.theming import _PRESET_THEMES

        assert "default" in _PRESET_THEMES
        assert "awesome" in _PRESET_THEMES

    def test_preset_themes_are_theme_instances(self):
        from common.theming import _PRESET_THEMES, Theme

        for tid, theme in _PRESET_THEMES.items():
            assert isinstance(theme, Theme), f"{tid} not a Theme instance"


class TestThemeManagerBasics:
    """ThemeManager 基础行为。"""

    def _make_isolated_manager(self):
        """创建与全局 ~/.handsome_agent/tui_config.json 隔离的实例。"""
        from common.theming.theme_manager import ThemeManager

        ThemeManager._instance = None
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(
                ThemeManager, "_get_config_path",
                lambda self: Path(tmp) / "tui_config.json",
            ):
                m = ThemeManager()
        return m

    def test_singleton_returns_same_instance(self):
        from common.theming.theme_manager import ThemeManager

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(
                ThemeManager, "_get_config_path",
                lambda self: Path(tmp) / "tui_config.json",
            ):
                ThemeManager._instance = None
                a = ThemeManager.get_instance()
                b = ThemeManager.get_instance()
                assert a is b

    def test_default_theme_id(self):
        m = self._make_isolated_manager()
        assert m.get_current_theme_id() == "default"

    def test_set_theme_invalid_id_returns_false(self):
        m = self._make_isolated_manager()
        assert m.set_theme("nonexistent_theme_xyz") is False

    def test_set_theme_default_returns_true(self):
        m = self._make_isolated_manager()
        assert m.set_theme("default") is True
        assert m.get_current_theme_id() == "default"


class TestThemeManagerTransparency:
    """透明度开关与级别。"""

    def _make_isolated_manager(self):
        """创建与全局 ~/.handsome_agent/tui_config.json 隔离的实例。"""
        from common.theming.theme_manager import ThemeManager

        ThemeManager._instance = None
        with tempfile.TemporaryDirectory() as tmp:
            # 让 _get_config_path 指向临时目录
            with patch.object(
                ThemeManager, "_get_config_path",
                lambda self: Path(tmp) / "tui_config.json",
            ):
                m = ThemeManager()
        return m

    def test_transparency_default_disabled(self):
        m = self._make_isolated_manager()
        assert m.is_transparency_enabled() is False

    def test_toggle_transparency(self):
        m = self._make_isolated_manager()
        original = m.is_transparency_enabled()
        new = m.toggle_transparency()
        assert new != original

    def test_transparency_level_clamped(self):
        m = self._make_isolated_manager()
        m.set_transparency_level(2.0)  # 超出范围
        assert m.get_transparency_level() == 1.0
        m.set_transparency_level(-1.0)
        assert m.get_transparency_level() == 0.0


class TestThemeManagerCallback:
    """主题变更回调测试。"""

    def test_register_and_invoke_callback(self):
        from common.theming.theme_manager import ThemeManager

        ThemeManager._instance = None
        m = ThemeManager()

        received = []
        m.register_theme_change_callback(lambda tid: received.append(tid))

        m.set_theme("default")
        assert "default" in received

    def test_callback_exception_does_not_propagate(self):
        from common.theming.theme_manager import ThemeManager

        ThemeManager._instance = None
        m = ThemeManager()

        def bad_callback(tid):
            raise RuntimeError("intentional")

        m.register_theme_change_callback(bad_callback)
        # 不应抛出
        m.set_theme("default")


class TestTransparencyCSSGenerator:
    """动态透明度 CSS 测试。"""

    def test_disabled_returns_empty(self):
        from common.theming.styles.transparency import generate_transparent_css

        assert generate_transparent_css(0.85, enabled=False) == ""

    def test_default_level_produces_css(self):
        from common.theming.styles.transparency import generate_transparent_css

        css = generate_transparent_css()
        assert ".transparent-header" in css
        assert "--transparency-alpha" in css

    def test_alpha_hex_format(self):
        from common.theming.styles.transparency import generate_transparent_css

        # level=1.0 → alpha_hex="FF"
        css = generate_transparent_css(level=1.0)
        assert "--transparency-hex: FF" in css

        # level=0.0 → alpha_hex="00"
        css = generate_transparent_css(level=0.0)
        assert "--transparency-hex: 00" in css

    def test_alpha_clamped(self):
        from common.theming.styles.transparency import generate_transparent_css

        # level > 1.0 应被裁剪到 1.0
        css_high = generate_transparent_css(level=2.0)
        assert "--transparency-hex: FF" in css_high

        # level < 0.0 应被裁剪到 0.0
        css_low = generate_transparent_css(level=-0.5)
        assert "--transparency-hex: 00" in css_low


class TestStylesLoader:
    """CSS 加载器测试。"""

    def test_list_app_stylesheets_returns_four(self):
        from common.theming.styles import list_app_stylesheets

        sheets = list_app_stylesheets()
        assert len(sheets) == 4
        assert any("base.css" in s for s in sheets)
        assert any("layout.css" in s for s in sheets)
        assert any("components.css" in s for s in sheets)
        assert any("animations.css" in s for s in sheets)

    def test_list_theme_stylesheets_default(self):
        from common.theming.styles import list_theme_stylesheets

        sheets = list_theme_stylesheets("default")
        assert len(sheets) == 1
        assert sheets[0].exists()

    def test_list_theme_stylesheets_unknown(self):
        from common.theming.styles import list_theme_stylesheets

        sheets = list_theme_stylesheets("nonexistent_theme_xyz")
        assert sheets == []


class TestBackwardsCompatShim:
    """tui.theming 兼容层测试。"""

    def test_tui_theming_re_exports_theme_manager(self):
        tui_theming = importlib.import_module("tui.theming")
        common_theming = importlib.import_module("common.theming")

        # 必须指向同一对象
        assert tui_theming.ThemeManager is common_theming.ThemeManager
        assert tui_theming.get_theme_manager is common_theming.get_theme_manager

    def test_tui_theming_keeps_local_utils(self):
        tui_theming = importlib.import_module("tui.theming")

        # 仍保留 tui 本地工具
        assert hasattr(tui_theming, "MESSAGE_ICONS")
        assert hasattr(tui_theming, "FILE_TYPE_ICONS")
        assert hasattr(tui_theming, "TypographyConfig")

    def test_tui_theming_css_package_works(self):
        css = importlib.import_module("tui.theming.css")
        common_css = importlib.import_module("common.theming.css")

        assert css.get_stylesheets is common_css.get_stylesheets
        assert css.get_theme_css is common_css.get_theme_css

    def test_get_stylesheets_returns_valid_paths(self):
        from tui.theming.css import get_stylesheets

        sheets = get_stylesheets()
        for s in sheets:
            assert Path(s).exists(), f"Not found: {s}"


class TestReverseDependencyNote:
    """注意：tui.theming 仍属于 tui 模块；common.theming 不反向依赖 tui。"""

    def test_common_theming_does_not_import_tui(self):
        """common.theming 不应反向依赖 tui。"""
        import pathlib

        common_theming_dir = pathlib.Path("common/theming")
        offenders = []
        for py in common_theming_dir.rglob("*.py"):
            if "__pycache__" in py.parts:
                continue
            content = py.read_text(encoding="utf-8")
            if "import tui" in content or "from tui" in content:
                offenders.append(str(py))

        assert offenders == [], (
            f"common.theming 不应 import tui，但发现：{offenders}"
        )