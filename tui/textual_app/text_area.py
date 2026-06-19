#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TextArea 组件模块

提供支持按 Enter 发送消息的 TextArea 子类。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from textual import events as textual_events

# 条件导入 Textual 组件
try:
    from textual.app import App
    from textual.widgets import TextArea
    from textual.message import Message
except ImportError:
    TextArea = None
    Message = object
    App = None


class SubmitTextArea(TextArea):
    """支持按 Enter 发送消息的 TextArea。
    
    - Enter（无修饰键）：触发 Submitted 事件（不插入换行）
    - Ctrl+Enter：插入换行（默认行为）
    
    内部使用自定义的 InputSubmitted 消息事件。
    """
    
    class InputSubmitted(Message):
        """输入提交事件（按 Enter 触发）。"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    async def _on_key(self, event: "textual_events.Key") -> None:
        """拦截 Enter 键：无修饰键时触发提交，否则保持默认行为。
        
        Args:
            event: 键盘事件
        """
        key = event.key
        
        # Enter without modifiers -> submit message
        # Textual 中修饰键编码在 key 字符串中：plain="enter", ctrl+enter="ctrl+enter"
        if key == "enter":
            event.stop()
            event.prevent_default()
            self.post_message(self.InputSubmitted())
            return
        
        # Ctrl+Enter / Shift+Enter / Alt+Enter -> insert newline (default behavior)
        # 这些 key 字符串包含 '+' 修饰符前缀
        if key.startswith("ctrl+") or key.startswith("shift+") or key.startswith("alt+"):
            await super()._on_key(event)
            return
        
        # 其他键保持默认行为
        await super()._on_key(event)
