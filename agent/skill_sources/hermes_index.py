#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集中索引来源 - HermesIndexSource

通过集中索引服务进行技能搜索，无需直接调用 GitHub API。
索引每日由 CI 重建，包含所有技能的元数据 + resolved GitHub 路径。
"""

import json
import logging
import time
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

from .base import SkillSource, SourceResult, SourceSkillInfo
from .github_auth import GitHubAuth, get_github_auth

logger = logging.getLogger(__name__)

# 集中索引 URL
HERMES_INDEX_URL = "https://hermes-agent.nousresearch.com/docs/api/skills-index.json"
HERMES_INDEX_TTL = 6 * 3600  # 6 小时缓存


@dataclass
class IndexEntry:
    """索引条目"""
    identifier: str
    name: str
    description: str
    source: str
    repo: Optional[str] = None
    path: Optional[str] = None
    resolved_github_id: Optional[str] = None
    trust_level: str = "community"
    tags: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)


class HermesIndexSource(SkillSource):
    """
    集中索引来源。

    特点：
    - 搜索零 API 调用（直接从索引返回）
    - 安装时使用 resolved_github_id 直接下载
    - 索引不可用时自动降级
    """

    SOURCE_TYPE = "hermes-index"

    def __init__(self, auth: Optional[GitHubAuth] = None, cache_dir: Optional[Path] = None):
        super().__init__("Hermes Index")
        self.auth = auth or get_github_auth()
        self._index: Optional[Dict[str, Any]] = None
        self._loaded = False
        self._available = False

        # 缓存目录
        if cache_dir is None:
            from common.config import get_config_dir
            cache_dir = get_config_dir() / ".hub" / "index-cache"
        self._cache_dir = Path(cache_dir)
        self._cache_file = self._cache_dir / "hermes-index.json"

        # GitHub 源（用于实际下载）
        self._github_source: Optional['GitHubSource'] = None

    @property
    def source_type(self) -> str:
        return self.SOURCE_TYPE

    @property
    def is_available(self) -> bool:
        """索引是否可用"""
        self._ensure_loaded()
        return self._available

    def _ensure_loaded(self) -> None:
        """确保索引已加载"""
        if self._loaded:
            return

        self._loaded = True
        self._index = self._load_index()

        if self._index and self._index.get("skills"):
            self._available = True

    def _load_index(self) -> Optional[Dict[str, Any]]:
        """加载索引（从缓存或远程）"""
        # 1. 尝试从缓存加载
        cached = self._read_cache()
        if cached is not None:
            return cached

        # 2. 从远程加载
        try:
            import httpx
            resp = httpx.get(HERMES_INDEX_URL, timeout=15, follow_redirects=True)
            if resp.status_code != 200:
                logger.debug("Hermes index fetch returned %d", resp.status_code)
                return self._load_stale_cache()

            data = resp.json()
        except Exception as e:
            logger.debug("Hermes index fetch failed: %s", e)
            return self._load_stale_cache()

        # 3. 验证结构
        if not isinstance(data, dict) or "skills" not in data:
            return self._load_stale_cache()

        # 4. 缓存到本地
        self._write_cache(data)
        return data

    def _read_cache(self) -> Optional[Dict[str, Any]]:
        """读取本地缓存（如果未过期）"""
        if not self._cache_file.exists():
            return None

        try:
            stat = self._cache_file.stat()
            if time.time() - stat.st_mtime > HERMES_INDEX_TTL:
                return None

            with open(self._cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None

    def _load_stale_cache(self) -> Optional[Dict[str, Any]]:
        """加载过期的缓存（作为降级）"""
        if self._cache_file.exists():
            try:
                with open(self._cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    def _write_cache(self, data: Dict[str, Any]) -> None:
        """写入缓存"""
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            with open(self._cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, default=str)
        except Exception as e:
            logger.debug("Could not write index cache: %s", e)

    async def search(self, query: str) -> List[SourceSkillInfo]:
        """搜索索引中的技能"""
        self._ensure_loaded()

        if not self._index or not self._available:
            return []

        skills = self._index.get("skills", [])
        if not skills:
            return []

        results = []
        query_lower = query.lower().strip()

        for skill in skills:
            searchable = f"{skill.get('name', '')} {skill.get('description', '')} {' '.join(skill.get('tags', []))}".lower()

            if not query_lower or query_lower in searchable:
                results.append(SourceSkillInfo(
                    name=skill.get('name', ''),
                    description=skill.get('description', ''),
                    author=skill.get('author', ''),
                    version=skill.get('version', '1.0.0'),
                    source=self.name,
                    url=skill.get('url', ''),
                    tags=skill.get('tags', []),
                ))

            if len(results) >= 10:
                break

        return results

    async def install(self, skill_ref: str, target_dir: Path) -> SourceResult:
        """从索引安装技能"""
        self._ensure_loaded()

        if not self._index or not self._available:
            return SourceResult(
                success=False,
                skill_name="",
                error="Hermes index not available, falling back to other sources",
                source_name=self.name,
            )

        # 查找技能
        entry = self._find_entry(skill_ref)
        if not entry:
            return SourceResult(
                success=False,
                skill_name="",
                error=f"Skill not found in index: {skill_ref}",
                source_name=self.name,
            )

        # 使用 resolved path 直接下载
        resolved = entry.get('resolved_github_id')
        if not resolved:
            repo = entry.get('repo', '')
            path = entry.get('path', '')
            if repo and path:
                resolved = f"{repo}/{path}"

        if not resolved:
            return SourceResult(
                success=False,
                skill_name=entry.get('name', ''),
                error="No resolved GitHub path available",
                source_name=self.name,
            )

        # 通过 GitHubSource 下载
        from .github import GitHubSource
        github = GitHubSource(auth=self.auth)
        return await github.install(f"github:{resolved}", target_dir)

    def parse_ref(self, ref: str) -> Optional[Dict[str, Any]]:
        """解析技能引用"""
        # 尝试匹配索引中的 identifier
        self._ensure_loaded()

        if not self._index:
            return None

        # 去掉前缀
        normalized = ref
        for prefix in ("hermes-index/", "hermes/", ""):
            if ref.startswith(prefix):
                normalized = ref[len(prefix):]
                break

        # 在索引中查找
        entry = self._find_entry(normalized)
        if entry:
            return {
                'identifier': entry.get('identifier', ''),
                'name': entry.get('name', ''),
                'repo': entry.get('repo', ''),
                'path': entry.get('path', ''),
            }

        return None

    def _find_entry(self, identifier: str) -> Optional[Dict[str, Any]]:
        """在索引中查找技能"""
        if not self._index:
            return None

        skills = self._index.get("skills", [])

        # 精确匹配 identifier
        for skill in skills:
            sid = skill.get('identifier', '')
            if sid == identifier or sid == f"hermes-index/{identifier}":
                return skill

        # 匹配 name
        for skill in skills:
            name = skill.get('name', '').lower()
            if name == identifier.lower():
                return skill

        return None

    def list_all(self) -> List[SourceSkillInfo]:
        """列出索引中的所有技能"""
        self._ensure_loaded()

        if not self._index or not self._available:
            return []

        results = []
        for skill in self._index.get("skills", []):
            results.append(SourceSkillInfo(
                name=skill.get('name', ''),
                description=skill.get('description', ''),
                author=skill.get('author', ''),
                version=skill.get('version', '1.0.0'),
                source=self.name,
                url=skill.get('url', ''),
                tags=skill.get('tags', []),
            ))

        return results