#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skin/Theme engine for Handsome Agent CLI.

🚪 Access - 💬 CLI - 皮肤/主题系统

参考 Hermes 的 skin_engine.py 设计，支持：
- 内置皮肤（default, ares, mono, slate）
- 用户皮肤（~/.handsome_agent/skins/<name>.yaml）
- 颜色、品牌、spinner 等配置

SKIN YAML SCHEMA
================

.. code-block:: yaml

    name: myskin
    description: My custom skin

    colors:
      banner_border: "#8B9A46"          # Panel border color
      banner_title: "#A0B45A"           # Panel title text color
      banner_accent: "#FFD700"          # Section headers
      banner_dim: "#647030"             # Dim/muted text
      banner_text: "#FFFFFF"             # Body text
      ui_accent: "#A0B45A"              # General UI accent
      ui_ok: "#4CAF50"                 # Success indicators
      ui_error: "#F44336"              # Error indicators
      ui_warn: "#FF9800"               # Warning indicators

    branding:
      agent_name: "Handsome Agent"
      welcome: "Welcome!"
      goodbye: "Goodbye!"
      prompt_symbol: "❯"

USAGE
=====

.. code-block:: python

    from cli.ui.skin_engine import get_active_skin, list_skins, set_active_skin

    skin = get_active_skin()
    print(skin.colors.get("banner_title"))
    print(skin.get_branding("agent_name"))
"""

import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from common.terminal.colors import (
    HEX_AVOCADO,
    HEX_AVOCADO_BRIGHT,
    HEX_AVOCADO_DIM,
    HEX_GOLD,
)

logger = logging.getLogger(__name__)

# ============================================================================
# Paths
# ============================================================================

def _get_skins_dir() -> Path:
    """Get the user skins directory."""
    home = Path.home()
    skins_dir = home / ".handsome_agent" / "skins"
    skins_dir.mkdir(parents=True, exist_ok=True)
    return skins_dir


# ============================================================================
# Default colors
# ============================================================================

DEFAULT_COLORS = {
    # Banner colors
    "banner_border": HEX_AVOCADO,          # #8B9A46
    "banner_title": HEX_AVOCADO_BRIGHT,     # #A0B45A
    "banner_accent": HEX_GOLD,             # #FFD700
    "banner_dim": HEX_AVOCADO_DIM,         # #647030
    "banner_text": "#FFFFFF",               # White
    # UI colors
    "ui_accent": HEX_AVOCADO_BRIGHT,
    "ui_label": HEX_AVOCADO,
    "ui_ok": "#4CAF50",
    "ui_error": "#F44336",
    "ui_warn": "#FF9800",
    "ui_info": "#2196F3",
    # Status bar
    "status_bar_bg": "#1a1a2e",
    "status_bar_text": "#C0C0C0",
    "status_bar_strong": HEX_AVOCADO_BRIGHT,
    "status_bar_dim": "#8B8682",
    "status_bar_good": "#8FBC8F",
    "status_bar_warn": "#FFD700",
    "status_bar_bad": "#FF8C00",
    "status_bar_critical": "#FF6B6B",
}


# ============================================================================
# Default branding
# ============================================================================

DEFAULT_BRANDING = {
    "agent_name": "Handsome Agent",
    "welcome": "Welcome to Handsome Agent!",
    "goodbye": "Goodbye! See you next time!",
    "response_label": " 🤖 Handsome ",
    "prompt_symbol": "❯",
    "help_header": "(^_^)? Commands",
}


# ============================================================================
# Default spinner
# ============================================================================

DEFAULT_SPINNER = {
    "waiting_faces": ["(⚔)", "(⛨)"],
    "thinking_faces": ["(⌁)", "(<>)"],
    "thinking_verbs": ["forging", "plotting", "thinking", "analyzing"],
    "wings": [],  # No wings by default
}


# ============================================================================
# Skin data structure
# ============================================================================

@dataclass
class SkinConfig:
    """Complete skin configuration."""

    name: str
    description: str = ""
    colors: Dict[str, str] = field(default_factory=dict)
    spinner: Dict[str, Any] = field(default_factory=dict)
    branding: Dict[str, str] = field(default_factory=dict)
    tool_prefix: str = "┊"
    tool_emojis: Dict[str, str] = field(default_factory=dict)
    banner_logo: str = ""    # Rich-markup ASCII art logo
    banner_hero: str = ""    # Rich-markup hero art

    def get_color(self, key: str, fallback: str = "") -> str:
        """Get a color value with fallback."""
        return self.colors.get(key, fallback)

    def get_branding(self, key: str, fallback: str = "") -> str:
        """Get a branding string with fallback."""
        return self.branding.get(key, fallback)

    def get_spinner_wings(self) -> List[tuple]:
        """Get spinner wing pairs, or empty list if none."""
        raw = self.spinner.get("wings", [])
        result = []
        for pair in raw:
            if isinstance(pair, list) and len(pair) == 2:
                result.append((pair[0], pair[1]))
        return result


# ============================================================================
# Built-in skins
# ============================================================================

def _create_default_skin() -> SkinConfig:
    """Create the default (avocado green) skin."""
    return SkinConfig(
        name="default",
        description="Classic Avocado Green theme",
        colors=DEFAULT_COLORS.copy(),
        spinner=DEFAULT_SPINNER.copy(),
        branding=DEFAULT_BRANDING.copy(),
        tool_prefix="┊",
    )


def _create_ares_skin() -> SkinConfig:
    """Create the Ares (crimson/bronze) skin."""
    return SkinConfig(
        name="ares",
        description="Crimson/bronze war-god theme",
        colors={
            "banner_border": "#CD7F32",
            "banner_title": "#FFD700",
            "banner_accent": "#FFBF00",
            "banner_dim": "#B8860B",
            "banner_text": "#FFF8DC",
            "ui_accent": "#FFBF00",
            "ui_label": "#DAA520",
            "ui_ok": "#4CAF50",
            "ui_error": "#EF5350",
            "ui_warn": "#FFA726",
            "ui_info": "#64B5F6",
            "status_bar_bg": "#1a1a2e",
            "status_bar_text": "#C0C0C0",
            "status_bar_strong": "#FFD700",
            "status_bar_dim": "#8B8682",
            "status_bar_good": "#8FBC8F",
            "status_bar_warn": "#FFD700",
            "status_bar_bad": "#FF8C00",
            "status_bar_critical": "#FF6B6B",
        },
        spinner={
            "waiting_faces": ["(⚔)", "(⛨)"],
            "thinking_faces": ["(⌁)", "(<>)"],
            "thinking_verbs": ["forging", "plotting"],
            "wings": [
                ["⟪⚔", "⚔⟫"],
                ["⟪▲", "▲⟫"],
            ],
        },
        branding={
            "agent_name": "Ares Agent",
            "welcome": "Enter the battlefield!",
            "goodbye": "Until next time, warrior! ⚔",
            "response_label": " ⚔ Ares ",
            "prompt_symbol": "❯",
            "help_header": "(^_^)? Commands",
        },
        tool_prefix="⚔",
    )


def _create_mono_skin() -> SkinConfig:
    """Create a clean monochrome skin."""
    return SkinConfig(
        name="mono",
        description="Clean grayscale monochrome",
        colors={
            "banner_border": "#808080",
            "banner_title": "#FFFFFF",
            "banner_accent": "#FFFFFF",
            "banner_dim": "#666666",
            "banner_text": "#CCCCCC",
            "ui_accent": "#FFFFFF",
            "ui_label": "#AAAAAA",
            "ui_ok": "#AAAAAA",
            "ui_error": "#888888",
            "ui_warn": "#BBBBBB",
            "ui_info": "#999999",
            "status_bar_bg": "#1a1a1a",
            "status_bar_text": "#AAAAAA",
            "status_bar_strong": "#FFFFFF",
            "status_bar_dim": "#666666",
            "status_bar_good": "#888888",
            "status_bar_warn": "#AAAAAA",
            "status_bar_bad": "#CCCCCC",
            "status_bar_critical": "#FFFFFF",
        },
        spinner={
            "waiting_faces": ["(•)", "(·)"],
            "thinking_faces": ["(○)", "(●)"],
            "thinking_verbs": ["processing", "working"],
            "wings": [],
        },
        branding={
            "agent_name": "Mono Agent",
            "welcome": "Terminal aesthetic.",
            "goodbye": "Clean exit.",
            "response_label": " ▸ Mono ",
            "prompt_symbol": "›",
            "help_header": "Commands",
        },
        tool_prefix="│",
    )


def _create_slate_skin() -> SkinConfig:
    """Create a cool blue developer theme."""
    return SkinConfig(
        name="slate",
        description="Cool blue developer theme",
        colors={
            "banner_border": "#3B82F6",
            "banner_title": "#60A5FA",
            "banner_accent": "#93C5FD",
            "banner_dim": "#1E40AF",
            "banner_text": "#E0E7FF",
            "ui_accent": "#60A5FA",
            "ui_label": "#3B82F6",
            "ui_ok": "#4ADE80",
            "ui_error": "#F87171",
            "ui_warn": "#FBBF24",
            "ui_info": "#38BDF8",
            "status_bar_bg": "#0F172A",
            "status_bar_text": "#94A3B8",
            "status_bar_strong": "#60A5FA",
            "status_bar_dim": "#475569",
            "status_bar_good": "#4ADE80",
            "status_bar_warn": "#FBBF24",
            "status_bar_bad": "#F87171",
            "status_bar_critical": "#EF4444",
        },
        spinner={
            "waiting_faces": ["(◉)", "(◎)"],
            "thinking_faces": ["(○)", "(●)"],
            "thinking_verbs": ["loading", "processing", "analyzing"],
            "wings": [],
        },
        branding={
            "agent_name": "Slate Agent",
            "welcome": "Developer mode engaged.",
            "goodbye": "Signed off.",
            "response_label": " ▸ Slate ",
            "prompt_symbol": "❯",
            "help_header": "Commands",
        },
        tool_prefix="│",
    )


# Built-in skins registry
_BUILTIN_SKINS = {
    "default": _create_default_skin,
    "ares": _create_ares_skin,
    "mono": _create_mono_skin,
    "slate": _create_slate_skin,
}


# ============================================================================
# Skin registry and management
# ============================================================================

_active_skin_name: Optional[str] = None
_loaded_skins: Dict[str, SkinConfig] = {}


def list_skins() -> List[SkinConfig]:
    """List all available skins (built-in + user)."""
    skins = []

    # Built-in skins
    for name, factory in _BUILTIN_SKINS.items():
        skins.append(factory())

    # User skins
    skins_dir = _get_skins_dir()
    if skins_dir.exists():
        for yaml_file in skins_dir.glob("*.yaml"):
            try:
                skin = _load_skin_from_file(yaml_file)
                if skin:
                    skins.append(skin)
            except Exception as e:
                logger.warning(f"Failed to load skin {yaml_file}: {e}")

    return skins


def list_skin_names() -> List[str]:
    """List all available skin names."""
    names = list(_BUILTIN_SKINS.keys())

    skins_dir = _get_skins_dir()
    if skins_dir.exists():
        for yaml_file in skins_dir.glob("*.yaml"):
            name = yaml_file.stem
            if name not in names:
                names.append(name)

    return sorted(names)


def get_active_skin() -> SkinConfig:
    """Get the currently active skin."""
    global _active_skin_name

    if _active_skin_name:
        skin = _get_skin_by_name(_active_skin_name)
        if skin:
            return skin

    # Fall back to default
    return _create_default_skin()


def _get_skin_by_name(name: str) -> Optional[SkinConfig]:
    """Get a skin by name (built-in or user)."""
    global _loaded_skins

    # Check cache
    if name in _loaded_skins:
        return _loaded_skins[name]

    # Check built-in
    if name in _BUILTIN_SKINS:
        skin = _BUILTIN_SKINS[name]()
        _loaded_skins[name] = skin
        return skin

    # Check user skins
    skins_dir = _get_skins_dir()
    yaml_file = skins_dir / f"{name}.yaml"

    if yaml_file.exists():
        skin = _load_skin_from_file(yaml_file)
        if skin:
            _loaded_skins[name] = skin
            return skin

    return None


def _load_skin_from_file(path: Path) -> Optional[SkinConfig]:
    """Load a skin from a YAML file."""
    try:
        import yaml

        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data:
            return None

        name = data.get("name", path.stem)

        return SkinConfig(
            name=name,
            description=data.get("description", ""),
            colors=data.get("colors", {}),
            spinner=data.get("spinner", {}),
            branding=data.get("branding", {}),
            tool_prefix=data.get("tool_prefix", "┊"),
            tool_emojis=data.get("tool_emojis", {}),
            banner_logo=data.get("banner_logo", ""),
            banner_hero=data.get("banner_hero", ""),
        )

    except ImportError:
        logger.warning("PyYAML not installed, cannot load user skins")
        return None
    except Exception as e:
        logger.warning(f"Failed to load skin from {path}: {e}")
        return None


def set_active_skin(name: str) -> bool:
    """Set the active skin by name."""
    global _active_skin_name

    skin = _get_skin_by_name(name)
    if skin:
        _active_skin_name = name
        return True

    return False


def get_skin_info(name: str) -> Optional[Dict[str, Any]]:
    """Get information about a skin."""
    skin = _get_skin_by_name(name)
    if not skin:
        return None

    return {
        "name": skin.name,
        "description": skin.description,
        "colors": list(skin.colors.keys()),
        "branding": list(skin.branding.keys()),
    }


# ============================================================================
# Skin preferences in config
# ============================================================================

def load_skin_from_config() -> None:
    """Load the active skin from config file."""
    try:
        config_path = Path.home() / ".handsome_agent" / "config.json"
        if config_path.exists():
            import json
            with open(config_path, encoding="utf-8") as f:
                config = json.load(f)

            display = config.get("display", {})
            skin_name = display.get("skin")
            if skin_name:
                set_active_skin(skin_name)

    except Exception as e:
        logger.warning(f"Failed to load skin from config: {e}")


def save_skin_to_config(name: str) -> None:
    """Save the active skin to config file."""
    try:
        config_path = Path.home() / ".handsome_agent" / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        config = {}
        if config_path.exists():
            import json
            with open(config_path, encoding="utf-8") as f:
                config = json.load(f)

        if "display" not in config:
            config["display"] = {}

        config["display"]["skin"] = name

        with open(config_path, encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    except Exception as e:
        logger.warning(f"Failed to save skin to config: {e}")


# ============================================================================
# Initialize on import
# ============================================================================

# Load skin from config on import
load_skin_from_config()
