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
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Static, Button
from textual.binding import Binding
from textual.events import Click
from textual import on

from common.logging_manager import get_access_logger


# ============================================================================
# LogScreen - 全局日志窗口
# ============================================================================


class LogScreen(ModalScreen):
    """全局日志查看器模态窗口."""

    CSS = """
    LogScreen {
        align: center middle;
        background: $primary 30%;
    }

    /* ponytail: 覆盖紫色主题下的选中色（默认回退到 primary=紫），
       在日志弹窗里强制用中性 surface + 反色文字，避免选中文字看起来变紫。
       ponytail: $boost 在内置主题下是固定 rgba (255,255,255,0.04)，
       切主题不变；$text / $text-muted 不是 Textual 官方变量，
       改用 $foreground 才是真正跟主题的。*/
    LogScreen .screen--selection {
        background: $surface;
        color: $foreground;
    }

    #log-window {
        width: 90%;
        height: 80%;
        background: $surface 85%;
    }

    #log-header {
        width: 100%;
        height: 3;
        background: $accent;
        layout: horizontal;
        color: $foreground;
    }

    #log-header-title {
        width: 1fr;
        height: 100%;
        content-align: left middle;
        padding: 0 2;
        text-style: bold;
    }

    #btn-open-log {
        width: auto;
        height: 3;
        padding: 0 2;
        margin-right: 1;
        background: $primary;
        color: white;
        content-align: center middle;
    }

    #btn-open-log:hover {
        background: $accent;
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
        height: 1;
        layout: horizontal;
        content-align: center middle;
    }

    .log-footer-item {
        width: auto;
        color: $text-muted;
        padding: 0 1;
    }

    .log-footer-item:hover {
        color: $accent;
        background: $surface;
    }

    .log-footer-separator {
        width: auto;
        color: $text-disabled;
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
            with Horizontal(id="log-header"):
                yield Static("📜 日志查看器  (Esc/F3 关闭)", id="log-header-title")
                yield Button("📄 打开日志文件", id="btn-open-log")
            with ScrollableContainer(id="log-scroll"):
                yield WrappedLog(id="log-content")
            with Horizontal(id="log-footer"):
                yield Static("↑↓ 滚动", classes="log-footer-item")
                yield Static("|", classes="log-footer-separator")
                yield Static("鼠标可选中文本", classes="log-footer-item")
                yield Static("|", classes="log-footer-separator")
                yield Static("Esc/F3 关闭", id="log-footer-close", classes="log-footer-item")

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

    def on_click(self, event) -> None:
        """点击背景时关闭"""
        if event.widget is self:
            self.action_close()

    @on(Click, "#log-footer-close")
    def _handle_footer_close_click(self, event: Static.Click) -> None:
        """点击 footer 关闭按钮"""
        event.stop()
        self.action_close()

    def _get_log_file_path(self) -> str:
        """获取最新的日志文件路径（按日期轮转后不再是固定名字）"""
        try:
            from common.config import get_logs_dir
            logs_dir = get_logs_dir()
            if not logs_dir.exists():
                return ""
            # 找最新的 .log 文件（按日期轮转后是 agent-z-YYYY-MM-DD.log）
            files = sorted(logs_dir.glob("agent-z-*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
            if files:
                return str(files[0])
            # 兼容未开启轮转时的旧文件名
            fallback = logs_dir / "agent-z.log"
            if fallback.exists():
                return str(fallback)
            return ""
        except Exception:
            return ""

    def _open_log_file(self) -> None:
        """用系统默认程序打开日志文件"""
        import os
        import sys
        path = self._get_log_file_path()
        if not path or not os.path.exists(path):
            self.notify("日志文件未开启，请到设置中启用文件日志", severity="warning")
            return
        try:
            if sys.platform == "win32":
                os.startfile(path)  # type: ignore
            elif sys.platform == "darwin":
                os.system(f"open {path!r}")
            else:
                os.system(f"xdg-open {path!r}")
        except Exception as e:
            self._logger.debug(f"Failed to open log file: {e}")

    def on_button_pressed(self, event: "Button.Pressed") -> None:  # type: ignore[override]
        """处理按钮点击"""
        if event.button.id == "btn-open-log":
            self._open_log_file()


# ============================================================================
# 模块导出
# ============================================================================

__all__ = ["LogScreen"]