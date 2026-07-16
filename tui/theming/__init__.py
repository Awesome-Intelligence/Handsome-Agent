#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TUI Theming System for Agent-Z.

🚪 Access - 💬 TUI - Theming - 样式和主题管理（向后兼容层）

v8.x 重构说明：
- 主题核心（``Theme`` / ``_PRESET_THEMES`` / ``ThemeManager``）已上移到
  ``common.theming``，本模块改为 re-export 保持向后兼容。
- 本地仍保留与 tui 绑定的工具：颜色辅助、图标映射、排版系统。
- ``tui.theming.css`` 子模块继续 re-export 自 ``common.theming.css``。

Usage::

    from tui.theming import ThemeManager, get_theme_manager  # 现在来自 common

    manager = get_theme_manager()
    manager.set_theme("default")

CSS 模块::

    from tui.theming.css import get_stylesheets

    stylesheets = get_stylesheets()  # 返回 CSS 文件路径列表
"""

from __future__ import annotations

# 主题核心：上移到 common 层，本模块 re-export 保持向后兼容
from common.theming import (
    Theme,
    _PRESET_THEMES,
    ThemeManager,
    get_theme_manager,
)

# tui 本地工具：颜色辅助、图标映射、排版系统
from .colors import (
    TRANSPARENCY_LEVELS,
    transparent,
    STATUS_ONLINE,
    STATUS_BUSY,
    STATUS_AWAY,
    STATUS_OFFLINE,
    STATUS_ERROR,
    STATUS_SUCCESS,
    STATUS_WARNING,
    STATUS_INFO,
)

from .icons import (
    MESSAGE_ICONS,
    MESSAGE_COLORS,
    FILE_TYPE_ICONS,
    get_file_icon,
    TASK_STATUS_ICONS,
    TASK_PRIORITY_ICONS,
    LOG_LEVEL_ICONS,
    get_log_icon,
    AGENT_STATUS_ICONS,
    PANEL_ICONS,
)

# 排版系统
from .typography import (
    # 字体大小常量
    FONT_SIZE_XXS,
    FONT_SIZE_XS,
    FONT_SIZE_SM,
    FONT_SIZE_MD,
    FONT_SIZE_LG,
    FONT_SIZE_XL,
    FONT_SIZE_XXL,
    # 配置
    TypographyConfig,
    DEFAULT_TYPOGRAPHY,
    COMPACT_TYPOGRAPHY,
    LARGE_TYPOGRAPHY,
    TYPOGRAPHY_PRESETS,
    ELEMENT_FONT_CLASSES,
    # 函数
    get_typography_preset,
    generate_typography_css,
    generate_element_font_css,
)

# 计算半透明颜色（使用 default 主题的紫色）
DEFAULT_ACCENT = "#B180D7"
PURPLE_ACCENT_10 = transparent(DEFAULT_ACCENT, TRANSPARENCY_LEVELS["sm"])
PURPLE_ACCENT_25 = transparent(DEFAULT_ACCENT, TRANSPARENCY_LEVELS["lg"])
PURPLE_ACCENT_50 = transparent(DEFAULT_ACCENT, TRANSPARENCY_LEVELS["xl"])

# 状态色透明版本
STATUS_ONLINE_15 = transparent(STATUS_ONLINE, TRANSPARENCY_LEVELS["md"])
STATUS_BUSY_10 = transparent(STATUS_BUSY, TRANSPARENCY_LEVELS["sm"])
STATUS_ERROR_15 = transparent(STATUS_ERROR, TRANSPARENCY_LEVELS["md"])
STATUS_WARNING_15 = transparent(STATUS_WARNING, TRANSPARENCY_LEVELS["md"])
STATUS_INFO_15 = transparent(STATUS_INFO, TRANSPARENCY_LEVELS["md"])

# 主题颜色常量（高雅紫）
PURPLE_PRIMARY = "#B180D7"
PURPLE_BRIGHT = "#C9A0E0"
PURPLE_DIM = "#9A6BC2"
PURPLE_DARK = "#7A4DA8"
WHITE = "#FFFFFF"
GRAY_DIM = "#888888"
GOLD = "#C9A0E0"

__all__ = [
    # 数据类
    "Theme",
    "TypographyConfig",
    # 主题配置
    "_PRESET_THEMES",
    # 管理器
    "ThemeManager",
    "get_theme_manager",
    # 排版系统
    "FONT_SIZE_XXS",
    "FONT_SIZE_XS",
    "FONT_SIZE_SM",
    "FONT_SIZE_MD",
    "FONT_SIZE_LG",
    "FONT_SIZE_XL",
    "FONT_SIZE_XXL",
    "DEFAULT_TYPOGRAPHY",
    "COMPACT_TYPOGRAPHY",
    "LARGE_TYPOGRAPHY",
    "TYPOGRAPHY_PRESETS",
    "ELEMENT_FONT_CLASSES",
    "get_typography_preset",
    "generate_typography_css",
    "generate_element_font_css",
    # 透明度系统
    "TRANSPARENCY_LEVELS",
    "transparent",
    # 状态颜色
    "STATUS_ONLINE",
    "STATUS_BUSY",
    "STATUS_AWAY",
    "STATUS_OFFLINE",
    "STATUS_ERROR",
    "STATUS_SUCCESS",
    "STATUS_WARNING",
    "STATUS_INFO",
    # 半透明颜色
    "PURPLE_ACCENT_10",
    "PURPLE_ACCENT_25",
    "PURPLE_ACCENT_50",
    "STATUS_ONLINE_15",
    "STATUS_BUSY_10",
    "STATUS_ERROR_15",
    "STATUS_WARNING_15",
    "STATUS_INFO_15",
    # 主题颜色常量
    "PURPLE_PRIMARY",
    "PURPLE_BRIGHT",
    "PURPLE_DIM",
    "PURPLE_DARK",
    "WHITE",
    "GRAY_DIM",
    "GOLD",
    # 消息类型
    "MESSAGE_ICONS",
    "MESSAGE_COLORS",
    # 文件类型图标
    "FILE_TYPE_ICONS",
    "get_file_icon",
    # 任务状态图标
    "TASK_STATUS_ICONS",
    # 任务优先级图标
    "TASK_PRIORITY_ICONS",
    # 日志级别图标
    "LOG_LEVEL_ICONS",
    "get_log_icon",
    # Agent 状态图标
    "AGENT_STATUS_ICONS",
    # 面板图标
    "PANEL_ICONS",
]