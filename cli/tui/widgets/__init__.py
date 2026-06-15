#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TUI Widgets - Textual UI Widget Components

🚪 Access - 💬 CLI - TUI Widgets

提供 Textual TUI 所需的组件库，包括：
- StatusBar: 状态栏组件
- CommandPaletteScreen: 命令面板组件
- MessageList: 消息列表组件
- StreamingText: 流式文本渲染组件
- ApprovalDialog: 权限审批对话框
"""

from .status_bar import StatusBar

# 命令面板（带降级机制）
try:
    from .command_palette import CommandPaletteScreen, Command
except ImportError:
    CommandPaletteScreen = None
    Command = None

# 消息列表组件
try:
    from .message_list import (
        MessageList,
        MessageItem,
        MessageRole,
        MessageListUpdated,
        StreamingComplete,
        MessageClicked,
    )
except ImportError:
    MessageList = None
    MessageItem = None
    MessageRole = None
    MessageListUpdated = None
    StreamingComplete = None
    MessageClicked = None

# 流式文本组件
try:
    from .streaming_text import (
        StreamingText,
        StreamingState,
        TextType,
        StreamingStarted,
        StreamingUpdate,
        StreamingEnded,
        ThinkingToggled,
        create_streaming_text,
    )
except ImportError:
    StreamingText = None
    StreamingState = None
    TextType = None
    StreamingStarted = None
    StreamingUpdate = None
    StreamingEnded = None
    ThinkingToggled = None
    create_streaming_text = None

# 审批对话框组件
try:
    from .approval_dialog import (
        ApprovalDialog,
        ApprovalMode,
        RiskLevel,
        SENSITIVE_OPERATIONS,
        ApprovalManager,
        ApprovalRequested,
        ApprovalConfirmed,
        ApprovalRejected,
        create_approval_dialog,
    )
except ImportError:
    ApprovalDialog = None
    ApprovalMode = None
    RiskLevel = None
    SENSITIVE_OPERATIONS = None
    ApprovalManager = None
    ApprovalRequested = None
    ApprovalConfirmed = None
    ApprovalRejected = None
    create_approval_dialog = None

__all__ = [
    # 基础组件
    "StatusBar",
    "CommandPaletteScreen",
    "Command",
    # 消息列表
    "MessageList",
    "MessageItem",
    "MessageRole",
    "MessageListUpdated",
    "StreamingComplete",
    "MessageClicked",
    # 流式文本
    "StreamingText",
    "StreamingState",
    "TextType",
    "StreamingStarted",
    "StreamingUpdate",
    "StreamingEnded",
    "ThinkingToggled",
    "create_streaming_text",
    # 审批对话框
    "ApprovalDialog",
    "ApprovalMode",
    "RiskLevel",
    "SENSITIVE_OPERATIONS",
    "ApprovalManager",
    "ApprovalRequested",
    "ApprovalConfirmed",
    "ApprovalRejected",
    "create_approval_dialog",
]