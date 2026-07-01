#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skills.sh 来源适配器

从 skills.sh 社区平台获取技能。

skills.sh 是一个标准化的技能索引协议，支持 /.well-known/skills 端点。

📋 Logging Layer: SkillsShSource
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from .base import SkillSource, SourceResult, SourceSkillInfo
from .github_auth import GitHubAuth

logger = logging.getLogger(__name__)

# skills.sh API 端点
SKILLS_SH_INDEX_URL = "https://skills.sh/index.json"
SKILLS_SH_API_URL = "https://skills.sh/api/skills"


class SkillsShSource(SkillSource):
    """
    Skills.sh 社区技能来源。

    支持：
    - 从 skills.sh 索引搜索技能
    - 直接从 GitHub 安装技能（通过 skills.sh 代理）
    - 解析 skills.sh 格式的技能引用
    """

    SOURCE_TYPE = "skills-sh"

    # 信任级别
    TRUST_LEVEL = "community"

    def __init__(self, auth: Optional[GitHubAuth] = None):
        super().__init__("Skills.sh")
        self.auth = auth or GitHubAuth()
        self._index_cache: Optional[List[Dict[str, Any]]] = None
        self._index_loaded = False

    @property
    def source_type(self) -> str:
        return self.SOURCE_TYPE

    def parse_ref(self, ref: str) -> Optional[Dict[str, Any]]:
        """解析 skills.sh 格式的技能引用

        支持格式：
        - skills-sh:owner/repo/skill-name
        - owner/repo/skill-name (通过 skills.sh 索引)
        """
        # 直接格式
        pattern = re.compile(r'^skills-sh:([^/]+)/([^/]+)/([^/]+)$')
        match = pattern.match(ref.lower())
        if match:
            return {
                'owner': match.group(1),
                'repo': match.group(2),
                'skill': match.group(3),
            }

        # 简略格式 - 通过索引解析
        pattern = re.compile(r'^([^/]+)/([^/]+)/([^/]+)$')
        match = pattern.match(ref.lower())
        if match:
            return {
                'owner': match.group(1),
                'repo': match.group(2),
                'skill': match.group(3),
            }

        return None

    async def search(self, query: str) -> List[SourceSkillInfo]:
        """从 skills.sh 搜索技能"""
        results = []

        try:
            # 尝试从索引获取
            skills = await self._fetch_index()
            if not skills:
                return results

            query_lower = query.lower().strip()
            for skill in skills:
                name = skill.get('name', '').lower()
                desc = skill.get('description', '').lower()
                tags = ' '.join(skill.get('tags', [])).lower()

                searchable = f"{name} {desc} {tags}"
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

        except Exception as e:
            logger.debug(f"Skills.sh search failed: {e}")

        return results

    async def install(self, skill_ref: str, target_dir: Path) -> SourceResult:
        """从 skills.sh 安装技能"""
        parsed = self.parse_ref(skill_ref)
        if not parsed:
            return SourceResult(
                success=False,
                skill_name="",
                error=f"Invalid skills.sh reference: {skill_ref}",
                source_name=self.name,
            )

        try:
            import aiohttp

            owner = parsed['owner']
            repo = parsed['repo']
            skill_name = parsed['skill']

            # 尝试从 skills.sh API 获取安装 URL
            url = f"{SKILLS_SH_API_URL}/{owner}/{repo}/{skill_name}/download"
            headers = self.auth.get_headers()

            async with aiohttp.ClientSession() as session:
                # 获取下载链接
                async with session.get(url, headers=headers) as resp:
                    if resp.status != 200:
                        return SourceResult(
                            success=False,
                            skill_name=skill_name,
                            error=f"Skill not found on skills.sh: {owner}/{repo}/{skill_name}",
                            source_name=self.name,
                        )

                    data = await resp.json()
                    download_url = data.get('download_url')

                    if not download_url:
                        return SourceResult(
                            success=False,
                            skill_name=skill_name,
                            error="No download URL provided",
                            source_name=self.name,
                        )

                    # 下载技能
                    skill_dir = target_dir / skill_name
                    success = await self._download_skill(
                        session, download_url, skill_dir
                    )

                    if success:
                        return SourceResult(
                            success=True,
                            skill_name=skill_name,
                            metadata={'path': str(skill_dir)},
                            source_name=self.name,
                        )
                    else:
                        return SourceResult(
                            success=False,
                            skill_name=skill_name,
                            error="Failed to download skill files",
                            source_name=self.name,
                        )

        except ImportError:
            return SourceResult(
                success=False,
                skill_name="",
                error="aiohttp not available",
                source_name=self.name,
            )
        except Exception as e:
            logger.error(f"Skills.sh install failed: {e}")
            return SourceResult(
                success=False,
                skill_name=parsed.get('skill', ''),
                error=str(e),
                source_name=self.name,
            )

    async def _fetch_index(self) -> List[Dict[str, Any]]:
        """获取 skills.sh 索引"""
        if self._index_loaded and self._index_cache is not None:
            return self._index_cache

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(SKILLS_SH_INDEX_URL, timeout=15) as resp:
                    if resp.status == 200:
                        self._index_cache = await resp.json()
                        self._index_loaded = True
                        return self._index_cache or []

        except Exception as e:
            logger.debug(f"Failed to fetch skills.sh index: {e}")

        return []

    async def _download_skill(
        self,
        session: 'aiohttp.ClientSession',
        url: str,
        target_dir: Path
    ) -> bool:
        """下载技能文件到目标目录"""
        try:
            async with session.get(url, timeout=30) as resp:
                if resp.status != 200:
                    return False

                import zipfile
                import io

                content = await resp.read()
                target_dir.mkdir(parents=True, exist_ok=True)

                # 解压 ZIP
                with zipfile.ZipFile(io.BytesIO(content)) as zf:
                    zf.extractall(target_dir)

                return True

        except Exception as e:
            logger.debug(f"Failed to download skill: {e}")
            return False

    def list_all(self) -> List[SourceSkillInfo]:
        """列出所有可用技能（同步版本）"""
        try:
            import httpx
            resp = httpx.get(SKILLS_SH_INDEX_URL, timeout=15)
            if resp.status_code == 200:
                skills = resp.json()
                return [
                    SourceSkillInfo(
                        name=s.get('name', ''),
                        description=s.get('description', ''),
                        author=s.get('author', ''),
                        version=s.get('version', '1.0.0'),
                        source=self.name,
                        url=s.get('url', ''),
                        tags=s.get('tags', []),
                    )
                    for s in skills
                ]
        except Exception as e:
            logger.debug(f"Failed to list skills.sh skills: {e}")
        return []
