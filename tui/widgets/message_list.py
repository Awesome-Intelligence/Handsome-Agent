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
    from textual.containers import VerticalScroll, Vertical
    from textual.message import Message
    from textual.widget import MountError
    from textual._node_list import DuplicateIds
    from textual.widgets._markdown import MarkdownStream
    from textual import on
    from textual.events import Click, Key
except ImportError:
    TEXTUAL_AVAILABLE = False
    Markdown = object  # type: ignore
    Static = object  # type: ignore
    VerticalScroll = object  # type: ignore
    Vertical = object  # type: ignore
    Message = object  # type: ignore
    Key = object  # type: ignore
    Click = object  # type: ignore
    MountError = object  # type: ignore
    DuplicateIds = object  # type: ignore

    def on(*args, **kwargs):
        """Mock on decorator when textual is not available."""

        def decorator(func):
            return func

        return decorator


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
    thinking: Optional[str] = None
    thinking_collapsed: bool = True
    cached_header: Optional[str] = (
        None  # ponytail: 流式期间 header 不变，缓存避免每 150ms 重算
    )

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


class MessageList(VerticalScroll if TEXTUAL_AVAILABLE else object, can_focus=False):
    """消息列表组件 - 使用 VerticalScroll + Markdown 实现

    注意：设置 can_focus=False 以避免 Textual 8.x 的自动聚焦问题。
    """

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
        # ponytail: 保留旧参数属性以兼容现有调用方，不再用于流式逻辑
        self.streaming_throttle_ms = streaming_throttle_ms
        self.streaming_buffer_size = streaming_buffer_size
        self.streaming_max_delay_ms = streaming_max_delay_ms

        self._messages: list[MessageItem] = []
        self._message_index: dict[str, MessageItem] = {}  # 消息索引，加速查找
        self._message_counter = 0
        self._streaming_active: dict[str, str] = {}
        self._message_widgets: dict[str, Static | Markdown] = {}
        # ponytail: MarkdownStream 替代手动 buffering — Textual 内置异步批处理
        self._markdown_streams: dict[str, MarkdownStream] = {}
        # ponytail: 思考内容用 sibling Static(label) + Markdown(body) 代替 Collapsible 嵌套
        self._message_thinking_labels: dict[str, Static] = {}
        self._message_thinking_bodies: dict[str, Markdown] = {}
        self._message_containers: dict[str, Vertical] = {}  # 消息容器引用
        self._logger = get_access_logger("MessageList", sublayer="tui")
        self._i18n = (
            get_i18n()
        )  # ponytail: cache i18n instance — avoid per-message call

        # 自动滚动优化
        self._user_scrolled_to_bottom: bool = True  # 用户是否在底部
        self._scroll_throttle_ms: int = (
            300  # ponytail: increased from 100 — on_scroll entry has overhead even when throttled
        )
        self._last_scroll_time: float = 0  # 上次滚动时间
        self._suppress_scroll_event: bool = (
            False  # ponytail: prevent scroll feedback loop
        )

        # ponytail: max_scroll_y 缓存优化 — 避免每次滚动事件都触发布局计算
        self._cached_max_scroll_y: float = 0.0  # 缓存的 max_scroll_y 值
        self._max_scroll_dirty: bool = True  # 脏标记，True 表示需要重新计算
        self._scroll_dirty: bool = False  # 滚动事件脏标记，延迟处理

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
        # ponytail: 标记 max_scroll_y 需要重新计算
        self._invalidate_max_scroll()
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

        # ponytail: avoid duplicate streaming message if one already exists for this role
        # (append_streaming_thinking may have already called start_streaming)
        for msg_id, role_val in self._streaming_active.items():
            if role_val == role_enum.value:
                return msg_id

        # No existing streaming message — create one (only now increment counter)
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
        self._trim_messages()

        self._render_message(msg)
        # ponytail: 标记 max_scroll_y 需要重新计算
        self._invalidate_max_scroll()
        return msg_id

    def append_streaming_text(self, message_id: str, text: str) -> None:
        """流式追加文本 — 通过 MarkdownStream 异步批处理，Textual 内部合并写入"""
        if message_id not in self._streaming_active:
            return

        msg = self._message_index.get(message_id)
        if msg is None:
            return

        msg.content += text

        stream = self._markdown_streams.get(message_id)
        widget = self._message_widgets.get(message_id)
        if stream is None and isinstance(widget, Markdown):
            try:
                stream = Markdown.get_stream(widget)
                self._markdown_streams[message_id] = stream
            except RuntimeError:
                # ponytail: 无 event loop 时(测试环境)回退到 widget.append
                widget.append(text)
                return
        if stream is not None:
            self._schedule_async(stream.write(text))

    def append_streaming_thinking(self, message_id: str, text: str) -> None:
        """流式追加思考内容到消息"""
        # thinking 先于 start_streaming 到达时，主动创建流式消息
        if message_id not in self._streaming_active:
            message_id = self.start_streaming(MessageRole.ASSISTANT)

        msg = self._message_index.get(message_id)
        if msg is None:
            return

        # 更新消息的 thinking 字段
        if msg.thinking is None:
            msg.thinking = ""
        msg.thinking += text

        # thinking body 已存在则增量更新
        if message_id in self._message_thinking_bodies:
            self._update_thinking_body(message_id, msg)
        elif message_id in self._message_widgets:
            # 消息已渲染但还没有 thinking widgets,重渲染为带 thinking 的版本
            self._upgrade_to_thinking_message(msg)
        elif msg.is_complete:
            # thinking 在 complete_streaming 之后才到达,补创建带 thinking widgets 的消息
            self._render_message(msg)

    def _update_thinking_body(self, message_id: str, msg: MessageItem) -> None:
        """更新 thinking body Markdown 内容 + label 文字"""
        body = self._message_thinking_bodies.get(message_id)
        label = self._message_thinking_labels.get(message_id)
        if body is None:
            return
        body.update(msg.thinking or "")
        if label is not None:
            label.update(self._format_thinking_label(msg))

    def _upgrade_to_thinking_message(self, msg: MessageItem) -> None:
        """thinking 在 streaming 之后到达 — 重渲染为带 thinking widget 的版本"""
        if msg.id not in self._message_widgets:
            return

        def _do_upgrade():
            old_widget = self._message_widgets.pop(msg.id, None)
            old_stream = self._markdown_streams.pop(msg.id, None)
            # ponytail: cancel old stream task (private API, same as oterm cancel_streams)
            if old_stream is not None:
                task = getattr(old_stream, "_task", None)
                if task is not None:
                    task.cancel()
            if old_widget is not None:
                try:
                    old_widget.remove()
                except Exception as e:
                    self._logger.debug(f"Failed to remove old widget: {e}")
            self._render_message(msg)

        self.call_later(_do_upgrade)

    def _toggle_thinking(self, message_id: str) -> None:
        """切换单条消息的 thinking 展开/折叠"""
        msg = self._message_index.get(message_id)
        if msg is None or not msg.thinking:
            return
        msg.thinking_collapsed = not msg.thinking_collapsed
        body = self._message_thinking_bodies.get(message_id)
        label = self._message_thinking_labels.get(message_id)
        if body is not None:
            body.display = not msg.thinking_collapsed
        if label is not None:
            label.update(self._format_thinking_label(msg))

    @on(Click, ".thinking-label")
    def _on_thinking_label_click(self, event: Click) -> None:
        """点击思考标签切换展开/折叠"""
        widget = event.widget
        if widget.id and widget.id.startswith("msg-thinking-label-"):
            msg_id = widget.id[len("msg-thinking-label-") :]
            self._toggle_thinking(msg_id)
            event.stop()

    def complete_streaming(self, message_id: str) -> None:
        if message_id not in self._streaming_active:
            return

        msg = self._message_index.get(message_id)
        if msg:
            msg.is_streaming = False
            msg.is_complete = True

        self._streaming_active.pop(message_id, None)

        stream = self._markdown_streams.pop(message_id, None)
        widget = self._message_widgets.get(message_id)
        if widget is not None and msg is not None:
            full = self._format_message_header(msg) + msg.content
            if stream is not None:
                self._schedule_async(self._finish_stream(stream, widget, full))
            else:
                # ponytail: 无 stream 时(测试环境/未通过 append 创建)延迟 update
                self.call_later(widget.update, full)

        self._post_message(StreamingComplete(self, message_id))

    @staticmethod
    def _schedule_async(coro) -> None:
        """ponytail: 桥接 async → sync — 在 event loop 上调度协程"""
        import asyncio

        try:
            asyncio.get_running_loop().create_task(coro)
        except RuntimeError:
            pass  # 无运行中的 loop,跳过(子线程中通过 call_later 间接到达)

    @staticmethod
    async def _finish_stream(stream, widget, full_text: str) -> None:
        """停止 MarkdownStream 并强制完整重解析"""
        await stream.stop()
        await widget.update(full_text)

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
            # 清理 thinking widgets
            if message_id in self._message_thinking_labels:
                self._message_thinking_labels[message_id].remove()
                del self._message_thinking_labels[message_id]
            if message_id in self._message_thinking_bodies:
                self._message_thinking_bodies[message_id].remove()
                del self._message_thinking_bodies[message_id]
            # 清理 Container
            if message_id in self._message_containers:
                container = self._message_containers[message_id]
                container.remove()
                del self._message_containers[message_id]
            # 清理相关状态
            self._streaming_active.pop(message_id, None)
            self._markdown_streams.pop(message_id, None)
            # ponytail: 标记 max_scroll_y 需要重新计算
            self._invalidate_max_scroll()
            self._post_message(MessageListUpdated(self, len(self._messages)))
            return True
        return False

    def clear_messages(self) -> None:
        self._messages.clear()
        self._message_index.clear()
        self._streaming_active.clear()
        self._markdown_streams.clear()
        for widget in self._message_widgets.values():
            widget.remove()
        self._message_widgets.clear()
        for label in self._message_thinking_labels.values():
            label.remove()
        self._message_thinking_labels.clear()
        for body in self._message_thinking_bodies.values():
            body.remove()
        self._message_thinking_bodies.clear()
        for container in self._message_containers.values():
            container.remove()
        self._message_containers.clear()
        # ponytail: 标记 max_scroll_y 需要重新计算
        self._invalidate_max_scroll()
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
            # ponytail: suppress scroll event during programmatic scroll — breaks feedback loop
            self._suppress_scroll_event = True
            self.scroll_end(animate=False)
            self._suppress_scroll_event = False

    def _check_if_at_bottom(self) -> bool:
        """检查滚动区域是否在底部附近（用于检测用户是否在底部）"""
        # ponytail: 使用缓存的 max_scroll_y 避免频繁触发布局计算
        try:
            current_y = self.scroll_y
            max_scroll = self._get_max_scroll_y_cached()
            return (max_scroll - current_y) < 50
        except Exception:
            return True

    def _mark_scrolled_to_bottom(self) -> None:
        """标记用户已滚动到/接近底部"""
        self._user_scrolled_to_bottom = True

    def _mark_scrolled_away(self) -> None:
        """标记用户已离开底部区域"""
        self._user_scrolled_to_bottom = False

    # ========================================================================
    # max_scroll_y 缓存优化方法 (ponytail)
    # ========================================================================

    def _invalidate_max_scroll(self) -> None:
        """标记 max_scroll_y 需要重新计算

        在以下情况调用：
        - 添加新消息后
        - 删除消息后
        - 流式输出完成后
        - 窗口大小改变时
        """
        self._max_scroll_dirty = True

    def _get_max_scroll_y_cached(self) -> float:
        """获取缓存的 max_scroll_y 值

        只有在脏标记为 True 时才真正计算，否则直接返回缓存值。
        这样可以避免在滚动事件中频繁触发布局计算。

        Returns:
            最大可滚动高度（以行为单位）
        """
        if self._max_scroll_dirty:
            try:
                self._cached_max_scroll_y = self.max_scroll_y
            except Exception:
                # 如果计算失败，返回一个安全的默认值
                self._cached_max_scroll_y = 0.0
            self._max_scroll_dirty = False
        return self._cached_max_scroll_y

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
                # 清理 thinking widgets
                if msg_id in self._message_thinking_labels:
                    self._message_thinking_labels[msg_id].remove()
                    del self._message_thinking_labels[msg_id]
                if msg_id in self._message_thinking_bodies:
                    self._message_thinking_bodies[msg_id].remove()
                    del self._message_thinking_bodies[msg_id]
                # 清理 Container
                if msg_id in self._message_containers:
                    container = self._message_containers[msg_id]
                    container.remove()
                    del self._message_containers[msg_id]
                # 清理相关状态
                self._markdown_streams.pop(msg_id, None)

    def _format_message_header(self, msg: MessageItem) -> str:
        # ponytail: header 对一条消息不变，缓存复用 — 流式每 150ms 一次浪费
        if msg.cached_header is not None:
            return msg.cached_header

        msg_type = msg.role.value.upper()
        icon = MESSAGE_ICONS.get(msg_type, "💬")

        i18n_instance = self._i18n
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
            header = f"{icon} **{role_label}** {msg.time_str}\n\n"
        else:
            header = f"{icon} **{role_label}**\n\n"
        msg.cached_header = header
        return header

    def _format_message_content(self, msg: MessageItem) -> str:
        # ponytail: 流式期间不再拼游标字符到 content — 改用 CSS 处理或直接干掉
        return msg.content

    def _render_message(self, msg: MessageItem) -> None:
        header = self._format_message_header(msg)
        content = self._format_message_content(msg)
        full_content = header + content

        if msg.role == MessageRole.SYSTEM:
            # ponytail: guard against duplicate mount
            if msg.id in self._message_widgets:
                return
            widget = Static(
                f"--- {msg.content} ---", classes=f"message-{msg.role.value}"
            )
            widget.id = f"msg-widget-{msg.id}"
            self._message_widgets[msg.id] = widget

            def _do_mount():
                try:
                    self.mount(widget)
                    self._do_smart_scroll()
                except MountError:
                    # widget already mounted, ignore
                    pass
                except Exception as e:
                    self._logger.error(f"Failed to mount widget: {e}")

            self.call_later(_do_mount)
            return

        # 流式消息用 Static（轻量），完成后升级为 Markdown
        if msg.is_streaming:
            self._render_message_streaming(msg, full_content)
            return

        # 如果消息有思考内容，使用 Container 包装
        # 防御性检查：确保 thinking 是有效字符串
        if (
            msg.thinking is not None
            and msg.role == MessageRole.ASSISTANT
            and isinstance(msg.thinking, str)
            and msg.thinking.strip()
        ):
            try:
                self._render_message_with_thinking(msg, full_content)
            except Exception as e:
                self._logger.warning(
                    f"Failed to render message with thinking, falling back: {e}"
                )
                # 回退到普通渲染
                self._render_message_plain(msg, full_content)
            return

        # 普通消息渲染
        self._render_message_plain(msg, full_content)

    def _render_message_streaming(self, msg: MessageItem, full_content: str) -> None:
        """渲染流式消息（直接用 Markdown widget + MarkdownStream 增量更新）"""
        if msg.id in self._message_widgets:
            return
        widget = Markdown(full_content, classes=f"message-{msg.role.value}")
        widget.id = f"msg-widget-{msg.id}"
        self._message_widgets[msg.id] = widget
        # ponytail: MarkdownStream 懒初始化 — get_stream 内部调用 asyncio.create_task,
        # 需要 event loop；推迟到首次 append_streaming_text (必定在 event loop 上)

        def _do_mount():
            try:
                self.mount(widget)
                self._do_smart_scroll()
            except (MountError, DuplicateIds):
                pass
            except Exception as e:
                self._logger.error(f"Failed to mount streaming widget: {e}")

        self.call_later(_do_mount)

    def _render_message_plain(self, msg: MessageItem, full_content: str) -> None:
        """渲染普通消息（无思考内容）"""
        # ponytail: guard against duplicate mount if already scheduled/rendered
        if msg.id in self._message_widgets:
            return
        # USER/TOOL/ERROR 用 Static 避免无谓的 markdown 解析；ASSISTANT 保持 Markdown
        if msg.role == MessageRole.ASSISTANT:
            widget = Markdown(full_content, classes=f"message-{msg.role.value}")
        else:
            widget = Static(full_content, classes=f"message-{msg.role.value}")
        widget.id = f"msg-widget-{msg.id}"
        self._message_widgets[msg.id] = widget

        def _do_mount():
            try:
                if widget.parent is not None:
                    return
                self.mount(widget)
                self._do_smart_scroll()
            except Exception as e:
                self._logger.error(f"Failed to mount widget: {e}")

        self.call_later(_do_mount)

    def _render_message_with_thinking(
        self, msg: MessageItem, full_content: str
    ) -> None:
        """渲染带思考内容的消息 — 用 sibling Markdown + Static(label) + Markdown(body) 代替嵌套 Collapsible

        widget 树:
            Vertical
            ├── Markdown (response)
            ├── Static  (thinking-label)  # click 切 body display
            └── Markdown (thinking-body)
        """
        if msg.id in self._message_widgets:
            return

        msg_widget = Markdown(full_content, classes=f"message-{msg.role.value}")
        msg_widget.id = f"msg-widget-{msg.id}"
        self._message_widgets[msg.id] = msg_widget

        thinking_label = Static(
            self._format_thinking_label(msg),
            classes="thinking-label",
            id=f"msg-thinking-label-{msg.id}",
        )
        thinking_body = Markdown(
            msg.thinking or "",
            classes="thinking-body",
            id=f"msg-thinking-body-{msg.id}",
        )
        # ponytail: 通过 display 控制可见性,没有 Collapsible 的折叠状态机
        thinking_body.display = bool(msg.thinking) and not msg.thinking_collapsed
        thinking_label.display = bool(msg.thinking)
        self._message_thinking_labels[msg.id] = thinking_label
        self._message_thinking_bodies[msg.id] = thinking_body

        container = Vertical(
            msg_widget,
            thinking_label,
            thinking_body,
            classes=f"message-container message-{msg.role.value}",
        )
        container.id = f"msg-container-{msg.id}"

        def _do_mount():
            try:
                self.mount(container)
                self._message_containers[msg.id] = container
                self._do_smart_scroll()
            except (MountError, DuplicateIds):
                self._logger.debug(
                    f"Mount error in thinking render, re-rendering: {msg.id}"
                )
                self._message_widgets.pop(msg.id, None)
                self._render_message(msg)
            except Exception as e:
                self._logger.error(f"Failed to mount message with thinking: {e}")

        self.call_later(_do_mount)

    def _format_thinking_label(self, msg: MessageItem) -> str:
        """思考内容标签 — 显示折叠/展开符号 + 标题"""
        marker = "▾" if not msg.thinking_collapsed else "▸"
        title = self._i18n.t("message.thinking") or "思考过程"
        return f"{marker} {title}"

    def _update_message_widget(self, msg: MessageItem) -> None:
        if msg.id not in self._message_widgets:
            self._render_message(msg)
            return

        widget = self._message_widgets[msg.id]

        if isinstance(widget, Markdown):
            if msg.role == MessageRole.SYSTEM:
                widget.update(f"--- {msg.content} ---")
            elif msg.is_streaming:
                pass
            else:
                header = self._format_message_header(msg)
                content = self._format_message_content(msg)
                widget.update(header + content)
        elif isinstance(widget, Static):
            if msg.role == MessageRole.SYSTEM:
                widget.update(f"--- {msg.content} ---")
            elif msg.is_streaming:
                widget.update(msg.content + (" ▌" if msg.is_streaming else ""))
            else:
                header = self._format_message_header(msg)
                content = self._format_message_content(msg)
                widget.update(header + content)

        if msg.thinking is not None and msg.id in self._message_thinking_bodies:
            self._update_thinking_body(msg.id, msg)

        if self._user_scrolled_to_bottom:
            self.call_later(self._do_smart_scroll)

    def _upgrade_to_markdown(self, msg: MessageItem) -> None:
        if msg.id not in self._message_widgets:
            return

        widget = self._message_widgets[msg.id]

        if isinstance(widget, Markdown):
            return

        old_widget = widget
        try:
            old_widget.remove()
        except Exception as e:
            self._logger.debug(f"Failed to remove widget during markdown upgrade: {e}")

        if msg.thinking is not None and msg.role == MessageRole.ASSISTANT:
            self._render_message(msg)
            return

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
                    self._do_smart_scroll()
                except MountError:
                    pass
                except Exception as e:
                    self._logger.error(f"Failed to mount markdown widget: {e}")

            self.call_later(_do_mount)

    def _render_or_update_message(self, msg: MessageItem) -> None:
        if msg.id in self._message_widgets:
            self._update_message_widget(msg)
        else:
            self._render_message(msg)

    def _post_message(self, msg: Message) -> None:
        if hasattr(self, "post_message"):
            self.post_message(msg)

    def on_mount(self) -> None:
        self._logger.info("MessageList mounted")
        # ponytail: 懒启动 — 仅在首次 scroll 时才启动 200ms 检查定时器
        # 无滚动时直接跳过，节省 5 次/秒 主线程唤醒
        self._scroll_timer = None

    def _ensure_scroll_timer(self) -> None:
        """确保滚动检查定时器运行；已运行则 noop。"""
        if self._scroll_timer is None or not getattr(
            self._scroll_timer, "_active", True
        ):
            self._scroll_timer = self.set_interval(0.2, self._scroll_check_timer)

    def _stop_scroll_timer(self) -> None:
        """停止滚动检查定时器（无滚动 1.5s 后调用）。"""
        if self._scroll_timer is not None:
            try:
                self._scroll_timer.stop()
            except Exception:
                pass
            self._scroll_timer = None

    def on_scroll(self) -> None:
        """监听滚动事件，只设置脏标记，延迟处理"""
        if self._suppress_scroll_event:
            return
        # ponytail: 懒启动定时器 — 首次 scroll 时才开 200ms 检查循环
        self._ensure_scroll_timer()
        # 只标记脏，不立即处理（避免频繁触发布局计算）
        self._scroll_dirty = True

    def _scroll_check_timer(self) -> None:
        """定时器回调：定期检查滚动位置（200ms 一次）"""
        # ponytail: 空闲 1.5s 后自动停止定时器 — 滚完就关，省 5 次/秒唤醒
        idle_window_ms = 1500
        if (
            not self._scroll_dirty
            and self._last_scroll_time > 0
            and (time.time() * 1000 - self._last_scroll_time) > idle_window_ms
        ):
            self._stop_scroll_timer()
            return
        if not self._scroll_dirty:
            return
        self._scroll_dirty = False
        current_time = time.time() * 1000
        if current_time - self._last_scroll_time < self._scroll_throttle_ms:
            return
        self._last_scroll_time = current_time
        self._do_deferred_scroll_check()

    def _do_deferred_scroll_check(self) -> None:
        """Check if user is at bottom — 使用缓存的 max_scroll_y"""
        # ponytail: 使用缓存的 max_scroll_y 避免频繁触发布局计算
        try:
            max_scroll = self._get_max_scroll_y_cached()
            current_y = self.scroll_y
            if (max_scroll - current_y) < 50:
                self._mark_scrolled_to_bottom()
            else:
                self._mark_scrolled_away()
        except Exception:
            pass

    def on_scroll_to(self, event) -> None:
        """监听 scroll_to 事件"""
        if self._suppress_scroll_event:
            return
        self.on_scroll()

    def scroll_to_bottom(self, animate: bool = True) -> None:
        """手动滚动到底部，同时标记用户在底部"""
        super().scroll_end(animate=animate)
        self._user_scrolled_to_bottom = True
        self._last_scroll_time = time.time() * 1000

    def _toggle_all_thinking(self, expanded: bool) -> None:
        """展开或收起所有思考内容"""
        for msg_id, msg in self._message_index.items():
            if not msg.thinking:
                continue
            msg.thinking_collapsed = not expanded
            body = self._message_thinking_bodies.get(msg_id)
            label = self._message_thinking_labels.get(msg_id)
            if body is not None:
                body.display = expanded
            if label is not None:
                label.update(self._format_thinking_label(msg))

    @on(Key)
    def _handle_thinking_key(self, event) -> None:
        """处理思考内容快捷键

        - 'e': 展开所有思考内容
        - 'c': 收起所有思考内容
        """
        key = event.key
        if key == "e":
            self._toggle_all_thinking(expanded=True)
        elif key == "c":
            self._toggle_all_thinking(expanded=False)


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
