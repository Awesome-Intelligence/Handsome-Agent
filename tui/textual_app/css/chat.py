#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""聊天区域样式（#chat-area / MessageList）

🚪 Access - 💬 TUI - Textual App - CSS - 聊天区域

包含：
- #chat-area 主体滚动容器
- MessageList 消息列表
- 流式输出指示器
"""

from __future__ import annotations

CHAT_CSS = """
/* 聊天区域 */
#chat-area {
    height: 1fr;
    width: 1fr;
    background: transparent;
    margin: 0;
    padding: 0;
    border: blank;
    /* #chat-area 就是 ChatContainer(VerticalScroll) 本身，必须允许纵向滚动。
       原来的 overflow: hidden 会禁用它自身的滚动（无滚动条、鼠标滚轮失效）。 */
    overflow-x: hidden;
    overflow-y: auto;
}

/* MessageList (VerticalScroll) 样式 */
#chat-area MessageList {
    width: 100%;
    height: 100%;
    overflow-x: hidden;
    overflow-y: auto;
    border: blank;
    padding: 1 2;
    background: transparent;
}

/* 流式输出指示器 - Textual CSS 不支持动画，使用静态样式 */
.streaming-indicator {
    color: #8b949e;
}
"""