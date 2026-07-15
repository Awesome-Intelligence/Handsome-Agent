#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Modal/Dialog Screen 的内嵌 CSS（CustomModelInputScreen）

🚪 Access - 💬 TUI - Textual App - CSS - Screens

包含 ``CustomModelInputScreen``（自定义模型输入弹窗）的 CSS，
原先内嵌在 app.py L2665–2693 中，现统一收纳到 css 子包。
"""

from __future__ import annotations

CUSTOM_MODEL_SCREEN_CSS = """
CustomModelInputScreen {
    align: center middle;
}

#dialog {
    width: 50;
    height: auto;
    border: solid $primary;
    background: $surface;
    padding: 1 2;
}

#title {
    text-align: center;
    text-style: bold;
    color: $primary;
    margin-bottom: 1;
}

#input-container {
    margin: 1 0;
}

#buttons {
    height: auto;
    align: center;
}
"""