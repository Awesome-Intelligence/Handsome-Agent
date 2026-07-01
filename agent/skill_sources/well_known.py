#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Well-Known 技能来源 - WellKnownSkillSource

从暴露 /.well-known/skills/index.json 的域名获取技能列表。
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse, urlunparse

import httpx

from .base import SkillSource, SourceResult, SourceSkillInfo

logger = logging.getLogger(__name__)

# Well-Known 路径
WELL_KNOWN_PATH = "/.well-known/skills"

# 缓存配置
WELL_KNOWN_CACHE_TTL = 3600  # 1 小时


class WellKnownSkillSource(SkillSource):
    """
    Well-Known 技能来源。

    从暴露 /.well-known/skills/index.json 的域名获取技能列表。
    支持通过 URL 查询技能索引。
    """

    SOURCE_TYPE = "well-known"

    def __init__(self, cache_dir: Optional[Path] = None):
        super().__init__("Well-Known Skills")
        if cache_dir is None:
            from common.config import get_config_dir
            cache_dir = get_config_dir() / ".hub" / "index-cache"
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def source_type(self) -> str:
        return self.SOURCE_TYPE

    def parse_ref(self, ref: str) -> Optional[Dict[str, Any]]:
        """解析 well-known 技能引用

        格式: "well-known:<base_url>/<skill_name>" 或 "well-known:<index_url>#<skill_name>"
        """
        if not ref.startswith("well-known:"):
            return None

        raw = ref[len("well-known:"):]
        if not raw.startswith(("http://", "https://")):
            return None

        parsed_url = urlparse(raw)
        clean_url = urlunparse(parsed_url._replace(fragment=""))
        fragment = parsed_url.fragment

        # 解析索引 URL 和技能名
        if clean_url.endswith("/index.json"):
            if not fragment:
                return None
            base_url = clean_url[:-len("/index.json")]
            skill_name = fragment
            skill_url = f"{base_url}/{skill_name}"
            return {
                "type": "well-known",
                "index_url": clean_url,
                "base_url": base_url,
                "skill_name": skill_name,
                "skill_url": skill_url,
            }

        # 解析 skill URL
        if clean_url.endswith("/SKILL.md"):
            skill_url = clean_url[:-len("/SKILL.md")]
        else:
            skill_url = clean_url.rstrip("/")

        if WELL_KNOWN_PATH not in skill_url:
            return None

        base_url, skill_name = skill_url.rsplit("/", 1)
        return {
            "type": "well-known",
            "index_url": f"{base_url}/index.json",
            "base_url": base_url,
            "skill_name": skill_name,
            "skill_url": skill_url,
        }

    async def search(self, query: str) -> List[SourceSkillInfo]:
        """搜索 well-known 技能"""
        index_url = self._query_to_index_url(query)
        if not index_url:
            return []

        parsed = self._parse_index(index_url)
        if not parsed:
            return []

        results: List[SourceSkillInfo] = []
        for entry in parsed["skills"][:10]:
            name = entry.get("name")
            if not isinstance(name, str) or not name:
                continue
            description = entry.get("description", "")
            files = entry.get("files", ["SKILL.md"])

            results.append(SourceSkillInfo(
                name=name,
                description=str(description),
                source=self.SOURCE_TYPE,
                url=self._wrap_identifier(parsed["base_url"], name),
                tags=[],  # well-known 不保证有 tags
            ))

        return results

    async def install(self, skill_ref: str, target_dir: Path) -> SourceResult:
        """安装 well-known 技能"""
        parsed = self.parse_ref(skill_ref)
        if not parsed:
            return SourceResult(
                success=False,
                skill_name="",
                error="Invalid well-known skill reference",
                source_name=self.SOURCE_TYPE,
            )

        skill_name = parsed["skill_name"]

        # 获取索引中的文件列表
        entry = self._index_entry(parsed["index_url"], skill_name)
        if not entry:
            return SourceResult(
                success=False,
                skill_name=skill_name,
                error=f"Skill not found in index: {skill_ref}",
                source_name=self.SOURCE_TYPE,
            )

        files = entry.get("files", ["SKILL.md"])
        if not isinstance(files, list) or not files:
            files = ["SKILL.md"]

        downloaded: Dict[str, str] = {}
        for rel_path in files:
            if not isinstance(rel_path, str) or not rel_path:
                continue

            # 安全验证
            safe_rel_path = self._validate_rel_path(rel_path)
            if not safe_rel_path:
                return SourceResult(
                    success=False,
                    skill_name=skill_name,
                    error=f"Unsafe file path: {rel_path}",
                    source_name=self.SOURCE_TYPE,
                )

            text = self._fetch_text(f"{parsed['skill_url']}/{safe_rel_path}")
            if text is None:
                return SourceResult(
                    success=False,
                    skill_name=skill_name,
                    error=f"Failed to fetch file: {rel_path}",
                    source_name=self.SOURCE_TYPE,
                )
            downloaded[safe_rel_path] = text

        if "SKILL.md" not in downloaded:
            return SourceResult(
                success=False,
                skill_name=skill_name,
                error="SKILL.md not found",
                source_name=self.SOURCE_TYPE,
            )

        # 写入文件
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            for rel_path, content in downloaded.items():
                target_path = target_dir / rel_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(content, encoding="utf-8")

            return SourceResult(
                success=True,
                skill_name=skill_name,
                skill_data=b"",  # 已直接写入文件
                metadata={
                    "source": self.SOURCE_TYPE,
                    "installed_path": str(target_dir),
                    "index_url": parsed["index_url"],
                },
                source_name=self.SOURCE_TYPE,
            )
        except Exception as e:
            logger.exception("Failed to install well-known skill %s", skill_ref)
            return SourceResult(
                success=False,
                skill_name=skill_name,
                error=str(e),
                source_name=self.SOURCE_TYPE,
            )

    def _query_to_index_url(self, query: str) -> Optional[str]:
        """将查询转换为索引 URL"""
        query = query.strip()
        if not query.startswith(("http://", "https://")):
            return None

        if query.endswith("/index.json"):
            return query

        if WELL_KNOWN_PATH in query:
            base_url = query.split(f"{WELL_KNOWN_PATH}/", 1)[0] + WELL_KNOWN_PATH
            return f"{base_url}/index.json"

        return query.rstrip("/") + f"{WELL_KNOWN_PATH}/index.json"

    def _parse_index(self, index_url: str) -> Optional[Dict[str, Any]]:
        """解析技能索引"""
        cache_key = f"well_known_index_{hashlib.md5(index_url.encode()).hexdigest()}"
        cached = self._read_cache(cache_key)
        if isinstance(cached, dict) and isinstance(cached.get("skills"), list):
            return cached

        try:
            resp = httpx.get(index_url, timeout=20, follow_redirects=True)
        except httpx.HTTPError as e:
            logger.debug("Failed to fetch well-known index: %s", e)
            return None

        if resp.status_code != 200:
            return None

        try:
            data = resp.json()
        except json.JSONDecodeError:
            return None

        skills = data.get("skills", []) if isinstance(data, dict) else []
        if not isinstance(skills, list):
            return None

        parsed = {
            "index_url": index_url,
            "base_url": index_url[:-len("/index.json")],
            "skills": skills,
        }
        self._write_cache(cache_key, parsed)
        return parsed

    def _index_entry(self, index_url: str, skill_name: str) -> Optional[Dict[str, Any]]:
        """从索引中获取技能条目"""
        parsed = self._parse_index(index_url)
        if not parsed:
            return None
        for entry in parsed["skills"]:
            if isinstance(entry, dict) and entry.get("name") == skill_name:
                return entry
        return None

    def _fetch_text(self, url: str) -> Optional[str]:
        """获取文本内容"""
        try:
            resp = httpx.get(url, timeout=20, follow_redirects=True)
            if resp.status_code == 200:
                return resp.text
        except httpx.HTTPError:
            pass
        return None

    @staticmethod
    def _wrap_identifier(base_url: str, skill_name: str) -> str:
        """包装技能标识符"""
        return f"well-known:{base_url.rstrip('/')}/{skill_name}"

    @staticmethod
    def _validate_rel_path(rel_path: str) -> Optional[str]:
        """验证相对路径安全性"""
        import re

        rel_path = rel_path.strip()
        if not rel_path:
            return None

        # 禁止绝对路径和路径遍历
        if rel_path.startswith("/") or ".." in rel_path:
            return None

        # 标准化路径
        normalized = rel_path.replace("\\", "/")
        parts = [p for p in normalized.split("/") if p and p != "."]

        # 检查是否有危险字符
        for part in parts:
            if not re.match(r'^[a-zA-Z0-9_\-. ]+$', part):
                return None

        return "/".join(parts)

    def _read_cache(self, key: str) -> Optional[Any]:
        """读取缓存"""
        cache_file = self._cache_dir / f"{key}.json"
        if not cache_file.exists():
            return None

        try:
            import time
            stat = cache_file.stat()
            if time.time() - stat.st_mtime > WELL_KNOWN_CACHE_TTL:
                return None
            return json.loads(cache_file.read_text())
        except (OSError, json.JSONDecodeError):
            return None

    def _write_cache(self, key: str, data: Any) -> None:
        """写入缓存"""
        cache_file = self._cache_dir / f"{key}.json"
        try:
            cache_file.write_text(json.dumps(data), encoding="utf-8")
        except OSError:
            pass