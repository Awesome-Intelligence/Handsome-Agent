#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skills Config - Skill configuration management.

🚪 Access - 💬 CLI - 技能配置

提供技能启用/禁用、优先级排序等配置管理功能。
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def get_config_path() -> Path:
    """Get the skills config file path."""
    config_dir = Path.home() / ".agent_z"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "skills_config.json"


def load_skills_config() -> Dict[str, Any]:
    """Load skills configuration.

    Returns:
        Skills config dict
    """
    config_path = get_config_path()
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return _default_config()


def save_skills_config(config: Dict[str, Any]):
    """Save skills configuration.

    Args:
        config: Skills config dict
    """
    config_path = get_config_path()
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def _default_config() -> Dict[str, Any]:
    """Get default skills configuration.

    Returns:
        Default config dict
    """
    return {
        "enabled_skills": [],
        "disabled_skills": [],
        "skill_priorities": {},
        "template_vars": {},
        "inline_shell": False,
        "inline_shell_timeout": 10,
    }


def get_enabled_skills() -> List[str]:
    """Get list of enabled skill names.

    Returns:
        List of enabled skill names
    """
    config = load_skills_config()
    return config.get("enabled_skills", [])


def get_disabled_skills() -> List[str]:
    """Get list of disabled skill names.

    Returns:
        List of disabled skill names
    """
    config = load_skills_config()
    return config.get("disabled_skills", [])


def enable_skill(skill_name: str):
    """Enable a skill.

    Args:
        skill_name: Skill name
    """
    config = load_skills_config()

    # Remove from disabled if present
    if skill_name in config.get("disabled_skills", []):
        config["disabled_skills"].remove(skill_name)

    # Add to enabled if not present
    if skill_name not in config.get("enabled_skills", []):
        config.setdefault("enabled_skills", []).append(skill_name)

    save_skills_config(config)


def disable_skill(skill_name: str):
    """Disable a skill.

    Args:
        skill_name: Skill name
    """
    config = load_skills_config()

    # Remove from enabled if present
    if skill_name in config.get("enabled_skills", []):
        config["enabled_skills"].remove(skill_name)

    # Add to disabled if not present
    if skill_name not in config.get("disabled_skills", []):
        config.setdefault("disabled_skills", []).append(skill_name)

    save_skills_config(config)


def is_skill_enabled(skill_name: str) -> bool:
    """Check if a skill is enabled.

    Args:
        skill_name: Skill name

    Returns:
        True if skill is enabled
    """
    config = load_skills_config()

    enabled = config.get("enabled_skills", [])
    disabled = config.get("disabled_skills", [])

    # If specific list is used, only enabled ones are allowed
    if enabled:
        return skill_name in enabled

    # Otherwise, only disabled ones are blocked
    return skill_name not in disabled


def set_skill_priority(skill_name: str, priority: int):
    """Set skill priority.

    Args:
        skill_name: Skill name
        priority: Priority value (higher = more preferred)
    """
    config = load_skills_config()
    config.setdefault("skill_priorities", {})[skill_name] = priority
    save_skills_config(config)


def get_skill_priority(skill_name: str) -> int:
    """Get skill priority.

    Args:
        skill_name: Skill name

    Returns:
        Priority value (default: 0)
    """
    config = load_skills_config()
    return config.get("skill_priorities", {}).get(skill_name, 0)


def get_template_vars() -> Dict[str, str]:
    """Get template variables.

    Returns:
        Dict of template variables
    """
    config = load_skills_config()
    return config.get("template_vars", {})


def set_template_var(key: str, value: str):
    """Set a template variable.

    Args:
        key: Variable name
        value: Variable value
    """
    config = load_skills_config()
    config.setdefault("template_vars", {})[key] = value
    save_skills_config(config)


def get_inline_shell_enabled() -> bool:
    """Check if inline shell expansion is enabled.

    Returns:
        True if enabled
    """
    config = load_skills_config()
    return config.get("inline_shell", False)


def set_inline_shell_enabled(enabled: bool, timeout: int = 10):
    """Set inline shell expansion settings.

    Args:
        enabled: Whether to enable
        timeout: Timeout in seconds
    """
    config = load_skills_config()
    config["inline_shell"] = enabled
    config["inline_shell_timeout"] = timeout
    save_skills_config(config)


# =============================================================================
# CLI Functions
# =============================================================================

def list_skills(only_installed: bool = False) -> List[Dict[str, Any]]:
    """List all available skills.

    Args:
        only_installed: Only show installed skills

    Returns:
        List of skill info dicts
    """
    try:
        from tools.skills_tool import list_skills as _list_tools
        skills = _list_tools()
    except ImportError:
        skills = []

    if only_installed:
        enabled = get_enabled_skills()
        if enabled:
            skills = [s for s in skills if s["name"] in enabled]

    return skills


def search_skills(query: str) -> List[Dict[str, Any]]:
    """Search for skills.

    Args:
        query: Search query

    Returns:
        List of matching skills
    """
    skills = list_skills()
    query_lower = query.lower()

    results = []
    for skill in skills:
        name = skill.get("name", "").lower()
        desc = skill.get("description", "").lower()
        category = skill.get("category", "").lower()

        if query_lower in name or query_lower in desc or query_lower in category:
            results.append(skill)

    return results


if __name__ == "__main__":
    # Test
    print("Skills config path:", get_config_path())
    print("\nEnabled skills:", get_enabled_skills())
    print("Disabled skills:", get_disabled_skills())
    print("Template vars:", get_template_vars())
    print("Inline shell:", get_inline_shell_enabled())
