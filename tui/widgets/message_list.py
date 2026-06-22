#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MessageList Widget - 消息列表组件

🚪 Access - 💬 CLI - TUI Widgets - MessageList

使用 RichLog 实现高性能消息列表显示，支持：
- 用户消息、助手消息、系统消息、工具消息
- 流式输出（打字机效果）
- 思考内容显示
- 错误消息高亮
- 自动滚动
- 历史消息数量限制
"""

from __future__ import annotations

from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import time

# Rich 文本支持
try:
    from rich.text import Text
except ImportError:
    Text = str  # type: ignore

# Textual 框架导入（带降级机制）
TEXTUAL_AVAILABLE = True
try:
    from textual.widgets import RichLog
    from textual.message import Message
except ImportError:
    TEXTUAL_AVAILABLE = False
    RichLog = object  # type: ignore
    Message = object  # type: ignore

# 主题图标和颜色
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

# i18n 支持
try:
    from common.i18n import get_i18n
except ImportError:
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

class MessageList(RichLog if TEXTUAL_AVAILABLE else object):
    """消息列表组件 - 使用 RichLog 实现"""

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
        # RichLog 初始化参数
        kwargs = {
            "id": id,
            "classes": classes,
            "auto_scroll": auto_scroll,
            "max_lines": max_messages,
        }
        super().__init__(**kwargs)

        self.max_messages = max_messages
        self.auto_scroll = auto_scroll
        self.show_timestamps = show_timestamps
        self.show_role_icons = show_role_icons
        self.streaming_throttle_ms = streaming_throttle_ms

        self._messages: list[MessageItem] = []
        self._message_counter = 0
        self._streaming_active: dict[str, str] = {}
        self._last_streaming_update: dict[str, float] = {}
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

        # 渲染并写入 RichLog
        self._render_and_write()
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

        self._render_and_write()
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
                self._update_last_message()
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

        self._render_and_write()

    def complete_streaming(self, message_id: str) -> None:
        if message_id not in self._streaming_active:
            return

        for msg in self._messages:
            if msg.id == message_id:
                msg.is_streaming = False
                msg.is_complete = True
                break

        thinking_id = f"{message_id}-thinking"
        for msg in self._messages:
            if msg.id == thinking_id:
                msg.is_streaming = False
                msg.is_complete = True
                break

        del self._streaming_active[message_id]
        if message_id in self._last_streaming_update:
            del self._last_streaming_update[message_id]

        self._render_and_write()
        self._post_message(StreamingComplete(self, message_id))

    # ========================================================================
    # 消息操作方法
    # ========================================================================

    def update_message(self, message_id: str, content: str) -> None:
        for msg in self._messages:
            if msg.id == message_id:
                msg.content = content
                self._render_and_write()
                break

    def remove_message(self, message_id: str) -> bool:
        for i, msg in enumerate(self._messages):
            if msg.id == message_id:
                self._messages.pop(i)
                self._render_and_write()
                self._post_message(MessageListUpdated(self, len(self._messages)))
                return True
        return False

    def clear_messages(self) -> None:
        self._messages.clear()
        self._streaming_active.clear()
        self._last_streaming_update.clear()
        self.clear()
        self._post_message(MessageListUpdated(self, 0))

    def get_messages(self) -> list[MessageItem]:
        return self._messages.copy()

    def scroll_to_bottom(self) -> None:
        if self.auto_scroll:
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
                    removed += 1
                    i -= 1

    def _format_message(self, msg: MessageItem) -> Text:
        msg_type = msg.role.value.upper()
        icon = MESSAGE_ICONS.get(msg_type, "💬")
        color = MESSAGE_COLORS.get(msg_type, "#c9d1d9")

        timestamp_str = f"[dim]{msg.time_str}[/]" if self.show_timestamps else ""

        role_labels = {
            MessageRole.USER: "你",
            MessageRole.ASSISTANT: "助手",
            MessageRole.SYSTEM: "系统",
            MessageRole.TOOL: f"工具({msg.tool_name})",
            MessageRole.ERROR: "错误",
            MessageRole.THINKING: "思考",
        }
        role_label = role_labels.get(msg.role, "")

        tool_prefix = ""
        if msg.role == MessageRole.TOOL and msg.tool_name:
            tool_prefix = f"[#a371f7]{msg.tool_name}[/]: "

        streaming_indicator = " ▌" if msg.is_streaming else ""

        if msg.role == MessageRole.SYSTEM:
            return Text.from_markup(f"\n[dim]--- {msg.content} ---\n[/]")

        header = f"{icon} [bold {color}]{role_label}[/]"
        if timestamp_str:
            header += f"  [dim]{timestamp_str}[/]"

        content_lines = msg.content.split("\n")

        if msg.role == MessageRole.THINKING:
            lines = [f"  {header}"]
            for line in content_lines:
                lines.append(f"    [{color}]{line}{streaming_indicator}[/]")
            return Text.from_markup("\n".join(lines) + "\n")

        if msg.role == MessageRole.USER:
            lines = [header]
            for line in content_lines:
                lines.append(f"  [{color}]{line}{streaming_indicator}[/]")
            return Text.from_markup("\n".join(lines) + "\n")

        lines = [header]
        for line in content_lines:
            lines.append(f"  [{color}]{tool_prefix}{line}{streaming_indicator}[/]")
        return Text.from_markup("\n".join(lines) + "\n")

    def _render_and_write(self) -> None:
        """渲染所有消息并写入 RichLog"""
        self.clear()
        for msg in self._messages:
            self.write(self._format_message(msg))
        if self.auto_scroll:
            self.scroll_end(animate=False)

    def _update_last_message(self) -> None:
        """更新最后一条消息（用于流式输出）"""
        if not self._messages:
            return
        self._render_and_write()

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