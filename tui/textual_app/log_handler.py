#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TUI 日志处理器模块

提供将后端日志路由到 TUI 日志面板的功能。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from textual.widgets import Log


class TuiLogHandler(logging.Handler):
    """将后端日志输出重定向到 Textual Log 组件的日志处理器。

    线程安全：通过 App.call_from_thread() 将日志从任意线程路由到 UI 线程。
    组件就绪前自动缓冲日志，就绪后一次性刷新。
    过滤规则：排除 TextualUI 相关的 DEBUG 日志（窗口切换、面板切换等）。
    """

    # 要过滤的 logger 名称前缀（这些日志太频繁，不显示在面板）
    _FILTER_PREFIXES = ("TextualUI", "cli.tui", "tui.", "keybinding", "key_binding", "KeyBinding")
    # 要过滤的日志消息关键词（UI 交互类日志）
    _FILTER_KEYWORDS = (
        "tab", "panel", "sidebar", "log", "command palette", "screen",
        "session", "window", "theme", "focus", "mount", "unmount",
        "key", "binding", "shortcut",
    )

    def __init__(self, app, buffer_size: int = 500):
        super().__init__()
        self._app = app
        self._widget: Log | None = None
        self._buffer: list[logging.LogRecord] = []
        self._buffer_size = buffer_size

    def set_widget(self, widget: Log) -> None:
        """设置目标 Log 组件并刷新缓冲区。
        
        Args:
            widget: Log 组件实例
        """
        self._widget = widget
        if self._buffer:
            for record in self._buffer:
                self._write_log(record)
            self._buffer.clear()

    def emit(self, record: logging.LogRecord) -> None:
        """接收日志记录（任意线程），路由到 UI 线程写入。
        
        Args:
            record: 日志记录
        """
        # 过滤：排除 TextualUI 相关的 DEBUG 日志
        if record.levelno == logging.DEBUG and self._is_ui_debug_log(record):
            return
        
        if self._widget is None:
            if len(self._buffer) < self._buffer_size:
                self._buffer.append(record)
            return
        try:
            self._app.call_from_thread(self._write_log, record)
        except Exception:
            pass

    def _is_ui_debug_log(self, record: logging.LogRecord) -> bool:
        """判断是否为 UI 相关的 DEBUG 日志（需要过滤）。
        
        Args:
            record: 日志记录
            
        Returns:
            True 如果需要过滤
        """
        name = record.name
        if any(name.startswith(prefix) for prefix in self._FILTER_PREFIXES):
            return True
        # 也过滤 UI 交互类消息
        msg_lower = record.getMessage().lower()
        return any(kw in msg_lower for kw in self._FILTER_KEYWORDS)

    def _write_log(self, record: logging.LogRecord) -> None:
        """在 UI 线程中写入 RichLog 组件，直接追加到 lines 列表。
        
        绕过 RichLog 的 deferred render 机制，确保日志立即可见。
        
        Args:
            record: 日志记录
        """
        if self._widget is None:
            return
        
        msg = self.format(record)
        # write_line() 会自动在消息末尾添加换行符
        self._widget.write_line(msg)
