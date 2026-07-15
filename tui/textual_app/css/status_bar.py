#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""底部状态栏样式（#status-bar / status-* / Select 控件）

🚪 Access - 💬 TUI - Textual App - CSS - 状态栏

包含：
- #status-bar / #status-content / #status-right
- 状态图标、模型、token、queue、progress、time、tools、mode-toggle
- #status-model Select 控件的紧凑样式
"""

from __future__ import annotations

STATUS_BAR_CSS = """
/* === 状态栏样式 === */
#status-bar {
    height: 1;
    width: 100%;
    background: $primary;
    padding: 0;
    margin: 0;
    outline: thick solid $secondary;
}

#status-content {
    height: 100%;
    layout: horizontal;
    padding: 0 0;
    align: left middle;
    color: $foreground;
}

.status-icon {
    width: auto;
    margin-right: 2;
}

.status-model {
    width: 22;
    max-width: 22;
    height: 1;
    margin-right: 2;
    background: $surface;
    color: $foreground;
    text-style: bold;
}

/* Select widget in status bar - compact mode */
#status-model Select {
    height: 1;
    width: 100%;
}

#status-model Select.-textual-compact {
    border: none;
    background: transparent;
}

#status-model Select.-textual-compact > SelectCurrent {
    border: none;
    background: transparent;
    padding: 0 1 0 0;
}

#status-model Select.-textual-compact > SelectCurrent > Static#label {
    color: $foreground;
    width: auto;
}

#status-model Select > SelectOverlay {
    overlay: screen;
    constrain: none inside;
}

.status-tokens {
    width: auto;
    margin-right: 2;
    color: $foreground;
}

.status-queue {
    width: auto;
    margin-right: 2;
    color: $warning;
    display: none;
}

.status-queue.has-queue {
    display: block;
}

#status-progress {
    width: 15;
    margin-right: 2;
}

.status-time {
    width: auto;
    margin-right: 2;
    color: $foreground;
}

.status-tools {
    width: auto;
    color: $accent;
    margin-right: 1;
}

.status-mode-toggle {
    width: auto;
    color: $foreground;
    padding: 0 1;
    min-width: 2;
}

.status-mode-toggle:hover {
    color: $accent;
    background: $surface;
    border: none;
}

#status-right {
    width: 1fr;
    layout: horizontal;
    align: right middle;
}

.status-mode-toggle:focus {
    border: none;
}
"""