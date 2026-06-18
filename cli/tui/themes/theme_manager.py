#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Theme Manager for Textual UI.

🚪 Access - 💬 CLI - Textual UI - 主题管理器
"""

from __future__ import annotations

import json
import logging
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

from .preset_themes import _PRESET_THEMES
from .theme_config import Theme


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
        self._transparency_enabled: bool = False  # 透明度开关
        self._transparency_level: float = 0.85  # 透明度级别 (0.0-1.0)
        self._theme_change_callback: Optional[callable] = None  # 主题变更回调
        
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
        
        # 调用主题变更回调
        if self._theme_change_callback:
            try:
                self._theme_change_callback(theme_id)
            except Exception as e:
                self._logger.error(f"Theme change callback failed: {e}")
        
        return True

    def register_theme_change_callback(self, callback: callable) -> None:
        """注册主题变更回调.
        
        Args:
            callback: 主题变更时调用的回调函数，接收 theme_id 参数
        """
        self._theme_change_callback = callback

    def get_theme_css_path(self, theme_id: str) -> Optional[Path]:
        """获取主题 CSS 文件路径.
        
        Args:
            theme_id: 主题 ID
            
        Returns:
            主题 CSS 文件路径，如果不存在则返回 None
        """
        # 检查是否是皮肤主题（skin_ 开头）
        if theme_id.startswith("skin_"):
            return None  # 皮肤主题使用动态生成的 CSS
        
        # 检查是否是预设主题
        if theme_id in _PRESET_THEMES:
            themes_dir = Path(__file__).parent.parent / "styles" / "themes"
            css_path = themes_dir / f"{theme_id}.css"
            if css_path.exists():
                return css_path
        
        return None

    # ============================================================================
    # 透明度控制方法
    # ============================================================================
    
    def is_transparency_supported(self) -> bool:
        """检查终端是否支持透明度.
        
        Returns:
            True 如果终端支持 RGBA 颜色
        """
        import os
        # 检查常见支持透明度的终端
        term = os.environ.get("TERM", "")
        term_program = os.environ.get("TERM_PROGRAM", "")
        
        # 支持透明度的终端
        transparent_terminals = [
            "iTerm.app",           # iTerm2
            "Apple_Terminal",       # macOS Terminal (部分支持)
            "vscode",               # VS Code 终端
            "Hyper",                # Hyper
            "alacritty",            # Alacritty
            "kitty",                # Kitty
            "wezterm",              # WezTerm
            "ghostty",              # Ghostty
        ]
        
        # 检查 TERM_PROGRAM
        if term_program in transparent_terminals:
            return True
        
        # 检查 TERM 变量 (部分终端会设置)
        if "256" in term or "truecolor" in term or "rgb" in term:
            return True
        
        # 默认返回 False，让用户手动启用
        return False
    
    def is_transparency_enabled(self) -> bool:
        """检查透明度是否启用.
        
        Returns:
            True 如果透明度已启用
        """
        return self._transparency_enabled
    
    def set_transparency_enabled(self, enabled: bool) -> None:
        """设置透明度启用状态.
        
        Args:
            enabled: 是否启用透明度
        """
        self._transparency_enabled = enabled
        self._logger.info(f"Transparency {'enabled' if enabled else 'disabled'}")
        self._save_preference()
    
    def toggle_transparency(self) -> bool:
        """切换透明度状态.
        
        Returns:
            切换后的透明度状态
        """
        self._transparency_enabled = not self._transparency_enabled
        self._logger.info(f"Transparency toggled: {self._transparency_enabled}")
        self._save_preference()
        return self._transparency_enabled
    
    def get_transparency_level(self) -> float:
        """获取透明度级别.
        
        Returns:
            透明度级别 (0.0 完全透明 - 1.0 完全不透明)
        """
        return self._transparency_level
    
    def set_transparency_level(self, level: float) -> None:
        """设置透明度级别.
        
        Args:
            level: 透明度级别 (0.0 完全透明 - 1.0 完全不透明)
        """
        self._transparency_level = max(0.0, min(1.0, level))
        self._logger.debug(f"Transparency level set to: {self._transparency_level}")
        self._save_preference()
    
    def generate_transparent_css(self) -> str:
        """生成支持透明度的 CSS 变量块.
        
        Returns:
            CSS 变量定义字符串
        """
        if not self._transparency_enabled:
            return ""
        
        # 计算透明度的 alpha 值
        alpha = self._transparency_level
        
        # 生成 RGBA 颜色值（使用 hex8 格式，Textual 支持）
        # hex8 格式: #RRGGBBAA (AA 是 alpha)
        alpha_hex = format(int(alpha * 255), '02X')
        
        return f"""
/* ============================================================================
   透明度配置 (Frosted Glass Effect)
   ============================================================================ */

:root {{
    --transparency-alpha: {alpha};
    --transparency-hex: {alpha_hex};
}}

/* 毛玻璃效果样式类 */
.transparent-surface {{
    background: rgba(13, 17, 23, {alpha});
}}

.transparent-header {{
    background: rgba(22, 27, 34, {alpha});
}}

.transparent-footer {{
    background: rgba(33, 38, 45, {alpha});
}}

.transparent-sidebar {{
    background: rgba(22, 27, 34, {alpha});
}}

.transparent-input {{
    background: rgba(13, 17, 23, {alpha});
}}

.transparent-border {{
    border: solid rgba(48, 54, 61, {alpha});
}}
"""
    
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
                
                # 加载主题偏好
                theme_id = config.get("theme", {}).get("active_theme")
                if theme_id and self.get_theme(theme_id):
                    self._current_theme_id = theme_id
                    self._logger.debug(f"Loaded theme preference: {theme_id}")
                
                # 加载透明度设置
                transparency = config.get("theme", {}).get("transparency", {})
                if transparency:
                    self._transparency_enabled = transparency.get("enabled", False)
                    self._transparency_level = transparency.get("level", 0.85)
                    self._logger.debug(
                        f"Loaded transparency: enabled={self._transparency_enabled}, "
                        f"level={self._transparency_level}"
                    )
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
            
            # 保存主题偏好
            config["theme"]["active_theme"] = self._current_theme_id
            
            # 保存透明度设置
            config["theme"]["transparency"] = {
                "enabled": self._transparency_enabled,
                "level": self._transparency_level,
            }
            
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            self._logger.debug(
                f"Saved theme preference: {self._current_theme_id}, "
                f"transparency: {self._transparency_enabled}"
            )
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
            # 获取皮肤强调色
            skin_accent = skin_config.get_color("ui_accent", "#A0B45A")
            skin_border = skin_config.get_color("banner_border", "#8B9A46")
            
            # 构建自定义主题颜色映射
            css_colors = {
                # 基础颜色
                "--primary": skin_border,
                "--primary-bright": skin_config.get_color("banner_title", "#A0B45A"),
                "--primary-dim": skin_config.get_color("banner_dim", "#647030"),
                "--primary-dark": skin_config.get_color("banner_border", "#465A1E"),
                # 强调色 - 不再由皮肤控制，保持主题独立
                # $accent 和 --accent 由各主题 CSS 文件控制
                "$primary": skin_border,
                "--accent-bright": skin_accent,
                "--accent-dim": skin_config.get_color("ui_label", "#8B9A46"),
                "--accent-dark": skin_config.get_color("banner_dim", "#647030"),
                # 文字颜色
                "$text": skin_config.get_color("banner_text", "#FFFFFF"),
                "--text": skin_config.get_color("banner_text", "#FFFFFF"),
                "--text-dim": skin_config.get_color("banner_dim", "#888888"),
                # --text-accent 和 --border-accent 由主题 CSS 控制
                # 背景颜色
                "$background": skin_config.get_color("status_bar_bg", "#465A1E"),
                "$surface": "#1a1a1a",
                "--background": skin_config.get_color("status_bar_bg", "#465A1E"),
                "--surface": "#1a1a1a",
                "--surface-light": "#2a2a2a",
                # 边框颜色
                "$border": skin_config.get_color("banner_dim", "#647030"),
                "--border": skin_config.get_color("banner_dim", "#647030"),
                "--border-light": skin_config.get_color("banner_border", "#8B9A46"),
                # --border-accent 由主题 CSS 控制
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


__all__ = [
    "ThemeManager",
    "get_theme_manager",
]
