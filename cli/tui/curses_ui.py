#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Curses UI Module - 重新导出自 cli.tui.core.curses_ui

🚪 Access - 💬 CLI - Curses UI 组件

此文件已迁移到 cli/tui/core/curses_ui.py，此文件提供向后兼容。

新代码请使用:
    from cli.tui.core.curses_ui import ...
"""

# 重新导出自新位置
from cli.tui.core.curses_ui import (
    flush_stdin,
    has_curses,
    curses_radiolist,
    curses_checklist,
    radio_select,
    multi_select,
)

__all__ = [
    "flush_stdin",
    "has_curses",
    "curses_radiolist",
    "curses_checklist",
    "radio_select",
    "multi_select",
]
