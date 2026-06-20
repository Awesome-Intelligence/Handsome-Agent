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
    """
    theme_id: str
    display_name_key: str


__all__ = [
    "Theme",
]
