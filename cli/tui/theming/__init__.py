#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TUI Theming System for Handsome Agent.

🚪 Access - 💬 CLI - Theming - 统一的样式和主题管理

提供：
- 主题配置管理 (ThemeManager)
- 颜色常量 (STATUS_ONLINE, STATUS_ERROR 等)
- 图标映射 (MESSAGE_ICONS, FILE_TYPE_ICONS 等)
- 透明度工具 (transparent 函数)
- 排版系统 (TypographyConfig)

Usage::

    from cli.tui.theming import ThemeManager, get_theme_manager

    manager = get_theme_manager()
    manager.set_theme("default")
    css = manager.get_current_css()

CSS 模块::

    from cli.tui.theming.css import get_stylesheets

    stylesheets = get_stylesheets()  # 返回 CSS 文件路径列表
"""

from __future__ import annotations

# 导入子模块
from .theme_config import (
    Theme,
    ThemeConfig,
    THEME_CONFIGS,
    generate_semantic_colors,
    generate_theme_css,
    get_all_theme_css,
)

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

from .theme_manager import (
    ThemeManager,
    get_theme_manager,
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

from .preset_themes import (
    _PRESET_THEMES,
)

# 计算半透明颜色（需要从 theme_config 导入 THEME_CONFIGS）
AVOCADO_ACCENT_10 = transparent(THEME_CONFIGS["default"].accent, TRANSPARENCY_LEVELS["sm"])
AVOCADO_ACCENT_25 = transparent(THEME_CONFIGS["default"].accent, TRANSPARENCY_LEVELS["lg"])
AVOCADO_ACCENT_50 = transparent(THEME_CONFIGS["default"].accent, TRANSPARENCY_LEVELS["xl"])

# 状态色透明版本
STATUS_ONLINE_15 = transparent(STATUS_ONLINE, TRANSPARENCY_LEVELS["md"])
STATUS_BUSY_10 = transparent(STATUS_BUSY, TRANSPARENCY_LEVELS["sm"])
STATUS_ERROR_15 = transparent(STATUS_ERROR, TRANSPARENCY_LEVELS["md"])
STATUS_WARNING_15 = transparent(STATUS_WARNING, TRANSPARENCY_LEVELS["md"])
STATUS_INFO_15 = transparent(STATUS_INFO, TRANSPARENCY_LEVELS["md"])

# 主题颜色常量
AVOCADO_PRIMARY = "#8B9A46"
AVOCADO_BRIGHT = "#A0B45A"
AVOCADO_DIM = "#647030"
AVOCADO_DARK = "#465A1E"
WHITE = "#FFFFFF"
GRAY_DIM = "#888888"
GOLD = "#B180D7"

__all__ = [
    # 数据类
    "Theme",
    "ThemeConfig",
    "TypographyConfig",
    # 主题配置
    "THEME_CONFIGS",
    "generate_semantic_colors",
    "generate_theme_css",
    "get_all_theme_css",
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
    "AVOCADO_ACCENT_10",
    "AVOCADO_ACCENT_25",
    "AVOCADO_ACCENT_50",
    "STATUS_ONLINE_15",
    "STATUS_BUSY_10",
    "STATUS_ERROR_15",
    "STATUS_WARNING_15",
    "STATUS_INFO_15",
    # 主题颜色常量
    "AVOCADO_PRIMARY",
    "AVOCADO_BRIGHT",
    "AVOCADO_DIM",
    "AVOCADO_DARK",
    "WHITE",
    "GRAY_DIM",
    "GOLD",
    # 预设主题
    "_PRESET_THEMES",
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
