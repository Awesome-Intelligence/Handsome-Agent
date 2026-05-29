#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交互式选择器 - 支持键盘上下键选择，类似 OpenClaw 风格

特性：
- 跨平台支持（Windows/macOS/Linux）
- 键盘上下键导航
- Enter 确认选择
- Q/ESC 退出
- 牛油果绿主题
"""

import sys
import os
import platform

IS_WINDOWS = platform.system() == "Windows"
IS_UNIX = not IS_WINDOWS

# Unix 特定模块
if IS_UNIX:
    import termios
    import tty

# 牛油果绿主题颜色（RGB: 139, 154, 70 / #8B9A46）
AVOCADO_GREEN = "\033[38;2;139;154;70m"      # 牛油果绿
AVOCADO_LIGHT = "\033[38;2;160;180;90m"      # 亮牛油果绿
AVOCADO_DARK = "\033[38;2;100;120;50m"       # 暗牛油果绿
GRAY = "\033[90m"              # 暗灰色
RESET = "\033[0m"
BOLD = "\033[1m"
BLUE = "\033[34m"


def clear_screen():
    """清除屏幕."""
    os.system('cls' if IS_WINDOWS else 'clear')


def print_menu(options, current_idx, title=None, description=None, current_value=None):
    """打印菜单（原地更新）.
    
    Args:
        options: 选项列表，每个选项可以是字符串或元组 (id, label)
        current_idx: 当前选中的索引
        title: 标题
        description: 描述
        current_value: 当前已配置的值（用于标记）
    """
    # 不清屏，保留 Logo 显示
    # clear_screen()  # 注释掉，保留之前的输出
    
    print()
    
    if title:
        print(f"{BOLD}{AVOCADO_GREEN}╭{'─' * 50}╮{RESET}")
        print(f"{BOLD}{AVOCADO_GREEN}│{RESET}{BOLD}{AVOCADO_LIGHT} {title.center(50)} {RESET}{AVOCADO_GREEN}│{RESET}")
        print(f"{BOLD}{AVOCADO_GREEN}╰{'─' * 50}╯{RESET}")
        print()
    
    for i, opt in enumerate(options):
        # opt 可能是元组 (id, label) 或单个字符串
        if isinstance(opt, tuple):
            opt_id, opt_label = opt
            display_text = opt_label
            # 检查是否是当前已配置的值
            is_current = (current_value is not None and opt_id == current_value)
        else:
            display_text = opt
            is_current = False
        
        # 添加已配置标记
        marker = "[*] " if is_current else ""
        
        if i == current_idx:
            # 选中状态
            print(f"  {AVOCADO_GREEN}▶ {BOLD}{marker}{display_text}{RESET} ")
        else:
            # 未选中状态
            print(f"  {GRAY}  {marker}{display_text}{RESET}")
    
    print()
    
    # 底部提示
    if description:
        print(f"{AVOCADO_DARK}{'─' * 50}{RESET}")
        print(f"{AVOCADO_LIGHT}{description}{RESET}")
    
    print(f"{AVOCADO_DARK}{'─' * 50}{RESET}")
    print(f"{GRAY}↑↓ 移动   Enter 确认   Q/ESC 退出{RESET}")


def get_key_unix():
    """获取 Unix 平台的按键."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        
        # 检查是否是特殊键
        if ch == '\x1b':  # ESC
            next_ch = sys.stdin.read(1)
            if next_ch == '[':
                arrow = sys.stdin.read(1)
                if arrow == 'A':
                    return 'UP'
                elif arrow == 'B':
                    return 'DOWN'
                elif arrow == 'C':
                    return 'RIGHT'
                elif arrow == 'D':
                    return 'LEFT'
            return 'ESC'
        elif ch == '\r':
            return 'ENTER'
        elif ch == 'q' or ch == 'Q':
            return 'QUIT'
        elif ch == '\x03':  # Ctrl+C
            return 'QUIT'
        else:
            return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def get_key_windows():
    """获取 Windows 平台的按键."""
    import msvcrt
    import time
    
    # 非阻塞检查
    if not msvcrt.kbhit():
        return None
    
    ch = msvcrt.getch()
    
    # 功能键
    if ch in (b'\x00', b'\xe0'):
        key = msvcrt.getch()
        if key == b'H':
            return 'UP'
        elif key == b'P':
            return 'DOWN'
        elif key == b'M':
            return 'RIGHT'
        elif key == b'K':
            return 'LEFT'
        return 'UNKNOWN'
    
    # 普通键
    if ch == b'\r':
        return 'ENTER'
    elif ch == b'q' or ch == b'Q':
        return 'QUIT'
    elif ch == b'\x1b':  # ESC
        return 'ESC'
    elif ch == b'\x03':  # Ctrl+C
        return 'QUIT'
    
    try:
        return ch.decode('utf-8')
    except:
        return 'UNKNOWN'


def keyboard_select(options, title=None, description=None, default_idx=0, current_value=None):
    """键盘选择器（跨平台）.
    
    Args:
        options: 选项列表
        title: 标题
        description: 描述
        default_idx: 默认选中索引
        current_value: 当前已配置的值（用于标记）
    """
    import time
    import sys
    
    if not options:
        return None
    
    current_idx = default_idx
    length = len(options)
    
    # 打印初始菜单（不清屏，保留 Logo）
    print_menu(options, current_idx, title, description, current_value)
    
    while True:
        # 获取按键
        if IS_WINDOWS:
            key = get_key_windows()
        else:
            key = get_key_unix()
        
        if key is None:
            # 没有按键，稍等一下避免 CPU 占用过高
            time.sleep(0.05)
            continue
        
        # 处理按键 - 重新打印整个界面
        if key == 'UP':
            current_idx = (current_idx - 1) % length
            clear_screen()
            print_menu(options, current_idx, title, description, current_value)
        
        elif key == 'DOWN':
            current_idx = (current_idx + 1) % length
            clear_screen()
            print_menu(options, current_idx, title, description, current_value)
        
        elif key == 'ENTER':
            return current_idx
        
        elif key in ('QUIT', 'ESC'):
            return None


def number_select(options, title=None, description=None, current_value=None):
    """数字选择器（备用方案）.
    
    Args:
        current_value: 当前已配置的值（用于标记）
    """
    # 移除了 clear_screen()，保留之前的输出
    print()
    
    if title:
        print(f"{BOLD}{AVOCADO_GREEN}{'─' * 50}{RESET}")
        print(f"{BOLD}{AVOCADO_GREEN}{title}{RESET}")
        print(f"{BOLD}{AVOCADO_GREEN}{'─' * 50}{RESET}")
        print()


def print_menu_with_logo(options, title=None, current_value=None):
    """打印 Logo + 菜单，并在选择过程中保持 Logo 显示.
    
    Args:
        options: 选项列表
        title: 标题
        current_value: 当前已配置的值（用于标记）
    """
    import time
    import sys
    
    if not options:
        return None
    
    # 获取 Logo
    from .ui import print_banner
    import io
    
    # 捕获 Logo 输出
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    print_banner()
    logo_output = sys.stdout.getvalue()
    sys.stdout = old_stdout
    
    # 动态导入，避免循环依赖
    from .setup_wizard import has_existing_config, show_current_config, load_config
    
    # 清屏并显示 Logo
    clear_screen()
    print(logo_output, end='')
    
    # 显示配置（如果有）
    if has_existing_config():
        config = load_config()
        show_current_config(config)
        print()
    
    # 显示菜单
    current_idx = 0
    length = len(options)
    
    # 打印菜单
    _print_menu(options, current_idx, title, current_value)
    
    while True:
        # 获取按键
        if IS_WINDOWS:
            key = get_key_windows()
        else:
            key = get_key_unix()
        
        if key is None:
            time.sleep(0.05)
            continue
        
        if key == 'UP':
            current_idx = (current_idx - 1) % length
            clear_screen()
            print(logo_output, end='')
            if has_existing_config():
                config = load_config()
                show_current_config(config)
                print()
            _print_menu(options, current_idx, title, current_value)
        
        elif key == 'DOWN':
            current_idx = (current_idx + 1) % length
            clear_screen()
            print(logo_output, end='')
            if has_existing_config():
                config = load_config()
                show_current_config(config)
                print()
            _print_menu(options, current_idx, title, current_value)
        
        elif key == 'ENTER':
            return current_idx
        
        elif key in ('QUIT', 'ESC'):
            return None


def _print_menu(options, current_idx, title=None, current_value=None):
    """内部函数：打印菜单（不清屏）.
    
    Args:
        options: 选项列表
        current_idx: 当前选中的索引
        title: 标题
        current_value: 当前已配置的值（用于标记）
    """
    print()
    
    if title:
        print(f"{BOLD}{AVOCADO_GREEN}╭{'─' * 50}╮{RESET}")
        print(f"{BOLD}{AVOCADO_GREEN}│{RESET}{BOLD}{AVOCADO_LIGHT} {title.center(50)} {RESET}{AVOCADO_GREEN}│{RESET}")
        print(f"{BOLD}{AVOCADO_GREEN}╰{'─' * 50}╯{RESET}")
        print()
    
    for i, opt in enumerate(options):
        if isinstance(opt, tuple):
            opt_id, opt_label = opt
            display_text = opt_label
            # 检查是否是当前已配置的值
            is_current = (current_value is not None and opt_id == current_value)
        else:
            display_text = opt
            is_current = False
        
        # 添加已配置标记
        marker = "[*] " if is_current else ""
        
        if i == current_idx:
            print(f"  {AVOCADO_GREEN}▶ {BOLD}{marker}{display_text}{RESET} ")
        else:
            print(f"  {GRAY}  {marker}{display_text}{RESET}")
    
    print()
    
    print(f"{AVOCADO_DARK}{'─' * 50}{RESET}")
    print(f"{GRAY}↑↓ 移动   Enter 确认   Q/ESC 退出{RESET}")


def select_option(options, title=None, description=None, default_idx=0, allow_keyboard=True, current_value=None):
    """选择器入口.
    
    Args:
        options: 选项列表，每个选项可以是字符串或元组 (id, label)
        title: 菜单标题
        description: 菜单描述
        default_idx: 默认选中的索引
        allow_keyboard: 是否允许键盘选择（True 使用键盘，False 使用数字）
        current_value: 当前已配置的值（用于标记）
    
    Returns:
        选中的索引，或 None（用户退出）
    """
    if not options:
        return None
    
    # 如果只有一个选项，直接返回
    if len(options) == 1:
        return 0
    
    # 优先使用键盘选择
    # Windows 上始终使用键盘选择，Unix/Linux 取决于终端
    use_keyboard = False
    if allow_keyboard:
        if IS_WINDOWS:
            # Windows 上始终尝试键盘选择
            use_keyboard = True
        elif sys.stdin.isatty():
            # Unix/Linux 上只有在交互式终端才使用
            use_keyboard = True
    
    # 使用键盘选择
    if use_keyboard:
        try:
            return keyboard_select(options, title, description, default_idx, current_value)
        except Exception as e:
            # 键盘选择失败，降级到数字选择
            print(f"{GRAY}键盘选择出错: {e}，使用数字选择{RESET}")
    
    # 回退到数字选择
    return number_select(options, title, description, current_value)


def select_option_safe(options, title=None, description=None, default_idx=0, current_value=None):
    """安全的选择器入口，捕获所有异常.
    
    Args:
        current_value: 当前已配置的值（用于标记）
    """
    import sys
    import traceback
    try:
        return select_option(options, title, description, default_idx, True, current_value)
    except KeyboardInterrupt:
        print(f"\n{GRAY}用户中断选择{RESET}")
        return None
    except Exception as e:
        print(f"\n{GRAY}键盘选择出错，回退到数字选择: {e}{RESET}")
        traceback.print_exc()
        return number_select(options, title, description, current_value)


if __name__ == "__main__":
    # 测试代码
    print("测试交互式选择器\n")
    
    options = [
        ("option1", "第一个选项 - 这是中文"),
        ("option2", "第二个选项 - English"),
        ("option3", "第三个选项 - 日本語"),
        ("option4", "第四个选项"),
        ("option5", "第五个选项"),
    ]
    
    result = select_option(options, title="选择测试菜单", description="请选择一个选项")
    
    if result is not None:
        print(f"\n✅ 你选择了: {options[result]}")
    else:
        print("\n❌ 你取消了选择")
