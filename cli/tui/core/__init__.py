#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Core Module - TUI 基础设施模块

🚪 Access - 💬 CLI - TUI - Core

包含 TUI 的核心基础设施组件：
- keybindings: 快捷键映射系统
- markdown_renderer: Markdown 渲染器
- curses_ui: Curses UI 组件
"""

from __future__ import annotations

# 导出快捷键模块
from cli.tui.core.keybindings import (
    KeyBinding,
    KeyBindingGroup,
    KeyBindingManager,
    KeyBindingCategory,
    create_default_keybindings,
)

# 导出 Markdown 渲染模块
from cli.tui.core.markdown_renderer import (
    MarkdownRenderer,
    HandsomeAgentRenderer,
    HandsomeAgentMarkdown,
    RichFormatter,
    markdown_to_rich,
    is_markdown_available,
    get_markdown_features,
    MISTUNE_AVAILABLE,
    PYGMENTS_AVAILABLE,
)

# 导出 Curses UI 模块
from cli.tui.core.curses_ui import (
    has_curses,
    flush_stdin,
    curses_radiolist,
    curses_checklist,
    radio_select,
    multi_select,
    IS_WINDOWS,
    IS_TTY,
)

__all__ = [
    # keybindings
    "KeyBinding",
    "KeyBindingGroup",
    "KeyBindingManager",
    "KeyBindingCategory",
    "create_default_keybindings",
    # markdown_renderer
    "MarkdownRenderer",
    "HandsomeAgentRenderer",
    "HandsomeAgentMarkdown",
    "RichFormatter",
    "markdown_to_rich",
    "is_markdown_available",
    "get_markdown_features",
    "MISTUNE_AVAILABLE",
    "PYGMENTS_AVAILABLE",
    # curses_ui
    "has_curses",
    "flush_stdin",
    "curses_radiolist",
    "curses_checklist",
    "radio_select",
    "multi_select",
    "IS_WINDOWS",
    "IS_TTY",
]
