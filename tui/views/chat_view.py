#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChatView - 聊天视图组件

🚪 Access - 💬 CLI - TUI Views - ChatView

提供独立的聊天会话界面，包括：
- 消息列表区域
- 输入区域
- 发送按钮
"""

from __future__ import annotations

from typing import TYPE_CHECKING

# 降级机制：如果 textual 不可用，提供友好提示
try:
    from textual.app import ComposeResult
    from textual.widgets import RichLog, Input, Button
    from textual.containers import Container, VerticalScroll
    from textual.message import Message
except ImportError:
    pass

# i18n 支持
try:
    from common.i18n import get_i18n, t
except ImportError:
    # 降级：简单的翻译函数
    def get_i18n():
        class SimpleI18n:
            def t(self, key, default=None, **kwargs):
                return default or key
        return SimpleI18n()
    
    def t(key, default=None, **kwargs):
        return default or key

# 日志支持
try:
    from common.logging_manager import get_access_logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    def get_access_logger(*args, **kwargs):
        return logging.getLogger("HandsomeAgent")


# ============================================================================
# ChatView CSS 样式
# ============================================================================

CHAT_VIEW_CSS = """
ChatView {
    height: 100%;
    width: 100%;
    layout: vertical;
}

#chat-messages {
    height: 1fr;
    width: 100%;
    background: $surface;
    border: solid $avocado_dim;
}

#chat-input-area {
    height: auto;
    width: 100%;
    padding: 1 2;
    background: $surface;
    border-top: solid $avocado_dim;
}

#chat-input-container {
    width: 100%;
    height: auto;
}

#chat-input {
    width: 1fr;
    border: solid $avocado_primary;
    background: $surface;
    color: $white;
}

#chat-input:focus {
    border: solid $avocado_bright;
}

#send-button {
    width: auto;
    min-width: 8;
    margin-left: 1;
}

.assistant-message {
    color: $avocado_bright;
}

.user-message {
    color: $white;
}

/* j/k 导航提示 */
.nav-hint {
    color: $gray_dim;
}
"""


# ============================================================================
# ChatView 类
# ============================================================================

class ChatView(Container):
    """聊天视图组件.
    
    提供独立的聊天会话界面，包含消息列表、输入框和发送按钮。
    
    Attributes:
        tab_id: 标签页 ID
        tab_title: 标签页标题
    """
    
    CSS = CHAT_VIEW_CSS
    
    def __init__(self, tab_id: str, tab_title: str | None = None, **kwargs):
        """初始化 ChatView.
        
        Args:
            tab_id: 标签页唯一标识
            tab_title: 标签页显示标题
            **kwargs: 传递给父类的其他参数
        """
        super().__init__(**kwargs)
        self.tab_id = tab_id
        self.tab_title = tab_title or t("chat.tab.default", "Chat")
        self._logger = get_access_logger("ChatView", sublayer="tui")
        self._message_history: list[dict[str, str]] = []
    
    def compose(self) -> ComposeResult:
        """组合聊天视图布局.
        
        Returns:
            ComposeResult: 组件生成器
        """
        # 消息列表区域
        with VerticalScroll(id="chat-messages"):
            yield RichLog(id="chat-log", auto_scroll=True)
        
        # 输入区域
        with Container(id="chat-input-area"):
            with Container(id="chat-input-container"):
                yield Input(
                    placeholder=t("chat.input.placeholder", "Type your message..."),
                    id="chat-input"
                )
                yield Button(
                    t("chat.button.send", "Send"),
                    id="send-button",
                    variant="primary"
                )
    
    def on_mount(self) -> None:
        """视图挂载时初始化."""
        self._logger.info(f"ChatView mounted: {self.tab_id}")
    
    def on_key(self, event: "Input.Key") -> None:
        """处理键盘事件，支持 j/k 导航."""
        key = event.key
        
        # 获取消息滚动区域
        messages_container = self.query_one("#chat-messages", VerticalScroll)
        
        if key == "j" or key == "down":
            # 向下滚动
            messages_container.scroll_down(animate=True)
            event.prevent_default()
        elif key == "k" or key == "up":
            # 向上滚动
            messages_container.scroll_up(animate=True)
            event.prevent_default()
    
    def append_message(self, role: str, content: str) -> None:
        """追加消息到聊天日志.
        
        Args:
            role: 消息角色 (user/assistant)
            content: 消息内容
        """
        # 保存到历史记录
        self._message_history.append({"role": role, "content": content})
        
        # 更新显示
        log = self.query_one("#chat-log", RichLog)
        if log:
            if role == "user":
                log.write(f"[bold #A0B45A]You:[/] {content}")
            elif role == "assistant":
                log.write(f"[bold #8B9A46]Agent:[/] {content}")
            else:
                log.write(f"[dim]{content}[/]")
    
    def clear_messages(self) -> None:
        """清空聊天消息."""
        self._message_history.clear()
        log = self.query_one("#chat-log", RichLog)
        if log:
            log.clear()
    
    def get_message_history(self) -> list[dict[str, str]]:
        """获取消息历史.
        
        Returns:
            消息历史列表
        """
        return self._message_history.copy()
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """处理输入框提交事件.
        
        Args:
            event: 输入提交事件
        """
        input_widget = self.query_one("#chat-input", Input)
        if input_widget.value.strip():
            # 发布消息提交事件
            self.post_message(ChatMessageSubmitted(self.tab_id, input_widget.value))
            input_widget.value = ""
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮按下事件.
        
        Args:
            event: 按钮按下事件
        """
        if event.button.id == "send-button":
            input_widget = self.query_one("#chat-input", Input)
            if input_widget.value.strip():
                # 发布消息提交事件
                self.post_message(ChatMessageSubmitted(self.tab_id, input_widget.value))
                input_widget.value = ""


# ============================================================================
# ChatView 消息类
# ============================================================================

class ChatMessageSubmitted(Message):
    """聊天消息提交事件.
    
    当用户在 ChatView 中提交消息时发布此事件。
    
    Attributes:
        tab_id: 标签页 ID
        message: 用户输入的消息内容
    """
    
    def __init__(self, tab_id: str, message: str) -> None:
        """初始化事件.
        
        Args:
            tab_id: 标签页 ID
            message: 消息内容
        """
        super().__init__()
        self.tab_id = tab_id
        self.message = message


# ============================================================================
# 模块导出
# ============================================================================

__all__ = [
    "ChatView",
    "ChatMessageSubmitted",
    "CHAT_VIEW_CSS",
]