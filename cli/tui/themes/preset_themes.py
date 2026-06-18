#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Preset Theme Definitions.

🚪 Access - 💬 CLI - Textual UI - 预设主题定义
"""

from __future__ import annotations

from typing import Dict

from .theme_config import Theme


# ============================================================================
# Preset Themes
# ============================================================================


def _create_default_theme() -> Theme:
    """创建高雅紫主题 (Elegant Purple)."""
    return Theme(
        theme_id="default",
        display_name_key="tui.theme.default.name",
        colors={
            # 基础颜色
            "--primary": "#8B9A46",
            "--primary-bright": "#A0B45A",
            "--primary-dim": "#647030",
            "--primary-dark": "#465A1E",
            # 文字颜色
            "--text": "#FFFFFF",
            "--text-dim": "#888888",
            "--text-accent": "#A0B45A",
            # 背景颜色
            "--background": "#465A1E",
            "--surface": "#1a1a1a",
            "--surface-light": "#2a2a2a",
            # 边框颜色
            "$border": "#B180D7",
            "--border": "#B180D7",
            "--border-light": "#8B9A46",
            "--border-accent": "#A0B45A",
            # UI 状态颜色
            "--success": "#4CAF50",
            "--warning": "#FF9800",
            "--error": "#F44336",
            "--info": "#2196F3",
        },
        transparency=1.0,
    )


def _create_awesome_theme() -> Theme:
    """创建 Awesome 主题 (Vibrant Green)."""
    return Theme(
        theme_id="awesome",
        display_name_key="tui.theme.awesome.name",
        colors={
            # 基础颜色
            "--primary": "#A9FC6E",
            "--primary-bright": "#C5FF9E",
            "--primary-dim": "#7FD94A",
            "--primary-dark": "#5FA832",
            # 文字颜色
            "--text": "#FFFFFF",
            "--text-dim": "#A0C47A",
            "--text-accent": "#C5FF9E",
            # 背景颜色
            "--background": "#1A2E0A",
            "--surface": "#1a1a1a",
            "--surface-light": "#2a2a2a",
            # 边框颜色
            "$border": "#A9FC6E",
            "--border": "#A9FC6E",
            "--border-light": "#7FD94A",
            "--border-accent": "#C5FF9E",
            # UI 状态颜色
            "--success": "#4CAF50",
            "--warning": "#FF9800",
            "--error": "#F44336",
            "--info": "#2196F3",
        },
        transparency=1.0,
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
