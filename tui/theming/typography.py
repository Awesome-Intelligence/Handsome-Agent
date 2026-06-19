#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Typography System for Textual UI.

🚪 Access - 💬 CLI - Theming - 排版系统
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


# ============================================================================
# 字体大小常量
# ============================================================================

FONT_SIZE_XXS = 9
FONT_SIZE_XS = 10
FONT_SIZE_SM = 12
FONT_SIZE_MD = 14
FONT_SIZE_LG = 16
FONT_SIZE_XL = 18
FONT_SIZE_XXL = 22


# ============================================================================
# Typography Config
# ============================================================================


@dataclass
class TypographyConfig:
    """排版配置数据类.
    
    Attributes:
        font_size: 基础字体大小
        line_height: 行高
        heading_scale: 标题缩放比例
        code_font: 代码字体
        ui_font: UI 字体
    """
    font_size: int = FONT_SIZE_MD
    line_height: float = 1.4
    heading_scale: float = 1.25
    code_font: str = "JetBrains Mono"
    ui_font: str = "JetBrains Mono"


# 预设排版配置
DEFAULT_TYPOGRAPHY = TypographyConfig(
    font_size=FONT_SIZE_MD,
    line_height=1.4,
    heading_scale=1.25,
)

COMPACT_TYPOGRAPHY = TypographyConfig(
    font_size=FONT_SIZE_SM,
    line_height=1.3,
    heading_scale=1.2,
)

LARGE_TYPOGRAPHY = TypographyConfig(
    font_size=FONT_SIZE_LG,
    line_height=1.5,
    heading_scale=1.3,
)

TYPOGRAPHY_PRESETS: Dict[str, TypographyConfig] = {
    "default": DEFAULT_TYPOGRAPHY,
    "compact": COMPACT_TYPOGRAPHY,
    "large": LARGE_TYPOGRAPHY,
}


# ============================================================================
# 元素字体类
# ============================================================================


ELEMENT_FONT_CLASSES: Dict[str, str] = {
    # 标题
    "h1": "font-xxl",
    "h2": "font-xl",
    "h3": "font-lg",
    "h4": "font-md",
    "h5": "font-sm",
    "h6": "font-xs",
    # 文本
    "body": "font-md",
    "caption": "font-sm",
    "small": "font-xs",
    # 代码
    "code": "font-sm",
    # UI 元素
    "button": "font-md",
    "input": "font-md",
    "label": "font-sm",
}


# ============================================================================
# Typography Functions
# ============================================================================


def get_typography_preset(name: str) -> TypographyConfig:
    """获取排版预设.
    
    Args:
        name: 预设名称 (default, compact, large)
        
    Returns:
        TypographyConfig 实例
    """
    return TYPOGRAPHY_PRESETS.get(name, DEFAULT_TYPOGRAPHY)


def generate_typography_css(config: TypographyConfig) -> str:
    """生成排版 CSS.
    
    Args:
        config: 排版配置
    
    Returns:
        CSS 字符串
    """
    return f"""
/* Typography CSS */
Screen {{
    font-size: {config.font_size};
    line-height: {config.line_height};
}}

.font-xxl {{ font-size: {int(config.font_size * config.heading_scale ** 2)}; }}
.font-xl {{ font-size: {int(config.font_size * config.heading_scale)}; }}
.font-lg {{ font-size: {config.font_size + 2}; }}
.font-md {{ font-size: {config.font_size}; }}
.font-sm {{ font-size: {config.font_size - 2}; }}
.font-xs {{ font-size: {config.font_size - 4}; }}
"""


def generate_element_font_css() -> str:
    """生成元素字体 CSS.
    
    Returns:
        CSS 字符串
    """
    return """
/* Element Font Classes */
.font-xxl { font-size: 22; font-weight: bold; }
.font-xl { font-size: 18; font-weight: bold; }
.font-lg { font-size: 16; }
.font-md { font-size: 14; }
.font-sm { font-size: 12; }
.font-xs { font-size: 10; }
"""


__all__ = [
    # 字体大小常量
    "FONT_SIZE_XXS",
    "FONT_SIZE_XS",
    "FONT_SIZE_SM",
    "FONT_SIZE_MD",
    "FONT_SIZE_LG",
    "FONT_SIZE_XL",
    "FONT_SIZE_XXL",
    # 配置
    "TypographyConfig",
    "DEFAULT_TYPOGRAPHY",
    "COMPACT_TYPOGRAPHY",
    "LARGE_TYPOGRAPHY",
    "TYPOGRAPHY_PRESETS",
    # 元素字体类
    "ELEMENT_FONT_CLASSES",
    # 函数
    "get_typography_preset",
    "generate_typography_css",
    "generate_element_font_css",
]
