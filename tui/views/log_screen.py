#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LogScreen - 全局日志窗口

🚪 Access - 💬 CLI - TUI Views - LogScreen

独立的全局日志查看器，通过 Alt+L 快捷键打开/关闭，
替代侧边栏中的日志面板，提供更大的显示空间和更好的可读性。
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static
from textual.binding import Binding

# 日志支持
try:
    from common.logging_manager import get_access_logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    def get_access_logger(*args, **kwargs):
        return logging.getLogger("HandsomeAgent")


# ============================================================================
# LogScreen - 全局日志窗口
# ============================================================================


class LogScreen(ModalScreen):
    """全局日志查看器模态窗口."""

    CSS = """
    LogScreen {
        align: center middle;
    }

    #log-window {
        width: 90%;
        height: 80%;
        border: solid $accent;
        background: $surface;
    }

    #log-header {
        width: 100%;
        height: 3;
        background: $accent;
        content-align: center middle;
        color: $text;
        text-style: bold;
    }

    #log-scroll {
        width: 100%;
        height: 1fr;
    }

    #log-content {
        width: 100%;
        height: auto;
    }

    #log-footer {
        width: 100%;
        height: 2;
        background: $accent 20%;
        content-align: center middle;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "关闭", show=False),
        Binding("q", "close", "关闭", show=False),
        Binding("l", "close", "关闭", show=False),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._logger = get_access_logger("LogScreen", sublayer="tui")
        self._wrapped_log: "WrappedLog | None" = None

    def compose(self) -> ComposeResult:
        """组合子组件."""
        from tui.sidebar import WrappedLog
        from textual.containers import ScrollableContainer

        with Vertical(id="log-window"):
            yield Static("📜 日志查看器  (Esc/q/Alt+L 关闭)", id="log-header")
            with ScrollableContainer(id="log-scroll"):
                yield WrappedLog(id="log-content", markup=False)
            yield Static("↑↓ 滚动  |  鼠标可选中文本  |  Esc 关闭", id="log-footer")

    def on_mount(self) -> None:
        """挂载时注册到 TuiLogHandler."""
        self._logger.debug("Log screen mounted")

        from tui.sidebar import WrappedLog
        log_widget = self.query_one("#log-content", WrappedLog)
        self._wrapped_log = log_widget

        # 注册到 TuiLogHandler
        try:
            app = self.app
            if hasattr(app, "_tui_log_handler") and app._tui_log_handler is not None:
                app._tui_log_handler.set_widget(log_widget)
                self._logger.debug("Log widget registered to TuiLogHandler")
        except Exception as e:
            self._logger.warning(f"Failed to register log widget: {e}")

    def action_close(self) -> None:
        """关闭日志窗口."""
        self._logger.debug("Log screen closed")
        self.dismiss()


# ============================================================================
# 模块导出
# ============================================================================

__all__ = ["LogScreen"]