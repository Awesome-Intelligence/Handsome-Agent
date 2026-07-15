#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LLM Provider 元数据目录（跨 tui/cli 共享）

🚪 Access - 💬 Common - LLM Providers

包含 Provider 模型清单、能力、定价、上下文窗口等元信息。
由 ``cli.cli_commands.providers`` 与 ``tui.views.settings_screen`` 等模块共用。
"""

from .catalog import PROVIDERS, get_provider_info, get_provider_ids

__all__ = [
    "PROVIDERS",
    "get_provider_info",
    "get_provider_ids",
]