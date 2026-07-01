#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Progressive Disclosure - 渐进式披露架构

实现三层技能内容披露机制，平衡上下文窗口效率和技能可见性：

Tier 1 (系统提示索引)
  - 仅包含技能元数据（名称、描述、分类）
  - 自动注入到系统提示
  - 两层缓存：内存 LRU + 磁盘快照

Tier 2 (完整技能内容)
  - 用户通过 /skill-name 调用时加载
  - 包含完整 SKILL.md 内容和模板变量替换

Tier 3 (支持文件)
  - 按需加载技能目录中的辅助文件
  - scripts/, assets/, references/ 等

🚪 Access - 📋 Skills - Progressive Disclosure
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from common.logging_manager import get_decision_logger

logger = get_decision_logger("ProgressiveDisclosure")

# ============================================================================
# 常量定义
# ============================================================================

# 缓存配置
_PROMPT_CACHE_MAX = 32  # LRU 缓存最大条目数
_SNAPSHOT_FILENAME = ".skills_prompt_snapshot.json"
_SKILL_INDEX_FILENAME = ".skills_index.json"

# 缓存锁
_CACHE_LOCK = threading.RLock()


# ============================================================================
# Tier 1: 系统提示技能索引构建
# ============================================================================

# 内存 LRU 缓存
_PROMPT_CACHE: OrderedDict[str, str] = OrderedDict()
_CACHE_KEY_COUNTER: Dict[str, int] = {}  # 用于 LRU 淘汰计数


class SkillsIndexCache:
    """
    技能索引缓存管理器

    实现两层缓存：
    1. 内存 LRU 缓存 - 进程内快速访问
    2. 磁盘快照 - 进程重启后快速恢复
    """

    def __init__(self, skills_dir: Path):
        self.skills_dir = Path(skills_dir)
        self.snapshot_path = self.skills_dir / _SNAPSHOT_FILENAME
        self.index_path = self.skills_dir / _SKILL_INDEX_FILENAME

    def _get_cache_key(
        self,
        platform: str,
        disabled_skills: Set[str],
        external_dirs: Tuple[str, ...],
    ) -> str:
        """生成缓存键"""
        key_parts = [
            str(self.skills_dir.resolve()),
            platform,
            "|".join(sorted(disabled_skills)),
            "|".join(sorted(external_dirs)),
        ]
        key_str = ":".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()

    def _load_snapshot(self) -> Optional[Dict[str, Any]]:
        """从磁盘加载快照"""
        if not self.snapshot_path.exists():
            return None

        try:
            data = json.loads(self.snapshot_path.read_text(encoding="utf-8"))
            # 验证快照是否过期
            cached_mtime = data.get("skills_dir_mtime", 0)
            current_mtime = self._get_dir_mtime()
            if cached_mtime != current_mtime:
                logger.debug("Snapshot expired (mtime mismatch)")
                return None
            return data
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load snapshot: {e}")
            return None

    def _write_snapshot(self, data: Dict[str, Any]) -> None:
        """写入磁盘快照"""
        try:
            data["skills_dir_mtime"] = self._get_dir_mtime()
            data["updated_at"] = datetime.now().isoformat()
            self.snapshot_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.debug(f"Wrote snapshot to {self.snapshot_path}")
        except OSError as e:
            logger.warning(f"Failed to write snapshot: {e}")

    def _get_dir_mtime(self) -> int:
        """获取技能目录的修改时间戳"""
        if self.skills_dir.exists():
            return int(self.skills_dir.stat().st_mtime)
        return 0

    def get_cached_prompt(self) -> Optional[str]:
        """获取缓存的系统提示"""
        snapshot = self._load_snapshot()
        if snapshot:
            return snapshot.get("system_prompt")
        return None

    def cache_prompt(self, prompt: str) -> None:
        """缓存系统提示到磁盘"""
        snapshot = self._load_snapshot() or {}
        snapshot["system_prompt"] = prompt
        self._write_snapshot(snapshot)

    def invalidate(self) -> None:
        """使缓存失效"""
        with _CACHE_LOCK:
            _PROMPT_CACHE.clear()
        try:
            if self.snapshot_path.exists():
                self.snapshot_path.unlink()
        except OSError:
            pass


def build_skills_index_for_prompt(
    skills_dir: Optional[Path] = None,
    platform: Optional[str] = None,
    disabled_skills: Optional[Set[str]] = None,
    external_dirs: Optional[List[Path]] = None,
) -> str:
    """
    构建用于系统提示的技能索引（Tier 1）

    Args:
        skills_dir: 技能目录，默认使用配置的技能目录
        platform: 当前平台，用于平台过滤
        disabled_skills: 禁用的技能集合
        external_dirs: 外部技能目录列表

    Returns:
        格式化的技能索引字符串
    """
    if skills_dir is None:
        from common.config import get_skills_dir
        skills_dir = get_skills_dir()

    skills_dir = Path(skills_dir)
    if not skills_dir.exists():
        return ""

    disabled = disabled_skills or set()
    platform = platform or _get_current_platform()

    # 创建缓存管理器
    cache = SkillsIndexCache(skills_dir)

    # 生成缓存键
    external_dirs_tuple = tuple(
        str(d.resolve()) for d in (external_dirs or [])
    )
    cache_key = cache._get_cache_key(platform, disabled, external_dirs_tuple)

    # 检查内存缓存
    with _CACHE_LOCK:
        if cache_key in _PROMPT_CACHE:
            # 移到末尾（LRU 更新）
            _PROMPT_CACHE.move_to_end(cache_key)
            logger.debug("Using in-memory cache")
            return _PROMPT_CACHE[cache_key]

    # 尝试从磁盘快照加载
    snapshot = cache._load_snapshot()
    if snapshot:
        prompt = snapshot.get("system_prompt", "")
        if prompt:
            with _CACHE_LOCK:
                _PROMPT_CACHE[cache_key] = prompt
                _evict_if_needed()
            return prompt

    # 冷启动：构建新索引
    logger.info("Building fresh skills index for system prompt")
    prompt = _build_fresh_skills_prompt(
        skills_dir, platform, disabled, external_dirs
    )

    # 缓存结果
    with _CACHE_LOCK:
        _PROMPT_CACHE[cache_key] = prompt
        _evict_if_needed()

    # 更新磁盘快照
    cache.cache_prompt(prompt)

    return prompt


def _build_fresh_skills_prompt(
    skills_dir: Path,
    platform: str,
    disabled: Set[str],
    external_dirs: Optional[List[Path]],
) -> str:
    """构建全新的技能索引"""
    from agent.skill_platform import skill_matches_platform
    from agent.skill_utils import iter_skill_index_files, parse_frontmatter

    skills_by_category: Dict[str, List[Tuple[str, str]]] = {}
    category_descriptions: Dict[str, str] = {}

    # 扫描主技能目录
    for skill_md in iter_skill_index_files(skills_dir, "SKILL.md"):
        try:
            content = skill_md.read_text(encoding="utf-8")
            frontmatter, body = parse_frontmatter(content)

            name = frontmatter.get("name") or skill_md.parent.name
            if name in disabled:
                continue

            # 平台过滤
            if not skill_matches_platform(frontmatter):
                continue

            category = frontmatter.get("category", "general")
            description = frontmatter.get("description", "")

            skills_by_category.setdefault(category, []).append((name, description))

        except Exception as e:
            logger.debug(f"Error reading skill {skill_md}: {e}")

    # 扫描外部目录
    if external_dirs:
        for ext_dir in external_dirs:
            if not ext_dir.exists() or ext_dir.resolve() == skills_dir.resolve():
                continue

            for skill_md in iter_skill_index_files(ext_dir, "SKILL.md"):
                try:
                    content = skill_md.read_text(encoding="utf-8")
                    frontmatter, body = parse_frontmatter(content)

                    name = frontmatter.get("name") or skill_md.parent.name
                    if name in disabled:
                        continue

                    if not skill_matches_platform(frontmatter):
                        continue

                    category = frontmatter.get("category", "general")
                    description = frontmatter.get("description", "")

                    # 避免重复
                    existing = skills_by_category.get(category, [])
                    if not any(n == name for n, _ in existing):
                        skills_by_category.setdefault(category, []).append((name, description))

                except Exception as e:
                    logger.debug(f"Error reading external skill {skill_md}: {e}")

    # 扫描分类描述文件
    for desc_file in skills_dir.glob("*/DESCRIPTION.md"):
        try:
            content = desc_file.read_text(encoding="utf-8")
            frontmatter, _ = parse_frontmatter(content)
            cat_desc = frontmatter.get("description", "")
            if cat_desc:
                rel = desc_file.relative_to(skills_dir)
                category = rel.parts[0] if rel.parts else "general"
                category_descriptions[category] = cat_desc.strip().strip("'\"")
        except Exception:
            pass

    # 构建输出
    if not skills_by_category:
        return ""

    index_lines = []
    for category in sorted(skills_by_category.keys()):
        cat_desc = category_descriptions.get(category, "")
        if cat_desc:
            index_lines.append(f"  {category}: {cat_desc}")
        else:
            index_lines.append(f"  {category}:")

        # 分类内去重并排序
        seen = set()
        for name, desc in sorted(skills_by_category[category], key=lambda x: x[0]):
            if name in seen:
                continue
            seen.add(name)
            if desc:
                index_lines.append(f"    - {name}: {desc}")
            else:
                index_lines.append(f"    - {name}")

    return (
        "## Available Skills\n"
        "Scan the skills below. If a skill matches or is partially relevant "
        "to your task, load it with skill_view(name) and follow its instructions.\n"
        "It is better to have context you don't need than to miss critical steps.\n"
        "\n"
        "<available_skills>\n"
        + "\n".join(index_lines) + "\n"
        + "</available_skills>\n"
        "\n"
        "Use /skill-name to activate a skill."
    )


def _evict_if_needed() -> None:
    """LRU 缓存淘汰"""
    global _PROMPT_CACHE
    while len(_PROMPT_CACHE) > _PROMPT_CACHE_MAX:
        _PROMPT_CACHE.popitem(last=False)


def _get_current_platform() -> str:
    """获取当前平台"""
    import sys
    return sys.platform


# ============================================================================
# Tier 2: 完整技能内容加载
# ============================================================================

class SkillLoader:
    """
    技能内容加载器

    负责 Tier 2 完整技能内容的加载和模板处理。
    """

    def __init__(self, skills_dir: Optional[Path] = None):
        if skills_dir is None:
            from common.config import get_skills_dir
            skills_dir = get_skills_dir()
        self.skills_dir = Path(skills_dir)

        # 加载中的技能（防止重复加载）
        self._loading: Set[str] = set()
        self._lock = threading.Lock()

    def load_skill(
        self,
        skill_name: str,
        session_id: Optional[str] = None,
        substitute_vars: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        加载完整技能内容（Tier 2）

        Args:
            skill_name: 技能名称
            session_id: 会话 ID（用于模板变量替换）
            substitute_vars: 是否执行模板变量替换

        Returns:
            技能内容字典，包含 name, description, content, path 等
        """
        # 查找技能文件
        skill_path = self._find_skill_path(skill_name)
        if not skill_path:
            logger.warning(f"Skill not found: {skill_name}")
            return None

        try:
            content = skill_path.read_text(encoding="utf-8")
            from agent.skill_utils import parse_frontmatter

            frontmatter, body = parse_frontmatter(content)

            result: Dict[str, Any] = {
                "name": frontmatter.get("name") or skill_path.parent.name,
                "description": frontmatter.get("description", ""),
                "content": body.strip(),
                "path": str(skill_path.parent),
                "category": frontmatter.get("category", "general"),
                "tags": frontmatter.get("tags", []),
                "metadata": frontmatter,
            }

            # 模板变量替换
            if substitute_vars:
                from agent.skill_preprocessing import preprocess_skill_content
                processed, _ = preprocess_skill_content(
                    result["content"],
                    skill_dir=skill_path.parent,
                    session_id=session_id,
                )
                result["content"] = processed

            return result

        except Exception as e:
            logger.error(f"Failed to load skill {skill_name}: {e}")
            return None

    def _find_skill_path(self, skill_name: str) -> Optional[Path]:
        """查找技能文件路径"""
        from agent.skill_utils import iter_skill_index_files

        # 精确匹配
        for skill_md in iter_skill_index_files(self.skills_dir, "SKILL.md"):
            try:
                content = skill_md.read_text(encoding="utf-8")
                from agent.skill_utils import parse_frontmatter
                frontmatter, _ = parse_frontmatter(content)
                name = frontmatter.get("name") or skill_md.parent.name
                if name == skill_name:
                    return skill_md
            except Exception:
                continue

        # 按目录名匹配
        for skill_md in iter_skill_index_files(self.skills_dir, "SKILL.md"):
            if skill_md.parent.name == skill_name:
                return skill_md

        return None

    def get_skill_metadata(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """获取技能元数据（不含内容）"""
        skill_path = self._find_skill_path(skill_name)
        if not skill_path:
            return None

        try:
            content = skill_path.read_text(encoding="utf-8")
            from agent.skill_utils import parse_frontmatter
            frontmatter, _ = parse_frontmatter(content)

            return {
                "name": frontmatter.get("name") or skill_path.parent.name,
                "description": frontmatter.get("description", ""),
                "category": frontmatter.get("category", "general"),
                "tags": frontmatter.get("tags", []),
                "platforms": frontmatter.get("platforms", []),
                "path": str(skill_path.parent),
            }
        except Exception:
            return None

    def check_skill_readiness(self, skill_name: str) -> Tuple[bool, List[str], List[str]]:
        """
        检查技能是否就绪（前置条件验证）

        检查技能声明的环境变量和工具是否满足。

        Args:
            skill_name: 技能名称

        Returns:
            Tuple[is_ready, missing_env_vars, missing_tools]
            - is_ready: 技能是否就绪
            - missing_env_vars: 缺失的环境变量列表
            - missing_tools: 缺失的工具列表（暂不支持）
        """
        skill_path = self._find_skill_path(skill_name)
        if not skill_path:
            return False, [], []

        try:
            content = skill_path.read_text(encoding="utf-8")
            from agent.skill_utils import parse_frontmatter
            frontmatter, _ = parse_frontmatter(content)

            # 检查环境变量
            from tools.skill_env_collector import extract_required_env_vars, get_missing_env_vars
            env_requirements = extract_required_env_vars(frontmatter)
            missing_env_vars = get_missing_env_vars(env_requirements)

            # 检查 prerequisites.tools
            missing_tools = []
            prereqs = frontmatter.get("prerequisites", {})
            for tool in prereqs.get("tools", []):
                # 检查工具是否可用（通过检查全局工具注册）
                tool_name = str(tool).lstrip("!")
                if not self._check_tool_available(tool_name):
                    missing_tools.append(tool_name)

            is_ready = len(missing_env_vars) == 0 and len(missing_tools) == 0
            return is_ready, missing_env_vars, missing_tools

        except Exception as e:
            logger.error(f"Failed to check skill readiness for {skill_name}: {e}")
            return False, [], []

    def _check_tool_available(self, tool_name: str) -> bool:
        """检查工具是否可用"""
        try:
            from tools.schema_registry import get_tool_registry
            registry = get_tool_registry()
            return tool_name in registry.get_all_tool_names()
        except Exception:
            # 如果无法获取工具注册表，假设工具不可用
            return False

    def get_readiness_report(self, skill_name: str) -> Dict[str, Any]:
        """
        获取技能就绪状态报告

        Args:
            skill_name: 技能名称

        Returns:
            就绪状态报告字典
        """
        is_ready, missing_env_vars, missing_tools = self.check_skill_readiness(skill_name)
        skill_path = self._find_skill_path(skill_name)

        if not skill_path:
            return {"ready": False, "error": "Skill not found"}

        try:
            content = skill_path.read_text(encoding="utf-8")
            from agent.skill_utils import parse_frontmatter
            frontmatter, _ = parse_frontmatter(content)

            from tools.skill_env_collector import extract_required_env_vars
            env_requirements = extract_required_env_vars(frontmatter)

            env_status = []
            for req in env_requirements:
                env_status.append({
                    "name": req.name,
                    "required": not req.optional,
                    "set": bool(__import__("os").getenv(req.name)),
                    "prompt": req.prompt,
                })

            return {
                "ready": is_ready,
                "skill_name": skill_name,
                "environment_variables": env_status,
                "missing_env_vars": missing_env_vars,
                "missing_tools": missing_tools,
            }

        except Exception as e:
            return {"ready": False, "error": str(e)}


# ============================================================================
# Tier 3: 支持文件按需加载
# ============================================================================

class SupportFileLoader:
    """
    技能支持文件加载器

    负责 Tier 3 按需加载技能目录中的辅助文件。
    """

    # 支持的文件类型
    SUPPORTED_EXTENSIONS = {
        ".md", ".txt", ".py", ".sh", ".bash",
        ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
        ".html", ".css", ".js", ".ts",
    }

    # 忽略的文件/目录
    IGNORED_PATTERNS = {
        "__pycache__", ".git", ".pytest_cache",
        "node_modules", ".venv", "venv",
        ".DS_Store", "Thumbs.db",
    }

    def __init__(self, skill_dir: Optional[Path] = None):
        self.skill_dir = Path(skill_dir) if skill_dir else None

    def list_support_files(self, skill_dir: Path) -> List[Dict[str, Any]]:
        """
        列出技能目录中的支持文件

        Returns:
            支持文件信息列表 [{name, path, size, type}]
        """
        if not skill_dir.exists():
            return []

        files = []
        for item in skill_dir.iterdir():
            # 忽略自身（SKILL.md）
            if item.name == "SKILL.md":
                continue

            # 忽略模式匹配
            if item.name in self.IGNORED_PATTERNS:
                continue

            if item.is_file():
                ext = item.suffix.lower()
                if ext in self.SUPPORTED_EXTENSIONS:
                    try:
                        size = item.stat().st_size
                        files.append({
                            "name": item.name,
                            "path": str(item),
                            "relative_path": str(item.relative_to(skill_dir)),
                            "size": size,
                            "type": "file",
                        })
                    except OSError:
                        pass
            elif item.is_dir():
                # 递归列出子目录中的文件
                sub_files = self._list_dir_files(item, skill_dir)
                files.extend(sub_files)

        return sorted(files, key=lambda x: x["relative_path"])

    def _list_dir_files(
        self,
        directory: Path,
        base_dir: Path,
        max_depth: int = 2,
    ) -> List[Dict[str, Any]]:
        """递归列出目录中的文件"""
        if max_depth <= 0:
            return []

        files = []
        for item in directory.iterdir():
            if item.name in self.IGNORED_PATTERNS:
                continue

            if item.is_file():
                ext = item.suffix.lower()
                if ext in self.SUPPORTED_EXTENSIONS:
                    try:
                        files.append({
                            "name": item.name,
                            "path": str(item),
                            "relative_path": str(item.relative_to(base_dir)),
                            "size": item.stat().st_size,
                            "type": "file",
                        })
                    except OSError:
                        pass
            elif item.is_dir():
                files.extend(self._list_dir_files(item, base_dir, max_depth - 1))

        return files

    def load_file_content(self, file_path: Path, max_size: int = 1024 * 1024) -> Optional[str]:
        """
        加载支持文件内容

        Args:
            file_path: 文件路径
            max_size: 最大文件大小（默认 1MB）

        Returns:
            文件内容或 None
        """
        if not file_path.exists():
            return None

        try:
            size = file_path.stat().st_size
            if size > max_size:
                logger.warning(f"File too large: {file_path} ({size} bytes)")
                return None

            return file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return None

    def load_skill_scripts(self, skill_dir: Path) -> Dict[str, str]:
        """
        加载技能目录中的脚本文件

        Returns:
            脚本名 -> 脚本内容的字典
        """
        scripts_dir = skill_dir / "scripts"
        if not scripts_dir.exists():
            return {}

        scripts = {}
        if scripts_dir.is_dir():
            for script in scripts_dir.iterdir():
                if script.is_file() and script.suffix in {".sh", ".bash", ".py"}:
                    content = self.load_file_content(script)
                    if content:
                        scripts[script.name] = content

        return scripts


# ============================================================================
# 渐进式披露管理器
# ============================================================================

class ProgressiveDisclosureManager:
    """
    渐进式披露管理器

    整合三层披露机制，提供统一的技能内容访问接口。
    """

    def __init__(self, skills_dir: Optional[Path] = None):
        from common.config import get_skills_dir

        self.skills_dir = Path(skills_dir) if skills_dir else get_skills_dir()
        self.index_cache = SkillsIndexCache(self.skills_dir)
        self.skill_loader = SkillLoader(self.skills_dir)
        self.support_loader = SupportFileLoader()

    def get_system_prompt_index(self) -> str:
        """
        获取 Tier 1 系统提示索引

        Returns:
            用于系统提示的技能索引
        """
        from agent.skill_platform import get_disabled_skill_names

        disabled = get_disabled_skill_names()
        return build_skills_index_for_prompt(
            skills_dir=self.skills_dir,
            disabled_skills=disabled,
        )

    def load_skill_content(
        self,
        skill_name: str,
        session_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        获取 Tier 2 完整技能内容

        Args:
            skill_name: 技能名称
            session_id: 会话 ID

        Returns:
            技能内容字典
        """
        return self.skill_loader.load_skill(skill_name, session_id)

    def load_support_files(
        self,
        skill_name: str,
        include_scripts: bool = True,
    ) -> Dict[str, Any]:
        """
        获取 Tier 3 支持文件

        Args:
            skill_name: 技能名称
            include_scripts: 是否包含脚本文件

        Returns:
            支持文件信息 {files: [...], scripts: {...}}
        """
        metadata = self.skill_loader.get_skill_metadata(skill_name)
        if not metadata:
            return {"files": [], "scripts": {}}

        skill_dir = Path(metadata["path"])
        result: Dict[str, Any] = {
            "files": self.support_loader.list_support_files(skill_dir),
        }

        if include_scripts:
            result["scripts"] = self.support_loader.load_skill_scripts(skill_dir)

        return result

    def invalidate_cache(self) -> None:
        """使所有缓存失效"""
        self.index_cache.invalidate()

    def check_skill_readiness(self, skill_name: str) -> Tuple[bool, List[str], List[str]]:
        """
        检查技能是否就绪

        Returns:
            Tuple[is_ready, missing_env_vars, missing_tools]
        """
        return self.skill_loader.check_skill_readiness(skill_name)

    def get_readiness_report(self, skill_name: str) -> Dict[str, Any]:
        """获取技能就绪状态报告"""
        return self.skill_loader.get_readiness_report(skill_name)

    def get_skill_tier_info(self, skill_name: str) -> Dict[str, Any]:
        """
        获取技能的层级信息

        Returns:
            包含各层级可用信息的字典
        """
        result: Dict[str, Any] = {"tier1": False, "tier2": False, "tier3": False}

        # Tier 1: 检查是否在索引中
        metadata = self.skill_loader.get_skill_metadata(skill_name)
        if metadata:
            result["tier1"] = True
            result["metadata"] = metadata

        # Tier 2: 检查是否能加载完整内容
        content = self.skill_loader.load_skill(skill_name, substitute_vars=False)
        if content:
            result["tier2"] = True
            result["has_content"] = bool(content.get("content"))

        # Tier 3: 检查是否有支持文件
        if metadata:
            support = self.load_support_files(skill_name)
            result["tier3"] = len(support.get("files", [])) > 0 or len(support.get("scripts", {})) > 0

        return result


# ============================================================================
# 全局实例和便捷函数
# ============================================================================

_manager: Optional[ProgressiveDisclosureManager] = None


def get_progressive_disclosure_manager() -> ProgressiveDisclosureManager:
    """获取全局渐进式披露管理器"""
    global _manager
    if _manager is None:
        _manager = ProgressiveDisclosureManager()
    return _manager


def get_skills_system_prompt() -> str:
    """获取用于系统提示的技能索引（Tier 1）"""
    return get_progressive_disclosure_manager().get_system_prompt_index()


def load_skill_full(skill_name: str, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """加载完整技能内容（Tier 2）"""
    return get_progressive_disclosure_manager().load_skill_content(skill_name, session_id)


def get_skill_support_files(skill_name: str) -> Dict[str, Any]:
    """获取技能支持文件（Tier 3）"""
    return get_progressive_disclosure_manager().load_support_files(skill_name)


def invalidate_skills_cache() -> None:
    """使技能缓存失效"""
    get_progressive_disclosure_manager().invalidate_cache()


def check_skill_readiness(skill_name: str) -> Tuple[bool, List[str], List[str]]:
    """
    检查技能是否就绪

    Args:
        skill_name: 技能名称

    Returns:
        Tuple[is_ready, missing_env_vars, missing_tools]
    """
    return get_progressive_disclosure_manager().check_skill_readiness(skill_name)


def get_skill_readiness_report(skill_name: str) -> Dict[str, Any]:
    """获取技能就绪状态报告"""
    return get_progressive_disclosure_manager().get_readiness_report(skill_name)


# ============================================================================
# SkillRecommender 集成
# ============================================================================

def get_skill_recommender() -> "SkillRecommender":
    """获取技能推荐器（基于渐进式披露的技能数据）"""
    from agent.skill_recommender import SkillRecommender, create_recommender_from_skills

    # 从 progressive_disclosure 加载技能数据
    manager = get_progressive_disclosure_manager()
    skills_data = []

    # 获取所有技能
    from agent.skill_utils import iter_skill_index_files, parse_frontmatter

    for skill_md in iter_skill_index_files(manager.skills_dir, "SKILL.md"):
        try:
            content = skill_md.read_text(encoding="utf-8")
            frontmatter, _ = parse_frontmatter(content)

            # 检查平台兼容性
            from agent.skill_platform import skill_matches_platform
            if not skill_matches_platform(frontmatter):
                continue

            skills_data.append({
                "skill_id": frontmatter.get("name") or skill_md.parent.name,
                "name": frontmatter.get("name") or skill_md.parent.name,
                "description": frontmatter.get("description", ""),
                "tags": frontmatter.get("tags", []),
                "category": frontmatter.get("category", "general"),
            })
        except Exception:
            continue

    return create_recommender_from_skills(skills_data)


def recommend_skills(
    description: str,
    top_n: int = 5,
) -> List[Dict[str, Any]]:
    """
    根据描述推荐技能

    Args:
        description: 用户描述或查询
        top_n: 返回数量

    Returns:
        推荐的技能列表
    """
    recommender = get_skill_recommender()
    results = recommender.recommend_by_description(description, top_n=top_n)

    return [
        {
            "skill_id": r.skill.skill_id,
            "name": r.skill.name,
            "description": r.skill.description,
            "score": r.total_score,
            "matched_keywords": r.matched_keywords,
        }
        for r in results
    ]
