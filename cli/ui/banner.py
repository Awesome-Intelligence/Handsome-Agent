#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Banner Module - CLI 特有的 Banner 组件

🚪 Access - 💬 CLI - Banner 组件

CLI 特有的 setup wizard banner 功能。
通用 banner 功能请使用 common.terminal.banner
"""

# 通用 banner 功能请从 common.terminal.banner 导入：
# from common.terminal.banner import build_welcome_banner, print_simple_banner

# CLI 特有的 setup wizard banner
HANDSOME_LOGO = """\
[bold #B180D7]░█░█░█▀█░█▀█░█▀▄░█▀▀░█▀█░█▄█░█▀▀[/]
[bold #B180D7]░█▀█░█▀█░█░█░█░█░▀▀█░█░█░█░█░█▀▀[/]
[bold #B180D7]░▀░▀░▀░▀░▀░▀░▀▀░░▀▀▀░▀▀▀░▀░▀░▀▀▀[/]"""


def print_setup_banner(config: dict = None) -> None:
    """Print setup wizard banner with optional config info."""
    # 清理 Rich 标记
    clean_logo = HANDSOME_LOGO.replace('[bold #B180D7]', '').replace('[/]', '')

    print()
    print(f"╔{'═' * 56}╗")
    print(f"║{' ' * 56}║")

    # Logo
    for line in clean_logo.split('\n'):
        print(f"║   {line}{' ' * (56 - len(line))}║")

    print(f"║{' ' * 56}║")
    print(f"║   ⚙️  Setup Wizard{' ' * 38}║")
    print(f"║{' ' * 56}║")

    # 显示配置状态
    if config:
        llm = config.get('llm', {})
        provider = llm.get('provider', 'none')
        model = llm.get('model', '')
        if provider and provider != 'none':
            status_text = f"LLM: {provider}"
            if model:
                status_text += f" / {model}"
            print(f"║   ✓ {status_text:<52}║")
        else:
            print(f"║   ○ {'Not configured':<49}║")
    else:
        print(f"║   ○ {'Not configured':<49}║")

    print(f"║{' ' * 56}║")
    print(f"╚{'═' * 56}╝")
    print()


def print_setup_summary(config_status: dict) -> None:
    """Print setup configuration summary."""
    print()
    print(f"╔{'═' * 56}╗")
    print(f"║{' ' * 56}║")
    print(f"║   📋 Configuration Summary{' ' * 30}║")
    print(f"║{' ' * 56}║")

    # LLM Status
    llm = config_status.get("llm", {})
    if llm.get("configured"):
        print(f"║   ✓ LLM: {llm.get('provider', 'unknown'):<46}║")
        if llm.get("model"):
            print(f"║     Model: {llm.get('model', '')[:44]:<44}║")
    else:
        print(f"║   ○ LLM: Not configured{' ' * 37}║")

    print(f"║{' ' * 56}║")

    # Terminal Status
    terminal = config_status.get("terminal", {})
    backend = terminal.get("backend", "local")
    print(f"║   ✓ Terminal: {backend:<45}║")

    print(f"║{' ' * 56}║")

    # Memory Status
    memory = config_status.get("memory", {})
    if memory.get("enabled"):
        vector_store = memory.get("vector_store", "sqlite")
        print(f"║   ✓ Memory: {vector_store:<44}║")
    else:
        print(f"║   ○ Memory: Disabled{' ' * 40}║")

    print(f"║{' ' * 56}║")
    print(f"╚{'═' * 56}╝")
    print()
