#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill Utils - Skill utility functions.

🧠 Decision - 📋 Skills - 技能工具函数

参考 Hermes 的 agent/skill_utils.py 设计，提供：
- 前端解析
- 配置变量提取
- 外部技能目录管理
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter from skill content.

    Args:
        content: Raw skill content

    Returns:
        Tuple of (frontmatter dict, body content)
    """
    import yaml

    lines = content.split("\n")

    if len(lines) < 3 or lines[0].strip() != "---":
        return {}, content

    # Find closing ---
    end_idx = None
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        return {}, content

    try:
        frontmatter = yaml.safe_load("\n".join(lines[1:end_idx]))
        if not isinstance(frontmatter, dict):
            frontmatter = {}
    except Exception:
        frontmatter = {}

    body = "\n".join(lines[end_idx + 1:]).strip()

    return frontmatter, body


def extract_skill_config_vars(frontmatter: Dict[str, Any]) -> List[str]:
    """Extract skill config variable names from frontmatter.

    Args:
        frontmatter: Frontmatter dict

    Returns:
        List of config variable names
    """
    config_vars = []

    # Look for config in metadata
    metadata = frontmatter.get("metadata", {})
    if isinstance(metadata, dict):
        config = metadata.get("config", {})
        if isinstance(config, dict):
            config_vars.extend(config.keys())

    # Also check top-level config
    config = frontmatter.get("config", {})
    if isinstance(config, dict):
        config_vars.extend(config.keys())

    return list(set(config_vars))


def resolve_skill_config_values(config_vars: List[str]) -> Dict[str, str]:
    """Resolve skill config values from config file.

    Args:
        config_vars: List of config variable names

    Returns:
        Dict mapping variable names to resolved values
    """
    from common.config import get_config_value

    resolved = {}
    for var in config_vars:
        value = get_config_value(f"skills.{var}")
        if value is not None:
            resolved[var] = value

    return resolved


def get_external_skills_dirs() -> List[Path]:
    """Get list of external skills directories.

    Returns:
        List of Path objects
    """
    from common.config import load_config

    config = load_config()
    external_dirs = config.get("skills", {}).get("external_dirs", [])

    dirs = []
    for dir_path in external_dirs:
        path = Path(dir_path).expanduser()
        if path.exists():
            dirs.append(path)

    return dirs


def get_skill_by_name(skill_name: str) -> Optional[Dict[str, Any]]:
    """Get skill info by name.

    Args:
        skill_name: Skill name

    Returns:
        Skill info dict or None
    """
    from tools.skills_tool import skill_view
    import json

    try:
        result = json.loads(skill_view(skill_name))
        if result.get("success"):
            return result
    except Exception:
        pass

    return None


def get_all_skills() -> List[Dict[str, Any]]:
    """Get all available skills.

    Returns:
        List of skill info dicts
    """
    from tools.skills_tool import list_skills
    return list_skills()


def get_skills_by_category(category: str) -> List[Dict[str, Any]]:
    """Get skills in a specific category.

    Args:
        category: Category name

    Returns:
        List of skill info dicts
    """
    skills = get_all_skills()
    return [s for s in skills if s.get("category") == category]


def search_skills(query: str) -> List[Dict[str, Any]]:
    """Search skills by name or description.

    Args:
        query: Search query

    Returns:
        List of matching skills
    """
    skills = get_all_skills()
    query_lower = query.lower()

    results = []
    for skill in skills:
        name = skill.get("name", "").lower()
        desc = skill.get("description", "").lower()

        if query_lower in name or query_lower in desc:
            results.append(skill)

    return results


def validate_skill(skill_path: Path) -> Tuple[bool, List[str]]:
    """Validate a skill directory.

    Args:
        skill_path: Path to skill directory

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []

    # Check if directory exists
    if not skill_path.exists():
        return False, ["Skill directory does not exist"]

    # Check for SKILL.md
    skill_file = skill_path / "SKILL.md"
    if not skill_file.exists():
        errors.append("SKILL.md not found")

    # Check frontmatter
    if skill_file.exists():
        try:
            content = skill_file.read_text(encoding="utf-8")
            frontmatter, body = parse_frontmatter(content)

            if not frontmatter.get("name"):
                errors.append("Frontmatter missing 'name' field")

            if not body.strip():
                errors.append("SKILL.md has no content")

        except Exception as e:
            errors.append(f"Failed to parse SKILL.md: {e}")

    return len(errors) == 0, errors


def get_skill_commands() -> List[str]:
    """Get list of skill slash commands.

    Returns:
        List of slash command names
    """
    from agent.skill_commands import get_skill_commands as _get_cmds

    commands = _get_cmds()
    return list(commands.keys())


if __name__ == "__main__":
    # Test
    print("External skills dirs:", get_external_skills_dirs())
    print("\nAll skills:", get_all_skills())
    print("\nSkill commands:", get_skill_commands())