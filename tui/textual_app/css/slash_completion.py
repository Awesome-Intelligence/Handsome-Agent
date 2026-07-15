#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""斜杠命令补全浮层样式（#slash-completion）

🚪 Access - 💬 TUI - Textual App - CSS - 斜杠补全

Ctrl+/ 触发的命令补全浮层样式。
"""

from __future__ import annotations

SLASH_COMPLETION_CSS = """
/* === 斜杠命令补全浮层 === */
#slash-completion {
    display: none;
    height: auto;
    max-height: 5;
    background: $surface;
    border: solid $accent;
    padding: 0 1;
    width: 60%;
}

#slash-completion.visible {
    display: block;
}

#slash-completion > ListItem {
    padding: 0 1;
}

#slash-completion > ListItem:hover,
#slash-completion > ListItem.selected {
    background: $primary 20%;
}
"""