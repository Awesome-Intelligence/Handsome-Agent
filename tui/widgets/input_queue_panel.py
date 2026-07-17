#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Input Queue Floating Panel

🚪 Access - 💬 CLI - TUI Widgets - InputQueuePanel

悬浮在 statusbar 上方的输入队列列表面板，实时显示排队中的用户消息。
支持单条删除和清空全部操作。
"""

from __future__ import annotations

import logging
from collections import deque
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from textual.widgets import ListView as LV, ListItem as LI

from textual.widgets import ListView, ListItem, Static
from textual.containers import Container, Horizontal
from textual import on
from textual.events import Click

try:
    from rich.text import Text
except ImportError:
    Text = None


logger = logging.getLogger(__name__)


class QueueDeleteClicked:
    """删除单项事件（简单数据对象，非 Textual Message，用于回调）。"""

    def __init__(self, index: int):
        self.index = index


class QueueClearAllClicked:
    """清空全部事件。"""

    pass


class InputQueuePanel(Container):
    """悬浮式输入队列面板。

    特性：
    - 队列长度 > 0 时自动展开显示（.has-queue class）
    - 无标题行，无边框
    - 宽度 100% 全屏，背景色跟随主题（$surface）
    - 每个队列项：⏳ 排队提示符 + 内容预览 + 删除按钮 ×
    - 无底部操作栏，仅支持单项删除
    """

    DEFAULT_CSS = ""  # 样式集中在 tui/textual_app/css/input_queue.py

    def __init__(self, **kwargs):
        super().__init__(id="input-queue-panel", **kwargs)
        self.on_delete: Optional[Callable[[int], None]] = None
        self.on_clear_all: Optional[Callable[[], None]] = None
        self._queue_ref: Optional[deque] = None
        self._max_content_preview = 60

    def bind_queue(self, queue_ref: deque) -> None:
        """绑定外部队列引用（AgentApp._pending_queue）。"""
        self._queue_ref = queue_ref

    def set_callbacks(
        self,
        on_delete: Optional[Callable[[int], None]] = None,
        on_clear_all: Optional[Callable[[], None]] = None,
    ) -> None:
        """设置回调函数。"""
        self.on_delete = on_delete
        self.on_clear_all = on_clear_all

    def refresh_from_queue(self, queue_len: int) -> None:
        """根据外部队列状态刷新面板内容。

        必须通过 call_next 调用以避免布局计算期 height=0 问题。
        """
        try:
            if queue_len > 0:
                self.set_class(True, "has-queue")
                self._rebuild_items()
            else:
                self.set_class(False, "has-queue")
                list_view = self.query_one("#queue-list", ListView)
                list_view.clear()
        except Exception as e:
            logger.debug(f"Failed to refresh queue panel: {e}")

    def _rebuild_items(self) -> None:
        """根据绑定的 deque 重建所有 ListItem（仅队列项，无底部操作栏）。"""
        if self._queue_ref is None:
            return
        try:
            list_view = self.query_one("#queue-list", ListView)
        except Exception:
            return

        list_view.clear()
        items = list(self._queue_ref)

        for idx, content in enumerate(items):
            list_view.mount(self._build_queue_item(idx, content))

    def _build_queue_item(self, index: int, content: str) -> ListItem:
        """构建单个队列项 ListItem（⏳ 提示符 + 内容 + 删除按钮，无序号）。

        Args:
            index: 在队列中的索引，用于删除按钮的 id 绑定（用户不可见）
            content: 队列消息内容
        """
        if len(content) > self._max_content_preview:
            display_content = content[: self._max_content_preview] + "..."
        else:
            display_content = content
        # 排队提示符：⏳ 内容...
        prefixed_content = f"⏳ {display_content}"

        if Text is not None:
            content_text = Text(prefixed_content)
            delete_text = Text(" ×")
        else:
            content_text = prefixed_content
            delete_text = " ×"

        item = ListItem(
            Horizontal(
                Static(content_text, classes="queue-content"),
                Static(
                    delete_text,
                    classes="queue-delete",
                    id=f"queue-delete-{index}",
                ),
                classes="queue-item-row",
            ),
            classes="queue-item",
        )
        return item

    @on(Click, ".queue-delete")
    def _on_delete_click(self, event: Click) -> None:
        """点击单项删除按钮。"""
        try:
            widget_id = getattr(event.control, "id", "") or ""
            if widget_id.startswith("queue-delete-"):
                idx_str = widget_id[len("queue-delete-"):]
                idx = int(idx_str)
                if callable(self.on_delete):
                    self.on_delete(idx)
        except Exception as e:
            logger.debug(f"Queue delete click failed: {e}")

    def compose(self):
        yield ListView(id="queue-list")
