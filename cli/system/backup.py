#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backup - Configuration backup utility.

🚪 Access - 💬 CLI - 备份功能

提供配置和数据备份功能。
"""

import json
import shutil
import tarfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional


def get_backup_dir() -> Path:
    """Get the backup directory."""
    backup_dir = Path.home() / ".agent_z" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def backup_config(filename: str = None) -> str:
    """Backup configuration to a JSON file.

    Args:
        filename: Optional backup filename

    Returns:
        Backup file path
    """
    from common.config import load_config

    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"config_backup_{timestamp}.json"

    backup_dir = get_backup_dir()
    backup_path = backup_dir / filename

    config = load_config()

    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    return str(backup_path)


def restore_config(backup_file: str) -> bool:
    """Restore configuration from a backup file.

    Args:
        backup_file: Backup file path

    Returns:
        True if successful
    """
    from common.config import save_config

    backup_path = Path(backup_file)
    if not backup_path.exists():
        print(f"Backup file not found: {backup_file}")
        return False

    try:
        with open(backup_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        save_config(config)
        print(f"Config restored from: {backup_file}")
        return True
    except Exception as e:
        print(f"Failed to restore: {e}")
        return False


def list_backups() -> list:
    """List available backups.

    Returns:
        List of backup file info dicts
    """
    backup_dir = get_backup_dir()
    backups = []

    for file in backup_dir.glob("config_backup_*.json"):
        try:
            stat = file.stat()
            backups.append({
                "name": file.name,
                "path": str(file),
                "size": stat.st_size,
                "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
        except Exception:
            pass

    # Sort by mtime (newest first)
    backups.sort(key=lambda x: x["mtime"], reverse=True)

    return backups


def delete_backup(backup_file: str) -> bool:
    """Delete a backup file.

    Args:
        backup_file: Backup file path or name

    Returns:
        True if successful
    """
    backup_dir = get_backup_dir()

    if "/" not in backup_file and "\\" not in backup_file:
        backup_path = backup_dir / backup_file
    else:
        backup_path = Path(backup_file)

    if backup_path.exists():
        backup_path.unlink()
        print(f"Deleted: {backup_file}")
        return True

    print(f"Backup not found: {backup_file}")
    return False


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "backup":
            path = backup_config()
            print(f"Backup created: {path}")

        elif command == "restore" and len(sys.argv) > 2:
            restore_config(sys.argv[2])

        elif command == "list":
            for backup in list_backups():
                print(f"  {backup['name']} ({backup['mtime']})")

        elif command == "delete" and len(sys.argv) > 2:
            delete_backup(sys.argv[2])

    else:
        print("Usage:")
        print("  agentz backup")
        print("  agentz backup restore <file>")
        print("  agentz backup list")
        print("  agentz backup delete <file>")