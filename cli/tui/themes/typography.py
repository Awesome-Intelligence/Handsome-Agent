#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Typography System - 字体排版系统

🚪 Access - 💬 CLI - Textual UI - 字体系统

定义字体大小层级和排版规范，支持主题自定义。

字体大小层级：
- xs (10): 极小 - 状态栏次要信息
- sm (12): 小 - 辅助说明、次要标签
- md (14): 中 - 正文（默认）
- lg (16): 大 - 小标题
- xl (18): 特大 - 大标题、欢迎横幅
- xxl (22): 极大 - Banner
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar


# ============================================================================
# 字体大小层级定义
# ============================================================================

# 基础字体大小常量
FONT_SIZE_XXS = 9
FONT_SIZE_XS = 10
FONT_SIZE_SM = 12
FONT_SIZE_MD = 14
FONT_SIZE_LG = 16
FONT_SIZE_XL = 18
FONT_SIZE_XXL = 22
FONT_SIZE_XXXL = 26


@dataclass
class TypographyConfig:
    """字体排版配置"""
    # 全局字体大小
    screen: int = FONT_SIZE_MD
    
    # 各元素字体大小
    banner: int = FONT_SIZE_XL      # 欢迎横幅
    title: int = FONT_SIZE_LG       # 标题
    subtitle: int = FONT_SIZE_MD    # 副标题
    body: int = FONT_SIZE_MD        # 正文
    caption: int = FONT_SIZE_SM     # 辅助文字
    status: int = FONT_SIZE_SM      # 状态栏
    input: int = FONT_SIZE_MD       # 输入框
    button: int = FONT_SIZE_MD      # 按钮
    tooltip: int = FONT_SIZE_XS      # 提示文字
    
    # 消息字体大小
    user_message: int = FONT_SIZE_MD
    assistant_message: int = FONT_SIZE_MD
    system_message: int = FONT_SIZE_SM
    
    # 行高
    line_height: float = 1.4
    line_height_tight: float = 1.2
    line_height_loose: float = 1.6
    
    def to_css(self) -> str:
        """转换为 CSS 变量定义"""
        return f"""
        /* 字体大小 */
        --font-xxs: {FONT_SIZE_XXS};
        --font-xs: {FONT_SIZE_XS};
        --font-sm: {FONT_SIZE_SM};
        --font-md: {FONT_SIZE_MD};
        --font-lg: {FONT_SIZE_LG};
        --font-xl: {FONT_SIZE_XL};
        --font-xxl: {FONT_SIZE_XXL};
        
        /* 元素字体大小 */
        --font-banner: {self.banner};
        --font-title: {self.title};
        --font-subtitle: {self.subtitle};
        --font-body: {self.body};
        --font-caption: {self.caption};
        --font-status: {self.status};
        --font-input: {self.input};
        --font-button: {self.button};
        --font-tooltip: {self.tooltip};
        
        /* 行高 */
        --line-height: {self.line_height};
        --line-height-tight: {self.line_height_tight};
        --line-height-loose: {self.line_height_loose};
        """


# ============================================================================
# 预设字体配置
# ============================================================================

# 默认字体配置（中等大小，适合大多数用户）
DEFAULT_TYPOGRAPHY = TypographyConfig(
    screen=FONT_SIZE_MD,
    banner=FONT_SIZE_XL,
    title=FONT_SIZE_LG,
    subtitle=FONT_SIZE_MD,
    body=FONT_SIZE_MD,
    caption=FONT_SIZE_SM,
    status=FONT_SIZE_SM,
    input=FONT_SIZE_MD,
    button=FONT_SIZE_MD,
    tooltip=FONT_SIZE_XS,
)

# 小字体配置（适合屏幕较小或视力好的用户）
COMPACT_TYPOGRAPHY = TypographyConfig(
    screen=FONT_SIZE_SM,
    banner=FONT_SIZE_LG,
    title=FONT_SIZE_MD,
    subtitle=FONT_SIZE_SM,
    body=FONT_SIZE_SM,
    caption=FONT_SIZE_XS,
    status=FONT_SIZE_XS,
    input=FONT_SIZE_SM,
    button=FONT_SIZE_SM,
    tooltip=FONT_SIZE_XXS,
)

# 大字体配置（适合视力不好的用户）
LARGE_TYPOGRAPHY = TypographyConfig(
    screen=FONT_SIZE_LG,
    banner=FONT_SIZE_XXL,
    title=FONT_SIZE_XL,
    subtitle=FONT_SIZE_LG,
    body=FONT_SIZE_LG,
    caption=FONT_SIZE_MD,
    status=FONT_SIZE_MD,
    input=FONT_SIZE_LG,
    button=FONT_SIZE_LG,
    tooltip=FONT_SIZE_SM,
)

# 预设字体配置映射
TYPOGRAPHY_PRESETS: dict[str, TypographyConfig] = {
    "default": DEFAULT_TYPOGRAPHY,
    "compact": COMPACT_TYPOGRAPHY,
    "large": LARGE_TYPOGRAPHY,
}


# ============================================================================
# 元素样式映射
# ============================================================================

# CSS 类名到字体大小配置的映射
ELEMENT_FONT_CLASSES: dict[str, str] = {
    # 标题类
    "banner": "--font-banner",
    "title": "--font-title",
    "subtitle": "--font-subtitle",
    
    # 正文类
    "body": "--font-body",
    "message": "--font-body",
    "paragraph": "--font-body",
    
    # 辅助类
    "caption": "--font-caption",
    "hint": "--font-caption",
    "secondary": "--font-caption",
    
    # 状态类
    "status": "--font-status",
    "label": "--font-status",
    
    # 输入类
    "input": "--font-input",
    "textarea": "--font-input",
    
    # 按钮类
    "button": "--font-button",
    
    # 提示类
    "tooltip": "--font-tooltip",
}


# ============================================================================
# 工具函数
# ============================================================================

def get_typography_preset(preset: str = "default") -> TypographyConfig:
    """
    获取预设字体配置
    
    Args:
        preset: 预设名称 ("default", "compact", "large")
    
    Returns:
        TypographyConfig 实例
    """
    return TYPOGRAPHY_PRESETS.get(preset, DEFAULT_TYPOGRAPHY)


def generate_typography_css(preset: str = "default") -> str:
    """
    生成字体相关的 CSS
    
    Args:
        preset: 预设名称
    
    Returns:
        CSS 变量定义字符串
    """
    config = get_typography_preset(preset)
    return config.to_css()


def generate_element_font_css(element_class: str, preset: str = "default") -> str:
    """
    生成特定元素的字体 CSS
    
    Args:
        element_class: 元素类名
        preset: 预设名称
    
    Returns:
        CSS 字符串
    """
    if element_class not in ELEMENT_FONT_CLASSES:
        return ""
    
    var_name = ELEMENT_FONT_CLASSES[element_class]
    return f"{element_class} {{ font-size: var({var_name}); }}"


__all__ = [
    # 字体大小常量
    "FONT_SIZE_XXS",
    "FONT_SIZE_XS",
    "FONT_SIZE_SM",
    "FONT_SIZE_MD",
    "FONT_SIZE_LG",
    "FONT_SIZE_XL",
    "FONT_SIZE_XXL",
    "FONT_SIZE_XXXL",
    # 配置类
    "TypographyConfig",
    # 预设
    "DEFAULT_TYPOGRAPHY",
    "COMPACT_TYPOGRAPHY",
    "LARGE_TYPOGRAPHY",
    "TYPOGRAPHY_PRESETS",
    # 映射
    "ELEMENT_FONT_CLASSES",
    # 函数
    "get_typography_preset",
    "generate_typography_css",
    "generate_element_font_css",
]
