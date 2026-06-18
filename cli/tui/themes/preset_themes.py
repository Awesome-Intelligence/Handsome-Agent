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
    """创建牛油果绿主题 (Avocado Green)."""
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
            "--border": "#647030",
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


def _create_ares_theme() -> Theme:
    """创建战争之神主题 (Ares - Crimson/Bronze)."""
    return Theme(
        theme_id="ares",
        display_name_key="tui.theme.ares.name",
        colors={
            # 基础颜色
            "--primary": "#CD7F32",
            "--primary-bright": "#FFD700",
            "--primary-dim": "#B8860B",
            "--primary-dark": "#8B4513",
            # 文字颜色
            "--text": "#FFF8DC",
            "--text-dim": "#B8860B",
            "--text-accent": "#FFD700",
            # 背景颜色
            "--background": "#8B4513",
            "--surface": "#1a1a1a",
            "--surface-light": "#2a2a2a",
            # 边框颜色
            "--border": "#B8860B",
            "--border-light": "#CD7F32",
            "--border-accent": "#FFD700",
            # UI 状态颜色
            "--success": "#4CAF50",
            "--warning": "#FFA726",
            "--error": "#EF5350",
            "--info": "#64B5F6",
        },
        transparency=1.0,
    )


def _create_mono_theme() -> Theme:
    """创建灰度单色主题 (Monochrome)."""
    return Theme(
        theme_id="mono",
        display_name_key="tui.theme.mono.name",
        colors={
            # 基础颜色
            "--primary": "#808080",
            "--primary-bright": "#FFFFFF",
            "--primary-dim": "#666666",
            "--primary-dark": "#404040",
            # 文字颜色
            "--text": "#CCCCCC",
            "--text-dim": "#666666",
            "--text-accent": "#FFFFFF",
            # 背景颜色
            "--background": "#1a1a1a",
            "--surface": "#1a1a1a",
            "--surface-light": "#2a2a2a",
            # 边框颜色
            "--border": "#404040",
            "--border-light": "#666666",
            "--border-accent": "#808080",
            # UI 状态颜色
            "--success": "#888888",
            "--warning": "#AAAAAA",
            "--error": "#CCCCCC",
            "--info": "#999999",
        },
        transparency=1.0,
    )


def _create_slate_theme() -> Theme:
    """创建酷蓝开发者主题 (Slate - Cool Blue)."""
    return Theme(
        theme_id="slate",
        display_name_key="tui.theme.slate.name",
        colors={
            # 基础颜色
            "--primary": "#607D8B",
            "--primary-bright": "#90CAF9",
            "--primary-dim": "#455A64",
            "--primary-dark": "#37474F",
            # 文字颜色
            "--text": "#E0E7FF",
            "--text-dim": "#94A3B8",
            "--text-accent": "#60A5FA",
            # 背景颜色
            "--background": "#37474F",
            "--surface": "#0F172A",
            "--surface-light": "#1E293B",
            # 边框颜色
            "--border": "#475569",
            "--border-light": "#607D8B",
            "--border-accent": "#90CAF9",
            # UI 状态颜色
            "--success": "#4ADE80",
            "--warning": "#FBBF24",
            "--error": "#F87171",
            "--info": "#38BDF8",
        },
        transparency=1.0,
    )


# 预设主题注册表
_PRESET_THEMES: Dict[str, Theme] = {
    "default": _create_default_theme(),
    "ares": _create_ares_theme(),
    "mono": _create_mono_theme(),
    "slate": _create_slate_theme(),
}


__all__ = [
    "_create_default_theme",
    "_create_ares_theme",
    "_create_mono_theme",
    "_create_slate_theme",
    "_PRESET_THEMES",
]
