#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Textual Theme System for Handsome Agent.

🚪 Access - 💬 CLI - Textual UI - 主题系统

基于 Textual CSS 的主题系统，支持：
- 四套预设主题（default/ares/mono/slate）
- 动态主题切换
- 与皮肤引擎（skin_engine.py）保持兼容
- i18n 主题名称
- 用户主题偏好持久化

预设主题：

| 主题 ID | 名称 | 主色 |
|---------|------|------|
| default | 牛油果绿 | #8B9A46 |
| ares | 战争之神 | #8B4513 |
| mono | 灰度单色 | #666666 |
| slate | 酷蓝开发者 | #607D8B |

Usage::

    from cli.tui.themes import ThemeManager, get_theme_manager

    manager = get_theme_manager()
    manager.set_theme("slate")
    css = manager.get_current_css()
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

# i18n 支持
try:
    from common.i18n import get_i18n, t
except ImportError:
    def get_i18n():
        class SimpleI18n:
            def t(self, key, default=None, **kwargs):
                return default or key
        return SimpleI18n()
    def t(key, default=None, **kwargs):
        return default or key

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
    """
    theme_id: str
    display_name_key: str
    colors: Dict[str, str] = field(default_factory=dict)


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
    )


# 预设主题注册表
_PRESET_THEMES: Dict[str, Theme] = {
    "default": _create_default_theme(),
    "ares": _create_ares_theme(),
    "mono": _create_mono_theme(),
    "slate": _create_slate_theme(),
}


# ============================================================================
# Theme Manager
# ============================================================================


class ThemeManager:
    """Textual 主题管理器.
    
    负责：
    - 管理预设和自定义主题
    - 生成动态 CSS
    - 保存/加载用户主题偏好
    - 与皮肤引擎（skin_engine.py）保持兼容
    """

    _instance: Optional["ThemeManager"] = None

    def __init__(self):
        """初始化主题管理器."""
        self._current_theme_id: str = "default"
        self._custom_themes: Dict[str, Theme] = {}
        self._logger = get_access_logger("ThemeManager", sublayer="tui")
        
        # 从配置文件加载用户偏好
        self._load_preference()

    @classmethod
    def get_instance(cls) -> "ThemeManager":
        """获取单例实例."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def list_themes(self) -> list[Theme]:
        """列出所有可用的主题.
        
        Returns:
            主题列表（预设主题 + 自定义主题）
        """
        themes = list(_PRESET_THEMES.values())
        themes.extend(self._custom_themes.values())
        return themes

    def list_theme_ids(self) -> list[str]:
        """列出所有主题 ID.
        
        Returns:
            主题 ID 列表
        """
        ids = list(_PRESET_THEMES.keys())
        ids.extend(self._custom_themes.keys())
        return ids

    def get_theme(self, theme_id: str) -> Optional[Theme]:
        """获取指定主题.
        
        Args:
            theme_id: 主题 ID
            
        Returns:
            主题对象，如果不存在则返回 None
        """
        # 优先检查预设主题
        if theme_id in _PRESET_THEMES:
            return _PRESET_THEMES[theme_id]
        # 检查自定义主题
        return self._custom_themes.get(theme_id)

    def get_current_theme(self) -> Theme:
        """获取当前激活的主题.
        
        Returns:
            当前主题对象
        """
        theme = self.get_theme(self._current_theme_id)
        if theme is None:
            # 回退到默认主题
            self._logger.warning(
                f"Theme '{self._current_theme_id}' not found, falling back to 'default'"
            )
            self._current_theme_id = "default"
            theme = _PRESET_THEMES["default"]
        return theme

    def set_theme(self, theme_id: str) -> bool:
        """设置当前主题.
        
        Args:
            theme_id: 主题 ID
            
        Returns:
            True 如果设置成功，False 如果主题不存在
        """
        theme = self.get_theme(theme_id)
        if theme is None:
            self._logger.warning(f"Theme '{theme_id}' not found")
            return False
        
        self._current_theme_id = theme_id
        self._logger.info(f"Theme changed to: {theme_id}")
        
        # 保存用户偏好
        self._save_preference()
        
        return True

    def get_current_theme_id(self) -> str:
        """获取当前主题 ID.
        
        Returns:
            当前主题 ID
        """
        return self._current_theme_id

    def get_current_display_name(self) -> str:
        """获取当前主题的显示名称（使用 i18n）.
        
        Returns:
            主题显示名称
        """
        theme = self.get_current_theme()
        i18n = get_i18n()
        return i18n.t(theme.display_name_key, default=theme.theme_id)

    def generate_css(self, theme: Theme) -> str:
        """为主题生成完整的 CSS 样式.
        
        Args:
            theme: 主题对象
            
        Returns:
            CSS 样式字符串
        """
        colors = theme.colors
        
        # 构建 :root CSS 变量块
        var_lines = [":root {"]
        for var_name, color_value in colors.items():
            var_lines.append(f"    {var_name}: {color_value};")
        var_lines.append("}")
        
        # 构建完整 CSS
        css_template = """
/* Handsome Agent - {theme_id} Theme CSS */

/* ============================================================================
   CSS Variables (Theme Colors)
   ============================================================================ */

{var_block}

/* ============================================================================
   Base Styles
   ============================================================================ */

Screen {{
    background: $background;
}}

/* ============================================================================
   Container Styles
   ============================================================================ */

#main-container {{
    height: 100%;
    width: 100%;
    background: $surface;
}}

#tab-container {{
    height: auto;
    width: 100%;
    background: $background;
    border-bottom: solid $border;
}}

/* ============================================================================
   Tabs Styles
   ============================================================================ */

Tabs {{
    height: auto;
    background: $background;
    margin: 0;
    padding: 0 1;
}}

Tab {{
    background: $primary-dim;
    color: $text;
    padding: 0 2;
    margin: 0 1;
}}

Tab:hover {{
    background: $primary;
}}

Tab.active {{
    background: $primary;
    color: $text-accent;
    text-style: bold;
}}

/* ============================================================================
   Welcome Banner Styles
   ============================================================================ */

#welcome-banner {{
    height: auto;
    width: 100%;
    padding: 1 2;
    background: $primary-dim;
    border: solid $border-light;
}}

#welcome-title {{
    text-style: bold;
    color: $text-accent;
    height: 3;
}}

#welcome-content {{
    color: $text;
    height: auto;
    padding: 1 0;
}}

/* ============================================================================
   Status Bar Styles
   ============================================================================ */

#status-bar {{
    height: 3;
    width: 100%;
    background: $primary;
    padding: 0 2;
    dock: bottom;
}}

/* ============================================================================
   Input Area Styles
   ============================================================================ */

#input-area {{
    height: 3;
    width: 100%;
    padding: 0 2;
    background: $surface;
}}

.input-field {{
    border: solid $primary;
    background: $surface;
    color: $text;
}}

.input-field:focus {{
    border: solid $primary-bright;
}}

/* ============================================================================
   Chat Log Styles
   ============================================================================ */

#chat-log {{
    height: 100%;
    width: 100%;
    background: $surface;
    border: solid $border;
}}

/* ============================================================================
   Button Styles
   ============================================================================ */

Button {{
    background: $primary;
    color: $text;
}}

Button:hover {{
    background: $primary-bright;
}}

Button:pressed {{
    background: $primary-dim;
}}

/* ============================================================================
   Sidebar Styles
   ============================================================================ */

#sidebar {{
    width: 25;
    height: 100%;
    background: $background;
    border-right: solid $border;
}}

/* ============================================================================
   Content Area Styles
   ============================================================================ */

#content-area {{
    height: 1fr;
    width: 100%;
    background: $surface;
}}

/* ============================================================================
   ChatView Styles
   ============================================================================ */

ChatView {{
    height: 100%;
    width: 100%;
}}

/* ============================================================================
   Status Colors
   ============================================================================ */

.status-success {{
    color: $success;
}}

.status-warning {{
    color: $warning;
}}

.status-error {{
    color: $error;
}}

.status-info {{
    color: $info;
}}

/* ============================================================================
   Message Styles
   ============================================================================ */

.user-message {{
    color: $text-accent;
}}

.assistant-message {{
    color: $text;
}}

.system-message {{
    color: $text-dim;
}}
""".format(
            theme_id=theme.theme_id,
            var_block="\n".join(var_lines),
        )
        
        return css_template

    def get_current_css(self) -> str:
        """获取当前主题的 CSS 样式.
        
        Returns:
            CSS 样式字符串
        """
        theme = self.get_current_theme()
        return self.generate_css(theme)

    # ============================================================================
    # Preference Persistence
    # ============================================================================

    def _get_config_path(self) -> Path:
        """获取配置文件路径."""
        config_dir = Path.home() / ".handsome_agent"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "tui_config.json"

    def _load_preference(self) -> None:
        """从配置文件加载用户主题偏好."""
        try:
            config_path = self._get_config_path()
            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    config = json.load(f)
                
                theme_id = config.get("theme", {}).get("active_theme")
                if theme_id and self.get_theme(theme_id):
                    self._current_theme_id = theme_id
                    self._logger.debug(f"Loaded theme preference: {theme_id}")
        except Exception as e:
            self._logger.debug(f"Failed to load theme preference: {e}")

    def _save_preference(self) -> None:
        """保存用户主题偏好到配置文件."""
        try:
            config_path = self._get_config_path()
            
            config = {}
            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    config = json.load(f)
            
            if "theme" not in config:
                config["theme"] = {}
            
            config["theme"]["active_theme"] = self._current_theme_id
            
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            self._logger.debug(f"Saved theme preference: {self._current_theme_id}")
        except Exception as e:
            self._logger.warning(f"Failed to save theme preference: {e}")

    # ============================================================================
    # Skin Engine Compatibility
    # ============================================================================

    def apply_skin_colors(self, skin_config) -> bool:
        """从皮肤引擎的配置应用颜色到当前主题.
        
        Args:
            skin_config: SkinConfig 对象（来自 skin_engine.py）
            
        Returns:
            True 如果应用成功
        """
        try:
            # 构建自定义主题颜色映射
            css_colors = {
                # 基础颜色
                "--primary": skin_config.get_color("banner_border", "#8B9A46"),
                "--primary-bright": skin_config.get_color("banner_title", "#A0B45A"),
                "--primary-dim": skin_config.get_color("banner_dim", "#647030"),
                "--primary-dark": skin_config.get_color("banner_border", "#465A1E"),
                # 文字颜色
                "--text": skin_config.get_color("banner_text", "#FFFFFF"),
                "--text-dim": skin_config.get_color("banner_dim", "#888888"),
                "--text-accent": skin_config.get_color("ui_accent", "#A0B45A"),
                # 背景颜色
                "--background": skin_config.get_color("status_bar_bg", "#465A1E"),
                "--surface": "#1a1a1a",
                "--surface-light": "#2a2a2a",
                # 边框颜色
                "--border": skin_config.get_color("banner_dim", "#647030"),
                "--border-light": skin_config.get_color("banner_border", "#8B9A46"),
                "--border-accent": skin_config.get_color("ui_accent", "#A0B45A"),
                # UI 状态颜色
                "--success": skin_config.get_color("ui_ok", "#4CAF50"),
                "--warning": skin_config.get_color("ui_warn", "#FF9800"),
                "--error": skin_config.get_color("ui_error", "#F44336"),
                "--info": skin_config.get_color("ui_info", "#2196F3"),
            }
            
            # 创建自定义主题
            custom_theme = Theme(
                theme_id=f"skin_{skin_config.name}",
                display_name_key=f"tui.theme.skin.name:{skin_config.name}",
                colors=css_colors,
            )
            
            # 注册并应用自定义主题
            self._custom_themes[custom_theme.theme_id] = custom_theme
            self.set_theme(custom_theme.theme_id)
            
            self._logger.info(f"Applied skin colors from: {skin_config.name}")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to apply skin colors: {e}")
            return False

    def load_skin_from_engine(self) -> bool:
        """从皮肤引擎加载当前激活的皮肤.
        
        Returns:
            True 如果加载成功
        """
        try:
            from cli.skin_engine import get_active_skin
            skin = get_active_skin()
            return self.apply_skin_colors(skin)
        except ImportError:
            self._logger.debug("Skin engine not available")
            return False
        except Exception as e:
            self._logger.error(f"Failed to load skin from engine: {e}")
            return False


# ============================================================================
# Global Instance Access
# ============================================================================


def get_theme_manager() -> ThemeManager:
    """获取主题管理器单例.
    
    Returns:
        ThemeManager 实例
    """
    return ThemeManager.get_instance()


# ============================================================================
# Module Export
# ============================================================================

__all__ = [
    "Theme",
    "ThemeManager",
    "get_theme_manager",
]