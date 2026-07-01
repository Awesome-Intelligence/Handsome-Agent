#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技能命名空间模块

支持 namespace:skill-name 格式引用技能，解决同名冲突。
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from pathlib import Path

from common.logging_manager import get_decision_logger

logger = get_decision_logger("SkillNamespace")

# 命名空间模式: namespace:skill-name
NAMESPACE_PATTERN = re.compile(r'^([a-zA-Z][a-zA-Z0-9_-]*):(.+)$')

# 默认命名空间
DEFAULT_NAMESPACE = "default"

# 保留命名空间（系统使用）
RESERVED_NAMESPACES = {"system", "user", "external", "default"}


@dataclass
class QualifiedSkill:
    """带命名空间的技能引用"""
    namespace: str
    skill_name: str
    full_name: str  # namespace:skill-name
    source: str = ""  # 来源标识


@dataclass 
class NamespaceRegistry:
    """命名空间注册表"""
    namespace_skills: Dict[str, Set[str]] = field(default_factory=dict)
    skill_namespaces: Dict[str, str] = field(default_factory=dict)  # skill_name -> namespace


class SkillNamespace:
    """技能命名空间管理器"""
    
    def __init__(self) -> None:
        self.registry = NamespaceRegistry()
        self._aliases: Dict[str, QualifiedSkill] = {}  # 别名 -> 完全限定名
    
    def register(
        self,
        skill_name: str,
        namespace: str = DEFAULT_NAMESPACE,
        skill_path: Optional[Path] = None,
    ) -> QualifiedSkill:
        """注册技能到命名空间
        
        Args:
            skill_name: 技能名称
            namespace: 命名空间
            skill_path: 技能路径
        
        Returns:
            QualifiedSkill: 完全限定的技能引用
        """
        # 规范化命名空间
        namespace = self._normalize_namespace(namespace)
        
        # 创建完全限定名
        qualified = QualifiedSkill(
            namespace=namespace,
            skill_name=skill_name,
            full_name=f"{namespace}:{skill_name}",
            source=str(skill_path) if skill_path else "",
        )
        
        # 注册到表
        if namespace not in self.registry.namespace_skills:
            self.registry.namespace_skills[namespace] = set()
        
        self.registry.namespace_skills[namespace].add(skill_name)
        self.registry.skill_namespaces[qualified.full_name] = namespace
        
        # 注册别名
        self._aliases[skill_name] = qualified
        self._aliases[qualified.full_name] = qualified
        
        logger.debug(f"Registered skill: {qualified.full_name}")
        
        return qualified
    
    def unregister(self, skill_name: str, namespace: Optional[str] = None) -> bool:
        """注销技能
        
        Args:
            skill_name: 技能名称
            namespace: 命名空间，None 表示所有命名空间
        
        Returns:
            是否成功注销
        """
        if namespace:
            qualified = self._resolve(skill_name, namespace)
            if qualified:
                self._remove_qualified(qualified)
                return True
            return False
        else:
            # 从所有命名空间移除
            removed = False
            for ns in list(self.registry.namespace_skills.keys()):
                if skill_name in self.registry.namespace_skills.get(ns, set()):
                    qualified = QualifiedSkill(
                        namespace=ns,
                        skill_name=skill_name,
                        full_name=f"{ns}:{skill_name}",
                    )
                    self._remove_qualified(qualified)
                    removed = True
            return removed
    
    def _remove_qualified(self, qualified: QualifiedSkill) -> None:
        """移除完全限定的技能"""
        ns = qualified.namespace
        name = qualified.skill_name
        
        if ns in self.registry.namespace_skills:
            self.registry.namespace_skills[ns].discard(name)
            if not self.registry.namespace_skills[ns]:
                del self.registry.namespace_skills[ns]
        
        self.registry.skill_namespaces.pop(qualified.full_name, None)
        self._aliases.pop(name, None)
        self._aliases.pop(qualified.full_name, None)
    
    def resolve(self, skill_ref: str) -> Optional[QualifiedSkill]:
        """解析技能引用
        
        Args:
            skill_ref: 技能引用（可以是简名、别名或完全限定名）
        
        Returns:
            QualifiedSkill 或 None
        """
        # 尝试解析 namespace:skill 格式
        match = NAMESPACE_PATTERN.match(skill_ref)
        if match:
            namespace = match.group(1)
            skill_name = match.group(2)
            return self._resolve(skill_name, namespace)
        
        # 简单名称：优先检查默认命名空间，避免同名冲突
        qualified = self._resolve(skill_ref, DEFAULT_NAMESPACE)
        if qualified:
            return qualified
        
        # 默认命名空间没有，则检查别名
        if skill_ref in self._aliases:
            return self._aliases[skill_ref]
        
        return None
    
    def _resolve_from_ref(self, ref: str) -> Optional[QualifiedSkill]:
        """从引用字符串解析（仅检查别名，不处理简单名称）"""
        # 检查是否已经是完全限定名
        if ref in self._aliases:
            return self._aliases[ref]
        
        return None
    
    def _resolve(
        self,
        skill_name: str,
        namespace: str = DEFAULT_NAMESPACE,
    ) -> Optional[QualifiedSkill]:
        """在指定命名空间中解析技能"""
        namespace = self._normalize_namespace(namespace)
        
        if skill_name in self.registry.namespace_skills.get(namespace, set()):
            # 尝试从别名表获取完整的 QualifiedSkill
            full_name = f"{namespace}:{skill_name}"
            if full_name in self._aliases:
                return self._aliases[full_name]
            # 降级：创建新的 QualifiedSkill（但会丢失 source）
            return QualifiedSkill(
                namespace=namespace,
                skill_name=skill_name,
                full_name=full_name,
            )
        
        return None
    
    def list_namespaces(self) -> List[str]:
        """列出所有命名空间"""
        return list(self.registry.namespace_skills.keys())
    
    def list_skills(
        self,
        namespace: Optional[str] = None,
    ) -> List[QualifiedSkill]:
        """列出命名空间中的技能
        
        Args:
            namespace: 命名空间，None 表示所有命名空间
        
        Returns:
            技能列表
        """
        skills = []
        namespaces = [namespace] if namespace else self.list_namespaces()
        
        for ns in namespaces:
            ns = self._normalize_namespace(ns)
            for name in self.registry.namespace_skills.get(ns, set()):
                skills.append(QualifiedSkill(
                    namespace=ns,
                    skill_name=name,
                    full_name=f"{ns}:{name}",
                ))
        
        return skills
    
    def get_skill_path(
        self,
        skill_name: str,
        namespace: Optional[str] = None,
    ) -> Optional[Path]:
        """获取技能路径
        
        Args:
            skill_name: 技能名称
            namespace: 命名空间
        
        Returns:
            技能路径或 None
        """
        qualified = self.resolve(f"{namespace}:{skill_name}" if namespace else skill_name)
        if qualified and qualified.source:
            return Path(qualified.source)
        return None
    
    def check_conflict(
        self,
        skill_name: str,
    ) -> List[QualifiedSkill]:
        """检查同名技能冲突
        
        Args:
            skill_name: 技能名称
        
        Returns:
            所有同名技能的列表
        """
        conflicts = []
        for ns, skills in self.registry.namespace_skills.items():
            if skill_name in skills:
                conflicts.append(QualifiedSkill(
                    namespace=ns,
                    skill_name=skill_name,
                    full_name=f"{ns}:{skill_name}",
                ))
        return conflicts
    
    def _normalize_namespace(self, namespace: str) -> str:
        """规范化命名空间"""
        return namespace.lower().strip()
    
    def is_reserved(self, namespace: str) -> bool:
        """检查是否是保留命名空间"""
        return namespace.lower() in RESERVED_NAMESPACES


# 全局实例
_namespace: Optional[SkillNamespace] = None


def get_skill_namespace() -> SkillNamespace:
    """获取全局命名空间管理器"""
    global _namespace
    if _namespace is None:
        _namespace = SkillNamespace()
    return _namespace


def parse_qualified_name(name: str) -> Tuple[str, str]:
    """解析完全限定技能名
    
    Args:
        name: namespace:skill-name 或 skill-name
    
    Returns:
        (namespace, skill_name)
    """
    match = NAMESPACE_PATTERN.match(name)
    if match:
        return match.group(1), match.group(2)
    return DEFAULT_NAMESPACE, name