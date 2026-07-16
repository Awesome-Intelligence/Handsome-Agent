#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill Workflows - 技能组合 Bundle 机制

提供多技能协同工作的能力：
- 将多个相关技能组合成一个工作流
- 一个命令加载多个技能
- 支持可选的额外指令注入
- 缺失技能的容错处理

🎯 Workflow - 📋 Skills - 技能组合

参考 Hermes 的 agent/skill_bundles.py 设计，实现：
- Bundle YAML 格式定义
- Bundle 扫描与缓存
- 多技能消息构建
- 优先于同名 Skill 的分发机制
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from common.logging_manager import get_execution_logger

logger = get_execution_logger("SkillWorkflows")

# ============================================================================
# 常量定义
# ============================================================================

# Bundle 目录
BUNDLE_DIR_NAME = "skill-bundles"

# Bundle 文件名模式
_BUNDLE_INVALID_CHARS = re.compile(r"[^a-z0-9-_]")
_BUNDLE_MULTI_HYPHEN = re.compile(r"-{2,}")

# 全局缓存
_bundles_cache: Dict[str, Dict[str, Any]] = {}
_bundles_cache_mtime: float = 0.0


# ============================================================================
# 数据结构
# ============================================================================

@dataclass
class BundleInfo:
    """Bundle 信息"""
    name: str                          # Bundle 名称
    slug: str                          # URL 友好的 slug
    description: str                   # 描述
    skills: List[str]                  # 技能 ID 列表
    instruction: str = ""               # 可选的额外指令
    source_file: Optional[Path] = None # 来源文件
    author: str = ""                   # 作者
    version: str = "1.0.0"             # 版本


@dataclass
class BundleResult:
    """Bundle 执行结果"""
    success: bool
    message: str                       # 构建的消息内容
    loaded_skills: List[str] = field(default_factory=list)  # 成功加载的技能
    missing_skills: List[str] = field(default_factory=list)  # 缺失的技能
    bundle_name: str = ""               # Bundle 名称


# ============================================================================
# 工具函数
# ============================================================================

def _bundles_dir() -> Path:
    """获取 Bundle 目录路径"""
    override = os.environ.get("AGENTZ_BUNDLES_DIR")
    if override:
        return Path(override).expanduser()

    # 默认在 AGENT_Z_HOME 目录下
    from common.config import AGENT_Z_HOME
    return AGENT_Z_HOME / BUNDLE_DIR_NAME


def _slugify(name: str) -> str:
    """将名称转换为 URL 友好的 slug

    Args:
        name: 原始名称

    Returns:
        slug 格式字符串
    """
    cmd = name.lower().replace(" ", "-").replace("_", "-")
    cmd = _BUNDLE_INVALID_CHARS.sub("", cmd)
    cmd = _BUNDLE_MULTI_HYPHEN.sub("-", cmd).strip("-")
    return cmd


def _iter_bundle_files() -> List[Path]:
    """迭代所有 Bundle YAML 文件"""
    bundle_dir = _bundles_dir()

    if not bundle_dir.exists():
        return []

    files = []
    for f in bundle_dir.iterdir():
        if f.is_file() and f.suffix in (".yaml", ".yml"):
            files.append(f)

    return files


def _max_mtime(files: List[Path]) -> float:
    """获取文件列表的最大 mtime

    Args:
        files: 文件路径列表

    Returns:
        最大修改时间
    """
    base = _bundles_dir()
    mtimes = []

    if base.exists():
        try:
            mtimes.append(base.stat().st_mtime)
        except OSError:
            pass

    for f in files:
        try:
            mtimes.append(f.stat().st_mtime)
        except OSError:
            continue

    return max(mtimes) if mtimes else 0.0


def _load_bundle_file(bundle_path: Path) -> Optional[Dict[str, Any]]:
    """加载单个 Bundle 文件

    Args:
        bundle_path: Bundle YAML 文件路径

    Returns:
        Bundle 数据字典或 None
    """
    try:
        import yaml

        with open(bundle_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data:
            logger.warning(f"Empty bundle file: {bundle_path}")
            return None

        # 提取字段
        name = str(data.get("name") or bundle_path.stem).strip()
        slug = _slugify(name)
        description = str(data.get("description", ""))
        skills = data.get("skills", [])
        instruction = str(data.get("instruction", ""))
        author = str(data.get("author", ""))
        version = str(data.get("version", "1.0.0"))

        # 验证 skills 字段
        if not skills:
            logger.warning(f"Bundle '{name}' has no skills defined")
            return None

        if not isinstance(skills, list):
            logger.warning(f"Bundle '{name}' skills must be a list")
            return None

        return {
            "name": name,
            "slug": slug,
            "description": description,
            "skills": skills,
            "instruction": instruction,
            "author": author,
            "version": version,
            "source_file": str(bundle_path),
        }

    except ImportError:
        logger.error("PyYAML is required for Bundle support. Install with: pip install pyyaml")
        return None
    except Exception as e:
        logger.error(f"Failed to load bundle from {bundle_path}: {e}")
        return None


def _snapshot(cache: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
    """创建缓存快照用于增量检测"""
    return {k: v.get("name", k) for k, v in cache.items()}


# ============================================================================
# 核心 API
# ============================================================================

def scan_bundles() -> Dict[str, Dict[str, Any]]:
    """扫描 Bundle 目录并重建缓存

    Returns:
        Dict mapping "/slug" to bundle info
    """
    global _bundles_cache, _bundles_cache_mtime

    files = _iter_bundle_files()
    out: Dict[str, Dict[str, Any]] = {}

    for f in files:
        info = _load_bundle_file(f)
        if not info:
            continue

        key = f"/{info['slug']}"
        if key in out:
            logger.warning(
                f"Duplicate bundle slug '{key}' from {f}; keeping existing"
            )
            continue

        out[key] = info

    _bundles_cache = out
    _bundles_cache_mtime = _max_mtime(files)

    logger.debug(f"Scanned {len(out)} bundles")
    return out


def get_bundles() -> Dict[str, Dict[str, Any]]:
    """获取当前的 Bundle 映射，必要时重新扫描

    Returns:
        Dict mapping "/slug" to bundle info
    """
    global _bundles_cache, _bundles_cache_mtime

    files = _iter_bundle_files()
    current_mtime = _max_mtime(files)

    if not _bundles_cache or _bundles_cache_mtime != current_mtime:
        scan_bundles()

    return _bundles_cache


def get_bundle(name_or_slug: str) -> Optional[Dict[str, Any]]:
    """根据名称或 slug 获取 Bundle

    Args:
        name_or_slug: Bundle 名称或 slug

    Returns:
        Bundle 信息或 None
    """
    bundles = get_bundles()

    # 直接匹配 slug
    slug = f"/{_slugify(name_or_slug)}"
    if slug in bundles:
        return bundles[slug]

    # 模糊匹配名称
    for key, info in bundles.items():
        if info.get("name") == name_or_slug:
            return info

    return None


def resolve_bundle_command_key(command: str) -> Optional[str]:
    """将命令解析为 Bundle key

    Args:
        command: 命令名称（可能有 / 前缀）

    Returns:
        Bundle key (如 "/backend-dev") 或 None
    """
    # 移除前导斜杠并规范化
    normalized = _slugify(command.lstrip("/"))

    bundles = get_bundles()

    # 精确匹配
    key = f"/{normalized}"
    if key in bundles:
        return key

    # 名称匹配
    for bundle_key, info in bundles.items():
        if info.get("name", "").lower() == command.lower():
            return bundle_key

    return None


def resolve_skill_command_key(command: str) -> Optional[str]:
    """将命令解析为 Skill key（排除 Bundle）

    Args:
        command: 命令名称

    Returns:
        Skill key 或 None
    """
    from agent.skill_commands import get_skill_commands

    # 先检查是否是 Bundle
    if resolve_bundle_command_key(command):
        return None

    # 查找 Skill
    commands = get_skill_commands()
    normalized = _slugify(command.lstrip("/"))

    # 精确匹配
    key = f"/{normalized}"
    if key in commands:
        return key

    # 模糊匹配
    for cmd_key, info in commands.items():
        if info.get("name", "").lower() == command.lower():
            return cmd_key

    return None


# ============================================================================
# 消息构建
# ============================================================================

def _load_skill_payload(skill_id: str, task_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """加载单个技能内容

    Args:
        skill_id: 技能 ID
        task_id: 可选的 task ID

    Returns:
        技能数据或 None
    """
    from agent.skill_commands import load_skill
    return load_skill(skill_id, task_id=task_id)


def _build_skill_message(
    skill_id: str,
    skill_data: Dict[str, Any],
    bundle_name: str,
) -> str:
    """构建单个技能的消息块

    Args:
        skill_id: 技能 ID
        skill_data: 技能数据
        bundle_name: Bundle 名称

    Returns:
        格式化消息
    """
    content = str(skill_data.get("content") or "")

    lines = [
        f"[Loaded as part of the \"{bundle_name}\" skill bundle.]",
        "",
        content.strip(),
    ]

    return "\n".join(lines)


def build_bundle_invocation_message(
    bundle_key: str,
    user_instruction: str = "",
    task_id: Optional[str] = None,
) -> Optional[BundleResult]:
    """构建 Bundle 调用的完整消息

    Args:
        bundle_key: Bundle key (如 "/backend-dev")
        user_instruction: 用户指令
        task_id: 可选的 task ID

    Returns:
        BundleResult 或 None（如果 Bundle 不存在）
    """
    bundles = get_bundles()
    info = bundles.get(bundle_key)

    if not info:
        return None

    bundle_name = info["name"]
    skills = info.get("skills", [])
    instruction = info.get("instruction", "")

    loaded_names: List[str] = []
    missing: List[str] = []
    skill_blocks: List[str] = []
    seen: set[str] = set()

    # 依次加载每个技能
    for skill_id in skills:
        identifier = (skill_id or "").strip()
        if not identifier or identifier in seen:
            continue
        seen.add(identifier)

        loaded = _load_skill_payload(identifier, task_id=task_id)
        if not loaded:
            missing.append(identifier)
            continue

        skill_blocks.append(_build_skill_message(identifier, loaded, bundle_name))
        loaded_names.append(identifier)

    # 如果没有成功加载任何技能
    if not loaded_names:
        logger.warning(f"Bundle '{bundle_name}' has no valid skills to load")
        return BundleResult(
            success=False,
            message="",
            loaded_skills=[],
            missing_skills=missing,
            bundle_name=bundle_name,
        )

    # 构建消息头部
    header_lines = [
        f'[IMPORTANT: The user has invoked the "{bundle_name}" skill bundle.]',
        f"Bundle: {bundle_name}",
        f"Skills loaded: {', '.join(loaded_names)}",
    ]

    if missing:
        header_lines.append(f"Skills missing (skipped): {', '.join(missing)}")

    if instruction:
        header_lines.extend(["", f"Bundle instruction: {instruction}"])

    if user_instruction:
        header_lines.extend(["", f"User instruction: {user_instruction}"])

    header = "\n".join(header_lines)

    # 组装完整消息
    message = "\n\n".join([header, *skill_blocks])

    return BundleResult(
        success=True,
        message=message,
        loaded_skills=loaded_names,
        missing_skills=missing,
        bundle_name=bundle_name,
    )


# ============================================================================
# Bundle 管理
# ============================================================================

def list_bundles() -> List[BundleInfo]:
    """列出所有 Bundle

    Returns:
        Bundle 信息列表
    """
    bundles = get_bundles()
    result = []

    for key, info in bundles.items():
        result.append(BundleInfo(
            name=info.get("name", ""),
            slug=info.get("slug", key.lstrip("/")),
            description=info.get("description", ""),
            skills=info.get("skills", []),
            instruction=info.get("instruction", ""),
            author=info.get("author", ""),
            version=info.get("version", "1.0.0"),
        ))

    # 按名称排序
    result.sort(key=lambda x: x.name)
    return result


def create_bundle(
    name: str,
    skills: List[str],
    description: str = "",
    instruction: str = "",
    author: str = "",
) -> Tuple[bool, str]:
    """创建新的 Bundle

    Args:
        name: Bundle 名称
        skills: 技能 ID 列表
        description: 描述
        instruction: 额外指令
        author: 作者

    Returns:
        (成功标志, 消息)
    """
    if not skills:
        return False, "Bundle must have at least one skill"

    bundle_dir = _bundles_dir()
    bundle_dir.mkdir(parents=True, exist_ok=True)

    slug = _slugify(name)
    file_path = bundle_dir / f"{slug}.yaml"

    if file_path.exists():
        return False, f"Bundle '{name}' already exists at {file_path}"

    import yaml

    data = {
        "name": name,
        "description": description,
        "skills": skills,
    }

    if instruction:
        data["instruction"] = instruction

    if author:
        data["author"] = author

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

        # 清除缓存
        global _bundles_cache
        _bundles_cache = {}

        return True, f"Bundle '{name}' created at {file_path}"

    except Exception as e:
        return False, f"Failed to create bundle: {e}"


def update_bundle(
    name_or_slug: str,
    skills: Optional[List[str]] = None,
    description: Optional[str] = None,
    instruction: Optional[str] = None,
) -> Tuple[bool, str]:
    """更新现有 Bundle

    Args:
        name_or_slug: Bundle 名称或 slug
        skills: 新的技能列表（可选）
        description: 新的描述（可选）
        instruction: 新的指令（可选）

    Returns:
        (成功标志, 消息)
    """
    bundle = get_bundle(name_or_slug)
    if not bundle:
        return False, f"Bundle '{name_or_slug}' not found"

    file_path = Path(bundle.get("source_file", ""))
    if not file_path.exists():
        return False, f"Bundle source file not found: {file_path}"

    import yaml

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if skills is not None:
            data["skills"] = skills

        if description is not None:
            data["description"] = description

        if instruction is not None:
            data["instruction"] = instruction

        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

        # 清除缓存
        global _bundles_cache
        _bundles_cache = {}

        return True, f"Bundle '{bundle['name']}' updated"

    except Exception as e:
        return False, f"Failed to update bundle: {e}"


def delete_bundle(name_or_slug: str) -> Tuple[bool, str]:
    """删除 Bundle

    Args:
        name_or_slug: Bundle 名称或 slug

    Returns:
        (成功标志, 消息)
    """
    bundle = get_bundle(name_or_slug)
    if not bundle:
        return False, f"Bundle '{name_or_slug}' not found"

    file_path = Path(bundle.get("source_file", ""))
    if not file_path.exists():
        return False, f"Bundle source file not found: {file_path}"

    try:
        file_path.unlink()

        # 清除缓存
        global _bundles_cache
        _bundles_cache = {}

        return True, f"Bundle '{bundle['name']}' deleted"

    except Exception as e:
        return False, f"Failed to delete bundle: {e}"


def reload_bundles() -> Dict[str, Any]:
    """重新扫描并返回变更差异

    Returns:
        包含 added, removed, unchanged 的字典
    """
    global _bundles_cache

    before = _snapshot(_bundles_cache)
    new = scan_bundles()
    after = _snapshot(new)

    added_names = sorted(set(after) - set(before))
    removed_names = sorted(set(before) - set(after))
    unchanged = sorted(set(after) & set(before))

    return {
        "added": [{"name": n, "slug": after[n]} for n in added_names],
        "removed": [{"name": n, "slug": before[n]} for n in removed_names],
        "unchanged": unchanged,
        "total": len(after),
    }


def show_bundle(name_or_slug: str) -> Optional[str]:
    """显示 Bundle 详细信息

    Args:
        name_or_slug: Bundle 名称或 slug

    Returns:
        格式化的 Bundle 信息或 None
    """
    bundle = get_bundle(name_or_slug)
    if not bundle:
        return None

    lines = [
        f"# Bundle: {bundle['name']}",
        "",
        f"Slug: /{bundle.get('slug', '')}",
        f"Description: {bundle.get('description', 'N/A')}",
        f"Author: {bundle.get('author', 'N/A')}",
        f"Version: {bundle.get('version', '1.0.0')}",
        "",
        "Skills:",
    ]

    for skill_id in bundle.get("skills", []):
        lines.append(f"  - {skill_id}")

    if bundle.get("instruction"):
        lines.extend(["", f"Instruction:", bundle["instruction"]])

    return "\n".join(lines)


# ============================================================================
# CLI 支持
# ============================================================================

def get_bundle_templates() -> List[Dict[str, str]]:
    """获取内置的 Bundle 模板

    Returns:
        模板列表
    """
    return [
        {
            "id": "dev-workflow",
            "name": "开发工作流",
            "description": "包含代码审查、测试、PR 流程的完整开发工作流",
            "skills": ["github-code-review", "test-driven-development", "github-pr-workflow"],
        },
        {
            "id": "data-science",
            "name": "数据科学",
            "description": "数据分析、机器学习、可视化工作流",
            "skills": ["data-analysis", "ml-pipeline", "visualization"],
        },
        {
            "id": "devops",
            "name": "DevOps",
            "description": "CI/CD、容器化、监控部署工作流",
            "skills": ["ci-cd-pipeline", "docker-deployment", "monitoring-setup"],
        },
    ]


# ============================================================================
# 模块初始化
# ============================================================================

# 预热缓存
try:
    scan_bundles()
except Exception:
    pass


if __name__ == "__main__":
    # 测试
    print("Skill Workflows Bundle System")
    print("=" * 50)

    bundles = list_bundles()
    print(f"Found {len(bundles)} bundles:\n")

    for bundle in bundles:
        print(f"  /{bundle.slug}")
        print(f"    Name: {bundle.name}")
        print(f"    Description: {bundle.description}")
        print(f"    Skills: {', '.join(bundle.skills)}")
        print()
