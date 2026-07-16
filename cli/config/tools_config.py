#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tools Config - Tool configuration management.

🚪 Access - 💬 CLI - 工具配置

提供工具集启用/禁用、工具参数配置等管理功能。
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


# Tool categories
TOOL_CATEGORIES = {
    "web": {
        "name": "Web & Browser",
        "tools": ["web_search", "web_scrape", "browser_open", "browser_click", "browser_type"],
    },
    "file": {
        "name": "File Operations",
        "tools": ["file_read", "file_write", "file_edit", "file_delete", "dir_list"],
    },
    "terminal": {
        "name": "Terminal",
        "tools": ["terminal_exec", "terminal_run_script"],
    },
    "memory": {
        "name": "Memory",
        "tools": ["memory_save", "memory_search", "memory_delete"],
    },
    "image": {
        "name": "Image",
        "tools": ["image_gen", "image_edit", "vision_analyze"],
    },
    "voice": {
        "name": "Voice",
        "tools": ["tts_speak", "stt_listen"],
    },
    "general": {
        "name": "General",
        "tools": ["app_launcher", "webhook_trigger", "http_request"],
    },
}


def get_config_path() -> Path:
    """Get the tools config file path."""
    config_dir = Path.home() / ".agent_z"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "tools_config.json"


def load_tools_config() -> Dict[str, Any]:
    """Load tools configuration.

    Returns:
        Tools config dict
    """
    config_path = get_config_path()
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return _default_config()


def save_tools_config(config: Dict[str, Any]):
    """Save tools configuration.

    Args:
        config: Tools config dict
    """
    config_path = get_config_path()
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def _default_config() -> Dict[str, Any]:
    """Get default tools configuration.

    Returns:
        Default config dict
    """
    return {
        "enabled_toolsets": ["web", "file", "terminal", "general"],
        "disabled_toolsets": [],
        "tool_params": {},
        "approval_mode": "ask",  # ask, auto_approve, auto_reject
        "dangerous_tools": ["terminal_exec"],
    }


def get_enabled_toolsets() -> List[str]:
    """Get list of enabled toolset names.

    Returns:
        List of enabled toolset names
    """
    config = load_tools_config()
    return config.get("enabled_toolsets", [])


def get_disabled_toolsets() -> List[str]:
    """Get list of disabled toolset names.

    Returns:
        List of disabled toolset names
    """
    config = load_tools_config()
    return config.get("disabled_toolsets", [])


def enable_toolset(toolset: str):
    """Enable a toolset.

    Args:
        toolset: Toolset name
    """
    config = load_tools_config()

    if toolset not in TOOL_CATEGORIES:
        return

    # Remove from disabled if present
    if toolset in config.get("disabled_toolsets", []):
        config["disabled_toolsets"].remove(toolset)

    # Add to enabled if not present
    if toolset not in config.get("enabled_toolsets", []):
        config.setdefault("enabled_toolsets", []).append(toolset)

    save_tools_config(config)


def disable_toolset(toolset: str):
    """Disable a toolset.

    Args:
        toolset: Toolset name
    """
    config = load_tools_config()

    if toolset not in TOOL_CATEGORIES:
        return

    # Remove from enabled if present
    if toolset in config.get("enabled_toolsets", []):
        config["enabled_toolsets"].remove(toolset)

    # Add to disabled if not present
    if toolset not in config.get("disabled_toolsets", []):
        config.setdefault("disabled_toolsets", []).append(toolset)

    save_tools_config(config)


def is_toolset_enabled(toolset: str) -> bool:
    """Check if a toolset is enabled.

    Args:
        toolset: Toolset name

    Returns:
        True if toolset is enabled
    """
    config = load_tools_config()

    enabled = config.get("enabled_toolsets", [])
    disabled = config.get("disabled_toolsets", [])

    # If specific list is used, only enabled ones are allowed
    if enabled:
        return toolset in enabled

    # Otherwise, only disabled ones are blocked
    return toolset not in disabled


def get_tool_params(tool_name: str) -> Dict[str, Any]:
    """Get parameters for a tool.

    Args:
        tool_name: Tool name

    Returns:
        Tool parameters dict
    """
    config = load_tools_config()
    return config.get("tool_params", {}).get(tool_name, {})


def set_tool_params(tool_name: str, params: Dict[str, Any]):
    """Set parameters for a tool.

    Args:
        tool_name: Tool name
        params: Parameters dict
    """
    config = load_tools_config()
    config.setdefault("tool_params", {})[tool_name] = params
    save_tools_config(config)


def get_approval_mode() -> str:
    """Get approval mode for dangerous tools.

    Returns:
        Approval mode: 'ask', 'auto_approve', or 'auto_reject'
    """
    config = load_tools_config()
    return config.get("approval_mode", "ask")


def set_approval_mode(mode: str):
    """Set approval mode.

    Args:
        mode: Approval mode
    """
    if mode not in ("ask", "auto_approve", "auto_reject"):
        return

    config = load_tools_config()
    config["approval_mode"] = mode
    save_tools_config(config)


def list_toolsets() -> List[Dict[str, Any]]:
    """List all available toolsets.

    Returns:
        List of toolset info dicts
    """
    result = []

    for name, info in TOOL_CATEGORIES.items():
        result.append({
            "name": name,
            "display_name": info["name"],
            "tools": info["tools"],
            "enabled": is_toolset_enabled(name),
        })

    return result


if __name__ == "__main__":
    print("Available toolsets:")
    for ts in list_toolsets():
        status = "✓" if ts["enabled"] else "✗"
        print(f"  {status} {ts['name']} ({ts['display_name']})")
        print(f"     Tools: {', '.join(ts['tools'])}")
