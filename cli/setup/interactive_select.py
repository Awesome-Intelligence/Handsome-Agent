#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交互式选择器 - 跨平台实现
"""

import sys
import os
import platform
from typing import List, Union, Optional, Tuple, Any


AVOCADO_GREEN = "\033[38;2;160;180;90m"
AVOCADO_LIGHT = "\033[38;2;160;180;90m"
AVOCADO_DARK = "\033[38;2;100;120;50m"
GRAY = "\033[90m"
RESET = "\033[0m"
BOLD = "\033[1m"

IS_WINDOWS = (platform.system() == "Windows")

HAS_INQUIRER = False
try:
    import inquirer
    HAS_INQUIRER = True
except ImportError:
    try:
        import inquirer3
        HAS_INQUIRER = True
    except ImportError:
        pass


def print_logo():
    """打印 Logo"""
    from common.terminal.banner import print_setup_banner
    print_setup_banner()


def _hide_cursor():
    print('\033[?25l', end='', flush=True)


def _show_cursor():
    print('\033[?25h', end='', flush=True)


def _fallback_select(
    options: List[Union[str, Tuple[str, str]]],
    title: Optional[str] = None,
    default_idx: int = 0,
    current_value: Optional[str] = None
) -> Optional[int]:
    """降级选择方案（数字输入）"""
    print()
    print(f"{BOLD}{AVOCADO_GREEN}{'─' * 50}{RESET}")
    print(f"{BOLD}{AVOCADO_GREEN}{title}{RESET}")
    print(f"{BOLD}{AVOCADO_GREEN}{'─' * 50}{RESET}")
    print()
    
    for i, opt in enumerate(options):
        if isinstance(opt, tuple):
            opt_id, opt_label = opt
            display_text = opt_label
        else:
            display_text = str(opt)
        
        marker = f"{i + 1}. "
        prefix = f"  {AVOCADO_GREEN}▶{RESET} " if i == default_idx else "    "
        print(f"{prefix}{marker}{display_text}")
    
    print()
    print(f"{AVOCADO_DARK}{'─' * 50}{RESET}")
    print(f"{GRAY}输入数字选择，或 q 退出{RESET}")
    
    while True:
        try:
            choice = input(f"\n{AVOCADO_GREEN}❯{RESET} ").strip()
            
            if choice.lower() in ('q', 'quit', 'exit'):
                return None
            
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(options):
                    return idx
                print(f"{AVOCADO_DARK}无效选择，请输入 1-{len(options)}{RESET}")
            else:
                print(f"{AVOCADO_DARK}请输入数字{RESET}")
        except (EOFError, KeyboardInterrupt):
            return None


def select_option(
    options: List[Union[str, Tuple[str, str]]],
    title: Optional[str] = None,
    description: Optional[str] = None,
    default_idx: int = 0,
    current_value: Optional[str] = None,
    show_logo: bool = True,
    show_config: bool = True
) -> Optional[int]:
    """智能选择器"""
    if not options:
        return None
    
    if show_logo:
        print_logo()
    
    return _fallback_select(options, title, default_idx, current_value)


def select_option_safe(
    options: List[Union[str, Tuple[str, str]]],
    title: Optional[str] = None,
    description: Optional[str] = None,
    default_idx: int = 0,
    current_value: Optional[str] = None
) -> Optional[int]:
    """安全的选择器"""
    return select_option(
        options, 
        title=title, 
        description=description,
        default_idx=default_idx,
        current_value=current_value
    )


def print_menu_with_logo(
    options: List[Union[str, Tuple[str, str]]],
    title: Optional[str] = None,
    current_value: Optional[str] = None
) -> Optional[int]:
    """打印 Logo + 菜单"""
    return select_option(
        options,
        title=title,
        current_value=current_value,
        show_logo=True,
        show_config=True
    )


def checkbox_with_inquirer(
    options: List[Union[str, Tuple[str, Any]]],
    title: Optional[str] = None,
    defaults: Optional[List[str]] = None
) -> Optional[List[str]]:
    """Checkbox 多选功能"""
    return None
