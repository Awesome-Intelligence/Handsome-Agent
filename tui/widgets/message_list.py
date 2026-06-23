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
    from textual.containers import VerticalScroll, Container
    from textual.message import Message
except ImportError:
    TEXTUAL_AVAILABLE = False
    Markdown = object  # type: ignore
    Static = object  # type: ignore
    VerticalScroll = object  # type: ignore
    Container = object  # type: ignore
    Message = object  # type: ignore

# Collapsible 组件 (Textual 0.37+)
TEXTUAL_COLLAPSIBLE_AVAILABLE = True
try:
    from textual.widgets import Collapsible
except ImportError:
    TEXTUAL_COLLAPSIBLE_AVAILABLE = False
    Collapsible = object  # type: ignore

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
    # 思考内容相关字段
    thinking_content: Optional[str] = None
    thinking_collapsed: bool = True  # 默认收起

    @property
    def time_str(self) -> str:
        return datetime.fromtimestamp(self.timestamp).strftime("%H:%M:%S")

    @property
    def has_thinking(self) -> bool:
        return bool(self.thinking_content)


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
        self._scroll_throttle_ms: int = 150  # 滚动节流时间（优化：从 100 改为 150ms）
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
        """追加思考内容 - 现在存到主消息的 thinking_content 字段中"""
        if message_id not in self._streaming_active:
            return

        # 使用索引快速查找主消息
        msg = self._message_index.get(message_id)
        if msg is None:
            return

        # 将思考内容追加到主消息的 thinking_content 字段
        if msg.thinking_content is None:
            msg.thinking_content = ""
        msg.thinking_content += text

        # 更新渲染（触发思考内容更新）
        self._update_thinking_widget(msg)

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
            # 如果有思考内容，需要重新渲染整个消息（包含 Collapsible）
            if msg.has_thinking:
                self._rebuild_message_with_thinking(msg)
            else:
                self._upgrade_to_markdown(msg)

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
        """检查滚动区域是否在底部附近（用于检测用户是否在底部）
        
        优化：只访问必要的属性，减少 DOM 查询开销
        """
        try:
            max_scroll = self.max_scroll_y  # 最大滚动偏移
            # 如果几乎没有可滚动内容，认为在底部
            if max_scroll <= 50:
                return True
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
        # 如果消息有思考内容，使用 Collapsible 结构渲染
        if msg.has_thinking and TEXTUAL_COLLAPSIBLE_AVAILABLE:
            self._render_message_with_thinking(msg)
            return

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

    def _render_message_with_thinking(self, msg: MessageItem) -> None:
        """渲染带有思考内容的消息 - 使用 Collapsible 嵌套"""
        # 如果 Collapsible 不可用，回退到普通渲染
        if not TEXTUAL_COLLAPSIBLE_AVAILABLE:
            self._render_message_fallback(msg)
            return

        # 格式化思考内容标题
        i18n = get_i18n()
        thinking_title = i18n.t("message.thinking", default="💭 Thinking")

        # 思考内容
        thinking_content = msg.thinking_content or ""
        if msg.is_streaming:
            thinking_content += " ▌"

        # 回复内容
        header = self._format_message_header(msg)
        content = self._format_message_content(msg)
        response_content = header + content

        # 创建子组件
        if msg.is_streaming:
            thinking_widget = Static(thinking_content, classes="thinking-content")
        else:
            thinking_widget = Markdown(thinking_content, classes="thinking-content")
        thinking_widget.id = f"thinking-{msg.id}"

        # Collapsible - 默认收起
        collapsible = Collapsible(
            thinking_widget,
            title=thinking_title,
            collapsed=msg.thinking_collapsed,
            collapsed_symbol="▶",
            expanded_symbol="▼",
            classes="message-thinking",
        )
        collapsible.id = f"thinking-collapsible-{msg.id}"

        # 回复内容（主消息）
        if msg.is_streaming:
            response_widget = Static(response_content, classes=f"message-{msg.role.value}", markup=True)
        else:
            response_widget = Markdown(response_content, classes=f"message-{msg.role.value}")
        response_widget.id = f"response-{msg.id}"

        # 创建消息容器（按垂直顺序排列）
        container_id = f"msg-container-{msg.id}"
        container = Container(
            collapsible,
            response_widget,
            classes="message-container",
        )
        container.id = container_id

        self._message_widgets[msg.id] = container
        # 同时记录子组件引用
        self._message_widgets[f"collapsible-{msg.id}"] = collapsible
        self._message_widgets[f"thinking-{msg.id}"] = thinking_widget
        self._message_widgets[f"response-{msg.id}"] = response_widget

        def _do_mount():
            try:
                self.mount(container)
                self._do_smart_scroll()
            except Exception as e:
                self._logger.error(f"Failed to mount thinking message: {e}")

        self.call_later(_do_mount)

    def _render_message_fallback(self, msg: MessageItem) -> None:
        """当 Collapsible 不可用时的回退渲染"""
        header = self._format_message_header(msg)

        # 格式化思考内容
        thinking_header = f"**💭 Thinking**\n\n"
        thinking_content = msg.thinking_content or ""
        if msg.is_streaming:
            thinking_content += " ▌"
        full_thinking = thinking_header + thinking_content

        # 回复内容
        content = self._format_message_content(msg)
        full_content = header + content

        if msg.is_streaming:
            thinking_widget = Static(full_thinking, classes="thinking-content", markup=True)
            response_widget = Static(full_content, classes=f"message-{msg.role.value}", markup=True)
        else:
            thinking_widget = Markdown(full_thinking, classes="thinking-content")
            response_widget = Markdown(full_content, classes=f"message-{msg.role.value}")

        # 创建容器
        container_id = f"msg-container-{msg.id}"
        container = Container(thinking_widget, response_widget, classes="message-container-fallback")
        container.id = container_id

        self._message_widgets[msg.id] = container
        self._message_widgets[f"thinking-{msg.id}"] = thinking_widget
        self._message_widgets[f"response-{msg.id}"] = response_widget

        def _do_mount():
            try:
                self.mount(container)
                self._do_smart_scroll()
            except Exception as e:
                self._logger.error(f"Failed to mount fallback message: {e}")

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

    def _update_thinking_widget(self, msg: MessageItem) -> None:
        """更新思考内容组件（流式输出时调用）"""
        thinking_widget_id = f"thinking-{msg.id}"

        if thinking_widget_id not in self._message_widgets:
            # 如果思考组件不存在，先渲染整个消息
            if msg.has_thinking:
                self._render_message_with_thinking(msg)
            return

        thinking_widget = self._message_widgets[thinking_widget_id]
        thinking_content = msg.thinking_content or ""

        if msg.is_streaming:
            thinking_content += " ▌"

        if isinstance(thinking_widget, Static):
            thinking_widget.update(thinking_content)

        # 智能滚动
        self.call_later(self._do_smart_scroll)

    def _rebuild_message_with_thinking(self, msg: MessageItem) -> None:
        """重建带有思考内容的消息（流式完成时调用）"""
        container_id = f"msg-container-{msg.id}"

        # 移除旧的消息组件
        if container_id in self._message_widgets:
            old_container = self._message_widgets[container_id]
            old_container.remove()

        # 清理旧组件引用
        for key in [f"collapsible-{msg.id}", f"thinking-{msg.id}", f"response-{msg.id}"]:
            if key in self._message_widgets:
                del self._message_widgets[key]

        # 重新渲染消息
        self._render_message_with_thinking(msg)

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
        # 滚动事件节流：避免频繁计算
        current_time = time.time() * 1000
        if current_time - self._last_scroll_time < self._scroll_throttle_ms:
            return
        self._last_scroll_time = current_time
        
        if self._check_if_at_bottom():
            self._mark_scrolled_to_bottom()
        else:
            self._mark_scrolled_away()

    def on_scroll_to(self, event) -> None:
        """监听 scroll_to 事件"""
        # scroll_to 事件同样需要节流
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
