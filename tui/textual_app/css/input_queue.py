#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""输入队列悬浮面板样式（#input-queue-panel / .queue-item 等）

🚪 Access - 💬 TUI - Textual App - CSS - 输入队列面板

包含：
- #input-queue-panel          悬浮容器（overlay + dock: bottom）
- #input-queue-actions        顶部操作栏（计数 + 清空按钮）
- #input-queue-count          左：⏳ N 条排队计数
- #input-queue-clear-all      右：🗑️ 清空按钮
- #input-queue-list           列表容器（Vertical，height: 1fr，max-height: 30vh）
- .queue-item                 单个队列项（Horizontal，首项带 .first）
- .queue-index                序号列（首项显示 ▶ 1）
- .queue-content              内容预览列
- .queue-delete-btn           删除按钮 ×
"""

from __future__ import annotations

INPUT_QUEUE_CSS = """
/* === 输入队列悬浮面板 === */

/* 悬浮面板容器：overlay 叠加 + 底部停靠，无边框无标题 */
#input-queue-panel {
    display: none;
    overlay: screen;
    dock: bottom;
    layout: vertical;
    width: 100%;
    height: auto;
    max-height: 30vh;
    background: $surface;
    border: none;
    padding: 0;
    margin: 0;
    margin-bottom: 9;
}

/* 可见状态（使用 .visible class，不是 .has-queue） */
#input-queue-panel.visible {
    display: block;
}

/* 顶部操作栏：左计数 + 右清空 */
#input-queue-actions {
    layout: horizontal;
    height: 1;
    width: 100%;
    padding: 0 1;
    background: $surface;
}

#input-queue-count {
    width: 1fr;
    height: 100%;
    color: $secondary;
    content-align: left middle;
}

#input-queue-clear-all {
    width: auto;
    height: 100%;
    color: $error;
    content-align: right middle;
    padding: 0 1;
}

#input-queue-clear-all:hover {
    background: $error 15%;
}

/* 列表容器：height:1fr 撑开（C3-6 要求），可滚动 */
#input-queue-list {
    layout: vertical;
    height: 1fr;
    width: 100%;
    background: transparent;
    border: none;
    padding: 0;
    margin: 0;
    overflow-y: auto;
}

/* 单个队列项基础样式 */
.queue-item {
    layout: horizontal;
    align: left middle;
    padding: 0 1;
    height: auto;
    max-height: 3;
    background: transparent;
    border: none;
}

.queue-item:hover {
    background: $primary 15%;
}

/* 队首高亮：▶ 符号 + 背景高亮 */
.queue-item.first {
    background: $primary 20%;
}

/* 序号列：首项显示 ▶ 1，其他显示 "  N " */
.queue-index {
    width: 4;
    height: 100%;
    color: $secondary;
    content-align: right middle;
}

.queue-item.first .queue-index {
    color: $primary;
}

/* 内容预览列 */
.queue-content {
    width: 1fr;
    height: auto;
    max-height: 3;
    color: $foreground;
    content-align: left middle;
    padding: 0 1;
}

/* 删除按钮 × */
.queue-delete-btn {
    width: 4;
    height: 100%;
    color: $error;
    content-align: right middle;
    padding: 0 1;
}

.queue-delete-btn:hover {
    background: $error 15%;
    color: $error;
}
"""
