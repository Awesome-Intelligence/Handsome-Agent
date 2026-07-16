#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Agent-Z TUI 样式系统（模块化子包）

🚪 Access - 💬 TUI - Textual App - CSS 聚合入口

v8.x 重构：
原 ``tui/textual_app/css.py`` 单文件（407 行）已拆为以下职责单一子模块，
本模块负责按加载顺序拼装为单一 ``APP_CSS`` 字符串。

子模块：
- base           全局基础（Screen / MarkdownFence）
- chat           聊天区域（#chat-area / MessageList）
- header         顶部 Header（#app-header / welcome-banner / theme-toggle）
- status_bar     底部状态栏
- input_area     输入区（#input-area / #user-input）
- slash_completion  斜杠补全浮层
- sidebar_layout 侧边栏与主区域布局
- transparency   毛玻璃样式（静态默认 + 运行时由 common.theming.styles 动态注入）
- screens        Modal/Dialog Screen 的内嵌 CSS（CustomModelInputScreen）
"""

from __future__ import annotations

from .base import BASE_CSS
from .chat import CHAT_CSS
from .header import HEADER_CSS
from .status_bar import STATUS_BAR_CSS
from .input_area import INPUT_AREA_CSS
from .slash_completion import SLASH_COMPLETION_CSS
from .sidebar_layout import SIDEBAR_LAYOUT_CSS
from .transparency import TRANSPARENCY_CSS
from .screens import CUSTOM_MODEL_SCREEN_CSS


# ============================================================================
# APP_CSS — 所有静态 CSS 拼装后的单一字符串
# ============================================================================

APP_CSS = f"""
/*
 * Agent-Z TUI 主样式表（v8.x 模块化拼装版）
 *
 * CSS 架构说明：
 * - 使用 Textual Theme 变量实现主题切换
 * - 主题颜色在 app.py 的 THEMES 中定义
 * - CSS 中使用 $变量名 引用主题颜色
 *
 * 可用变量：
 * - $primary: 主强调色
 * - $secondary: 次强调色
 * - $accent: 强调色
 * - $background: 背景色
 * - $surface: 表面色
 * - $foreground: 前景/文字色
 * - $success: 成功色
 * - $warning: 警告色
 * - $error: 错误色
 */

{BASE_CSS}

{CHAT_CSS}

{HEADER_CSS}

{STATUS_BAR_CSS}

{INPUT_AREA_CSS}

{SLASH_COMPLETION_CSS}

{SIDEBAR_LAYOUT_CSS}

{TRANSPARENCY_CSS}
"""


__all__ = [
    "APP_CSS",
    "BASE_CSS",
    "CHAT_CSS",
    "HEADER_CSS",
    "STATUS_BAR_CSS",
    "INPUT_AREA_CSS",
    "SLASH_COMPLETION_CSS",
    "SIDEBAR_LAYOUT_CSS",
    "TRANSPARENCY_CSS",
    "CUSTOM_MODEL_SCREEN_CSS",
]