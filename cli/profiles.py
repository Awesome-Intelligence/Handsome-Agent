#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Profiles CLI - Multiple configuration profiles.

🚪 Access - 💬 CLI - 多配置文件

参考 Hermes 的 profiles.py 设计，增强版：
- Profile 导入/导出 (tar.gz)
- Profile 元数据 (profile.yaml)
- Profile 描述
- Profile 复制

This module provides:
- handsome profile list       - List all profiles
- handsome profile create     - Create a new profile
- handsome profile delete     - Delete a profile
- handsome profile use <name>  - Switch to a profile
- handsome profile rename       - Rename a profile
- handsome profile export <name> - Export profile to tar.gz
- handsome profile import <file> - Import profile from tar.gz
- handsome profile describe <name> - LLM-driven profile description

Each profile has its own config files and metadata.
"""

import json
import os
import shutil
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any


def get_profiles_dir() -> Path:
    """Get the profiles directory."""
    home = Path.home() / ".handsome_agent"
    profiles_dir = home / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    return profiles_dir


def get_default_dir() -> Path:
    """Get the default config directory."""
    return Path.home() / ".handsome_agent"


def get_profile_dir(name: str) -> Path:
    """Get profile directory by name."""
    if name == "default":
        return get_default_dir()
    return get_profiles_dir() / name


def get_backups_dir() -> Path:
    """Get the backups directory."""
    backups_dir = get_default_dir() / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)
    return backups_dir


# =============================================================================
# Profile Metadata
# =============================================================================

def get_metadata_path(name: str) -> Path:
    """Get profile metadata file path."""
    return get_profile_dir(name) / "profile.yaml"


def load_metadata(name: str) -> Dict[str, Any]:
    """Load profile metadata.

    Args:
        name: Profile name

    Returns:
        Metadata dict
    """
    metadata_path = get_metadata_path(name)
    if metadata_path.exists():
        try:
            import yaml
            with open(metadata_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception:
            pass
    return {}


def save_metadata(name: str, metadata: Dict[str, Any]):
    """Save profile metadata.

    Args:
        name: Profile name
        metadata: Metadata dict
    """
    import yaml

    profile_dir = get_profile_dir(name)
    profile_dir.mkdir(parents=True, exist_ok=True)

    metadata_path = get_metadata_path(name)
    with open(metadata_path, 'w', encoding='utf-8') as f:
        yaml.dump(metadata, f, default_flow_style=False, allow_unicode=True)


def create_default_metadata(name: str) -> Dict[str, Any]:
    """Create default metadata for a profile.

    Args:
        name: Profile name

    Returns:
        Default metadata dict
    """
    return {
        "name": name,
        "created_at": datetime.now().isoformat(),
        "description": "",
        "tags": [],
        "color": None,
        "default_model": None,
        "default_toolsets": [],
    }


# =============================================================================
# Basic Operations
# =============================================================================

def list_profiles() -> list:
    """List all available profiles with metadata.

    Returns:
        List of profile info dicts
    """
    profiles_dir = get_profiles_dir()
    profiles = [
        {
            "name": "default",
            "metadata": load_metadata("default"),
        }
    ]

    if profiles_dir.exists():
        for item in profiles_dir.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                name = item.name
                profiles.append({
                    "name": name,
                    "metadata": load_metadata(name),
                })

    return sorted(profiles, key=lambda x: x["name"])


def profile_exists(name: str) -> bool:
    """Check if a profile exists.

    Args:
        name: Profile name

    Returns:
        True if profile exists
    """
    if name == "default":
        return True
    return get_profiles_dir().joinpath(name).exists()


def create_profile(name: str, copy_from: str = "default", description: str = "") -> bool:
    """Create a new profile.

    Args:
        name: Profile name
        copy_from: Profile to copy settings from (default: 'default')
        description: Profile description

    Returns:
        True if successful
    """
    from cli import ui

    if profile_exists(name):
        ui.print_error(f"Profile '{name}' already exists")
        return False

    # Source directory
    source_dir = get_profile_dir(copy_from)

    if not source_dir.exists():
        ui.print_error(f"Source profile '{copy_from}' not found")
        return False

    # Target directory
    target_dir = get_profile_dir(name)
    target_dir.mkdir(parents=True, exist_ok=True)

    # Copy config files
    files_to_copy = ["config.json", ".env"]
    for filename in files_to_copy:
        src = source_dir / filename
        if src.exists():
            shutil.copy2(src, target_dir / filename)

    # Copy metadata if exists
    src_metadata = get_metadata_path(copy_from)
    if src_metadata.exists():
        shutil.copy2(src_metadata, target_dir / "profile.yaml")

    # Create or update metadata
    metadata = load_metadata(copy_from) if copy_from != "default" else create_default_metadata(name)
    metadata["name"] = name
    metadata["created_at"] = datetime.now().isoformat()
    metadata["copied_from"] = copy_from
    if description:
        metadata["description"] = description
    save_metadata(name, metadata)

    ui.print_success(f"Profile '{name}' created (copied from '{copy_from}')")
    return True


def delete_profile(name: str, force: bool = False) -> bool:
    """Delete a profile.

    Args:
        name: Profile name
        force: Force delete without confirmation

    Returns:
        True if successful
    """
    from cli import ui

    if name == "default":
        ui.print_error("Cannot delete the 'default' profile")
        return False

    profile_dir = get_profiles_dir() / name
    if not profile_dir.exists():
        ui.print_error(f"Profile '{name}' not found")
        return False

    # Confirm deletion
    if not force:
        response = input(f"Delete profile '{name}'? (yes/no): ")
        if response.lower() not in ("yes", "y"):
            ui.print_info("Deletion cancelled")
            return False

    shutil.rmtree(profile_dir)
    ui.print_success(f"Profile '{name}' deleted")
    return True


def rename_profile(old_name: str, new_name: str) -> bool:
    """Rename a profile.

    Args:
        old_name: Old profile name
        new_name: New profile name

    Returns:
        True if successful
    """
    from cli import ui

    if old_name == "default":
        ui.print_error("Cannot rename the 'default' profile")
        return False

    if profile_exists(new_name):
        ui.print_error(f"Profile '{new_name}' already exists")
        return False

    source_dir = get_profile_dir(old_name)
    if not source_dir.exists():
        ui.print_error(f"Profile '{old_name}' not found")
        return False

    # Update metadata
    metadata = load_metadata(old_name)
    metadata["name"] = new_name
    metadata["renamed_from"] = old_name
    metadata["renamed_at"] = datetime.now().isoformat()

    target_dir = get_profiles_dir() / new_name
    shutil.move(str(source_dir), str(target_dir))

    # Update metadata in new location
    save_metadata(new_name, metadata)

    ui.print_success(f"Profile '{old_name}' renamed to '{new_name}'")
    return True


def switch_profile(name: str) -> bool:
    """Switch to a profile.

    Args:
        name: Profile name

    Returns:
        True if successful
    """
    from cli import ui

    if name == "default":
        # Remove symlink if exists
        link = get_profiles_dir() / "current"
        if link.is_symlink() or link.exists():
            link.unlink()
        ui.print_success("Switched to 'default' profile")
        return True

    if not profile_exists(name):
        ui.print_error(f"Profile '{name}' not found")
        return False

    profiles_dir = get_profiles_dir()
    link = profiles_dir / "current"

    # Remove existing link
    if link.is_symlink() or link.exists():
        link.unlink()

    # Create new link
    profile_dir = profiles_dir / name
    link.symlink_to(profile_dir, target_is_directory=True)

    ui.print_success(f"Switched to '{name}' profile")
    return True


def get_current_profile() -> str:
    """Get the current active profile name.

    Returns:
        Profile name
    """
    profiles_dir = get_profiles_dir()
    link = profiles_dir / "current"

    if link.is_symlink():
        return link.resolve().name

    return "default"


# =============================================================================
# Import / Export
# =============================================================================

def export_profile(name: str, output_file: str = None) -> str:
    """Export profile to tar.gz archive.

    Args:
        name: Profile name
        output_file: Output file path (auto-generated if None)

    Returns:
        Export file path
    """
    from cli import ui

    if not profile_exists(name):
        ui.print_error(f"Profile '{name}' not found")
        return None

    # Generate filename if not provided
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = str(get_backups_dir() / f"{name}_{timestamp}.tar.gz")

    profile_dir = get_profile_dir(name)

    ui.print_info(f"Exporting profile '{name}'...")

    # Create tar.gz archive
    try:
        with tarfile.open(output_file, "w:gz") as tar:
            # Add profile files
            for item in profile_dir.iterdir():
                if item.is_file():
                    tar.add(item, arcname=item.name)
                elif item.is_dir() and item.name not in (".", ".."):
                    tar.add(item, arcname=item.name)

        ui.print_success(f"Profile exported to: {output_file}")
        return output_file
    except Exception as e:
        ui.print_error(f"Export failed: {e}")
        return None


def import_profile(input_file: str, name: str = None) -> bool:
    """Import profile from tar.gz archive.

    Args:
        input_file: Input archive path
        name: Target profile name (extracted from archive if None)

    Returns:
        True if successful
    """
    from cli import ui

    input_path = Path(input_file)
    if not input_path.exists():
        ui.print_error(f"Archive not found: {input_file}")
        return False

    # Extract name from archive if not provided
    if not name:
        name = input_path.stem.replace(".tar.gz", "").rsplit("_", 1)[0]

    # Check if profile already exists
    if profile_exists(name):
        ui.print_warning(f"Profile '{name}' already exists")
        response = input("Overwrite? (yes/no): ")
        if response.lower() not in ("yes", "y"):
            ui.print_info("Import cancelled")
            return False
        # Remove existing profile
        if name != "default":
            shutil.rmtree(get_profiles_dir() / name)

    # Create profile directory
    target_dir = get_profile_dir(name)
    target_dir.mkdir(parents=True, exist_ok=True)

    ui.print_info(f"Importing profile '{name}'...")

    try:
        with tarfile.open(input_path, "r:gz") as tar:
            # Extract all files
            tar.extractall(target_dir)

        # Load and update metadata
        metadata = load_metadata(name)
        metadata["imported_at"] = datetime.now().isoformat()
        metadata["imported_from"] = str(input_path)
        save_metadata(name, metadata)

        ui.print_success(f"Profile '{name}' imported from: {input_file}")
        return True
    except Exception as e:
        ui.print_error(f"Import failed: {e}")
        if name != "default":
            shutil.rmtree(target_dir)
        return False


def backup_profile(name: str) -> str:
    """Create a backup of a profile.

    Args:
        name: Profile name

    Returns:
        Backup file path
    """
    from cli import ui

    # Create backup with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{name}_{timestamp}.tar.gz"
    backup_path = str(get_backups_dir() / backup_name)

    return export_profile(name, backup_path)


def restore_backup(backup_file: str, name: str = None) -> bool:
    """Restore a profile from backup.

    Args:
        backup_file: Backup file path
        name: Target profile name

    Returns:
        True if successful
    """
    from cli import ui

    if not name:
        # Extract name from backup filename
        backup_path = Path(backup_file)
        name = backup_path.stem.replace(".tar.gz", "").rsplit("_", 1)[0]

    return import_profile(backup_file, name)


# =============================================================================
# CLI Commands
# =============================================================================

def profile_list():
    """List all profiles with details."""
    from cli import ui

    profiles = list_profiles()
    current = get_current_profile()

    ui.print_header("Available Profiles")

    for profile in profiles:
        name = profile["name"]
        metadata = profile.get("metadata", {})

        marker = " ← current" if name == current else ""
        description = metadata.get("description", "")
        tags = metadata.get("tags", [])

        print(f"\n  • {name}{marker}")
        if description:
            print(f"    {description}")
        if tags:
            print(f"    Tags: {', '.join(tags)}")


def profile_info(name: str):
    """Show detailed profile information.

    Args:
        name: Profile name
    """
    from cli import ui

    if not profile_exists(name):
        ui.print_error(f"Profile '{name}' not found")
        return

    profile_dir = get_profile_dir(name)
    metadata = load_metadata(name)

    ui.print_header(f"Profile: {name}")

    print(f"\n  Path: {profile_dir}")
    print(f"  Created: {metadata.get('created_at', 'unknown')}")

    if metadata.get("copied_from"):
        print(f"  Copied from: {metadata['copied_from']}")
    if metadata.get("renamed_from"):
        print(f"  Renamed from: {metadata['renamed_from']}")
    if metadata.get("imported_from"):
        print(f"  Imported from: {metadata['imported_from']}")

    print(f"\n  Description:")
    desc = metadata.get("description", "No description")
    print(f"    {desc}")

    tags = metadata.get("tags", [])
    if tags:
        print(f"\n  Tags: {', '.join(tags)}")

    # List files
    print(f"\n  Files:")
    for item in profile_dir.iterdir():
        if not item.name.startswith("."):
            print(f"    - {item.name}")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "list":
            profile_list()

        elif command == "info" and len(sys.argv) > 2:
            profile_info(sys.argv[2])

        elif command == "create" and len(sys.argv) > 2:
            copy_from = sys.argv[3] if len(sys.argv) > 3 else "default"
            create_profile(sys.argv[2], copy_from)

        elif command == "delete" and len(sys.argv) > 2:
            delete_profile(sys.argv[2])

        elif command == "use" and len(sys.argv) > 2:
            switch_profile(sys.argv[2])

        elif command == "rename" and len(sys.argv) > 3:
            rename_profile(sys.argv[2], sys.argv[3])

        elif command == "export" and len(sys.argv) > 2:
            export_profile(sys.argv[2])

        elif command == "import" and len(sys.argv) > 2:
            name = sys.argv[3] if len(sys.argv) > 3 else None
            import_profile(sys.argv[2], name)

        elif command == "backup" and len(sys.argv) > 2:
            backup_profile(sys.argv[2])

        elif command == "restore" and len(sys.argv) > 2:
            name = sys.argv[3] if len(sys.argv) > 3 else None
            restore_backup(sys.argv[2], name)

        else:
            print("Usage:")
            print("  handsome profile list")
            print("  handsome profile info <name>")
            print("  handsome profile create <name> [copy_from]")
            print("  handsome profile delete <name>")
            print("  handsome profile use <name>")
            print("  handsome profile rename <old> <new>")
            print("  handsome profile export <name> [file]")
            print("  handsome profile import <file> [name]")
            print("  handsome profile backup <name>")
            print("  handsome profile restore <file> [name]")