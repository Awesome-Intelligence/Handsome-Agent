"""技能来源抽象基类"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path


@dataclass
class SourceResult:
    """来源搜索/安装结果"""
    success: bool
    skill_name: str
    skill_data: Optional[bytes] = None  # 技能内容（zip 或目录）
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    source_name: str = ""


@dataclass
class SourceSkillInfo:
    """技能元数据（用于搜索）"""
    name: str
    description: str
    author: str = ""
    version: str = ""
    source: str = ""
    url: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class SourceUpdateInfo:
    """来源更新信息"""
    skill_name: str
    has_update: bool
    current_version: str = ""
    latest_version: str = ""
    current_hash: str = ""
    latest_hash: str = ""
    changelog: str = ""
    source_name: str = ""


class SkillSource(ABC):
    """技能来源抽象基类"""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def search(self, query: str) -> List[SourceSkillInfo]:
        """搜索技能

        Args:
            query: 搜索关键词

        Returns:
            匹配的技能列表
        """
        pass

    @abstractmethod
    async def install(self, skill_ref: str, target_dir: Path) -> SourceResult:
        """安装技能

        Args:
            skill_ref: 技能引用（如 owner/repo 或 URL）
            target_dir: 安装目标目录

        Returns:
            安装结果
        """
        pass

    @abstractmethod
    def parse_ref(self, ref: str) -> Optional[Dict[str, Any]]:
        """解析技能引用

        Args:
            ref: 技能引用字符串

        Returns:
            解析后的引用信息，None 表示不匹配此来源
        """
        pass

    @property
    @abstractmethod
    def source_type(self) -> str:
        """来源类型标识"""
        pass

    async def fetch_latest(self, identifier: str, current_hash: str = "") -> Optional[SourceUpdateInfo]:
        """获取最新版本信息

        用于检测更新。

        Args:
            identifier: 技能标识符
            current_hash: 当前版本的哈希值

        Returns:
            更新信息，如果没有更新返回 None
        """
        # 默认实现不支持更新检测
        return None

    async def list_skills(self) -> List[SourceSkillInfo]:
        """列出来源中的所有技能

        Returns:
            技能列表
        """
        # 默认实现返回空列表
        return []
