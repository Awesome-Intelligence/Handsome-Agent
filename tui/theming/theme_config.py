#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Theme Configuration Data Classes.

🚪 Access - 💬 CLI - Theming - 主题配置数据类
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict

# 日志支持
try:
    from common.logging_manager import get_access_logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    def get_access_logger(*args, **kwargs):
        return logging.getLogger("HandsomeAgent")

logger = logging.getLogger(__name__)


# ============================================================================
# Theme Data Structure
# ============================================================================


@dataclass
class Theme:
    """Textual 主题配置数据类.
    
    Attributes:
        theme_id: 主题唯一标识符
        display_name_key: i18n 键，用于显示主题名称
        colors: CSS 变量名到颜色值的映射
        transparency: 透明度配置 (0.0 完全透明 - 1.0 完全不透明)
    """
    theme_id: str
    display_name_key: str
    colors: Dict[str, str] = field(default_factory=dict)
    transparency: float = 1.0  # 默认不透明


# ============================================================================
# ThemeConfig - 语义化主题配置
# ============================================================================


@dataclass
class ThemeConfig:
    """语义化主题配置数据类.
    
    用于定义主题的强调色和其他样式变量。
    颜色变量通过 CSS 类（.theme-default 等）应用。
    """
    name: str
    accent: str
    accent_bright: str
    accent_dim: str
    accent_dark: str
    banner_color: str  # Banner 字体颜色
    input_border: str  # 输入框默认边框颜色
    input_border_focus: str  # 输入框聚焦边框颜色
    tab_indicator: str  # Tab 页签下划线颜色
    tab_active_color: str  # Tab 激活时文字颜色
    frame_border: str  # 外边框颜色


# 预设主题配置
THEME_CONFIGS: Dict[str, ThemeConfig] = {
    "default": ThemeConfig(
        name="Avocado Green",
        accent="#a371f7",
        accent_bright="#a371f7",
        accent_dim="#8b5acd",
        accent_dark="#6b4ea8",
        banner_color="#B180D7",
        input_border="#B180D7",
        input_border_focus="#a371f7",
        tab_indicator="#a371f7",
        tab_active_color="#a371f7",
        frame_border="#B180D7",
    ),
    "ares": ThemeConfig(
        name="War God",
        accent="#CD7F32",
        accent_bright="#E8A060",
        accent_dim="#A06028",
        accent_dark="#7A4520",
        banner_color="#E8A060",  # 亮橙色
        input_border="#A06028",  # 暗橙色
        input_border_focus="#CD7F32",  # 主题色
        tab_indicator="#CD7F32",  # 主题橙色
        tab_active_color="#CD7F32",  # 主题橙色
        frame_border="#E8A060",  # 亮橙色边框
    ),
    "mono": ThemeConfig(
        name="Monochrome",
        accent="#808080",
        accent_bright="#A0A0A0",
        accent_dim="#606060",
        accent_dark="#404040",
        banner_color="#A0A0A0",  # 亮灰色
        input_border="#606060",  # 暗灰色
        input_border_focus="#808080",  # 主题色
        tab_indicator="#808080",  # 主题灰色
        tab_active_color="#808080",  # 主题灰色
        frame_border="#A0A0A0",  # 亮灰色边框
    ),
    "slate": ThemeConfig(
        name="Cool Blue",
        accent="#607D8B",
        accent_bright="#78909C",
        accent_dim="#455A64",
        accent_dark="#37474F",
        banner_color="#78909C",  # 亮蓝色
        input_border="#455A64",  # 暗蓝色
        input_border_focus="#607D8B",  # 主题色
        tab_indicator="#607D8B",  # 主题蓝色
        tab_active_color="#607D8B",  # 主题蓝色
        frame_border="#78909C",  # 亮蓝色边框
    ),
}


def generate_semantic_colors(theme: ThemeConfig) -> Dict[str, str]:
    """生成 CSS 语义化颜色变量.
    
    Args:
        theme: ThemeConfig 实例
        
    Returns:
        CSS 变量名到颜色值的映射字典
    """
    return {
        "--accent": theme.accent,
        "--accent-bright": theme.accent_bright,
        "--accent-dim": theme.accent_dim,
        "--accent-dark": theme.accent_dark,
    }


def generate_theme_css(theme_id: str) -> str:
    """生成主题覆盖类 CSS 字符串.
    
    Args:
        theme_id: 主题 ID (default/awesome)
        
    Returns:
        主题 CSS 类定义字符串
    """
    theme = THEME_CONFIGS.get(theme_id, THEME_CONFIGS["default"])
    colors = generate_semantic_colors(theme)
    css_parts = [f".theme-{theme_id} {{"]
    for var, value in colors.items():
        css_parts.append(f"    {var}: {value};")
    css_parts.append("}")
    return "\n".join(css_parts)


def get_all_theme_css() -> str:
    """生成所有主题的 CSS 字符串.
    
    Returns:
        所有主题 CSS 类定义的组合字符串
    """
    return "\n\n".join(generate_theme_css(tid) for tid in THEME_CONFIGS)


__all__ = [
    "Theme",
    "ThemeConfig",
    "THEME_CONFIGS",
    "generate_semantic_colors",
    "generate_theme_css",
    "get_all_theme_css",
]
