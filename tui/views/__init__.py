#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TUI Views - Textual UI View Components

🚪 Access - 💬 CLI - TUI Views

提供 Textual TUI 所需的内容视图组件，包括：
- ChatView: 聊天视图组件
- HelpScreen: 帮助面板组件
- SessionPickerScreen: 会话选择器
- WelcomeScreen: 欢迎界面组件
- OnboardingScreen: 首次使用引导流程
"""

from .chat_view import ChatView

# 帮助面板（带降级机制）
try:
    from .help_view import HelpScreen
except ImportError:
    HelpScreen = None

# 会话选择器（带降级机制）
try:
    from .session_picker import SessionPickerScreen
except ImportError:
    SessionPickerScreen = None

# 欢迎界面（带降级机制）
try:
    from .welcome_screen import (
        WelcomeScreen,
        WelcomeScreenMessage,
        StartOnboarding,
        SkipOnboarding,
        OpenSettings,
    )
except ImportError:
    WelcomeScreen = None
    WelcomeScreenMessage = None
    StartOnboarding = None
    SkipOnboarding = None
    OpenSettings = None

# 首次使用引导（带降级机制）
try:
    from .onboarding_screen import (
        OnboardingStep,
        OnboardingScreen,
        OnboardingMessage,
        OnboardingComplete,
        OnboardingSkipped,
        ConfigurationSaved,
    )
except ImportError:
    OnboardingStep = None
    OnboardingScreen = None
    OnboardingMessage = None
    OnboardingComplete = None
    OnboardingSkipped = None
    ConfigurationSaved = None

__all__ = [
    "ChatView",
    "HelpScreen",
    "SessionPickerScreen",
    # 欢迎界面
    "WelcomeScreen",
    "WelcomeScreenMessage",
    "StartOnboarding",
    "SkipOnboarding",
    "OpenSettings",
    # 引导流程
    "OnboardingStep",
    "OnboardingScreen",
    "OnboardingMessage",
    "OnboardingComplete",
    "OnboardingSkipped",
    "ConfigurationSaved",
]