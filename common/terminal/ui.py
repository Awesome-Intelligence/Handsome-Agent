#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Custom TUI Module - Geek Green themed terminal output.

🚪 Access - 💬 CLI - UI 组件

这是一个门面模块，将功能委托给专门的模块：
- cli.components.colors: 颜色定义和 Theme
- cli.components.output: 输出函数
- cli.components.banner: Banner 渲染

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

from .colors import (
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

from .output import (
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
# Round formatting helpers
# ============================================================================

DIGIT_EMOJI = {
    "0": "0️⃣", "1": "1️⃣", "2": "2️⃣", "3": "3️⃣", "4": "4️⃣",
    "5": "5️⃣", "6": "6️⃣", "7": "7️⃣", "8": "8️⃣", "9": "9️⃣",
}


def format_round(n: int, max_digits: int = 4) -> str:
    """Format round number with digit emojis.
    
    Args:
        n: The round number
        max_digits: Maximum digits to display before truncating
        
    Returns:
        Emoji-formatted string like "1️⃣5️⃣" or "1️⃣0️⃣0️⃣0️⃣+"
    """
    s = str(n)
    if len(s) <= max_digits:
        return "".join(DIGIT_EMOJI[d] for d in s)
    # Truncate and add +
    truncated = "".join(DIGIT_EMOJI[d] for d in s[:max_digits])
    return f"{truncated}+"


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
        self.llm_call_count = 0

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

    def increment_llm_call(self):
        """Increment the LLM call counter."""
        self.llm_call_count += 1

    def reset_llm_call_count(self):
        """Reset the LLM call counter for a new dialogue round."""
        self.llm_call_count = 0

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
        except OSError:
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

        round_part = format_round(self.llm_call_count) if self.llm_call_count > 0 else f"{Theme.SECONDARY_DIM}n/a{Colors.RESET}"

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
                f"{Theme.BORDER_DIM}│{Colors.RESET}",
                round_part,
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
                f"{Theme.BORDER_DIM}│{Colors.RESET}",
                round_part,
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
# Banner (delegated to cli.components.banner)
# ============================================================================

def print_banner(model: str = None, tools_count: int = None, skills_count: int = None, version: str = "0.0.1"):
    """Print welcome banner - 委托给 cli.components.banner 统一处理"""
    from .banner import build_welcome_banner, print_simple_banner

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
    print_header("Agent-Z", "Welcome!")
    print(f"  {Theme.PRIMARY_BOLD}🚀 Agent-Z V 0.0.1{Colors.RESET}")
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
        # 支持 display_name 和 name 两种字段
        provider_name = provider.get("display_name", provider.get("name", "Unknown"))
        provider_models = provider.get("supported_models", provider.get("models", []))
        default_model = provider.get("default_model", "")

        print(f"{Theme.BORDER}│{Colors.RESET}")
        print(f"{Theme.BORDER}│{Colors.RESET} {Theme.SUCCESS}{i}. {provider_name}{Colors.RESET}")
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
        except OSError:
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
# Backward compatibility aliases (deprecated, use output instead)
# ============================================================================

def supports_color() -> bool:
    """Check if terminal supports colors. Alias for should_use_color()."""
    return should_use_color()


# ============================================================================
# UI Facade - 提供统一的属性访问接口
# ============================================================================

class _UIFacade:
    """UI 门面类 - 提供统一的属性访问接口"""

    def __init__(self):
        # 颜色和主题
        self.Colors = Colors
        self.Theme = Theme
        self.Colors_class = Colors
        self.Theme_class = Theme

        # 状态栏
        self.status_bar = status_bar
        self.StatusBar = StatusBar

        # Spinner
        self.Spinner = Spinner

        # 常量
        self.HAS_RICH = HAS_RICH
        self.HEX_AVOCADO = HEX_AVOCADO
        self.HEX_AVOCADO_BRIGHT = HEX_AVOCADO_BRIGHT
        self.HEX_AVOCADO_DIM = HEX_AVOCADO_DIM
        self.RGB_AVOCADO = RGB_AVOCADO
        self.RGB_AVOCADO_BRIGHT = RGB_AVOCADO_BRIGHT
        self.RGB_AVOCADO_DIM = RGB_AVOCADO_DIM

    def print_info(self, text, prefix=True):
        print_info(text, prefix)

    def print_success(self, text, prefix=True):
        print_success(text, prefix)

    def print_warning(self, text, prefix=True):
        print_warning(text, prefix)

    def print_error(self, text, prefix=True):
        print_error(text, prefix)

    def print_header(self, text, border=False):
        print_header(text, border)

    def print_divider(self, char="─", width=None):
        print_divider(char, width)

    def print_step(self, step, total, title):
        print_step(step, total, title)

    def print_substep(self, text, indent=1):
        print_substep(text, indent)

    def print_end_step(self):
        print_end_step()

    def print_box(self, content, title=None, style="double", width=None):
        print_box(content, title, style, width)

    def print_table_row(self, items, widths=None):
        print_table_row(items, widths)

    def print_spinner(self, message="Processing"):
        return print_spinner(message)

    def prompt(self, question, default=None, password=False, required=False):
        return prompt(question, default, password, required)

    def prompt_yes_no(self, question, default=True):
        return prompt_yes_no(question, default)

    def prompt_choice(self, question, options, default=0):
        return prompt_choice(question, options, default)

    def print_banner(self, model=None, tools_count=None, skills_count=None, version="0.0.1"):
        print_banner(model, tools_count, skills_count, version)

    def print_banner_simple(self):
        print_banner_simple()

    def print_prompt(self, message=None):
        return print_prompt(message)

    def print_header_text(self, text):
        print_header_text(text)

    def print_menu(self, options, selected=None):
        print_menu(options, selected)

    def print_config_item(self, key, value):
        print_config_item(key, value)

    def print_list(self, items, title=None, icon="•"):
        print_list(items, title, icon)

    def print_agent_response(self, response, confidence=None):
        print_agent_response(response, confidence)

    def print_status_bar(self):
        print_status_bar()

    def print_user_input(self, prompt=None):
        print_user_input(prompt)

    def print_provider_list(self, providers):
        print_provider_list(providers)

    def print_setup_complete(self):
        print_setup_complete()

    def print_rich_table(self, data, headers=None, title=None, style="accent"):
        print_rich_table(data, headers, title, style)

    def print_rich_panel(self, content, title=None, style="accent", width=None):
        print_rich_panel(content, title, style, width)

    def print_rich_progress(self, items, title=None, style="accent"):
        print_rich_progress(items, title, style)

    def print_rich_success(self, message):
        print_rich_success(message)

    def print_rich_error(self, message):
        print_rich_error(message)

    def print_rich_warning(self, message):
        print_rich_warning(message)

    def print_rich_info(self, message):
        print_rich_info(message)


# 全局 UI 实例
ui = _UIFacade()
