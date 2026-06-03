#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skills Tool - Skill directory scanning and management.

🏃 Execution - 🛠️ ToolExec - 技能工具

参考 Hermes 的 tools/skills_tool.py 设计，提供：
- 技能目录扫描
- SKILL.md 解析
- 技能视图获取
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Default skills directory
SKILLS_DIR = Path(__file__).parent.parent / "skills"


def get_skills_dir() -> Path:
    """Get the skills directory."""
    return SKILLS_DIR


def set_skills_dir(path: Path | str):
    """Set a custom skills directory."""
    global SKILLS_DIR
    SKILLS_DIR = Path(path)


def list_skills() -> list[Dict[str, Any]]:
    """List all available skills.

    Returns:
        List of skill info dicts
    """
    skills = []

    if not SKILLS_DIR.exists():
        return skills

    for skill_path in SKILLS_DIR.iterdir():
        if not skill_path.is_dir() or skill_path.name.startswith("."):
            continue

        skill_file = skill_path / "SKILL.md"
        if not skill_file.exists():
            continue

        try:
            content = skill_file.read_text(encoding="utf-8")
            frontmatter = _parse_frontmatter(content)

            skills.append({
                "name": skill_path.name,
                "path": str(skill_path.relative_to(SKILLS_DIR)),
                "description": frontmatter.get("description", ""),
                "category": frontmatter.get("category", "general"),
                "author": frontmatter.get("author", ""),
                "version": frontmatter.get("version", "1.0.0"),
                "enabled": not frontmatter.get("disabled", False),
                "skill_dir": str(skill_path),
            })
        except Exception as e:
            logger.debug(f"Failed to load skill at {skill_path}: {e}")

    return skills


def skill_exists(skill_name: str) -> bool:
    """Check if a skill exists.

    Args:
        skill_name: Skill name

    Returns:
        True if skill exists
    """
    skill_path = SKILLS_DIR / skill_name
    return skill_path.exists() and (skill_path / "SKILL.md").exists()


def skill_view(skill_name: str, task_id: str = None, preprocess: bool = True) -> str:
    """Get the skill view (formatted skill content).

    Args:
        skill_name: Skill name
        task_id: Optional task ID
        preprocess: Whether to preprocess content

    Returns:
        JSON string with skill info and content
    """
    result = {
        "success": False,
        "name": skill_name,
        "path": "",
        "content": "",
        "error": "",
    }

    # Try direct path first
    skill_path = SKILLS_DIR / skill_name
    if not skill_path.exists():
        # Try without leading slash
        if skill_name.startswith("/"):
            skill_name = skill_name[1:]
            skill_path = SKILLS_DIR / skill_name

    if not skill_path.exists():
        result["error"] = f"Skill not found: {skill_name}"
        return json.dumps(result)

    skill_file = skill_path / "SKILL.md"
    if not skill_file.exists():
        result["error"] = f"SKILL.md not found in {skill_name}"
        return json.dumps(result)

    try:
        content = skill_file.read_text(encoding="utf-8")
        frontmatter = _parse_frontmatter(content)

        # Get actual content (after frontmatter)
        body_content = _get_content_after_frontmatter(content)

        result["success"] = True
        result["name"] = skill_path.name
        result["path"] = str(skill_path.relative_to(SKILLS_DIR))
        result["content"] = body_content
        result["skill_dir"] = str(skill_path)
        result["description"] = frontmatter.get("description", "")
        result["category"] = frontmatter.get("category", "general")

        if preprocess:
            result["content"] = _preprocess_content(body_content, skill_path)

    except Exception as e:
        result["error"] = str(e)

    return json.dumps(result)


def _parse_frontmatter(content: str) -> Dict[str, Any]:
    """Parse YAML frontmatter from skill content.

    Args:
        content: Raw skill content

    Returns:
        Dict of frontmatter values
    """
    import yaml

    frontmatter = {}
    lines = content.split("\n")

    if len(lines) < 3 or lines[0].strip() != "---":
        return frontmatter

    # Find closing ---
    end_idx = None
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        return frontmatter

    try:
        frontmatter = yaml.safe_load("\n".join(lines[1:end_idx]))
        if not isinstance(frontmatter, dict):
            frontmatter = {}
    except Exception:
        frontmatter = {}

    return frontmatter


def _get_content_after_frontmatter(content: str) -> str:
    """Get content after frontmatter.

    Args:
        content: Raw content with frontmatter

    Returns:
        Content after frontmatter
    """
    lines = content.split("\n")

    if len(lines) < 3 or lines[0].strip() != "---":
        return content

    # Find closing ---
    end_idx = None
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        return content

    return "\n".join(lines[end_idx + 1:]).strip()


def _preprocess_content(content: str, skill_dir: Path) -> str:
    """Preprocess skill content.

    Args:
        content: Raw content
        skill_dir: Skill directory

    Returns:
        Preprocessed content
    """
    # TODO: Add template variable substitution, inline shell expansion, etc.
    return content


def get_skill_references(skill_name: str) -> list[Dict[str, str]]:
    """Get skill reference files.

    Args:
        skill_name: Skill name

    Returns:
        List of reference files
    """
    skill_path = SKILLS_DIR / skill_name
    if not skill_path.exists():
        return []

    references = []
    ref_dir = skill_path / "references"

    if not ref_dir.exists():
        return []

    for ref_file in ref_dir.iterdir():
        if ref_file.is_file():
            references.append({
                "name": ref_file.name,
                "path": str(ref_file.relative_to(SKILLS_DIR)),
                "type": ref_file.suffix.lstrip("."),
            })

    return references


def get_skill_prompts(skill_name: str) -> list[Dict[str, str]]:
    """Get skill prompt templates.

    Args:
        skill_name: Skill name

    Returns:
        List of prompt templates
    """
    skill_path = SKILLS_DIR / skill_name
    if not skill_path.exists():
        return []

    prompts = []
    prompts_dir = skill_path / "prompts"

    if not prompts_dir.exists():
        return []

    for prompt_file in prompts_dir.iterdir():
        if prompt_file.is_file() and prompt_file.suffix == ".md":
            try:
                content = prompt_file.read_text(encoding="utf-8")
                prompts.append({
                    "name": prompt_file.stem,
                    "path": str(prompt_file.relative_to(SKILLS_DIR)),
                    "content": content,
                })
            except Exception:
                pass

    return prompts


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    # Test
    print("Skills directory:", SKILLS_DIR)
    print("\nAvailable skills:")
    skills = list_skills()
    for skill in skills:
        print(f"  - {skill['name']}: {skill.get('description', '')}")