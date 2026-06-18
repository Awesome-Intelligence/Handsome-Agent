#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Color definitions and utilities for Handsome Agent CLI.

🚪 Access - 💬 CLI - 颜色系统

参考 Hermes 的 colors.py 设计，支持：
- 高雅紫主题色
- ANSI 颜色码
- Rich 格式颜色 (rgb, hex)
- 皮肤/主题系统
"""

import os
import sys
from typing import Optional

# ============================================================================
# Color Detection
# ============================================================================

def should_use_color() -> bool:
    """Return True when colored output is appropriate.

    Respects:
    - NO_COLOR environment variable (https://no-color.org/)
    - TERM=dumb
    - Non-TTY stdout
    """
    if os.environ.get("NO_COLOR") is not None:
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    if not sys.stdout.isatty():
        return False
    return True


def supports_ansi() -> bool:
    """Check if terminal supports ANSI escape codes."""
    if os.environ.get("WT_SESSION"):  # Windows Terminal
        return True
    if os.environ.get("TERM"):
        return True
    # Check Windows Console Mode
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            STD_OUTPUT_HANDLE = -11
            handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
            mode = ctypes.c_ulong()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
                return bool(mode.value & ENABLE_VIRTUAL_TERMINAL_PROCESSING)
        except Exception:
            pass
    return False


def enable_ansi_support():
    """Enable ANSI escape sequence support on Windows."""
    if sys.platform != "win32":
        return

    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32

        for handle_id in (-11, -12):  # stdout, stderr
            handle = kernel32.GetStdHandle(handle_id)
            mode = ctypes.c_ulong()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
                kernel32.SetConsoleMode(handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING)
    except Exception:
        pass


# ============================================================================
# ANSI Color Constants
# ============================================================================

class Colors:
    """ANSI color codes - 高雅紫主题."""

    RESET = "\033[0m"

    # Style modifiers
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    REVERSE = "\033[7m"

    # Basic colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright colors
    BLACK_BRIGHT = "\033[90m"
    RED_BRIGHT = "\033[91m"
    GREEN_BRIGHT = "\033[92m"
    YELLOW_BRIGHT = "\033[93m"
    BLUE_BRIGHT = "\033[94m"
    MAGENTA_BRIGHT = "\033[95m"
    CYAN_BRIGHT = "\033[96m"
    WHITE_BRIGHT = "\033[97m"

    # Gray (256-color mode)
    GRAY = "\033[38;5;245m"
    GRAY_DIM = "\033[38;5;245m\033[2m"

    # 高雅紫主题色 (Elegant Purple)
    # RGB: 177, 128, 215 / #B180D7
    AVOCADO = "\033[38;2;177;128;215m"
    AVOCADO_BRIGHT = "\033[38;2;201;160;224m"
    AVOCADO_DIM = "\033[38;2;139;92;172m"
    AVOCADO_DARK = "\033[38;2;107;78;168m"

    # Background colors
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"
    BG_AVOCADO = "\033[48;2;177;128;215m"


# ============================================================================
# Rich-compatible Color Strings
# ============================================================================

# Hex colors for rich library
HEX_AVOCADO = "#8B9A46"
HEX_AVOCADO_BRIGHT = "#A0B45A"
HEX_AVOCADO_DIM = "#647030"
HEX_GOLD = "#FFD700"

# RGB colors for rich library
RGB_AVOCADO = "rgb(139,154,70)"
RGB_AVOCADO_BRIGHT = "rgb(160,180,90)"
RGB_AVOCADO_DIM = "rgb(100,120,50)"
RGB_GOLD = "rgb(255,215,0)"


# ============================================================================
# Color Helper Functions
# ============================================================================

def color(text: str, *codes: str) -> str:
    """Apply color codes to text (only when color output is appropriate)."""
    if not should_use_color():
        return text
    return "".join(codes) + text + Colors.RESET


def colorize(text: str, fg: Optional[str] = None, bg: Optional[str] = None,
             bold: bool = False, dim: bool = False) -> str:
    """Apply color and style to text.

    Args:
        text: Text to colorize
        fg: Foreground color (ANSI code or hex)
        bg: Background color (ANSI code or hex)
        bold: Apply bold style
        dim: Apply dim style
    """
    parts = []

    if bold:
        parts.append(Colors.BOLD)
    if dim:
        parts.append(Colors.DIM)

    if fg:
        parts.append(fg)

    result = "".join(parts) + text + Colors.RESET
    return result


def strip_color(text: str) -> str:
    """Remove ANSI color codes from text."""
    import re
    ansi_pattern = re.compile(r'\x1b\[[0-9;]*m')
    return ansi_pattern.sub('', text)


# ============================================================================
# Theme Colors (for consistent UI styling)
# ============================================================================

class Theme:
    """Theme colors - 高雅紫主题的统一配色."""

    # Border colors
    BORDER = Colors.AVOCADO
    BORDER_DIM = Colors.GRAY
    BORDER_LIGHT = Colors.AVOCADO_DIM

    # Primary colors
    PRIMARY = Colors.AVOCADO_BRIGHT
    PRIMARY_BOLD = f"{Colors.BOLD}{Colors.AVOCADO_BRIGHT}"
    PRIMARY_DIM = Colors.AVOCADO_DIM

    # Secondary colors
    SECONDARY = Colors.WHITE
    SECONDARY_DIM = Colors.GRAY
    SECONDARY_MUTED = Colors.GRAY

    # Accent colors
    ACCENT = Colors.AVOCADO_BRIGHT
    ACCENT_DIM = Colors.AVOCADO

    # Status colors
    SUCCESS = Colors.GREEN
    SUCCESS_BRIGHT = Colors.GREEN_BRIGHT
    ERROR = Colors.RED
    ERROR_BRIGHT = Colors.RED_BRIGHT
    WARNING = Colors.YELLOW
    WARNING_BRIGHT = Colors.YELLOW_BRIGHT
    INFO = Colors.BLUE
    INFO_BRIGHT = Colors.CYAN


# ============================================================================
# Skin-aware Colors (for theming support)
# ============================================================================

def get_skin_color(key: str, fallback: str) -> str:
    """Get color from active skin, or return fallback.

    Args:
        key: Color key (e.g., 'banner_accent', 'banner_text')
        fallback: Fallback color if skin not available
    """
    try:
        from cli.skin_engine import get_active_skin
        return get_active_skin().get_color(key, fallback)
    except ImportError:
        return fallback


def get_skin_branding(key: str, fallback: str) -> str:
    """Get branding string from active skin, or return fallback."""
    try:
        from cli.skin_engine import get_active_skin
        return get_active_skin().get_branding(key, fallback)
    except ImportError:
        return fallback


# ============================================================================
# Convenience Functions
# ============================================================================

def success(text: str) -> str:
    """Return text in success color (green)."""
    return f"{Colors.GREEN}{text}{Colors.RESET}"


def error(text: str) -> str:
    """Return text in error color (red)."""
    return f"{Colors.RED}{text}{Colors.RESET}"


def warning(text: str) -> str:
    """Return text in warning color (yellow)."""
    return f"{Colors.YELLOW}{text}{Colors.RESET}"


def info(text: str) -> str:
    """Return text in info color (blue)."""
    return f"{Colors.BLUE}{text}{Colors.RESET}"


def accent(text: str) -> str:
    """Return text in accent color (avocado)."""
    return f"{Colors.AVOCADO_BRIGHT}{text}{Colors.RESET}"


def dim(text: str) -> str:
    """Return text in dim style."""
    return f"{Colors.DIM}{text}{Colors.RESET}"


def bold(text: str) -> str:
    """Return text in bold style."""
    return f"{Colors.BOLD}{text}{Colors.RESET}"


# ============================================================================
# Rich Console Setup
# ============================================================================

def get_rich_console():
    """Get a rich Console instance for enhanced output."""
    try:
        from rich.console import Console
        return Console()
    except ImportError:
        return None


# ============================================================================
# Terminal Width Helpers
# ============================================================================

def get_terminal_width() -> int:
    """Get current terminal width."""
    try:
        import shutil
        return shutil.get_terminal_size().columns
    except Exception:
        return 80


def get_terminal_height() -> int:
    """Get current terminal height."""
    try:
        import shutil
        return shutil.get_terminal_size().lines
    except Exception:
        return 24