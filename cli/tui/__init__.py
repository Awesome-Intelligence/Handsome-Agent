#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TUI (Terminal User Interface) - 终端界面渲染层

🚪 Access - 💬 CLI - TUI 渲染层

⚠️ 已弃用：此模块内容已迁移到顶层 `tui/` 目录
   请使用 `from tui import ...` 代替 `from cli.tui import ...`

此文件提供向后兼容，建议逐步迁移到新的导入路径。

Usage（已弃用）:
    from cli.tui import TEXTUAL_AVAILABLE  # 请改用 from tui import TEXTUAL_AVAILABLE

Usage（新方式）:
    from tui import TEXTUAL_AVAILABLE
    from tui.textual_app import run_textual_app
"""

from __future__ import annotations

import warnings

# 发出弃用警告
warnings.warn(
    "cli.tui 模块已弃用，请使用 tui 模块代替。\n"
    "例如：from cli.tui import ... -> from tui import ...",
    DeprecationWarning,
    stacklevel=2
)

# ============================================================================
# 立即 patch Textual 的 LayerLogger 以修复 Textual 8.x 兼容性问题
# 这个 patch 必须在任何 Textual 代码导入之前执行
# ============================================================================

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

# ============================================================================
# 从新的 tui 模块重导出所有公共 API
# ============================================================================

# 主应用
from tui import (
    # 主应用
    HandsomeAgentApp,
    run_textual_app,
    TEXTUAL_AVAILABLE,
    check_textual_available,
    get_textual_import_error,
    get_textual_install_hint,
    is_textual_compatible,
    create_fallback_app,
    APP_CSS,
    TuiLogHandler,
    NotificationAnimationManager,
    NotificationType,
    SubmitTextArea,
    AVOCADO_PRIMARY,
    AVOCADO_BRIGHT,
    AVOCADO_DIM,
    AVOCADO_DARK,
    # 主题系统
    ThemeManager,
    get_theme_manager,
    Theme,
    ThemeConfig,
    # 视图
    ChatView,
    ChatMessageSubmitted,
    HelpScreen,
    SessionPickerScreen,
    WelcomeScreen,
    OnboardingScreen,
    # 组件
    StatusBar,
    CommandPaletteScreen,
    Command,
    MessageList,
    StreamingText,
    ApprovalDialog,
    # 核心
    keybindings,
    markdown_renderer,
    curses_ui,
)

# 重新导出 keybindings 模块的函数（用于 from cli.tui.core.keybindings import ...）
from tui.core.keybindings import (
    KeyBinding,
    KeyBindingManager,
    KeyBindingCategory,
    create_default_keybindings,
)

# 重新导出 curses_ui 模块的函数
from tui.core.curses_ui import (
    has_curses,
    curses_radiolist,
    curses_checklist,
    radio_select,
    multi_select,
    flush_stdin,
)

# 重新导出 widgets 中的组件
from tui.widgets import (
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
    "create_fallback_app",
    "APP_CSS",
    "TuiLogHandler",
    "NotificationAnimationManager",
    "NotificationType",
    "SubmitTextArea",
    # 主题颜色
    "AVOCADO_PRIMARY",
    "AVOCADO_BRIGHT",
    "AVOCADO_DIM",
    "AVOCADO_DARK",
    # 主题系统
    "Theme",
    "ThemeConfig",
    "ThemeManager",
    "get_theme_manager",
    # Textual Widgets
    "StatusBar",
    "CommandPaletteScreen",
    "Command",
    "MessageList",
    "StreamingText",
    # Textual Views
    "ChatView",
    "ChatMessageSubmitted",
    "HelpScreen",
    "SessionPickerScreen",
    "WelcomeScreen",
    "OnboardingScreen",
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
    # 核心模块
    "keybindings",
    "markdown_renderer",
    "curses_ui",
]
