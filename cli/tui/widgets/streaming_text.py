#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
StreamingText Widget - 流式文本渲染组件

🚪 Access - 💬 CLI - TUI Widgets - StreamingText

提供流式文本的逐字追加效果，支持思考内容和输出的分离显示。

Features:
- 文本逐字追加效果
- 思考/输出文本区分
- 可折叠/展开思考内容
- 配置开关控制是否显示思考
- 节流优化避免频繁 UI 更新
- 流式结束时触发事件

This module provides the streaming text rendering capabilities separate from
the message list, allowing for more flexible integration.
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import time

# Textual 框架导入（带降级机制）
TEXTUAL_AVAILABLE = True
try:
    from textual.widget import Widget
    from textual.message import Message
except ImportError:
    TEXTUAL_AVAILABLE = False
    Widget = object  # type: ignore
    Message = object  # type: ignore

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
COLOR_SUCCESS = "#4CAF50"        # 绿色
COLOR_WARNING = "#FF9800"        # 橙色
COLOR_DANGER = "#F44336"         # 红色
COLOR_INFO = "#2196F3"           # 蓝色

# 背景和文字颜色
WHITE = "white"
GRAY_DIM = "#888888"
GRAY_LIGHT = "#AAAAAA"
SURFACE = "#1a1a1a"


# ============================================================================
# 文本类型枚举
# ============================================================================

class TextType(Enum):
    """文本类型"""
    OUTPUT = "output"     # 普通输出文本
    THINKING = "thinking" # 思考内容
    TOOL = "tool"         # 工具执行输出
    ERROR = "error"      # 错误信息


# ============================================================================
# 流式文本状态
# ============================================================================

@dataclass
class StreamingState:
    """流式文本状态
    
    Attributes:
        text: 累积的文本
        text_type: 文本类型
        is_streaming: 是否正在流式输出
        start_time: 开始时间
        last_update: 最后更新时间
    """
    text: str = ""
    text_type: TextType = TextType.OUTPUT
    is_streaming: bool = False
    start_time: float = field(default_factory=time.time)
    last_update: float = field(default_factory=time.time)


# ============================================================================
# 流式文本事件
# ============================================================================

class StreamingStarted(Message):
    """流式开始事件"""
    def __init__(self, sender: Widget, text_type: TextType) -> None:
        super().__init__()
        self.text_type = text_type


class StreamingUpdate(Message):
    """流式更新事件"""
    def __init__(self, sender: Widget, text: str, delta: str) -> None:
        super().__init__()
        self.text = text
        self.delta = delta


class StreamingEnded(Message):
    """流式结束事件"""
    def __init__(self, sender: Widget, text: str, text_type: TextType, duration: float) -> None:
        super().__init__()
        self.text = text
        self.text_type = text_type
        self.duration = duration


class ThinkingToggled(Message):
    """思考内容折叠状态切换事件"""
    def __init__(self, sender: Widget, is_expanded: bool) -> None:
        super().__init__()
        self.is_expanded = is_expanded


# ============================================================================
# StreamingText Widget
# ============================================================================

class StreamingText(Widget):
    """流式文本渲染组件
    
    支持逐字追加效果和思考内容的分离显示。
    
    Features:
    - 文本逐字追加效果
    - 思考/输出文本区分
    - 可折叠/展开思考内容
    - 配置开关控制是否显示思考
    - 节流优化
    
    Attributes:
        show_thinking: 是否显示思考内容
        thinking_expanded: 思考内容是否展开
        throttle_ms: 节流时间（毫秒）
        buffer_size: 累积缓冲区大小
    """
    
    def __init__(
        self,
        show_thinking: bool = True,
        thinking_expanded: bool = False,
        throttle_ms: int = 50,
        buffer_size: int = 100,
        **kwargs
    ) -> None:
        """初始化流式文本组件
        
        Args:
            show_thinking: 是否显示思考内容
            thinking_expanded: 思考内容是否默认展开
            throttle_ms: 节流时间（毫秒）
            buffer_size: 累积缓冲区大小
            **kwargs: 传递给父类的参数
        """
        super().__init__(**kwargs)
        self.show_thinking = show_thinking
        self.thinking_expanded = thinking_expanded
        self.throttle_ms = throttle_ms
        self.buffer_size = buffer_size
        
        # 流式状态
        self._output_state = StreamingState(text_type=TextType.OUTPUT)
        self._thinking_state = StreamingState(text_type=TextType.THINKING)
        self._tool_state = StreamingState(text_type=TextType.TOOL)
        
        # 累积缓冲区
        self._output_buffer = ""
        self._thinking_buffer = ""
        
        # 渲染缓存
        self._render_cache = ""
        self._cache_dirty = True
        
        # 回调函数
        self._on_streaming_end: Optional[Callable[[str, str], None]] = None
        
        # 日志
        self._logger = get_access_logger("StreamingText", sublayer="cli")
    
    # ========================================================================
    # 流式控制方法
    # ========================================================================
    
    def start_streaming(
        self,
        text_type: str | TextType = TextType.OUTPUT,
        initial_text: str = ""
    ) -> None:
        """开始流式输出
        
        Args:
            text_type: 文本类型
            initial_text: 初始文本
        """
        # 转换文本类型
        if isinstance(text_type, str):
            type_enum = self._str_to_text_type(text_type)
        else:
            type_enum = text_type
        
        # 获取对应的状态
        state = self._get_state(type_enum)
        
        # 重置状态
        state.text = initial_text
        state.is_streaming = True
        state.start_time = time.time()
        state.last_update = time.time()
        
        # 发送开始事件
        self.post_message(StreamingStarted(self, type_enum))
        
        self._cache_dirty = True
        self.refresh()
        
        self._logger.debug(f"Streaming started: {type_enum.value}")
    
    def append_text(
        self,
        text: str,
        text_type: str | TextType = TextType.OUTPUT
    ) -> None:
        """追加文本（带节流优化）
        
        Args:
            text: 要追加的文本
            text_type: 文本类型
        """
        # 转换文本类型
        if isinstance(text_type, str):
            type_enum = self._str_to_text_type(text_type)
        else:
            type_enum = text_type
        
        # 获取对应的状态和缓冲区
        state = self._get_state(type_enum)
        buffer = self._get_buffer(type_enum)
        
        if not state.is_streaming:
            self._logger.warning(f"Streaming not started for type: {type_enum.value}")
            return
        
        # 累积到缓冲区
        buffer += text
        
        # 节流检查
        current_time = time.time() * 1000
        time_since_last_update = current_time - state.last_update
        
        if time_since_last_update < self.throttle_ms and len(buffer) < self.buffer_size:
            # 继续累积，稍后一起更新
            self._set_buffer(type_enum, buffer)
            return
        
        # 更新状态
        state.text += buffer
        state.last_update = current_time
        self._set_buffer(type_enum, "")
        
        # 发送更新事件
        self.post_message(StreamingUpdate(self, state.text, buffer))
        
        self._cache_dirty = True
        self.refresh()
    
    def end_streaming(
        self,
        text_type: str | TextType = TextType.OUTPUT
    ) -> str:
        """结束流式输出
        
        Args:
            text_type: 文本类型
            
        Returns:
            最终文本内容
        """
        # 转换文本类型
        if isinstance(text_type, str):
            type_enum = self._str_to_text_type(text_type)
        else:
            type_enum = text_type
        
        # 获取对应的状态
        state = self._get_state(type_enum)
        buffer = self._get_buffer(type_enum)
        
        # 刷新缓冲区剩余内容
        if buffer:
            state.text += buffer
            self._set_buffer(type_enum, "")
        
        # 标记结束
        state.is_streaming = False
        
        # 计算持续时间
        duration = time.time() - state.start_time
        
        # 发送结束事件
        self.post_message(StreamingEnded(self, state.text, type_enum, duration))
        
        # 触发回调
        if self._on_streaming_end:
            self._on_streaming_end(type_enum.value, state.text)
        
        self._cache_dirty = True
        self.refresh()
        
        self._logger.debug(f"Streaming ended: {type_enum.value}, duration={duration:.2f}s")
        return state.text
    
    def complete_streaming(self) -> tuple[str, str]:
        """完成所有流式输出
        
        Returns:
            (output_text, thinking_text) 元组
        """
        output_text = self.end_streaming(TextType.OUTPUT)
        thinking_text = self.end_streaming(TextType.THINKING)
        return output_text, thinking_text
    
    # ========================================================================
    # 内容访问方法
    # ========================================================================
    
    def get_output(self) -> str:
        """获取输出文本"""
        return self._output_state.text
    
    def get_thinking(self) -> str:
        """获取思考文本"""
        return self._thinking_state.text
    
    def get_tool_output(self) -> str:
        """获取工具输出文本"""
        return self._tool_state.text
    
    def get_all_text(self) -> str:
        """获取所有文本"""
        parts = []
        if self._output_state.text:
            parts.append(self._output_state.text)
        if self.show_thinking and self._thinking_state.text:
            if parts:
                parts.append("\n")
            parts.append(f"[思考过程]\n{self._thinking_state.text}")
        if self._tool_state.text:
            if parts:
                parts.append("\n")
            parts.append(self._tool_state.text)
        return "".join(parts)
    
    def clear(self) -> None:
        """清空所有文本"""
        self._output_state = StreamingState(text_type=TextType.OUTPUT)
        self._thinking_state = StreamingState(text_type=TextType.THINKING)
        self._tool_state = StreamingState(text_type=TextType.TOOL)
        self._output_buffer = ""
        self._thinking_buffer = ""
        self._render_cache = ""
        self._cache_dirty = True
        self.refresh()
        self._logger.debug("All text cleared")
    
    # ========================================================================
    # 思考内容控制
    # ========================================================================
    
    def toggle_thinking(self) -> None:
        """切换思考内容展开/折叠状态"""
        self.thinking_expanded = not self.thinking_expanded
        self._cache_dirty = True
        self.refresh()
        self.post_message(ThinkingToggled(self, self.thinking_expanded))
        self._logger.debug(f"Thinking toggled: expanded={self.thinking_expanded}")
    
    def set_show_thinking(self, show: bool) -> None:
        """设置是否显示思考内容
        
        Args:
            show: 是否显示
        """
        self.show_thinking = show
        self._cache_dirty = True
        self.refresh()
    
    # ========================================================================
    # 回调设置
    # ========================================================================
    
    def set_on_streaming_end(
        self,
        callback: Callable[[str, str], None]
    ) -> None:
        """设置流式结束回调
        
        Args:
            callback: 回调函数 (text_type, text) -> None
        """
        self._on_streaming_end = callback
    
    # ========================================================================
    # 内部方法
    # ========================================================================
    
    def _str_to_text_type(self, type_str: str) -> TextType:
        """将字符串转换为文本类型枚举"""
        type_map = {
            "output": TextType.OUTPUT,
            "thinking": TextType.THINKING,
            "think": TextType.THINKING,
            "tool": TextType.TOOL,
            "error": TextType.ERROR,
        }
        return type_map.get(type_str.lower(), TextType.OUTPUT)
    
    def _get_state(self, text_type: TextType) -> StreamingState:
        """获取对应文本类型的状态"""
        if text_type == TextType.THINKING:
            return self._thinking_state
        elif text_type == TextType.TOOL:
            return self._tool_state
        else:
            return self._output_state
    
    def _get_buffer(self, text_type: TextType) -> str:
        """获取对应文本类型的缓冲区"""
        if text_type == TextType.THINKING:
            return self._thinking_buffer
        else:
            return self._output_buffer
    
    def _set_buffer(self, text_type: TextType, buffer: str) -> None:
        """设置对应文本类型的缓冲区"""
        if text_type == TextType.THINKING:
            self._thinking_buffer = buffer
        else:
            self._output_buffer = buffer
    
    def _translate(self, key: str, default: str) -> str:
        """获取翻译文本"""
        i18n = get_i18n()
        result = i18n.t(key, default=default)
        if result == key:
            return default
        return result
    
    def _format_thinking_block(self, thinking: str) -> str:
        """格式化思考内容块
        
        Args:
            thinking: 思考内容
            
        Returns:
            格式化的思考内容字符串
        """
        if not thinking:
            return ""
        
        label = self._translate("tui.streaming.thinking", "思考过程")
        expand_icon = "▼" if self.thinking_expanded else "▶"
        
        if self.thinking_expanded:
            # 展开状态：显示完整内容
            return f"\n[{expand_icon}] {label}\n[{GRAY_DIM}]{thinking}[/]\n"
        else:
            # 折叠状态：只显示第一行
            first_line = thinking.split("\n")[0]
            if len(first_line) > 50:
                first_line = first_line[:50] + "..."
            return f"\n[{expand_icon}] {label}: {first_line}...[/]\n"
    
    # ========================================================================
    # 渲染方法
    # ========================================================================
    
    def render(self) -> str:
        """渲染流式文本
        
        Returns:
            格式化的文本字符串
        """
        if self._cache_dirty or self._output_state.is_streaming:
            self._render_cache = self._build_render_text()
            self._cache_dirty = False
        
        return self._render_cache
    
    def _build_render_text(self) -> str:
        """构建渲染文本"""
        parts = []
        
        # 输出文本
        if self._output_state.text:
            parts.append(self._output_state.text)
            if self._output_state.is_streaming:
                parts.append(" ▌")  # 光标指示器
        
        # 思考内容
        if self.show_thinking and self._thinking_state.text:
            parts.append(self._format_thinking_block(self._thinking_state.text))
        
        # 工具输出
        if self._tool_state.text:
            if parts:
                parts.append("\n")
            parts.append(f"[{COLOR_INFO}]{self._tool_state.text}[/]")
        
        return "".join(parts)
    
    def on_mount(self) -> None:
        """组件挂载时初始化"""
        self._logger.info("StreamingText mounted")
        self._cache_dirty = True
        self.refresh()


# ============================================================================
# 便捷函数
# ============================================================================

def create_streaming_text(
    show_thinking: bool = True,
    thinking_expanded: bool = False,
    **kwargs
) -> StreamingText:
    """创建流式文本组件（便捷函数）
    
    Args:
        show_thinking: 是否显示思考内容
        thinking_expanded: 思考内容是否默认展开
        **kwargs: 其他参数
        
    Returns:
        StreamingText 实例
    """
    return StreamingText(
        show_thinking=show_thinking,
        thinking_expanded=thinking_expanded,
        **kwargs
    )


# ============================================================================
# 模块导出
# ============================================================================

__all__ = [
    "StreamingText",
    "StreamingState",
    "TextType",
    "StreamingStarted",
    "StreamingUpdate",
    "StreamingEnded",
    "ThinkingToggled",
    "create_streaming_text",
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