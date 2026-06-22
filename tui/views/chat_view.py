#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChatView - 聊天消息显示组件

🚪 Access - 💬 CLI - TUI Views - ChatView

使用 MessageList 组件实现富文本消息显示，支持：
- 用户消息、助手消息、系统消息、工具消息
- 流式输出（打字机效果）
- 思考内容显示
- 错误消息高亮
- 自动滚动
"""

from __future__ import annotations

from typing import TYPE_CHECKING

# 降级机制：如果 textual 不可用，提供友好提示
try:
    from textual.app import ComposeResult
    from textual.containers import Container
except ImportError:
    pass

# MessageList 组件导入
try:
    from tui.widgets.message_list import MessageList, MessageRole
except ImportError:
    MessageList = None
    MessageRole = None

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
}

ChatView #chat-list {
    height: 100%;
    width: 100%;
    background: transparent;
}
"""


# ============================================================================
# ChatView 类
# ============================================================================

class ChatView(Container):
    """聊天消息显示组件.

    使用 MessageList 实现富文本消息显示，支持多种消息类型和流式输出。
    输入功能由外部的 #user-input 组件处理。

    Attributes:
        tab_id: 标签页 ID
    """

    CSS = CHAT_VIEW_CSS

    def __init__(self, tab_id: str = "main", **kwargs):
        """初始化 ChatView.

        Args:
            tab_id: 标签页唯一标识
            **kwargs: 传递给父类的其他参数
        """
        super().__init__(**kwargs)
        self.tab_id = tab_id
        self._logger = get_access_logger("ChatView", sublayer="tui")
        self._message_list: MessageList | None = None
        self._current_streaming_id: str | None = None

    def compose(self) -> ComposeResult:
        """组合聊天视图布局.

        Returns:
            ComposeResult: 组件生成器
        """
        # 消息列表区域 - 使用 MessageList 支持富文本和流式输出
        if MessageList:
            yield MessageList(
                id="chat-list",
                max_messages=200,
                auto_scroll=True,
                show_timestamps=True,
                show_role_icons=True,
                streaming_throttle_ms=30,
            )
        else:
            # 降级：如果 MessageList 不可用，使用占位符
            from textual.widgets import Static
            yield Static("[dim]MessageList not available[/dim]", id="chat-list")

    def on_mount(self) -> None:
        """视图挂载时初始化."""
        self._logger.info(f"ChatView mounted: {self.tab_id}")
        if MessageList:
            self._message_list = self.query_one("#chat-list", MessageList)

    # ========================================================================
    # 消息操作方法（保持 API 兼容性）
    # ========================================================================

    def append_message(self, role: str, content: str) -> None:
        """追加消息到聊天日志（兼容旧 API）.

        Args:
            role: 消息角色 (user/assistant/system/tool/error)
            content: 消息内容
        """
        if not self._message_list:
            self._logger.warning("MessageList not available")
            return

        # 保存到历史记录
        self._message_history.append({"role": role, "content": content})

        # 使用 MessageList 添加消息
        self._message_list.add_message(role, content)

    def clear_messages(self) -> None:
        """清空聊天消息."""
        self._message_history.clear()
        if self._message_list:
            self._message_list.clear_messages()

    def get_message_history(self) -> list[dict[str, str]]:
        """获取消息历史.

        Returns:
            消息历史列表
        """
        return self._message_history.copy()

    def write(self, text: str) -> None:
        """直接写入文本（兼容 RichLog 的 write 接口）.

        转换为 assistant 消息追加。

        Args:
            text: 要写入的文本
        """
        if self._message_list:
            self._message_list.add_assistant_message(text)

    def clear(self) -> None:
        """清空内容（兼容 RichLog 的 clear 接口）."""
        self.clear_messages()

    # ========================================================================
    # 流式输出方法
    # ========================================================================

    def start_streaming(self, role: str = "assistant") -> str:
        """开始流式输出.

        Args:
            role: 消息角色

        Returns:
            消息 ID
        """
        if not self._message_list:
            return ""

        self._current_streaming_id = self._message_list.start_streaming(role)
        return self._current_streaming_id

    def append_streaming_text(self, text: str) -> None:
        """追加流式文本.

        Args:
            text: 要追加的文本
        """
        if not self._message_list or not self._current_streaming_id:
            return

        self._message_list.append_streaming_text(self._current_streaming_id, text)

    def append_streaming_thinking(self, text: str) -> None:
        """追加思考内容.

        Args:
            text: 思考内容
        """
        if not self._message_list or not self._current_streaming_id:
            return

        self._message_list.append_streaming_thinking(self._current_streaming_id, text)

    def complete_streaming(self) -> None:
        """完成流式输出."""
        if not self._message_list or not self._current_streaming_id:
            return

        self._message_list.complete_streaming(self._current_streaming_id)
        self._current_streaming_id = None

    def cancel_streaming(self) -> None:
        """取消流式输出."""
        if self._current_streaming_id:
            self._message_list.remove_message(self._current_streaming_id)
            self._current_streaming_id = None

    # ========================================================================
    # 便捷消息方法
    # ========================================================================

    def add_user_message(self, content: str) -> str:
        """添加用户消息.

        Args:
            content: 消息内容

        Returns:
            消息 ID
        """
        self._message_history.append({"role": "user", "content": content})
        if self._message_list:
            return self._message_list.add_user_message(content)
        return ""

    def add_assistant_message(self, content: str) -> str:
        """添加助手消息.

        Args:
            content: 消息内容

        Returns:
            消息 ID
        """
        self._message_history.append({"role": "assistant", "content": content})
        if self._message_list:
            return self._message_list.add_assistant_message(content)
        return ""

    def add_system_message(self, content: str) -> str:
        """添加系统消息.

        Args:
            content: 消息内容

        Returns:
            消息 ID
        """
        self._message_history.append({"role": "system", "content": content})
        if self._message_list:
            return self._message_list.add_system_message(content)
        return ""

    def add_tool_message(self, content: str, tool_name: str) -> str:
        """添加工具执行消息.

        Args:
            content: 消息内容
            tool_name: 工具名称

        Returns:
            消息 ID
        """
        self._message_history.append({"role": "tool", "content": content})
        if self._message_list:
            return self._message_list.add_tool_message(content, tool_name)
        return ""

    def add_error_message(self, content: str) -> str:
        """添加错误消息.

        Args:
            content: 消息内容

        Returns:
            消息 ID
        """
        self._message_history.append({"role": "error", "content": content})
        if self._message_list:
            return self._message_list.add_error_message(content)
        return ""

    def add_thinking_message(self, content: str) -> str:
        """添加思考内容消息.

        Args:
            content: 思考内容

        Returns:
            消息 ID
        """
        if self._message_list:
            return self._message_list.add_thinking_message(content)
        return ""

    # ========================================================================
    # 辅助方法
    # ========================================================================

    def scroll_to_bottom(self) -> None:
        """滚动到底部."""
        if self._message_list:
            self._message_list.scroll_to_bottom()

    def get_message_count(self) -> int:
        """获取消息数量.

        Returns:
            消息数量
        """
        if self._message_list:
            return len(self._message_list.get_messages())
        return len(self._message_history)

    def is_streaming(self) -> bool:
        """检查是否正在流式输出.

        Returns:
            True 如果正在流式输出
        """
        return self._current_streaming_id is not None


# ============================================================================
# 模块导出
# ============================================================================

__all__ = [
    "ChatView",
    "CHAT_VIEW_CSS",
]