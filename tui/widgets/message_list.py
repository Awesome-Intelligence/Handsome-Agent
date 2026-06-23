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
        streaming_throttle_ms: int = 150,
        streaming_buffer_size: int = 30,
        streaming_max_delay_ms: int = 200,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)

        self.max_messages = max_messages
        self.auto_scroll = auto_scroll
        self.show_timestamps = show_timestamps
        self.show_role_icons = show_role_icons
        self.streaming_throttle_ms = streaming_throttle_ms
        self.streaming_buffer_size = streaming_buffer_size
        self.streaming_max_delay_ms = streaming_max_delay_ms

        self._messages: list[MessageItem] = []
        self._message_index: dict[str, MessageItem] = {}  # 消息索引，加速查找
        self._message_counter = 0
        self._streaming_active: dict[str, str] = {}
        self._last_streaming_update: dict[str, float] = {}
        self._streaming_buffer: dict[str, str] = {}  # 文本累积缓冲区
        self._streaming_timers: dict[str, any] = {}  # 定时器引用
        self._message_widgets: dict[str, Static | Markdown] = {}
        self._logger = get_access_logger("MessageList", sublayer="tui")

        # 自动滚动优化
        self._user_scrolled_to_bottom: bool = True  # 用户是否在底部
        self._scroll_throttle_ms: int = 100  # 滚动节流时间
        self._last_scroll_time: float = 0  # 上次滚动时间

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
        self._message_index[msg_id] = msg  # 维护索引
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
        self._message_index[msg_id] = msg  # 维护索引
        self._streaming_active[msg_id] = role_enum.value
        self._streaming_buffer[msg_id] = ""  # 初始化缓冲区
        self._trim_messages()

        self._render_message(msg)
        return msg_id

    def append_streaming_text(self, message_id: str, text: str) -> None:
        """流式追加文本 - 使用累积缓冲区减少 UI 刷新

        优化策略:
        1. 文本先累积到缓冲区，不立即更新 UI
        2. 当缓冲区达到一定大小(streaming_buffer_size)时更新
        3. 或者当距离上次更新超过最大延迟(streaming_max_delay_ms)时更新
        """
        if message_id not in self._streaming_active:
            return

        # 将文本累积到缓冲区
        if message_id not in self._streaming_buffer:
            self._streaming_buffer[message_id] = ""
        self._streaming_buffer[message_id] += text

        current_time = time.time() * 1000
        last_update = self._last_streaming_update.get(message_id, 0)
        time_since_last_update = current_time - last_update

        # 检查是否需要立即更新
        buffer_size = len(self._streaming_buffer[message_id])
        should_update = (
            buffer_size >= self.streaming_buffer_size or
            time_since_last_update >= self.streaming_max_delay_ms
        )

        if should_update and time_since_last_update >= self.streaming_throttle_ms:
            self._flush_streaming_buffer(message_id)
            self._last_streaming_update[message_id] = current_time

    def _flush_streaming_buffer(self, message_id: str) -> None:
        """刷新流式缓冲区 - 将累积的文本批量更新到 UI"""
        if message_id not in self._streaming_buffer:
            return

        buffered_text = self._streaming_buffer.get(message_id, "")
        if not buffered_text:
            return

        # 使用索引快速查找消息（索引在 add_message/start_streaming 时已维护）
        msg = self._message_index.get(message_id)
        if msg is None:
            return

        msg.content += buffered_text
        self._streaming_buffer[message_id] = ""  # 清空缓冲区
        self._update_message_widget(msg)

    def append_streaming_thinking(self, message_id: str, text: str) -> None:
        if message_id not in self._streaming_active:
            return

        thinking_id = f"{message_id}-thinking"
        thinking_msg = self._message_index.get(thinking_id)

        if thinking_msg:
            thinking_msg.content += text
        else:
            # 首次创建思考消息时，同时添加到列表和索引
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
            self._message_index[thinking_id] = thinking_msg

        self._render_or_update_message(thinking_msg)

    def complete_streaming(self, message_id: str) -> None:
        if message_id not in self._streaming_active:
            return

        # 先刷新剩余的缓冲区内容
        if message_id in self._streaming_buffer and self._streaming_buffer.get(message_id, ""):
            self._flush_streaming_buffer(message_id)

        # 使用索引快速查找（索引在 start_streaming 时已维护）
        msg = self._message_index.get(message_id)
        if msg:
            msg.is_streaming = False
            msg.is_complete = True
            self._upgrade_to_markdown(msg)

        thinking_id = f"{message_id}-thinking"
        thinking_msg = self._message_index.get(thinking_id)
        if thinking_msg:
            thinking_msg.is_streaming = False
            thinking_msg.is_complete = True
            self._upgrade_to_markdown(thinking_msg)

        # 清理流式状态
        self._streaming_active.pop(message_id, None)
        self._last_streaming_update.pop(message_id, None)
        self._streaming_buffer.pop(message_id, None)
        self._streaming_timers.pop(message_id, None)

        self._post_message(StreamingComplete(self, message_id))

    # ========================================================================
    # 消息操作方法
    # ========================================================================

    def update_message(self, message_id: str, content: str) -> None:
        # 使用索引快速查找（索引已维护，直接查询即可）
        msg = self._message_index.get(message_id)
        if msg:
            msg.content = content
            self._update_message_widget(msg)

    def remove_message(self, message_id: str) -> bool:
        # 使用索引快速查找（索引已维护，直接查询即可）
        msg = self._message_index.get(message_id)
        if msg:
            self._messages.remove(msg)
            self._message_index.pop(message_id, None)
            if message_id in self._message_widgets:
                widget = self._message_widgets[message_id]
                widget.remove()
                del self._message_widgets[message_id]
            # 清理相关状态
            self._streaming_active.pop(message_id, None)
            self._streaming_buffer.pop(message_id, None)
            self._last_streaming_update.pop(message_id, None)
            self._post_message(MessageListUpdated(self, len(self._messages)))
            return True
        return False

    def clear_messages(self) -> None:
        self._messages.clear()
        self._message_index.clear()
        self._streaming_active.clear()
        self._last_streaming_update.clear()
        self._streaming_buffer.clear()
        self._streaming_timers.clear()
        for widget in self._message_widgets.values():
            widget.remove()
        self._message_widgets.clear()
        self._post_message(MessageListUpdated(self, 0))

    def get_messages(self) -> list[MessageItem]:
        return self._messages.copy()

    def scroll_to_bottom(self) -> None:
        self.scroll_end(animate=True)

    def _should_auto_scroll(self) -> bool:
        """判断是否应该自动滚动到最新消息

        策略:
        1. auto_scroll 开关必须打开
        2. 用户必须在底部位置（_user_scrolled_to_bottom 为 True）
        3. 距离上次滚动时间要超过节流时间
        """
        if not self.auto_scroll:
            return False

        if not self._user_scrolled_to_bottom:
            return False

        current_time = time.time() * 1000
        if current_time - self._last_scroll_time < self._scroll_throttle_ms:
            return False

        return True

    def _do_smart_scroll(self) -> None:
        """智能滚动 - 只在必要时滚动"""
        if self._should_auto_scroll():
            self._last_scroll_time = time.time() * 1000
            self.scroll_end(animate=False)

    def _check_if_at_bottom(self) -> bool:
        """检查滚动区域是否在底部附近（用于检测用户是否在底部）"""
        try:
            # 获取可滚动区域的尺寸
            scroll_height = self.scroll_home  # 滚动区域总高度
            max_scroll = self.max_scroll_y  # 最大滚动偏移
            current_y = self.scroll_y  # 当前滚动位置

            # 如果最大滚动接近当前滚动位置，说明在底部
            # 允许 50 像素的误差
            return (max_scroll - current_y) < 50
        except Exception:
            return True  # 默认认为在底部

    def _mark_scrolled_to_bottom(self) -> None:
        """标记用户已滚动到/接近底部"""
        self._user_scrolled_to_bottom = True

    def _mark_scrolled_away(self) -> None:
        """标记用户已离开底部区域"""
        self._user_scrolled_to_bottom = False

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
            # 批量删除：找出需要保留的消息
            streaming_ids = set(self._streaming_active.keys())
            # 包括正在流式输出的思考消息
            for msg_id in list(self._streaming_active.keys()):
                streaming_ids.add(f"{msg_id}-thinking")

            # 保留的消息（在列表前面）+ 流式消息
            msgs_to_keep = []
            for msg in self._messages:
                if msg.id in streaming_ids or len(msgs_to_keep) < self.max_messages:
                    msgs_to_keep.append(msg)

            # 找出被删除的消息
            old_msg_ids = {msg.id for msg in self._messages}
            new_msg_ids = {msg.id for msg in msgs_to_keep}
            removed_ids = old_msg_ids - new_msg_ids

            # 更新列表
            self._messages = msgs_to_keep

            # 更新索引
            self._message_index = {msg.id: msg for msg in self._messages}

            # 清理已删除消息的 widget
            for msg_id in removed_ids:
                if msg_id in self._message_widgets:
                    widget = self._message_widgets[msg_id]
                    widget.remove()
                    del self._message_widgets[msg_id]
                # 清理相关状态
                self._streaming_buffer.pop(msg_id, None)
                self._last_streaming_update.pop(msg_id, None)

    def _format_message_header(self, msg: MessageItem) -> str:
        msg_type = msg.role.value.upper()
        icon = MESSAGE_ICONS.get(msg_type, "💬")

        i18n_instance = get_i18n()
        role_key_map = {
            MessageRole.USER: "message.role.user",
            MessageRole.ASSISTANT: "message.role.assistant",
            MessageRole.SYSTEM: "message.role.system",
            MessageRole.TOOL: "message.role.tool",
            MessageRole.ERROR: "message.role.error",
            MessageRole.THINKING: "message.role.thinking",
        }
        role_label = i18n_instance.t(role_key_map.get(msg.role, ""))

        # Special handling for tool messages with tool name
        if msg.role == MessageRole.TOOL and msg.tool_name:
            role_label = f"{role_label}({msg.tool_name})"

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
                # 使用智能滚动 - 只在用户位于底部时自动滚动
                self._do_smart_scroll()
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

        # 使用智能滚动 - 只在用户位于底部时自动滚动
        self.call_later(self._do_smart_scroll)

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
                    # 使用智能滚动 - 只在用户位于底部时自动滚动
                    self._do_smart_scroll()
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

    def on_scroll(self) -> None:
        """监听滚动事件，检测用户是否在底部"""
        if self._check_if_at_bottom():
            self._mark_scrolled_to_bottom()
        else:
            self._mark_scrolled_away()

    def on_scroll_to(self, event) -> None:
        """监听 scroll_to 事件"""
        self.on_scroll()

    def scroll_to_bottom(self, animate: bool = True) -> None:
        """手动滚动到底部，同时标记用户在底部"""
        super().scroll_end(animate=animate)
        self._user_scrolled_to_bottom = True
        self._last_scroll_time = time.time() * 1000


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
