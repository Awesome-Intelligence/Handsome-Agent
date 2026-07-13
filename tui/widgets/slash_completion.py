#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Slash Command Completion List

🚪 Access - 💬 CLI - TUI Widgets - SlashCompletionList

浮动在输入框下方的斜杠命令补全列表，按 Tab 插入选中命令。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from textual.widgets import ListView as LV

from textual.widgets import ListView, ListItem, Static

try:
    from rich.text import Text
except ImportError:
    Text = None

# 主题色
_SLASH_CMD_COLOR = "#C9A0E0"  # 高雅紫


class SlashCompletionList(ListView):
    """斜杠命令补全浮动列表。

    交互：
    - ↑↓：在列表内导航
    - Tab：插入当前选中命令
    - Esc：关闭列表
    - 点击列表外：关闭列表

    属性：
        on_complete: (command: str) -> None，选中命令后的回调
        on_dismiss: () -> None，列表关闭时的回调
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.on_complete: callable | None = None
        self.on_dismiss: callable | None = None
        self._commands: list[tuple[str, dict]] = []

    def filter_commands(self, query: str) -> None:
        """根据 query 过滤命令并更新列表。

        Args:
            query: 用户输入（以 / 开头）
        """
        if not query.startswith("/"):
            self._set_items([])
            return

        raw_query = query.lstrip("/")
        try:
            from agent.skill_commands import get_skill_commands

            all_cmds = get_skill_commands()
        except Exception:
            all_cmds = {}

        # ponytail: 简单 startswith 匹配，正式场景可换 rapidfuzz
        self._commands = [
            (name, info)
            for name, info in all_cmds.items()
            if raw_query in name.lstrip("/")
        ]
        self._commands.sort(key=lambda x: x[0])
        self._set_items(self._commands)

    def _set_items(self, commands: list[tuple[str, dict]]) -> None:
        """更新列表项。"""
        self.clear()
        if not commands:
            self.set_class(False, "visible")
            return

        self.set_class(True, "visible")
        for cmd, info in commands[:8]:  # 最多 8 条
            desc = info.get("description", "")[:40]
            label = Text.from_markup(
                f"[bold {_SLASH_CMD_COLOR}]{cmd}[/]  [dim]{desc}[/]"
            )
            self.append(ListItem(Static(label, markup=True), id=cmd))

        self.index = 0

    def insert_selected(self) -> str | None:
        """插入当前选中项的命令名。

        Returns:
            选中的命令名，或 None
        """
        if self.index is None or self.index < 0 or self.index >= len(self._commands):
            return None
        cmd, _ = self._commands[self.index]
        if callable(self.on_complete):
            self.on_complete(cmd)
        return cmd

    def dismiss(self) -> None:
        """关闭补全列表（不清除 on_dismiss 回调，调用者负责）。"""
        self._set_items([])
        self.set_class(False, "visible")
