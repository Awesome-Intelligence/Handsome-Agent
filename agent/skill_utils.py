#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill Utils - Skill utility functions.

🧠 Decision - 📋 Skills - 技能工具函数

参考 Hermes 的 agent/skill_utils.py 设计，提供：
- 前端解析（委托给 common.skill_utils）
- 平台过滤（委托给 agent.skill_platform）
- 配置变量提取
- 外部技能目录管理
- 插件技能命名空间支持
"""

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

logger = logging.getLogger(__name__)

# 命名空间正则：字母、数字、下划线，长度 1-32
NAMESPACE_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{0,31}$")

# 排除的技能路径模式（相对于技能目录根）
EXCLUDED_PATTERNS = [
    # Hidden directories
    re.compile(r"^\."),
    # Common non-skill directories
    re.compile(r"^__pycache__$"),
    re.compile(r"^node_modules$"),
    re.compile(r"^\.git$"),
]


def skill_matches_platform(frontmatter: Dict[str, Any]) -> bool:
    """检查技能是否与当前平台兼容。

    委托给 agent.skill_platform.skill_matches_platform（功能更完整，包含Termux处理）。

    Args:
        frontmatter: 技能的 frontmatter 字典

    Returns:
        True 如果技能在当前平台可用，否则 False
    """
    from agent.skill_platform import skill_matches_platform as _check
    return _check(frontmatter)


def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter from skill content.

    委托给 common.skill_utils 中的统一实现。

    Args:
        content: Raw skill content

    Returns:
        Tuple of (frontmatter dict, body content)
    """
    from common.skill_utils import parse_frontmatter as _parse
    return _parse(content)


def iter_skill_index_files(base_dir: Path, index_name: str = "SKILL.md") -> Iterator[Path]:
    """递归迭代目录下所有技能索引文件。

    委托给 common.skill_utils.iter_skill_index_files。

    Args:
        base_dir: 基础目录路径
        index_name: 索引文件名，默认为 "SKILL.md"

    Yields:
        Path: 索引文件的路径
    """
    from common.skill_utils import iter_skill_index_files as _iter
    return _iter(base_dir, index_name)


# =============================================================================
# 保留以下函数作为兼容层，实际实现已迁移到 common/skill_utils.py
# 命名空间相关函数保留在此作为便捷入口
# =============================================================================


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


# 外部目录缓存：(config_path_str, mtime_ns) -> resolved dirs list
_EXTERNAL_DIRS_CACHE: Dict[Tuple[str, int], List[Path]] = {}


def _external_dirs_cache_clear() -> None:
    """Test hook - drop the in-process cache."""
    _EXTERNAL_DIRS_CACHE.clear()


def get_external_skills_dirs() -> List[Path]:
    """Get list of external skills directories with mtime caching.

    从配置中读取外部技能目录列表，使用 mtime 缓存优化性能。
    配置变更时自动刷新缓存。

    Returns:
        List of Path objects
    """
    from common.config import get_config_path, get_settings

    config_path = get_config_path()
    if not config_path.exists():
        return []

    # 缓存键：使用配置路径和 mtime_ns
    try:
        stat = config_path.stat()
        cache_key: Tuple[str, int] = (str(config_path), stat.st_mtime_ns)
    except OSError:
        cache_key = None

    # 检查缓存
    if cache_key is not None:
        cached = _EXTERNAL_DIRS_CACHE.get(cache_key)
        if cached is not None:
            return list(cached)

    # 解析配置
    skills_cfg = get_settings().skills
    external_dirs = skills_cfg.get("external_dirs", [])

    dirs = []
    for dir_path in external_dirs:
        # 展开 ~ 和环境变量
        expanded = os.path.expanduser(os.path.expandvars(str(dir_path)))
        path = Path(expanded)
        if path.exists():
            dirs.append(path)

    # 更新缓存
    if cache_key is not None:
        _EXTERNAL_DIRS_CACHE[cache_key] = list(dirs)

    return dirs


def get_all_skills_dirs() -> List[Path]:
    """Get all skills directories (local + external).

    Returns:
        List of Path objects, local first then external
    """
    from common.config import get_skills_dir

    dirs = [get_skills_dir()]
    dirs.extend(get_external_skills_dirs())
    return dirs


def is_excluded_skill_path(path: Path) -> bool:
    """Check if a skill path should be excluded.

    Args:
        path: Skill path to check (directory name or relative path)

    Returns:
        True if path should be excluded
    """
    name = path.name if isinstance(path, Path) else str(path)
    for pattern in EXCLUDED_PATTERNS:
        if pattern.match(name):
            return True
    return False


def parse_qualified_name(name: str) -> Tuple[Optional[str], str]:
    """Parse qualified skill name with namespace.

    支持两种格式：
    - "namespace:skill" -> ("namespace", "skill")
    - "skill" -> (None, "skill")

    Args:
        name: Qualified or simple skill name

    Returns:
        Tuple of (namespace, skill_name)
    """
    if ":" in name:
        parts = name.split(":", 1)
        return parts[0], parts[1]
    return None, name


def is_valid_namespace(namespace: str) -> bool:
    """Validate namespace format.

    命名空间规则：
    - 以字母开头
    - 仅包含字母、数字、下划线
    - 长度 1-32 字符

    Args:
        namespace: Namespace string to validate

    Returns:
        True if valid
    """
    if not namespace:
        return False
    return bool(NAMESPACE_PATTERN.match(namespace))


def list_plugin_skills(namespace: str) -> List[Dict[str, Any]]:
    """List skills provided by a plugin namespace.

    从外部技能目录中查找指定命名空间的技能。

    Args:
        namespace: Plugin namespace name

    Returns:
        List of skill info dicts
    """
    # parse_frontmatter 已在本模块定义（委托给 common.skill_utils）
    skills = []
    external_dirs = get_external_skills_dirs()

    for skills_dir in external_dirs:
        # 查找 namespace 子目录
        namespace_dir = skills_dir / namespace
        if not namespace_dir.exists() or not namespace_dir.is_dir():
            continue

        # 遍历 namespace 下的技能目录
        for skill_path in namespace_dir.iterdir():
            if not skill_path.is_dir():
                continue
            if is_excluded_skill_path(skill_path):
                continue

            skill_file = skill_path / "SKILL.md"
            if not skill_file.exists():
                continue

            try:
                content = skill_file.read_text(encoding="utf-8")
                frontmatter, body = parse_frontmatter(content)

                if not body.strip():
                    continue

                skills.append({
                    "name": skill_path.name,
                    "namespace": namespace,
                    "qualified_name": f"{namespace}:{skill_path.name}",
                    "path": str(skill_path),
                    "description": frontmatter.get("description", ""),
                    "category": frontmatter.get("category", "general"),
                    "author": frontmatter.get("author", ""),
                    "version": frontmatter.get("version", "1.0.0"),
                    "enabled": not frontmatter.get("disabled", False),
                })
            except Exception as e:
                logger.debug(f"Failed to load skill at {skill_path}: {e}")

    return skills


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
    print("All skills dirs:", get_all_skills_dirs())
    print("\nAll skills:", get_all_skills())
    print("\nSkill commands:", get_skill_commands())

    # Test namespace functions
    print("\n--- Namespace Tests ---")
    print("parse_qualified_name('my_plugin:code_review'):", parse_qualified_name("my_plugin:code_review"))
    print("parse_qualified_name('simple_skill'):", parse_qualified_name("simple_skill"))
    print("is_valid_namespace('my_plugin'):", is_valid_namespace("my_plugin"))
    print("is_valid_namespace('123invalid'):", is_valid_namespace("123invalid"))
    print("is_valid_namespace(''):", is_valid_namespace(""))
    print("is_excluded_skill_path('.hidden'):", is_excluded_skill_path(Path(".hidden")))
    print("is_excluded_skill_path('__pycache__'):", is_excluded_skill_path(Path("__pycache__")))
    print("is_excluded_skill_path('valid_skill'):", is_excluded_skill_path(Path("valid_skill")))

    # Test iter_skill_index_files
    print("\n--- iter_skill_index_files Test ---")
    from common.config import get_skills_dir
    skills_dir = get_skills_dir()
    print(f"Scanning skills directory: {skills_dir}")
    for skill_file in iter_skill_index_files(skills_dir):
        print(f"  Found: {skill_file}")