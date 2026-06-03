#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Config CLI - Configuration management commands

🚪 Access - 💬 CLI - 配置管理
"""

import json
import os
import subprocess
from pathlib import Path


def _get_config_file() -> Path:
    """Get config file path."""
    config_dir = Path.home() / ".handsome_agent"
    config_dir.mkdir(exist_ok=True)
    return config_dir / "config.json"


def _load_config() -> dict:
    """Load config from file."""
    config_file = _get_config_file()
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_config(config: dict):
    """Save config to file."""
    config_file = _get_config_file()
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def show_config(json_output: bool = False):
    """Show current configuration."""
    config = _load_config()

    if json_output:
        print(json.dumps(config, indent=2))
        return

    from cli import ui

    ui.print_header("当前配置")

    if not config:
        ui.print_warning("配置文件为空或不存在")
        print("运行 'handsome setup' 进行配置")
        return

    # Print sections
    for section, values in config.items():
        print(f"\n  {section.upper()}:")
        if isinstance(values, dict):
            for key, value in values.items():
                print(f"    {key}: {value}")
        else:
            print(f"    {values}")


def edit_config():
    """Edit configuration in $EDITOR."""
    config_file = _get_config_file()

    # Create default config if not exists
    if not config_file.exists():
        default_config = {
            "llm": {
                "provider": "",
                "model": "",
            },
            "display": {},
            "preferences": {}
        }
        _save_config(default_config)

    # Open in editor
    editor = os.environ.get("EDITOR", "notepad" if os.name == "nt" else "nano")
    try:
        subprocess.run([editor, str(config_file)], check=True)
    except Exception as e:
        print(f"Failed to open editor: {e}")
        print(f"Config file: {config_file}")


def set_config(key: str, value: str):
    """Set a configuration value.

    Args:
        key: Configuration key (e.g., 'llm.provider')
        value: Configuration value
    """
    config = _load_config()

    # Parse key path (e.g., 'llm.provider' -> config['llm']['provider'] = value)
    parts = key.split(".")
    current = config

    for i, part in enumerate(parts[:-1]):
        if part not in current:
            current[part] = {}
        current = current[part]

    # Set value
    current[parts[-1]] = value

    _save_config(config)

    from cli import ui
    ui.print_success(f"已设置 {key} = {value}")


def get_config(key: str):
    """Get a configuration value.

    Args:
        key: Configuration key (e.g., 'llm.provider')
    """
    config = _load_config()

    # Parse key path
    parts = key.split(".")
    current = config

    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            print(f"Key '{key}' not found")
            return

    print(current)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "show":
            show_config()
        elif sys.argv[1] == "edit":
            edit_config()
        elif sys.argv[1] == "get" and len(sys.argv) > 2:
            get_config(sys.argv[2])
        elif sys.argv[1] == "set" and len(sys.argv) > 3:
            set_config(sys.argv[2], sys.argv[3])