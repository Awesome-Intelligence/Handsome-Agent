#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Preset Theme Definitions.

🚪 Access - 💬 CLI - Theming - 预设主题定义

每个主题的样式定义在对应的 CSS 文件中：
- default: css/themes/default.css
- awesome: css/themes/awesome.css

Theme 对象仅存储主题元数据（ID、名称）。
"""

from __future__ import annotations

from typing import Dict

from .theme_config import Theme


# ============================================================================
# Preset Themes
# ============================================================================


def _create_default_theme() -> Theme:
    """创建默认主题 (Avocado Green)."""
    return Theme(
        theme_id="default",
        display_name_key="tui.theme.default.name",
    )


def _create_awesome_theme() -> Theme:
    """创建 Awesome 主题 (Vibrant Green)."""
    return Theme(
        theme_id="awesome",
        display_name_key="tui.theme.awesome.name",
    )


# 预设主题注册表
_PRESET_THEMES: Dict[str, Theme] = {
    "default": _create_default_theme(),
    "awesome": _create_awesome_theme(),
}


__all__ = [
    "_create_default_theme",
    "_create_awesome_theme",
    "_PRESET_THEMES",
]
