#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cross-platform curses-based UI components for Handsome Agent CLI.

Inspired by Hermes Agent's curses_ui.py design.
Provides curses multi-select with keyboard navigation, plus a
text-based numbered fallback for terminals without curses support.

🚪 Access - 💬 CLI - Curses UI 组件

跨平台支持：
- Windows (使用 curses 包或降级方案)
- macOS (原生 curses)
- Linux (原生 curses)
"""

import sys
import os
from typing import Callable, List, Optional, Set, Tuple, Union

# 平台检测
IS_WINDOWS = sys.platform == "win32"
IS_TTY = sys.stdin.isatty() if hasattr(sys.stdin, 'isatty') else False


def flush_stdin() -> None:
    """Flush any stray bytes from the stdin input buffer.

    Must be called after curses.wrapper() returns, before the next
    input()/getpass.getpass() call. curses.endwin() restores the terminal
    but does NOT drain the OS input buffer.

    On non-TTY stdin or when curses is not available, this is a no-op.
    """
    if not IS_TTY:
        return

    if IS_WINDOWS:
        # Windows: 使用 msvcrt 清空输入缓冲区
        try:
            import msvcrt
            while msvcrt.kbhit():
                msvcrt.getch()
        except ImportError:
            pass
    else:
        # Unix: 使用 termios
        try:
            import termios
            termios.tcflush(sys.stdin, termios.TCIFLUSH)
        except ImportError:
            pass


def has_curses() -> bool:
    """Check if curses library is available and working."""
    if IS_WINDOWS:
        try:
            import curses
            return True
        except ImportError:
            try:
                import _curses
                return True
            except ImportError:
                return False
    else:
        try:
            import curses
            return True
        except ImportError:
            return False


def curses_radiolist(
    question: str,
    choices: List[Union[str, Tuple[str, str]]],
    selected: int = 0,
    cancel_returns: int = -1,
    description: Optional[str] = None
) -> int:
    """Single-select menu using curses with arrow key navigation.

    Args:
        question: The question/title to display above the list.
        choices: List of choice strings or (value, label) tuples.
        selected: Index of the initially selected item.
        cancel_returns: Value to return on cancel/escape.
        description: Optional description text below the question.

    Returns:
        Index of selected choice, or cancel_returns on cancel.
    """
    if not has_curses():
        return _fallback_radiolist(question, choices, selected, cancel_returns, description)

    if not IS_TTY:
        return _fallback_radiolist(question, choices, selected, cancel_returns, description)

    try:
        import curses
    except ImportError:
        return _fallback_radiolist(question, choices, selected, cancel_returns, description)

    # 预处理 choices
    processed_choices = []
    for choice in choices:
        if isinstance(choice, tuple):
            processed_choices.append(choice)
        else:
            processed_choices.append((str(choice), str(choice)))

    # 预处理颜色
    try:
        curses.initscr()
        has_colors = curses.has_colors()
        curses.endwin()
    except Exception:
        has_colors = False

    def draw_menu(stdscr):
        curses.curs_set(0)

        if has_colors:
            try:
                curses.start_color()
                curses.use_default_colors()
                # 定义颜色对：1=绿色(选中), 2=黄色(高亮), 3=灰色(默认)
                curses.init_pair(1, curses.COLOR_GREEN, -1)
                curses.init_pair(2, curses.COLOR_YELLOW, -1)
                curses.init_pair(3, 8 if curses.COLORS > 8 else curses.COLOR_WHITE, -1)
                color_selected = curses.color_pair(1)
                color_highlight = curses.A_BOLD
                color_normal = curses.A_NORMAL
                color_dim = curses.color_pair(3)
            except Exception:
                color_selected = curses.A_REVERSE
                color_highlight = curses.A_BOLD
                color_normal = curses.A_NORMAL
                color_dim = curses.A_DIM
        else:
            color_selected = curses.A_REVERSE
            color_highlight = curses.A_BOLD
            color_normal = curses.A_NORMAL
            color_dim = curses.A_DIM

        cursor = selected
        scroll_offset = 0
        result_holder = [cancel_returns]

        while True:
            stdscr.clear()
            max_y, max_x = stdscr.getmaxyx()

            # 计算可用行数
            header_rows = 3  # 标题 + 问题 + 空行
            footer_rows = 2  # 底部提示行
            if description:
                header_rows += 1
            visible_rows = max_y - header_rows - footer_rows

            # 绘制标题
            try:
                title = " Handsome Agent Setup "
                stdscr.addnstr(0, 0, title.center(max_x - 2, '─'), max_x - 2, curses.A_BOLD)
            except curses.error:
                pass

            # 绘制问题
            try:
                display_question = question[:max_x - 6]
                stdscr.addnstr(1, 0, display_question, max_x - 2, curses.A_BOLD)
            except curses.error:
                pass

            # 绘制描述（如果有）
            if description:
                try:
                    display_desc = description[:max_x - 6]
                    stdscr.addnstr(2, 0, display_desc, max_x - 2, color_dim)
                except curses.error:
                    pass

            # 计算滚动
            if cursor < scroll_offset:
                scroll_offset = cursor
            elif cursor >= scroll_offset + visible_rows:
                scroll_offset = cursor - visible_rows + 1

            # 绘制选项
            start_y = header_rows
            for draw_i, i in enumerate(range(scroll_offset, min(len(processed_choices), scroll_offset + visible_rows))):
                y = start_y + draw_i
                if y >= max_y - footer_rows:
                    break

                value, label = processed_choices[i]
                arrow = "❯" if i == cursor else " "
                check = "●" if i == selected else "○"

                if i == cursor:
                    line = f" {arrow} [{check}] {label}"
                    attr = color_selected if has_colors else curses.A_REVERSE
                else:
                    line = f" {arrow}   {check} {label}"
                    attr = color_normal

                try:
                    stdscr.addnstr(y, 2, line, max_x - 4, attr)
                except curses.error:
                    pass

            # 绘制底部提示
            footer_y = max_y - footer_rows
            help_text = " ↑↓ navigate  ENTER select  ESC cancel "
            try:
                stdscr.addnstr(footer_y, 0, help_text.center(max_x - 2, '─'), max_x - 2, color_dim)
            except curses.error:
                pass

            stdscr.refresh()
            key = stdscr.getch()

            if key in (curses.KEY_UP, ord('k'), ord('K')):
                cursor = (cursor - 1) % len(processed_choices)
            elif key in (curses.KEY_DOWN, ord('j'), ord('J')):
                cursor = (cursor + 1) % len(processed_choices)
            elif key in (curses.KEY_ENTER, 10, 13):
                result_holder[0] = cursor
                return
            elif key in (curses.KEY_ESCAPE, 27):
                result_holder[0] = cancel_returns
                return
            elif key in (curses.KEY_HOME, ord('g')):
                cursor = 0
            elif key in (curses.KEY_END, ord('G')):
                cursor = len(processed_choices) - 1
            elif key == curses.KEY_PPAGE:  # Page Up
                cursor = max(0, cursor - visible_rows)
            elif key == curses.KEY_NPAGE:  # Page Down
                cursor = min(len(processed_choices) - 1, cursor + visible_rows)

    # 运行 curses
    try:
        result = curses.wrapper(draw_menu)
        # curses 会自动重置终端状态，不需要额外清屏
        # 避免清掉之前打印的内容（如 banner）
        flush_stdin()
        return result if result is not None else cancel_returns
    except Exception:
        flush_stdin()
        return _fallback_radiolist(question, choices, selected, cancel_returns, description)


def curses_checklist(
    title: str,
    items: List[str],
    selected: Set[int],
    cancel_returns: Optional[Set[int]] = None,
    status_fn: Optional[Callable[[Set[int]], str]] = None,
) -> Set[int]:
    """Curses multi-select checklist. Returns set of selected indices.

    Args:
        title: Header line displayed above the checklist.
        items: Display labels for each row.
        selected: Indices that start checked (pre-selected).
        cancel_returns: Returned on ESC/q. Defaults to original selected.
        status_fn: Optional callback f(chosen_indices) -> str for status bar.

    Returns:
        Set of selected indices.
    """
    if cancel_returns is None:
        cancel_returns = set(selected)

    if not has_curses():
        return _fallback_checklist(title, items, selected, cancel_returns)

    if not IS_TTY:
        return cancel_returns

    try:
        import curses
    except ImportError:
        return _fallback_checklist(title, items, selected, cancel_returns)

    def draw_checklist(stdscr):
        curses.curs_set(0)

        try:
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_GREEN, -1)
            curses.init_pair(2, curses.COLOR_YELLOW, -1)
            curses.init_pair(3, 8 if curses.COLORS > 8 else curses.COLOR_WHITE, -1)
            color_checked = curses.color_pair(1)
            color_highlight = curses.A_BOLD
            color_normal = curses.A_NORMAL
            color_dim = curses.color_pair(3)
        except Exception:
            color_checked = curses.A_BOLD
            color_highlight = curses.A_BOLD
            color_normal = curses.A_NORMAL
            color_dim = curses.A_DIM

        chosen = set(selected)
        cursor = 0
        scroll_offset = 0
        result_holder = [cancel_returns]

        while True:
            stdscr.clear()
            max_y, max_x = stdscr.getmaxyx()

            # 预留底部状态栏
            footer_rows = 1 if status_fn else 0
            visible_rows = max_y - 3 - footer_rows

            # 标题
            try:
                stdscr.addnstr(0, 0, title, max_x - 1, curses.A_BOLD)
                stdscr.addnstr(
                    1, 0,
                    "  ↑↓ navigate  SPACE toggle  ENTER confirm  ESC cancel",
                    max_x - 1, color_dim,
                )
            except curses.error:
                pass

            # 滚动
            if cursor < scroll_offset:
                scroll_offset = cursor
            elif cursor >= scroll_offset + visible_rows:
                scroll_offset = cursor - visible_rows + 1

            # 绘制选项
            for draw_i, i in enumerate(range(scroll_offset, min(len(items), scroll_offset + visible_rows))):
                y = draw_i + 3
                if y >= max_y - 1 - footer_rows:
                    break

                check = "✓" if i in chosen else " "
                arrow = "→" if i == cursor else " "
                line = f" {arrow} [{check}] {items[i]}"

                attr = color_normal
                if i == cursor:
                    attr = color_highlight

                try:
                    stdscr.addnstr(y, 0, line, max_x - 1, attr)
                except curses.error:
                    pass

            # 状态栏
            if status_fn:
                try:
                    status_text = status_fn(chosen)
                    if status_text:
                        sx = max(0, max_x - len(status_text) - 1)
                        stdscr.addnstr(max_y - 1, sx, status_text, max_x - sx - 1, color_dim)
                except curses.error:
                    pass

            stdscr.refresh()
            key = stdscr.getch()

            if key in (curses.KEY_UP, ord('k'), ord('K')):
                cursor = (cursor - 1) % len(items)
            elif key in (curses.KEY_DOWN, ord('j'), ord('J')):
                cursor = (cursor + 1) % len(items)
            elif key == ord(' '):
                chosen.symmetric_difference_update({cursor})
            elif key in (curses.KEY_ENTER, 10, 13):
                result_holder[0] = chosen
                return
            elif key in (curses.KEY_ESCAPE, 27, ord('q'), ord('Q')):
                result_holder[0] = cancel_returns
                return
            elif key == curses.KEY_HOME or ord('g') in (ord('g'),):
                cursor = 0
            elif key == curses.KEY_END or ord('G') in (ord('G'),):
                cursor = len(items) - 1

    try:
        result = curses.wrapper(draw_checklist)
        # curses 会自动重置终端状态，不需要额外清屏
        # 避免清掉之前打印的内容（如 banner）
        flush_stdin()
        return result if result is not None else cancel_returns
    except Exception:
        flush_stdin()
        return _fallback_checklist(title, items, selected, cancel_returns)


def _fallback_radiolist(
    question: str,
    choices: List[Union[str, Tuple[str, str]]],
    selected: int,
    cancel_returns: int,
    description: Optional[str] = None
) -> int:
    """Text-based fallback for radiolist when curses is not available.

    Args:
        question: The question/title to display.
        choices: List of choice strings or (value, label) tuples.
        selected: Index of the initially selected item.
        cancel_returns: Value to return on cancel.
        description: Optional description.

    Returns:
        Index of selected choice, or cancel_returns on cancel.
    """
    # 不打印重复的标题，curses 已经显示过了
    # print(f"─── {question} ───")

    if description:
        print(f"  {description}")
    print()

    # 预处理 choices
    processed_choices = []
    for i, choice in enumerate(choices):
        if isinstance(choice, tuple):
            processed_choices.append((i, choice[1]))
        else:
            processed_choices.append((i, str(choice)))

    # 显示选项
    for i, label in processed_choices:
        marker = "●" if i == selected else "○"
        if i == selected:
            print(f"  {marker} {i + 1}. {label} (default)")
        else:
            print(f"     {i + 1}. {label}")

    print()
    print("  ↑↓ change selection  ENTER confirm  q cancel")

    # 读取输入
    while True:
        try:
            choice = input("\nEnter selection (1-{}, or q): ".format(len(choices))).strip()

            if choice.lower() in ('q', 'quit', 'exit', 'cancel', ''):
                return cancel_returns

            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(choices):
                    return idx

            print(f"Invalid input. Please enter a number 1-{len(choices)} or 'q' to cancel.")
        except (KeyboardInterrupt, EOFError):
            print()
            return cancel_returns


def _fallback_checklist(
    title: str,
    items: List[str],
    selected: Set[int],
    cancel_returns: Set[int]
) -> Set[int]:
    """Text-based fallback for checklist when curses is not available.

    Args:
        title: Header line.
        items: Display labels for each row.
        selected: Indices that start checked.
        cancel_returns: Returned on cancel.

    Returns:
        Set of selected indices.
    """
    print()
    print(f"─── {title} ───")
    print("  SPACE toggle  ENTER confirm  q cancel")
    print()

    chosen = set(selected)

    for i, item in enumerate(items):
        check = "[*]" if i in chosen else "[ ]"
        print(f"  {check} {i + 1}. {item}")

    print()
    print("Toggle with numbers, confirm with ENTER, cancel with q")

    while True:
        try:
            choice = input("\nEnter toggle (1-{}) or confirm (ENTER): ".format(len(items))).strip()

            if choice.lower() in ('q', 'quit', 'exit', 'cancel'):
                return cancel_returns

            if choice == '':
                return chosen

            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(items):
                    chosen.symmetric_difference_update({idx})
                    # 重新显示
                    print()
                    for j, item in enumerate(items):
                        check = "[*]" if j in chosen else "[ ]"
                        print(f"  {check} {j + 1}. {item}")
                    print()
                    continue

            print(f"Invalid input. Enter a number 1-{len(items)} to toggle, or ENTER to confirm.")
        except (KeyboardInterrupt, EOFError):
            print()
            return cancel_returns


# ============================================================================
# Public API - 统一的单选/多选接口
# ============================================================================

def radio_select(
    question: str,
    options: List[Union[str, Tuple[str, str]]],
    default: int = 0,
    description: Optional[str] = None
) -> Optional[int]:
    """Single-select menu with curses fallback.

    Args:
        question: The question/title.
        options: List of strings or (value, label) tuples.
        default: Index of default selection.
        description: Optional description text.

    Returns:
        Index of selected option, or None if cancelled.
    """
    return curses_radiolist(question, options, selected=default, cancel_returns=-1, description=description)


def multi_select(
    title: str,
    items: List[str],
    selected: Set[int] = None,
    status_fn: Optional[Callable[[Set[int]], str]] = None
) -> Optional[Set[int]]:
    """Multi-select checklist with curses fallback.

    Args:
        title: Header line.
        items: Display labels for each row.
        selected: Indices that start checked.
        status_fn: Optional status bar callback.

    Returns:
        Set of selected indices, or None if cancelled.
    """
    if selected is None:
        selected = set()

    result = curses_checklist(
        title, items, selected,
        cancel_returns=None,
        status_fn=status_fn
    )
    return result if result is not None else None


# ============================================================================
# 测试入口
# ============================================================================

if __name__ == "__main__":
    print("Testing curses_ui module")
    print()

    # 测试单选
    options = [
        ("option1", "First Option - This is a longer option"),
        ("option2", "Second Option"),
        ("option3", "Third Option"),
        ("option4", "Fourth Option - Another longer text"),
        ("option5", "Fifth Option"),
    ]

    print("Curses available:", has_curses())
    print()

    result = radio_select(
        "Select your preference:",
        options,
        default=0,
        description="Choose one option from the list below"
    )

    if result is not None and result >= 0:
        print(f"\nSelected: {options[result]}")
    else:
        print("\nCancelled")