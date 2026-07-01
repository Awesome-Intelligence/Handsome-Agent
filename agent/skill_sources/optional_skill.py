#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可选技能来源 - OptionalSkillSource

从项目内置的 skills/system/ 目录中扫描可选技能。
这些技能是官方维护的，但不是默认激活的。
"""

import logging
import re
from pathlib import Path
from typing import List, Optional, Dict, Any

import yaml

from .base import SkillSource, SourceResult, SourceSkillInfo

logger = logging.getLogger(__name__)


class OptionalSkillSource(SkillSource):
    """
    可选技能来源。

    从项目内置的 skills/system/ 目录中扫描可选技能。
    这些技能是官方维护的（builtin trust level），但不是默认激活的。
    """

    SOURCE_TYPE = "optional"

    def __init__(self, skills_dir: Optional[Path] = None):
        super().__init__("Optional Skills")
        if skills_dir is None:
            # 默认使用项目的 skills/system 目录
            project_root = Path(__file__).parent.parent.parent.parent
            skills_dir = project_root / "skills" / "system"
        self._skills_dir = Path(skills_dir)

    @property
    def source_type(self) -> str:
        return self.SOURCE_TYPE

    def parse_ref(self, ref: str) -> Optional[Dict[str, Any]]:
        """解析可选技能引用

        格式: "optional/<skill_name>" 或 "optional/<category>/<skill_name>"
        """
        if not ref.startswith("optional/"):
            return None

        rel_path = ref[len("optional/"):]
        parts = rel_path.split("/")

        # 验证技能名安全
        skill_name = parts[-1]
        if not self._is_valid_skill_name(skill_name):
            return None

        return {
            "type": "optional",
            "rel_path": rel_path,
            "skill_name": skill_name,
        }

    async def search(self, query: str) -> List[SourceSkillInfo]:
        """搜索可选技能"""
        results: List[SourceSkillInfo] = []
        query_lower = query.lower()

        for meta in self._scan_all():
            searchable = f"{meta.name} {meta.description} {' '.join(meta.tags)}".lower()
            if query_lower in searchable:
                results.append(meta)
            if len(results) >= 10:
                break

        return results

    async def install(self, skill_ref: str, target_dir: Path) -> SourceResult:
        """安装可选技能到目标目录"""
        parsed = self.parse_ref(skill_ref)
        if not parsed:
            return SourceResult(
                success=False,
                skill_name="",
                error="Invalid optional skill reference",
                source_name=self.SOURCE_TYPE,
            )

        skill_dir = self._skills_dir / parsed["rel_path"]
        if not skill_dir.is_dir():
            return SourceResult(
                success=False,
                skill_name=parsed["skill_name"],
                error=f"Skill not found: {skill_ref}",
                source_name=self.SOURCE_TYPE,
            )

        try:
            target_dir.mkdir(parents=True, exist_ok=True)

            # 复制所有文件
            import shutil
            for item in skill_dir.rglob("*"):
                if item.is_file() and not item.name.startswith("."):
                    rel_path = item.relative_to(skill_dir)
                    target_path = target_dir / rel_path
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, target_path)

            return SourceResult(
                success=True,
                skill_name=parsed["skill_name"],
                skill_data=b"",  # 已直接写入文件
                metadata={
                    "source": self.SOURCE_TYPE,
                    "installed_path": str(target_dir),
                },
                source_name=self.SOURCE_TYPE,
            )
        except Exception as e:
            logger.exception("Failed to install optional skill %s", skill_ref)
            return SourceResult(
                success=False,
                skill_name=parsed["skill_name"],
                error=str(e),
                source_name=self.SOURCE_TYPE,
            )

    def _scan_all(self) -> List[SourceSkillInfo]:
        """扫描所有可选技能"""
        if not self._skills_dir.is_dir():
            return []

        results: List[SourceSkillInfo] = []
        for skill_md in self._skills_dir.rglob("SKILL.md"):
            parent = skill_md.parent

            try:
                content = skill_md.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            fm = self._parse_frontmatter(content)
            if not fm:
                continue

            name = fm.get("name", parent.name)
            desc = fm.get("description", "")

            # 解析 metadata.hermes.tags
            tags = []
            meta_block = fm.get("metadata", {})
            if isinstance(meta_block, dict):
                hermes_meta = meta_block.get("hermes", {})
                if isinstance(hermes_meta, dict):
                    tags = hermes_meta.get("tags", [])

            rel_path = str(parent.relative_to(self._skills_dir))

            results.append(SourceSkillInfo(
                name=name,
                description=desc[:200] if desc else "",
                author=fm.get("author", "Handsome Agent"),
                version=fm.get("version", ""),
                source=self.SOURCE_TYPE,
                url=f"optional/{rel_path}",
                tags=tags if isinstance(tags, list) else [],
            ))

        return results

    @staticmethod
    def _parse_frontmatter(content: str) -> Dict[str, Any]:
        """解析 YAML frontmatter"""
        if not content.startswith("---"):
            return {}
        match = re.search(r'\n---\s*\n', content[3:])
        if not match:
            return {}
        yaml_text = content[3:match.start() + 3]
        try:
            parsed = yaml.safe_load(yaml_text)
            return parsed if isinstance(parsed, dict) else {}
        except yaml.YAMLError:
            return {}

    @staticmethod
    def _is_valid_skill_name(name: str) -> bool:
        """验证技能名安全性"""
        if not name:
            return False
        # 只允许字母、数字、下划线和连字符
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', name))