#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Theme Configuration Data Classes.

🚪 Access - 💬 CLI - Theming - 主题配置数据类

每个主题的样式定义在对应的 CSS 文件中（css/themes/*.css）。
"""

from __future__ import annotations

from dataclasses import dataclass


# ============================================================================
# Theme Data Structure
# ============================================================================


@dataclass
class Theme:
    """Textual 主题配置数据类.

    Attributes:
        theme_id: 主题唯一标识符
        display_name_key: i18n 键，用于显示主题名称
        primary: 主强调色
        secondary: 次强调色
        accent: 强调色
        foreground: 前景/文字色
        background: 背景色
        surface: 表面色
        panel: 面板色
        success: 成功色
        warning: 警告色
        error: 错误色
        banner_color: Banner 文字颜色
    """
    theme_id: str
    display_name_key: str
    primary: str = "#B180D7"
    secondary: str = "#C9A0E0"
    accent: str = "#B180D7"
    foreground: str = "#FFFFFF"
    background: str = "#1a1a1a"
    surface: str = "#2a2a2a"
    panel: str = "#1a1a1a"
    success: str = "#4CAF50"
    warning: str = "#FF9800"
    error: str = "#F44336"
    banner_color: str = "#C9A0E0"


__all__ = [
    "Theme",
]
