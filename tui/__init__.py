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
    AVOCADO_PRIMARY,
    AVOCADO_BRIGHT,
    AVOCADO_DIM,
    AVOCADO_DARK,
)

# 主题系统
from tui.theming import (
    ThemeManager,
    get_theme_manager,
    Theme,
    ThemeConfig,
)

# 视图
from tui.views import (
    ChatView,
    ChatMessageSubmitted,
    HelpScreen,
    SessionPickerScreen,
    WelcomeScreen,
    OnboardingScreen,
)

# 组件
from tui.widgets import (
    StatusBar,
    CommandPaletteScreen,
    Command,
    MessageList,
    StreamingText,
    ApprovalDialog,
)

# 核心
from tui.core import (
    keybindings,
    markdown_renderer,
    curses_ui,
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
    "AVOCADO_PRIMARY",
    "AVOCADO_BRIGHT",
    "AVOCADO_DIM",
    "AVOCADO_DARK",
    # 主题系统
    "ThemeManager",
    "get_theme_manager",
    "Theme",
    "ThemeConfig",
    # 视图
    "ChatView",
    "ChatMessageSubmitted",
    "HelpScreen",
    "SessionPickerScreen",
    "WelcomeScreen",
    "OnboardingScreen",
    # 组件
    "StatusBar",
    "CommandPaletteScreen",
    "Command",
    "MessageList",
    "StreamingText",
    "ApprovalDialog",
    # 核心
    "keybindings",
    "markdown_renderer",
    "curses_ui",
]
