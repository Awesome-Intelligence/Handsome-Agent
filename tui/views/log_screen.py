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
        background: $boost 40%;
    }

    #log-window {
        width: 90%;
        height: 80%;
        border: solid $accent;
        background: $surface 85%;
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
        Binding("escape", "close", "关闭", show=True),
        Binding("ctrl+c", "copy", "复制"),
        Binding("f3", "close", "关闭", show=False),
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
            yield Static("📜 日志查看器  (Esc/F3 关闭)", id="log-header")
            with ScrollableContainer(id="log-scroll"):
                yield WrappedLog(id="log-content")
            yield Static("↑↓ 滚动  |  鼠标可选中文本  |  Esc/F3 关闭", id="log-footer")

    def on_mount(self) -> None:
        """挂载时注册到 TuiLogHandler 并滚动到底部."""
        self._logger.debug("Log screen mounted")

        from tui.sidebar import WrappedLog
        from textual.containers import ScrollableContainer

        log_widget = self.query_one("#log-content", WrappedLog)
        self._wrapped_log = log_widget

        # 注册到 TuiLogHandler（会 replay 全部历史日志）
        try:
            app = self.app
            if hasattr(app, "_tui_log_handler") and app._tui_log_handler is not None:
                app._tui_log_handler.set_widget(log_widget)
                self._logger.debug("Log widget registered to TuiLogHandler")
        except Exception as e:
            self._logger.warning(f"Failed to register log widget: {e}")

        # replay 完成后滚动到底部（call_after_refresh 确保 DOM 渲染完毕）
        def _scroll_to_bottom() -> None:
            scroll = self.query_one("#log-scroll", ScrollableContainer)
            scroll.scroll_end(animate=False)

        self.call_after_refresh(_scroll_to_bottom)

    def action_copy(self) -> None:
        """复制日志内容."""
        try:
            log_widget = self.query_one("#log-content")
            text = ""
            if hasattr(log_widget, "_lines"):
                text = "\n".join(log_widget._lines)
            elif hasattr(log_widget, "text"):
                text = getattr(log_widget, "text", "")
            if text:
                self.app.copy_to_clipboard(text)
                self.notify("已复制日志内容")
            else:
                self.notify("日志为空")
        except Exception as e:
            self._logger.debug(f"Copy action failed: {e}")

    def action_close(self) -> None:
        """关闭日志窗口."""
        self._logger.debug("Log screen closed")
        # ponytail: 关闭时停掉 flush timer、清空 widget 引用，
        # 否则定时器每 100ms 写一次孤儿 widget，下一次开 Modal 还会更慢。
        try:
            app = self.app
            if getattr(app, "_tui_log_handler", None) is not None:
                app._tui_log_handler.detach_widget()
        except Exception as e:
            self._logger.debug(f"detach_widget failed (ignored): {e}")
        self.dismiss()


# ============================================================================
# 模块导出
# ============================================================================

__all__ = ["LogScreen"]