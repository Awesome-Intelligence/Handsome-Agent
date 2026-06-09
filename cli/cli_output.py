#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI output helpers for Handsome Agent.

🚪 Access - 💬 CLI - 输出函数

提取了 print_info/success/warning/error 等通用输出函数，
统一管理 CLI 的格式化输出。

参考 Hermes 的 cli_output.py 设计。
"""

import getpass
import sys
from typing import Optional

from cli.colors import Colors, color, should_use_color


# ============================================================================
# Print Helpers
# ============================================================================

def print_info(text: str, prefix: bool = True) -> None:
    """Print a dim informational message.

    Args:
        text: Message text
        prefix: Whether to add ℹ prefix
    """
    if prefix:
        print(color(f"  ℹ {text}", Colors.DIM))
    else:
        print(color(f"  {text}", Colors.DIM))


def print_success(text: str, prefix: bool = True) -> None:
    """Print a green success message with ✓ prefix.

    Args:
        text: Message text
        prefix: Whether to add ✓ prefix
    """
    if prefix:
        print(color(f"  ✓ {text}", Colors.GREEN))
    else:
        print(color(f"  {text}", Colors.GREEN))


def print_warning(text: str, prefix: bool = True) -> None:
    """Print a yellow warning message with ⚠ prefix.

    Args:
        text: Message text
        prefix: Whether to add ⚠ prefix
    """
    if prefix:
        print(color(f"  ⚠ {text}", Colors.YELLOW))
    else:
        print(color(f"  {text}", Colors.YELLOW))


def print_error(text: str, prefix: bool = True) -> None:
    """Print a red error message with ✗ prefix.

    Args:
        text: Message text
        prefix: Whether to add ✗ prefix
    """
    if prefix:
        print(color(f"  ✗ {text}", Colors.RED))
    else:
        print(color(f"  {text}", Colors.RED))


def print_header(text: str, border: bool = False) -> None:
    """Print a bold header.

    Args:
        text: Header text
        border: Whether to draw border around header
    """
    if border:
        print()
        print(color(f"  ╭{'─' * 50}╮", Colors.AVOCADO_BRIGHT))
        print(color(f"  │ {text.center(48)} │", Colors.AVOCADO_BRIGHT))
        print(color(f"  ╰{'─' * 50}╯", Colors.AVOCADO_BRIGHT))
        print()
    else:
        print()
        print(color(f"  ◆ {text}", Colors.AVOCADO_BRIGHT))
        print()


def print_debug(text: str) -> None:
    """Print a debug message (only when DEBUG is enabled)."""
    if _debug_enabled():
        print(color(f"  [DEBUG] {text}", Colors.DIM))


def print_divider(char: str = "─", width: Optional[int] = None) -> None:
    """Print a divider line.

    Args:
        char: Character to use for divider
        width: Width of divider (defaults to terminal width)
    """
    if width is None:
        try:
            import shutil
            width = shutil.get_terminal_size().columns - 4
        except Exception:
            width = 60

    print(color(f"  {char * width}", Colors.AVOCADO_DIM))


# ============================================================================
# Input Prompts
# ============================================================================

def prompt(
    question: str,
    default: Optional[str] = None,
    password: bool = False,
    required: bool = False,
) -> str:
    """Prompt the user for input with optional default and password masking.

    Args:
        question: Question text
        default: Default value if user presses Enter
        password: Whether to mask input (for API keys, etc.)
        required: Whether the field is required

    Returns:
        User's input (stripped), or *default* if empty and not required
    """
    suffix = f" [{default}]" if default else ""
    required_hint = " (必填)" if required else ""
    display = color(f"  {question}{suffix}{required_hint}: ", Colors.YELLOW)

    try:
        if password:
            value = getpass.getpass(display)
        else:
            value = input(display)

        value = value.strip()

        if not value and required:
            print_error("此项为必填项，请输入值")
            return prompt(question, default, password, required)

        return value if value else (default or "")

    except (KeyboardInterrupt, EOFError):
        print()
        return ""


def prompt_yes_no(question: str, default: bool = True) -> bool:
    """Prompt for a yes/no answer.

    Args:
        question: Question text
        default: Default value if user presses Enter

    Returns:
        True for yes, False for no
    """
    hint = "Y/n" if default else "y/N"
    answer = prompt(f"{question} ({hint})")

    if not answer:
        return default

    return answer.lower().startswith("y")


def prompt_choice(question: str, options: list, default: int = 0) -> int:
    """Prompt for a numbered choice.

    Args:
        question: Question text
        options: List of option strings
        default: Default option index

    Returns:
        Selected index, or default on empty input
    """
    print()
    print(color(f"  {question}", Colors.AVOCADO_BRIGHT))
    print()

    for i, opt in enumerate(options):
        marker = "●" if i == default else "○"
        prefix = f"  {marker} {i + 1}. "
        if i == default:
            print(color(prefix, Colors.GREEN) + color(opt, Colors.GREEN_BRIGHT))
        else:
            print(f"  {marker} {i + 1}. {opt}")

    print()
    print(color(f"  Enter for default ({default + 1})", Colors.DIM))

    while True:
        try:
            value = input(color("  Select: ", Colors.YELLOW)).strip()

            if not value:
                return default

            idx = int(value) - 1
            if 0 <= idx < len(options):
                return idx

            print_error(f"Please enter a number between 1 and {len(options)}")
        except ValueError:
            print_error("Please enter a number")
        except (KeyboardInterrupt, EOFError):
            print()
            return default


# ============================================================================
# Progress & Status
# ============================================================================

def print_step(step: int, total: int, title: str) -> None:
    """Print a step indicator.

    Args:
        step: Current step number
        total: Total number of steps
        title: Step title
    """
    print()
    print(color(f"  ├ ", Colors.AVOCADO) + color(f"[{step}/{total}]", Colors.AVOCADO_BRIGHT),
          end=" ")
    print(color(title, Colors.AVOCADO))
    print(color("  │", Colors.AVOCADO))


def print_substep(text: str, indent: int = 1) -> None:
    """Print a substep with indentation.

    Args:
        text: Substep text
        indent: Indentation level (1-4)
    """
    indent_str = "  " * indent
    print(color(f"  │{indent_str}", Colors.AVOCADO), end=" ")
    print(color(text, Theme.SECONDARY_DIM))


def print_end_step() -> None:
    """Print end of step section."""
    print(color("  └" + "─" * 50, Colors.AVOCADO_DIM))


def print_spinner(message: str = "Processing") -> "Spinner":
    """Create and start a spinner.

    Args:
        message: Spinner message

    Returns:
        Spinner instance (call .stop() when done)
    """
    return Spinner(message)


# ============================================================================
# Spinner Class
# ============================================================================

class Spinner:
    """Loading spinner for long operations."""

    def __init__(self, message: str = "Processing"):
        self.message = message
        self.spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.running = False
        self.last_update = 0

    def start(self) -> None:
        """Start the spinner."""
        self.running = True
        self.last_update = _get_time()
        print(color(f"  ⠋ {self.message}...", Colors.AVOCADO_BRIGHT), end="\r", flush=True)

    def update(self) -> None:
        """Update spinner animation."""
        if not self.running:
            return

        now = _get_time()
        if now - self.last_update > 0.1:
            idx = int((now * 10) % len(self.spinner_chars))
            print(color(f"  {self.spinner_chars[idx]} {self.message}...", Colors.AVOCADO_BRIGHT),
                  end="\r", flush=True)
            self.last_update = now

    def stop(self, success: bool = True, message: Optional[str] = None) -> None:
        """Stop the spinner and show completion.

        Args:
            success: Whether the operation succeeded
            message: Optional custom message
        """
        self.running = False

        # Clear the line
        print(" " * 60, end="\r")

        if message:
            if success:
                print_success(message, prefix=False)
            else:
                print_error(message, prefix=False)
        elif success:
            print_success("Done", prefix=False)
        else:
            print_error("Failed", prefix=False)


# ============================================================================
# Box Drawing Helpers
# ============================================================================

def print_box(content: str, title: Optional[str] = None,
              style: str = "double", width: Optional[int] = None) -> None:
    """Print content in a box.

    Args:
        content: Content text
        title: Optional box title
        style: Box style ('single', 'double', 'rounded')
        width: Box width (defaults to content width + 4)
    """
    if width is None:
        width = len(content.split('\n')[0]) + 4
        width = max(width, 40)

    lines = content.split('\n')

    if style == "double":
        top = "╔"
        bottom = "╚"
        side = "║"
        tl = "╗"
        tr = "╝"
    elif style == "rounded":
        top = "╭"
        bottom = "╰"
        side = "│"
        tl = "╮"
        tr = "╯"
    else:  # single
        top = "┌"
        bottom = "└"
        side = "│"
        tl = "┐"
        tr = "┘"

    print()
    print(color(f"  {top}{'─' * (width - 2)}{tl}", Colors.AVOCADO))

    if title:
        title_padding = (width - 4 - len(title)) // 2
        print(color(f"  {side}", Colors.AVOCADO) + " " * title_padding +
              color(title, Colors.AVOCADO_BRIGHT) + " " * (width - 4 - title_padding - len(title)) +
              color(f" {side}", Colors.AVOCADO))

        print(color(f"  {side}" + " " * (width - 2) + f" {side}", Colors.AVOCADO))

    for line in lines:
        line = line.strip()
        if line:
            print(color(f"  {side}", Colors.AVOCADO) + f" {line}" +
                  " " * (width - 3 - len(line)) + color(f" {side}", Colors.AVOCADO))

    print(color(f"  {bottom}{'─' * (width - 2)}{tr}", Colors.AVOCADO))
    print()


def print_table_row(items: list, widths: Optional[list] = None) -> None:
    """Print a table row.

    Args:
        items: List of cell values
        widths: Optional list of cell widths
    """
    if widths is None:
        widths = [max(len(str(item)) for item in items) + 2] * len(items)

    print("  ", end="")
    for item, width in zip(items, widths):
        print(str(item).ljust(width), end="")
    print()


# ============================================================================
# Debug Helpers
# ============================================================================

def _debug_enabled() -> bool:
    """Check if debug mode is enabled."""
    import os
    return os.environ.get("DEBUG", "").lower() in ("1", "true", "yes")


def _get_time() -> float:
    """Get current time (for spinner)."""
    import time
    return time.time()


# ============================================================================
# Rich Console Integration
# ============================================================================

def print_rich_table(data: list, headers: Optional[list] = None,
                     title: Optional[str] = None, style: str = "accent") -> None:
    """Print data as a rich table.

    Args:
        data: List of rows
        headers: Optional header row
        title: Table title
        style: Color style ('accent', 'success', 'warning', 'error')
    """
    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title=title, show_header=headers is not None)

        if headers:
            for header in headers:
                table.add_column(header)

        for row in data:
            table.add_row(*[str(cell) for cell in row])

        console.print(table)
    except ImportError:
        # Fallback to simple text table
        if headers:
            print_table_row(headers)
        for row in data:
            print_table_row(row)


# ============================================================================
# Streaming Output
# ============================================================================

def print_stream_start(prefix: str = "🤖") -> None:
    """Start streaming output with prefix.

    Args:
        prefix: Streaming indicator prefix (default: 🤖)
    """
    print()
    print(color(f"  {prefix} ", Colors.AVOCADO_BRIGHT), end="", flush=True)


def print_stream_chunk(chunk: str, flush: bool = True) -> None:
    """Print a streaming chunk without newline.

    Args:
        chunk: Content chunk to print
        flush: Whether to flush immediately
    """
    print(chunk, end="", flush=flush)


def print_stream_end() -> None:
    """End streaming output with newline."""
    print()  # Newline after streaming content


class StreamingPrinter:
    """Streaming printer for progressive output.

    Usage:
        printer = StreamingPrinter(prefix="🤖")
        await printer.start()
        for chunk in stream:
            printer.print(chunk)
        await printer.finish()
    """

    def __init__(self, prefix: str = "🤖", color_code: str = Colors.AVOCADO_BRIGHT):
        """Initialize streaming printer.

        Args:
            prefix: Streaming indicator prefix
            color_code: Color code for the prefix
        """
        self.prefix = prefix
        self.color_code = color_code
        self.started = False
        self._buffer = ""

    def start(self) -> None:
        """Start streaming output."""
        print()
        print(color(f"  {self.prefix} ", self.color_code), end="", flush=True)
        self.started = True

    def print(self, chunk: str, flush: bool = True) -> None:
        """Print a chunk to streaming output.

        Args:
            chunk: Content chunk to print
            flush: Whether to flush immediately
        """
        if not self.started:
            self.start()
        print(chunk, end="", flush=flush)
        self._buffer += chunk

    def finish(self, newline: bool = True) -> str:
        """Finish streaming output.

        Args:
            newline: Whether to add newline at end

        Returns:
            Complete streamed content
        """
        if newline and self.started:
            print(flush=True)
        self.started = False
        return self._buffer

    def clear(self) -> None:
        """Clear the streamed content buffer."""
        self._buffer = ""

    @property
    def content(self) -> str:
        """Get current buffered content."""
        return self._buffer


# ============================================================================
# Export for backward compatibility
# ============================================================================

# Re-export from colors module for convenience
from cli.colors import (
    Colors,
    Theme,
    should_use_color,
    get_terminal_width,
    get_terminal_height,
    strip_color,
)