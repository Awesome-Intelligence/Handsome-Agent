#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dump - Configuration dump utility.

🚪 Access - 💬 CLI - 配置转储

提供配置导出功能，用于调试和支持。
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional


def dump_config(format: str = "json") -> str:
    """Dump current configuration.

    Args:
        format: Output format ('json', 'yaml', 'env')

    Returns:
        Dumped configuration as string
    """
    from common.config import load_config

    config = load_config()

    if format == "json":
        return json.dumps(config, indent=2, ensure_ascii=False)

    elif format == "yaml":
        import yaml
        return yaml.dump(config, default_flow_style=False, allow_unicode=True)

    elif format == "env":
        lines = []
        for section, values in config.items():
            if isinstance(values, dict):
                for key, value in values.items():
                    env_key = f"{section.upper()}_{key.upper()}"
                    lines.append(f"{env_key}={value}")
            else:
                lines.append(f"{section.upper()}={values}")
        return "\n".join(lines)

    else:
        raise ValueError(f"Unknown format: {format}")


def save_dump(filename: str, format: str = "json"):
    """Save configuration dump to file.

    Args:
        filename: Output filename
        format: Output format
    """
    content = dump_config(format)

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Config dumped to: {filename}")


def load_dump(filename: str) -> dict:
    """Load configuration from dump file.

    Args:
        filename: Dump file path

    Returns:
        Configuration dict
    """
    from common.config import save_config

    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()

    # Try JSON first
    try:
        config = json.loads(content)
        save_config(config)
        print(f"Config loaded from: {filename}")
        return config
    except json.JSONDecodeError:
        pass

    # Try YAML
    try:
        import yaml
        config = yaml.safe_load(content)
        save_config(config)
        print(f"Config loaded from: {filename}")
        return config
    except Exception:
        pass

    raise ValueError(f"Unable to parse file: {filename}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "load" and len(sys.argv) > 2:
            load_dump(sys.argv[2])
        else:
            save_dump(sys.argv[1])
    else:
        print(dump_config())