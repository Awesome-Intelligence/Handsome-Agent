#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Textual TUI Application Module - Handsome Agent

🚪 Access - 💬 CLI - Textual UI

导出主应用类和基础设施组件。
"""

from __future__ import annotations

# 向后兼容：允许从旧路径导入
from .app import (
    # 主应用类
    HandsomeAgentApp,
    # 启动函数
    run_textual_app,
    check_textual_available,
    get_textual_import_error,
    get_textual_install_hint,
    is_textual_compatible,
    create_fallback_app,
    TEXTUAL_AVAILABLE,
)
from .css import APP_CSS
from .log_handler import TuiLogHandler
from .notifications import NotificationAnimationManager, NotificationType
from .text_area import SubmitTextArea

# 主题颜色常量
from .app import (
    PURPLE_PRIMARY,
    PURPLE_BRIGHT,
    PURPLE_DIM,
    PURPLE_DARK,
)

__all__ = [
    # 主应用类
    "HandsomeAgentApp",
    # 启动函数
    "run_textual_app",
    "check_textual_available",
    "get_textual_import_error",
    "get_textual_install_hint",
    "is_textual_compatible",
    "create_fallback_app",
    # 可用性标志
    "TEXTUAL_AVAILABLE",
    # CSS
    "APP_CSS",
    # 日志处理
    "TuiLogHandler",
    # 通知系统
    "NotificationAnimationManager",
    "NotificationType",
    # 文本区域
    "SubmitTextArea",
    # 主题颜色
    "PURPLE_PRIMARY",
    "PURPLE_BRIGHT",
    "PURPLE_DIM",
    "PURPLE_DARK",
]
