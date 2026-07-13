#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Help View - Textual TUI Help Panel

🚪 Access - 💬 CLI - TUI Views - HelpView

提供帮助面板功能，支持：
- 按类别分组显示快捷键
- 键盘快捷键视觉提示
- Esc/q 关闭

Features:
- 分类显示快捷键
- 快捷键视觉格式化
- 可自定义内容
"""

from __future__ import annotations

from typing import TYPE_CHECKING

# Textual 框架导入（带降级机制）
TEXTUAL_AVAILABLE = True
try:
    from textual.app import ComposeResult
    from textual.screen import ModalScreen
    from textual.widgets import Static
    from textual.containers import Container, VerticalScroll
    from textual.message import Message
    from textual.binding import Binding
except ImportError:
    TEXTUAL_AVAILABLE = False
    ModalScreen = object  # type: ignore
    Static = object  # type: ignore
    VerticalScroll = object  # type: ignore
    Container = object  # type: ignore
    Message = object  # type: ignore
    Binding = lambda *a, **k: None  # type: ignore

# i18n 支持
try:
    from common.i18n import get_i18n
except ImportError:
    # 降级：简单的翻译函数
    def get_i18n():
        class SimpleI18n:
            def t(self, key, default=None, **kwargs):
                return default or key
        return SimpleI18n()

# 日志支持
try:
    from common.logging_manager import get_access_logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    def get_access_logger(*args, **kwargs):
        return logging.getLogger("HandsomeAgent")


# ============================================================================
# HelpView CSS - 参考 SettingsScreen 风格
# ============================================================================

HELP_VIEW_CSS = """
HelpScreen {
    align: center middle;
    background: $boost 40%;
}

#help-container {
    width: 70%;
    height: 70%;
    border: solid $accent;
    background: $surface;
}

#help-header {
    width: 100%;
    height: 3;
    background: $accent;
    content-align: center middle;
    color: $text;
    text-style: bold;
}

#help-body {
    height: 1fr;
}

#help-content {
    padding: 1 2;
    height: 100%;
}

#help-footer {
    width: 100%;
    height: 2;
    background: $accent 20%;
    content-align: center middle;
    color: $text-muted;
}
"""


# ============================================================================
# HelpScreen - 帮助面板模态窗口
# ============================================================================

class HelpScreen(ModalScreen):
    """帮助面板模态窗口
    
    显示键盘快捷键帮助信息，按类别分组。
    
    Messages:
        HelpClosed: 帮助面板关闭事件
    """
    
    CSS = HELP_VIEW_CSS
    
    BINDINGS = [
        Binding("escape", "close", "关闭", show=False),
        Binding("q", "close", "关闭", show=False),
    ]
    
    # 面板关闭消息
    class HelpClosed(Message):
        """帮助面板关闭消息"""
        pass
    
    def __init__(
        self,
        custom_content: str | None = None,
        **kwargs
    ) -> None:
        """初始化帮助面板

        Args:
            custom_content: 自定义帮助内容
            **kwargs: 传递给父类的参数
        """
        super().__init__(**kwargs)
        self._custom_content = custom_content
        self._logger = get_access_logger("HelpView", sublayer="cli")
    
    def compose(self) -> ComposeResult:
        """组合组件
        
        Returns:
            组件生成器
        """
        i18n = get_i18n()
        
        with Container(id="help-container"):
            yield Static("⌨ 快捷键帮助  (Esc/Q 关闭)", id="help-header")
            
            with VerticalScroll(id="help-body"):
                yield Static(self._build_help_content(), id="help-content")
            
            yield Static("↑↓ 滚动  |  Esc/Q 关闭", id="help-footer")
    
    def _build_help_content(self) -> str:
        """构建帮助内容
        
        Returns:
            格式化的帮助内容
        """
        if self._custom_content:
            return self._custom_content
        
        i18n = get_i18n()
        content_lines = []
        
        bindings = self._get_bindings()

        if not bindings:
            content_lines.append("[dim]暂无快捷键绑定[/dim]")
            return "\n".join(content_lines)

        content_lines.append("[bold]快捷键[/]")

        for binding in bindings:
            if getattr(binding, "show", True) is False:
                continue

            key_display = self._format_key(binding.key)
            desc = getattr(binding, "description", "") or getattr(binding, "action", "") or ""
            content_lines.append(
                f"  [bold]{key_display:<15}[/]  {desc}"
            )

        return "\n".join(content_lines)
    
    def _get_bindings(self) -> list:
        """获取应用的实际快捷键绑定"""
        if hasattr(self.app, "bindings") and hasattr(self.app.bindings, "keys"):
            return list(self.app.bindings.keys.values())
        return getattr(self.app, "BINDINGS", [])
    
    def _format_key(self, key: str) -> str:
        """格式化键名用于显示
        
        Args:
            key: 原始键名
            
        Returns:
            格式化后的键名
        """
        parts = key.split("+")
        formatted = []
        
        for part in parts:
            part = part.lower().strip()
            if part == "ctrl":
                formatted.append("Ctrl")
            elif part == "shift":
                formatted.append("Shift")
            elif part == "alt":
                formatted.append("Alt")
            elif part == "escape":
                formatted.append("Esc")
            elif part == "tab":
                formatted.append("Tab")
            elif part == "up":
                formatted.append("↑")
            elif part == "down":
                formatted.append("↓")
            elif part == "left":
                formatted.append("←")
            elif part == "right":
                formatted.append("→")
            else:
                formatted.append(part.upper())
        
        return "+".join(formatted)
    
    def on_mount(self) -> None:
        """组件挂载时初始化"""
        self._logger.debug("Help screen mounted")
    
    def action_close(self) -> None:
        """关闭帮助面板"""
        self._logger.debug("Closing help screen")
        self.post_message(self.HelpClosed())
        self.dismiss()


# ============================================================================
# 模块导出
# ============================================================================

__all__ = [
    "HelpScreen",
    "HELP_VIEW_CSS",
]