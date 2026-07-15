#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""毛玻璃（半透明）样式 — CSS class 占位说明

🚪 Access - 💬 TUI - Textual App - CSS - 透明度

本模块的 ``TRANSPARENCY_CSS`` 仅作为**默认值**（透明度未启用时的样式参考）。
运行时透明度 CSS 由 ``common.theming.styles.transparency.generate_transparent_css``
根据当前透明度级别动态生成，并通过 ``app.styling._update_transparency_styles``
的 ``add_stylesheet`` 注入，**单一来源原则**。

提供静态样式的好处：
- 即使 ThemeManager 初始化失败，class 名仍可用，不会崩溃
- 文档化本 App 支持的所有半透明 class
"""

from __future__ import annotations

TRANSPARENCY_CSS = """
/* ============================================================================
   半透明背景样式 (Frosted Glass Effect) — 默认值
   运行时实际值由 common.theming.styles.transparency 动态注入
   支持 Ctrl+Shift+B 快捷键切换
   ============================================================================ */

/* 半透明面板 - 毛玻璃效果 */
.transparent-panel {
    background: rgba(13, 17, 23, 0.75);
    border: solid rgba(48, 54, 61, 0.5);
}

/* 半透明标题栏 */
.transparent-header {
    background: rgba(22, 27, 34, 0.80);
}

/* 半透明状态栏 */
.transparent-status-bar {
    background: rgba(33, 38, 45, 0.80);
}

/* 半透明页脚 */
.transparent-footer {
    background: rgba(33, 38, 45, 0.85);
}

/* 半透明侧边栏 */
.transparent-sidebar {
    background: rgba(22, 27, 34, 0.75);
    border-left: solid rgba(48, 54, 61, 0.5);
}

/* 半透明聊天区域 */
.transparent-chat {
    background: transparent;
}

/* 半透明输入框 */
.transparent-input {
    background: rgba(13, 17, 23, 0.60);
    border: blank;
}

.transparent-input:focus {
    border: heavy rgba(88, 166, 255, 0.8);
}

/* 半透明欢迎横幅 */
.transparent-welcome {
    background: rgba(22, 27, 34, 0.65);
    border-bottom: solid rgba(48, 54, 61, 0.4);
}

/* 透明度切换指示器 */
.transparency-indicator {
    color: $accent;
    text-style: bold;
}
"""