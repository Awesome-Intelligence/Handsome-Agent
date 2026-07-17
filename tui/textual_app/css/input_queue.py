#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""输入队列悬浮面板样式（#input-queue-panel / .queue-item 等）

🚪 Access - 💬 TUI - Textual App - CSS - 输入队列面板

包含：
- #input-queue-panel 悬浮容器（overlay + dock:bottom）
- #queue-list ListView 列表容器
- .queue-item / .queue-index / .queue-content / .queue-delete 单个队列项
- .queue-footer / .queue-count / .queue-clear 底部操作栏
"""

from __future__ import annotations

INPUT_QUEUE_CSS = """
/* === 输入队列悬浮面板 === */

/* 悬浮面板容器：overlay 叠加 + 底部停靠，无边框无标题 */
#input-queue-panel {
    display: none;
    overlay: screen;
    dock: bottom;
    width: 100%;
    height: auto;
    max-height: 8;
    background: $surface;
    border: none;
    padding: 0;
    margin: 0;
    margin-bottom: 9;
}

#input-queue-panel.has-queue {
    display: block;
}

/* ListView 列表容器：height:auto 使面板高度根据内容项数量自适应（最低 2 行 = 1 条数据 + 1 个底部操作栏） */
#input-queue-panel > #queue-list {
    height: auto;
    width: 100%;
    background: transparent;
    border: none;
    padding: 0;
    margin: 0;
}

/* ListItem 基础样式（覆盖 Textual 默认边框） */
#queue-list > ListItem {
    background: transparent;
    border: none;
    padding: 0;
    margin: 0;
    height: 1;
}

/* 单个队列项 */
.queue-item {
    layout: horizontal;
    align: left middle;
    padding: 0 2;
    height: 1;
    background: transparent;
    border: none;
}

.queue-item:hover {
    background: $primary 20%;
}

.queue-item .queue-item-row {
    layout: horizontal;
    align: left middle;
    height: 100%;
    width: 100%;
}

/* 内容预览列（无序号，直接从左侧开始显示） */
.queue-item .queue-content {
    width: 1fr;
    color: $foreground;
    height: 100%;
    content-align: left middle;
}

/* 删除按钮 × */
.queue-item .queue-delete {
    width: 3;
    color: $error;
    text-align: right;
    height: 100%;
    content-align: right middle;
}

.queue-item .queue-delete:hover {
    color: $error;
    text-style: bold;
    background: $error 10%;
}
"""
