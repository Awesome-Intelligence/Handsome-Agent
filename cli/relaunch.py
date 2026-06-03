#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Relauch - CLI self-restart utility.

🚪 Access - 💬 CLI - 自我重启

允许 CLI 重新执行自身（例如在 setup 后启动 chat）。
"""

import os
import sys
from pathlib import Path


def relaunch(args: list = None):
    """Relaunch the CLI with the same arguments.

    Args:
        args: Optional list of arguments (defaults to sys.argv)
    """
    if args is None:
        args = sys.argv[1:]

    # Get the Python executable
    python = sys.executable

    # Build command
    cmd = [python, "-m", "cli.main"] + args

    # Execute
    os.execv(python, cmd)


def relaunch_chat():
    """Relaunch into chat mode."""
    relaunch(["chat"])


def relaunch_setup():
    """Relaunch into setup mode."""
    relaunch(["setup"])


if __name__ == "__main__":
    print("Relaunching...")
    relaunch()