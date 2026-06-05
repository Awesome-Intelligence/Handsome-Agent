#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交互式选择器 - 跨平台实现

方案优先级：
1. inquirer（跨平台，优先使用）
2. 数字输入（最后的保障）

特性：
- ✅ 跨平台：Windows/macOS/Linux
- ✅ 牛油果绿主题
"""

import sys
import os
import platform
from typing import List, Union, Optional, Tuple, Any


# ============ 颜色配置 ============
# 与 cli/colors.py Theme.ACCENT 保持一致 #A0B45A
AVOCADO_GREEN = "\033[38;2;160;180;90m"    # #A0B45A Theme.ACCENT
AVOCADO_LIGHT = "\033[38;2;160;180;90m"    # #A0B45A
AVOCADO_DARK = "\033[38;2;100;120;50m"     # #647832
GRAY = "\033[90m"
RESET = "\033[0m"
BOLD = "\033[1m"


# ============ 平台检测 ============
IS_WINDOWS = (platform.system() == "Windows")


# ============ 依赖检测 ============
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
    """打印 Logo - 使用增强的 Banner"""
    from .banner import print_setup_banner
    print_setup_banner()


def print_config_summary():
    """打印配置摘要"""
    from .setup import has_existing_config, show_current_config, load_config as wizard_load_config
    
    if has_existing_config():
        config = wizard_load_config()
        if isinstance(config, dict):
            show_current_config(config)
            print()


def _hide_cursor():
    """隐藏终端光标"""
    print('\033[?25l', end='', flush=True)

def _show_cursor():
    """显示终端光标"""
    print('\033[?25h', end='', flush=True)

# ============ 1. inquirer 主实现（跨平台） ============

# 牛油果绿主题 - 匹配 Handsome Agent 品牌色 #A0B45A
AVOCADO_THEME = None  # 延迟初始化

def _get_avocado_theme():
    """获取牛油果绿主题（延迟初始化）"""
    global AVOCADO_THEME
    if AVOCADO_THEME is None:
        try:
            from inquirer.themes import GreenPassion
            AVOCADO_THEME = GreenPassion()
            # 自定义牛油果绿颜色 #A0B45A
            AVOCADO_COLOR = "\033[38;2;160;180;90m"  # 牛油果绿
            AVOCADO_BOLD = "\033[1m\033[38;2;160;180;90m"  # 加粗牛油果绿
            # 设置 List 选中项颜色
            AVOCADO_THEME.List.selection_color = AVOCADO_COLOR
            AVOCADO_THEME.List.selection_cursor = "▸ "
            AVOCADO_THEME.List.unselected_color = "\033[90m"  # 灰色
            # 设置 Checkbox 颜色 - 与 List 保持一致
            AVOCADO_THEME.Checkbox.selection_color = AVOCADO_COLOR
            AVOCADO_THEME.Checkbox.selection_cursor = "▸ "
            AVOCADO_THEME.Checkbox.unselected_color = "\033[90m"  # 灰色
            AVOCADO_THEME.Checkbox.selected_color = AVOCADO_COLOR
            AVOCADO_THEME.Checkbox.selected_cursor = "◉"
            AVOCADO_THEME.Checkbox.unselected_cursor = "◯"
            # 设置问题颜色 - 统一为牛油果绿
            AVOCADO_THEME.Question.default_color = AVOCADO_COLOR
            AVOCADO_THEME.Question.brackets_color = AVOCADO_COLOR
            AVOCADO_THEME.Question.mark_color = AVOCADO_COLOR
        except Exception:
            AVOCADO_THEME = None
    return AVOCADO_THEME


def _select_with_inquirer(
    options: List[Union[str, Tuple[str, str]]],
    title: Optional[str] = None,
    current_value: Optional[str] = None
) -> Optional[int]:
    """
    使用 inquirer 库（首选，跨平台）
    Ctrl+C 直接返回 None（退出选择），不降级到其他菜单
    使用牛油果绿主题
    """
    try:
        import inquirer
    except ImportError:
        import inquirer3 as inquirer

    choices = []
    option_map = {}

    for i, opt in enumerate(options):
        if isinstance(opt, tuple):
            opt_id, opt_label = opt
            is_current = (current_value is not None and opt_id == current_value)
            label = f"[*] {opt_label}" if is_current else f"    {opt_label}"
        else:
            label = str(opt)
            opt_id = label
        choices.append((label, i))
        option_map[i] = opt_id

    questions = [
        inquirer.List(
            'choice',
            message=title or "请选择",
            choices=choices,
        )
    ]

    _hide_cursor()
    try:
        # 主题传给 prompt，不是传给 List
        result = inquirer.prompt(questions, theme=_get_avocado_theme())
    except KeyboardInterrupt:
        # Ctrl+C 直接返回 None（退出），不降级
        _show_cursor()
        return None
    finally:
        _show_cursor()

    if result and 'choice' in result:
        return result['choice']
    return None


def checkbox_with_inquirer(
    options: List[Union[str, Tuple[str, Any]]],
    title: Optional[str] = None,
    defaults: Optional[List[str]] = None
) -> Optional[List[str]]:
    """
    使用 inquirer 库的 Checkbox 多选功能
    - 空格切换选中/取消
    - 上下箭头导航
    - 回车确认
    - Ctrl+C 返回 None
    """
    try:
        import inquirer
    except ImportError:
        try:
            import inquirer3 as inquirer
        except ImportError:
            return None

    # inquirer.Checkbox 使用简单的字符串列表
    # choices 格式: 字符串或 (value, name) 元组
    # 返回: 选中的字符串列表
    
    questions = [
        inquirer.Checkbox(
            'choices',
            message=title or "请选择",
            choices=options,
        )
    ]

    _hide_cursor()
    try:
        result = inquirer.prompt(questions, theme=_get_avocado_theme())
    except KeyboardInterrupt:
        _show_cursor()
        return None
    finally:
        _show_cursor()

    # result['choices'] 返回选中的字符串列表（value）
    if result and 'choices' in result:
        return result['choices']
    return None


# ============ 2. 自定义实现（后备） ============
def _get_key_native():
    """获取原生键盘输入"""
    if IS_WINDOWS:
        try:
            import msvcrt
            key = msvcrt.getch()
            
            if key in (b'\x00', b'\xe0'):
                key = msvcrt.getch()
                if key == b'H':
                    return 'UP'
                elif key == b'P':
                    return 'DOWN'
                elif key == b'M':
                    return 'RIGHT'
                elif key == b'K':
                    return 'LEFT'
                return key.decode('ascii', errors='ignore')
            else:
                try:
                    return key.decode('ascii', errors='ignore')
                except:
                    return key
        except ImportError:
            return input()
    else:
        try:
            import tty
            import termios
            
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(sys.stdin.fileno())
                ch = sys.stdin.read(1)
                
                if ch == '\x1b':
                    ch2 = sys.stdin.read(1)
                    if ch2 == '[':
                        ch3 = sys.stdin.read(1)
                        if ch3 == 'A':
                            return 'UP'
                        elif ch3 == 'B':
                            return 'DOWN'
                        elif ch3 == 'C':
                            return 'RIGHT'
                        elif ch3 == 'D':
                            return 'LEFT'
                        return ch3
                    elif ch2 == '\x1b' or ch2 == '':
                        return 'ESC'
                    return ch2
                elif ch == '\r' or ch == '\n':
                    return 'ENTER'
                elif ch in ('\x03', '\x1a'):
                    raise KeyboardInterrupt
                return ch
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        except (ImportError, termios.error):
            try:
                return input()
            except EOFError:
                return None


def _select_with_native(
    options: List[Union[str, Tuple[str, str]]],
    title: Optional[str] = None,
    current_value: Optional[str] = None
) -> Optional[int]:
    """
    自定义实现（inquirer 失败时的后备）
    """
    CURSOR_UP = "\033[1A"
    CURSOR_DOWN = "\033[1B"
    ERASE_LINE = "\033[K"
    
    current_idx = 0
    first_run = True
    
    _hide_cursor()
    try:
        while True:
            if not first_run:
                lines_to_up = len(options) + 7
                if not title:
                    lines_to_up -= 4
                
                for _ in range(lines_to_up):
                    print(f"{CURSOR_UP}{ERASE_LINE}", end="")
                sys.stdout.flush()
            else:
                first_run = False
            
            if title:
                print(f"{BOLD}{AVOCADO_GREEN}╭{'─' * 50}╮{RESET}")
                print(f"{BOLD}{AVOCADO_GREEN}│{RESET}{BOLD}{AVOCADO_LIGHT} {title.center(50)} {RESET}{AVOCADO_GREEN}│{RESET}")
                print(f"{BOLD}{AVOCADO_GREEN}╰{'─' * 50}╯{RESET}")
                print()
            
            for i, opt in enumerate(options):
                if isinstance(opt, tuple):
                    opt_id, opt_label = opt
                    display_text = opt_label
                    is_current = (current_value is not None and opt_id == current_value)
                else:
                    display_text = str(opt)
                    is_current = False
                
                marker = "[*] " if is_current else f"{i + 1}. "
                
                if i == current_idx:
                    print(f"  {AVOCADO_GREEN}▶{RESET} {BOLD}{AVOCADO_GREEN}{marker}{display_text}{RESET}")
                else:
                    print(f"    {GRAY}{marker}{display_text}{RESET}")
            
            print()
            print(f"{AVOCADO_DARK}{'─' * 50}{RESET}")
            print(f"{GRAY}↑↓ 移动 | 数字选择 | Enter 确认 | Q/ESC 退出{RESET}", end="")
            sys.stdout.flush()
            
            key = _get_key_native()
            
            if key is None:
                continue
            
            if key in ('UP', 'k', 'K'):
                current_idx = (current_idx - 1) % len(options)
            elif key in ('DOWN', 'j', 'J'):
                current_idx = (current_idx + 1) % len(options)
            elif key in ('ENTER', '\r', '\n'):
                print()
                print()
                return current_idx
            elif key in ('q', 'Q', 'ESC', '\x1b'):
                print(f"\n\n{AVOCADO_DARK}已退出选择{RESET}")
                return None
            elif key.isdigit():
                idx = int(key) - 1
                if 0 <= idx < len(options):
                    current_idx = idx
                    print(f"\n\n{AVOCADO_DARK}{'─' * 50}{RESET}")
                    return current_idx
    
    except (KeyboardInterrupt, EOFError):
        print(f"\n\n{GRAY}用户中断选择{RESET}")
        return None
    finally:
        _show_cursor()


# ============ 3. 降级选择方案 ============
def _fallback_select(
    options: List[Union[str, Tuple[str, str]]],
    title: Optional[str] = None,
    default_idx: int = 0,
    current_value: Optional[str] = None
) -> Optional[int]:
    """
    降级选择方案（数字输入）
    """
    print()
    print(f"{BOLD}{AVOCADO_GREEN}{'─' * 50}{RESET}")
    print(f"{BOLD}{AVOCADO_GREEN}{title}{RESET}")
    print(f"{BOLD}{AVOCADO_GREEN}{'─' * 50}{RESET}")
    print()
    
    for i, opt in enumerate(options):
        if isinstance(opt, tuple):
            opt_id, opt_label = opt
            display_text = opt_label
            is_current = (current_value is not None and opt_id == current_value)
        else:
            display_text = str(opt)
            is_current = False
        
        marker = "[*] " if is_current else f"{i + 1}. "
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


# ============ 主选择器 ============
def select_option(
    options: List[Union[str, Tuple[str, str]]],
    title: Optional[str] = None,
    description: Optional[str] = None,
    default_idx: int = 0,
    current_value: Optional[str] = None,
    show_logo: bool = True,
    show_config: bool = True
) -> Optional[int]:
    """
    智能选择器 - 跨平台实现
    
    方案优先级：
    1. inquirer（跨平台，优先使用）
    2. 数字输入（最后保障）
    
    Args:
        options: 选项列表
        title: 标题
        current_value: 当前值（用于标记）
        show_logo: 是否显示 Logo
        show_config: 是否显示配置
    
    Returns:
        选中索引，None 表示退出
    """
    if not options:
        return None
    
    if show_logo:
        print_logo()
    
    if show_config:
        print_config_summary()
    
    try:
        if HAS_INQUIRER:
            result = _select_with_inquirer(options, title, current_value)
            if result is not None:
                return result
            return None

    except Exception as e:
        print(f"{GRAY}选择器出错: {e}{RESET}")
    
    # 最后的保障：数字输入
    return _fallback_select(options, title, default_idx, current_value)


def select_option_safe(
    options: List[Union[str, Tuple[str, str]]],
    title: Optional[str] = None,
    description: Optional[str] = None,
    default_idx: int = 0,
    current_value: Optional[str] = None
) -> Optional[int]:
    """
    安全的选择器 - 捕获所有异常
    """
    try:
        return select_option(
            options, 
            title=title, 
            description=description,
            default_idx=default_idx,
            current_value=current_value
        )
    except Exception as e:
        print(f"\n{GRAY}菜单选择出错: {e}{RESET}")
        return _fallback_select(options, title or "请选择", default_idx, current_value)


def print_menu_with_logo(
    options: List[Union[str, Tuple[str, str]]],
    title: Optional[str] = None,
    current_value: Optional[str] = None
) -> Optional[int]:
    """
    打印 Logo + 菜单（兼容旧接口）
    """
    return select_option(
        options,
        title=title,
        current_value=current_value,
        show_logo=True,
        show_config=True
    )


if __name__ == "__main__":
    print("测试交互式选择器\n")
    
    options = [
        ("option1", "第一个选项 - 这是中文"),
        ("option2", "第二个选项 - English"),
        ("option3", "第三个选项 - 日本語"),
        ("option4", "第四个选项"),
        ("option5", "第五个选项"),
    ]
    
    result = print_menu_with_logo(options, title="选择测试菜单", current_value="option2")
    
    if result is not None:
        print(f"\n✅ 你选择了: {options[result]}")
    else:
        print("\n❌ 你取消了选择")
