#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Textual App 依赖导入层（带降级机制）

🚪 Access - 💬 TUI - Textual App - 依赖导入

v8.x 重构：
原 ``app.py`` 第 1–227 行（约 200 行）的所有 try/except fallback 导入
统一迁移到此模块。

提供：
- Textual 框架全量 API（App/Widgets/Binding/Container 等）
- Rich 库 API（RichText / Style）
- i18n 国际化支持（带 SimpleI18n fallback）
- 日志系统（get_access_logger / LogManager）
- 跨模块 widgets/views/services/consumers 容错导入
- ``_patch_textual_logger()`` —— Textual LayerLogger 静音补丁

所有导入均使用 ``None`` 或 stub fallback，**不会抛 ImportError**，
以保证 ``from tui.textual_app.app import AgentApp`` 在任何环境都能 import。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

# ============================================================================
# Textual 框架导入（带降级）
# ============================================================================

TEXTUAL_AVAILABLE = True
_TEXTUAL_IMPORT_ERROR: str | None = None

try:
    from textual.app import App, ComposeResult
    from textual.widgets import (
        Header,
        Footer,
        Static,
        RichLog,
        TextArea,
        Button,
    )
    from textual.widgets import Markdown, LoadingIndicator, Select, Input
    from textual.binding import Binding
    from textual.containers import Container, Vertical, Horizontal
    from textual.screen import Screen as TextualScreen
    from textual.message import Message
    from textual import on
    from textual.events import Key, Click
    from textual import events as textual_events
    from textual.theme import Theme

    # NewLine 在 Textual 0.x 中已被移除，使用 Rich.Text 替代
    try:
        from textual.widgets._text_area import NewLine
    except ImportError:
        # Textual 1.x 不再有 NewLine，创建一个简单的替代类
        class NewLine:
            def __init__(self, count: int = 1):
                self.count = count

    KeyEvent = Key
except ImportError as e:
    TEXTUAL_AVAILABLE = False
    _TEXTUAL_IMPORT_ERROR = str(e)

    # TextualScreen 后备定义
    class TextualScreen:
        """Textual Screen 的后备类."""

        pass

    class NewLine:  # type: ignore[no-redef]
        def __init__(self, count: int = 1):
            self.count = count

    # 必要的占位类型（让代码仍能被 import，但不真正运行 Textual）
    App = object  # type: ignore[misc,assignment]
    ComposeResult = object  # type: ignore[misc,assignment]
    Header = Footer = Static = RichLog = TextArea = Button = None  # type: ignore
    Markdown = LoadingIndicator = Select = Input = None  # type: ignore
    Binding = None  # type: ignore
    Container = Vertical = Horizontal = None  # type: ignore
    Message = None  # type: ignore
    on = lambda *args, **kwargs: lambda f: f  # type: ignore
    Key = Click = None  # type: ignore
    textual_events = None  # type: ignore
    Theme = None  # type: ignore
    KeyEvent = None  # type: ignore


# ============================================================================
# Rich 库导入
# ============================================================================

try:
    from rich.text import Text as RichText
    from rich.style import Style
except ImportError:
    RichText = None  # type: ignore
    Style = None  # type: ignore


if TYPE_CHECKING:
    from textual.widget import Widget


# ============================================================================
# i18n 支持（带 SimpleI18n fallback）
# ============================================================================

try:
    from common.i18n import get_i18n, t
except ImportError:

    def get_i18n():
        class SimpleI18n:
            def t(self, key, default=None, **kwargs):
                return default or key

        return SimpleI18n()

    def t(key, default=None, **kwargs):
        return default or key


# ============================================================================
# 日志系统
# ============================================================================

try:
    from common.logging_manager import get_access_logger, LogManager
except ImportError:
    logging.basicConfig(level=logging.INFO)

    def get_access_logger(*args, **kwargs):
        return logging.getLogger("Agent")

    LogManager = None  # type: ignore


# ============================================================================
# Textual Logger 静音补丁
# ============================================================================


def _patch_textual_logger() -> None:
    """Patch Textual's LayerLogger to be compatible."""
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


# 立即执行一次，让全局静音生效
_patch_textual_logger()


# ============================================================================
# 跨模块容错导入（widgets / views / services / consumers）
# ============================================================================

try:
    from agent.context.token_estimator import estimate_messages_tokens_rough
except ImportError:
    estimate_messages_tokens_rough = None  # type: ignore


try:
    from tui.widgets.chat_container import ChatContainer
except ImportError:
    ChatContainer = None  # type: ignore


try:
    from tui.views.session_picker import SessionPickerScreen
except ImportError:
    SessionPickerScreen = None  # type: ignore


try:
    from tui.sidebar import SidebarContainer
except ImportError:
    SidebarContainer = None  # type: ignore


try:
    from tui.consumers import TUIConsumer
except ImportError:
    TUIConsumer = None  # type: ignore


try:
    from tui.widgets.approval_dialog import (
        ApprovalDialog,
        ApprovalMode,
        RiskLevel,
        ApprovalManager,
        ApprovalConfirmed,
        ApprovalRejected,
        create_approval_dialog,
    )
except ImportError:
    ApprovalDialog = None  # type: ignore
    ApprovalMode = None  # type: ignore
    RiskLevel = None  # type: ignore
    ApprovalManager = None  # type: ignore
    ApprovalConfirmed = None  # type: ignore
    ApprovalRejected = None  # type: ignore
    create_approval_dialog = None  # type: ignore


try:
    from tui.services.session_store import SessionStore
except ImportError:
    SessionStore = None  # type: ignore


try:
    from tui.views.help_view import HelpScreen
except ImportError:
    HelpScreen = None  # type: ignore


try:
    from tui.views.file_preview import FilePreviewScreen
except ImportError:
    FilePreviewScreen = None  # type: ignore


try:
    from tui.views.settings_screen import SettingsScreen
except ImportError:
    SettingsScreen = None  # type: ignore


try:
    from tui.views.log_screen import LogScreen
except ImportError:
    LogScreen = None  # type: ignore


# ponytail: common.theming.css 已删除；_load_stylesheets 现在只依赖内联 APP_CSS。
get_stylesheets = None  # type: ignore


__all__ = [
    # Textual
    "TEXTUAL_AVAILABLE",
    "_TEXTUAL_IMPORT_ERROR",
    "TextualScreen",
    "App",
    "ComposeResult",
    "Header",
    "Footer",
    "Static",
    "RichLog",
    "TextArea",
    "Button",
    "Markdown",
    "LoadingIndicator",
    "Select",
    "Input",
    "Binding",
    "Container",
    "Vertical",
    "Horizontal",
    "Message",
    "on",
    "Key",
    "Click",
    "textual_events",
    "Theme",
    "NewLine",
    "KeyEvent",
    # Rich
    "RichText",
    "Style",
    # i18n
    "get_i18n",
    "t",
    # logging
    "get_access_logger",
    "LogManager",
    # helpers
    "_patch_textual_logger",
    # cross-module
    "estimate_messages_tokens_rough",
    "ChatContainer",
    "SessionPickerScreen",
    "SidebarContainer",
    "TUIConsumer",
    "ApprovalDialog",
    "ApprovalMode",
    "RiskLevel",
    "ApprovalManager",
    "ApprovalConfirmed",
    "ApprovalRejected",
    "create_approval_dialog",
    "SessionStore",
    "HelpScreen",
    "FilePreviewScreen",
    "SettingsScreen",
    "LogScreen",
    "get_stylesheets",
]