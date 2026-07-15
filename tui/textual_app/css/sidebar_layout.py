#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""侧边栏与主区域布局样式（#sidebar-container / #log-output / #main-area）

🚪 Access - 💬 TUI - Textual App - CSS - 侧边栏布局

包含：
- #sidebar-container 左侧面板
- #log-output 日志屏幕
- #main-area 主区域布局
"""

from __future__ import annotations

SIDEBAR_LAYOUT_CSS = """
/* === 侧边栏样式 === */
#sidebar-container {
    width: 50;
    height: 100%;
    background: transparent;
    border: blank;
    margin: 0;
    padding: 0;
}

#log-output {
    height: 100%;
    background: $background;
    color: #8b949e;
}

/* === 主区域布局 === */
#main-area {
    height: 1fr;
    width: 100%;
    margin: 0;
    padding: 0;
}
"""