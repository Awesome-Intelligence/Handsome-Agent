#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Common Skill Utilities - 技能工具公共函数

提供跨模块共享的技能相关工具函数，避免代码重复。

📋 Logging Layer: CommonSkillUtils
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, Iterator, List, Tuple

import yaml

# 排除的目录（VCS、虚拟环境、缓存等）
SKILL_EXCLUDED_DIRS = frozenset({
    ".git", ".github", ".hub", ".archive", ".venv", "venv",
    "node_modules", "site-packages", "__pycache__", ".tox",
    ".nox", ".pytest_cache", ".mypy_cache", ".ruff_cache"
})


def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter from skill content.

    支持标准 YAML frontmatter 格式：
    ---
    name: Skill Name
    description: Description
    ---
    # Skill Content

    Args:
        content: Raw skill content

    Returns:
        Tuple of (frontmatter dict, body content)
    """
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


def iter_skill_index_files(
    base_dir: Path,
    index_name: str = "SKILL.md"
) -> Iterator[Path]:
    """遍历技能目录，产出匹配的文件路径。

    使用 os.walk 遍历（跟随符号链接），排除 VCS、虚拟环境和缓存目录。

    Args:
        base_dir: 技能根目录
        index_name: 要查找的文件名，默认 SKILL.md

    Yields:
        匹配的 Path 对象
    """
    if not base_dir.exists() or not base_dir.is_dir():
        return

    matches = []
    for root, dirs, files in os.walk(base_dir, followlinks=True):
        # 过滤掉排除的目录（就地修改）
        dirs[:] = [d for d in dirs if d not in SKILL_EXCLUDED_DIRS]
        if index_name in files:
            matches.append(Path(root) / index_name)

    for path in sorted(matches, key=lambda p: str(p.relative_to(base_dir))):
        yield path


def get_skill_platforms(frontmatter: Dict[str, Any]) -> List[str]:
    """从 frontmatter 中提取支持的平台列表。

    Args:
        frontmatter: 技能的 frontmatter 字典

    Returns:
        平台列表，默认返回 ["linux", "macos", "windows"]
    """
    platforms = frontmatter.get("platforms")
    if not platforms:
        return ["linux", "macos", "windows"]
    if isinstance(platforms, str):
        return [platforms]
    if isinstance(platforms, list):
        return [str(p).lower().strip() for p in platforms]
    return ["linux", "macos", "windows"]


def get_skill_category(frontmatter: Dict[str, Any]) -> str:
    """从 frontmatter 中提取技能分类。

    Args:
        frontmatter: 技能的 frontmatter 字典

    Returns:
        分类名称，默认为 "general"
    """
    category = frontmatter.get("category")
    if category:
        return str(category).lower().strip()
    return "general"


def get_skill_tags(frontmatter: Dict[str, Any]) -> List[str]:
    """从 frontmatter 中提取技能标签。

    支持多种格式：
    - metadata.hermes.tags: [tag1, tag2]
    - tags: [tag1, tag2]

    Args:
        frontmatter: 技能的 frontmatter 字典

    Returns:
        标签列表
    """
    # 检查 metadata.hermes.tags
    metadata = frontmatter.get("metadata", {})
    if isinstance(metadata, dict):
        hermes = metadata.get("hermes", {})
        if isinstance(hermes, dict):
            tags = hermes.get("tags", [])
            if isinstance(tags, list):
                return [str(t).lower().strip() for t in tags if t]

    # 检查顶层 tags
    tags = frontmatter.get("tags", [])
    if isinstance(tags, list):
        return [str(t).lower().strip() for t in tags if t]

    return []
