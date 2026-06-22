"""
Handsome Agent TUI Module

A modern terminal user interface for the Handsome Agent application.

🚪 Access - 💬 TUI - Module

Usage:
    from tui import HandsomeAgentApp, ThemeManager
    from tui.textual_app import run_textual_app

    # 独立启动 TUI
    python -m tui.main

    # 从 CLI 启动 TUI
    python -m cli.main --textual
"""

__version__ = "0.1.0"

# 主应用
from tui.textual_app import (
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
    PURPLE_PRIMARY,
    PURPLE_BRIGHT,
    PURPLE_DIM,
    PURPLE_DARK,
)

# 主题系统
from tui.theming import (
    ThemeManager,
    get_theme_manager,
    Theme,
)

# 视图
from tui.views import (
    ChatView,
    HelpScreen,
    SessionPickerScreen,
    WelcomeScreen,
    OnboardingScreen,
)

# 组件
from tui.widgets import (
    CommandPaletteScreen,
    Command,
    MessageList,
    StreamingText,
    ApprovalDialog,
)

# 核心模块
import tui.core.keybindings as keybindings
import tui.core.markdown_renderer as markdown_renderer
from common.terminal.curses_ui import (
    has_curses,
    curses_radiolist,
    curses_checklist,
    radio_select,
    multi_select,
    flush_stdin,
)

__all__ = [
    # 版本
    "__version__",
    # 主应用
    "HandsomeAgentApp",
    "run_textual_app",
    "TEXTUAL_AVAILABLE",
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
    "PURPLE_PRIMARY",
    "PURPLE_BRIGHT",
    "PURPLE_DIM",
    "PURPLE_DARK",
    # 主题系统
    "ThemeManager",
    "get_theme_manager",
    "Theme",
    # 视图
    "ChatView",
    "HelpScreen",
    "SessionPickerScreen",
    "WelcomeScreen",
    "OnboardingScreen",
    # 组件
    "CommandPaletteScreen",
    "Command",
    "MessageList",
    "StreamingText",
    "ApprovalDialog",
    # 核心模块
    "keybindings",
    "markdown_renderer",
    "has_curses",
    "curses_radiolist",
    "curses_checklist",
    "radio_select",
    "multi_select",
    "flush_stdin",
]
