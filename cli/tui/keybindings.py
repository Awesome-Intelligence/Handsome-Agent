#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Key Bindings Module - 重新导出自 cli.tui.core.keybindings

🚪 Access - 💬 CLI - TUI - Key Bindings

此文件已迁移到 cli/tui/core/keybindings.py，此文件提供向后兼容。

新代码请使用:
    from cli.tui.core.keybindings import ...
"""

# 重新导出自新位置
from cli.tui.core.keybindings import (
    KeyBinding,
    KeyBindingGroup,
    KeyBindingManager,
    KeyBindingCategory,
    create_default_keybindings,
)

__all__ = [
    "KeyBinding",
    "KeyBindingGroup",
    "KeyBindingManager",
    "KeyBindingCategory",
    "create_default_keybindings",
]
