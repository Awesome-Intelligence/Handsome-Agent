#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TUI (Terminal User Interface) - 终端界面渲染层

🚪 Access - 💬 CLI - TUI 渲染层

提供 curses 和其他 TUI 组件，用于构建交互式终端界面。

模块：
- curses_ui: 跨平台 curses UI 组件
- textual_app: Textual 框架 TUI 应用
- rich_panel: Rich 库面板组件
- theme_engine: 主题引擎
- layout_manager: 布局管理器
- widgets: Textual UI 组件库
- keybindings: 快捷键绑定系统
"""

# 立即 patch Textual 的 LayerLogger 以修复 Textual 8.x 兼容性问题
# 这个 patch 必须在任何 Textual 代码导入之前执行
def _patch_textual_logger_early():
    """Early patch for Textual's LayerLogger."""
    try:
        from textual._log import LayerLogger
        LayerLogger.system = lambda *args, **kwargs: None
        LayerLogger.info = lambda *args, **kwargs: None
        LayerLogger.debug = lambda *args, **kwargs: None
        LayerLogger.warning = lambda *args, **kwargs: None
        LayerLogger.error = lambda *args, **kwargs: None
        LayerLogger.critical = lambda *args, **kwargs: None
    except ImportError:
        pass

_patch_textual_logger_early()

from .curses_ui import (
    has_curses,
    curses_radiolist,
    curses_checklist,
    radio_select,
    multi_select,
    flush_stdin,
)

# Textual TUI 支持（可选）
from .textual_app import (
    TEXTUAL_AVAILABLE,
    HandsomeAgentApp,
    run_textual_app,
    check_textual_available,
    get_textual_import_error,
    get_textual_install_hint,
    is_textual_compatible,
    # 主题颜色（用于横幅等 Rich 标记）
    AVOCADO_PRIMARY,
    AVOCADO_BRIGHT,
    AVOCADO_DIM,
    AVOCADO_DARK,
)

# 主题系统
from .themes import Theme, ThemeManager, get_theme_manager

# Textual UI 组件
from .widgets import StatusBar, CommandPaletteScreen, Command

# Textual UI Views
from .views import ChatView, ChatMessageSubmitted, HelpScreen

# 快捷键管理
from .keybindings import (
    KeyBinding,
    KeyBindingManager,
    KeyBindingCategory,
    create_default_keybindings,
)

# 审批对话框组件
from .widgets import (
    ApprovalDialog,
    ApprovalMode,
    RiskLevel,
    SENSITIVE_OPERATIONS,
    ApprovalManager,
    ApprovalConfirmed,
    ApprovalRejected,
    create_approval_dialog,
)

__all__ = [
    # Curses UI
    "has_curses",
    "curses_radiolist",
    "curses_checklist",
    "radio_select",
    "multi_select",
    "flush_stdin",
    # Textual UI
    "TEXTUAL_AVAILABLE",
    "HandsomeAgentApp",
    "run_textual_app",
    "check_textual_available",
    "get_textual_import_error",
    "get_textual_install_hint",
    "is_textual_compatible",
    # 主题颜色（用于横幅等 Rich 标记）
    "AVOCADO_PRIMARY",
    "AVOCADO_BRIGHT",
    "AVOCADO_DIM",
    "AVOCADO_DARK",
    # 主题系统
    "Theme",
    "ThemeManager",
    "get_theme_manager",
    # Textual Widgets
    "StatusBar",
    "CommandPaletteScreen",
    "Command",
    # Textual Views
    "ChatView",
    "ChatMessageSubmitted",
    "HelpScreen",
    # Key Bindings
    "KeyBinding",
    "KeyBindingManager",
    "KeyBindingCategory",
    "create_default_keybindings",
    # 审批对话框
    "ApprovalDialog",
    "ApprovalMode",
    "RiskLevel",
    "SENSITIVE_OPERATIONS",
    "ApprovalManager",
    "ApprovalConfirmed",
    "ApprovalRejected",
    "create_approval_dialog",
]