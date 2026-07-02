#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Command Palette Widget - Textual TUI Command Palette

🚪 Access - 💬 CLI - TUI Widgets - Command Palette

提供命令面板功能，支持：
- 模糊搜索命令
- 键盘快捷键提示
- 回车执行、Esc 取消
- 可配置的命令列表

Features:
- 实时模糊搜索
- 键盘导航（↑/↓/j/k）
- 命令执行回调
- 快捷键提示显示
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, TYPE_CHECKING

# Textual 框架导入（带降级机制）
TEXTUAL_AVAILABLE = True
try:
    from textual.app import ComposeResult
    from textual.screen import ModalScreen
    from textual.widgets import Static, Input, ListView, ListItem
    from textual.message import Message
    from textual.widget import Widget
except ImportError:
    TEXTUAL_AVAILABLE = False
    ModalScreen = object  # type: ignore
    Static = object  # type: ignore
    Input = object  # type: ignore
    ListView = object  # type: ignore
    ListItem = object  # type: ignore
    Message = object  # type: ignore
    Widget = object  # type: ignore

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
# 主题颜色常量（高雅紫）
# ============================================================================

PURPLE_PRIMARY = "#B180D7"       # rgb(177,128,215) - 主色
PURPLE_BRIGHT = "#C9A0E0"        # rgb(201,160,224) - 亮色
PURPLE_DIM = "#8B5CAC"           # rgb(139,92,172) - 暗色
PURPLE_DARK = "#6B4EA8"          # rgb(107,78,168) - 深色
WHITE = "white"
GRAY_DIM = "#888888"
GOLD = "#FFD700"


# ============================================================================
# Command 定义
# ============================================================================

@dataclass
class Command:
    """命令定义

    Attributes:
        id: 命令唯一标识
        name: 命令名称
        description: 命令描述
        shortcut: 快捷键提示（可选）
        action: 命令执行回调
        category: 命令类别
    """
    id: str
    name: str
    description: str
    action: Callable
    shortcut: str = ""
    category: str = "general"

    def matches(self, query: str) -> bool:
        """检查命令是否匹配查询

        Args:
            query: 搜索查询

        Returns:
            True 如果匹配，否则 False
        """
        query = query.lower().strip()
        if not query:
            return True

        # 简单的模糊匹配
        name_lower = self.name.lower()
        desc_lower = self.description.lower()

        # 检查查询字符串是否是名称或描述的子串
        if query in name_lower or query in desc_lower:
            return True

        # 简单的首字母匹配
        words = name_lower.split()
        if all(word.startswith(query[i]) for i, word in enumerate(words) if i < len(query)):
            return True

        return False


# ============================================================================
# Command Palette CSS
# ============================================================================

COMMAND_PALETTE_CSS = """
CommandPaletteScreen {
    background: """ + PURPLE_DARK + """;
}

#palette-container {
    width: 60;
    height: auto;
    max-height: 20;
    margin: 1 2;
    background: $surface;
    border: solid """ + PURPLE_PRIMARY + """;
    border-title-style: bold;
    padding: 0 1;
}

#search-input {
    width: 100%;
    margin: 1 0;
    border: solid """ + PURPLE_DIM + """;
}

#search-input:focus {
    border: solid """ + PURPLE_BRIGHT + """;
}

#command-list {
    height: 12;
    width: 100%;
    padding: 0;
}

.command-item {
    width: 100%;
    height: auto;
    padding: 0 1;
}

.command-item:hover {
    background: """ + PURPLE_DIM + """;
}

.command-item:focus {
    background: """ + PURPLE_PRIMARY + """;
}

.command-name {
    width: 100%;
    color: """ + PURPLE_BRIGHT + """;
    text-style: bold;
}

.command-description {
    width: 100%;
    color: """ + WHITE + """;
}

.command-shortcut {
    width: 100%;
    color: """ + GOLD + """;
}

#hint-bar {
    width: 100%;
    height: auto;
    padding: 1 0;
    color: """ + GRAY_DIM + """;
}
"""


# ============================================================================
# CommandPaletteScreen - 命令面板模态窗口
# ============================================================================

class CommandPaletteScreen(ModalScreen):
    """命令面板模态窗口

    提供命令搜索和执行功能，支持：
    - 模糊搜索命令
    - 键盘导航
    - 快捷键提示

    Messages:
        CommandExecuted: 命令执行事件
        PaletteClosed: 面板关闭事件
    """

    CSS = COMMAND_PALETTE_CSS

    # 命令执行消息
    class CommandExecuted(Message):
        """命令执行消息"""
        def __init__(self, sender: Widget, command: Command) -> None:
            super().__init__()
            self.command = command

    # 面板关闭消息
    class PaletteClosed(Message):
        """面板关闭消息"""
        pass

    def __init__(
        self,
        commands: list[Command] | None = None,
        key_binding_manager: Optional[object] = None,
        **kwargs
    ) -> None:
        """初始化命令面板

        Args:
            commands: 命令列表（如果为 None，使用默认命令）
            key_binding_manager: KeyBindingManager 实例，用于从快捷键绑定生成命令列表
            **kwargs: 传递给父类的参数
        """
        super().__init__(**kwargs)
        self._key_binding_manager = key_binding_manager
        self._commands = commands or self._get_default_commands()
        self._filtered_commands: list[Command] = self._commands.copy()
        self._selected_index: int = 0
        self._logger = get_access_logger("CommandPalette", sublayer="cli")

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
                formatted.append("Ctrl+")
            elif part == "shift":
                formatted.append("Shift+")
            elif part == "alt":
                formatted.append("Alt+")
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

        return "".join(formatted)

    def _get_default_commands(self) -> list[Command]:
        """获取默认命令列表

        Returns:
            默认命令列表
        """
        i18n = get_i18n()

        # 如果有 KeyBindingManager，从绑定生成命令列表
        if self._key_binding_manager is not None:
            return self._build_commands_from_bindings()

        return [
            Command(
                id="new_tab",
                name=i18n.t("tui.command.new_tab"),
                description=i18n.t("tui.command.new_tab_desc"),
                shortcut="Ctrl+T",
                action=lambda: self.app.post_message(self.CommandExecuted(
                    self, Command("", "", "", None)
                )),
                category="tab",
            ),
            Command(
                id="close_tab",
                name=i18n.t("tui.command.close_tab"),
                description=i18n.t("tui.command.close_tab_desc"),
                shortcut="Ctrl+W",
                action=lambda: self.app.post_message(self.CommandExecuted(
                    self, Command("", "", "", None)
                )),
                category="tab",
            ),
            Command(
                id="toggle_theme",
                name=i18n.t("tui.command.toggle_theme"),
                description=i18n.t("tui.command.toggle_theme_desc"),
                shortcut="",
                action=lambda: self.app.post_message(self.CommandExecuted(
                    self, Command("", "", "", None)
                )),
                category="appearance",
            ),
            Command(
                id="clear_screen",
                name=i18n.t("tui.command.clear_screen"),
                description=i18n.t("tui.command.clear_screen_desc"),
                shortcut="Ctrl+L",
                action=lambda: self.app.post_message(self.CommandExecuted(
                    self, Command("", "", "", None)
                )),
                category="view",
            ),
            Command(
                id="show_help",
                name=i18n.t("tui.command.show_help"),
                description=i18n.t("tui.command.show_help_desc"),
                shortcut="F1",
                action=lambda: self.app.post_message(self.CommandExecuted(
                    self, Command("", "", "", None)
                )),
                category="help",
            ),
            Command(
                id="quit",
                name=i18n.t("tui.command.quit"),
                description=i18n.t("tui.command.quit_desc"),
                shortcut="Ctrl+Q",
                action=lambda: self.app.post_message(self.CommandExecuted(
                    self, Command("", "", "", None)
                )),
                category="system",
            ),
            Command(
                id="settings",
                name=i18n.t("tui.command.settings"),
                description=i18n.t("tui.command.settings_desc"),
                shortcut="Ctrl+,",
                action=lambda: self.app.action_open_settings(),
                category="system",
            ),
        ]

    def _build_commands_from_bindings(self) -> list[Command]:
        """从 KeyBindingManager 的绑定生成命令列表

        将 KeyBindingManager 中的快捷键绑定与预定义 i18n 命令结合，
        保证显示正确的翻译名称，同时使用真实的 action 回调。

        Returns:
            从快捷键绑定构建的命令列表
        """
        i18n = get_i18n()

        # 预定义的 i18n 命令模板（确保正确的翻译）
        # 注意：F2 (settings) 不在 KeyBindingManager 中，仅在 app.BINDINGS 直接定义，
        # 所以不包含在此列表；用户仍可通过 Ctrl+, 快捷键触发设置。
        predefined = [
            ("ctrl+t", "new_tab"),
            ("ctrl+w", "close_tab"),
            ("ctrl+l", "clear_screen"),
            ("f1", "show_help"),
            ("ctrl+q", "quit"),
            ("q", "quit"),
        ]

        try:
            bindings = self._key_binding_manager.bindings
        except AttributeError:
            # 如果没有 bindings 属性，回退到默认命令
            return self._get_default_commands_fallback()

        # 建立 key -> binding 的映射
        key_to_binding = {b.key.lower(): b for b in bindings}

        commands = []
        for key, cmd_key in predefined:
            binding = key_to_binding.get(key.lower())
            if binding is None:
                continue

            name = i18n.t(f"tui.command.{cmd_key}")
            desc = i18n.t(f"tui.command.{cmd_key}_desc")
            shortcut = self._format_key(binding.key)

            commands.append(Command(
                id=binding.key,
                name=name,
                description=desc,
                shortcut=shortcut,
                action=binding.action,
                category=binding.category,
            ))

        return commands

        return commands

    def _get_default_commands_fallback(self) -> list[Command]:
        """回退的默认命令（当 KeyBindingManager 不可用时）"""
        i18n = get_i18n()
        return [
            Command(
                id="new_tab",
                name=i18n.t("tui.command.new_tab"),
                description=i18n.t("tui.command.new_tab_desc"),
                shortcut="Ctrl+T",
                action=lambda: self.app.post_message(self.CommandExecuted(
                    self, Command("", "", "", None)
                )),
                category="tab",
            ),
            Command(
                id="close_tab",
                name=i18n.t("tui.command.close_tab"),
                description=i18n.t("tui.command.close_tab_desc"),
                shortcut="Ctrl+W",
                action=lambda: self.app.post_message(self.CommandExecuted(
                    self, Command("", "", "", None)
                )),
                category="tab",
            ),
            Command(
                id="toggle_theme",
                name=i18n.t("tui.command.toggle_theme"),
                description=i18n.t("tui.command.toggle_theme_desc"),
                shortcut="",
                action=lambda: self.app.post_message(self.CommandExecuted(
                    self, Command("", "", "", None)
                )),
                category="appearance",
            ),
            Command(
                id="clear_screen",
                name=i18n.t("tui.command.clear_screen"),
                description=i18n.t("tui.command.clear_screen_desc"),
                shortcut="Ctrl+L",
                action=lambda: self.app.post_message(self.CommandExecuted(
                    self, Command("", "", "", None)
                )),
                category="view",
            ),
            Command(
                id="show_help",
                name=i18n.t("tui.command.show_help"),
                description=i18n.t("tui.command.show_help_desc"),
                shortcut="F1",
                action=lambda: self.app.post_message(self.CommandExecuted(
                    self, Command("", "", "", None)
                )),
                category="help",
            ),
            Command(
                id="quit",
                name=i18n.t("tui.command.quit"),
                description=i18n.t("tui.command.quit_desc"),
                shortcut="Ctrl+Q",
                action=lambda: self.app.post_message(self.CommandExecuted(
                    self, Command("", "", "", None)
                )),
                category="system",
            ),
            Command(
                id="settings",
                name=i18n.t("tui.command.settings"),
                description=i18n.t("tui.command.settings_desc"),
                shortcut="Ctrl+,",
                action=lambda: self.app.action_open_settings(),
                category="system",
            ),
        ]

    def compose(self) -> ComposeResult:
        """组合组件

        Returns:
            组件生成器
        """
        i18n = get_i18n()

        # 标题
        title = i18n.t("tui.command_palette.title")
        yield Static(
            f"[bold {PURPLE_BRIGHT}]⌘ {title}[/]",
            id="palette-title"
        )

        # 搜索输入
        placeholder = i18n.t("tui.command_palette.search_hint")
        yield Input(
            placeholder=placeholder,
            id="search-input"
        )

        # 命令列表
        yield ListView(id="command-list")

        # 提示栏
        hint_up = i18n.t("tui.command_palette.hint_up")
        hint_down = i18n.t("tui.command_palette.hint_down")
        hint_enter = i18n.t("tui.command_palette.hint_enter")
        hint_esc = i18n.t("tui.command_palette.hint_esc")
        yield Static(
            f"[{GRAY_DIM}]{hint_up} {hint_down} 导航  |  {hint_enter} 执行  |  {hint_esc} 关闭[/]",
            id="hint-bar"
        )

    def on_mount(self) -> None:
        """组件挂载时初始化"""
        self._logger.debug("Command palette mounted")

        # 设置焦点到搜索框
        input_widget = self.query_one("#search-input", Input)
        input_widget.focus()

        # 初始化命令列表
        self._update_command_list()

    def _update_command_list(self) -> None:
        """更新命令列表"""
        list_view = self.query_one("#command-list", ListView)

        # 获取搜索查询
        input_widget = self.query_one("#search-input", Input)
        query = input_widget.value

        # 过滤命令
        self._filtered_commands = [
            cmd for cmd in self._commands
            if cmd.matches(query)
        ]

        # 清空并重建列表
        list_view.clear()

        for command in self._filtered_commands:
            # 创建命令项（使用时间戳确保 ID 唯一）
            shortcut_display = f" [{PURPLE_BRIGHT}]{command.shortcut}[/{PURPLE_BRIGHT}]" if command.shortcut else ""
            item_content = (
                f"[{PURPLE_BRIGHT}]{command.name}[/{PURPLE_BRIGHT}]"
                f"[{GRAY_DIM}] - {command.description}[/{GRAY_DIM}]"
                f"[{GOLD}]{shortcut_display}[/{GOLD}]"
            )
            # 使用唯一 ID 避免重复打开时冲突
            # 注意：command.id 可能包含 "+" (如 "ctrl+t")，需要替换为 "_" 以符合 DOM ID 规范
            import time
            safe_id = command.id.replace("+", "_").replace(" ", "_")
            unique_id = f"cmd-{safe_id}-{int(time.time() * 1000) % 1000000}"
            item = ListItem(
                Static(item_content),
                id=unique_id
            )
            list_view.append(item)

        # 选择第一个命令
        self._selected_index = 0
        if self._filtered_commands:
            list_view.index = 0

    def _select_previous(self) -> None:
        """选择上一个命令"""
        list_view = self.query_one("#command-list", ListView)
        if list_view.index is not None and list_view.index > 0:
            list_view.index -= 1
            self._selected_index = list_view.index

    def _select_next(self) -> None:
        """选择下一个命令"""
        list_view = self.query_one("#command-list", ListView)
        max_index = len(self._filtered_commands) - 1
        if list_view.index is not None and list_view.index < max_index:
            list_view.index += 1
            self._selected_index = list_view.index

    def _execute_selected(self) -> None:
        """执行选中的命令"""
        if not self._filtered_commands:
            return

        selected = self._filtered_commands[self._selected_index]
        self._logger.info(f"Executing command: {selected.name}")

        # 执行命令
        try:
            selected.action()
        except Exception as e:
            self._logger.error(f"Error executing command {selected.id}: {e}")

        # 发送执行消息
        self.post_message(self.CommandExecuted(self, selected))

        # 关闭面板
        self._close()

    def _close(self) -> None:
        """关闭面板"""
        self._logger.debug("Closing command palette")
        self.post_message(self.PaletteClosed())
        self.app.pop_screen()

    def on_input_changed(self, event: Input.Changed) -> None:
        """搜索框内容变化时更新列表"""
        if event.input.id == "search-input":
            self._update_command_list()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """搜索框提交时执行命令"""
        if event.input.id == "search-input":
            self._execute_selected()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """列表项选中时执行命令"""
        self._execute_selected()

    def on_key(self, event: "Input.Key") -> None:
        """处理键盘事件"""
        key = event.key

        # 上方向键或 k
        if key in ("up", "k"):
            self._select_previous()
            event.prevent_default()

        # 下方向键或 j
        elif key in ("down", "j"):
            self._select_next()
            event.prevent_default()

        # 回车
        elif key == "enter":
            self._execute_selected()
            event.prevent_default()

        # Esc
        elif key == "escape":
            self._close()
            event.prevent_default()


# ============================================================================
# 模块导出
# ============================================================================

__all__ = [
    "Command",
    "CommandPaletteScreen",
]