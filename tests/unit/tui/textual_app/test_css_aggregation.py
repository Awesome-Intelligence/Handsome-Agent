#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for tui.textual_app.css subpackage

🚪 Access - 💬 Tests - TUI - CSS 模块化拼装

覆盖：
- 所有 9 个子模块可独立导入
- APP_CSS 拼装后包含所有原始 CSS 选择器
- 各 *_CSS 常量包含该域关键选择器
- tui.textual_app.app 仍能导入 APP_CSS（旧路径兼容）
"""

from __future__ import annotations


class TestCSSModulesImportable:
    """所有 CSS 子模块可独立导入。"""

    def test_subpackage_imports(self):
        from tui.textual_app.css import (
            BASE_CSS,
            CHAT_CSS,
            HEADER_CSS,
            STATUS_BAR_CSS,
            INPUT_AREA_CSS,
            SLASH_COMPLETION_CSS,
            SIDEBAR_LAYOUT_CSS,
            TRANSPARENCY_CSS,
            CUSTOM_MODEL_SCREEN_CSS,
        )

        for css in (
            BASE_CSS, CHAT_CSS, HEADER_CSS, STATUS_BAR_CSS,
            INPUT_AREA_CSS, SLASH_COMPLETION_CSS, SIDEBAR_LAYOUT_CSS,
            TRANSPARENCY_CSS, CUSTOM_MODEL_SCREEN_CSS,
        ):
            assert isinstance(css, str)
            assert css.strip(), "CSS block must not be empty"

    def test_app_css_attribute_exists(self):
        from tui.textual_app.css import APP_CSS

        assert isinstance(APP_CSS, str)
        assert len(APP_CSS) > 1000, "APP_CSS should aggregate substantial content"


class TestCSSBlockContent:
    """各分块包含正确选择器。"""

    def test_base_contains_screen(self):
        from tui.textual_app.css.base import BASE_CSS
        assert "Screen {" in BASE_CSS
        assert "$background" in BASE_CSS
        assert "MarkdownFence" in BASE_CSS

    def test_chat_contains_chat_area(self):
        from tui.textual_app.css.chat import CHAT_CSS
        assert "#chat-area" in CHAT_CSS
        assert "MessageList" in CHAT_CSS
        assert ".streaming-indicator" in CHAT_CSS

    def test_header_contains_app_header(self):
        from tui.textual_app.css.header import HEADER_CSS
        assert "#app-header" in HEADER_CSS
        assert "#welcome-banner" in HEADER_CSS
        assert "#theme-toggle" in HEADER_CSS

    def test_status_bar_contains_status_widgets(self):
        from tui.textual_app.css.status_bar import STATUS_BAR_CSS
        assert "#status-bar" in STATUS_BAR_CSS
        assert ".status-tokens" in STATUS_BAR_CSS
        assert ".status-mode-toggle" in STATUS_BAR_CSS
        assert "#status-model Select" in STATUS_BAR_CSS

    def test_input_area_contains_user_input(self):
        from tui.textual_app.css.input_area import INPUT_AREA_CSS
        assert "#input-area" in INPUT_AREA_CSS
        assert "#user-input" in INPUT_AREA_CSS
        assert ".input-field" in INPUT_AREA_CSS

    def test_slash_completion_contains_palette(self):
        from tui.textual_app.css.slash_completion import SLASH_COMPLETION_CSS
        assert "#slash-completion" in SLASH_COMPLETION_CSS
        assert ".visible" in SLASH_COMPLETION_CSS

    def test_sidebar_layout_contains_sidebar(self):
        from tui.textual_app.css.sidebar_layout import SIDEBAR_LAYOUT_CSS
        assert "#sidebar-container" in SIDEBAR_LAYOUT_CSS
        assert "#main-area" in SIDEBAR_LAYOUT_CSS
        assert "#log-output" in SIDEBAR_LAYOUT_CSS

    def test_transparency_contains_classes(self):
        from tui.textual_app.css.transparency import TRANSPARENCY_CSS
        assert ".transparent-panel" in TRANSPARENCY_CSS
        assert ".transparent-header" in TRANSPARENCY_CSS
        assert ".transparency-indicator" in TRANSPARENCY_CSS

    def test_custom_model_screen_css(self):
        from tui.textual_app.css.screens import CUSTOM_MODEL_SCREEN_CSS
        assert "CustomModelInputScreen" in CUSTOM_MODEL_SCREEN_CSS
        assert "#dialog" in CUSTOM_MODEL_SCREEN_CSS
        assert "#buttons" in CUSTOM_MODEL_SCREEN_CSS


class TestAPPCSSAgggregation:
    """APP_CSS 包含所有原始选择器。"""

    def test_app_css_contains_all_sections(self):
        from tui.textual_app.css import APP_CSS

        # 各域关键选择器必须出现在拼装结果中
        expected_selectors = [
            # base
            "Screen {",
            "MarkdownFence",
            # chat
            "#chat-area",
            "MessageList",
            ".streaming-indicator",
            # header
            "#app-header",
            "#welcome-banner",
            "#theme-toggle",
            # status bar
            "#status-bar",
            ".status-tokens",
            ".status-mode-toggle",
            "#status-model Select",
            # input area
            "#input-area",
            "#user-input",
            ".input-field",
            # slash completion
            "#slash-completion",
            # sidebar layout
            "#sidebar-container",
            "#main-area",
            "#log-output",
            # transparency
            ".transparent-panel",
            ".transparent-header",
            ".transparency-indicator",
        ]
        for selector in expected_selectors:
            assert selector in APP_CSS, f"APP_CSS missing: {selector}"

    def test_app_css_starts_with_header_comment(self):
        from tui.textual_app.css import APP_CSS

        assert APP_CSS.lstrip().startswith("/*"), (
            "APP_CSS should start with a comment block"
        )
        assert "Agent-Z TUI" in APP_CSS


class TestBackwardsCompat:
    """旧路径 `from .css import APP_CSS` 仍可用。"""

    def test_app_py_css_import_path(self):
        """app.py 的 `from .css import APP_CSS` 必须正常工作。"""
        # 不强制拉起整个 App，只验证 css 子包可导入
        from tui.textual_app import css as css_pkg

        assert hasattr(css_pkg, "APP_CSS")
        assert isinstance(css_pkg.APP_CSS, str)


class TestOldCSSModuleRemoved:
    """tui/textual_app/css.py 单文件已被子包取代。"""

    def test_no_old_css_py(self):
        """确认旧单文件已被删除（子包优先）。"""
        import pathlib

        old = pathlib.Path("tui/textual_app/css.py")
        assert not old.exists(), f"Old single file still exists: {old}"

    def test_css_subpackage_has_init(self):
        import pathlib

        init = pathlib.Path("tui/textual_app/css/__init__.py")
        assert init.exists()