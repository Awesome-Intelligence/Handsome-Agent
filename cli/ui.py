#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Custom TUI Module - Geek Green themed terminal output.

🚪 Access - 💬 CLI - UI 组件

这是一个门面模块，将功能委托给专门的模块：
- cli.colors: 颜色定义和 Theme
- cli.cli_output: 输出函数
- cli.banner: Banner 渲染

参考 Hermes 的设计，将职责分离到专门的模块中。
"""

import os
import sys
import time
import shutil
import re
from typing import Optional, List, Dict, Any

# ============================================================================
# Re-export from specialized modules for backward compatibility
# ============================================================================

from cli.colors import (
    Colors,
    Theme,
    should_use_color,
    supports_ansi,
    enable_ansi_support,
    get_terminal_width,
    get_terminal_height,
    strip_color as strip_ansi,
    HEX_AVOCADO,
    HEX_AVOCADO_BRIGHT,
    HEX_AVOCADO_DIM,
    RGB_AVOCADO,
    RGB_AVOCADO_BRIGHT,
    RGB_AVOCADO_DIM,
)

from cli.cli_output import (
    print_info,
    print_success,
    print_warning,
    print_error,
    print_header,
    print_divider,
    print_step,
    print_substep,
    print_end_step,
    print_box,
    print_table_row,
    print_spinner,
    Spinner,
    prompt,
    prompt_yes_no,
    prompt_choice,
)

# ============================================================================
# Rich library integration
# ============================================================================

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

# Initialize rich console
_rich_console = Console() if HAS_RICH else None


# ============================================================================
# StatusBar (UI-specific, retained here)
# ============================================================================

class StatusBar:
    """Persistent status bar inspired by Hermes Agent."""

    def __init__(self):
        self.model = "Unknown"
        self.provider = ""
        self.session_start = time.time()
        self.token_count = 0
        self.max_tokens = 128000
        self.cost = 0.0
        self.tools_enabled = []
        self.yolo_mode = False
        self.connected = False

    def update_model(self, model_name: str, provider: str = ""):
        """Update current model name."""
        self.model = model_name[:26] if len(model_name) > 26 else model_name
        self.provider = provider

    def add_tokens(self, tokens: int):
        """Add to token count."""
        self.token_count += tokens

    def add_cost(self, cost: float):
        """Add to session cost."""
        self.cost += cost

    def set_tools(self, tools: list):
        """Set enabled tools."""
        self.tools_enabled = tools

    def toggle_yolo(self, enabled: bool):
        """Toggle YOLO mode."""
        self.yolo_mode = enabled

    def set_connected(self, connected: bool):
        """Set connection status."""
        self.connected = connected

    def get_duration(self) -> str:
        """Get formatted session duration."""
        elapsed = int(time.time() - self.session_start)
        minutes = elapsed // 60
        seconds = elapsed % 60
        if minutes < 60:
            return f"{minutes}m {seconds}s"
        hours = minutes // 60
        minutes = minutes % 60
        return f"{hours}h {minutes}m"

    def get_context_color(self) -> str:
        """Get color based on context usage."""
        ratio = self.token_count / self.max_tokens if self.max_tokens > 0 else 0
        if ratio < 0.5:
            return Theme.SUCCESS
        elif ratio < 0.8:
            return Theme.WARNING
        elif ratio < 0.95:
            return Colors.YELLOW_BRIGHT
        else:
            return Theme.ERROR

    def get_context_bar(self, width: int = 20) -> str:
        """Get visual context fill bar."""
        ratio = min(self.token_count / self.max_tokens, 1.0) if self.max_tokens > 0 else 0
        filled = int(ratio * width)
        empty = width - filled
        color = self.get_context_color()

        bar = f"{color}█{Colors.RESET}" * filled
        bar += f"{Colors.GRAY_DIM}░{Colors.RESET}" * empty
        return bar

    def render(self) -> str:
        """Render the status bar."""
        try:
            terminal_width = shutil.get_terminal_size().columns
        except:
            terminal_width = 80

        conn_icon = f"{Theme.SUCCESS}●{Colors.RESET}" if self.connected else f"{Theme.WARNING}○{Colors.RESET}"

        model_display = self.model
        if self.provider:
            model_display = f"{self.provider}:{self.model}"
        model_part = f"{Theme.PRIMARY_BOLD}{model_display}{Colors.RESET}"

        token_part = f"{Theme.SECONDARY_DIM}{self.token_count:,}/{self.max_tokens:,}{Colors.RESET}"

        context_bar = self.get_context_bar(12)

        cost_part = f"{Theme.SECONDARY}${self.cost:.4f}{Colors.RESET}" if self.cost > 0 else f"{Theme.SECONDARY_DIM}n/a{Colors.RESET}"

        duration_part = f"{Theme.SECONDARY}{self.get_duration()}{Colors.RESET}"

        yolo_badge = f" {Theme.ERROR_BRIGHT}{Colors.BOLD}⚠ YOLO{Colors.RESET}" if self.yolo_mode else ""

        tools_badge = f" {Theme.ACCENT}🔧{Colors.RESET}" if self.tools_enabled else ""

        if terminal_width >= 90:
            parts = [
                f"{Theme.BORDER}│{Colors.RESET}",
                conn_icon,
                model_part,
                f"{Theme.BORDER_DIM}│{Colors.RESET}",
                token_part,
                f"{Theme.BORDER_DIM}│{Colors.RESET}",
                context_bar,
                f"{Theme.BORDER_DIM}│{Colors.RESET}",
                cost_part,
                f"{Theme.BORDER_DIM}│{Colors.RESET}",
                duration_part,
                yolo_badge,
                tools_badge,
            ]
        elif terminal_width >= 60:
            parts = [
                f"{Theme.BORDER}│{Colors.RESET}",
                conn_icon,
                model_part,
                f"{Theme.BORDER_DIM}│{Colors.RESET}",
                token_part,
                f"{Theme.BORDER_DIM}│{Colors.RESET}",
                duration_part,
                yolo_badge,
                tools_badge,
            ]
        else:
            parts = [
                f"{Theme.BORDER}│{Colors.RESET}",
                conn_icon,
                model_part,
                f"{Theme.BORDER_DIM}│{Colors.RESET}",
                duration_part,
            ]

        return " ".join(parts)


# Global status bar instance
status_bar = StatusBar()


# ============================================================================
# Banner (delegated to cli.banner)
# ============================================================================

def print_banner(model: str = None, tools_count: int = None, skills_count: int = None, version: str = "0.0.1"):
    """Print welcome banner - 委托给 cli.banner 统一处理"""
    from cli.banner import build_welcome_banner, print_simple_banner

    try:
        # 尝试使用 rich 版本
        if HAS_RICH:
            build_welcome_banner(
                model=model,
                provider=None,
                cwd=os.getcwd(),
                tools_count=tools_count or 0,
                skills_count=skills_count or 0,
                context_length=None,
            )
        else:
            print_simple_banner()
    except Exception:
        # 降级使用简单版本
        print_banner_simple()


def print_banner_simple():
    """Print simple banner without rich enhancements (fallback)."""
    print_header("Handsome Agent", "Welcome!")
    print(f"  {Theme.PRIMARY_BOLD}🚀 Handsome Agent V 0.0.1{Colors.RESET}")
    print()


# ============================================================================
# Box Drawing Helpers (UI-specific)
# ============================================================================

def print_top_border(width: int = 0):
    """Print top border with corners."""
    width = width or get_terminal_width()
    print(f"{Theme.BORDER}╭{'─' * (width - 2)}╮{Colors.RESET}")


def print_bottom_border(width: int = 0):
    """Print bottom border with corners."""
    width = width or get_terminal_width()
    print(f"{Theme.BORDER}╰{'─' * (width - 2)}╯{Colors.RESET}")


def print_border_side(content: str, width: int = 0, align: str = "left"):
    """Print content with side borders."""
    width = width or get_terminal_width()
    content_len = len(strip_ansi(content))
    padding = width - content_len - 4
    if padding < 0:
        padding = 0

    if align == "right":
        content = f"{' ' * padding}{content}"
    elif align == "center":
        content = f"{' ' * (padding // 2)}{content}"

    padding_right = width - len(strip_ansi(content)) - 4
    if padding_right < 0:
        padding_right = 0

    print(f"{Theme.BORDER}│{Colors.RESET} {content}{' ' * padding_right}{Theme.BORDER}│{Colors.RESET}")


def print_boxed_message(message: str, style: str = "info"):
    """Print a message in a box with styling."""
    width = min(get_terminal_width(), 80)

    color_map = {
        "success": Theme.SUCCESS,
        "error": Theme.ERROR,
        "warning": Theme.WARNING,
        "info": Theme.INFO,
    }

    border_color = color_map.get(style, Theme.BORDER)

    print()
    print(f"{border_color}╭{'─' * (width - 2)}╮{Colors.RESET}")
    print_border_side(message, width, "left")
    print(f"{border_color}╰{'─' * (width - 2)}╯{Colors.RESET}")
    print()


# ============================================================================
# UI-specific Output Functions
# ============================================================================

def print_prompt(message: str = None) -> str:
    """Print input prompt and return the prompt string."""
    if message:
        print(f"{Theme.ACCENT}{message}{Colors.RESET}")
    return f"{Theme.ACCENT}❯{Colors.RESET} "


def print_header_text(text: str):
    """Print header text."""
    print(f"{Theme.PRIMARY_BOLD}{text}{Colors.RESET}")


def print_menu(options: List[tuple], selected: int = None):
    """Print menu with consistent styling."""
    for i, (key, desc) in enumerate(options):
        if i == selected:
            marker = f"{Theme.ACCENT}❯"
            num = f"{Theme.ACCENT}{i + 1}."
        else:
            marker = " "
            num = f"{Colors.GRAY}{i + 1}."
        print(f"  {marker} {num} {Theme.SECONDARY}{desc}{Colors.RESET}")


def print_config_item(key: str, value: str):
    """Print configuration item."""
    print(f"  {Theme.SECONDARY_DIM}▸{Colors.RESET} {Theme.SECONDARY}{key}:{Colors.RESET} {Theme.PRIMARY}{value}{Colors.RESET}")


def print_list(items: List[str], title: str = None, icon: str = "•"):
    """Print a formatted list of items."""
    if title:
        print(f"{Theme.PRIMARY_BOLD}{title}{Colors.RESET}")
    for item in items:
        print(f"  {Theme.ACCENT}{icon}{Colors.RESET} {item}")


def print_agent_response(response: str, confidence: float = None):
    """Print agent response with beautiful formatting."""
    print()
    print_divider("─")
    print(f"{Theme.PRIMARY_BOLD}🤖 Assistant:{Colors.RESET}")
    print_divider("─")
    print()
    print(f"{Theme.SECONDARY}{response}{Colors.RESET}")

    if confidence is not None:
        conf_color = Theme.SUCCESS if confidence > 0.7 else Theme.WARNING if confidence > 0.4 else Theme.ERROR
        print()
        print(f"{Theme.SECONDARY_DIM}Confidence: {conf_color}{confidence:.0%}{Colors.RESET}")


def print_status_bar():
    """Print the persistent status bar."""
    print()
    print_divider("─")
    print(status_bar.render())
    print_divider("─")


def print_user_input(prompt: str = None):
    """Print user input prompt with icon."""
    if prompt:
        print(f"{Theme.ACCENT}👤 {prompt}:{Colors.RESET}")
    print(f"{Theme.ACCENT}❯{Colors.RESET} ", end="")


def print_provider_list(providers: List[Dict[str, Any]]):
    """Print the list of available LLM providers."""
    print(f"{Theme.BORDER}│{Colors.RESET}")
    print(f"{Theme.BORDER}│{Colors.RESET} {Theme.PRIMARY_BOLD}可用的大模型提供商:{Colors.RESET}")
    print(f"{Theme.BORDER}│{Colors.RESET}")

    for i, provider in enumerate(providers, 1):
        provider_name = provider.get("name", "Unknown")
        provider_description = provider.get("description", "")
        provider_models = provider.get("models", [])
        default_model = provider.get("default_model", "")

        print(f"{Theme.BORDER}│{Colors.RESET}")
        print(f"{Theme.BORDER}│{Colors.RESET} {Theme.SUCCESS}{i}. {provider_name}{Colors.RESET}")
        if provider_description:
            print(f"{Theme.BORDER}│{Colors.RESET}   {Theme.SECONDARY}{provider_description}{Colors.RESET}")
        if provider_models:
            print(f"{Theme.BORDER}│{Colors.RESET}   {Theme.SECONDARY_DIM}支持模型: {', '.join(provider_models[:3])}{'...' if len(provider_models) > 3 else ''}{Colors.RESET}")
        if default_model:
            print(f"{Theme.BORDER}│{Colors.RESET}   {Theme.SECONDARY_DIM}默认模型: {default_model}{Colors.RESET}")

    print(f"{Theme.BORDER}│{Colors.RESET}")


def print_setup_complete():
    """Print setup completion message."""
    print()
    print_divider("─")
    print(f"{Theme.SUCCESS}✓ 配置已保存!{Colors.RESET}")
    print_divider("─")
    print()


# ============================================================================
# Rich-based helper functions
# ============================================================================

def print_rich_table(data: List[List[str]], headers: List[str] = None,
                     title: str = None, style: str = "accent") -> None:
    """Print data as a rich table."""
    if not HAS_RICH:
        # Fallback to simple text table
        print()
        if title:
            print(f"{Theme.PRIMARY_BOLD}{title}{Colors.RESET}")
        if headers:
            print("  " + " | ".join(headers))
            print("  " + "-" * len(" | ".join(headers)))
        for row in data:
            print("  " + " | ".join(row))
        print()
        return

    table = Table(show_header=headers is not None, box=box.ROUNDED)

    color_map = {
        "accent": "#8B9A46",
        "success": "#4CAF50",
        "warning": "#FF9800",
        "error": "#F44336",
    }
    border_color = color_map.get(style, "#8B9A46")

    if headers:
        for h in headers:
            table.add_column(h, style=border_color)
    elif data:
        for _ in data[0]:
            table.add_column()

    for row in data:
        table.add_row(*row)

    if title:
        print()
        print(f"{Theme.PRIMARY_BOLD}{title}{Colors.RESET}")

    _rich_console.print(table)
    print()


def print_rich_panel(content: str, title: str = None,
                     style: str = "accent", width: int = None) -> None:
    """Print content in a rich panel."""
    if not HAS_RICH:
        print_boxed_message(content, style)
        return

    color_map = {
        "accent": "#8B9A46",
        "success": "#4CAF50",
        "warning": "#FF9800",
        "error": "#F44336",
        "info": "#2196F3",
    }
    border_color = color_map.get(style, "#8B9A46")

    if width is None:
        try:
            width = min(shutil.get_terminal_size().columns, 80)
        except:
            width = 80

    panel = Panel(
        content,
        title=title,
        border_style=border_color,
        padding=(1, 2),
        width=width
    )
    _rich_console.print(panel)


def print_rich_progress(items: List[str], title: str = None,
                        style: str = "accent") -> None:
    """Print items as a rich list with optional title."""
    if not HAS_RICH:
        print_list(items, title)
        return

    color_map = {
        "accent": "#8B9A46",
        "success": "#4CAF50",
        "warning": "#FF9800",
        "error": "#F44336",
    }
    item_color = color_map.get(style, "#8B9A46")

    if title:
        print(f"\n{Theme.PRIMARY_BOLD}{title}{Colors.RESET}")

    for item in items:
        _rich_console.print(f"[{item_color}]•[/{item_color}] {item}")


def print_rich_success(message: str) -> None:
    """Print success message with rich styling."""
    if HAS_RICH:
        _rich_console.print(f"[bold #4CAF50]✓[/] {message}")
    else:
        print_success(message)


def print_rich_error(message: str) -> None:
    """Print error message with rich styling."""
    if HAS_RICH:
        _rich_console.print(f"[bold #F44336]✗[/] {message}")
    else:
        print_error(message)


def print_rich_warning(message: str) -> None:
    """Print warning message with rich styling."""
    if HAS_RICH:
        _rich_console.print(f"[bold #FF9800]⚠[/] {message}")
    else:
        print_warning(message)


def print_rich_info(message: str) -> None:
    """Print info message with rich styling."""
    if HAS_RICH:
        _rich_console.print(f"[bold #2196F3]ℹ[/] {message}")
    else:
        print_info(message)


# ============================================================================
# Backward compatibility aliases (deprecated, use cli_output instead)
# ============================================================================

def supports_color() -> bool:
    """Check if terminal supports colors. Alias for should_use_color()."""
    return should_use_color()