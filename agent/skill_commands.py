#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill Commands - Shared slash command helpers for skills.

🧠 Decision - 📋 Skills - 技能命令处理

参考 Hermes 的 agent/skill_commands.py 设计，提供：
- 技能加载和激活
- 斜杠命令注册
- 模板变量替换

与 CLI (cli/skills_cli.py) 共享，以便两者都可以通过 /skill-name 命令调用技能。
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

from agent.skill_preprocessing import substitute_template_vars

# Skill command registry
_skill_commands: Dict[str, Dict[str, Any]] = {}
_skill_commands_platform: Optional[str] = None

# Patterns for sanitizing skill names
_SKILL_INVALID_CHARS = re.compile(r"[^a-z0-9-]")
_SKILL_MULTI_HYPHEN = re.compile(r"-{2,}")


def _sanitize_skill_name(name: str) -> str:
    """Convert a skill name to a clean hyphen-separated slug."""
    slug = name.lower().strip()
    slug = _SKILL_INVALID_CHARS.sub("-", slug)
    slug = _SKILL_MULTI_HYPHEN.sub("-", slug)
    return slug.strip("-")


def _get_skills_dir() -> Path:
    """Get the skills directory."""
    return Path(__file__).parent.parent / "skills"


def load_skill(skill_identifier: str, task_id: str | None = None) -> Optional[Dict[str, Any]]:
    """Load a skill by name/path.

    Args:
        skill_identifier: Skill name or path
        task_id: Optional task ID

    Returns:
        Loaded skill dict or None
    """
    from tools.skills_tool import skill_view

    raw_identifier = (skill_identifier or "").strip()
    if not raw_identifier:
        return None

    try:
        normalized = raw_identifier.lstrip("/")
        loaded_skill = json.loads(
            skill_view(normalized, task_id=task_id)
        )
    except Exception as e:
        logger.warning(f"Failed to load skill '{skill_identifier}': {e}")
        return None

    if not loaded_skill.get("success"):
        return None

    return loaded_skill


def get_skill_commands() -> Dict[str, Dict[str, Any]]:
    """Get all available skill slash commands.

    Returns:
        Dict mapping slash command names to skill info
    """
    global _skill_commands, _skill_commands_platform

    skills_dir = _get_skills_dir()

    # Check if we need to rebuild the cache
    current_platform = _resolve_platform()
    if _skill_commands and _skill_commands_platform == current_platform:
        return _skill_commands

    # Rebuild cache
    _skill_commands = {}
    _skill_commands_platform = current_platform

    if not skills_dir.exists():
        return _skill_commands

    # Scan skills directories
    for skill_path in skills_dir.rglob("SKILL.md"):
        try:
            skill_dir = skill_path.parent
            skill_name = skill_dir.name

            # Skip hidden directories
            if skill_name.startswith("."):
                continue

            # Parse frontmatter
            content = skill_path.read_text(encoding="utf-8")
            frontmatter = _parse_frontmatter(content)

            # Check if disabled for this platform
            if current_platform:
                disabled_platforms = frontmatter.get("disabled_platforms", [])
                if current_platform in disabled_platforms:
                    continue

            # Get activation command
            slash_cmd = frontmatter.get("slash_command") or f"skill-{_sanitize_skill_name(skill_name)}"

            _skill_commands[slash_cmd] = {
                "name": skill_name,
                "path": str(skill_dir.relative_to(skills_dir)),
                "description": frontmatter.get("description", ""),
                "category": frontmatter.get("category", "general"),
                "author": frontmatter.get("author", ""),
                "version": frontmatter.get("version", "1.0.0"),
            }
        except Exception as e:
            logger.debug(f"Failed to load skill at {skill_path}: {e}")

    return _skill_commands


def _resolve_platform() -> Optional[str]:
    """Resolve the current platform scope."""
    return os.getenv("HANDSOME_PLATFORM") or None


def _parse_frontmatter(content: str) -> Dict[str, Any]:
    """Parse YAML frontmatter from skill content.

    委托给 agent.skill_utils 中的统一实现。

    Args:
        content: Raw skill content

    Returns:
        Dict of frontmatter values
    """
    from agent.skill_utils import parse_frontmatter
    fm, _ = parse_frontmatter(content)
    return fm


def build_skill_message(
    loaded_skill: Dict[str, Any],
    skill_dir: Optional[Path],
    user_instruction: str = "",
) -> str:
    """Format a loaded skill into a message payload.

    Args:
        loaded_skill: Loaded skill dict
        skill_dir: Skill directory path
        user_instruction: Optional user instruction

    Returns:
        Formatted skill message
    """
    content = str(loaded_skill.get("content") or "")

    # Template substitution using unified preprocessing
    content = substitute_template_vars(content, skill_dir)

    parts = [content.strip()]

    # Add skill directory info
    if skill_dir:
        parts.append("")
        parts.append(f"[Skill directory: {skill_dir}]")
        parts.append("Resolve any relative paths against that directory.")

    if user_instruction:
        parts.append("")
        parts.append(f"User instruction: {user_instruction}")

    return "\n".join(parts)


def activate_skill(skill_name: str, user_instruction: str = "") -> Optional[str]:
    """Activate a skill and return the formatted message.

    Args:
        skill_name: Skill name
        user_instruction: Optional user instruction

    Returns:
        Formatted skill message or None
    """
    loaded_skill = load_skill(skill_name)
    if not loaded_skill:
        return None

    skill_path = loaded_skill.get("path", "")
    skill_dir = _get_skills_dir() / Path(skill_path).parent if skill_path else None

    return build_skill_message(loaded_skill, skill_dir, user_instruction)


# =============================================================================
# Skill Registry
# =============================================================================

def register_skill_command(
    name: str,
    handler: callable,
    description: str = "",
    category: str = "general",
):
    """Register a skill as a slash command.

    Args:
        name: Slash command name (without leading slash)
        handler: Handler function
        description: Command description
        category: Command category
    """
    global _skill_commands

    slash_cmd = f"/{name}" if not name.startswith("/") else name

    _skill_commands[slash_cmd] = {
        "name": name,
        "handler": handler,
        "description": description,
        "category": category,
    }


def get_skill_info(skill_name: str) -> Optional[Dict[str, Any]]:
    """Get information about a skill.

    Args:
        skill_name: Skill name

    Returns:
        Skill info dict or None
    """
    commands = get_skill_commands()

    # Try exact match
    if skill_name in commands:
        return commands[skill_name]

    # Try with prefix
    for name, info in commands.items():
        if name.endswith(skill_name) or info.get("name") == skill_name:
            return info

    return None


def resolve_command(command: str) -> Optional[Dict[str, Any]]:
    """解析命令，优先检查 Bundle，然后检查 Skill

    Args:
        command: 命令名称（可能有 / 前缀）

    Returns:
        {"type": "bundle", "key": "/slug"} 或 {"type": "skill", "key": "/slug"}
        或 None
    """
    # 优先检查 Bundle
    try:
        from agent.skill_workflows import resolve_bundle_command_key
        bundle_key = resolve_bundle_command_key(command)
        if bundle_key:
            return {"type": "bundle", "key": bundle_key}
    except ImportError:
        pass

    # 检查 Skill
    key = resolve_skill_command_key(command)
    if key:
        return {"type": "skill", "key": key}

    return None


def execute_command(command: str, user_instruction: str = "", task_id: Optional[str] = None) -> Optional[str]:
    """执行命令，自动路由到 Bundle 或 Skill

    Args:
        command: 命令名称
        user_instruction: 用户指令
        task_id: 可选的 task ID

    Returns:
        格式化消息或 None
    """
    result = resolve_command(command)
    if not result:
        return None

    if result["type"] == "bundle":
        try:
            from agent.skill_workflows import build_bundle_invocation_message
            bundle_result = build_bundle_invocation_message(
                result["key"],
                user_instruction=user_instruction,
                task_id=task_id,
            )
            if bundle_result and bundle_result.success:
                return bundle_result.message
        except ImportError:
            pass

    elif result["type"] == "skill":
        from agent.skill_commands import activate_skill
        return activate_skill(result["key"], user_instruction)

    return None


def list_skills_by_category() -> Dict[str, list]:
    """List all skills grouped by category.

    Returns:
        Dict mapping categories to skill lists
    """
    commands = get_skill_commands()
    categories: Dict[str, list] = {}

    for name, info in commands.items():
        category = info.get("category", "general")
        if category not in categories:
            categories[category] = []
        categories[category].append(info)

    return categories


if __name__ == "__main__":
    # Test
    print("Available skill commands:")
    commands = get_skill_commands()
    for name, info in commands.items():
        print(f"  /{name}: {info.get('description', '')} [{info.get('category')}]")