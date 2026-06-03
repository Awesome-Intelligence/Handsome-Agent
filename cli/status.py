#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Status command - Show system status

🚪 Access - 💬 CLI - 状态显示
"""

import json
from typing import Optional


def show_status(verbose: bool = False, json_output: bool = False):
    """Show system status.

    Args:
        verbose: Show detailed status
        json_output: Output as JSON
    """
    from cli import ui
    from common.config import get_settings

    # Load config
    try:
        settings = get_settings()
        config = settings.model_dump() if hasattr(settings, 'model_dump') else {}
    except Exception:
        config = {}

    # Build status dict
    status = {
        "llm": {
            "provider": config.get("llm", {}).get("provider", "Not configured"),
            "model": config.get("model", {}).get("name", "Not configured"),
            "context_window": config.get("model", {}).get("context_window", None),
        },
        "session": {
            "enabled": config.get("session", {}).get("enabled", True),
            "storage": config.get("session", {}).get("storage", "memory"),
        },
        "memory": {
            "enabled": config.get("memory", {}).get("enabled", False),
            "type": config.get("memory", {}).get("type", "none"),
        },
    }

    if verbose:
        status["display"] = config.get("display", {})
        status["preferences"] = config.get("preferences", {})

    if json_output:
        print(json.dumps(status, indent=2))
        return

    # Text output
    ui.print_header("系统状态")

    # LLM
    llm = status["llm"]
    if llm["provider"] != "Not configured":
        ui.print_success("✓ LLM 已配置")
        print(f"  Provider: {llm['provider']}")
        print(f"  Model: {llm['model']}")
        if llm['context_window']:
            print(f"  Context: {llm['context_window']} tokens")
    else:
        ui.print_warning("○ LLM 未配置")
        print("  运行 'handsome setup' 配置")

    print()

    # Session
    session = status["session"]
    if session["enabled"]:
        ui.print_success("✓ Session 已启用")
        print(f"  Storage: {session['storage']}")
    else:
        ui.print_warning("○ Session 已禁用")

    print()

    # Memory
    memory = status["memory"]
    if memory["enabled"]:
        ui.print_success("✓ Memory 已启用")
        print(f"  Type: {memory['type']}")
    else:
        ui.print_info("○ Memory 未启用")


if __name__ == "__main__":
    show_status()