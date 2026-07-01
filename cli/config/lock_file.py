#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技能版本锁定文件管理

管理 skills/.lock 文件，记录已安装技能的版本信息。

🚪 Access - 💬 CLI - 锁文件管理
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class LockEntry:
    """锁文件条目"""
    skill_name: str
    version: str
    source: str  # 来源（github, url, local 等）
    source_ref: str  # 来源引用（如 GitHub URL）
    installed_at: str  # ISO 格式时间
    checksum: str = ""  # 文件校验和
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LockEntry':
        """从字典创建"""
        return cls(**data)


@dataclass
class LockFile:
    """锁文件数据"""
    version: str = "1.0"
    skills: Dict[str, LockEntry] = field(default_factory=dict)
    updated_at: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'version': self.version,
            'skills': {k: v.to_dict() for k, v in self.skills.items()},
            'updated_at': self.updated_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LockFile':
        """从字典创建"""
        skills = {}
        for k, v in data.get('skills', {}).items():
            skills[k] = LockEntry.from_dict(v)
        
        return cls(
            version=data.get('version', '1.0'),
            skills=skills,
            updated_at=data.get('updated_at', ''),
        )


class HubLockFile:
    """技能版本锁定文件管理器"""
    
    LOCK_FILE_NAME = ".lock"
    LOCK_FILE_VERSION = "1.0"
    
    def __init__(self, skills_dir: Path):
        """初始化锁文件管理器
        
        Args:
            skills_dir: 技能目录路径
        """
        self.skills_dir = Path(skills_dir)
        self.lock_file_path = self.skills_dir / self.LOCK_FILE_NAME
        self._lock_data: Optional[LockFile] = None
    
    def _ensure_loaded(self):
        """确保锁文件已加载"""
        if self._lock_data is None:
            self._lock_data = self._load()
    
    def _load(self) -> LockFile:
        """加载锁文件"""
        if not self.lock_file_path.exists():
            return LockFile()
        
        try:
            with open(self.lock_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return LockFile.from_dict(data)
        except Exception as e:
            logger.warning(f"Failed to load lock file: {e}")
            return LockFile()
    
    def _save(self):
        """保存锁文件"""
        self._ensure_loaded()
        self._lock_data.updated_at = datetime.now().isoformat()
        
        # 原子写入
        temp_path = self.lock_file_path.with_suffix('.tmp')
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(self._lock_data.to_dict(), f, indent=2, ensure_ascii=False)
            temp_path.replace(self.lock_file_path)
        except Exception as e:
            logger.error(f"Failed to save lock file: {e}")
            if temp_path.exists():
                temp_path.unlink()
            raise
    
    def add(self, skill_name: str, version: str, source: str, 
            source_ref: str, checksum: str = "", metadata: Dict = None) -> bool:
        """添加技能到锁文件
        
        Args:
            skill_name: 技能名称
            version: 版本
            source: 来源类型
            source_ref: 来源引用
            checksum: 文件校验和（可选）
            metadata: 额外元数据
        
        Returns:
            是否添加成功（False 表示版本冲突）
        """
        self._ensure_loaded()
        
        # 检查版本冲突
        if skill_name in self._lock_data.skills:
            existing = self._lock_data.skills[skill_name]
            if existing.version != version:
                logger.warning(
                    f"Version conflict for {skill_name}: "
                    f"locked={existing.version}, new={version}"
                )
                return False
        
        entry = LockEntry(
            skill_name=skill_name,
            version=version,
            source=source,
            source_ref=source_ref,
            installed_at=datetime.now().isoformat(),
            checksum=checksum,
            metadata=metadata or {},
        )
        
        self._lock_data.skills[skill_name] = entry
        self._save()
        
        logger.info(f"Added {skill_name} v{version} to lock file")
        return True
    
    def remove(self, skill_name: str) -> bool:
        """从锁文件移除技能
        
        Args:
            skill_name: 技能名称
        
        Returns:
            是否成功移除
        """
        self._ensure_loaded()
        
        if skill_name not in self._lock_data.skills:
            return False
        
        del self._lock_data.skills[skill_name]
        self._save()
        
        logger.info(f"Removed {skill_name} from lock file")
        return True
    
    def get(self, skill_name: str) -> Optional[LockEntry]:
        """获取技能锁记录
        
        Args:
            skill_name: 技能名称
        
        Returns:
            锁记录条目，如果不存在返回 None
        """
        self._ensure_loaded()
        return self._lock_data.skills.get(skill_name)
    
    def get_all(self) -> Dict[str, LockEntry]:
        """获取所有锁记录
        
        Returns:
            所有锁记录的字典
        """
        self._ensure_loaded()
        return self._lock_data.skills.copy()
    
    def check_conflict(self, skill_name: str, version: str) -> bool:
        """检查版本冲突
        
        Args:
            skill_name: 技能名称
            version: 要安装的版本
        
        Returns:
            True 表示有冲突，False 表示无冲突
        """
        self._ensure_loaded()
        
        if skill_name not in self._lock_data.skills:
            return False
        
        existing = self._lock_data.skills[skill_name]
        return existing.version != version
    
    def update(self, skill_name: str, version: str = None, 
               source_ref: str = None, checksum: str = None) -> bool:
        """更新锁记录
        
        Args:
            skill_name: 技能名称
            version: 新版本（可选）
            source_ref: 新来源引用（可选）
            checksum: 新校验和（可选）
        
        Returns:
            是否更新成功
        """
        self._ensure_loaded()
        
        if skill_name not in self._lock_data.skills:
            logger.warning(f"Skill {skill_name} not in lock file")
            return False
        
        entry = self._lock_data.skills[skill_name]
        
        if version is not None:
            entry.version = version
        if source_ref is not None:
            entry.source_ref = source_ref
        if checksum is not None:
            entry.checksum = checksum
        
        entry.installed_at = datetime.now().isoformat()
        
        self._save()
        return True
    
    def list_outdated(self, current_versions: Dict[str, str]) -> List[str]:
        """列出过时的技能
        
        Args:
            current_versions: {skill_name: current_version}
        
        Returns:
            过时技能的名称列表
        """
        self._ensure_loaded()
        
        outdated = []
        for skill_name, locked_entry in self._lock_data.skills.items():
            current = current_versions.get(skill_name)
            if current and current != locked_entry.version:
                outdated.append(skill_name)
        
        return outdated
    
    def compute_checksum(self, skill_dir: Path) -> str:
        """计算技能目录的校验和
        
        Args:
            skill_dir: 技能目录路径
        
        Returns:
            MD5 校验和
        """
        hash_md5 = hashlib.md5()
        
        for file_path in sorted(skill_dir.rglob('*')):
            if file_path.is_file():
                rel_path = file_path.relative_to(skill_dir)
                hash_md5.update(str(rel_path).encode())
                
                try:
                    content = file_path.read_bytes()
                    hash_md5.update(content)
                except Exception:
                    pass
        
        return hash_md5.hexdigest()
    
    def verify(self, skill_name: str, skill_dir: Path) -> bool:
        """验证技能完整性
        
        Args:
            skill_name: 技能名称
            skill_dir: 技能目录路径
        
        Returns:
            True 表示验证通过，False 表示验证失败或无法验证
        """
        self._ensure_loaded()
        
        entry = self._lock_data.skills.get(skill_name)
        if not entry or not entry.checksum:
            return True  # 无法验证，认为通过
        
        current_checksum = self.compute_checksum(skill_dir)
        return current_checksum == entry.checksum


def get_lock_file(skills_dir: Path = None) -> HubLockFile:
    """获取锁文件管理器实例
    
    Args:
        skills_dir: 技能目录路径，如果为 None 则使用默认路径
    
    Returns:
        HubLockFile 实例
    """
    if skills_dir is None:
        from common.config import get_skills_dir
        skills_dir = get_skills_dir()
    
    return HubLockFile(skills_dir)
