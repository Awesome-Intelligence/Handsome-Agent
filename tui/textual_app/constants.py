#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Agent-Z TUI 颜色与状态常量

🚪 Access - 💬 TUI - Textual App - 常量

原 ``app.py`` L199–209 的 ``PURPLE_*`` / ``STATUS_*`` 常量迁移至此。

注意：与 ``tui.theming`` 内的同名常量并存（兼容层）。
此处常量用于 Rich 文本内嵌颜色标记，
``tui.theming`` 常量用于 CSS 主题系统。
"""

from __future__ import annotations


# ============================================================================
# 颜色常量（用于横幅等 Rich 标记）
# ============================================================================

PURPLE_PRIMARY = "#B180D7"
PURPLE_BRIGHT = "#C9A0E0"
PURPLE_DIM = "#9A6BC2"
PURPLE_DARK = "#7A4DA8"
WHITE = "white"
GRAY_DIM = "#888888"
GOLD = "#FFD700"


# ============================================================================
# 状态色（agent 状态指示）
# ============================================================================

STATUS_ONLINE = "#3fb950"
STATUS_BUSY = "#f0883e"
STATUS_ERROR = "#f85149"


__all__ = [
    "PURPLE_PRIMARY",
    "PURPLE_BRIGHT",
    "PURPLE_DIM",
    "PURPLE_DARK",
    "WHITE",
    "GRAY_DIM",
    "GOLD",
    "STATUS_ONLINE",
    "STATUS_BUSY",
    "STATUS_ERROR",
]