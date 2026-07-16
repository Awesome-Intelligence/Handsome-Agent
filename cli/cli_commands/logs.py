#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Logs command - Log viewer for Agent-Z

🚪 Access - 💬 CLI - 日志查看

提供日志查看功能，支持级别过滤、搜索等。
"""

import sys
import os
from pathlib import Path
from typing import Optional, List
from datetime import datetime


def show_logs(lines: int = 50, level: Optional[str] = None, search: Optional[str] = None) -> None:
    """Display recent log entries.
    
    Args:
        lines: Number of lines to show (default 50)
        level: Filter by level (debug/info/warning/error)
        search: Search keyword in logs
    """
    from common.terminal.colors import Colors, color
    from common.terminal.ui import print_header, print_info, print_error
    
    print_header("📋 日志查看")
    
    # 获取日志目录
    log_dir = _get_log_dir()
    if not log_dir:
        print_error("日志目录不存在")
        return
    
    # 获取日志文件
    log_file = _get_log_file(log_dir)
    if not log_file:
        print_error("日志文件不存在")
        return
    
    # 读取日志
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
    except Exception as e:
        print_error(f"读取日志失败: {e}")
        return
    
    # 过滤日志
    filtered = _filter_logs(all_lines, level, search)
    
    # 显示最后 N 行
    display_lines = filtered[-lines:] if len(filtered) > lines else filtered
    
    print()
    print(color(f"  共 {len(filtered)} 条日志（显示 {len(display_lines)} 条）", Colors.DIM))
    print()
    
    if not display_lines:
        print_info("没有符合条件的日志")
        return
    
    # 打印日志
    for line in display_lines:
        _print_log_line(line, level)
    
    print()


def _get_log_dir() -> Optional[Path]:
    """获取日志目录"""
    try:
        from common.config import get_logs_dir
        return get_logs_dir()
    except Exception:
        # 回退到默认路径
        config_dir = Path.home() / ".agent_z"
        log_dir = config_dir / "logs"
        return log_dir if log_dir.exists() else None


def _get_log_file(log_dir: Path) -> Optional[Path]:
    """获取日志文件"""
    # 查找最新的日志文件
    log_files = list(log_dir.glob("*.log"))
    log_files.extend(log_dir.glob("*.log.*"))
    
    if not log_files:
        return None
    
    # 返回最新的日志文件
    return max(log_files, key=lambda f: f.stat().st_mtime)


def _filter_logs(lines: List[str], level: Optional[str], search: Optional[str]) -> List[str]:
    """过滤日志"""
    level_map = {
        "debug": ["DEBUG"],
        "info": ["INFO"],
        "warning": ["WARNING", "WARN"],
        "error": ["ERROR", "FATAL", "CRITICAL"],
    }
    
    if level:
        level_patterns = level_map.get(level.lower(), [level.upper()])
    else:
        level_patterns = None
    
    filtered = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 级别过滤
        if level_patterns:
            if not any(p in line for p in level_patterns):
                continue
        
        # 搜索过滤
        if search:
            if search.lower() not in line.lower():
                continue
        
        filtered.append(line)
    
    return filtered


def _print_log_line(line: str, level: Optional[str]) -> None:
    """打印单条日志"""
    from common.terminal.colors import Colors, color
    
    # 解析日志级别
    level_icons = {
        "DEBUG": (Colors.DIM, "🔍"),
        "INFO": (Colors.BLUE, "ℹ"),
        "WARNING": (Colors.YELLOW, "⚠"),
        "WARN": (Colors.YELLOW, "⚠"),
        "ERROR": (Colors.RED, "✗"),
        "FATAL": (Colors.RED, "💀"),
        "CRITICAL": (Colors.RED, "💀"),
    }
    
    # 检测级别
    detected_level = None
    for lvl, (color_code, icon) in level_icons.items():
        if lvl in line:
            detected_level = lvl
            break
    
    if detected_level:
        color_code, icon = level_icons[detected_level]
        print(color(f"  {icon} {line}", color_code))
    else:
        print(color(f"  {line}", Colors.DIM))


def tail_logs(lines: int = 20) -> None:
    """实时跟踪日志（类似 tail -f）"""
    from common.terminal.colors import Colors, color
    from common.terminal.ui import print_header, print_error
    
    print_header("📋 实时日志跟踪 (Ctrl+C 退出)")
    print()
    
    log_dir = _get_log_dir()
    if not log_dir:
        print_error("日志目录不存在")
        return
    
    log_file = _get_log_file(log_dir)
    if not log_file:
        print_error("日志文件不存在")
        return
    
    print(color(f"  跟踪: {log_file}", Colors.DIM))
    print(color("  按 Ctrl+C 退出", Colors.DIM))
    print()
    
    # 实现简单的 tail -f
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            # 跳到文件末尾
            f.seek(0, 2)
            
            while True:
                line = f.readline()
                if line:
                    _print_log_line(line.strip(), None)
                else:
                    import time
                    time.sleep(0.5)
    except KeyboardInterrupt:
        print()
        print(color("  已停止跟踪", Colors.DIM))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="View Agent-Z logs")
    parser.add_argument("-n", "--lines", type=int, default=50, help="Number of lines to show")
    parser.add_argument("-l", "--level", choices=["debug", "info", "warning", "error"],
                        help="Filter by log level")
    parser.add_argument("-s", "--search", type=str, help="Search keyword")
    parser.add_argument("-f", "--follow", action="store_true", help="Follow log (like tail -f)")
    
    args = parser.parse_args()
    
    if args.follow:
        tail_logs(args.lines)
    else:
        show_logs(lines=args.lines, level=args.level, search=args.search)