#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Curses TUI - 原生键盘导航的多选/单选组件

🚪 Access - 💬 CLI - Curses TUI

参考 Hermes Agent 的 curses_ui.py 设计，提供：
- curses_checklist: 多选列表
- curses_radiolist: 单选列表
- curses_single_select: 单选菜单

特性：
- 原生键盘导航 (↑↓ 选择，空格/回车确认)
- 自动降级到数字输入
- 牛油果绿主题色
"""

import sys
from typing import Callable, List, Optional, Set

# 尝试导入 rich，用于降级时的彩色输出
try:
    from rich.console import Console
    from rich.text import Text
    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False

# 导入本地 colors
try:
    from cli.colors import Colors, color
except ImportError:
    # 降级：定义基本颜色
    class Colors:
        GREEN = "\033[92m"
        YELLOW = "\033[93m"
        DIM = "\033[2m"
        RESET = "\033[0m"

    def color(text: str, c: str) -> str:
        return f"{c}{text}{Colors.RESET}"


def flush_stdin() -> None:
    """刷新 stdin 输入缓冲区。

    在 curses.wrapper() 返回后调用，清除残留的按键码。
    在非 TTY 或 Windows 上是空操作。
    """
    try:
        if not sys.stdin.isatty():
            return
        import termios
        termios.tcflush(sys.stdin, termios.TCIFLUSH)
    except Exception:
        pass


def curses_checklist(
    title: str,
    items: List[str],
    selected: Set[int],
    *,
    cancel_returns: Set[int] | None = None,
    status_fn: Optional[Callable[[Set[int]], str]] = None,
) -> Set[int]:
    """Curses 多选列表。返回选中的索引集合。

    Args:
        title: 标题
        items: 显示标签列表
        selected: 初始选中的索引集合
        cancel_returns: 取消时返回的值，默认为 selected
        status_fn: 可选的状态回调函数
    """
    if cancel_returns is None:
        cancel_returns = set(selected)

    # 非 TTY 时直接返回默认值
    if not sys.stdin.isatty():
        return cancel_returns

    try:
        import curses
        chosen = set(selected)
        result_holder: list = [None]

        def _draw(stdscr):
            curses.curs_set(0)
            if curses.has_colors():
                curses.start_color()
                curses.use_default_colors()
                # 牛油果绿主题
                curses.init_pair(1, 139, -1)  # 绿色 - 选中
                curses.init_pair(2, 160, -1)  # 亮绿 - 标题
                curses.init_pair(3, 245, -1)  # 灰色 - 提示

            cursor = 0
            scroll_offset = 0

            while True:
                stdscr.clear()
                max_y, max_x = stdscr.getmaxyx()

                footer_rows = 1 if status_fn else 0

                # 标题
                try:
                    hattr = curses.A_BOLD
                    if curses.has_colors():
                        hattr |= curses.color_pair(2)
                    stdscr.addnstr(0, 0, title, max_x - 1, hattr)
                    stdscr.addnstr(
                        1, 0,
                        "  ↑↓ 选择  空格 切换  Enter 确认  ESC 取消",
                        max_x - 1, curses.A_DIM,
                    )
                except curses.error:
                    pass

                # 可滚动列表
                visible_rows = max_y - 3 - footer_rows
                if cursor < scroll_offset:
                    scroll_offset = cursor
                elif cursor >= scroll_offset + visible_rows:
                    scroll_offset = cursor - visible_rows + 1

                for draw_i, i in enumerate(
                    range(scroll_offset, min(len(items), scroll_offset + visible_rows))
                ):
                    y = draw_i + 3
                    if y >= max_y - 1 - footer_rows:
                        break
                    check = "✓" if i in chosen else " "
                    arrow = "→" if i == cursor else " "
                    line = f" {arrow} [{check}] {items[i]}"
                    attr = curses.A_NORMAL
                    if i == cursor:
                        attr = curses.A_BOLD
                        if curses.has_colors():
                            attr |= curses.color_pair(1)
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
                            sattr = curses.A_DIM
                            if curses.has_colors():
                                sattr |= curses.color_pair(3)
                            stdscr.addnstr(max_y - 1, sx, status_text, max_x - sx - 1, sattr)
                    except curses.error:
                        pass

                stdscr.refresh()
                key = stdscr.getch()

                if key in {curses.KEY_UP, ord("k")}:
                    cursor = (cursor - 1) % len(items)
                elif key in {curses.KEY_DOWN, ord("j")}:
                    cursor = (cursor + 1) % len(items)
                elif key == ord(" "):
                    chosen.symmetric_difference_update({cursor})
                elif key in {curses.KEY_ENTER, 10, 13}:
                    result_holder[0] = set(chosen)
                    return
                elif key in {27, ord("q")}:
                    result_holder[0] = cancel_returns
                    return

        curses.wrapper(_draw)
        flush_stdin()
        return result_holder[0] if result_holder[0] is not None else cancel_returns

    except KeyboardInterrupt:
        return cancel_returns
    except Exception:
        return _numbered_fallback(title, items, selected, cancel_returns, status_fn)


def curses_radiolist(
    title: str,
    items: List[str],
    selected: int = 0,
    *,
    cancel_returns: int | None = None,
    description: str | None = None,
) -> int:
    """Curses 单选列表。返回选中的索引。

    Args:
        title: 标题
        items: 显示标签列表
        selected: 初始选中的索引
        cancel_returns: 取消时返回的值，默认为 selected
        description: 可选的描述文本
    """
    if cancel_returns is None:
        cancel_returns = selected

    if not sys.stdin.isatty():
        return cancel_returns

    desc_lines: list[str] = []
    if description:
        desc_lines = description.splitlines()

    try:
        import curses
        result_holder: list = [None]

        def _draw(stdscr):
            curses.curs_set(0)
            if curses.has_colors():
                curses.start_color()
                curses.use_default_colors()
                curses.init_pair(1, 139, -1)  # 绿色
                curses.init_pair(2, 160, -1)  # 亮绿
            cursor = selected
            scroll_offset = 0

            while True:
                stdscr.clear()
                max_y, max_x = stdscr.getmaxyx()

                row = 0

                # 标题
                try:
                    hattr = curses.A_BOLD
                    if curses.has_colors():
                        hattr |= curses.color_pair(2)
                    stdscr.addnstr(row, 0, title, max_x - 1, hattr)
                    row += 1

                    # 描述行
                    for dline in desc_lines:
                        if row >= max_y - 1:
                            break
                        stdscr.addnstr(row, 0, dline, max_x - 1, curses.A_NORMAL)
                        row += 1

                    stdscr.addnstr(
                        row, 0,
                        "  ↑↓ 选择  Enter/SPACE 确认  ESC 取消",
                        max_x - 1, curses.A_DIM,
                    )
                    row += 1
                except curses.error:
                    pass

                # 可滚动列表
                items_start = row + 1
                visible_rows = max_y - items_start - 1
                if cursor < scroll_offset:
                    scroll_offset = cursor
                elif cursor >= scroll_offset + visible_rows:
                    scroll_offset = cursor - visible_rows + 1

                for draw_i, i in enumerate(
                    range(scroll_offset, min(len(items), scroll_offset + visible_rows))
                ):
                    y = draw_i + items_start
                    if y >= max_y - 1:
                        break
                    radio = "●" if i == selected else "○"
                    arrow = "→" if i == cursor else " "
                    line = f" {arrow} ({radio}) {items[i]}"
                    attr = curses.A_NORMAL
                    if i == cursor:
                        attr = curses.A_BOLD
                        if curses.has_colors():
                            attr |= curses.color_pair(1)
                    try:
                        stdscr.addnstr(y, 0, line, max_x - 1, attr)
                    except curses.error:
                        pass

                stdscr.refresh()
                key = stdscr.getch()

                if key in {curses.KEY_UP, ord("k")}:
                    cursor = (cursor - 1) % len(items)
                elif key in {curses.KEY_DOWN, ord("j")}:
                    cursor = (cursor + 1) % len(items)
                elif key in {ord(" "), curses.KEY_ENTER, 10, 13}:
                    result_holder[0] = cursor
                    return
                elif key in {27, ord("q")}:
                    result_holder[0] = cancel_returns
                    return

        curses.wrapper(_draw)
        flush_stdin()
        return result_holder[0] if result_holder[0] is not None else cancel_returns

    except KeyboardInterrupt:
        return cancel_returns
    except Exception:
        return _radio_numbered_fallback(title, items, selected, cancel_returns)


def _radio_numbered_fallback(
    title: str,
    items: List[str],
    selected: int,
    cancel_returns: int,
) -> int:
    """文本模式数字输入降级方案（单选）。"""
    try:
        print(color(f"\n  {title}", Colors.YELLOW))
        print(color("  输入数字选择，Enter 确认。\n", Colors.DIM))

        for i, label in enumerate(items):
            marker = color("●", Colors.GREEN) if i == selected else "○"
            print(f"  {marker} {i + 1:>2}. {label}")
        print()
        val = input(color(f"  选择 [默认 {selected + 1}]: ", Colors.DIM)).strip()
        if not val:
            return selected
        idx = int(val) - 1
        if 0 <= idx < len(items):
            return idx
        return selected
    except (ValueError, KeyboardInterrupt, EOFError):
        return cancel_returns


def curses_single_select(
    title: str,
    items: List[str],
    default_index: int = 0,
    *,
    cancel_label: str = "取消",
) -> int | None:
    """Curses 单选菜单。返回选中的索引，取消返回 None。

    Args:
        title: 标题
        items: 显示标签列表
        default_index: 默认选中的索引
        cancel_label: 取消选项的标签
    """
    if not sys.stdin.isatty():
        return None

    try:
        import curses
        result_holder: list = [None]

        all_items = list(items) + [cancel_label]
        cancel_idx = len(items)

        def _draw(stdscr):
            curses.curs_set(0)
            if curses.has_colors():
                curses.start_color()
                curses.use_default_colors()
                curses.init_pair(1, 139, -1)  # 绿色
                curses.init_pair(2, 160, -1)  # 亮绿
            cursor = min(default_index, len(all_items) - 1)
            scroll_offset = 0

            while True:
                stdscr.clear()
                max_y, max_x = stdscr.getmaxyx()

                try:
                    hattr = curses.A_BOLD
                    if curses.has_colors():
                        hattr |= curses.color_pair(2)
                    stdscr.addnstr(0, 0, title, max_x - 1, hattr)
                    stdscr.addnstr(
                        1, 0,
                        "  ↑↓ 选择  Enter 确认  ESC/q 取消",
                        max_x - 1, curses.A_DIM,
                    )
                except curses.error:
                    pass

                visible_rows = max_y - 3
                if cursor < scroll_offset:
                    scroll_offset = cursor
                elif cursor >= scroll_offset + visible_rows:
                    scroll_offset = cursor - visible_rows + 1

                for draw_i, i in enumerate(
                    range(scroll_offset, min(len(all_items), scroll_offset + visible_rows))
                ):
                    y = draw_i + 3
                    if y >= max_y - 1:
                        break
                    arrow = "→" if i == cursor else " "
                    line = f" {arrow} {all_items[i]}"
                    attr = curses.A_NORMAL
                    if i == cursor:
                        attr = curses.A_BOLD
                        if curses.has_colors():
                            attr |= curses.color_pair(1)
                    try:
                        stdscr.addnstr(y, 0, line, max_x - 1, attr)
                    except curses.error:
                        pass

                stdscr.refresh()
                key = stdscr.getch()

                if key in {curses.KEY_UP, ord("k")}:
                    cursor = (cursor - 1) % len(all_items)
                elif key in {curses.KEY_DOWN, ord("j")}:
                    cursor = (cursor + 1) % len(all_items)
                elif key in {curses.KEY_ENTER, 10, 13}:
                    result_holder[0] = cursor
                    return
                elif key in {27, ord("q")}:
                    result_holder[0] = None
                    return

        curses.wrapper(_draw)
        flush_stdin()
        if result_holder[0] is not None and result_holder[0] >= cancel_idx:
            return None
        return result_holder[0]

    except KeyboardInterrupt:
        return None
    except Exception:
        all_items = list(items) + [cancel_label]
        cancel_idx = len(items)
        return _numbered_single_fallback(title, all_items, cancel_idx)


def _numbered_single_fallback(
    title: str,
    items: List[str],
    cancel_idx: int,
) -> int | None:
    """文本模式数字输入降级方案（单选菜单）。"""
    print(f"\n  {title}\n")
    for i, label in enumerate(items, 1):
        print(f"  {i}. {label}")
    print()
    try:
        val = input(f"  选择 [1-{len(items)}]: ").strip()
        if not val:
            return None
        idx = int(val) - 1
        if 0 <= idx < len(items) and idx < cancel_idx:
            return idx
        if idx == cancel_idx:
            return None
    except (ValueError, KeyboardInterrupt, EOFError):
        pass
    return None


def _numbered_fallback(
    title: str,
    items: List[str],
    selected: Set[int],
    cancel_returns: Set[int],
    status_fn: Optional[Callable[[Set[int]], str]] = None,
) -> Set[int]:
    """文本模式数字输入降级方案（多选）。"""
    chosen = set(selected)
    print(color(f"\n  {title}", Colors.YELLOW))
    print(color("  输入数字切换，Enter 确认。\n", Colors.DIM))

    while True:
        for i, label in enumerate(items):
            marker = color("[✓]", Colors.GREEN) if i in chosen else "[ ]"
            print(f"  {marker} {i + 1:>2}. {label}")
        if status_fn:
            status_text = status_fn(chosen)
            if status_text:
                print(color(f"\n  {status_text}", Colors.DIM))
        print()
        try:
            val = input(color("  切换 # (或 Enter 确认): ", Colors.DIM)).strip()
            if not val:
                break
            idx = int(val) - 1
            if 0 <= idx < len(items):
                chosen.symmetric_difference_update({idx})
        except (ValueError, KeyboardInterrupt, EOFError):
            return cancel_returns
        print()

    return chosen


# ============================================================================
# 便捷函数
# ============================================================================

def select_one(
    title: str,
    items: List[str],
    default: int = 0,
    cancel: int | None = None,
) -> int | None:
    """单选菜单的便捷函数。

    Args:
        title: 标题
        items: 选项列表
        default: 默认选中的索引
        cancel: 取消时返回的值（默认 None）

    Returns:
        选中的索引，或 cancel（如果取消）
    """
    result = curses_single_select(title, items, default, cancel_label="取消")
    return result if result is not None else cancel


def select_many(
    title: str,
    items: List[str],
    selected: set[int] | None = None,
) -> set[int] | None:
    """多选列表的便捷函数。

    Args:
        title: 标题
        items: 选项列表
        selected: 初始选中的索引集合

    Returns:
        选中的索引集合，或 None（如果取消）
    """
    result = curses_checklist(title, items, selected or set())
    return result if result is not None else None


if __name__ == "__main__":
    # 测试代码
    print("Testing curses_ui...")

    # 测试单选
    options = ["选项 A", "选项 B", "选项 C", "选项 D", "选项 E"]
    result = select_one("选择一个选项", options, default=0)
    print(f"单选结果: {result}")

    # 测试多选
    selected = {0, 2}
    result = curses_checklist("选择多个选项", options, selected)
    print(f"多选结果: {result}")