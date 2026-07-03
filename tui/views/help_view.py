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
    from textual.containers import Container, ScrollableContainer
    from textual.message import Message
except ImportError:
    TEXTUAL_AVAILABLE = False
    ModalScreen = object  # type: ignore
    Static = object  # type: ignore
    ScrollableContainer = object  # type: ignore
    Container = object  # type: ignore
    Message = object  # type: ignore

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

# 快捷键模块
try:
    from ..keybindings import KeyBinding, KeyBindingManager
except ImportError:
    KeyBinding = None
    KeyBindingManager = None


# ============================================================================
# 主题颜色常量（高雅紫）
# ============================================================================

AVOCADO_PRIMARY = "#B180D7"       # rgb(177,128,215) - 主色
AVOCADO_BRIGHT = "#C9A0E0"        # rgb(201,160,224) - 亮色
AVOCADO_DIM = "#8B5CAC"           # rgb(139,92,172) - 暗色
AVOCADO_DARK = "#6B4EA8"          # rgb(107,78,168) - 深色
WHITE = "white"
GRAY_DIM = "#888888"
GOLD = "#FFD700"


# ============================================================================
# HelpView CSS
# ============================================================================

HELP_VIEW_CSS = """
HelpScreen {
    background: """ + AVOCADO_DARK + """;
}

#help-container {
    width: 70;
    height: auto;
    max-height: 80%;
    margin: 2 4;
    background: $surface;
    border: solid """ + AVOCADO_PRIMARY + """;
    border-title-style: bold;
    padding: 1 2;
}

#help-title {
    width: 100%;
    height: auto;
    padding: 1 0;
    text-style: bold;
    color: """ + AVOCADO_BRIGHT + """;
}

#help-content {
    width: 100%;
    height: auto;
    max-height: 70;
}

.help-category {
    width: 100%;
    height: auto;
    padding: 1 0;
}

.category-title {
    text-style: bold;
    color: """ + AVOCADO_PRIMARY + """;
    text-style: bold;
}

.kbinding-item {
    width: 100%;
    height: auto;
    padding: 0 2;
}

.kbinding-key {
    color: """ + GOLD + """;
    text-style: bold;
}

.kbinding-desc {
    color: """ + WHITE + """;
}

#help-footer {
    width: 100%;
    height: auto;
    padding: 1 0;
    color: """ + GRAY_DIM + """;
}
"""


# ============================================================================
# 快捷键类别名称映射
# ============================================================================

CATEGORY_NAMES = {
    "navigation": "导航",
    "tab": "标签页",
    "command": "命令",
    "help": "帮助",
    "session": "会话",
}

CATEGORY_NAMES_EN = {
    "navigation": "Navigation",
    "tab": "Tabs",
    "command": "Commands",
    "help": "Help",
    "session": "Session",
}


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
    
    # 面板关闭消息
    class HelpClosed(Message):
        """帮助面板关闭消息"""
        pass
    
    def __init__(
        self,
        key_binding_manager: KeyBindingManager | None = None,
        custom_content: str | None = None,
        **kwargs
    ) -> None:
        """初始化帮助面板
        
        Args:
            key_binding_manager: 快捷键管理器（如果为 None，使用默认内容）
            custom_content: 自定义帮助内容（如果提供，忽略 key_binding_manager）
            **kwargs: 传递给父类的参数
        """
        super().__init__(**kwargs)
        self._key_binding_manager = key_binding_manager
        self._custom_content = custom_content
        self._logger = get_access_logger("HelpView", sublayer="cli")
    
    def compose(self) -> ComposeResult:
        """组合组件
        
        Returns:
            组件生成器
        """
        i18n = get_i18n()
        
        # 标题
        title = i18n.t("tui.help.title")
        yield Static(
            f"[bold {AVOCADO_BRIGHT}]⌨ {title}[/]",
            id="help-title"
        )
        
        # 帮助内容
        with ScrollableContainer(id="help-content"):
            yield Static(self._build_help_content(), id="help-body")
        
        # 底部提示
        hint = i18n.t("tui.help.hint")
        yield Static(
            f"[{GRAY_DIM}]{hint}[/]",
            id="help-footer"
        )
    
    def _build_help_content(self) -> str:
        """构建帮助内容
        
        Returns:
            格式化的帮助内容
        """
        if self._custom_content:
            return self._custom_content
        
        # 使用默认快捷键内容
        i18n = get_i18n()
        content_lines = []
        
        # 分类显示快捷键
        categories = [
            ("navigation", i18n.t("tui.help.category.navigation")),
            ("tab", i18n.t("tui.help.category.tab")),
            ("command", i18n.t("tui.help.category.command")),
            ("help", i18n.t("tui.help.category.help")),
            ("session", i18n.t("tui.help.category.session")),
        ]
        
        default_bindings = self._get_default_bindings()
        
        for category_key, category_name in categories:
            bindings = [
                b for b in default_bindings
                if b.category == category_key
            ]
            
            if not bindings:
                continue
            
            content_lines.append(f"[bold {AVOCADO_PRIMARY}]{category_name}[/]")
            
            for binding in bindings:
                key_display = self._format_key(binding.key)
                desc = i18n.t(f"tui.keybinding.{binding.key}")
                # Fallback to binding description if key not found
                if desc == f"tui.keybinding.{binding.key}":
                    desc = binding.description
                content_lines.append(
                    f"  [{GOLD}]{key_display:<15}[/{GOLD}]  {desc}"
                )
            
            content_lines.append("")
        
        return "\n".join(content_lines)
    
    def _get_default_bindings(self) -> list[KeyBinding]:
        """获取默认快捷键列表
        
        Returns:
            快捷键列表
        """
        if self._key_binding_manager:
            return self._key_binding_manager.bindings
        
        # 返回硬编码的默认快捷键（action 已废弃，始终为 None）
        return [
            KeyBinding("up", "上移", category="navigation"),
            KeyBinding("down", "下移", category="navigation"),
            KeyBinding("j", "下移 (vim)", category="navigation"),
            KeyBinding("k", "上移 (vim)", category="navigation"),
            KeyBinding("ctrl+t", "新建标签", category="tab"),
            KeyBinding("ctrl+w", "关闭标签", category="tab"),
            KeyBinding("ctrl+tab", "切换到下一个标签", category="tab"),
            KeyBinding("ctrl+shift+tab", "切换到上一个标签", category="tab"),
            KeyBinding("ctrl+k", "打开命令面板", category="command"),
            KeyBinding("ctrl+l", "清屏", category="command"),
            KeyBinding("ctrl+c", "复制", category="command"),
            KeyBinding("ctrl+v", "粘贴", category="command"),
            KeyBinding("escape", "关闭/取消", category="command"),
            KeyBinding("ctrl+q", "退出应用", category="command"),
            KeyBinding("q", "退出应用", category="command"),
            KeyBinding("f1", "打开帮助", category="help"),
            KeyBinding("ctrl+/", "打开帮助", category="help"),
            KeyBinding("ctrl+r", "打开会话选择器", category="session"),
        ]
    
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
    
    def on_key(self, event: "Input.Key") -> None:
        """处理键盘事件"""
        key = event.key
        
        # Esc 或 q 关闭
        if key in ("escape", "q"):
            self._close()
            event.prevent_default()
    
    def _close(self) -> None:
        """关闭帮助面板"""
        self._logger.debug("Closing help screen")
        self.post_message(self.HelpClosed())
        self.app.pop_screen()


# ============================================================================
# 模块导出
# ============================================================================

__all__ = [
    "HelpScreen",
    "HELP_VIEW_CSS",
]