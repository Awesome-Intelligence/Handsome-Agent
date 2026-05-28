#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Custom TUI Module - Geek Green themed terminal output.
Inspired by Hermes Agent's elegant design principles.
"""

import sys
import os
import time
import shutil
import re
from typing import Optional, List, Dict, Any


class Colors:
    """Unified color scheme based on Geek Green theme."""

    RESET = "\033[0m"

    GREEN = "\033[38;2;34;197;94m"
    GREEN_BRIGHT = "\033[38;2;48;211;99m"
    GREEN_DIM = "\033[38;2;22;130;62m"

    GRAY = "\033[90m"
    GRAY_BRIGHT = "\033[38;2;229;231;235m"
    GRAY_DIM = "\033[38;2;71;85;105m"

    RED = "\033[38;2;239;68;68m"
    RED_BRIGHT = "\033[38;2;248;113;113m"
    YELLOW = "\033[38;2;234;179;8m"
    YELLOW_BRIGHT = "\033[38;2;250;204;21m"
    BLUE = "\033[38;2;59;130;246m"
    CYAN = "\033[38;2;6;182;212m"

    BG_GREEN = "\033[48;2;34;197;94m"
    BG_GRAY = "\033[48;2;15;23;42m"

    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    REVERSE = "\033[7m"


class Theme:
    """Unified theme colors - Main color is Geek Green, inspired by Hermes."""

    BORDER = Colors.GREEN
    BORDER_DIM = Colors.GRAY_DIM
    BORDER_LIGHT = Colors.GREEN_DIM

    PRIMARY = Colors.GREEN_BRIGHT
    PRIMARY_BOLD = f"{Colors.BOLD}{Colors.GREEN_BRIGHT}"
    PRIMARY_DIM = Colors.GREEN_DIM

    SECONDARY = Colors.GRAY_BRIGHT
    SECONDARY_DIM = Colors.GRAY
    SECONDARY_MUTED = Colors.GRAY_DIM

    ACCENT = Colors.GREEN_BRIGHT
    ACCENT_DIM = Colors.GREEN

    SUCCESS = Colors.GREEN
    SUCCESS_BRIGHT = Colors.GREEN_BRIGHT
    ERROR = Colors.RED
    ERROR_BRIGHT = Colors.RED_BRIGHT
    WARNING = Colors.YELLOW
    WARNING_BRIGHT = Colors.YELLOW_BRIGHT
    INFO = Colors.BLUE
    INFO_BRIGHT = Colors.CYAN


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


status_bar = StatusBar()


class Spinner:
    """Loading spinner for long operations."""

    def __init__(self, message: str = "Processing"):
        self.message = message
        self.spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.running = False
        self.last_update = 0

    def start(self):
        """Start the spinner."""
        self.running = True
        self.last_update = time.time()
        print(f"{Theme.ACCENT}⠋{Colors.RESET} {self.message}...", end="\r", flush=True)

    def update(self):
        """Update spinner animation."""
        if not self.running:
            return
        now = time.time()
        if now - self.last_update > 0.1:
            idx = int((now * 10) % len(self.spinner_chars))
            print(f"{Theme.ACCENT}{self.spinner_chars[idx]}{Colors.RESET} {self.message}...", end="\r", flush=True)
            self.last_update = now

    def stop(self, success: bool = True):
        """Stop the spinner and show completion."""
        self.running = False
        if success:
            print(f"{Theme.SUCCESS}✓{Colors.RESET} {self.message}")
        else:
            print(f"{Theme.ERROR}✗{Colors.RESET} {self.message}")


def get_terminal_width() -> int:
    """Get terminal width with fallback."""
    try:
        return shutil.get_terminal_size().columns
    except:
        return 80


def strip_ansi(text: str) -> str:
    """Remove ANSI codes from text."""
    ansi_pattern = re.compile(r'\x1b\[[0-9;]*m')
    return ansi_pattern.sub('', text)


def supports_color() -> bool:
    """Check if terminal supports colors."""
    return sys.stdout.isatty()


def print_top_border(width: int = 0):
    """Print top border with corners."""
    width = width or get_terminal_width()
    print(f"{Theme.BORDER}╭{'─' * (width - 2)}╮{Colors.RESET}")


def print_bottom_border(width: int = 0):
    """Print bottom border with corners."""
    width = width or get_terminal_width()
    print(f"{Theme.BORDER}╰{'─' * (width - 2)}╯{Colors.RESET}")


def print_divider(char: str = "─", width: int = 0):
    """Print divider line."""
    width = width or get_terminal_width()
    print(f"{Theme.BORDER_LIGHT}{char * width}{Colors.RESET}")


def print_header(text: str, subtitle: str = None, width: int = 0):
    """Print header with border, inspired by Hermes."""
    width = width or get_terminal_width()
    print()
    print_top_border(width)
    print_border_side(f"{Theme.PRIMARY_BOLD}{text}{Colors.RESET}", width)
    if subtitle:
        print_border_side(f"{Theme.SECONDARY_DIM}{subtitle}{Colors.RESET}", width)
    print_bottom_border(width)
    print()


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


def print_success(message: str):
    """Print success message with icon."""
    print(f"{Theme.SUCCESS}✓{Colors.RESET} {message}")


def print_error(message: str):
    """Print error message with icon."""
    print(f"{Theme.ERROR}✗{Colors.RESET} {message}")


def print_warning(message: str):
    """Print warning message with icon."""
    print(f"{Theme.WARNING}⚠{Colors.RESET} {message}")


def print_info(message: str):
    """Print info message with icon."""
    print(f"{Theme.INFO}ℹ{Colors.RESET} {message}")


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


def print_step(step: int, total: int, title: str):
    """Print step indicator."""
    total_str = str(total)
    step_str = str(step).rjust(len(total_str))
    print()
    print(f"{Theme.BORDER}├{Colors.RESET} {Theme.PRIMARY_BOLD}[{step_str}/{total_str}]{Colors.RESET} {Theme.PRIMARY}{title}{Colors.RESET}")
    print(f"{Theme.BORDER}│{Colors.RESET}")


def print_substep(text: str, indent: int = 1):
    """Print substep with indentation."""
    indent_str = "  " * indent
    print(f"{Theme.BORDER}│{Colors.RESET} {indent_str}{Theme.SECONDARY}{text}{Colors.RESET}")


def print_end_step():
    """Print end of step section."""
    print(f"{Theme.BORDER}└{'─' * 50}{Colors.RESET}")


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
    print()
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


def print_banner():
    """Print welcome banner inspired by Hermes Agent."""
    if not supports_color():
        print_header("Handsome Agent", "Welcome!")
        return

    width = get_terminal_width()
    max_width = min(width, 80)

    wow_lines = [
        " ░█░█░█▀█░█▀█░█▀▄░█▀▀░█▀█░█▄█░█▀▀ ",
        " ░█▀█░█▀█░█░█░█░█░▀▀█░█░█░█░█░█▀▀ ",
        " ░▀░▀░▀░▀░▀░▀░▀▀░░▀▀▀░▀▀▀░▀░▀░▀▀▀ ",
    ]

    print()
    print(f"{Theme.BORDER}╭{'─' * (max_width - 2)}╮{Colors.RESET}")
    print(f"{Theme.BORDER}│{Colors.RESET}{' ' * (max_width - 2)}{Theme.BORDER}│{Colors.RESET}")

    for line in wow_lines:
        line_len = len(line.rstrip())
        padding = (max_width - 2 - line_len) // 2
        print(f"{Theme.BORDER}│{Colors.RESET}{' ' * padding}{Theme.PRIMARY_BOLD}{line}{Colors.RESET}{' ' * (max_width - 2 - padding - line_len)}{Theme.BORDER}│{Colors.RESET}")

    print(f"{Theme.BORDER}│{Colors.RESET}{' ' * (max_width - 2)}{Theme.BORDER}│{Colors.RESET}")

    subtitle = "Where code meets intelligence"
    sub_len = len(subtitle)
    sub_padding = (max_width - 2 - sub_len) // 2
    print(f"{Theme.BORDER}│{Colors.RESET}{' ' * sub_padding}{Theme.SECONDARY_DIM}{subtitle}{Colors.RESET}{' ' * (max_width - 2 - sub_padding - sub_len)}{Theme.BORDER}│{Colors.RESET}")

    print(f"{Theme.BORDER}│{Colors.RESET}{' ' * (max_width - 2)}{Theme.BORDER}│{Colors.RESET}")
    print(f"{Theme.BORDER}╰{'─' * (max_width - 2)}╯{Colors.RESET}")
    print()
    print(f"  {Theme.PRIMARY_BOLD}🚀 Handsome Agent v1.0.0{Colors.RESET}")
    print()