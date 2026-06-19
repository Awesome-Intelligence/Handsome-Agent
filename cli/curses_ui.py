#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Curses UI Module - 重新导出自 tui.core.curses_ui

🚪 Access - 💬 CLI - Curses UI 组件

此文件已迁移到 tui/core/curses_ui.py，此文件提供向后兼容。
"""

# 重新导出自新位置
from tui.core.curses_ui import (
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