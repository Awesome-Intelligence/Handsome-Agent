#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Taps 管理器 - 管理用户自定义的额外技能仓库

Taps 允许用户添加额外的 GitHub 仓库作为技能来源。

默认 Taps:
- openai/skills
- anthropics/skills
- huggingface/skills
- VoltAgent/awesome-agent-skills

📋 Logging Layer: TapsManager
"""

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 默认 Taps
DEFAULT_TAPS: List[Dict[str, str]] = [
    {"repo": "openai/skills", "path": "skills/"},
    {"repo": "anthropics/skills", "path": "skills/"},
    {"repo": "huggingface/skills", "path": "skills/"},
    {"repo": "VoltAgent/awesome-agent-skills", "path": "skills/"},
]

# Taps 配置文件
TAPS_FILENAME = "taps.json"


class Tap:
    """单个 Tap 配置"""

    def __init__(
        self,
        repo: str,
        path: str = "skills/",
        enabled: bool = True,
        trust_level: str = "community",
    ):
        self.repo = repo
        self.path = path.rstrip("/") + "/" if path else "skills/"
        self.enabled = enabled
        self.trust_level = trust_level

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repo": self.repo,
            "path": self.path,
            "enabled": self.enabled,
            "trust_level": self.trust_level,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Tap':
        return cls(
            repo=data.get("repo", ""),
            path=data.get("path", "skills/"),
            enabled=data.get("enabled", True),
            trust_level=data.get("trust_level", "community"),
        )

    def __repr__(self) -> str:
        status = "enabled" if self.enabled else "disabled"
        return f"Tap({self.repo}, trust={self.trust_level}, {status})"


class TapsManager:
    """
    Taps 管理器。

    负责：
    - 加载/保存用户配置的 taps
    - 合并默认 taps 和用户 taps
    - 添加/移除/启用/禁用 taps
    """

    def __init__(self, config_dir: Optional[Path] = None):
        if config_dir is None:
            from common.config import get_config_dir
            config_dir = get_config_dir()
        self._config_dir = Path(config_dir)
        self._taps_file = self._config_dir / TAPS_FILENAME
        self._user_taps: List[Tap] = []
        self._loaded = False

    def _ensure_dir(self) -> None:
        """确保配置目录存在"""
        self._config_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> List[Tap]:
        """加载用户 taps 配置"""
        if self._loaded:
            return self._user_taps

        self._user_taps = []
        self._loaded = True

        if not self._taps_file.exists():
            return self._user_taps

        try:
            with open(self._taps_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            taps_data = data.get("taps", [])
            for tap_data in taps_data:
                if isinstance(tap_data, dict):
                    self._user_taps.append(Tap.from_dict(tap_data))

        except (json.JSONDecodeError, OSError) as e:
            logger.debug(f"Failed to load taps config: {e}")

        return self._user_taps

    def save(self) -> bool:
        """保存用户 taps 配置"""
        self._ensure_dir()

        try:
            data = {
                "version": 1,
                "taps": [tap.to_dict() for tap in self._user_taps],
            }
            with open(self._taps_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True

        except OSError as e:
            logger.error(f"Failed to save taps config: {e}")
            return False

    def get_all_taps(self, include_disabled: bool = False) -> List[Tap]:
        """
        获取所有 taps（默认 + 用户配置）

        Args:
            include_disabled: 是否包含禁用的 taps

        Returns:
            Tap 列表
        """
        self.load()

        result = []

        # 添加默认 taps（如果用户没有覆盖）
        default_repos = {tap.repo for tap in self._user_taps}
        for tap_data in DEFAULT_TAPS:
            if tap_data["repo"] not in default_repos:
                result.append(Tap(
                    repo=tap_data["repo"],
                    path=tap_data["path"],
                    enabled=True,
                    trust_level="trusted",  # 默认 taps 更可信
                ))

        # 添加用户 taps
        for tap in self._user_taps:
            if include_disabled or tap.enabled:
                result.append(tap)

        return result

    def list_taps(self) -> List[Dict[str, Any]]:
        """列出所有 taps（用于 CLI 显示）"""
        return [tap.to_dict() for tap in self.get_all_taps(include_disabled=True)]

    def add_tap(
        self,
        repo: str,
        path: str = "skills/",
        trust_level: str = "community",
    ) -> bool:
        """
        添加新的 tap。

        Args:
            repo: GitHub 仓库 (owner/repo)
            path: 技能目录路径
            trust_level: 信任级别

        Returns:
            是否成功
        """
        self.load()

        # 检查是否已存在
        for tap in self._user_taps:
            if tap.repo.lower() == repo.lower():
                logger.warning(f"Tap already exists: {repo}")
                return False

        tap = Tap(repo=repo, path=path, enabled=True, trust_level=trust_level)
        self._user_taps.append(tap)
        return self.save()

    def remove_tap(self, repo: str) -> bool:
        """
        移除 tap。

        Args:
            repo: GitHub 仓库 (owner/repo)

        Returns:
            是否成功
        """
        self.load()

        original_len = len(self._user_taps)
        self._user_taps = [
            tap for tap in self._user_taps
            if tap.repo.lower() != repo.lower()
        ]

        if len(self._user_taps) == original_len:
            logger.warning(f"Tap not found: {repo}")
            return False

        return self.save()

    def enable_tap(self, repo: str) -> bool:
        """启用 tap"""
        self.load()

        for tap in self._user_taps:
            if tap.repo.lower() == repo.lower():
                tap.enabled = True
                return self.save()

        logger.warning(f"Tap not found: {repo}")
        return False

    def disable_tap(self, repo: str) -> bool:
        """禁用 tap"""
        self.load()

        for tap in self._user_taps:
            if tap.repo.lower() == repo.lower():
                tap.enabled = False
                return self.save()

        logger.warning(f"Tap not found: {repo}")
        return False

    def update_tap(
        self,
        repo: str,
        path: Optional[str] = None,
        trust_level: Optional[str] = None,
    ) -> bool:
        """
        更新 tap 配置。

        Args:
            repo: GitHub 仓库
            path: 新路径
            trust_level: 新信任级别

        Returns:
            是否成功
        """
        self.load()

        for tap in self._user_taps:
            if tap.repo.lower() == repo.lower():
                if path is not None:
                    tap.path = path.rstrip("/") + "/" if path else "skills/"
                if trust_level is not None:
                    tap.trust_level = trust_level
                return self.save()

        logger.warning(f"Tap not found: {repo}")
        return False

    def reset_to_defaults(self) -> bool:
        """
        重置为默认 taps。

        Returns:
            是否成功
        """
        self._user_taps = []
        return self.save()

    def get_tap_for_repo(self, repo: str) -> Optional[Tap]:
        """获取指定仓库的 tap 配置"""
        self.load()

        repo_lower = repo.lower()
        for tap in self._user_taps:
            if tap.repo.lower() == repo_lower:
                return tap

        # 返回默认配置
        for tap_data in DEFAULT_TAPS:
            if tap_data["repo"].lower() == repo_lower:
                return Tap(
                    repo=tap_data["repo"],
                    path=tap_data["path"],
                    enabled=True,
                    trust_level="trusted",
                )

        return None


# 全局实例
_taps_manager: Optional[TapsManager] = None


def get_taps_manager() -> TapsManager:
    """获取全局 Taps 管理器实例"""
    global _taps_manager
    if _taps_manager is None:
        _taps_manager = TapsManager()
    return _taps_manager


def list_taps() -> List[Dict[str, Any]]:
    """列出所有 taps（便捷函数）"""
    return get_taps_manager().list_taps()


def add_tap(repo: str, path: str = "skills/") -> bool:
    """添加 tap（便捷函数）"""
    return get_taps_manager().add_tap(repo, path)


def remove_tap(repo: str) -> bool:
    """移除 tap（便捷函数）"""
    return get_taps_manager().remove_tap(repo)
