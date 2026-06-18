#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Textual Theme System for Handsome Agent.

🚪 Access - 💬 CLI - Textual UI - 主题系统

基于 Textual CSS 的主题系统，支持：
- 两套预设主题（default/awesome）
- 动态主题切换
- 与皮肤引擎（skin_engine.py）保持兼容
- i18n 主题名称
- 用户主题偏好持久化

预设主题：

| 主题 ID | 名称 | 主色 |
|---------|------|------|
| default | 高雅紫 | #B180D7 |
| awesome | Awesome | #A9FC6E |

Usage::

    from cli.tui.themes import ThemeManager, get_theme_manager

    manager = get_theme_manager()
    manager.set_theme("awesome")
    css = manager.get_current_css()

向后兼容：
    所有从 cli.tui.themes 导入的代码仍然有效。
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

from .preset_themes import (
    _PRESET_THEMES,
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

__all__ = [
    # 数据类
    "Theme",
    "ThemeConfig",
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
    "TypographyConfig",
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
