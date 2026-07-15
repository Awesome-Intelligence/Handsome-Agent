#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全局基础样式（Screen / 整体重置 / 字体）

🚪 Access - 💬 TUI - Textual App - CSS - 基础

提供 Screen 全屏样式、字体定义、MarkdownFence 高度限制等。
"""

from __future__ import annotations

BASE_CSS = """
/* ========== 整体样式 ========== */

Screen {
    background: $background;
    margin: 0;
    padding: 0;
}

/* ponytail: 限制代码块高度，防止长代码撑爆布局 (oterm 做法) */
MarkdownFence {
    max-height: 50;
}
"""