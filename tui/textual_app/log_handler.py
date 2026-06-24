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
    性能优化：使用批量写入减少 UI 刷新频率。
    """

    # 要过滤的 logger 名称前缀（这些日志太频繁，不显示在面板）
    _FILTER_PREFIXES = ("TextualUI", "cli.tui", "tui.", "keybinding", "key_binding", "KeyBinding")
    # 要过滤的日志消息关键词（UI 交互类日志）
    _FILTER_KEYWORDS = (
        "tab", "panel", "sidebar", "log", "command palette", "screen",
        "session", "window", "theme", "focus", "mount", "unmount",
        "key", "binding", "shortcut",
    )

    def __init__(self, app, buffer_size: int = 500, batch_size: int = 10, flush_interval_ms: int = 100):
        """初始化日志处理器。

        Args:
            app: Textual App 实例
            buffer_size: 组件就绪前的最大缓冲条数
            batch_size: 批量写入的日志条数
            flush_interval_ms: 批量刷新的时间间隔（毫秒）
        """
        super().__init__()
        self._app = app
        self._widget: Log | None = None
        self._buffer: list[logging.LogRecord] = []  # 组件就绪前的缓冲
        self._buffer_size = buffer_size

        # 批量写入优化
        self._pending_logs: list[str] = []  # 待写入的日志消息
        self._batch_size = batch_size  # 达到此数量时立即写入
        self._flush_interval_ms = flush_interval_ms  # 刷新间隔（毫秒）
        self._flush_timer = None  # 刷新定时器引用

    def set_widget(self, widget: Log) -> None:
        """设置目标 Log 组件并刷新缓冲区。

        Args:
            widget: Log 组件实例
        """
        self._widget = widget
        # 组件就绪后刷新缓冲区的日志
        if self._buffer:
            for record in self._buffer:
                self._write_log(record)
            self._buffer.clear()
        # 启动批量刷新定时器
        self._start_flush_timer()

    def _start_flush_timer(self) -> None:
        """启动批量刷新定时器"""
        if self._flush_timer is None and self._widget is not None:
            try:
                self._flush_timer = self._app.set_timer(
                    self._flush_interval_ms / 1000.0,
                    self._flush_pending_logs
                )
            except Exception:
                pass

    def _stop_flush_timer(self) -> None:
        """停止批量刷新定时器"""
        if self._flush_timer is not None:
            try:
                self._flush_timer.stop()
            except Exception:
                pass
            self._flush_timer = None

    def _flush_pending_logs(self) -> None:
        """批量刷新待写入的日志（定时器回调）"""
        if not self._pending_logs or self._widget is None:
            self._flush_timer = None
            self._start_flush_timer()
            return

        try:
            # 批量写入所有待处理的日志
            for msg in self._pending_logs:
                self._widget.write_line(msg)
            self._pending_logs.clear()
        except Exception:
            pass
        finally:
            self._flush_timer = None
            # 继续调度下一次刷新
            self._start_flush_timer()

    def emit(self, record: logging.LogRecord) -> None:
        """接收日志记录（任意线程），路由到 UI 线程写入。

        Args:
            record: 日志记录
        """
        # 过滤：排除 TextualUI 相关的 DEBUG 日志
        if record.levelno == logging.DEBUG and self._is_ui_debug_log(record):
            return

        if self._widget is None:
            # 组件未就绪，缓冲日志
            if len(self._buffer) < self._buffer_size:
                self._buffer.append(record)
            return

        try:
            # 将日志格式化并加入待写入队列
            msg = self.format(record)
            self._pending_logs.append(msg)

            # 如果队列达到批量大小，立即写入
            if len(self._pending_logs) >= self._batch_size:
                self._app.call_from_thread(self._flush_pending_logs)
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
        """在 UI 线程中写入 RichLog 组件（用于刷新旧缓冲日志）。

        此方法主要用于组件就绪时刷新之前缓冲的日志。
        正常日志写入使用批量写入机制（通过 _pending_logs）。

        Args:
            record: 日志记录
        """
        if self._widget is None:
            return
        
        msg = self.format(record)
        # write_line() 会自动在消息末尾添加换行符
        self._widget.write_line(msg)

    def close(self) -> None:
        """关闭日志处理器，清理资源。

        在应用退出时应调用此方法。
        """
        # 先刷新待写入的日志
        if self._pending_logs and self._widget is not None:
            try:
                for msg in self._pending_logs:
                    self._widget.write_line(msg)
                self._pending_logs.clear()
            except Exception:
                pass

        # 停止刷新定时器
        self._stop_flush_timer()

        # 清理引用
        self._widget = None
        self._app = None
