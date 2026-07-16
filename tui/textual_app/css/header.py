#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""应用顶部 Header 与欢迎横幅样式

🚪 Access - 💬 TUI - Textual App - CSS - Header

包含：
- #app-header：顶部横向 Header
- #welcome-banner / #header-info-right
- #version-info / #skills-info / #tools-info
- #theme-toggle：主题切换按钮
"""

from __future__ import annotations

HEADER_CSS = """
/* 自定义 Header - 模型信息显示 + 欢迎横幅 */
#app-header {
    height: 3;
    width: 100%;
    dock: top;
    background: $primary 20%;
    outline-bottom: solid $primary;
    layout: horizontal;
}

#welcome-banner {
    height: auto;
    width: auto;
    padding: 0 2;
    margin-right: 4;
    background: transparent;
}

#header-info-right {
    height: 3;
    width: 1fr;
    align: right middle;
}

#version-info,
#skills-info,
#tools-info {
    height: auto;
    width: 100%;
    padding: 0 2;
    background: transparent;
}

#theme-toggle {
    width: 5;
    height: 3;
    padding: 0 1;
    margin-left: 2;
    background: $accent;
    color: white;
    content-align: center middle;
}

#theme-toggle:hover {
    background: $primary;
}

#theme-toggle > .toggle--text {
    text-style: bold;
}
"""