#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TUI 主题/图标/排版工具（精简版）

🚪 Access - 💬 TUI - Theming - 图标与排版

v8.x→自定义主题系统已删除（迁移到 Textual 内置主题）。本模块现在
仅保留与主题无关的图标映射与排版配置，供 sidebar 等模块使用。
"""

from __future__ import annotations

# 图标映射（与主题无关，独立模块）
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

# 排版系统（与主题无关）
from .typography import (
    FONT_SIZE_XXS,
    FONT_SIZE_XS,
    FONT_SIZE_SM,
    FONT_SIZE_MD,
    FONT_SIZE_LG,
    FONT_SIZE_XL,
    FONT_SIZE_XXL,
    TypographyConfig,
    DEFAULT_TYPOGRAPHY,
    COMPACT_TYPOGRAPHY,
    LARGE_TYPOGRAPHY,
    TYPOGRAPHY_PRESETS,
    ELEMENT_FONT_CLASSES,
    get_typography_preset,
    generate_typography_css,
    generate_element_font_css,
)

__all__ = [
    # 图标
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
    # 排版
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
]