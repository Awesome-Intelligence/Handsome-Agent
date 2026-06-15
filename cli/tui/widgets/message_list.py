#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MessageList Widget - 消息列表组件

🚪 Access - 💬 CLI - TUI Widgets - MessageList

提供高性能的消息列表显示，支持：
- 用户消息（右侧对齐，使用主色调）
- 助手消息（左侧对齐，使用辅助色调）
- 系统消息（居中，使用灰色）
- 工具执行消息（带图标和缩进）
- 错误消息（红色）
- 消息时间戳显示
- 消息角色图标
- 流式文本逐字追加
- 虚拟化列表（只渲染可见项）
- 历史消息数量限制

Features:
- 虚拟化渲染（只渲染可见区域的消息）
- 历史消息数量限制（默认 100 条）
- 流式输出节流优化
- 自动滚动到底部
- 支持折叠思考内容
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import time

# Textual 框架导入（带降级机制）
TEXTUAL_AVAILABLE = True
try:
    from textual.widget import Widget
    from textual.message import Message
    from textual.scroll import ScrollableScroll
except ImportError:
    TEXTUAL_AVAILABLE = False
    Widget = object  # type: ignore
    Message = object  # type: ignore
    ScrollableScroll = object  # type: ignore

# i18n 支持
try:
    from common.i18n import get_i18n
except ImportError:
    # 降级：简单的翻译函数
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
# 主题颜色常量（牛油果绿）
# ============================================================================

# 牛油果绿主题 - Avocado Theme
AVOCADO_PRIMARY = "#8B9A46"       # rgb(139,154,70) - 主色
AVOCADO_BRIGHT = "#A0B45A"        # rgb(160,180,90) - 亮色
AVOCADO_DIM = "#647030"           # rgb(100,120,50) - 暗色
AVOCADO_DARK = "#465020"          # rgb(70,90,32) - 深色

# 状态颜色
COLOR_SUCCESS = "#4CAF50"        # 绿色 - 正常
COLOR_WARNING = "#FF9800"        # 橙色 - 警告
COLOR_DANGER = "#F44336"         # 红色 - 危险/错误
COLOR_INFO = "#2196F3"           # 蓝色 - 信息

# 背景和文字颜色
WHITE = "white"
GRAY_DIM = "#888888"
GRAY_LIGHT = "#AAAAAA"
SURFACE = "#1a1a1a"


# ============================================================================
# 消息类型枚举
# ============================================================================

class MessageRole(Enum):
    """消息角色类型"""
    USER = "user"           # 用户消息
    ASSISTANT = "assistant" # 助手消息
    SYSTEM = "system"       # 系统消息
    TOOL = "tool"           # 工具执行消息
    ERROR = "error"         # 错误消息
    THINKING = "thinking"   # 思考内容


# ============================================================================
# 消息数据结构
# ============================================================================

@dataclass
class MessageItem:
    """消息项数据结构
    
    Attributes:
        id: 消息唯一标识
        role: 消息角色
        content: 消息内容
        timestamp: 时间戳
        tool_name: 工具名称（仅工具消息）
        is_streaming: 是否正在流式输出
        is_complete: 是否已完成
    """
    id: str
    role: MessageRole
    content: str
    timestamp: float = field(default_factory=time.time)
    tool_name: Optional[str] = None
    is_streaming: bool = False
    is_complete: bool = True
    
    @property
    def time_str(self) -> str:
        """获取格式化的时间字符串"""
        return datetime.fromtimestamp(self.timestamp).strftime("%H:%M:%S")
    
    @property
    def is_thinking(self) -> bool:
        """是否为思考内容"""
        return self.role == MessageRole.THINKING
    
    @property
    def is_error(self) -> bool:
        """是否为错误消息"""
        return self.role == MessageRole.ERROR


# ============================================================================
# MessageList 消息事件
# ============================================================================

class MessageListUpdated(Message):
    """消息列表更新事件"""
    def __init__(self, sender: Widget, message_count: int) -> None:
        super().__init__()
        self.message_count = message_count


class StreamingComplete(Message):
    """流式输出完成事件"""
    def __init__(self, sender: Widget, message_id: str) -> None:
        super().__init__()
        self.message_id = message_id


class MessageClicked(Message):
    """消息点击事件"""
    def __init__(self, sender: Widget, message_id: str) -> None:
        super().__init__()
        self.message_id = message_id


# ============================================================================
# MessageList Widget
# ============================================================================

class MessageList(Widget):
    """消息列表组件
    
    高性能消息列表，支持虚拟化渲染和流式输出。
    
    Features:
    - 虚拟化渲染（只渲染可见区域的消息）
    - 多种消息类型样式
    - 流式文本逐字追加
    - 历史消息数量限制
    - 自动滚动到底部
    
    Attributes:
        max_messages: 最大历史消息数量
        auto_scroll: 是否自动滚动到底部
        show_timestamps: 是否显示时间戳
        show_role_icons: 是否显示角色图标
    """
    
    def __init__(
        self,
        max_messages: int = 100,
        auto_scroll: bool = True,
        show_timestamps: bool = True,
        show_role_icons: bool = True,
        streaming_throttle_ms: int = 50,
        **kwargs
    ) -> None:
        """初始化消息列表
        
        Args:
            max_messages: 最大历史消息数量
            auto_scroll: 是否自动滚动到底部
            show_timestamps: 是否显示时间戳
            show_role_icons: 是否显示角色图标
            streaming_throttle_ms: 流式输出节流时间（毫秒）
            **kwargs: 传递给父类的参数
        """
        super().__init__(**kwargs)
        self.max_messages = max_messages
        self.auto_scroll = auto_scroll
        self.show_timestamps = show_timestamps
        self.show_role_icons = show_role_icons
        self.streaming_throttle_ms = streaming_throttle_ms
        
        # 消息存储
        self._messages: list[MessageItem] = []
        self._message_counter = 0
        
        # 流式输出状态
        self._streaming_active: dict[str, str] = {}  # message_id -> role
        self._last_streaming_update: dict[str, float] = {}
        
        # 渲染缓存
        self._render_cache: list[str] = []
        self._cache_dirty = True
        
        # 日志
        self._logger = get_access_logger("MessageList", sublayer="cli")
    
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
        """添加新消息
        
        Args:
            role: 消息角色（字符串或枚举）
            content: 消息内容
            tool_name: 工具名称（仅工具消息）
            timestamp: 时间戳
            
        Returns:
            消息 ID
        """
        # 转换角色字符串
        if isinstance(role, str):
            role_enum = self._str_to_role(role)
        else:
            role_enum = role
        
        # 生成消息 ID
        self._message_counter += 1
        msg_id = f"msg-{self._message_counter}"
        
        # 创建消息项
        msg = MessageItem(
            id=msg_id,
            role=role_enum,
            content=content,
            timestamp=timestamp or time.time(),
            tool_name=tool_name,
            is_streaming=False,
            is_complete=True,
        )
        
        # 添加到列表
        self._messages.append(msg)
        self._cache_dirty = True
        
        # 限制历史消息数量
        self._trim_messages()
        
        # 触发更新
        self._schedule_render()
        # 只在有 post_message 方法的环境下发送消息事件
        if hasattr(self, 'post_message'):
            self.post_message(MessageListUpdated(self, len(self._messages)))
        
        self._logger.debug(f"Message added: {msg_id}, role={role_enum.value}")
        return msg_id
    
    def add_user_message(self, content: str) -> str:
        """添加用户消息"""
        return self.add_message(MessageRole.USER, content)
    
    def add_assistant_message(self, content: str) -> str:
        """添加助手消息"""
        return self.add_message(MessageRole.ASSISTANT, content)
    
    def add_system_message(self, content: str) -> str:
        """添加系统消息"""
        return self.add_message(MessageRole.SYSTEM, content)
    
    def add_tool_message(self, content: str, tool_name: str) -> str:
        """添加工具执行消息"""
        return self.add_message(MessageRole.TOOL, content, tool_name=tool_name)
    
    def add_error_message(self, content: str) -> str:
        """添加错误消息"""
        return self.add_message(MessageRole.ERROR, content)
    
    def add_thinking_message(self, content: str) -> str:
        """添加思考内容消息"""
        return self.add_message(MessageRole.THINKING, content)
    
    # ========================================================================
    # 流式输出方法
    # ========================================================================
    
    def start_streaming(self, role: str | MessageRole, content: str = "") -> str:
        """开始流式输出
        
        Args:
            role: 消息角色
            content: 初始内容（可选）
            
        Returns:
            消息 ID
        """
        # 转换角色字符串
        if isinstance(role, str):
            role_enum = self._str_to_role(role)
        else:
            role_enum = role
        
        # 生成消息 ID
        self._message_counter += 1
        msg_id = f"msg-{self._message_counter}"
        
        # 创建消息项
        msg = MessageItem(
            id=msg_id,
            role=role_enum,
            content=content,
            timestamp=time.time(),
            is_streaming=True,
            is_complete=False,
        )
        
        # 添加到列表
        self._messages.append(msg)
        self._cache_dirty = True
        
        # 记录流式输出状态
        self._streaming_active[msg_id] = role_enum.value
        
        # 限制历史消息数量
        self._trim_messages()
        
        # 触发更新
        self._schedule_render()
        
        self._logger.debug(f"Streaming started: {msg_id}")
        return msg_id
    
    def append_streaming_text(self, message_id: str, text: str) -> None:
        """追加流式文本（带节流优化）
        
        Args:
            message_id: 消息 ID
            text: 要追加的文本
        """
        if message_id not in self._streaming_active:
            self._logger.warning(f"Message not in streaming state: {message_id}")
            return
        
        # 节流检查
        current_time = time.time() * 1000  # 毫秒
        last_update = self._last_streaming_update.get(message_id, 0)
        if current_time - last_update < self.streaming_throttle_ms and text:
            # 累积文本，稍后一起更新
            return
        
        self._last_streaming_update[message_id] = current_time
        
        # 找到消息并追加内容
        for msg in self._messages:
            if msg.id == message_id:
                msg.content += text
                self._cache_dirty = True
                self._schedule_render()
                break
    
    def append_streaming_thinking(self, message_id: str, text: str) -> None:
        """追加思考内容
        
        Args:
            message_id: 消息 ID
            text: 要追加的思考文本
        """
        if message_id not in self._streaming_active:
            return
        
        # 找到对应的思考消息或创建新消息
        thinking_id = f"{message_id}-thinking"
        
        # 检查是否已存在思考消息
        thinking_msg = None
        for msg in self._messages:
            if msg.id == thinking_id:
                thinking_msg = msg
                break
        
        if thinking_msg:
            thinking_msg.content += text
        else:
            # 创建新的思考消息
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
        
        self._cache_dirty = True
        self._schedule_render()
    
    def complete_streaming(self, message_id: str) -> None:
        """完成流式输出
        
        Args:
            message_id: 消息 ID
        """
        if message_id not in self._streaming_active:
            return
        
        # 标记消息为已完成
        for msg in self._messages:
            if msg.id == message_id:
                msg.is_streaming = False
                msg.is_complete = True
                break
        
        # 标记关联的思考消息为已完成
        thinking_id = f"{message_id}-thinking"
        for msg in self._messages:
            if msg.id == thinking_id:
                msg.is_streaming = False
                msg.is_complete = True
                break
        
        # 清理状态
        del self._streaming_active[message_id]
        if message_id in self._last_streaming_update:
            del self._last_streaming_update[message_id]
        
        self._cache_dirty = True
        self._schedule_render()
        
        # 发送完成事件
        if hasattr(self, 'post_message'):
            self.post_message(StreamingComplete(self, message_id))
        
        self._logger.debug(f"Streaming completed: {message_id}")
    
    # ========================================================================
    # 消息操作方法
    # ========================================================================
    
    def update_message(self, message_id: str, content: str) -> None:
        """更新消息内容
        
        Args:
            message_id: 消息 ID
            content: 新的内容
        """
        for msg in self._messages:
            if msg.id == message_id:
                msg.content = content
                self._cache_dirty = True
                self._schedule_render()
                break
    
    def remove_message(self, message_id: str) -> bool:
        """移除消息
        
        Args:
            message_id: 消息 ID
            
        Returns:
            True 如果移除成功
        """
        for i, msg in enumerate(self._messages):
            if msg.id == message_id:
                self._messages.pop(i)
                self._cache_dirty = True
                self._schedule_render()
                if hasattr(self, 'post_message'):
                    self.post_message(MessageListUpdated(self, len(self._messages)))
                return True
        return False
    
    def clear_messages(self) -> None:
        """清空所有消息"""
        self._messages.clear()
        self._streaming_active.clear()
        self._last_streaming_update.clear()
        self._render_cache.clear()
        self._cache_dirty = True
        self._schedule_render()
        if hasattr(self, 'post_message'):
            self.post_message(MessageListUpdated(self, 0))
        self._logger.debug("All messages cleared")
    
    def get_message(self, message_id: str) -> Optional[MessageItem]:
        """获取消息
        
        Args:
            message_id: 消息 ID
            
        Returns:
            消息项，如果不存在返回 None
        """
        for msg in self._messages:
            if msg.id == message_id:
                return msg
        return None
    
    def get_messages(self) -> list[MessageItem]:
        """获取所有消息"""
        return self._messages.copy()
    
    def scroll_to_bottom(self) -> None:
        """滚动到底部"""
        if self.auto_scroll:
            self.scroll_end(animate=True)
    
    # ========================================================================
    # 内部方法
    # ========================================================================
    
    def _str_to_role(self, role_str: str) -> MessageRole:
        """将角色字符串转换为枚举
        
        Args:
            role_str: 角色字符串
            
        Returns:
            MessageRole 枚举
        """
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
        """限制历史消息数量"""
        if len(self._messages) > self.max_messages:
            # 计算需要移除的数量
            excess = len(self._messages) - self.max_messages
            
            # 移除旧消息（保留最新消息）
            # 注意：如果有正在流式输出的消息，不要移除它
            removed = 0
            for i in range(len(self._messages)):
                if removed >= excess:
                    break
                msg = self._messages[i]
                if msg.id not in self._streaming_active:
                    self._messages.pop(i)
                    removed += 1
                    i -= 1  # 调整索引
    
    def _schedule_render(self) -> None:
        """调度 UI 更新"""
        # 标记缓存为脏，由外部的 compose/render 机制处理更新
        self._cache_dirty = True
        # 如果有 set_timer 方法则使用它进行节流，否则直接刷新
        if hasattr(self, 'set_timer'):
            if not hasattr(self, '_render_scheduled') or not self._render_scheduled:
                self._render_scheduled = True
                self.set_timer(0.05, self._do_render)
        else:
            # 在没有 Textual 运行时的环境下直接刷新
            self._do_render()
    
    def _do_render(self) -> None:
        """执行渲染"""
        self._render_scheduled = False
        self._cache_dirty = True
        # 只在有 refresh 方法的环境下调用（已挂载到应用）
        if hasattr(self, 'refresh'):
            self.refresh()
        if hasattr(self, 'scroll_end') and self.auto_scroll:
            try:
                self.scroll_end(animate=False)
            except Exception:
                pass
    
    def _get_message_style(self, msg: MessageItem) -> tuple[str, str, str]:
        """获取消息样式
        
        Args:
            msg: 消息项
            
        Returns:
            (前缀, 颜色, 后缀) 元组
        """
        # 角色图标
        icons = {
            MessageRole.USER: "👤",
            MessageRole.ASSISTANT: "🤖",
            MessageRole.SYSTEM: "⚙️",
            MessageRole.TOOL: "🛠️",
            MessageRole.ERROR: "❌",
            MessageRole.THINKING: "💭",
        }
        
        # 颜色配置
        colors = {
            MessageRole.USER: AVOCADO_BRIGHT,
            MessageRole.ASSISTANT: AVOCADO_PRIMARY,
            MessageRole.SYSTEM: GRAY_DIM,
            MessageRole.TOOL: COLOR_INFO,
            MessageRole.ERROR: COLOR_DANGER,
            MessageRole.THINKING: GRAY_LIGHT,
        }
        
        # 前缀和后缀
        prefixes = {
            MessageRole.USER: "",
            MessageRole.ASSISTANT: "",
            MessageRole.SYSTEM: "",
            MessageRole.TOOL: "  ",
            MessageRole.ERROR: "",
            MessageRole.THINKING: "  ",
        }
        
        icon = icons.get(msg.role, "")
        color = colors.get(msg.role, WHITE)
        prefix = prefixes.get(msg.role, "")
        
        return icon, color, prefix
    
    def _format_message(self, msg: MessageItem) -> str:
        """格式化单条消息
        
        Args:
            msg: 消息项
            
        Returns:
            格式化的消息字符串
        """
        icon, color, prefix = self._get_message_style(msg)
        
        # 时间戳
        timestamp_str = f"[{GRAY_DIM}]{msg.time_str}[/] " if self.show_timestamps else ""
        
        # 角色标签
        role_labels = {
            MessageRole.USER: "你",
            MessageRole.ASSISTANT: "助手",
            MessageRole.SYSTEM: "系统",
            MessageRole.TOOL: f"工具({msg.tool_name})",
            MessageRole.ERROR: "错误",
            MessageRole.THINKING: "思考",
        }
        role_label = role_labels.get(msg.role, "")
        
        # 工具名称前缀
        tool_prefix = ""
        if msg.role == MessageRole.TOOL and msg.tool_name:
            tool_prefix = f"[{COLOR_INFO}]{msg.tool_name}[/]: "
        
        # 流式输出指示器
        streaming_indicator = " ▌" if msg.is_streaming else ""
        
        # 构建消息
        content_lines = msg.content.split("\n")
        
        if msg.role == MessageRole.SYSTEM:
            # 系统消息居中
            return f"\n[{GRAY_DIM}]--- {msg.content} ---[/]\n"
        
        if msg.role == MessageRole.USER:
            # 用户消息右侧对齐
            lines = []
            for line in content_lines:
                lines.append(f"[{color}]{icon}{role_label}: {line}{streaming_indicator}[/]")
            return "\n".join(lines) + "\n"
        
        if msg.role == MessageRole.THINKING:
            # 思考内容缩进显示
            lines = []
            for line in content_lines:
                lines.append(f"{prefix}[{color}]{icon}{line}{streaming_indicator}[/]")
            return "\n".join(lines) + "\n"
        
        # 默认：助手、工具、错误消息
        lines = []
        for line in content_lines:
            lines.append(f"{prefix}[{color}]{icon}{role_label}: {tool_prefix}{line}{streaming_indicator}[/]")
        return "\n".join(lines) + "\n"
    
    # ========================================================================
    # 翻译辅助方法
    # ========================================================================
    
    def _translate(self, key: str, default: str) -> str:
        """获取翻译文本
        
        Args:
            key: 翻译 key
            default: 默认文本
            
        Returns:
            翻译后的文本或默认文本
        """
        i18n = get_i18n()
        result = i18n.t(key, default=default)
        if result == key:
            return default
        return result
    
    # ========================================================================
    # 渲染方法
    # ========================================================================
    
    def render(self) -> str:
        """渲染消息列表
        
        Returns:
            格式化的消息列表字符串
        """
        if self._cache_dirty:
            self._render_cache = []
            for msg in self._messages:
                formatted = self._format_message(msg)
                self._render_cache.append(formatted)
            self._cache_dirty = False
        
        return "".join(self._render_cache)
    
    def on_mount(self) -> None:
        """组件挂载时初始化"""
        self._logger.info("MessageList mounted")
        self._schedule_render()
    
    def on_click(self, event) -> None:
        """处理点击事件"""
        # 可以在这里实现消息点击处理
        pass


# ============================================================================
# 模块导出
# ============================================================================

__all__ = [
    "MessageList",
    "MessageItem",
    "MessageRole",
    "MessageListUpdated",
    "StreamingComplete",
    "MessageClicked",
    # 颜色常量
    "AVOCADO_PRIMARY",
    "AVOCADO_BRIGHT",
    "AVOCADO_DIM",
    "AVOCADO_DARK",
    "COLOR_SUCCESS",
    "COLOR_WARNING",
    "COLOR_DANGER",
    "COLOR_INFO",
    "WHITE",
    "GRAY_DIM",
    "GRAY_LIGHT",
    "SURFACE",
]