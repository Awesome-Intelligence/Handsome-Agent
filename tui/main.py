#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TUI 独立入口点

🚪 Access - 💬 TUI - 入口

提供独立的 TUI 启动方式：`python -m tui.main`

Usage:
    python -m tui.main
    python -m tui.main --help
"""

from __future__ import annotations

# Patch Textual logger for compatibility
def _patch_textual_logger():
    """Patch Textual's LayerLogger for compatibility."""
    try:
        from textual._log import LayerLogger
        LayerLogger.system = lambda *args, **kwargs: None
        LayerLogger.info = lambda *args, **kwargs: None
        LayerLogger.debug = lambda *args, **kwargs: None
        LayerLogger.warning = lambda *args, **kwargs: None
        LayerLogger.error = lambda *args, **kwargs: None
        LayerLogger.critical = lambda *args, **kwargs: None
    except ImportError:
        pass

_patch_textual_logger()

import sys


def main():
    """TUI 主入口函数"""
    from tui.textual_app import run_textual_app

    # 设置 sys.argv 以便 argparse 可以正确解析
    # 移除 'main.py' 或 '-m tui' 前缀
    if len(sys.argv) > 1 and sys.argv[0].endswith('main.py'):
        sys.argv = sys.argv[1:]
    elif len(sys.argv) > 1 and 'tui' in sys.argv[0]:
        # 处理 python -m tui.main 的情况
        sys.argv = [''] + sys.argv[2:] if len(sys.argv) > 2 else ['']

    return run_textual_app()


if __name__ == "__main__":
    sys.exit(main())
