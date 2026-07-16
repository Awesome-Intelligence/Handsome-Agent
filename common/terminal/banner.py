#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Banner Module - Rich-powered terminal display.

🚪 Access - 📦 Common - Terminal - Banner 组件

降级机制：
- Rich 不可用时使用纯文本模式
- 所有 Rich 功能都有 fallback
"""

import os
import shutil
from typing import List, Optional

# Rich 降级机制
HAS_RICH = True
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
except ImportError:
    HAS_RICH = False
    # 提供降级类型
    class Console:
        """降级的 Console 类"""
        def print(self, *args, **kwargs):
            for arg in args:
                print(str(arg))
    
    class Panel:
        """降级的 Panel 类"""
        def __init__(self, *args, **kwargs):
            self.content = args[0] if args else ""
    
    class Table:
        """降级的 Table 类"""
        def __init__(self, *args, **kwargs):
            pass
        
        def add_column(self, *args, **kwargs):
            pass
        
        def add_row(self, *args, **kwargs):
            pass
    
    class Text:
        """降级的 Text 类"""
        def __init__(self, *args, **kwargs):
            self.content = args[0] if args else ""

try:
    from common.i18n import get_i18n
except ImportError:
    def get_i18n():
        class SimpleI18n:
            def t(self, key, default=None):
                return default or key
        return SimpleI18n()

console = Console() if HAS_RICH else None

# ============================================================================
# Default theme colors (avocado purple)
# ============================================================================

AVOCADO = "rgb(139,154,70)"
AVOCADO_BRIGHT = "rgb(160,180,90)"
AVOCADO_DIM = "rgb(100,120,50)"
AVOCADO_DARK = "rgb(70,90,30)"

WHITE = "white"
GRAY_DIM = "dim"
GOLD = "rgb(255,215,0)"


# ============================================================================
# ASCII Art Logo - 白色主题
# ============================================================================

# Agent-Z ASCII Art Logo
AGENT_Z_LOGO = """\
[bold #FFFFFF]█▀█ █▀▀ █▀▀ █▀█ ▀█▀    ▀▀█[/]
[bold #FFFFFF]█▀█ █ █ █▀▀ █ █  █  ▀▀ ▄▀ [/]
[bold #FFFFFF]▀ ▀ ▀▀▀ ▀▀▀ ▀ ▀  ▀     ▀▀▀[/]"""

# Agent-Z ASCII Art Logo

# Hero ASCII Art - 简约风格
HERO_ASCII = """\
[bold #FFFFFF]░█▀█░█░█░█▀▀░█▀▀░█▀█░█▄█░█▀▀░░░▀█▀░█▀█░▀█▀░█▀▀░█░░░█░░░▀█▀░█▀▀░█▀▀░█▀█░█▀▀░█▀▀[/]
[bold #FFFFFF]░█▀█░█▄█░█▀▀░▀▀█░█░█░█░█░█▀▀░░░░█░░█░█░░█░░█▀▀░█░░░█░░░░█░░█░█░█▀▀░█░█░█░░░█▀▀[/]
[bold #FFFFFF]░▀░▀░▀░▀░▀▀▀░▀▀▀░▀▀▀░▀░▀░▀▀▀░░░▀▀▀░▀░▀░░▀░░▀▀▀░▀▀▀░▀▀▀░▀▀▀░▀▀▀░▀░▀░▀▀▀░▀▀▀[/]
[dim #999999]                                                    Agent[/]"""


# ============================================================================
# Banner Builder
# ============================================================================

def build_welcome_banner(
    model: Optional[str] = None,
    provider: Optional[str] = None,
    cwd: Optional[str] = None,
    tools_count: int = 0,
    skills_count: int = 0,
    session_id: Optional[str] = None,
    context_length: Optional[int] = None,
    enabled_tools: Optional[List[str]] = None,
    config_status: Optional[dict] = None,
) -> None:
    """Build and print a welcome banner with rich styling."""
    i18n = get_i18n()

    # Use fixed theme colors (avocado purple theme)
    banner_border = AVOCADO
    banner_accent = AVOCADO_BRIGHT
    banner_dim = AVOCADO_DIM
    banner_title = GOLD
    banner_text = "white"

    # Fixed branding
    agent_name = "Agent-Z"
    welcome_msg = i18n.t("subtitle")

    # Print default logo
    console.print()
    console.print(HERO_ASCII)
    console.print()

    # Create layout table
    layout_table = Table.grid(padding=(1, 2))
    layout_table.add_column("left", justify="center", style=banner_accent)
    layout_table.add_column("right", justify="left", style=banner_text)

    # Left panel - ASCII Art + Version
    left_parts = []

    # Add ASCII Logo
    for line in AGENT_Z_LOGO.split('\n'):
        left_parts.append(line)

    left_parts.append("")
    left_parts.append(f"[dim {banner_dim}]Agent-Z[/]")
    left_parts.append(f"[dim {banner_dim}]Hermes-Brain + OpenClaw-Body[/]")

    # Model info
    if model:
        model_short = model.split("/")[-1] if "/" in model else model
        if len(model_short) > 28:
            model_short = model_short[:25] + "..."

        ctx_str = f" [dim]({_format_context(context_length)} context)" if context_length else ""
        left_parts.append("")
        left_parts.append(f"[bold {banner_border}]▶[/] [bold]{model_short}[/]{ctx_str}")

    if provider:
        left_parts.append(f"[dim]via {provider}[/]")

    # CWD
    if cwd:
        cwd_short = cwd if len(cwd) <= 40 else "..." + cwd[-37:]
        left_parts.append("")
        left_parts.append(f"[dim]{cwd_short}[/]")

    # Session
    if session_id:
        left_parts.append(f"[dim]Session: {session_id}[/]")

    # Right panel - Quick Stats
    right_parts = []

    # Quick Stats
    if tools_count > 0 or skills_count > 0:
        right_parts.append("")
        right_parts.append(f"[bold {banner_accent}]⚡ Quick Stats[/]")
        right_parts.append("")

        if tools_count > 0:
            right_parts.append(f"  [dim]{banner_border}▪[/] [white]{tools_count}[/] [dim]tools[/]")

        if skills_count > 0:
            right_parts.append(f"  [dim]{banner_border}▪[/] [white]{skills_count}[/] [dim]skills[/]")

    # Enabled tools
    if enabled_tools and len(enabled_tools) > 0:
        right_parts.append("")
        right_parts.append(f"[bold {banner_accent}]🔧 Tool Sets[/]")
        right_parts.append("")

        # Group tools
        tool_groups = _group_tools(enabled_tools)
        for group, tools in tool_groups.items():
            tools_str = ", ".join(tools[:5])
            if len(tools) > 5:
                tools_str += f" [dim]+{len(tools) - 5}[/]"
            right_parts.append(f"  [dim]{banner_border}▸[/] [white]{group}[/]")
            right_parts.append(f"    [dim]{tools_str}[/]")

    # Config status
    if config_status:
        right_parts.append("")
        right_parts.append(f"[bold {banner_accent}]📋 Config Status[/]")
        right_parts.append("")

        llm_configured = config_status.get("llm_configured", False)
        tools_configured = config_status.get("tools_configured", False)

        # Fixed status colors
        ui_ok = "#4CAF50"  # Green
        ui_error = "#888888"  # Gray

        if llm_configured:
            right_parts.append(f"  [{ui_ok}]✓[/] [white]LLM Configured[/]")
        else:
            right_parts.append(f"  [dim]○[/] [dim]LLM Not Configured[/]")

        if tools_configured:
            right_parts.append(f"  [{ui_ok}]✓[/] [white]Tools Available[/]")
        else:
            right_parts.append(f"  [dim]○[/] [dim]Tools Not Configured[/]")

    # Tips
    right_parts.append("")
    right_parts.append(f"[dim]{'-' * 30}[/]")
    right_parts.append(f"[dim]Type /help for commands[/]")
    right_parts.append(f"[dim]Type /setup to configure[/]")

    # Combine
    left_content = "\n".join(left_parts)
    right_content = "\n".join(right_parts)

    layout_table.add_row(left_content, right_content)

    # Create panel
    version = i18n.t("version", default="v0.0.1")
    panel = Panel(
        layout_table,
        title=f"[bold {banner_title}]{agent_name} {version}[/]",
        border_style=banner_border,
        padding=(1, 2),
    )

    console.print(panel)
    console.print()


def _format_context(tokens: Optional[int]) -> str:
    """Format token count for display."""
    if not tokens:
        return "?"

    if tokens >= 1_000_000:
        val = tokens / 1_000_000
        rounded = round(val)
        if abs(val - rounded) < 0.05:
            return f"{rounded}M"
        return f"{val:.1f}M"
    elif tokens >= 1_000:
        val = tokens / 1_000
        rounded = round(val)
        if abs(val - rounded) < 0.05:
            return f"{rounded}K"
        return f"{val:.1f}K"
    return str(tokens)


def _group_tools(tools: List[str]) -> dict:
    """Group tools by category."""
    groups = {}
    for tool in tools:
        if any(x in tool.lower() for x in ["web", "search", "browser"]):
            group = "Web & Browser"
        elif any(x in tool.lower() for x in ["file", "read", "write", "edit"]):
            group = "File Operations"
        elif any(x in tool.lower() for x in ["memory", "remember"]):
            group = "Memory"
        elif any(x in tool.lower() for x in ["terminal", "shell", "exec"]):
            group = "Terminal"
        elif any(x in tool.lower() for x in ["tts", "stt", "voice", "audio"]):
            group = "Voice"
        elif any(x in tool.lower() for x in ["image", "vision", "gen"]):
            group = "Image"
        else:
            group = "General"

        groups.setdefault(group, []).append(tool)

    return groups


def print_simple_banner() -> None:
    """Print a simple text banner without rich dependencies."""
    i18n = get_i18n()

    # 清理 Rich 标记
    clean_logo = AGENT_Z_LOGO.replace('[bold #FFFFFF]', '').replace('[/]', '')
    
    print()
    print(f"╔{'═' * 56}╗")
    print(f"║{' ' * 56}║")
    print(f"║{' ' * 56}║")
    print(f"║   {clean_logo}{' ' * (56 - len(clean_logo.split(chr(10))[0]))}║")
    print(f"║{' ' * 56}║")
    print(f"║{' ' * 20}{i18n.t('subtitle')}{' ' * (36 - len(i18n.t('subtitle')))}║")
    print(f"║{' ' * 56}║")
    print(f"╚{'═' * 56}╝")
    print()


# ============================================================================
# Setup Wizard Banner Functions
# ============================================================================

def print_setup_banner(config: dict = None) -> None:
    """Print setup wizard banner with optional config info."""
    # 清理 Rich 标记
    clean_logo = AGENT_Z_LOGO.replace('[bold #000000]', '').replace('[/]', '')

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
        semantic = memory.get("semantic_retrieval_enabled", False)
        semantic_str = "Semantic" if semantic else "Basic"
        print(f"║   ✓ Memory: {semantic_str:<44}║")
    else:
        print(f"║   ○ Memory: Disabled{' ' * 40}║")

    print(f"║{' ' * 56}║")
    print(f"╚{'═' * 56}╝")
    print()


# ============================================================================
# 模块导出
# ============================================================================

__all__ = [
    "build_welcome_banner",
    "print_simple_banner",
    "print_setup_banner",
    "print_setup_summary",
    "HAS_RICH",
    # 常量
    "AGENT_Z_LOGO",
    "AVOCADO",
    "AVOCADO_BRIGHT",
    "AVOCADO_DIM",
    "AVOCADO_DARK",
    "WHITE",
    "GRAY_DIM",
    "GOLD",
]
