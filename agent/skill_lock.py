#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill Lock File - 技能来源锁定系统

跟踪已安装技能的来源，支持：
- 避免重复安装
- 检测上游更新
- 卸载追踪
- 来源审计

🚪 Access - 📋 Skills - Lock 管理
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from common.config import get_settings

logger = logging.getLogger(__name__)

# Lock 文件版本
LOCK_VERSION = 1

# Lock 文件路径
LOCK_FILENAME = ".hub" / "lock.json"


@dataclass
class HubLockEntry:
    """Lock 文件条目"""
    skill_name: str
    source: str  # "github", "url", "hermes-index", etc.
    identifier: str  # 来源唯一标识符
    installed_at: str  # ISO 时间戳
    origin_hash: str  # 内容哈希，用于更新检测
    version: str = "1.0.0"
    author: str = ""
    description: str = ""
    trust_level: str = "community"  # "builtin", "trusted", "community"
    install_path: str = ""  # 相对路径
    extra: Dict[str, Any] = field(default_factory=dict)


class HubLockFile:
    """
    技能锁定文件管理器
    
    管理 .hub/lock.json 文件，记录所有从 Hub 安装的技能。
    """

    def __init__(self, skills_dir: Optional[Path] = None):
        if skills_dir is None:
            skills_dir = Path(get_settings().skills_dir)
        self._skills_dir = Path(skills_dir)
        self._lock_dir = self._skills_dir / ".hub"
        self._lock_file = self._lock_dir / "lock.json"
        self._cache: Optional[Dict[str, Any]] = None

    def _load(self) -> Dict[str, Any]:
        """加载 lock 文件"""
        if self._cache is not None:
            return self._cache

        if not self._lock_file.exists():
            self._cache = {"version": LOCK_VERSION, "installed": {}}
            return self._cache

        try:
            data = json.loads(self._lock_file.read_text(encoding="utf-8"))
            # 确保结构正确
            if not isinstance(data, dict):
                data = {"version": LOCK_VERSION, "installed": {}}
            data.setdefault("version", LOCK_VERSION)
            data.setdefault("installed", {})
            self._cache = data
            return data
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load lock file: {e}")
            self._cache = {"version": LOCK_VERSION, "installed": {}}
            return self._cache

    def _save(self, data: Dict[str, Any]) -> bool:
        """保存 lock 文件"""
        try:
            self._lock_dir.mkdir(parents=True, exist_ok=True)
            self._lock_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            self._cache = data
            return True
        except OSError as e:
            logger.error(f"Failed to save lock file: {e}")
            return False

    def _now_iso(self) -> str:
        """获取当前 UTC 时间戳"""
        return datetime.now(timezone.utc).isoformat()

    def _compute_hash(self, content: bytes) -> str:
        """计算内容哈希"""
        return hashlib.sha256(content).hexdigest()[:16]

    def _get_install_path(self, skill_name: str) -> str:
        """获取技能的相对安装路径"""
        return str(Path(skill_name))

    def add_entry(
        self,
        skill_name: str,
        source: str,
        identifier: str,
        content: bytes = b"",
        version: str = "1.0.0",
        author: str = "",
        description: str = "",
        trust_level: str = "community",
        extra: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        添加技能锁定条目
        
        Args:
            skill_name: 技能名称
            source: 来源类型
            identifier: 来源唯一标识符
            content: 技能内容（用于计算哈希）
            version: 版本
            author: 作者
            description: 描述
            trust_level: 信任级别
            extra: 额外信息
        
        Returns:
            是否成功
        """
        data = self._load()

        entry = {
            "skill_name": skill_name,
            "source": source,
            "identifier": identifier,
            "installed_at": self._now_iso(),
            "origin_hash": self._compute_hash(content) if content else "",
            "version": version,
            "author": author,
            "description": description,
            "trust_level": trust_level,
            "install_path": self._get_install_path(skill_name),
            "extra": extra or {},
        }

        data["installed"][skill_name] = entry
        return self._save(data)

    def remove_entry(self, skill_name: str) -> bool:
        """
        移除技能锁定条目
        
        Args:
            skill_name: 技能名称
        
        Returns:
            是否成功
        """
        data = self._load()

        if skill_name in data["installed"]:
            del data["installed"][skill_name]
            return self._save(data)

        return True  # 不存在也返回成功

    def get_entry(self, skill_name: str) -> Optional[HubLockEntry]:
        """
        获取技能锁定条目
        
        Args:
            skill_name: 技能名称
        
        Returns:
            锁定条目或 None
        """
        data = self._load()
        entry_data = data.get("installed", {}).get(skill_name)

        if not entry_data:
            return None

        return HubLockEntry(
            skill_name=entry_data["skill_name"],
            source=entry_data["source"],
            identifier=entry_data["identifier"],
            installed_at=entry_data["installed_at"],
            origin_hash=entry_data["origin_hash"],
            version=entry_data.get("version", "1.0.0"),
            author=entry_data.get("author", ""),
            description=entry_data.get("description", ""),
            trust_level=entry_data.get("trust_level", "community"),
            install_path=entry_data.get("install_path", ""),
            extra=entry_data.get("extra", {}),
        )

    def has_entry(self, skill_name: str) -> bool:
        """
        检查技能是否已锁定
        
        Args:
            skill_name: 技能名称
        
        Returns:
            是否已锁定
        """
        data = self._load()
        return skill_name in data.get("installed", {})

    def list_entries(self, source: Optional[str] = None) -> List[HubLockEntry]:
        """
        列出所有锁定条目
        
        Args:
            source: 可选的来源过滤
        
        Returns:
            锁定条目列表
        """
        data = self._load()
        entries = []

        for entry_data in data.get("installed", {}).values():
            if source and entry_data.get("source") != source:
                continue

            entries.append(HubLockEntry(
                skill_name=entry_data["skill_name"],
                source=entry_data["source"],
                identifier=entry_data["identifier"],
                installed_at=entry_data["installed_at"],
                origin_hash=entry_data["origin_hash"],
                version=entry_data.get("version", "1.0.0"),
                author=entry_data.get("author", ""),
                description=entry_data.get("description", ""),
                trust_level=entry_data.get("trust_level", "community"),
                install_path=entry_data.get("install_path", ""),
                extra=entry_data.get("extra", {}),
            ))

        return entries

    def update_hash(self, skill_name: str, content: bytes) -> bool:
        """
        更新技能的内容哈希
        
        用于在技能更新后更新哈希值。
        
        Args:
            skill_name: 技能名称
            content: 新的技能内容
        
        Returns:
            是否成功
        """
        data = self._load()

        if skill_name not in data["installed"]:
            return False

        data["installed"][skill_name]["origin_hash"] = self._compute_hash(content)
        return self._save(data)

    def check_update_available(self, skill_name: str, new_content: bytes) -> bool:
        """
        检查技能是否有可用更新
        
        Args:
            skill_name: 技能名称
            new_content: 新的技能内容
        
        Returns:
            是否有更新
        """
        entry = self.get_entry(skill_name)
        if not entry:
            return False

        new_hash = self._compute_hash(new_content)
        return new_hash != entry.origin_hash

    def get_outdated_skills(self) -> List[str]:
        """
        获取可能有更新的技能列表
        
        注意：这只是一个占位实现，实际的更新检测需要
        与各个来源适配器配合。
        
        Returns:
            可能有更新的技能名称列表
        """
        # 这个功能需要与来源适配器配合实现
        # 目前返回空列表
        return []

    def clear(self) -> bool:
        """清空所有锁定条目"""
        return self._save({"version": LOCK_VERSION, "installed": {}})


# 全局实例
_lock_file: Optional[HubLockFile] = None


def get_lock_file() -> HubLockFile:
    """获取全局 LockFile 实例"""
    global _lock_file
    if _lock_file is None:
        _lock_file = HubLockFile()
    return _lock_file


# 便捷函数

def lock_skill_install(
    skill_name: str,
    source: str,
    identifier: str,
    content: bytes = b"",
    **kwargs
) -> bool:
    """
    锁定技能安装
    
    Args:
        skill_name: 技能名称
        source: 来源类型
        identifier: 来源标识符
        content: 技能内容
        **kwargs: 其他参数
    
    Returns:
        是否成功
    """
    lock = get_lock_file()
    return lock.add_entry(skill_name, source, identifier, content, **kwargs)


def unlock_skill(skill_name: str) -> bool:
    """
    解锁技能（移除锁定）
    
    Args:
        skill_name: 技能名称
    
    Returns:
        是否成功
    """
    lock = get_lock_file()
    return lock.remove_entry(skill_name)


def is_skill_locked(skill_name: str) -> bool:
    """
    检查技能是否已锁定
    
    Args:
        skill_name: 技能名称
    
    Returns:
        是否已锁定
    """
    lock = get_lock_file()
    return lock.has_entry(skill_name)


def get_skill_lock_info(skill_name: str) -> Optional[HubLockEntry]:
    """
    获取技能锁定信息
    
    Args:
        skill_name: 技能名称
    
    Returns:
        锁定信息或 None
    """
    lock = get_lock_file()
    return lock.get_entry(skill_name)


def list_locked_skills(source: Optional[str] = None) -> List[HubLockEntry]:
    """
    列出已锁定的技能
    
    Args:
        source: 可选的来源过滤
    
    Returns:
        锁定条目列表
    """
    lock = get_lock_file()
    return lock.list_entries(source)


if __name__ == "__main__":
    # 测试
    lock = get_lock_file()
    
    # 添加测试条目
    lock.add_entry(
        skill_name="pdf-reader",
        source="github",
        identifier="hermes-agent/pdf-reader",
        content=b"test content",
        version="1.0.0",
        author="Hermes Team",
    )
    
    # 列出所有
    entries = lock.list_entries()
    print(f"Locked skills: {len(entries)}")
    for entry in entries:
        print(f"  - {entry.skill_name} ({entry.source})")
    
    # 检查更新
    has_update = lock.check_update_available("pdf-reader", b"new content")
    print(f"Update available: {has_update}")
