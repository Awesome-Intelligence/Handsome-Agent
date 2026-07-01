#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill Platform Filter - 技能平台过滤模块

根据操作系统平台过滤技能。

功能：
- 支持 macos, linux, windows 平台过滤
- 支持 Termux 特殊处理
- 从 SKILL.md frontmatter 读取 platforms 字段

📋 Logging Layer: SkillPlatform
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

from common.skill_utils import SKILL_EXCLUDED_DIRS

# 平台映射：用户友好的名称 -> sys.platform 前缀
PLATFORM_MAP = {
    "macos": "darwin",
    "linux": "linux",
    "windows": "win32",
    "termux": "android",  # Termux 在 Android 上运行 Linux 用户空间
    "android": "android",
}


def is_termux() -> bool:
    """检测是否在 Termux 环境中运行"""
    return os.path.exists("/data/data/com.termux/files/usr/bin/termux-chroot") or \
           os.environ.get("TERMUX_VERSION") or \
           os.path.exists("/proc/self/cgroup") and "com.termux" in str(Path("/proc/self/cgroup").read_text())


def get_current_platform() -> str:
    """获取当前平台标识"""
    return sys.platform


def skill_matches_platform(frontmatter: Dict[str, Any]) -> bool:
    """检查技能是否与当前操作系统兼容

    技能通过 SKILL.md frontmatter 的 platforms 列表声明平台要求::

        platforms: [macos]          # 仅 macOS
        platforms: [macos, linux]   # macOS 和 Linux

    如果字段不存在或为空，技能与所有平台兼容（向后兼容默认）。

    Termux 说明：在 Termux/Android 上，Python 报告的 sys.platform 在旧版
    Python 上是 "linux"，在 Python 3.13+ 上变成了 "android"。
    Termux 是在 Android 内核上运行的 Linux 用户空间，因此标记为 linux 的
    技能在 Termux 中被视为兼容，无论 Python 报告哪个 sys.platform 值。

    Args:
        frontmatter: SKILL.md 的 YAML frontmatter 字典

    Returns:
        True 如果技能与当前平台兼容
    """
    platforms = frontmatter.get("platforms")
    if not platforms:
        return True
    if not isinstance(platforms, list):
        platforms = [platforms]

    current = get_current_platform()
    running_in_termux = is_termux()

    for platform in platforms:
        normalized = str(platform).lower().strip()
        mapped = PLATFORM_MAP.get(normalized, normalized)

        # 检查平台匹配
        if current.startswith(mapped):
            return True

        # Termux 特殊处理：接受标记为 linux 的技能
        if running_in_termux and mapped == "linux":
            return True

        # 显式的 termux/android 标签匹配 Termux 会话
        if running_in_termux and mapped in ("termux", "android"):
            return True

    return False


def is_excluded_skill_path(path) -> bool:
    """检查路径是否应该被排除

    检查路径的任何组件是否在 SKILL_EXCLUDED_DIRS 中。
    用于排除依赖、虚拟环境、VCS 和缓存目录。
    """
    try:
        parts = path.parts
    except AttributeError:
        from pathlib import PurePath
        parts = PurePath(str(path)).parts
    return any(part in SKILL_EXCLUDED_DIRS for part in parts)


def iter_skill_index_files(skills_dir: Path, filename: str = "SKILL.md"):
    """遍历技能目录，产出匹配的文件路径。

    委托给 common.skill_utils.iter_skill_index_files（统一实现）。

    Args:
        skills_dir: 技能根目录
        filename: 要查找的文件名，默认 SKILL.md

    Yields:
        匹配的 Path 对象
    """
    from common.skill_utils import iter_skill_index_files as _iter
    return _iter(skills_dir, filename)


def get_disabled_skill_names() -> Set[str]:
    """从配置读取禁用的技能名称

    读取 common/config.py 中的 skills.disabled 配置。

    Returns:
        禁用的技能名称集合
    """
    disabled: Set[str] = set()
    try:
        from common.config import get_config_value
        disabled_config = get_config_value("skills.disabled")
        if disabled_config:
            if isinstance(disabled_config, str):
                disabled_config = [disabled_config]
            disabled = {str(s).strip() for s in disabled_config if s}
    except Exception:
        pass
    return disabled


def filter_skills_by_platform(skills_dir: Path) -> List[Path]:
    """过滤出与当前平台兼容的技能文件

    Args:
        skills_dir: 技能目录

    Returns:
        兼容的 SKILL.md 文件路径列表
    """
    import yaml

    compatible = []
    disabled = get_disabled_skill_names()

    for skill_md in iter_skill_index_files(skills_dir):
        try:
            content = skill_md.read_text(encoding="utf-8")

            # 解析 frontmatter
            frontmatter = _parse_frontmatter(content)
            if not frontmatter:
                # 没有 frontmatter，默认兼容
                compatible.append(skill_md)
                continue

            # 检查是否禁用
            name = frontmatter.get("name", skill_md.parent.name)
            if name in disabled:
                continue

            # 检查平台兼容性
            if skill_matches_platform(frontmatter):
                compatible.append(skill_md)

        except Exception:
            # 解析失败时保守地包含技能
            compatible.append(skill_md)

    return compatible


def _parse_frontmatter(content: str) -> Dict[str, Any]:
    """解析 YAML frontmatter

    委托给 agent.skill_utils 中的统一实现。
    """
    from agent.skill_utils import parse_frontmatter
    fm, _ = parse_frontmatter(content)
    return fm


def get_platform_info() -> Dict[str, Any]:
    """获取当前平台信息

    Returns:
        包含平台信息的字典
    """
    return {
        "platform": get_current_platform(),
        "is_termux": is_termux(),
        "excluded_dirs": list(SKILL_EXCLUDED_DIRS),
    }
