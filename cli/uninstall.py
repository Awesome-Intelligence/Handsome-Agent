#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Uninstall - Uninstall Handsome Agent.

🚪 Access - 💬 CLI - 卸载程序

提供清理功能以卸载 Handsome Agent。
"""

import os
import shutil
from pathlib import Path


def confirm_uninstall() -> bool:
    """Ask for uninstallation confirmation.

    Returns:
        True if confirmed
    """
    response = input("Are you sure you want to uninstall Handsome Agent? (yes/no): ")
    return response.lower() in ("yes", "y")


def remove_config_files() -> bool:
    """Remove configuration files.

    Returns:
        True if successful
    """
    config_dir = Path.home() / ".handsome_agent"

    if config_dir.exists():
        try:
            shutil.rmtree(config_dir)
            print(f"Removed: {config_dir}")
            return True
        except Exception as e:
            print(f"Failed to remove config: {e}")
            return False

    return True


def remove_scripts() -> bool:
    """Remove installed scripts/shortcuts.

    Returns:
        True if successful
    """
    # Remove pip-installed scripts (on Windows, this might be in Scripts)
    # On Unix, this might be in ~/.local/bin

    scripts_to_check = [
        Path.home() / ".local" / "bin" / "handsome",
        Path.home() / "Scripts" / "handsome.exe",  # Windows
    ]

    removed = False
    for script in scripts_to_check:
        if script.exists():
            try:
                script.unlink()
                print(f"Removed: {script}")
                removed = True
            except Exception:
                pass

    return removed


def show_uninstall_summary(config_removed: bool, scripts_removed: bool):
    """Show uninstall summary.

    Args:
        config_removed: Whether config was removed
        scripts_removed: Whether scripts were removed
    """
    print()
    print("=" * 50)
    print("UNINSTALL COMPLETE")
    print("=" * 50)
    print()

    if config_removed:
        print("✓ Configuration files removed")
    else:
        print("○ Configuration files preserved")
        print(f"  Location: {Path.home() / '.handsome_agent'}")

    if scripts_removed:
        print("✓ Scripts removed")
    else:
        print("○ Some scripts may remain")
        print("  Run 'pip uninstall handsome-agent' to remove completely")

    print()
    print("Thank you for using Handsome Agent!")


def uninstall(force: bool = False):
    """Uninstall Handsome Agent.

    Args:
        force: Skip confirmation
    """
    print("Uninstalling Handsome Agent...")
    print()

    # Confirm
    if not force and not confirm_uninstall():
        print("Uninstall cancelled.")
        return

    # Remove config
    config_removed = remove_config_files()

    # Remove scripts
    scripts_removed = remove_scripts()

    # Show summary
    show_uninstall_summary(config_removed, scripts_removed)


if __name__ == "__main__":
    import sys

    force = "--force" in sys.argv or "-f" in sys.argv
    uninstall(force=force)