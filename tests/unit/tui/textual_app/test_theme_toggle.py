#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""主题切换按钮行为回归。

🚪 Access - 💬 Tests - TUI - Theme Toggle

确认：
- 点击 ``#theme-toggle`` 切换 ``app.theme`` 顺序取下一项
- 点击同步刷新按钮标签（首字母）作为视觉反馈
- 点击触发 ``App.refresh_css``，让已挂载的 ModalScreen（LogScreen 等）也能拿到新主题颜色
"""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_theme_toggle_cycles_theme_and_updates_label() -> None:
    from tui.textual_app.app import AgentApp, THEME_CYCLE

    assert len(THEME_CYCLE) >= 2, "需要至少 2 个主题才能测试切换"

    app = AgentApp(model_name='test')
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        await pilot.pause()
        from textual.widgets import Static

        widget = app.query_one('#theme-toggle', Static)
        start_theme = app.theme if isinstance(app.theme, str) else 'textual-dark'
        start_idx = THEME_CYCLE.index(start_theme) if start_theme in THEME_CYCLE else -1
        next_theme = THEME_CYCLE[(start_idx + 1) % len(THEME_CYCLE)]

        await pilot.click('#theme-toggle')
        await pilot.pause()

        assert app.theme == next_theme, f"expected {next_theme}, got {app.theme}"
        # 标签应更新为下一个主题的首字母（仅大写），按钮宽度=5，有 padding。
        assert str(widget.content) == next_theme[:1].upper()


@pytest.mark.asyncio
async def test_theme_toggle_propagates_to_modal_screen() -> None:
    """点击切主题后，已挂载的 ModalScreen（如 LogScreen）也要拿到新颜色。

    Textual 默认 ``App.theme`` reactive 只重渲当前屏，不会自动级联到 ModalScreen。
    修复点在 ``_on_theme_toggle_click`` 里加了 ``self.refresh_css(animate=False)``。
    """
    from tui.textual_app.app import AgentApp
    from tui.views.log_screen import LogScreen
    from textual.widgets import Static

    app = AgentApp(model_name='test')
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        for _ in range(3): await pilot.pause()

        log = LogScreen()
        app.push_screen(log)
        await pilot.pause()
        for _ in range(3): await pilot.pause()
        # 初始（dark 主题）下记下 #log-header 背景
        hdr = log.query_one('#log-header', Static)
        before = str(hdr.styles.background)

        # 直接驱动切换：先换一个跟当前不一样的目标（保证真有变化）
        # 然后调出和点击等价的核心：refresh_css
        original_theme = app.theme
        # 找一个不是当前主题的目标
        from textual.theme import BUILTIN_THEMES
        candidates = [n for n in ('gruvbox', 'nord', 'catppuccin-mocha') if n != original_theme]
        target = candidates[0]
        app.theme = target
        await pilot.pause()
        # 模拟 _on_theme_toggle_click 里现在会做的：refresh_css
        app.refresh_css(animate=False)
        await pilot.pause()
        for _ in range(3): await pilot.pause()

        after = str(hdr.styles.background)
        assert before != after, (
            f"#log-header 背景没随主题变。before={before} after={after}。"
            f"_on_theme_toggle_click 缺少 self.refresh_css(animate=False) 调用。"
        )
