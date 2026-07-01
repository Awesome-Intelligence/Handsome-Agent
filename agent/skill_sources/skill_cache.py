#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集中缓存模块 - 统一管理技能相关缓存

提供多层缓存策略：
- 索引缓存（远程索引的本地副本）
- 搜索结果缓存（API 调用结果）
- GitHub Repo 树缓存（避免重复 API 调用）

📋 Logging Layer: SkillCache
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ============================================================================
# 缓存配置
# ============================================================================

# 索引缓存 TTL
INDEX_CACHE_TTL = 3600  # 1 小时

# Hermes 集中索引 TTL
HERMES_INDEX_TTL = 6 * 3600  # 6 小时

# 搜索结果缓存 TTL
SEARCH_CACHE_TTL = 300  # 5 分钟

# GitHub Repo 树缓存 TTL
GITHUB_TREE_CACHE_TTL = 1800  # 30 分钟


# ============================================================================
# 缓存目录管理
# ============================================================================

def get_cache_dir() -> Path:
    """获取缓存根目录"""
    from common.config import get_config_dir
    return get_config_dir() / ".hub" / "cache"


def get_index_cache_dir() -> Path:
    """获取索引缓存目录"""
    return get_cache_dir() / "index"


def get_github_cache_dir() -> Path:
    """获取 GitHub 缓存目录"""
    return get_cache_dir() / "github"


def ensure_cache_dirs() -> None:
    """确保所有缓存目录存在"""
    for cache_dir in [get_cache_dir(), get_index_cache_dir(), get_github_cache_dir()]:
        cache_dir.mkdir(parents=True, exist_ok=True)


# ============================================================================
# 基础缓存操作
# ============================================================================

def read_cache(cache_file: Path, ttl: int) -> Optional[Any]:
    """读取缓存文件（如果未过期）

    Args:
        cache_file: 缓存文件路径
        ttl: 缓存有效期（秒）

    Returns:
        缓存数据或 None
    """
    if not cache_file.exists():
        return None

    try:
        stat = cache_file.stat()
        if time.time() - stat.st_mtime > ttl:
            return None

        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.debug(f"Failed to read cache {cache_file}: {e}")
        return None


def write_cache(cache_file: Path, data: Any) -> bool:
    """写入缓存文件

    Args:
        cache_file: 缓存文件路径
        data: 要缓存的数据

    Returns:
        是否成功
    """
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, default=str)
        return True
    except Exception as e:
        logger.debug(f"Failed to write cache {cache_file}: {e}")
        return False


def read_stale_cache(cache_file: Path) -> Optional[Any]:
    """读取过期的缓存（作为降级方案）"""
    if not cache_file.exists():
        return None

    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def clear_cache(cache_type: str = "all") -> Dict[str, int]:
    """清除缓存

    Args:
        cache_type: "all" | "index" | "github" | "search"

    Returns:
        被删除的文件数
    """
    counts = {"index": 0, "github": 0, "search": 0}

    if cache_type in ("all", "index"):
        index_dir = get_index_cache_dir()
        if index_dir.exists():
            for f in index_dir.glob("*.json"):
                f.unlink()
                counts["index"] += 1

    if cache_type in ("all", "github"):
        github_dir = get_github_cache_dir()
        if github_dir.exists():
            for f in github_dir.glob("*.json"):
                f.unlink()
                counts["github"] += 1

    return counts


# ============================================================================
# 索引缓存
# ============================================================================

def read_hermes_index_cache() -> Optional[Dict[str, Any]]:
    """读取 Hermes 集中索引缓存"""
    cache_file = get_index_cache_dir() / "hermes-index.json"
    return read_cache(cache_file, HERMES_INDEX_TTL)


def write_hermes_index_cache(data: Dict[str, Any]) -> bool:
    """写入 Hermes 集中索引缓存"""
    cache_file = get_index_cache_dir() / "hermes-index.json"
    return write_cache(cache_file, data)


def read_hermes_stale_index_cache() -> Optional[Dict[str, Any]]:
    """读取过期的 Hermes 索引缓存"""
    cache_file = get_index_cache_dir() / "hermes-index.json"
    return read_stale_cache(cache_file)


# ============================================================================
# GitHub 树缓存
# ============================================================================

class GitHubTreeCache:
    """
    GitHub Repo 树缓存管理器。

    使用 Trees API 单次调用获取整个仓库结构，避免重复 API 调用。
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        if cache_dir is None:
            cache_dir = get_github_cache_dir()
        self._cache_dir = Path(cache_dir)
        self._memory_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}

    def get(self, repo: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存的 repo 树。

        Args:
            repo: 仓库名 (owner/repo)

        Returns:
            树数据或 None
        """
        # 检查内存缓存
        if repo in self._memory_cache:
            timestamp, data = self._memory_cache[repo]
            if time.time() - timestamp < GITHUB_TREE_CACHE_TTL:
                return data

        # 检查文件缓存
        cache_file = self._cache_dir / f"{repo.replace('/', '_')}.json"
        cached = read_cache(cache_file, GITHUB_TREE_CACHE_TTL)
        if cached:
            self._memory_cache[repo] = (time.time(), cached)
            return cached

        return None

    def set(self, repo: str, data: Dict[str, Any]) -> None:
        """
        设置 repo 树缓存。

        Args:
            repo: 仓库名
            data: 树数据
        """
        # 更新内存缓存
        self._memory_cache[repo] = (time.time(), data)

        # 更新文件缓存
        cache_file = self._cache_dir / f"{repo.replace('/', '_')}.json"
        write_cache(cache_file, data)

    def clear(self, repo: Optional[str] = None) -> None:
        """
        清除缓存。

        Args:
            repo: 如果指定，只清除该仓库的缓存；否则清除所有
        """
        if repo:
            # 清除内存
            self._memory_cache.pop(repo, None)
            # 清除文件
            cache_file = self._cache_dir / f"{repo.replace('/', '_')}.json"
            if cache_file.exists():
                cache_file.unlink()
        else:
            # 清除所有
            self._memory_cache.clear()
            clear_cache("github")


# 全局实例
_github_tree_cache: Optional[GitHubTreeCache] = None


def get_github_tree_cache() -> GitHubTreeCache:
    """获取全局 GitHub 树缓存实例"""
    global _github_tree_cache
    if _github_tree_cache is None:
        _github_tree_cache = GitHubTreeCache()
    return _github_tree_cache


# ============================================================================
# 搜索结果缓存
# ============================================================================

class SearchResultCache:
    """
    搜索结果缓存管理器。
    """

    def __init__(self, ttl: int = SEARCH_CACHE_TTL):
        self._ttl = ttl
        self._cache_dir = get_cache_dir() / "search"
        self._memory_cache: Dict[str, Tuple[float, List[Any]]] = {}

    def get(self, query: str, source: str) -> Optional[List[Any]]:
        """
        获取缓存的搜索结果。

        Args:
            query: 搜索查询
            source: 来源标识

        Returns:
            搜索结果或 None
        """
        key = f"{source}:{query.lower().strip()}"

        # 检查内存缓存
        if key in self._memory_cache:
            timestamp, data = self._memory_cache[key]
            if time.time() - timestamp < self._ttl:
                return data

        # 检查文件缓存
        cache_file = self._cache_dir / f"{hash(key)}.json"
        cached = read_cache(cache_file, self._ttl)
        if cached:
            self._memory_cache[key] = (time.time(), cached)
            return cached

        return None

    def set(self, query: str, source: str, results: List[Any]) -> None:
        """
        缓存搜索结果。

        Args:
            query: 搜索查询
            source: 来源标识
            results: 搜索结果
        """
        key = f"{source}:{query.lower().strip()}"

        # 更新内存缓存
        self._memory_cache[key] = (time.time(), results)

        # 更新文件缓存
        cache_file = self._cache_dir / f"{hash(key)}.json"
        write_cache(cache_file, results)

    def clear(self) -> None:
        """清除所有搜索缓存"""
        self._memory_cache.clear()
        if self._cache_dir.exists():
            for f in self._cache_dir.glob("*.json"):
                f.unlink()


# 全局实例
_search_result_cache: Optional[SearchResultCache] = None


def get_search_result_cache() -> SearchResultCache:
    """获取全局搜索结果缓存实例"""
    global _search_result_cache
    if _search_result_cache is None:
        _search_result_cache = SearchResultCache()
    return _search_result_cache


# ============================================================================
# 缓存统计
# ============================================================================

def get_cache_stats() -> Dict[str, Any]:
    """
    获取缓存统计信息。

    Returns:
        缓存统计字典
    """
    stats = {
        "index": {"count": 0, "size_bytes": 0},
        "github": {"count": 0, "size_bytes": 0},
        "search": {"count": 0, "size_bytes": 0},
    }

    cache_dir = get_cache_dir()
    if not cache_dir.exists():
        return stats

    for subdir in ["index", "github", "search"]:
        subdir_path = cache_dir / subdir
        if subdir_path.exists():
            files = list(subdir_path.glob("*.json"))
            stats[subdir]["count"] = len(files)
            stats[subdir]["size_bytes"] = sum(f.stat().st_size for f in files)

    return stats
