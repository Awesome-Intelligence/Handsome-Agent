#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""输入区样式（#input-area / #user-input / .input-field）

🚪 Access - 💬 TUI - Textual App - CSS - 输入区

包含：
- #input-area 底部 dock
- #user-input TextArea 输入控件
- .input-field 通用字段样式
- #input-area 内嵌状态条
"""

from __future__ import annotations

INPUT_AREA_CSS = """
/* 输入区域样式 */
#input-area {
    height: auto;
    width: 100%;
    dock: bottom;
    layout: vertical;
    padding: 0;
    margin: 0;
    border: none;
    background: $primary 20%;
}

#input-area #status-content {
    height: 100%;
    layout: horizontal;
    padding: 0 2;
    align: left bottom;
    color: $background;
}

#input-area #user-input {
    margin: 0;
    margin-top: 0;
}

#input-area Footer {
    dock: none;
    height: 1;
    background: $primary 40%;
}

.input-field {
    border: blank;
    background: $surface;
    color: $foreground;
    padding: 0;
    height: 100%;
    width: 1fr;
}

.input-field:focus {
    border: heavy $accent;
}

#user-input {
    background: transparent;
    color: $foreground;
    margin: 0;
    height: 7;
    padding: 0;
    border: blank;
}

#user-input:focus,
#user-input:hover {
    border: blank;
}
"""