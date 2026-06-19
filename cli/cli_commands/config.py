#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Config CLI module - 重新导出自 cli.config.config_cli

🚪 Access - 💬 CLI - 配置管理

此文件提供向后兼容，已迁移到 cli/config/config_cli.py。
"""

from cli.config.config_cli import (
    show_config,
    edit_config,
    set_config,
    get_config,
)

__all__ = [
    "show_config",
    "edit_config",
    "set_config",
    "get_config",
]
