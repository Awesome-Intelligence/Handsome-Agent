#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SessionPickerScreen CSS theme-awareness regressions.

🚪 Access - 💬 Tests - TUI - Session Picker CSS

The picker used to hardcode AVOCADO_* colors for 3 backgrounds, so pop-up
background, cursor and highlight stayed purple regardless of active theme.
Verify each one is now a theme variable so they follow the theme switch.
"""

from __future__ import annotations

import re

from tui.views.session_picker import SESSION_PICKER_CSS


# ponytail: 单文件 3 个背景断言，正则匹配 selection 块并核对 background 字段。


def _background_of(selector: str) -> str | None:
    """从 CSS 字符串里抓取 ``<selector> { ... background: VAL; ... }`` 的背景值。"""
    pattern = re.compile(
        rf"{re.escape(selector)}\s*\{{([^}}]*)",
        re.DOTALL,
    )
    m = pattern.search(SESSION_PICKER_CSS)
    if not m:
        return None
    body = m.group(1)
    bg_match = re.search(r"background:\s*([^;]+);", body)
    return bg_match.group(1).strip() if bg_match else None


def test_session_picker_screen_uses_theme_background() -> None:
    """SessionPickerScreen 自身背景必须是 $xxx 主题变量。"""
    value = _background_of("SessionPickerScreen")
    assert value is not None, "SessionPickerScreen 缺少 background 声明"
    assert value.startswith("$"), (
        f"SessionPickerScreen 背景硬编码为 {value!r}，切主题不会跟随。"
        "请改用 $primary/$surface 等主题变量。"
    )


def test_datatable_cursor_uses_theme_background() -> None:
    """#session-table 选中行高亮背景跟随主题。"""
    value = _background_of("#session-table .datatable--cursor")
    assert value is not None, "datatable--cursor 缺少 background 声明"
    assert value.startswith("$"), (
        f"datatable--cursor 背景硬编码为 {value!r}，切主题不会跟随。"
    )


def test_highlight_cursor_uses_theme_background() -> None:
    """:highlight_cursor 行底色跟随主题。"""
    value = _background_of("#session-table :highlight_cursor")
    assert value is not None, ":highlight_cursor 缺少 background 声明"
    assert value.startswith("$"), (
        f":highlight_cursor 背景硬编码为 {value!r}，切主题不会跟随。"
    )
