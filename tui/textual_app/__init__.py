#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Textual TUI Application Module

🚪 Access - 💬 CLI - Textual UI

导出主应用类和基础设施组件。
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# 向后兼容：暴露公共 API
# ---------------------------------------------------------------------------
#
# 注意：原代码使用 ``from .app import (AgentApp, run_textual_app, ...)``
# 这种**显式列表**形式在 v8.x 重构后容易因依赖顺序问题失败（若 app.py 顶部
# import 任一子模块出错，整个 from-import 块会被 Python 静默回滚）。
# 改用 ``import`` + 显式 ``__getattr__`` 风格，**鲁棒**地暴露所有公共符号。

from . import app as _app_module
from . import css as _css_module
from . import log_handler as _log_handler_module
from . import notifications as _notifications_module
from . import text_area as _text_area_module

# 主应用类 & 启动函数（来自 app.py）
AgentApp = _app_module.AgentApp
run_textual_app = _app_module.run_textual_app
check_textual_available = _app_module.check_textual_available
get_textual_import_error = _app_module.get_textual_import_error
get_textual_install_hint = _app_module.get_textual_install_hint
is_textual_compatible = _app_module.is_textual_compatible
create_fallback_app = _app_module.create_fallback_app
TEXTUAL_AVAILABLE = _app_module.TEXTUAL_AVAILABLE

# CSS 拼装
APP_CSS = _css_module.APP_CSS

# 日志处理
TuiLogHandler = _log_handler_module.TuiLogHandler

# 通知系统
NotificationAnimationManager = _notifications_module.NotificationAnimationManager
NotificationType = _notifications_module.NotificationType

# 文本区域
SubmitTextArea = _text_area_module.SubmitTextArea

# 主题颜色常量
PURPLE_PRIMARY = _app_module.PURPLE_PRIMARY
PURPLE_BRIGHT = _app_module.PURPLE_BRIGHT
PURPLE_DIM = _app_module.PURPLE_DIM
PURPLE_DARK = _app_module.PURPLE_DARK

__all__ = [
    # 主应用类
    "AgentApp",
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
