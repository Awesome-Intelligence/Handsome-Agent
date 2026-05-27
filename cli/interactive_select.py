#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""交互式选择器 - 支持Windows键盘选择，带牛油果绿主题"""

import sys
import os
import platform

IS_WINDOWS = platform.system() == "Windows"

# 牛油果绿主题颜色
AVOCADO_GREEN = "\033[38;2;112;145;40m"
AVOCADO_LIGHT = "\033[38;2;144;175;61m"
AVOCADO_DARK = "\033[38;2;85;110;30m"
GRAY = "\033[90m"
RESET = "\033[0m"


def print_menu(options, current, title=None):
    """Print menu with avocado green theme."""
    os.system('cls')
    print()
    if title:
        print(f"{AVOCADO_GREEN}{title}{RESET}")
        print(f"{AVOCADO_DARK}{'=' * 50}{RESET}")
    for i, opt in enumerate(options):
        if i == current:
            print(f"{AVOCADO_GREEN}> {i+1}. {opt}{RESET}")
        else:
            print(f"{GRAY}  {i+1}. {opt}{RESET}")
    print(f"{AVOCADO_DARK}{'=' * 50}{RESET}")
    print(f"{AVOCADO_LIGHT}↑↓移动  Enter确认  Q退出{RESET}")


def windows_select(options, title=None):
    """Windows键盘选择器."""
    import msvcrt
    
    current = 0
    length = len(options)
    print_menu(options, current, title)
    
    while True:
        if msvcrt.kbhit():
            ch = msvcrt.getch()
            
            if ch in (b'\x00', b'\xe0'):
                key = msvcrt.getch()
                if key == b'H':
                    current = (current - 1) % length
                    print_menu(options, current, title)
                elif key == b'P':
                    current = (current + 1) % length
                    print_menu(options, current, title)
            elif ch == b'\r':
                return current
            elif ch == b'q':
                return None


def unix_select(options, title=None):
    """Unix数字选择."""
    print()
    if title:
        print(f"{AVOCADO_GREEN}{title}{RESET}")
    print(f"{AVOCADO_DARK}{'=' * 50}{RESET}")
    for i, opt in enumerate(options):
        print(f"  {i+1}. {opt}")
    print(f"{AVOCADO_DARK}{'=' * 50}{RESET}")
    print()
    
    while True:
        try:
            choice = input(f"{AVOCADO_LIGHT}选择: {RESET}").strip().lower()
            if choice in ('q', 'quit', '取消'):
                return None
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return idx
            print(f"{GRAY}请输入 1-{len(options)} 之间的数字{RESET}")
        except ValueError:
            print(f"{GRAY}请输入数字{RESET}")
        except (EOFError, KeyboardInterrupt):
            return None


def select_option(options, title=None):
    """选择器入口."""
    if not options:
        return None
    
    if IS_WINDOWS:
        return windows_select(options, title)
    else:
        return unix_select(options, title)