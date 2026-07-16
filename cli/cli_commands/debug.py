#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug - Debug information and dump utilities.

🚪 Access - 💬 CLI - 调试工具

提供调试信息导出功能。
"""

import json
import os
import platform
import sys
from datetime import datetime
from pathlib import Path


def get_debug_info() -> dict:
    """Get debug information.

    Returns:
        Debug info dict
    """
    from common.config import load_config

    config = load_config()

    return {
        "timestamp": datetime.now().isoformat(),
        "python": {
            "version": sys.version,
            "executable": sys.executable,
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "cwd": os.getcwd(),
        "user": {
            "name": os.getenv("USER") or os.getenv("USERNAME") or "unknown",
            "home": str(Path.home()),
        },
        "config": config,
        "environment": {
            k: v for k, v in os.environ.items()
            if any(x in k.upper() for x in ["API", "KEY", "TOKEN", "SECRET", "PASSWORD"])
        } if False else {},  # Don't include secrets by default
    }


def dump_config(output_file: str = None):
    """Dump configuration for debugging.

    Args:
        output_file: Optional output file path
    """
    from cli import ui

    info = get_debug_info()

    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(info, f, indent=2, ensure_ascii=False)
        ui.print_success(f"Config dumped to: {output_file}")
    else:
        print(json.dumps(info, indent=2))


def export_debug_report() -> str:
    """Export a debug report.

    Returns:
        Debug report text
    """
    info = get_debug_info()

    lines = []
    lines.append("=" * 60)
    lines.append("Agent-Z DEBUG REPORT")
    lines.append("=" * 60)
    lines.append(f"Generated: {info['timestamp']}")
    lines.append("")

    lines.append("Python:")
    lines.append(f"  Version: {info['python']['version']}")
    lines.append(f"  Executable: {info['python']['executable']}")
    lines.append("")

    lines.append("Platform:")
    lines.append(f"  System: {info['platform']['system']}")
    lines.append(f"  Release: {info['platform']['release']}")
    lines.append(f"  Machine: {info['platform']['machine']}")
    lines.append("")

    lines.append("Environment:")
    lines.append(f"  CWD: {info['cwd']}")
    lines.append(f"  User: {info['user']['name']}")
    lines.append(f"  Home: {info['user']['home']}")
    lines.append("")

    lines.append("Configuration:")
    config = info.get('config', {})
    for section, values in config.items():
        lines.append(f"  {section}:")
        if isinstance(values, dict):
            for key, value in values.items():
                lines.append(f"    {key}: {value}")
        else:
            lines.append(f"    {values}")

    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)


if __name__ == "__main__":
    print(export_debug_report())