#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skills Sync - Manifest-based seeding and updating of bundled skills.

Copies bundled skills from the repo's skills/ directory into
~/.handsome_agent/skills/ and uses a manifest to track which skills
have been synced and their origin hash.

Manifest format (v2): each line is "skill_name:origin_hash" where origin_hash
is the MD5 of the bundled skill at the time it was last synced to the user dir.
Old v1 manifests (plain names without hashes) are auto-migrated.

Update logic:
  - NEW skills (not in manifest): copied to user dir, origin hash recorded.
  - EXISTING skills (in manifest, present in user dir):
      * If user copy matches origin hash: user hasn't modified it -> safe to
        update from bundled if bundled changed. New origin hash recorded.
      * If user copy differs from origin hash: user customized it -> SKIP.
  - DELETED by user (in manifest, absent from user dir): respected, not re-added.
  - REMOVED from bundled (in manifest, gone from repo): cleaned from manifest.

The manifest lives at ~/.handsome_agent/skills/.bundled_manifest.

Functions:
  - sync_from_hub(): Hub sync functionality
  - backup_skills(): Backup all skills to backup directory
  - restore_skills(backup_id): Restore from backup
  - check_updates(): Check for updatable skills
  - reset_bundled_skill(name, restore): Reset bundled skill
"""

import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from common.logging_manager import get_execution_logger
from tools.skill_manager_tool import get_skills_dir


logger = get_execution_logger("SkillsSync")

# Manifest file name
MANIFEST_FILE = ".bundled_manifest"

# Backup directory name
BACKUP_DIR = "skill_backups"


def _get_manifest_path() -> Path:
    """Get manifest file path."""
    return get_skills_dir() / MANIFEST_FILE


def _get_backup_dir() -> Path:
    """Get backup directory path."""
    return Path.home() / ".handsome_agent" / BACKUP_DIR


def _get_bundled_dir() -> Path:
    """Locate the bundled skills/ directory.

    Checks HANDSOME_BUNDLED_SKILLS env var first, then falls back to
    the relative path from this source file.
    """
    env_path = os.environ.get("HANDSOME_BUNDLED_SKILLS")
    if env_path:
        return Path(env_path)

    # Fall back to the skills directory relative to project root
    project_root = Path(__file__).parent.parent
    bundled_dir = project_root / "skills"
    return bundled_dir


def _read_manifest() -> Dict[str, str]:
    """
    Read the manifest as a dict of {skill_name: origin_hash}.

    Handles both v1 (plain names) and v2 (name:hash) formats.
    v1 entries get an empty hash string which triggers migration on next sync.
    """
    manifest_path = _get_manifest_path()
    if not manifest_path.exists():
        return {}

    try:
        result = {}
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            if ":" in line:
                # v2 format: name:hash
                name, _, hash_val = line.partition(":")
                result[name.strip()] = hash_val.strip()
            else:
                # v1 format: plain name — empty hash triggers migration
                result[line] = ""
        return result
    except (OSError, IOError):
        return {}


def _write_manifest(entries: Dict[str, str]) -> None:
    """Write the manifest file atomically in v2 format (name:hash).

    Uses a temp file + os.replace() to avoid corruption if the process
    crashes or is interrupted mid-write.
    """
    manifest_path = _get_manifest_path()
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    data = "\n".join(
        f"{name}:{hash_val}" for name, hash_val in sorted(entries.items())
    ) + "\n"

    try:
        fd, tmp_path = tempfile.mkstemp(
            dir=str(manifest_path.parent),
            prefix=".bundled_manifest_",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            _atomic_replace(Path(tmp_path), manifest_path)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    except Exception as e:
        logger.error("Failed to write skills manifest %s: %s", manifest_path, e)


def _atomic_replace(tmp_path: Path, target_path: Path) -> None:
    """Atomically replace target_path with tmp_path."""
    try:
        if os.name == "nt":
            os.replace(str(tmp_path), str(target_path))
        else:
            os.rename(str(tmp_path), str(target_path))
    except Exception as e:
        logger.error("Atomic replace failed: %s", e)
        raise


def _read_skill_name(skill_md: Path, fallback: str) -> str:
    """Read the name field from SKILL.md YAML frontmatter, falling back to fallback."""
    try:
        content = skill_md.read_text(encoding="utf-8", errors="replace")[:4000]
    except OSError:
        return fallback

    in_frontmatter = False
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped == "---":
            if in_frontmatter:
                break
            in_frontmatter = True
            continue
        if in_frontmatter and stripped.startswith("name:"):
            value = stripped.split(":", 1)[1].strip().strip("\"'")
            if value:
                return value
    return fallback


def _discover_bundled_skills(bundled_dir: Path) -> List[Tuple[str, Path]]:
    """
    Find all SKILL.md files in the bundled directory.
    Returns list of (skill_name, skill_directory_path) tuples.
    """
    skills = []
    if not bundled_dir.exists():
        return skills

    for skill_md in bundled_dir.rglob("SKILL.md"):
        # Skip hidden directories
        if any(part.startswith(".") for part in skill_md.parts):
            continue
        skill_dir = skill_md.parent
        skill_name = _read_skill_name(skill_md, skill_dir.name)
        skills.append((skill_name, skill_dir))

    return skills


def _compute_relative_dest(skill_dir: Path, bundled_dir: Path) -> Path:
    """
    Compute the destination path in SKILLS_DIR preserving the category structure.
    e.g., bundled/skills/mlops/axolotl -> ~/.handsome_agent/skills/mlops/axolotl
    """
    rel = skill_dir.relative_to(bundled_dir)
    return get_skills_dir() / rel


def _dir_hash(directory: Path) -> str:
    """Compute a hash of all file contents in a directory for change detection."""
    hasher = hashlib.md5()
    try:
        for fpath in sorted(directory.rglob("*")):
            if fpath.is_file():
                rel = fpath.relative_to(directory)
                hasher.update(str(rel).encode("utf-8"))
                hasher.update(fpath.read_bytes())
    except (OSError, IOError):
        pass
    return hasher.hexdigest()


def _is_excluded_skill_path(skill_path: Path) -> bool:
    """Check if a skill path should be excluded from sync."""
    excluded_names = {"__pycache__", ".git", ".pytest_cache", "node_modules"}
    return any(part in excluded_names for part in skill_path.parts)


def sync_from_hub(quiet: bool = False) -> dict:
    """
    Sync bundled skills into ~/.handsome_agent/skills/ using the manifest.

    Returns:
        dict with keys: copied (list), updated (list), skipped (int),
                        user_modified (list), cleaned (list), total_bundled (int)
    """
    bundled_dir = _get_bundled_dir()
    if not bundled_dir.exists():
        logger.warning("Bundled skills directory not found: %s", bundled_dir)
        return {
            "copied": [],
            "updated": [],
            "skipped": 0,
            "user_modified": [],
            "cleaned": [],
            "total_bundled": 0,
        }

    skills_dir = get_skills_dir()
    skills_dir.mkdir(parents=True, exist_ok=True)

    manifest = _read_manifest()
    bundled_skills = _discover_bundled_skills(bundled_dir)
    bundled_names = {name for name, _ in bundled_skills}

    copied = []
    updated = []
    user_modified = []
    skipped = 0

    for skill_name, skill_src in bundled_skills:
        dest = _compute_relative_dest(skill_src, bundled_dir)
        bundled_hash = _dir_hash(skill_src)

        if skill_name not in manifest:
            # ── New skill — never offered before ──
            try:
                if dest.exists():
                    # User already has a skill with the same name
                    skipped += 1
                    if _dir_hash(dest) == bundled_hash:
                        manifest[skill_name] = bundled_hash
                    elif not quiet:
                        logger.warning(
                            "Skill '%s': bundled version exists but you already "
                            "have a local skill by this name — yours was kept.",
                            skill_name,
                        )
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(skill_src, dest)
                    copied.append(skill_name)
                    manifest[skill_name] = bundled_hash
                    if not quiet:
                        logger.info("+ %s", skill_name)
            except (OSError, IOError) as e:
                if not quiet:
                    logger.error("Failed to copy %s: %s", skill_name, e)

        elif dest.exists():
            # ── Existing skill — in manifest AND on disk ──
            origin_hash = manifest.get(skill_name, "")
            user_hash = _dir_hash(dest)

            if not origin_hash:
                # v1 migration: no origin hash recorded
                manifest[skill_name] = user_hash
                skipped += 1
                continue

            if user_hash != origin_hash:
                # User modified this skill — don't overwrite their changes
                user_modified.append(skill_name)
                if not quiet:
                    logger.info("~ %s (user-modified, skipping)", skill_name)
                continue

            # User copy matches origin — check if bundled has a newer version
            if bundled_hash != origin_hash:
                try:
                    # Move old copy to a backup so we can restore on failure
                    backup = dest.with_suffix(".bak")
                    shutil.move(str(dest), str(backup))
                    try:
                        shutil.copytree(skill_src, dest)
                        manifest[skill_name] = bundled_hash
                        updated.append(skill_name)
                        if not quiet:
                            logger.info("^ %s (updated)", skill_name)
                        # Remove backup after successful copy
                        shutil.rmtree(backup, ignore_errors=True)
                    except (OSError, IOError):
                        # Restore from backup
                        if backup.exists() and not dest.exists():
                            shutil.move(str(backup), str(dest))
                        raise
                except (OSError, IOError) as e:
                    if not quiet:
                        logger.error("Failed to update %s: %s", skill_name, e)
            else:
                skipped += 1  # bundled unchanged, user unchanged

        else:
            # ── In manifest but not on disk — user deleted it ──
            skipped += 1

    # Clean stale manifest entries (skills removed from bundled dir)
    cleaned = sorted(set(manifest.keys()) - bundled_names)
    for name in cleaned:
        del manifest[name]

    # Also copy skill.md/skill.py files for categories (if not already present)
    for desc_md in bundled_dir.rglob("*.md"):
        if _is_excluded_skill_path(desc_md):
            continue
        rel = desc_md.relative_to(bundled_dir)
        dest_desc = skills_dir / rel
        if not dest_desc.exists():
            try:
                dest_desc.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(desc_md, dest_desc)
            except (OSError, IOError) as e:
                logger.debug("Could not copy %s: %s", desc_md, e)

    _write_manifest(manifest)

    return {
        "copied": copied,
        "updated": updated,
        "skipped": skipped,
        "user_modified": user_modified,
        "cleaned": cleaned,
        "total_bundled": len(bundled_skills),
    }


def backup_skills(quiet: bool = False) -> dict:
    """
    Backup all skills to the backup directory.

    Returns:
        dict with keys: backup_id (str), path (str), skill_count (int),
                        timestamp (str), skills (list of skill names)
    """
    skills_dir = get_skills_dir()
    backup_dir = _get_backup_dir()
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Create a timestamped backup directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_id = f"backup_{timestamp}"
    backup_path = backup_dir / backup_id

    # Collect all skills
    skills_to_backup = []
    if skills_dir.exists():
        for skill_md in skills_dir.rglob("SKILL.md"):
            if _is_excluded_skill_path(skill_md):
                continue
            skill_dir = skill_md.parent
            skill_name = _read_skill_name(skill_md, skill_dir.name)
            skills_to_backup.append(skill_name)

    # Create backup
    try:
        backup_path.mkdir(parents=True, exist_ok=True)

        for skill_md in skills_dir.rglob("SKILL.md"):
            if _is_excluded_skill_path(skill_md):
                continue
            skill_dir = skill_md.parent
            rel_path = skill_dir.relative_to(skills_dir)
            dest_path = backup_path / rel_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(skill_dir, dest_path)

        if not quiet:
            logger.info(
                "Backed up %d skills to %s", len(skills_to_backup), backup_path
            )

        return {
            "success": True,
            "backup_id": backup_id,
            "path": str(backup_path),
            "skill_count": len(skills_to_backup),
            "timestamp": timestamp,
            "skills": skills_to_backup,
        }
    except (OSError, IOError) as e:
        logger.error("Failed to backup skills: %s", e)
        return {
            "success": False,
            "error": str(e),
            "backup_id": backup_id,
            "path": str(backup_path),
        }


def restore_skills(backup_id: str, quiet: bool = False) -> dict:
    """
    Restore skills from a backup.

    Args:
        backup_id: The backup ID (directory name under backup_dir)

    Returns:
        dict with keys: success (bool), restored (list), message (str)
    """
    backup_dir = _get_backup_dir()
    backup_path = backup_dir / backup_id

    if not backup_path.exists():
        return {
            "success": False,
            "error": f"Backup not found: {backup_id}",
            "restored": [],
        }

    skills_dir = get_skills_dir()
    skills_dir.mkdir(parents=True, exist_ok=True)

    restored = []
    failed = []

    try:
        for item in backup_path.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                dest = skills_dir / item.name
                try:
                    if dest.exists():
                        # Backup existing skill first
                        backup_existing = dest.with_suffix(".bak.restore")
                        if backup_existing.exists():
                            shutil.rmtree(backup_existing)
                        shutil.move(str(dest), str(backup_existing))

                    shutil.copytree(item, dest)
                    restored.append(item.name)
                except (OSError, IOError) as e:
                    failed.append({"skill": item.name, "error": str(e)})

        message = f"Restored {len(restored)} skills from backup '{backup_id}'"
        if failed:
            message += f", {len(failed)} failed"

        if not quiet:
            if failed:
                logger.warning(message)
            else:
                logger.info(message)

        return {
            "success": len(failed) == 0,
            "restored": restored,
            "failed": failed,
            "message": message,
        }
    except (OSError, IOError) as e:
        logger.error("Failed to restore skills: %s", e)
        return {"success": False, "error": str(e), "restored": restored}


def list_backups() -> dict:
    """
    List all available backups.

    Returns:
        dict with keys: backups (list of backup info dicts)
    """
    backup_dir = _get_backup_dir()
    backups = []

    if backup_dir.exists():
        for item in sorted(backup_dir.iterdir(), reverse=True):
            if item.is_dir() and item.name.startswith("backup_"):
                # Count skills in backup
                skill_count = sum(
                    1 for f in item.rglob("SKILL.md")
                    if not _is_excluded_skill_path(f)
                )

                # Get timestamp from backup name
                timestamp = item.name.replace("backup_", "")

                backups.append({
                    "id": item.name,
                    "path": str(item),
                    "skill_count": skill_count,
                    "timestamp": timestamp,
                })

    return {"success": True, "backups": backups}


def check_updates(quiet: bool = False) -> dict:
    """
    Check for updatable skills.

    Returns:
        dict with keys: updatable (list of skill names with updates),
                        user_modified (list), up_to_date (list),
                        total_bundled (int)
    """
    bundled_dir = _get_bundled_dir()
    if not bundled_dir.exists():
        return {
            "updatable": [],
            "user_modified": [],
            "up_to_date": [],
            "total_bundled": 0,
        }

    manifest = _read_manifest()
    bundled_skills = _discover_bundled_skills(bundled_dir)
    skills_dir = get_skills_dir()

    updatable = []
    user_modified = []
    up_to_date = []

    for skill_name, skill_src in bundled_skills:
        dest = _compute_relative_dest(skill_src, bundled_dir)
        bundled_hash = _dir_hash(skill_src)

        if skill_name not in manifest:
            updatable.append(skill_name)
        elif dest.exists():
            origin_hash = manifest.get(skill_name, "")
            user_hash = _dir_hash(dest)

            if not origin_hash:
                # v1 migration, can't determine
                continue

            if user_hash != origin_hash:
                user_modified.append(skill_name)
            elif bundled_hash != origin_hash:
                updatable.append(skill_name)
            else:
                up_to_date.append(skill_name)

    if not quiet:
        logger.info(
            "Update check: %d updatable, %d user-modified, %d up-to-date",
            len(updatable),
            len(user_modified),
            len(up_to_date),
        )

    return {
        "updatable": updatable,
        "user_modified": user_modified,
        "up_to_date": up_to_date,
        "total_bundled": len(bundled_skills),
    }


def reset_bundled_skill(name: str, restore: bool = False) -> dict:
    """
    Reset a bundled skill's manifest tracking so future syncs work normally.

    When a user edits a bundled skill, subsequent syncs mark it as
    ``user_modified`` and skip it forever — even if the user later copies
    the bundled version back into place, because the manifest still holds
    the *old* origin hash. This function breaks that loop.

    Args:
        name: The skill name (matches the manifest key / skill frontmatter name).
        restore: If True, also delete the user's copy in SKILLS_DIR and let
                 the next sync re-copy the current bundled version. If False
                 (default), only clear the manifest entry — the user's
                 current copy is preserved but future updates work again.

    Returns:
        dict with keys:
          - ok: bool, whether the reset succeeded
          - action: one of "manifest_cleared", "restored", "not_in_manifest",
                    "bundled_missing"
          - message: human-readable description
          - synced: dict from sync_from_hub() if a sync was triggered, else None
    """
    manifest = _read_manifest()
    bundled_dir = _get_bundled_dir()
    bundled_skills = _discover_bundled_skills(bundled_dir)
    bundled_by_name = dict(bundled_skills)

    in_manifest = name in manifest
    is_bundled = name in bundled_by_name

    if not in_manifest and not is_bundled:
        return {
            "ok": False,
            "action": "not_in_manifest",
            "message": (
                f"'{name}' is not a tracked bundled skill. Nothing to reset."
            ),
            "synced": None,
        }

    # Step 1: drop the manifest entry so next sync treats it as new
    if in_manifest:
        del manifest[name]
        _write_manifest(manifest)

    # Step 2 (optional): delete the user's copy so next sync re-copies bundled
    deleted_user_copy = False
    if restore:
        if not is_bundled:
            return {
                "ok": False,
                "action": "bundled_missing",
                "message": (
                    f"'{name}' has no bundled source — manifest entry cleared "
                    f"but cannot restore from bundled (skill was removed upstream)."
                ),
                "synced": None,
            }
        # The destination mirrors the bundled path relative to bundled_dir.
        dest = _compute_relative_dest(bundled_by_name[name], bundled_dir)
        if dest.exists():
            try:
                shutil.rmtree(dest)
                deleted_user_copy = True
            except (OSError, IOError) as e:
                return {
                    "ok": False,
                    "action": "manifest_cleared",
                    "message": (
                        f"Cleared manifest entry for '{name}' but could not "
                        f"delete user copy at {dest}: {e}"
                    ),
                    "synced": None,
                }

    # Step 3: run sync to re-baseline (or re-copy if we deleted)
    synced = sync_from_hub(quiet=True)

    if restore and deleted_user_copy:
        action = "restored"
        message = f"Restored '{name}' from bundled source."
    elif restore:
        action = "restored"
        message = (
            f"Restored '{name}' (no prior user copy, re-copied from bundled)."
        )
    else:
        action = "manifest_cleared"
        message = (
            f"Cleared manifest entry for '{name}'. Future sync runs "
            f"will re-baseline against your current copy and accept upstream "
            f"changes."
        )

    return {"ok": True, "action": action, "message": message, "synced": synced}


if __name__ == "__main__":
    print("Syncing bundled skills into ~/.handsome_agent/skills/ ...")
    result = sync_from_hub(quiet=False)
    parts = [
        f"{len(result['copied'])} new",
        f"{len(result['updated'])} updated",
        f"{result['skipped']} unchanged",
    ]
    if result["user_modified"]:
        names = result["user_modified"]
        max_show = 5
        shown = ", ".join(names[:max_show])
        if len(names) > max_show:
            shown += f", +{len(names) - max_show} more"
        parts.append(f"{len(names)} user-modified (kept): {shown}")
    if result["cleaned"]:
        parts.append(f"{len(result['cleaned'])} cleaned from manifest")
    print(f"\nDone: {', '.join(parts)}. {result['total_bundled']} total bundled.")