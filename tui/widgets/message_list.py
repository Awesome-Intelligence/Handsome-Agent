#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MessageList Widget - 消息列表组件

🚪 Access - 💬 CLI - TUI Widgets - MessageList

使用 VerticalScroll + Markdown 实现富文本消息显示，支持：
- 用户消息、助手消息、系统消息、工具消息
- 流式输出（打字机效果）
- 思考内容显示
- 错误消息高亮
- 自动滚动
- 历史消息数量限制
- 鼠标文本选择
- Markdown 渲染
"""

from __future__ import annotations

from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import time

TEXTUAL_AVAILABLE = True
try:
    from textual.widgets import Markdown, Static
    from textual.containers import VerticalScroll
    from textual.message import Message
except ImportError:
    TEXTUAL_AVAILABLE = False
    Markdown = object  # type: ignore
    Static = object  # type: ignore
    VerticalScroll = object  # type: ignore
    Message = object  # type: ignore

try:
    from tui.theming import MESSAGE_ICONS, MESSAGE_COLORS
except ImportError:
    MESSAGE_ICONS = {
        "USER": "🧑",
        "ASSISTANT": "🤖",
        "SYSTEM": "⚙️",
        "TOOL": "🔧",
        "ERROR": "❌",
        "THINKING": "💭",
        "APPROVAL": "✅",
    }
    MESSAGE_COLORS = {
        "USER": "#58a6ff",
        "ASSISTANT": "#3fb950",
        "SYSTEM": "#8b949e",
        "TOOL": "#a371f7",
        "ERROR": "#f85149",
        "THINKING": "#f0883e",
        "APPROVAL": "#3fb950",
    }

try:
    from common.i18n import get_i18n
except ImportError:
    def get_i18n():
        class SimpleI18n:
            def t(self, key, default=None, **kwargs):
                return default or key
        return SimpleI18n()

try:
    from common.logging_manager import get_access_logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    def get_access_logger(*args, **kwargs):
        return logging.getLogger("HandsomeAgent")


# ============================================================================
# 主题颜色常量
# ============================================================================

AVOCADO_PRIMARY = "#B180D7"
AVOCADO_BRIGHT = "#C9A0E0"
AVOCADO_DIM = "#8B5CAC"
AVOCADO_DARK = "#6B4EA8"
COLOR_SUCCESS = "#4CAF50"
COLOR_WARNING = "#FF9800"
COLOR_DANGER = "#F44336"
COLOR_INFO = "#2196F3"
WHITE = "white"
GRAY_DIM = "#888888"
GRAY_LIGHT = "#AAAAAA"
SURFACE = "#1a1a1a"


# ============================================================================
# 消息类型枚举
# ============================================================================

class MessageRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"
    ERROR = "error"
    THINKING = "thinking"


# ============================================================================
# 消息数据结构
# ============================================================================

@dataclass
class MessageItem:
    id: str
    role: MessageRole
    content: str
    timestamp: float = field(default_factory=time.time)
    tool_name: Optional[str] = None
    is_streaming: bool = False
    is_complete: bool = True

    @property
    def time_str(self) -> str:
        return datetime.fromtimestamp(self.timestamp).strftime("%H:%M:%S")


# ============================================================================
# 消息事件
# ============================================================================

class MessageListUpdated(Message):
    def __init__(self, sender, message_count: int) -> None:
        super().__init__()
        self.message_count = message_count


class StreamingComplete(Message):
    def __init__(self, sender, message_id: str) -> None:
        super().__init__()
        self.message_id = message_id


# ============================================================================
# MessageList Widget
# ============================================================================

class MessageList(VerticalScroll if TEXTUAL_AVAILABLE else object):
    """消息列表组件 - 使用 VerticalScroll + Markdown 实现"""

    def __init__(
        self,
        max_messages: int = 100,
        auto_scroll: bool = True,
        show_timestamps: bool = True,
        show_role_icons: bool = True,
        streaming_throttle_ms: int = 50,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)

        self.max_messages = max_messages
        self.auto_scroll = auto_scroll
        self.show_timestamps = show_timestamps
        self.show_role_icons = show_role_icons
        self.streaming_throttle_ms = streaming_throttle_ms

        self._messages: list[MessageItem] = []
        self._message_counter = 0
        self._streaming_active: dict[str, str] = {}
        self._last_streaming_update: dict[str, float] = {}
        self._message_widgets: dict[str, Static | Markdown] = {}
        self._logger = get_access_logger("MessageList", sublayer="tui")

    # ========================================================================
    # 消息添加方法
    # ========================================================================

    def add_message(
        self,
        role: str | MessageRole,
        content: str,
        tool_name: Optional[str] = None,
        timestamp: Optional[float] = None,
    ) -> str:
        if isinstance(role, str):
            role_enum = self._str_to_role(role)
        else:
            role_enum = role

        self._message_counter += 1
        msg_id = f"msg-{self._message_counter}"

        msg = MessageItem(
            id=msg_id,
            role=role_enum,
            content=content,
            timestamp=timestamp or time.time(),
            tool_name=tool_name,
            is_streaming=False,
            is_complete=True,
        )

        self._messages.append(msg)
        self._trim_messages()

        self._render_message(msg)
        self._post_message(MessageListUpdated(self, len(self._messages)))

        return msg_id

    def add_user_message(self, content: str) -> str:
        return self.add_message(MessageRole.USER, content)

    def add_assistant_message(self, content: str) -> str:
        return self.add_message(MessageRole.ASSISTANT, content)

    def add_system_message(self, content: str) -> str:
        return self.add_message(MessageRole.SYSTEM, content)

    def add_tool_message(self, content: str, tool_name: str) -> str:
        return self.add_message(MessageRole.TOOL, content, tool_name=tool_name)

    def add_error_message(self, content: str) -> str:
        return self.add_message(MessageRole.ERROR, content)

    def add_thinking_message(self, content: str) -> str:
        return self.add_message(MessageRole.THINKING, content)

    # ========================================================================
    # 流式输出方法
    # ========================================================================

    def start_streaming(self, role: str | MessageRole, content: str = "") -> str:
        if isinstance(role, str):
            role_enum = self._str_to_role(role)
        else:
            role_enum = role

        self._message_counter += 1
        msg_id = f"msg-{self._message_counter}"

        msg = MessageItem(
            id=msg_id,
            role=role_enum,
            content=content,
            timestamp=time.time(),
            is_streaming=True,
            is_complete=False,
        )

        self._messages.append(msg)
        self._streaming_active[msg_id] = role_enum.value
        self._trim_messages()

        self._render_message(msg)
        return msg_id

    def append_streaming_text(self, message_id: str, text: str) -> None:
        if message_id not in self._streaming_active:
            return

        current_time = time.time() * 1000
        last_update = self._last_streaming_update.get(message_id, 0)
        if current_time - last_update < self.streaming_throttle_ms:
            return

        self._last_streaming_update[message_id] = current_time

        for msg in self._messages:
            if msg.id == message_id:
                msg.content += text
                self._update_message_widget(msg)
                break

    def append_streaming_thinking(self, message_id: str, text: str) -> None:
        if message_id not in self._streaming_active:
            return

        thinking_id = f"{message_id}-thinking"
        thinking_msg = None
        for msg in self._messages:
            if msg.id == thinking_id:
                thinking_msg = msg
                break

        if thinking_msg:
            thinking_msg.content += text
        else:
            self._message_counter += 1
            thinking_msg = MessageItem(
                id=thinking_id,
                role=MessageRole.THINKING,
                content=text,
                timestamp=time.time(),
                is_streaming=True,
                is_complete=False,
            )
            self._messages.append(thinking_msg)

        self._render_or_update_message(thinking_msg)

    def complete_streaming(self, message_id: str) -> None:
        if message_id not in self._streaming_active:
            return

        for msg in self._messages:
            if msg.id == message_id:
                msg.is_streaming = False
                msg.is_complete = True
                self._upgrade_to_markdown(msg)
                break

        thinking_id = f"{message_id}-thinking"
        for msg in self._messages:
            if msg.id == thinking_id:
                msg.is_streaming = False
                msg.is_complete = True
                self._upgrade_to_markdown(msg)
                break

        del self._streaming_active[message_id]
        if message_id in self._last_streaming_update:
            del self._last_streaming_update[message_id]

        self._post_message(StreamingComplete(self, message_id))

    # ========================================================================
    # 消息操作方法
    # ========================================================================

    def update_message(self, message_id: str, content: str) -> None:
        for msg in self._messages:
            if msg.id == message_id:
                msg.content = content
                self._update_message_widget(msg)
                break

    def remove_message(self, message_id: str) -> bool:
        for i, msg in enumerate(self._messages):
            if msg.id == message_id:
                self._messages.pop(i)
                if msg.id in self._message_widgets:
                    widget = self._message_widgets[msg.id]
                    widget.remove()
                    del self._message_widgets[msg.id]
                self._post_message(MessageListUpdated(self, len(self._messages)))
                return True
        return False

    def clear_messages(self) -> None:
        self._messages.clear()
        self._streaming_active.clear()
        self._last_streaming_update.clear()
        for widget in self._message_widgets.values():
            widget.remove()
        self._message_widgets.clear()
        self._post_message(MessageListUpdated(self, 0))

    def get_messages(self) -> list[MessageItem]:
        return self._messages.copy()

    def scroll_to_bottom(self) -> None:
        self.scroll_end(animate=True)

    # ========================================================================
    # 内部方法
    # ========================================================================

    def _str_to_role(self, role_str: str) -> MessageRole:
        role_map = {
            "user": MessageRole.USER,
            "assistant": MessageRole.ASSISTANT,
            "system": MessageRole.SYSTEM,
            "tool": MessageRole.TOOL,
            "error": MessageRole.ERROR,
            "thinking": MessageRole.THINKING,
        }
        return role_map.get(role_str.lower(), MessageRole.ASSISTANT)

    def _trim_messages(self) -> None:
        if len(self._messages) > self.max_messages:
            excess = len(self._messages) - self.max_messages
            removed = 0
            for i in range(len(self._messages)):
                if removed >= excess:
                    break
                msg = self._messages[i]
                if msg.id not in self._streaming_active:
                    self._messages.pop(i)
                    if msg.id in self._message_widgets:
                        widget = self._message_widgets[msg.id]
                        widget.remove()
                        del self._message_widgets[msg.id]
                    removed += 1
                    i -= 1

    def _format_message_header(self, msg: MessageItem) -> str:
        msg_type = msg.role.value.upper()
        icon = MESSAGE_ICONS.get(msg_type, "💬")

        role_labels = {
            MessageRole.USER: "我",
            MessageRole.ASSISTANT: "助手",
            MessageRole.SYSTEM: "系统",
            MessageRole.TOOL: f"工具({msg.tool_name})" if msg.tool_name else "工具",
            MessageRole.ERROR: "错误",
            MessageRole.THINKING: "思考",
        }
        role_label = role_labels.get(msg.role, "")

        if self.show_timestamps:
            return f"{icon} **{role_label}** {msg.time_str}\n\n"
        return f"{icon} **{role_label}**\n\n"

    def _format_message_content(self, msg: MessageItem) -> str:
        content = msg.content

        if msg.is_streaming:
            content += " ▌"

        return content

    def _render_message(self, msg: MessageItem) -> None:
        header = self._format_message_header(msg)
        content = self._format_message_content(msg)
        full_content = header + content

        if msg.role == MessageRole.SYSTEM:
            widget = Static(f"--- {msg.content} ---", classes=f"message-{msg.role.value}")
        else:
            if msg.is_streaming:
                widget = Static(full_content, classes=f"message-{msg.role.value}", markup=True)
            else:
                widget = Markdown(full_content, classes=f"message-{msg.role.value}")

        widget.id = f"msg-widget-{msg.id}"
        self._message_widgets[msg.id] = widget
        
        def _do_mount():
            try:
                self.mount(widget)
                if self.auto_scroll:
                    self.scroll_end(animate=False)
            except Exception as e:
                self._logger.error(f"Failed to mount widget: {e}")
        
        self.call_later(_do_mount)

    def _update_message_widget(self, msg: MessageItem) -> None:
        if msg.id not in self._message_widgets:
            self._render_message(msg)
            return

        widget = self._message_widgets[msg.id]

        header = self._format_message_header(msg)
        content = self._format_message_content(msg)
        full_content = header + content

        if isinstance(widget, Static):
            if msg.role == MessageRole.SYSTEM:
                widget.update(f"--- {msg.content} ---")
            else:
                widget.update(full_content)
        elif isinstance(widget, Markdown):
            pass

        if self.auto_scroll:
            self.call_later(self.scroll_end, animate=False)

    def _upgrade_to_markdown(self, msg: MessageItem) -> None:
        if msg.id not in self._message_widgets:
            return

        old_widget = self._message_widgets[msg.id]
        old_widget.remove()

        header = self._format_message_header(msg)
        content = self._format_message_content(msg)
        full_content = header + content

        if msg.role != MessageRole.SYSTEM:
            new_widget = Markdown(full_content, classes=f"message-{msg.role.value}")
            new_widget.id = f"msg-widget-{msg.id}"
            self._message_widgets[msg.id] = new_widget
            
            def _do_mount():
                try:
                    self.mount(new_widget)
                    if self.auto_scroll:
                        self.scroll_end(animate=False)
                except Exception as e:
                    self._logger.error(f"Failed to mount markdown widget: {e}")
            
            self.call_later(_do_mount)

    def _render_or_update_message(self, msg: MessageItem) -> None:
        if msg.id in self._message_widgets:
            self._update_message_widget(msg)
        else:
            self._render_message(msg)

    def _post_message(self, msg: Message) -> None:
        if hasattr(self, 'post_message'):
            self.post_message(msg)

    def on_mount(self) -> None:
        self._logger.info("MessageList mounted")


# ============================================================================
# 模块导出
# ============================================================================

__all__ = [
    "MessageList",
    "MessageItem",
    "MessageRole",
    "MessageListUpdated",
    "StreamingComplete",
]
