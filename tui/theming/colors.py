#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Color Constants and Transparency Utilities.

🚪 Access - 💬 CLI - Theming - 颜色和透明度工具
"""

from __future__ import annotations

import logging
from typing import Dict

logger = logging.getLogger(__name__)


# ============================================================================
# 透明度等级常量
# ============================================================================

TRANSPARENCY_LEVELS = {
    "xs": 0.05,  # 极淡 - 背景微变
    "sm": 0.10,  # 淡 - 悬停效果
    "md": 0.15,  # 中 - 选择状态
    "lg": 0.25,  # 重 - 次要强调
    "xl": 0.50,  # 浓 - 焦点指示
}


# ============================================================================
# 半透明颜色转换函数
# ============================================================================


def transparent(color: str, opacity: float) -> str:
    """将 hex 颜色转换为 rgba 格式。

    Args:
        color: hex 颜色字符串，如 "#8B9A46"
        opacity: 透明度，0.0-1.0

    Returns:
        rgba 格式字符串，如 "rgba(139, 154, 70, 0.5)"

    Examples:
        >>> transparent("#8B9A46", 0.5)
        'rgba(139, 154, 70, 0.5)'
        >>> transparent("#FF0000", 0.25)
        'rgba(255, 0, 0, 0.25)'
    """
    # 移除 # 号
    color = color.lstrip("#")

    # 支持 3 位和 6 位 hex 格式
    if len(color) == 3:
        color = "".join(c * 2 for c in color)

    # 解析 RGB 分量
    try:
        r = int(color[0:2], 16)
        g = int(color[2:4], 16)
        b = int(color[4:6], 16)
    except ValueError:
        # 如果解析失败，返回原始颜色
        logger.warning(f"Invalid hex color: #{color}, returning original")
        return color

    # 限制 opacity 范围
    opacity = max(0.0, min(1.0, opacity))

    return f"rgba({r}, {g}, {b}, {opacity})"


# ============================================================================
# 基础颜色常量（保持向后兼容）
# ============================================================================

# 状态颜色
STATUS_ONLINE = "#3fb950"
STATUS_BUSY = "#f0883e"
STATUS_AWAY = "#f0883e"
STATUS_OFFLINE = "#8b949e"
STATUS_ERROR = "#f85149"
STATUS_SUCCESS = "#3fb950"
STATUS_WARNING = "#d29922"
STATUS_INFO = "#58a6ff"


__all__ = [
    "TRANSPARENCY_LEVELS",
    "transparent",
    "STATUS_ONLINE",
    "STATUS_BUSY",
    "STATUS_AWAY",
    "STATUS_OFFLINE",
    "STATUS_ERROR",
    "STATUS_SUCCESS",
    "STATUS_WARNING",
    "STATUS_INFO",
]
