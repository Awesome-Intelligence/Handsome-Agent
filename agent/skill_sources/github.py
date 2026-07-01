"""GitHub 技能来源（使用 GitHubAuth）"""

import re
import zipfile
import io
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

from .base import SkillSource, SourceResult, SourceSkillInfo
from .github_auth import GitHubAuth, get_github_auth

logger = logging.getLogger(__name__)


class GitHubSource(SkillSource):
    """GitHub 技能来源"""

    SOURCE_TYPE = "github"
    API_BASE = "https://api.github.com"

    # 默认的技能搜索 taps
    DEFAULT_TAPS = [
        {"repo": "openai/skills", "path": "skills/"},
        {"repo": "anthropics/skills", "path": "skills/"},
        {"repo": "huggingface/skills", "path": "skills/"},
        {"repo": "VoltAgent/awesome-agent-skills", "path": "skills/"},
    ]

    # 匹配格式: github:owner/repo 或 github:owner/repo/skill-path
    PATTERN = re.compile(r'^github:([^/]+)/([^/]+)(?:/(.+))?$')

    def __init__(self, auth: Optional[GitHubAuth] = None, extra_taps: Optional[List[Dict]] = None):
        super().__init__("GitHub")
        self.auth = auth or get_github_auth()
        self.taps = list(self.DEFAULT_TAPS)
        if extra_taps:
            self.taps.extend(extra_taps)
        # 树缓存：避免重复 API 调用
        self._tree_cache: Dict[str, tuple] = {}

    @property
    def source_type(self) -> str:
        return self.SOURCE_TYPE

    @property
    def is_rate_limited(self) -> bool:
        """是否触发了速率限制"""
        return getattr(self, '_rate_limited', False)

    def parse_ref(self, ref: str) -> Optional[Dict[str, Any]]:
        match = self.PATTERN.match(ref.lower())
        if not match:
            return None

        return {
            'owner': match.group(1),
            'repo': match.group(2),
            'path': match.group(3) or '',
        }

    async def search(self, query: str) -> List[SourceSkillInfo]:
        """从 GitHub taps 搜索技能"""
        results = []

        try:
            import aiohttp

            headers = self.auth.get_headers()
            query_lower = query.lower()

            for tap in self.taps:
                try:
                    # 获取仓库内容
                    url = f"{self.API_BASE}/repos/{tap['repo']}/contents/{tap.get('path', '').rstrip('/')}"
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, headers=headers) as resp:
                            if resp.status != 200:
                                continue

                            items = await resp.json()
                            if not isinstance(items, list):
                                continue

                            for item in items:
                                if item.get('type') != 'dir':
                                    continue
                                dir_name = item.get('name', '')
                                if query_lower in dir_name.lower():
                                    # 获取技能元数据
                                    meta = await self._inspect_skill(tap['repo'], f"{tap.get('path', '')}{dir_name}")
                                    if meta:
                                        results.append(meta)
                except Exception as e:
                    logger.debug(f"Failed to search tap {tap['repo']}: {e}")
                    continue

        except ImportError:
            logger.warning("aiohttp not available, GitHub search skipped")
        except Exception as e:
            logger.warning(f"GitHub search failed: {e}")

        return results

    async def _inspect_skill(self, repo: str, path: str) -> Optional[SourceSkillInfo]:
        """检查技能元数据"""
        try:
            import aiohttp

            skill_md_path = f"{path.rstrip('/')}/SKILL.md"
            url = f"{self.API_BASE}/repos/{repo}/contents/{skill_md_path}"
            headers = {**self.auth.get_headers(), "Accept": "application/vnd.github.v3.raw"}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status != 200:
                        return None

                    content = await resp.text()
                    return self._parse_skill_metadata(content, repo, path)

        except Exception:
            pass

        return None

    def _parse_skill_metadata(self, content: str, repo: str, path: str) -> Optional[SourceSkillInfo]:
        """解析 SKILL.md 的 frontmatter"""
        import yaml

        if not content.startswith("---"):
            return None

        match = re.search(r'\n---\s*\n', content[3:])
        if not match:
            return None

        yaml_text = content[3:match.start() + 3]
        try:
            fm = yaml.safe_load(yaml_text)
            if not isinstance(fm, dict):
                return None

            skill_name = fm.get('name', path.split('/')[-1])
            return SourceSkillInfo(
                name=skill_name,
                description=fm.get('description', ''),
                author=fm.get('author', ''),
                version=fm.get('version', '1.0.0'),
                source=self.name,
                url=f"https://github.com/{repo}/{path}",
                tags=fm.get('tags', []),
            )
        except Exception:
            pass

        return None

    async def install(self, skill_ref: str, target_dir: Path) -> SourceResult:
        """从 GitHub 安装技能"""
        parsed = self.parse_ref(skill_ref)
        if not parsed:
            return SourceResult(
                success=False,
                skill_name="",
                error=f"Invalid GitHub reference: {skill_ref}",
                source_name=self.name,
            )

        try:
            import aiohttp

            owner = parsed['owner']
            repo = parsed['repo']
            skill_path = parsed['path']

            headers = self.auth.get_headers()

            # 如果没有指定路径，列出仓库中的 skills 目录
            if not skill_path:
                url = f"{self.API_BASE}/repos/{owner}/{repo}/contents/skills"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers) as resp:
                        if resp.status == 200:
                            items = await resp.json()
                            if isinstance(items, list) and items:
                                skill_path = "skills/" + items[0]['name']
                        else:
                            skill_path = ""

            if not skill_path:
                return SourceResult(
                    success=False,
                    skill_name=repo,
                    error="No skill path found",
                    source_name=self.name,
                )

            # 下载技能目录
            files = await self._download_directory(owner, repo, skill_path)
            if not files:
                return SourceResult(
                    success=False,
                    skill_name=skill_path.split('/')[-1],
                    error="Failed to download skill files",
                    source_name=self.name,
                )

            # 提取技能
            skill_name = skill_path.split('/')[-1]
            skill_dir = target_dir / skill_name
            skill_dir.mkdir(parents=True, exist_ok=True)

            for file_path, content in files.items():
                target_path = skill_dir / file_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(content, encoding='utf-8')

            return SourceResult(
                success=True,
                skill_name=skill_name,
                skill_data=None,
                metadata={'path': str(skill_dir), 'files': list(files.keys())},
                source_name=self.name,
            )

        except ImportError:
            return SourceResult(
                success=False,
                skill_name=parsed.get('repo', ''),
                error="aiohttp not available",
                source_name=self.name,
            )
        except Exception as e:
            logger.error(f"GitHub install failed: {e}")
            return SourceResult(
                success=False,
                skill_name=parsed.get('repo', ''),
                error=str(e),
                source_name=self.name,
            )

    async def _download_directory(self, owner: str, repo: str, path: str) -> Dict[str, str]:
        """递归下载 GitHub 目录"""
        try:
            import aiohttp

            files: Dict[str, str] = {}
            url = f"{self.API_BASE}/repos/{owner}/{repo}/contents/{path.rstrip('/')}"
            headers = self.auth.get_headers()

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status != 200:
                        return {}

                    items = await resp.json()
                    if not isinstance(items, list):
                        return {}

                    for item in items:
                        name = item.get('name', '')
                        item_type = item.get('type', '')

                        if item_type == 'file':
                            content = await self._fetch_file_content(owner, repo, f"{path}/{name}")
                            if content:
                                rel_path = name
                                files[rel_path] = content
                        elif item_type == 'dir':
                            sub_files = await self._download_directory(owner, repo, f"{path}/{name}")
                            for sub_name, sub_content in sub_files.items():
                                files[f"{name}/{sub_name}"] = sub_content

            return files

        except Exception as e:
            logger.debug(f"Failed to download directory {path}: {e}")
            return {}

    async def _fetch_file_content(self, owner: str, repo: str, path: str) -> Optional[str]:
        """获取单个文件内容"""
        try:
            import aiohttp

            url = f"{self.API_BASE}/repos/{owner}/{repo}/contents/{path}"
            headers = {**self.auth.get_headers(), "Accept": "application/vnd.github.v3.raw"}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        return await resp.text()

        except Exception:
            pass

        return None


def _get_github_token() -> Optional[str]:
    """获取 GitHub Token（兼容旧接口）"""
    auth = get_github_auth()
    return auth._resolve_token()