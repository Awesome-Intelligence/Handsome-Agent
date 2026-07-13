#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChatContainer - 聊天消息列表容器（oterm 风格）

🚪 Access - 💬 TUI - Widgets - ChatContainer

参考 E:\\oterm-study\\src\\oterm\\app\\widgets\\chat.py 的 ChatContainer：

- 内部用 ``VerticalScroll#messageContainer`` 挂载多条 ``ChatItem``。
- 每条消息一个 ChatItem，DOM 跟随消息对象走，**不再维护 5 个并行字典**。
- 提供对上层 app.py 兼容的流式接口：
  ``start_streaming`` / ``append_streaming_text`` / ``append_streaming_thinking``
  / ``complete_streaming`` / ``cancel_streaming``。
- 滚动跟随走 ``call_after_refresh``，避免 on_scroll 与 is_attached 的手写
  dance。

设计要点（与 oterm 一致）：

- ChatItem 的 ``author`` / ``text`` / ``tool_name`` 是 reactive，
  都在 mount **之前**赋值；watcher 在 mount 后触发，对应子 widget
  完成首次渲染（assistant 的 Markdown 由 watch_text 写入）。
- mount 是 fire-and-forget；流式追加时若 query_one 因未挂载而抛 NoMatches，
  直接跳过本 delta，下一 delta 时机通常已挂载完成。
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from typing import Any

from textual.containers import VerticalScroll
from textual.css.query import NoMatches
from textual.widget import Widget
from textual.widgets import Markdown

from common.logging_manager import get_access_logger
from tui.widgets.chat_item import Author, ChatItem

# 自动跟随流式输出时的窗口阈值（行）。小一点让"用户滚到中段"时也能继续跟。
_SCROLL_FOLLOW_THRESHOLD = 2

# 消息列表允许保留的最大消息数；超出后从顶端裁剪。
_MAX_MESSAGES = 80


def _near_bottom(container: VerticalScroll) -> bool:
    return container.max_scroll_y - container.scroll_y <= _SCROLL_FOLLOW_THRESHOLD


class ChatContainer(Widget, can_focus=False):
    """聊天消息列表容器。"""

    # ponytail: 原先是 reactive[list]，但全文无 watch_messages 订阅，每轮
    # reactive 状态机调用 + ≤200 dict 的列表复制是纯浪费。降级为普通 list。
    messages: list[dict[str, Any]]

    DEFAULT_CSS = """
    ChatContainer {
        width: 100%;
        height: 1fr;
        background: transparent;
        padding: 1 2;
    }

    #messageContainer {
        width: 100%;
        height: 100%;
        scrollbar-gutter: stable;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._logger = get_access_logger("ChatContainer", sublayer="tui")
        self._streaming_item: ChatItem | None = None
        self._items: list[ChatItem] = []
        self.messages = []

    def compose(self) -> Iterable[Widget]:
        yield VerticalScroll(id="messageContainer")

    def _get_message_container(self) -> VerticalScroll:
        return self.query_one("#messageContainer", VerticalScroll)

    # ------------------------------------------------------------------
    # 消息管理（同步入口；mount 是 fire-and-forget）
    # ------------------------------------------------------------------

    def add_message(
        self,
        role: str,
        content: str,
        *,
        tool_name: str | None = None,
    ) -> str:
        """添加一条已完成的非流式消息。

        Args:
            role: 角色，取 ``Author`` 字面量之一。
            content: 文本内容。
            tool_name: 仅 role="tool" 时使用，渲染为头部标签。

        Returns:
            新建 ChatItem 的 id。
        """
        item = ChatItem()
        item.author = (
            role
            if role in ("user", "assistant", "system", "tool", "error")
            else "assistant"
        )
        item.text = content
        if tool_name:
            item.tool_name = tool_name
        # fire-and-forget mount；watcher 在 mount 之后异步触发首屏渲染。
        self._get_message_container().mount(item)
        self._items.append(item)
        self.messages = self.messages + [
            {"role": role, "content": content, "tool_name": tool_name}
        ]
        self._schedule_follow_scroll()
        self._trim()
        return item.id or ""

    def add_user_message(self, content: str) -> str:
        return self.add_message("user", content)

    def add_assistant_message(self, content: str) -> str:
        return self.add_message("assistant", content)

    def add_system_message(self, content: str) -> str:
        return self.add_message("system", content)

    def add_tool_message(self, content: str, tool_name: str) -> str:
        return self.add_message("tool", content, tool_name=tool_name)

    def add_error_message(self, content: str) -> str:
        return self.add_message("error", content)

    def append_message(
        self,
        role: str,
        content: str,
        *,
        tool_name: str | None = None,
    ) -> str:
        return self.add_message(role, content, tool_name=tool_name)

    def add_thinking_message(self, content: str) -> str:
        """追加一段独立的思考块（非流式）。

        实现：挂一条 assistant ChatItem 但保持 ``text`` 为空，
        思考内容直接通过 watcher 写入 thinking-body。
        """
        item = ChatItem()
        item.author = "assistant"
        item.thinking = content
        self._get_message_container().mount(item)
        self._items.append(item)
        self._schedule_follow_scroll()
        self._trim()
        return item.id or ""

    def clear_messages(self) -> None:
        """清空所有消息并重置流状态。"""
        self._cancel_current_stream()
        # ponytail: batch_update 把 N 次独立 remove 合并为 1 次 layout pass，
        # 不然会话切换时 200 个 child 各自触发 PostMessage + ancestor 失效。
        container = self._get_message_container()
        app = self.app or container.app
        with app.batch_update():
            for child in list(container.children):
                child.remove()
        self._items.clear()
        self.messages = []

    # ------------------------------------------------------------------
    # 流式接口（兼容 app.py 调用）
    # ------------------------------------------------------------------

    def start_streaming(self, role: str = "assistant") -> str:
        """开始一条新的流式消息。

        Args:
            role: 消息角色。

        Returns:
            ChatItem id。
        """
        item = ChatItem()
        item.author = (
            role
            if role in ("user", "assistant", "system", "tool", "error")
            else "assistant"
        )
        self._get_message_container().mount(item)
        self._items.append(item)
        self._streaming_item = item
        self._trim()
        return item.id or ""

    def append_streaming_text(self, text: str) -> None:
        """追加流式回复文本。

        同步入口；通过 ``asyncio.create_task`` 把 coroutine 切到事件循环里
        —— 同步入口也能驱动 async 的 ``MarkdownStream.write``。
        """
        if not self._streaming_item or not text:
            return
        follow = _near_bottom(self._get_message_container())
        asyncio.create_task(self._do_append_text(self._streaming_item, text))
        if follow:
            self._schedule_follow_scroll()

    def append_streaming_thinking(self, text: str) -> None:
        """追加流式思考内容。

        若流尚未开始（thinking 比回答先到），自动开一条 assistant 流。
        """
        if not text:
            return
        if self._streaming_item is None:
            self.start_streaming("assistant")
        if self._streaming_item is None:
            return
        asyncio.create_task(self._do_append_thinking(self._streaming_item, text))

    async def _do_append_text(self, item: ChatItem, text: str) -> None:
        try:
            await item.append_text(text)
        except Exception as exc:  # pragma: no cover —— 防御性
            self._logger.warning(f"append_text failed: {exc}")

    async def _do_append_thinking(self, item: ChatItem, text: str) -> None:
        try:
            await item.append_thinking(text)
        except Exception as exc:  # pragma: no cover
            self._logger.warning(f"append_thinking failed: {exc}")

    def complete_streaming(self) -> str | None:
        """结束当前流。返回被收尾的 ChatItem id。"""
        item = self._streaming_item
        if item is None:
            return None
        self._streaming_item = None
        asyncio.create_task(self._finish_item(item))
        self.messages = self.messages + [
            {"role": item.author, "content": item.text, "tool_name": None}
        ]
        self._schedule_follow_scroll()
        return item.id

    async def _finish_item(self, item: ChatItem) -> None:
        try:
            await item.finish_stream()
        except Exception as exc:  # pragma: no cover —— 防御性
            self._logger.warning(f"finish_stream failed: {exc}")

    def cancel_streaming(self) -> None:
        """取消当前流。"""
        self._cancel_current_stream()

    def _cancel_current_stream(self) -> None:
        item = self._streaming_item
        if item is None:
            return
        self._streaming_item = None
        try:
            item.cancel_streams()
        except Exception as exc:  # pragma: no cover
            self._logger.warning(f"cancel_streams failed: {exc}")
        # 把不完整的 ChatItem 直接从 DOM 移除，与 oterm 的错误路径一致。
        try:
            item.remove()
        except Exception:
            pass
        if item in self._items:
            self._items.remove(item)

    # ------------------------------------------------------------------
    # RichLog 兼容（app.py 中部分 fallback 路径仍调用 write/clear）
    # ------------------------------------------------------------------

    def write(self, text: str) -> None:
        """兼容 RichLog.write：把整段视为 assistant 最终输出。"""
        self.add_assistant_message(text)

    def clear(self) -> None:
        """兼容 RichLog.clear。"""
        self.clear_messages()

    # ------------------------------------------------------------------
    # 历史与查询
    # ------------------------------------------------------------------

    def get_messages(self) -> list[dict[str, Any]]:
        """以 dict 列表返回当前消息快照（供 app.py 重建会话等用）。"""
        return list(self.messages)

    def is_streaming(self) -> bool:
        return self._streaming_item is not None

    def scroll_to_bottom(self) -> None:
        self._schedule_follow_scroll()

    def _schedule_follow_scroll(self) -> None:
        self._get_message_container().call_after_refresh(
            lambda: self._get_message_container().scroll_end()
        )

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    def _trim(self) -> None:
        """超出上限时移除最老的非流式 ChatItem。"""
        if len(self._items) <= _MAX_MESSAGES:
            return
        to_remove: list[ChatItem] = []
        for item in self._items:
            if item is self._streaming_item:
                continue
            to_remove.append(item)
            if len(self._items) - len(to_remove) <= _MAX_MESSAGES:
                break
        for item in to_remove:
            try:
                item.remove()
            except Exception:
                pass
            if item in self._items:
                self._items.remove(item)

    async def action_clear_chat(self) -> None:
        """绑快捷键时使用。"""
        self.clear_messages()


__all__ = ["ChatContainer"]
