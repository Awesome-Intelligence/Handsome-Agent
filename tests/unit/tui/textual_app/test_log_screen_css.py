#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LogScreen CSS theme-awareness regressions.

🚪 Access - 💬 Tests - TUI - LogScreen CSS

LogScreen used to use ``$boost`` (Textual built-in; in this version it
resolves to a constant white-alpha tint that does NOT change per-theme) and
``$text`` / ``$text-muted`` (not defined by Textual's built-in themes).
Both made the popup background and text appear identical regardless of theme.

Verify the popup now uses real theme variables on every background and color.
"""

from __future__ import annotations

import re


def _get_log_screen_css():
    # ponytail: 避免启动 textual；直接抓 View 源码里的 CSS。
    import tui.views.log_screen as ls

    src = open(ls.__file__, encoding="utf-8").read()
    m = re.search(r'CSS\s*=\s*"""(.*?)"""', src, re.DOTALL)
    assert m is not None, "LogScreen 没有找到 CSS 字符串"
    return m.group(1)


def test_log_screen_uses_theme_background_variables() -> None:
    """背景不能是 $boost（内置是常量白，不会跟主题）。"""
    css = _get_log_screen_css()
    # ponytail: $boost 仍然可用作 micro-contrast，但 LogScreen 外层必须是可切主题的值。
    assert "background: $boost" not in css, (
        "LogScreen 用了 $boost 作为背景；该变量在 Textual 当前版本是常量白-alpha，"
        "切主题不会变。改用 $primary/$surface 等主题变量。"
    )


def test_log_screen_avoids_undefined_text_variables() -> None:
    """禁用 $text / $text-muted（不是 Textual 官方主题变量，会回退到常量）。

    改用 $foreground；半透明写法 ``$foreground 70%`` 也合法。
    """
    import re

    css = _get_log_screen_css()
    # 剥离注释再扫，避免 ``/* ... $text-muted ... */`` 命中。
    no_comments = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    # 直接写 ``color: $text;`` 视为回归；允许 ``color: $foreground`` / `$foreground N%` / `$foreground-muted`。
    bad_bare = re.findall(r"color:\s*\$text\b(?!\-)", no_comments)
    assert not bad_bare, (
        "LogScreen 用了未定义的 $text 作为 color；改用 $foreground。"
    )
    bad_muted = re.findall(r"color:\s*\$text-muted", no_comments)
    assert not bad_muted, (
        "LogScreen 用了未定义的 $text-muted 作为 color；改用 $foreground 70% 等。"
    )
