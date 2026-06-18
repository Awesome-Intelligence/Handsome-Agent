#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Icon Mappings for UI Elements.

🚪 Access - 💬 CLI - Textual UI - 图标映射
"""

from __future__ import annotations

from pathlib import Path


# ============================================================================
# 消息类型图标和颜色
# ============================================================================

# 消息类型图标
MESSAGE_ICONS = {
    "USER": "🧑",
    "ASSISTANT": "🤖",
    "SYSTEM": "⚙️",
    "TOOL": "🔧",
    "ERROR": "❌",
    "THINKING": "💭",
    "APPROVAL": "✅",
}

# 消息类型颜色
MESSAGE_COLORS = {
    "USER": "#58a6ff",  # 蓝色
    "ASSISTANT": "#3fb950",  # 绿色
    "SYSTEM": "#8b949e",  # 灰色
    "TOOL": "#a371f7",  # 紫色
    "ERROR": "#f85149",  # 红色
    "THINKING": "#f0883e",  # 橙色
    "APPROVAL": "#3fb950",  # 绿色
}


# ============================================================================
# 文件类型图标
# ============================================================================

FILE_TYPE_ICONS = {
    ".py": "🐍",  # Python
    ".rs": "🦀",  # Rust
    ".js": "📜",  # JavaScript
    ".ts": "📘",  # TypeScript
    ".jsx": "⚛️",  # React JavaScript
    ".tsx": "⚛️",  # React TypeScript
    ".vue": "💚",  # Vue
    ".svelte": "🔥",  # Svelte
    ".go": "🐹",  # Go
    ".java": "☕",  # Java
    ".c": "©",  # C
    ".cpp": "➕",  # C++
    ".h": "📎",  # Header
    ".hpp": "📎",  # C++ Header
    ".cs": "🔷",  # C#
    ".rb": "💎",  # Ruby
    ".php": "🐘",  # PHP
    ".swift": "🦅",  # Swift
    ".kt": "🎯",  # Kotlin
    ".scala": "⚡",  # Scala
    ".md": "📝",  # Markdown
    ".txt": "📄",  # Text
    ".json": "📋",  # JSON
    ".yaml": "📄",  # YAML
    ".yml": "📄",  # YAML (short)
    ".toml": "⚙️",  # TOML
    ".xml": "📰",  # XML
    ".html": "🌐",  # HTML
    ".htm": "🌐",  # HTML (short)
    ".css": "🎨",  # CSS
    ".scss": "🎨",  # SCSS
    ".sass": "🎨",  # Sass
    ".less": "🎨",  # Less
    ".sql": "🗃️",  # SQL
    ".sh": "💻",  # Shell
    ".bash": "💻",  # Bash
    ".zsh": "💻",  # Zsh
    ".ps1": "🖥️",  # PowerShell
    ".bat": "🖥️",  # Batch
    ".dockerfile": "🐳",  # Docker
    ".gitignore": "📁",  # Git
    ".env": "🔐",  # Environment
    ".cfg": "⚙️",  # Config
    ".conf": "⚙️",  # Config
    ".ini": "⚙️",  # Config
    ".png": "🖼️",  # Image
    ".jpg": "🖼️",  # Image
    ".jpeg": "🖼️",  # Image
    ".gif": "🖼️",  # Image
    ".svg": "🖼️",  # Image
    ".ico": "🖼️",  # Image
    ".pdf": "📕",  # PDF
    ".zip": "📦",  # Archive
    ".tar": "📦",  # Archive
    ".gz": "📦",  # Archive
    ".rar": "📦",  # Archive
    ".7z": "📦",  # Archive
    ".mp3": "🎵",  # Audio
    ".wav": "🎵",  # Audio
    ".mp4": "🎬",  # Video
    ".mov": "🎬",  # Video
    ".avi": "🎬",  # Video
    ".exe": "⚡",  # Executable
    ".dll": "⚙️",  # Library
    ".so": "⚙️",  # Shared Object
    ".a": "📚",  # Static Library
    ".o": "📚",  # Object File
    ".default": "📄",  # 默认
}


def get_file_icon(filename: str) -> str:
    """根据文件名获取对应的图标.
    
    Args:
        filename: 文件名（可包含路径）
        
    Returns:
        对应的 Emoji 图标
    """
    _, ext = Path(filename).suffix.lower()
    return FILE_TYPE_ICONS.get(ext, FILE_TYPE_ICONS[".default"])


# ============================================================================
# 任务状态图标
# ============================================================================

TASK_STATUS_ICONS = {
    "todo": "📋",  # 待办
    "pending": "⏳",  # 等待中
    "in_progress": "🔄",  # 进行中
    "done": "✅",  # 完成
    "completed": "✅",  # 完成 (别名)
    "success": "✅",  # 成功
    "failed": "❌",  # 失败
    "error": "❌",  # 错误
    "blocked": "🚫",  # 阻塞
    "cancelled": "🚪",  # 取消
    "skipped": "⏭️",  # 跳过
}


# ============================================================================
# 任务优先级图标
# ============================================================================

TASK_PRIORITY_ICONS = {
    "urgent": "🔴",  # 紧急
    "high": "🟠",  # 高
    "medium": "🟡",  # 中
    "normal": "🟡",  # 正常
    "low": "🟢",  # 低
    "lowest": "⚪",  # 最低
}


# ============================================================================
# 日志级别图标
# ============================================================================

LOG_LEVEL_ICONS = {
    "DEBUG": "🐛",  # 调试
    "INFO": "ℹ️",  # 信息
    "WARNING": "⚠️",  # 警告
    "WARN": "⚠️",  # 警告 (别名)
    "ERROR": "❌",  # 错误
    "ERR": "❌",  # 错误 (别名)
    "CRITICAL": "☠️",  # 严重
    "FATAL": "💀",  # 致命
    "SUCCESS": "✅",  # 成功
    "VERBOSE": "📣",  # 详细
}


def get_log_icon(level: str) -> str:
    """根据日志级别获取对应的图标.
    
    Args:
        level: 日志级别字符串
        
    Returns:
        对应的 Emoji 图标
    """
    return LOG_LEVEL_ICONS.get(level.upper(), "ℹ️")


# ============================================================================
# Agent 状态图标
# ============================================================================

AGENT_STATUS_ICONS = {
    "idle": "🟢",  # 空闲
    "busy": "🟠",  # 忙碌
    "thinking": "💭",  # 思考中
    "working": "⚙️",  # 工作中
    "error": "🔴",  # 错误
    "offline": "⚫",  # 离线
    "connected": "🟢",  # 已连接
    "disconnected": "⚫",  # 已断开
    "loading": "⏳",  # 加载中
}


# ============================================================================
# 面板图标
# ============================================================================

PANEL_ICONS = {
    "file_tree": "📁",  # 文件树
    "tasks": "📋",  # 任务
    "agent": "🤖",  # Agent
    "logs": "📜",  # 日志
    "search": "🔍",  # 搜索
    "settings": "⚙️",  # 设置
    "help": "❓",  # 帮助
    "terminal": "💻",  # 终端
}


__all__ = [
    "MESSAGE_ICONS",
    "MESSAGE_COLORS",
    "FILE_TYPE_ICONS",
    "get_file_icon",
    "TASK_STATUS_ICONS",
    "TASK_PRIORITY_ICONS",
    "LOG_LEVEL_ICONS",
    "get_log_icon",
    "AGENT_STATUS_ICONS",
    "PANEL_ICONS",
]
