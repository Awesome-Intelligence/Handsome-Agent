#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Banner Module - Rich-powered terminal display.
Inspired by Hermes Agent's elegant design.

🚪 Access - 💬 CLI - Banner 组件

支持皮肤系统，通过 cli.skin_engine 获取主题颜色和品牌文案。

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
            # 直接打印第一个参数
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

from common.i18n import get_i18n

console = Console() if HAS_RICH else None

# ============================================================================
# Default colors (fallback when skin_engine not available)
# ============================================================================

AVOCADO = "rgb(139,154,70)"
AVOCADO_BRIGHT = "rgb(160,180,90)"
AVOCADO_DIM = "rgb(100,120,50)"
AVOCADO_DARK = "rgb(70,90,30)"

WHITE = "white"
GRAY_DIM = "dim"
GOLD = "rgb(255,215,0)"


# ============================================================================
# Helper function to get skin-aware colors
# ============================================================================

def _get_skin_color(key: str, fallback: str) -> str:
    """Get color from active skin, with fallback."""
    try:
        from cli.skin_engine import get_active_skin
        return get_active_skin().get_color(key, fallback)
    except ImportError:
        return fallback


def _get_skin_branding(key: str, fallback: str) -> str:
    """Get branding from active skin, with fallback."""
    try:
        from cli.skin_engine import get_active_skin
        return get_active_skin().get_branding(key, fallback)
    except ImportError:
        return fallback


# ============================================================================
# ASCII Art Logo - 高雅紫主题
# ============================================================================

# 主体 Logo - 竖排 "Handsome" (default skin)
HANDSOME_LOGO = """\
[bold #B180D7]░█░█░█▀█░█▀█░█▀▄░█▀▀░█▀█░█▄█░█▀▀[/]
[bold #B180D7]░█▀█░█▀█░█░█░█░█░▀▀█░█░█░█░█░█▀▀[/]
[bold #B180D7]░▀░▀░▀░▀░▀░▀░▀▀░░▀▀▀░▀▀▀░▀░▀░▀▀▀[/]"""

# Hero ASCII Art - 简约风格 (default skin)
HERO_ASCII = """\
[bold #A0B45A]░█▀█░█░█░█▀▀░█▀▀░█▀█░█▄█░█▀▀░░░▀█▀░█▀█░▀█▀░█▀▀░█░░░█░░░▀█▀░█▀▀░█▀▀░█▀█░█▀▀░█▀▀[/]
[bold #A0B45A]░█▀█░█▄█░█▀▀░▀▀█░█░█░█░█░█▀▀░░░░█░░█░█░░█░░█▀▀░█░░░█░░░░█░░█░█░█▀▀░█░█░█░░░█▀▀[/]
[bold #A0B45A]░▀░▀░▀░▀░▀▀▀░▀▀▀░▀▀▀░▀░▀░▀▀▀░░░▀▀▀░▀░▀░░▀░░▀▀▀░▀▀▀░▀▀▀░▀▀▀░▀▀▀░▀▀▀░▀░▀░▀▀▀░▀▀▀[/]
[dim #647030]                                                    Agent[/]"""


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
    """
    Build and print a welcome banner with rich styling.

    Args:
        model: Current model name
        provider: Model provider
        cwd: Current working directory
        tools_count: Number of available tools
        skills_count: Number of available skills
        session_id: Session identifier
        context_length: Model's context window size in tokens
        enabled_tools: List of enabled tool names
        config_status: Dict of configuration status
    """
    i18n = get_i18n()

    # Get skin-aware colors
    banner_border = _get_skin_color("banner_border", AVOCADO)
    banner_accent = _get_skin_color("banner_accent", AVOCADO_BRIGHT)
    banner_dim = _get_skin_color("banner_dim", AVOCADO_DIM)
    banner_title = _get_skin_color("banner_title", GOLD)
    banner_text = _get_skin_color("banner_text", "white")

    # Get skin-aware branding
    agent_name = _get_skin_branding("agent_name", "Handsome Agent")
    welcome_msg = _get_skin_branding("welcome", i18n.t("subtitle"))

    # Try to get custom logo from skin
    try:
        from cli.skin_engine import get_active_skin
        skin = get_active_skin()
        custom_logo = skin.banner_logo or skin.banner_hero
        if custom_logo:
            # Use skin's custom logo
            console.print()
            console.print(custom_logo)
            console.print()
    except Exception:
        # Use default logo
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
    for line in HANDSOME_LOGO.split('\n'):
        left_parts.append(line)

    left_parts.append("")
    left_parts.append(f"[dim {banner_dim}]Handsome Agent[/]")
    left_parts.append(f"[dim {banner_dim}]Handsome-Brain + OpenClaw-Body[/]")

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

        ui_ok = _get_skin_color("ui_ok", banner_border)
        ui_error = _get_skin_color("ui_error", "#888888")

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
        # Simple grouping based on prefix
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
    clean_logo = HANDSOME_LOGO.replace('[bold #8B9A46]', '').replace('[/]', '')
    
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


def print_setup_banner(config: dict = None) -> None:
    """Print banner for setup wizard using rich - unified style with chat.

    Args:
        config: Current configuration dict to display status.
    """
    i18n = get_i18n()

    if not HAS_RICH:
        # 降级到纯文本模式
        print_simple_banner()
        print(f"  ⚡ Setup Wizard")
        print(f"  {i18n.t('subtitle')}")
        print()
        return

    console.print()

    # 使用与 build_welcome_banner 一致的完整 ASCII logo + 状态面板
    content = f"""[bold {AVOCADO_BRIGHT}]
╔{'═' * 56}╗
║{' ' * 56}║
║{' ' * 56}║
║{' ' * 56}║
║{' ' * 56}║
║{' ' * 56}║
║{' ' * 56}║
║{' ' * 56}║
║{' ' * 56}║
║{' ' * 56}║
╚{'═' * 56}╝[/]"""

    # 使用完整的 build_welcome_banner 风格面板
    layout_table = Table.grid(padding=(1, 2))
    layout_table.add_column("left", justify="center", style=AVOCADO_BRIGHT)
    layout_table.add_column("right", justify="left", style="white")

    # Left panel - ASCII Art Logo
    left_parts = []
    for line in HANDSOME_LOGO.split('\n'):
        left_parts.append(line)
    left_parts.append("")
    left_parts.append(f"[dim {AVOCADO_DIM}]Handsome Agent[/]")
    left_parts.append(f"[dim {AVOCADO_DIM}]Handsome-Brain + OpenClaw-Body[/]")
    left_parts.append("")
    left_parts.append(f"[bold {AVOCADO}]⚡ Setup Wizard[/]")
    left_parts.append(f"[dim]{i18n.t('subtitle')}[/]")

    # Right panel - Setup Info with current config
    right_parts = []
    right_parts.append("")
    right_parts.append(f"[bold {AVOCADO_BRIGHT}]📋 Setup Status[/]")
    right_parts.append("")

    # Load current config if not provided
    if config is None:
        config = _load_current_config()

    # LLM Status
    llm = config.get('llm', {}) if isinstance(config, dict) else {}
    provider = llm.get('provider', '')
    model = llm.get('model', '')

    if provider and provider != 'none':
        model_short = model.split('/')[-1] if model else model
        if len(model_short) > 20:
            model_short = model_short[:17] + "..."
        right_parts.append(f"  [dim]▸[/] [white]{provider}[/] [dim]({model_short})[/]")
    else:
        right_parts.append(f"  [dim]○[/] [dim]LLM: Not configured[/]")

    # Terminal Backend
    terminal = config.get('terminal', {}) if isinstance(config, dict) else {}
    backend = terminal.get('backend', 'local')
    right_parts.append(f"  [dim]▸[/] [white]Terminal:[/] [dim]{backend}[/]")

    # Memory
    memory = config.get('memory', {}) if isinstance(config, dict) else {}
    mem_enabled = memory.get('enabled', True)
    mem_store = memory.get('vector_store', 'sqlite')
    mem_status = "✓" if mem_enabled else "✗"
    right_parts.append(f"  [dim]▸[/] [white]Memory:[/] [dim]{mem_store} {mem_status}[/]")

    # Intent Mode
    intent_mode = config.get('intent_mode', 'llm') if isinstance(config, dict) else 'llm'
    right_parts.append(f"  [dim]▸[/] [white]Intent:[/] [dim]{intent_mode}[/]")

    right_parts.append("")
    right_parts.append(f"[dim]{'-' * 30}[/]")
    right_parts.append(f"[dim]Type /help for commands[/]")
    right_parts.append(f"[dim]Type /setup to configure[/]")

    left_content = "\n".join(left_parts)
    right_content = "\n".join(right_parts)

    layout_table.add_row(left_content, right_content)

    panel = Panel(
        layout_table,
        title=f"[bold {GOLD}]Setup Wizard[/]",
        border_style=AVOCADO,
        padding=(1, 2),
    )

    console.print(panel)
    console.print()


def _load_current_config() -> dict:
    """Load current configuration from file."""
    config_file = os.path.expanduser("~/.handsome_agent/config.json")
    if os.path.exists(config_file):
        try:
            import json
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


# ============================================================================
# Rich-powered setup summary
# ============================================================================

def print_setup_summary(config_status: dict) -> None:
    """Print setup completion summary with rich styling."""
    
    if not HAS_RICH:
        # 降级到纯文本模式
        print()
        print("Configuration Summary")
        print("-" * 40)
        
        # LLM Config
        llm = config_status.get("llm", {})
        if llm.get("configured"):
            provider = llm.get("provider", "unknown")
            model = llm.get("model", "unknown")
            print(f"  ✓ LLM Provider: {provider} / {model}")
        else:
            print("  ○ LLM Provider: Not configured (basic mode)")
        
        # Terminal Config
        terminal = config_status.get("terminal", {})
        backend = terminal.get("backend", "local")
        print(f"  ✓ Terminal Backend: {backend}")
        
        # Memory
        memory = config_status.get("memory", {})
        if memory.get("enabled"):
            print(f"  ✓ Memory System: Vector {memory.get('vector_store', 'sqlite')}")
        else:
            print("  ○ Memory System: Disabled")
        
        # Tools
        tools = config_status.get("tools", {})
        tools_enabled = tools.get("count", 0)
        if tools_enabled > 0:
            print(f"  ✓ Tools Available: {tools_enabled} tools")
        else:
            print("  ○ Tools: None configured")
        
        print()
        return

    table = Table(title="[bold]Configuration Summary[/]", border_style=AVOCADO_DIM)
    table.add_column("Status", style=AVOCADO, width=10)
    table.add_column("Item", style=WHITE)
    table.add_column("Details", style=GRAY_DIM)

    # LLM Config
    llm = config_status.get("llm", {})
    if llm.get("configured"):
        provider = llm.get("provider", "unknown")
        model = llm.get("model", "unknown")
        table.add_row(
            f"[{AVOCADO}]✓[/]",
            "LLM Provider",
            f"{provider} / {model}"
        )
    else:
        table.add_row(
            f"[dim]○[/]",
            "LLM Provider",
            "Not configured (basic mode)"
        )

    # Terminal Config
    terminal = config_status.get("terminal", {})
    backend = terminal.get("backend", "local")
    table.add_row(
        f"[{AVOCADO}]✓[/]",
        "Terminal Backend",
        backend
    )

    # Memory
    memory = config_status.get("memory", {})
    if memory.get("enabled"):
        table.add_row(
            f"[{AVOCADO}]✓[/]",
            "Memory System",
            f"Vector: {memory.get('vector_store', 'sqlite')}"
        )
    else:
        table.add_row(
            f"[dim]○[/]",
            "Memory System",
            "Disabled"
        )

    # Tools
    tools = config_status.get("tools", {})
    tools_enabled = tools.get("count", 0)
    if tools_enabled > 0:
        table.add_row(
            f"[{AVOCADO}]✓[/]",
            "Tools Available",
            f"{tools_enabled} tools"
        )
    else:
        table.add_row(
            f"[dim]○[/]",
            "Tools",
            "None configured"
        )

    console.print()
    console.print(table)
    console.print()


def print_tool_status(tools_status: List[dict]) -> None:
    """Print tool availability status."""
    
    if not HAS_RICH:
        # 降级到纯文本模式
        print()
        print("Tool Status")
        print("-" * 40)
        
        for tool in tools_status:
            name = tool.get("name", "unknown")
            available = tool.get("available", False)
            hint = tool.get("hint", "")
            
            status = "✓" if available else "✗"
            hint_text = f" - {hint}" if hint else ""
            
            print(f"  {status} {name}{hint_text}")
        
        print()
        return

    table = Table(title="[bold]Tool Status[/]", border_style=AVOCADO_DIM)
    table.add_column("Tool", style=WHITE)
    table.add_column("Status", style=AVOCADO, width=12)
    table.add_column("Hint", style=GRAY_DIM)

    for tool in tools_status:
        name = tool.get("name", "unknown")
        available = tool.get("available", False)
        hint = tool.get("hint", "")

        status = f"[{AVOCADO}]✓[/]" if available else f"[dim]✗[/]"
        hint_text = hint if hint else ""

        table.add_row(name, status, hint_text)

    console.print()
    console.print(table)
    console.print()


# ============================================================================
# Quick entry point
# ============================================================================

if __name__ == "__main__":
    # Test banner
    print_simple_banner()

    print()
    print("=" * 60)
    print()

    build_welcome_banner(
        model="gpt-4o",
        provider="OpenAI",
        cwd="E:/Projects/Handsome-Agent",
        tools_count=15,
        skills_count=8,
        session_id="abc123",
        context_length=128000,
        enabled_tools=[
            "web_search", "web_scrape", "browser_open", "browser_click",
            "file_read", "file_write", "terminal_exec", "memory_save"
        ],
        config_status={
            "llm_configured": True,
            "tools_configured": True,
        }
    )


# ============================================================================
# 模块导出
# ============================================================================

__all__ = [
    "build_welcome_banner",
    "print_simple_banner",
    "print_setup_banner",
    "print_setup_summary",
    "print_tool_status",
    "HAS_RICH",
    # 常量
    "AVOCADO",
    "AVOCADO_BRIGHT",
    "AVOCADO_DIM",
    "AVOCADO_DARK",
    "WHITE",
    "GRAY_DIM",
    "GOLD",
]