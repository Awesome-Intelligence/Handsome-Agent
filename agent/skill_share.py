#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill Share - 技能分享和发布

提供技能分享功能：
- 生成分享包
- 发布到 GitHub Gist
- 分享链接生成

🚪 Access - 📋 Skills - 分享发布
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import re
import urllib.request
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from common.config import get_skills_dir
from common.logging_manager import get_execution_logger

logger = get_execution_logger("SkillShare")

# Gist API URL
GIST_API_URL = "https://api.github.com/gists"

# 分享平台
PLATFORMS = ["github", "gist", "npm", "local"]


@dataclass
class ShareMetadata:
    """分享元数据"""
    skill_name: str
    version: str
    description: str
    author: str
    tags: List[str] = field(default_factory=list)
    license: str = "MIT"
    homepage: str = ""
    repository: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.skill_name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "tags": self.tags,
            "license": self.license,
            "homepage": self.homepage,
            "repository": self.repository,
        }


@dataclass
class ShareResult:
    """分享结果"""
    success: bool
    url: str = ""
    id: str = ""
    message: str = ""
    platform: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "url": self.url,
            "id": self.id,
            "message": self.message,
            "platform": self.platform,
        }


class SkillShare:
    """
    技能分享工具

    支持：
    - 生成本地分享包
    - 发布到 GitHub Gist
    - 生成分享链接
    """

    def __init__(self):
        self._skills_dir = get_skills_dir()

    def generate_share_package(
        self,
        skill_name: str,
        include_supporting: bool = True,
    ) -> Dict[str, Any]:
        """
        生成本地分享包

        Args:
            skill_name: 技能名称
            include_supporting: 是否包含支持文件

        Returns:
            分享包信息
        """
        result = {
            "success": False,
            "skill_name": skill_name,
            "files": [],
            "metadata": None,
            "message": "",
        }

        skill_dir = self._skills_dir / skill_name
        if not skill_dir.exists():
            result["message"] = f"Skill not found: {skill_name}"
            return result

        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            result["message"] = "SKILL.md not found"
            return result

        try:
            # 读取技能内容
            content = skill_file.read_text(encoding="utf-8")

            # 解析元数据
            from agent.skill_utils import parse_frontmatter
            frontmatter, body = parse_frontmatter(content)

            # 创建元数据
            metadata = ShareMetadata(
                skill_name=skill_name,
                version=frontmatter.get("version", "1.0.0"),
                description=frontmatter.get("description", ""),
                author=frontmatter.get("author", ""),
                tags=frontmatter.get("tags", []),
                license=frontmatter.get("license", "MIT"),
            )

            result["metadata"] = metadata.to_dict()

            # 添加主文件
            result["files"].append({
                "name": "SKILL.md",
                "type": "main",
                "size": len(content),
            })

            # 添加支持文件
            if include_supporting:
                for subdir in ["references", "templates", "scripts", "assets"]:
                    subdir_path = skill_dir / subdir
                    if subdir_path.exists():
                        for file_path in subdir_path.rglob("*"):
                            if file_path.is_file():
                                rel_path = str(file_path.relative_to(skill_dir))
                                result["files"].append({
                                    "name": rel_path,
                                    "type": subdir,
                                    "size": file_path.stat().st_size,
                                })

            # 计算哈希
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            result["content_hash"] = content_hash
            result["success"] = True

            logger.info(f"Generated share package for {skill_name}")

        except Exception as e:
            result["message"] = f"Failed to generate package: {e}"

        return result

    def create_markdown_share(
        self,
        skill_name: str,
        include_code: bool = True,
    ) -> str:
        """
        创建 Markdown 格式的分享内容

        Args:
            skill_name: 技能名称
            include_code: 是否包含代码

        Returns:
            Markdown 格式的分享内容
        """
        skill_dir = self._skills_dir / skill_name
        if not skill_dir.exists():
            return f"# Skill not found: {skill_name}"

        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            return f"# SKILL.md not found for {skill_name}"

        try:
            content = skill_file.read_text(encoding="utf-8")
            frontmatter, body = parse_frontmatter(content)

            # 创建分享内容
            lines = [
                f"# {skill_name}",
                "",
                f"> {frontmatter.get('description', 'No description')}",
                "",
                f"**Version:** {frontmatter.get('version', '1.0.0')} | "
                f"**Author:** {frontmatter.get('author', 'Unknown')} | "
                f"**License:** {frontmatter.get('license', 'MIT')}",
                "",
                "## Install",
                "",
                "```bash",
                f"# Clone or download this skill",
                f"agentz skills install {skill_name}",
                "```",
                "",
                "## Usage",
                "",
            ]

            if include_code and body:
                lines.append("```markdown")
                lines.append(body[:2000])  # 限制长度
                if len(body) > 2000:
                    lines.append("...")
                lines.append("```")

            # 添加元数据
            lines.extend([
                "",
                "## Metadata",
                "",
                "```yaml",
                f"name: {skill_name}",
                f"description: {frontmatter.get('description', '')}",
                f"version: {frontmatter.get('version', '1.0.0')}",
                f"author: {frontmatter.get('author', '')}",
                f"category: {frontmatter.get('category', '')}",
            ])

            if frontmatter.get("triggers"):
                lines.append(f"triggers: {', '.join(frontmatter['triggers'])}")
            if frontmatter.get("tags"):
                lines.append(f"tags: {', '.join(frontmatter['tags'])}")

            lines.extend([
                "```",
                "",
                "---",
                f"*Shared from Agent-Z*",
            ])

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Failed to create markdown share: {e}")
            return f"# Error: {e}"

    def share_to_gist(
        self,
        skill_name: str,
        description: str = None,
        public: bool = False,
        github_token: str = None,
    ) -> ShareResult:
        """
        发布到 GitHub Gist

        Args:
            skill_name: 技能名称
            description: 描述
            public: 是否公开
            github_token: GitHub Token（可从环境变量获取）

        Returns:
            分享结果
        """
        result = ShareResult(
            success=False,
            platform="gist",
            message="",
        )

        # 检查 Token
        if not github_token:
            github_token = self._get_github_token()

        if not github_token:
            result.message = "GitHub token not found. Set GITHUB_TOKEN environment variable."
            return result

        skill_dir = self._skills_dir / skill_name
        if not skill_dir.exists():
            result.message = f"Skill not found: {skill_name}"
            return result

        try:
            # 收集文件
            files = {}

            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists():
                content = skill_file.read_text(encoding="utf-8")
                frontmatter, body = parse_frontmatter(content)

                files["SKILL.md"] = {
                    "content": content,
                }

                if description is None:
                    description = frontmatter.get("description", f"Skill: {skill_name}")

                # 添加支持文件
                for subdir in ["references", "templates", "scripts"]:
                    subdir_path = skill_dir / subdir
                    if subdir_path.exists():
                        for file_path in subdir_path.rglob("*"):
                            if file_path.is_file():
                                rel_path = str(file_path.relative_to(skill_dir))
                                try:
                                    file_content = file_path.read_text(encoding="utf-8")
                                    files[rel_path] = {
                                        "content": file_content,
                                    }
                                except Exception:
                                    pass

            # 创建 Gist
            gist_data = {
                "description": description or f"Skill: {skill_name}",
                "public": public,
                "files": files,
            }

            # 发送请求
            data = json.dumps(gist_data).encode("utf-8")
            req = urllib.request.Request(
                GIST_API_URL,
                data=data,
                headers={
                    "Authorization": f"token {github_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/vnd.github.v3+json",
                },
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=30) as response:
                gist = json.loads(response.read().decode("utf-8"))

                result.success = True
                result.url = gist["html_url"]
                result.id = gist["id"]
                result.message = "Shared successfully!"

                logger.info(f"Shared to Gist: {result.url}")

        except urllib.error.HTTPError as e:
            result.message = f"GitHub API error: {e.code} {e.reason}"
            logger.error(f"Gist share failed: {result.message}")
        except Exception as e:
            result.message = f"Failed to share: {e}"
            logger.error(f"Gist share failed: {result.message}")

        return result

    def _get_github_token(self) -> Optional[str]:
        """获取 GitHub Token"""
        import os
        return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

    def generate_install_command(self, skill_name: str, source: str = "local") -> str:
        """
        生成安装命令

        Args:
            skill_name: 技能名称
            source: 来源类型

        Returns:
            安装命令
        """
        if source == "local":
            return f"agentz skills install --local {skill_name}"
        elif source == "github":
            return f"agentz skills install --github owner/repo/{skill_name}"
        elif source == "gist":
            return f"agentz skills install --gist <gist-id>"
        else:
            return f"agentz skills install {skill_name}"

    def create_badge(self, skill_name: str, style: str = "flat") -> str:
        """
        生成技能徽章（SVG）

        Args:
            skill_name: 技能名称
            style: 徽章样式

        Returns:
            SVG 徽章 URL
        """
        # 使用 shields.io 生成徽章
        label = "skill"
        message = skill_name[:20] if len(skill_name) > 20 else skill_name
        color = "blue"

        url = f"https://img.shields.io/badge/{label}-{urllib.parse.quote(message)}-{color}.svg?style={style}"

        return url

    def create_readme_snippet(self, skill_name: str) -> str:
        """
        创建 README 片段

        Args:
            skill_name: 技能名称

        Returns:
            README 片段
        """
        skill_dir = self._skills_dir / skill_name
        if not skill_dir.exists():
            return f"# Skill not found: {skill_name}"

        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            return f"# SKILL.md not found"

        try:
            content = skill_file.read_text(encoding="utf-8")
            frontmatter, body = parse_frontmatter(content)

            # 简短的 README 片段
            lines = [
                f"## {skill_name}",
                "",
                f"{frontmatter.get('description', '')}",
                "",
                "### Install",
                "",
                "```bash",
                f"agentz skills install {skill_name}",
                "```",
                "",
            ]

            if frontmatter.get("triggers"):
                lines.extend([
                    "### Triggers",
                    "",
                    f"`{'`, `'.join(frontmatter['triggers'])}`",
                    "",
                ])

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Failed to create README snippet: {e}")
            return f"# Error: {e}"


# 全局实例
_share: Optional[SkillShare] = None


def get_share() -> SkillShare:
    """获取全局分享工具实例"""
    global _share
    if _share is None:
        _share = SkillShare()
    return _share


# 便捷函数

def generate_share_package(skill_name: str) -> Dict[str, Any]:
    """生成分享包"""
    return get_share().generate_share_package(skill_name)


def create_markdown_share(skill_name: str) -> str:
    """创建 Markdown 分享"""
    return get_share().create_markdown_share(skill_name)


def share_to_gist(
    skill_name: str,
    description: str = None,
    public: bool = False,
) -> ShareResult:
    """分享到 Gist"""
    return get_share().share_to_gist(skill_name, description, public)


if __name__ == "__main__":
    share = get_share()

    print("Skill Share Manager")
    print()
    print("Functions:")
    print("  - generate_share_package(): Generate a share package")
    print("  - create_markdown_share(): Create markdown for sharing")
    print("  - share_to_gist(): Share to GitHub Gist")
    print("  - create_readme_snippet(): Create README snippet")
    print()
    print("Example:")
    print('  share.share_to_gist("my-skill", public=True)')
