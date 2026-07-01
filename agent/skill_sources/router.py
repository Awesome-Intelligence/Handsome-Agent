"""技能来源路由（增强版）

支持多个技能来源：
- Hermes 集中索引（优先）
- GitHub 仓库
- skills.sh 社区
- Claude Market
- 直接 URL

计划中的来源（尚未实现）：
- ClawHubSource - ClawHub 市场
- LobeHubSource - LobeHub agents
- BrowseShSource - browse.sh 网站自动化
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

from .base import SkillSource, SourceResult, SourceSkillInfo, SourceUpdateInfo
from .github import GitHubSource
from .url import UrlSource
from .hermes_index import HermesIndexSource
from .github_auth import GitHubAuth, get_github_auth
from .skills_sh import SkillsShSource
from .claude_market import ClaudeMarketSource
from .optional_skill import OptionalSkillSource
from .well_known import WellKnownSkillSource
from .taps_manager import get_taps_manager

logger = logging.getLogger(__name__)

# 搜索超时配置（秒）
SEARCH_TIMEOUT = 15


class SourceRouter:
    """技能来源路由器"""

    def __init__(self):
        self.sources: Dict[str, SkillSource] = {}
        self._auth = get_github_auth()
        self._taps_manager = get_taps_manager()

    def register(self, source: SkillSource):
        """注册来源"""
        self.sources[source.name] = source

    def unregister(self, name: str):
        """取消注册来源"""
        if name in self.sources:
            del self.sources[name]

    def find_source(self, ref: str) -> Optional[SkillSource]:
        """查找匹配的来源"""
        for source in self.sources.values():
            if source.parse_ref(ref):
                return source
        return None

    async def install(self, ref: str, target_dir: Path) -> SourceResult:
        """通过路由安装技能"""
        source = self.find_source(ref)
        if not source:
            return SourceResult(
                success=False,
                skill_name="",
                error=f"No source found for: {ref}",
                source_name="",
            )

        return await source.install(ref, target_dir)

    async def search(self, query: str) -> Dict[str, List[SourceSkillInfo]]:
        """并行搜索所有来源（带超时控制）"""

        async def run_search_with_timeout(source: SkillSource) -> tuple:
            """在线程池中运行搜索，带超时控制"""
            try:
                results = await asyncio.wait_for(
                    source.search(query),
                    timeout=SEARCH_TIMEOUT
                )
                return source.name, results
            except asyncio.TimeoutError:
                logger.warning(f"Search timed out for {source.name}")
                return source.name, []
            except Exception as e:
                logger.warning(f"Search failed for {source.name}: {e}")
                return source.name, []

        tasks = [run_search_with_timeout(s) for s in self.sources.values()]
        results = await asyncio.gather(*tasks)

        return dict(results)

    async def unified_search(self, query: str, max_results: int = 50) -> List[SourceSkillInfo]:
        """统一搜索（合并所有来源结果，按信任级别去重）"""
        all_results = await self.search(query)

        # 按 trust_level 排序
        trust_rank = {"builtin": 3, "trusted": 2, "indexed": 1, "community": 0}
        merged: Dict[str, SourceSkillInfo] = {}

        for source_name, results in all_results.items():
            for r in results:
                r.source = source_name
                # 使用 (name, url) 作为 key 去重
                key = (r.name, r.url)
                if key not in merged:
                    merged[key] = r
                # 保留更高信任级别的结果
                elif trust_rank.get(source_name, 0) > trust_rank.get(merged[key].source, 0):
                    merged[key] = r

        return list(merged.values())[:max_results]

    def get_github_source_with_taps(self) -> GitHubSource:
        """获取带有用户自定义 taps 的 GitHubSource"""
        taps = self._taps_manager.get_all_taps()
        extra_taps = [
            {"repo": tap.repo, "path": tap.path}
            for tap in taps
            if tap.enabled
        ]
        return GitHubSource(auth=self._auth, extra_taps=extra_taps)

    def find_source_by_type(self, source_type: str) -> Optional[SkillSource]:
        """根据来源类型查找来源"""
        for source in self.sources.values():
            if source.source_type == source_type:
                return source
        return None

    async def check_update(
        self,
        skill_name: str,
        source_type: str,
        identifier: str,
        current_hash: str = "",
    ) -> Optional[SourceUpdateInfo]:
        """检查技能更新

        Args:
            skill_name: 技能名称
            source_type: 来源类型
            identifier: 来源标识符
            current_hash: 当前内容哈希

        Returns:
            更新信息，如果没有更新返回 None
        """
        source = self.find_source_by_type(source_type)
        if not source:
            logger.warning(f"Source not found: {source_type}")
            return None

        try:
            return await source.fetch_latest(identifier, current_hash)
        except Exception as e:
            logger.error(f"Failed to check update for {skill_name}: {e}")
            return None

    async def check_all_updates(
        self,
        locked_skills: List[Dict[str, str]],
    ) -> List[SourceUpdateInfo]:
        """批量检查多个技能的更新

        Args:
            locked_skills: 锁定技能列表，每个元素包含 source_type, identifier, hash

        Returns:
            有更新的技能列表
        """
        updates = []

        async def check_one(skill: Dict[str, str]) -> Optional[SourceUpdateInfo]:
            try:
                return await self.check_update(
                    skill_name=skill.get("skill_name", ""),
                    source_type=skill.get("source", ""),
                    identifier=skill.get("identifier", ""),
                    current_hash=skill.get("hash", ""),
                )
            except Exception as e:
                logger.error(f"Check update failed: {e}")
                return None

        # 并行检查所有技能
        tasks = [check_one(skill) for skill in locked_skills]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, SourceUpdateInfo) and result.has_update:
                updates.append(result)

        return updates


def create_default_router() -> SourceRouter:
    """创建默认路由器

    按优先级注册来源：
    1. HermesIndexSource - 集中索引（零 API 调用）
    2. OptionalSkillSource - 可选内置技能
    3. SkillsShSource - skills.sh 社区
    4. WellKnownSkillSource - .well-known/skills 端点
    5. ClaudeMarketSource - Claude Code 市场
    6. GitHubSource - GitHub + 用户 taps
    7. UrlSource - 直接 URL

    计划中的来源（尚未实现）：
    - ClawHubSource - ClawHub 市场
    - LobeHubSource - LobeHub agents
    - BrowseShSource - browse.sh 网站自动化
    """
    router = SourceRouter()
    auth = get_github_auth()
    taps_manager = get_taps_manager()

    # 获取用户 taps
    taps = taps_manager.get_all_taps()
    extra_taps = [
        {"repo": tap.repo, "path": tap.path}
        for tap in taps
        if tap.enabled
    ]

    # 按优先级注册来源
    router.register(HermesIndexSource(auth=auth))   # 集中索引（优先，零 API 调用）
    router.register(OptionalSkillSource())         # 可选内置技能
    router.register(SkillsShSource(auth=auth))      # skills.sh 社区
    router.register(WellKnownSkillSource())        # .well-known/skills 端点
    router.register(ClaudeMarketSource(auth=auth)) # Claude Code Market
    router.register(GitHubSource(auth=auth, extra_taps=extra_taps))  # GitHub + 用户 taps
    router.register(UrlSource())                   # 直接 URL

    return router