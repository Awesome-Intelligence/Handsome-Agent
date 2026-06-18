#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Textual TUI Application - Handsome Agent

🚪 Access - 💬 CLI - Textual UI 组件

本模块已重构为子包 cli/tui/textual_app/
此文件保留用于向后兼容。

新代码请使用:
    from cli.tui.textual_app import HandsomeAgentApp
"""

# 向后兼容：从子包重新导出所有内容
from cli.tui.textual_app import (
    # 主应用类
    HandsomeAgentApp,
    # CSS
    APP_CSS,
    # 日志处理
    TuiLogHandler,
    # 通知系统
    NotificationAnimationManager,
    NotificationType,
    # 文本区域
    SubmitTextArea,
    # 启动函数
    run_textual_app,
    check_textual_available,
    get_textual_import_error,
    get_textual_install_hint,
    is_textual_compatible,
    create_fallback_app,
    TEXTUAL_AVAILABLE,
    # 主题颜色
    AVOCADO_PRIMARY,
    AVOCADO_BRIGHT,
    AVOCADO_DIM,
    AVOCADO_DARK,
)

# 为了保持完整的向后兼容，也导入主题系统和通知系统
try:
    from cli.tui.themes import (
        ThemeManager,
        get_theme_manager,
    )
except ImportError:
    ThemeManager = None
    get_theme_manager = None

__all__ = [
    # 主应用类
    "HandsomeAgentApp",
    "run_textual_app",
    "check_textual_available",
    "get_textual_import_error",
    "get_textual_install_hint",
    "is_textual_compatible",
    "create_fallback_app",
    "TEXTUAL_AVAILABLE",
    # 主题颜色
    "AVOCADO_PRIMARY",
    "AVOCADO_BRIGHT",
    "AVOCADO_DIM",
    "AVOCADO_DARK",
    "WHITE",
    "GRAY_DIM",
    "GOLD",
    # 主题系统
    "ThemeManager",
    "get_theme_manager",
    # 通知动画系统
    "NotificationType",
    "NotificationAnimationManager",
    # Markdown 渲染系统
    "MarkdownRenderer",
    "markdown_to_rich",
    "is_markdown_available",
    # CSS
    "APP_CSS",
    # 日志处理
    "TuiLogHandler",
    # 文本区域
    "SubmitTextArea",
]
