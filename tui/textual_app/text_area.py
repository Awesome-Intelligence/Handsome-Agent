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
        # 斜杠命令补全回调
        self.slash_show: Callable[[], None] | None = None
        self.slash_update: Callable[[str], None] | None = None
        self.slash_complete: Callable[[], str | None] | None = None
        self.slash_dismiss: Callable[[], None] | None = None
        # 记录当前 / 触发时的快照（文本 + 光标位置）
        self._slash_snapshot: tuple[str, tuple[int, int]] | None = None

    async def _on_key(self, event: "textual_events.Key") -> None:
        """拦截 Enter 键与上下方向键。

        - 无修饰键的 Enter：触发提交
        - 带修饰键的 Enter：保持默认（插入换行）
        - Up / Down：在合适的边界位置触发历史导航
        - Tab：触发斜杠命令补全确认（当 slash_completion 激活时）

        Args:
            event: 键盘事件
        """
        key = event.key

        # DEBUG
        print(f"[_on_key] key={repr(key)} slash_show={self.slash_show} text={repr(self.text[:20])}")

        # Tab：确认斜杠命令补全
        if key == "tab" and self.slash_complete is not None:
            result = self.slash_complete()
            if result:
                event.stop()
                return
            # 没有选中项时继续默认行为（不插入\t）

        # Esc：关闭斜杠补全浮层
        if key == "escape" and self.slash_dismiss is not None:
            self.slash_dismiss()
            # 不 stop，让 Esc 继续（TextArea 自己的 esc 行为）

        # 检测 / 键：第一次按下时触发补全浮层
        if key == "/" and self.slash_show is not None:
            print(f"[/] triggering slash_show, text={repr(self.text)}, cursor={self.cursor_location}")
            self._slash_snapshot = (self.text, self.cursor_location)
            self.slash_show()
            print(f"[/] after slash_show, _slash_snapshot={self._slash_snapshot}")
            # 让默认行为插入 /

        # 检测普通可打印字符：更新补全过滤
        # Textual 的 key 事件中，普通字符 key 就是那个字符本身
        if (
            self.slash_update is not None
            and self._slash_snapshot is not None
            and len(key) == 1
            and key.isprintable()
            and not key.isspace()
        ):
            # 插入后更新过滤
            self.update_from_slash_query()

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

    def update_from_slash_query(self) -> None:
        """根据快照重建 /query 并触发过滤更新。"""
        if self._slash_snapshot is None or self.slash_update is None:
            return
        snapshot_text, _ = self._slash_snapshot
        # 快照之后新增的文本（/ 及其之后用户输入的内容）
        query = self.text[len(snapshot_text) :]
        if not query.startswith("/"):
            if self.slash_dismiss:
                self.slash_dismiss()
            return
        self.slash_update(query)

    def _on_blur(self, event: "textual_events.Blurred") -> None:
        """输入框丢失焦点时关闭补全浮层。"""
        if self.slash_dismiss:
            self.slash_dismiss()
        self._slash_snapshot = None
        super()._on_blur(event)
