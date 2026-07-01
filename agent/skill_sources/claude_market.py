#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude Market 来源适配器

从 Claude Code Marketplace 获取技能。

支持：
- 搜索 Claude Code Marketplace 上的公开技能
- 安装来自 Claude Market 的技能

📋 Logging Layer: ClaudeMarketSource
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import SkillSource, SourceResult, SourceSkillInfo
from .github_auth import GitHubAuth

logger = logging.getLogger(__name__)

# Claude Market API
CLAUDE_MARKET_URL = "https://api.claudemarket.ai/v1/skills"
CLAUDE_MARKET_SEARCH_URL = "https://api.claudemarket.ai/v1/skills/search"


class ClaudeMarketSource(SkillSource):
    """
    Claude Code Marketplace 技能来源。

    信任级别根据来源确定：
    - 官方认证的技能: trusted
    - 社区技能: community
    """

    SOURCE_TYPE = "claude-market"

    # Claude 官方可信仓库
    TRUSTED_REPOS = {"anthropic/claude-code"}

    def __init__(self, auth: Optional[GitHubAuth] = None):
        super().__init__("Claude Market")
        self.auth = auth or GitHubAuth()
        self._cache: Optional[List[Dict[str, Any]]] = None
        self._cache_time = 0

    @property
    def source_type(self) -> str:
        return self.SOURCE_TYPE

    def parse_ref(self, ref: str) -> Optional[Dict[str, Any]]:
        """解析 Claude Market 格式的技能引用

        支持格式：
        - claude-market:skill-id
        - claude:skill-id
        - marketplace:skill-id
        """
        patterns = [
            r'^claude-market:([a-zA-Z0-9_-]+)$',
            r'^claude:([a-zA-Z0-9_-]+)$',
            r'^marketplace:([a-zA-Z0-9_-]+)$',
            r'^([a-zA-Z0-9_-]+)$',  # 裸 ID
        ]

        for pattern in patterns:
            match = re.match(pattern, ref, re.IGNORECASE)
            if match:
                return {'skill_id': match.group(1)}

        return None

    def trust_level_for(self, identifier: str) -> str:
        """确定信任级别"""
        if identifier.startswith("anthropic/") or identifier.startswith("claude-market:official"):
            return "trusted"
        return "community"

    async def search(self, query: str) -> List[SourceSkillInfo]:
        """从 Claude Market 搜索技能"""
        results = []

        try:
            import aiohttp

            headers = self.auth.get_headers()
            headers["Accept"] = "application/json"

            params = {"q": query, "limit": 10}

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    CLAUDE_MARKET_SEARCH_URL,
                    headers=headers,
                    params=params,
                    timeout=15
                ) as resp:
                    if resp.status != 200:
                        return results

                    data = await resp.json()
                    skills = data.get('skills', [])

                    for skill in skills:
                        results.append(SourceSkillInfo(
                            name=skill.get('name', ''),
                            description=skill.get('description', ''),
                            author=skill.get('author', ''),
                            version=skill.get('version', '1.0.0'),
                            source=self.name,
                            url=skill.get('url', ''),
                            tags=skill.get('tags', []),
                        ))

        except ImportError:
            logger.warning("aiohttp not available, Claude Market search skipped")
        except Exception as e:
            logger.debug(f"Claude Market search failed: {e}")

        return results

    async def install(self, skill_ref: str, target_dir: Path) -> SourceResult:
        """从 Claude Market 安装技能"""
        parsed = self.parse_ref(skill_ref)
        if not parsed:
            return SourceResult(
                success=False,
                skill_name="",
                error=f"Invalid Claude Market reference: {skill_ref}",
                source_name=self.name,
            )

        skill_id = parsed['skill_id']

        try:
            import aiohttp

            headers = self.auth.get_headers()
            headers["Accept"] = "application/json"

            # 获取技能详情
            url = f"{CLAUDE_MARKET_URL}/{skill_id}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=15) as resp:
                    if resp.status != 200:
                        return SourceResult(
                            success=False,
                            skill_name=skill_id,
                            error=f"Skill not found: {skill_id}",
                            source_name=self.name,
                        )

                    data = await resp.json()
                    download_url = data.get('download_url')

                    if not download_url:
                        return SourceResult(
                            success=False,
                            skill_name=skill_id,
                            error="No download URL available",
                            source_name=self.name,
                        )

                    # 下载技能
                    skill_name = data.get('name', skill_id)
                    skill_dir = target_dir / skill_name

                    success = await self._download_skill(
                        session, download_url, skill_dir
                    )

                    if success:
                        return SourceResult(
                            success=True,
                            skill_name=skill_name,
                            metadata={
                                'skill_id': skill_id,
                                'path': str(skill_dir),
                            },
                            source_name=self.name,
                        )
                    else:
                        return SourceResult(
                            success=False,
                            skill_name=skill_name,
                            error="Download failed",
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
            logger.error(f"Claude Market install failed: {e}")
            return SourceResult(
                success=False,
                skill_name=skill_id,
                error=str(e),
                source_name=self.name,
            )

    async def _download_skill(
        self,
        session: 'aiohttp.ClientSession',
        url: str,
        target_dir: Path
    ) -> bool:
        """下载技能文件"""
        try:
            async with session.get(url, timeout=30) as resp:
                if resp.status != 200:
                    return False

                import zipfile
                import io

                content = await resp.read()
                target_dir.mkdir(parents=True, exist_ok=True)

                with zipfile.ZipFile(io.BytesIO(content)) as zf:
                    zf.extractall(target_dir)

                return True

        except Exception as e:
            logger.debug(f"Failed to download skill: {e}")
            return False

    def list_featured(self) -> List[SourceSkillInfo]:
        """获取精选技能"""
        try:
            import httpx
            resp = httpx.get(
                f"{CLAUDE_MARKET_URL}/featured",
                timeout=15,
                headers={"Accept": "application/json"}
            )
            if resp.status_code == 200:
                skills = resp.json().get('skills', [])
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
            logger.debug(f"Failed to get featured skills: {e}")
        return []
