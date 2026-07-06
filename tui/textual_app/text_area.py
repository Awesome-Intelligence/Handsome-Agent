#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TextArea 组件模块

提供支持按 Enter 发送消息的 TextArea 子类。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from textual import events as textual_events

# 条件导入 Textual 组件
try:
    from textual.widgets import TextArea
    from textual.message import Message
except ImportError:
    TextArea = None
    Message = object


class SubmitTextArea(TextArea):
    """支持按 Enter 发送消息的 TextArea。

    - Enter（无修饰键）：触发 Submitted 事件（不插入换行）
    - Ctrl+Enter：插入换行（默认行为）
    - Up / Down：在合适时机触发历史导航回调

    内部使用自定义的 InputSubmitted 消息事件。
    """

    # 不显式绑定 ctrl+enter，让 TextArea 内置的 Ctrl+Enter 换行行为自然生效
    # Enter 提交逻辑在 _on_key 中通过 key == "enter" 处理

    class InputSubmitted(Message):
        """输入提交事件（按 Enter 触发）。"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 历史导航回调：参数为方向，-1 表示向上（更早的历史），
        # 1 表示向下（更新的历史或还原当前输入）
        self.history_navigate: Callable[[int], None] | None = None
        # 是否启用历史导航（默认开启）
        self.history_navigation_enabled: bool = True

    async def _on_key(self, event: "textual_events.Key") -> None:
        """拦截 Enter 键与上下方向键。

        - 无修饰键的 Enter：触发提交
        - 带修饰键的 Enter：保持默认（插入换行）
        - Up / Down：在合适的边界位置触发历史导航

        Args:
            event: 键盘事件
        """
        key = event.key

        # Enter without modifiers -> submit message
        # Textual 中修饰键编码在 key 字符串中：plain="enter", ctrl+enter="ctrl+enter"
        if key == "enter":
            event.stop()
            event.prevent_default()
            self.post_message(self.InputSubmitted())
            return

        # Ctrl+Enter / Shift+Enter / Alt+Enter -> insert newline (default behavior)
        # 这些 key 字符串包含 '+' 修饰符前缀
        if (
            key.startswith("ctrl+")
            or key.startswith("shift+")
            or key.startswith("alt+")
        ):
            await super()._on_key(event)
            return

        # Up / Down：仅在合适位置触发历史导航，其余交由默认行为
        if (
            self.history_navigation_enabled
            and self.history_navigate is not None
            and key in ("up", "down")
        ):
            direction = -1 if key == "up" else 1
            if self._should_navigate_history(direction):
                event.stop()
                event.prevent_default()
                self.history_navigate(direction)
                return

        # 其他键保持默认行为
        await super()._on_key(event)

    def _should_navigate_history(self, direction: int) -> bool:
        """判断当前光标位置是否应该处理历史导航。

        单行输入：始终返回 True。
        多行输入：仅当光标位于首行（向上）或末行（向下）时返回 True，
        其余情况让默认行为接管（用于多行内移动光标）。

        Args:
            direction: -1 表示向上，1 表示向下

        Returns:
            True 表示应该拦截此方向键进行历史导航
        """
        text = self.text
        # 空内容或单行内容：直接交给历史导航
        if not text or "\n" not in text:
            return True

        try:
            line_count = self.document.line_count
            row, _ = self.cursor_location
        except (AttributeError, TypeError):
            return True

        if direction < 0:  # up
            return row == 0
        # down
        return row >= line_count - 1
