#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TUI Views - Textual UI View Components

🚪 Access - 💬 CLI - TUI Views

提供 Textual TUI 所需的内容视图组件，包括：
- HelpScreen: 帮助面板组件
- WelcomeScreen: 欢迎界面组件
- WizardScreen: 首次使用引导向导

注意：原先 ChatView 已被替换为 tui.widgets.ChatContainer（oterm 风格），
见 `tui/widgets/chat_container.py`。
"""

# ChatView 已迁移至 tui/widgets/chat_container.py 的 ChatContainer。

# 帮助面板（带降级机制）
try:
    from .help_view import HelpScreen
except ImportError:
    HelpScreen = None

# 首次使用引导（带降级机制）
try:
    from .onboarding import (
        WelcomeScreen,
        WizardScreen,
    )
except ImportError:
    WelcomeScreen = None
    WizardScreen = None

# 设置界面（带降级机制）
try:
    from .settings_screen import SettingsScreen
except ImportError:
    SettingsScreen = None

# 日志窗口（带降级机制）
try:
    from .log_screen import LogScreen
except ImportError:
    LogScreen = None

__all__ = [
    "HelpScreen",
    # 首次使用引导
    "WelcomeScreen",
    "WizardScreen",
    # 设置界面
    "SettingsScreen",
    # 日志窗口
    "LogScreen",
]
