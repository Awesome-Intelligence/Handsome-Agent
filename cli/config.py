#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration management for Handsome Agent.

Config files are stored in ~/.handsome_agent/:
- ~/.handsome_agent/config.json  - All settings (model, toolsets, terminal, etc.)
- ~/.handsome_agent/.env         - API keys and secrets

🚪 Access - 💬 CLI - 配置管理

This module provides:
- handsome config show    - Show current configuration
- handsome config edit     - Open config in editor
- handsome config set      - Set a specific value
- handsome setup           - Run setup wizard
"""

import copy
import json
import logging
import os
import platform
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Dict

logger = logging.getLogger(__name__)

# 线程安全锁
_CONFIG_LOCK = threading.RLock()

# Windows 检测
_IS_WINDOWS = platform.system() == "Windows"

# Config file path
def get_handsome_home() -> Path:
    """Get the Handsome Agent home directory."""
    return Path.home() / ".handsome_agent"


def get_config_path() -> Path:
    """Get the config file path."""
    home = get_handsome_home()
    home.mkdir(parents=True, exist_ok=True)
    return home / "config.json"


def get_env_path() -> Path:
    """Get the .env file path."""
    home = get_handsome_home()
    home.mkdir(parents=True, exist_ok=True)
    return home / ".env"


# =============================================================================
# Config Cache
# =============================================================================

_CONFIG_CACHE: Dict[str, Any] = {}
# (path, mtime_ns, size) -> cached config dict.
# load_config() returns a deepcopy of the cached value when the file
# hasn't changed since the last load.

_LAST_LOAD_STATS: tuple[int, int] = (0, 0)


def _get_file_stats(path: Path) -> tuple[int, int]:
    """Get file stats (mtime_ns, size)."""
    try:
        st = path.stat()
        return st.st_mtime_ns, st.st_size
    except OSError:
        return 0, 0


def _load_from_file(path: Path) -> dict:
    """Load config from JSON file."""
    if not path.exists():
        return {}

    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse {path}: {e}. Using default config.")
        return {}


def _save_to_file(path: Path, config: dict):
    """Save config to JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


# =============================================================================
# Default Config
# =============================================================================

DEFAULT_CONFIG = {
    "llm": {
        "provider": "",
        "model": "",
        "api_key": "",
        "base_url": "",
    },
    "model": {
        "name": "",
        "context_window": 128000,
        "temperature": 0.7,
        "max_tokens": 4096,
    },
    "display": {
        "verbose": False,
        "show_reasoning": False,
        "language": "zh",
    },
    "preferences": {
        "explanation_depth": "detailed",
        "response_format": "markdown",
        "log_level": "info",
    },
    "session": {
        "enabled": True,
        "storage": "memory",
    },
    "memory": {
        "enabled": False,
        "type": "none",
    },
    "terminal": {
        "backend": "local",
    },
}


# =============================================================================
# Public API
# =============================================================================

def load_config(use_cache: bool = True) -> dict:
    """Load configuration from file.

    Args:
        use_cache: If True, use cached config if file hasn't changed.

    Returns:
        Configuration dict with defaults merged in.
    """
    global _CONFIG_CACHE, _LAST_LOAD_STATS

    config_path = get_config_path()
    current_stats = _get_file_stats(config_path)

    with _CONFIG_LOCK:
        # Check cache
        if use_cache and current_stats == _LAST_LOAD_STATS and _CONFIG_CACHE:
            return copy.deepcopy(_CONFIG_CACHE)

        # Load from file
        file_config = _load_from_file(config_path)

        # Merge with defaults
        config = _deep_merge(copy.deepcopy(DEFAULT_CONFIG), file_config)

        # Update cache
        _CONFIG_CACHE = config
        _LAST_LOAD_STATS = current_stats

        return copy.deepcopy(config)


def save_config(config: dict):
    """Save configuration to file.

    Args:
        config: Configuration dict to save.
    """
    global _CONFIG_CACHE, _LAST_LOAD_STATS

    config_path = get_config_path()

    with _CONFIG_LOCK:
        _save_to_file(config_path, config)
        _CONFIG_CACHE = config
        _LAST_LOAD_STATS = _get_file_stats(config_path)


def get_config_value(key_path: str, default: Any = None) -> Any:
    """Get a configuration value by dot-separated key path.

    Args:
        key_path: Dot-separated key path (e.g., 'llm.provider')
        default: Default value if key not found.

    Returns:
        Configuration value or default.
    """
    config = load_config()
    parts = key_path.split(".")
    current = config

    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return default

    return current


def set_config_value(key_path: str, value: Any):
    """Set a configuration value by dot-separated key path.

    Args:
        key_path: Dot-separated key path (e.g., 'llm.provider')
        value: Value to set.
    """
    config = load_config()
    parts = key_path.split(".")
    current = config

    # Navigate to the parent
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]

    # Set the value
    current[parts[-1]] = value

    save_config(config)


# =============================================================================
# Helpers
# =============================================================================

def _deep_merge(base: dict, overlay: dict) -> dict:
    """Deep merge overlay dict into base dict.

    Args:
        base: Base dict (will be modified in place)
        overlay: Overlay dict with values to merge

    Returns:
        Merged dict (same as base)
    """
    for key, value in overlay.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def reset_config():
    """Reset configuration to defaults."""
    save_config(copy.deepcopy(DEFAULT_CONFIG))


def ensure_config_exists():
    """Ensure config file exists with defaults."""
    config_path = get_config_path()
    if not config_path.exists():
        save_config(copy.deepcopy(DEFAULT_CONFIG))


def get_config_file_path() -> Path:
    """Get the config file path (alias for get_config_path)."""
    return get_config_path()


def is_configured() -> bool:
    """Check if LLM is configured."""
    config = load_config()
    provider = config.get("llm", {}).get("provider", "")
    model = config.get("model", {}).get("name", "") or config.get("llm", {}).get("model", "")
    return bool(provider and provider != "none" and model)


# =============================================================================
# Config Validation
# =============================================================================

@dataclass
class ConfigValidator:
    """Configuration validator."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def validate(self) -> bool:
        """Validate configuration.

        Returns:
            True if config is valid, False otherwise.
        """
        self.errors.clear()
        self.warnings.clear()

        config = load_config()

        # Check LLM config
        llm = config.get("llm", {})
        if not llm.get("provider"):
            self.warnings.append("LLM provider not configured")
        if not llm.get("model") and not config.get("model", {}).get("name"):
            self.warnings.append("Model not configured")

        # Check API key
        if llm.get("provider") not in ("none", "") and not llm.get("api_key"):
            self.warnings.append("API key not set for provider: " + llm.get("provider"))

        return len(self.errors) == 0

    def get_report(self) -> str:
        """Get validation report."""
        lines = []

        if self.errors:
            lines.append("Errors:")
            for error in self.errors:
                lines.append(f"  ✗ {error}")

        if self.warnings:
            lines.append("\nWarnings:")
            for warning in self.warnings:
                lines.append(f"  ⚠ {warning}")

        if not self.errors and not self.warnings:
            lines.append("✓ Configuration is valid")

        return "\n".join(lines)


# =============================================================================
# Install Method Detection
# =============================================================================

def detect_install_method() -> str:
    """Detect how Handsome Agent was installed.

    Returns:
        'pip', 'git', 'docker', or 'source'
    """
    # Check for install method stamp
    home = get_handsome_home()
    stamp = home / ".install_method"
    try:
        method = stamp.read_text(encoding="utf-8").strip().lower()
        if method:
            return method
    except OSError:
        pass

    # Check for git
    project_root = Path(__file__).parent.parent.resolve()
    if (project_root / ".git").is_dir():
        return "git"

    # Check for container
    if os.path.exists("/.dockerenv") or os.path.exists("/run/.containerenv"):
        return "docker"

    return "pip"


def stamp_install_method(method: str):
    """Write the install method stamp."""
    home = get_handsome_home()
    home.mkdir(parents=True, exist_ok=True)
    stamp = home / ".install_method"
    try:
        stamp.write_text(method + "\n", encoding="utf-8")
    except OSError:
        pass


if __name__ == "__main__":
    # Test config
    print(f"Config path: {get_config_path()}")
    print(f"Handsome home: {get_handsome_home()}")

    config = load_config()
    print(f"Loaded config: {json.dumps(config, indent=2)}")

    print(f"Is configured: {is_configured()}")