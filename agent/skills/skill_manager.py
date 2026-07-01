#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill Manager Module - Inspired by Hermes Agent's skill system.

This module provides a unified framework for managing and executing skills.
Skills are self-contained units of functionality that can be dynamically loaded
and executed by the agent.

Supports multiple import methods:
- Decorator-based registration (@skill decorator)
- File/directory import (like OpenClaw)
- Module-based import (like Hermes)
- JSON/YAML configuration import
- Standard skill directory structure (industry standard - Hermes style)

Supports Hermes-style progressive skill discovery:
- Context-aware matching
- History-based recommendations
- Automatic parameter inference
- Multi-turn skill invocation
- Tag-based skill discovery
- Related skills recommendation

Standard Skill Directory Structure (Hermes Style):
skills/
  category/
    skill_name/
      SKILL.md          # Skill metadata documentation (YAML frontmatter + markdown)
      scripts/          # Helper scripts
      assets/           # Resource files (images, templates, etc.)
      references/       # Reference documentation
"""

import inspect
import asyncio
import os
import sys
import importlib
import json
import re
import time
from typing import Dict, List, Optional, Any, Callable, Union, Type
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging
from pathlib import Path

import yaml

from common.logging_manager import get_decision_logger
from agent.skills.fuzzy_match import fuzzy_find_and_replace
from agent.skill_utils import get_external_skills_dirs, iter_skill_index_files, parse_frontmatter
from tools.path_security import validate_within_dir


@dataclass
class SkillParameter:
    """Definition of a skill parameter."""
    name: str
    type: Type
    description: str
    required: bool = True
    default: Any = None
    prompt: str = ""


@dataclass
class SkillMetadata:
    """Metadata for a skill - compatible with Hermes SKILL.md format."""
    id: str
    name: str
    description: str
    category: str
    parameters: List[SkillParameter] = field(default_factory=list)
    requires_llm: bool = False
    requires_permission: bool = False
    aliases: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    source: str = "system"
    agent_created: bool = False
    usage_count: int = 0
    last_used: Optional[str] = None
    version: str = "1.0.0"
    author: str = ""
    license: str = "MIT"
    platforms: List[str] = field(default_factory=lambda: ["linux", "macos", "windows"])
    tags: List[str] = field(default_factory=list)
    related_skills: List[str] = field(default_factory=list)
    pinned: bool = False
    pinned_at: Optional[str] = None
    pinned_by: str = ""


@dataclass
class SkillResult:
    """Result of skill execution."""
    success: bool
    output: str
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseSkill(ABC):
    """Abstract base class for all skills."""
    
    @abstractmethod
    def get_metadata(self) -> SkillMetadata:
        """Return skill metadata."""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> SkillResult:
        """Execute the skill with provided arguments."""
        pass
    
    def validate_parameters(self, **kwargs) -> bool:
        """Validate input parameters."""
        metadata = self.get_metadata()
        for param in metadata.parameters:
            if param.required and param.name not in kwargs:
                return False
        return True
    
    def get_missing_parameters(self, **kwargs) -> List[str]:
        """获取缺失的必需参数"""
        metadata = self.get_metadata()
        missing = []
        for param in metadata.parameters:
            if param.required and param.name not in kwargs:
                missing.append(param.name)
        return missing


class SkillManager:
    """
    Manages the registration, discovery, and execution of skills.
    
    核心功能：
    - 技能注册与分类
    - 标签管理
    - 安全扫描集成
    - 技能固定 (Pinning)
    
    推荐功能由独立的 SkillRecommender 提供支持。
    支持跨 Profile 技能管理：
    - 每个 profile 有独立的技能目录
    - 可通过 profile 参数指定加载特定 profile 的技能
    """
    
    def __init__(self, profile: str = None, explanation_depth: str = "detailed", security_scan: bool = True):
        from common.config import get_current_profile, get_profile_skills_dir
        
        self._profile = profile or get_current_profile()
        self._skills_dir = get_profile_skills_dir(self._profile)
        
        self.skills: Dict[str, BaseSkill] = {}
        self.categories: Dict[str, List[str]] = {}
        self.tags: Dict[str, List[str]] = {}  # tag -> skill_ids
        self.skill_paths: Dict[str, str] = {}  # skill_id -> directory path
        self._explanation_depth = explanation_depth
        self._decision_logger = get_decision_logger("SkillManager")
        
        # 安全扫描配置
        self._security_scan_enabled = security_scan
        self._skill_scan_results: Dict[str, Any] = {}  # skill_id -> scan_result
        self._blocked_skills: Dict[str, str] = {}  # skill_id -> block_reason
        
        # 命名空间管理
        from agent.skill_namespace import get_skill_namespace
        self._namespace = get_skill_namespace()

    def record_usage(self, skill_id: str, success: bool = True) -> None:
        """记录技能使用情况
        
        同时更新多个追踪系统：
        - skills/telemetry.py (主追踪系统)
        - agent/skill_usage_tracker.py (Curator 兼容)
        
        Args:
            skill_id: 技能 ID
            success: 执行是否成功
        """
        # 更新 agent/skill_usage_tracker.py
        try:
            from agent.skill_usage_tracker import bump_use
            bump_use(skill_id)
        except ImportError:
            pass
        
        self._decision_logger.debug(f"Recorded skill usage: {skill_id}, success={success}")

    def record_view(self, skill_id: str) -> None:
        """记录技能查看
        
        同时更新多个追踪系统。
        
        Args:
            skill_id: 技能 ID
        """
        # 更新 agent/skill_usage_tracker.py
        try:
            from agent.skill_usage_tracker import bump_view
            bump_view(skill_id)
        except ImportError:
            pass

    def record_patch(self, skill_id: str) -> None:
        """记录技能修改
        
        同时更新多个追踪系统。
        
        Args:
            skill_id: 技能 ID
        """
        # 更新 agent/skill_usage_tracker.py
        try:
            from agent.skill_usage_tracker import bump_patch
            bump_patch(skill_id)
        except ImportError:
            pass

    @property
    def profile(self) -> str:
        """获取当前 profile 名称"""
        return self._profile
    
    @property
    def skills_dir(self) -> Path:
        """获取当前 profile 的技能目录"""
        return self._skills_dir
    
    def set_explanation_depth(self, depth: str) -> None:
        """设置日志详细程度"""
        self._explanation_depth = depth
    
    def register_skill(self, skill: BaseSkill):
        """Register a skill instance."""
        metadata = skill.get_metadata()
        
        self.skills[metadata.id] = skill
        
        for alias in metadata.aliases:
            self.skills[alias] = skill
        
        if metadata.category not in self.categories:
            self.categories[metadata.category] = []
        if metadata.id not in self.categories[metadata.category]:
            self.categories[metadata.category].append(metadata.id)
        
        for tag in metadata.tags:
            if tag not in self.tags:
                self.tags[tag] = []
            if metadata.id not in self.tags[tag]:
                self.tags[tag].append(metadata.id)
        
        try:
            from agent.skill_usage_tracker import get_skill_telemetry
            telemetry = get_skill_telemetry()
            if metadata.agent_created:
                telemetry.create_skill_record(
                    skill_id=metadata.id,
                    created_by="agent",
                    tags=metadata.tags,
                )
        except Exception as e:
            self._decision_logger.warning(f"Failed to create telemetry record: {e}")
        
        # 注册到命名空间
        self._namespace.register(
            skill_name=metadata.id,
            namespace=metadata.source or "default",
            skill_path=Path(metadata.source) if metadata.source else None,
        )
        
        self._decision_logger.info(f"Registered skill: {metadata.id} ({metadata.name})")
    
    def _scan_skill_security(self, skill_id: str, skill_path: Path, source: str = "community") -> Optional[Dict[str, Any]]:
        """
        对技能进行安全扫描
        
        Args:
            skill_id: 技能ID
            skill_path: 技能路径
            source: 技能来源
        
        Returns:
            扫描结果，如果被阻止则返回None
        """
        if not self._security_scan_enabled:
            return None
        
        try:
            from common.security import (
                scan_skill,
                should_allow_install,
                append_audit_log,
                quarantine_bundle,
            )
            from common.security.trust import TrustLevel, Verdict
            
            # 执行安全扫描
            scan_result = scan_skill(skill_path, source)
            
            # 记录扫描结果
            self._skill_scan_results[skill_id] = scan_result
            
            # 检查是否允许安装
            allowed, reason = should_allow_install(
                scan_result.verdict,
                scan_result.trust_level,
                force=False,
                findings_count=len(scan_result.findings),
            )
            
            # 记录审计日志
            append_audit_log(
                action="scan",
                skill_name=skill_id,
                source=source,
                trust_level=scan_result.trust_level.value,
                verdict=scan_result.verdict.value,
                extra=f"findings={len(scan_result.findings)}",
            )
            
            if allowed is True:
                self._decision_logger.info(f"技能安全扫描通过: {skill_id}")
                return scan_result.to_dict()
            elif allowed is None:
                # 需要确认 - 将技能隔离
                try:
                    files = []
                    for f in skill_path.rglob("*"):
                        if f.is_file():
                            rel_path = str(f.relative_to(skill_path))
                            try:
                                content = f.read_bytes()
                                files.append((rel_path, content))
                            except Exception:
                                pass
                    quarantine_bundle(skill_id, files)
                    append_audit_log(
                        action="quarantine",
                        skill_name=skill_id,
                        source=source,
                        trust_level=scan_result.trust_level.value,
                        verdict=scan_result.verdict.value,
                        extra=f"findings={len(scan_result.findings)}",
                    )
                except Exception as e:
                    self._decision_logger.warning(f"隔离技能失败: {skill_id}, {e}")
                
                self._blocked_skills[skill_id] = f"需要确认: {reason}"
                self._decision_logger.warning(f"技能需要确认: {skill_id} - {reason}")
                return None
            else:
                # 被阻止
                self._blocked_skills[skill_id] = reason
                self._decision_logger.warning(f"技能安全扫描阻止: {skill_id} - {reason}")
                
                append_audit_log(
                    action="block",
                    skill_name=skill_id,
                    source=source,
                    trust_level=scan_result.trust_level.value,
                    verdict=scan_result.verdict.value,
                    extra=f"reason={reason}",
                )
                return None
                
        except ImportError:
            self._decision_logger.warning("安全扫描模块不可用，跳过扫描")
            return None
        except Exception as e:
            self._decision_logger.error(f"安全扫描失败: {skill_id} - {e}")
            return None
    
    def get_skill_scan_result(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """
        获取技能的安全扫描结果
        
        Args:
            skill_id: 技能ID
        
        Returns:
            扫描结果字典
        """
        return self._skill_scan_results.get(skill_id)
    
    def is_skill_blocked(self, skill_id: str) -> bool:
        """
        检查技能是否被安全扫描阻止
        
        Args:
            skill_id: 技能ID
        
        Returns:
            是否被阻止
        """
        return skill_id in self._blocked_skills
    
    def get_block_reason(self, skill_id: str) -> Optional[str]:
        """
        获取技能被阻止的原因
        
        Args:
            skill_id: 技能ID
        
        Returns:
            阻止原因
        """
        return self._blocked_skills.get(skill_id)
    
    def scan_all_skills(self) -> Dict[str, Any]:
        """
        对所有已加载的技能进行安全扫描
        
        Returns:
            扫描结果汇总
        """
        results = {
            "total": len(self.skills),
            "scanned": 0,
            "passed": 0,
            "blocked": 0,
            "needs_confirmation": 0,
            "skills": {},
        }
        
        for skill_id, skill in self.skills.items():
            if skill_id in self._blocked_skills:
                results["blocked"] += 1
                continue
            
            skill_path_str = self.skill_paths.get(skill_id)
            if not skill_path_str:
                continue
            
            skill_path = Path(skill_path_str)
            if not skill_path.exists():
                continue
            
            metadata = skill.get_metadata()
            scan_result = self._scan_skill_security(skill_id, skill_path, metadata.source)
            
            results["scanned"] += 1
            if scan_result:
                results["passed"] += 1
                results["skills"][skill_id] = scan_result
            else:
                if skill_id in self._blocked_skills:
                    reason = self._blocked_skills[skill_id]
                    if "需要确认" in reason:
                        results["needs_confirmation"] += 1
                    else:
                        results["blocked"] += 1
        
        return results
    
    def unregister_skill(self, skill_id: str, force: bool = False):
        """注销技能（支持 force 覆盖 pinned 保护）"""
        if skill_id not in self.skills:
            self._decision_logger.warning(f"技能不存在: {skill_id}")
            return
        
        metadata = self.skills[skill_id].get_metadata()
        
        # 检查 pinned 状态
        if metadata.pinned and not force:
            error_msg = f"无法注销固定技能: {skill_id}，请先取消固定或使用 force=True"
            self._decision_logger.warning(error_msg)
            raise PermissionError(error_msg)
        
        if metadata.category in self.categories:
            if skill_id in self.categories[metadata.category]:
                self.categories[metadata.category].remove(skill_id)
        
        for tag in metadata.tags:
            if tag in self.tags and skill_id in self.tags[tag]:
                self.tags[tag].remove(skill_id)
        
        for alias in metadata.aliases:
            if alias in self.skills:
                del self.skills[alias]
        
        try:
            from agent.skill_usage_tracker import get_skill_telemetry
            telemetry = get_skill_telemetry()
            telemetry.delete_skill_record(skill_id)
        except Exception as e:
            self._decision_logger.warning(f"Failed to delete telemetry record: {e}")
        
        del self.skills[skill_id]
        self._decision_logger.info(f"Unregistered skill: {skill_id}")
    
    def pin_skill(self, skill_id: str, pinned_by: str = "user") -> bool:
        """固定技能
        
        Args:
            skill_id: 技能 ID
            pinned_by: 固定操作者
        
        Returns:
            是否固定成功
        """
        if skill_id not in self.skills:
            self._decision_logger.warning(f"无法固定不存在的技能: {skill_id}")
            return False
        
        skill = self.skills[skill_id]
        metadata = skill.get_metadata()
        metadata.pinned = True
        metadata.pinned_at = str(int(time.time()))
        metadata.pinned_by = pinned_by
        
        self._decision_logger.info(f"固定技能: {skill_id} (by: {pinned_by})")
        return True
    
    def unpin_skill(self, skill_id: str) -> bool:
        """取消固定技能
        
        Args:
            skill_id: 技能 ID
        
        Returns:
            是否取消固定成功
        """
        if skill_id not in self.skills:
            self._decision_logger.warning(f"无法取消固定不存在的技能: {skill_id}")
            return False
        
        skill = self.skills[skill_id]
        metadata = skill.get_metadata()
        
        if not metadata.pinned:
            self._decision_logger.warning(f"技能未被固定，无需取消: {skill_id}")
            return False
        
        metadata.pinned = False
        metadata.pinned_at = None
        metadata.pinned_by = ""
        
        self._decision_logger.info(f"取消固定技能: {skill_id}")
        return True
    
    def _find_collision_candidates(self, skill_name: str) -> List[Dict]:
        """
        检测同名技能冲突
        
        在多个搜索路径中查找同名技能，返回冲突技能列表。
        
        Args:
            skill_name: 技能名称
        
        Returns:
            冲突技能列表，每个元素包含路径信息
        """
        candidates = []
        
        # 获取所有技能目录（本地 + 外部）
        all_dirs = [self._skills_dir]
        try:
            external_dirs = get_external_skills_dirs()
            all_dirs.extend(external_dirs)
        except Exception as e:
            self._decision_logger.warning(f"获取外部技能目录失败: {e}")
        
        # 在所有目录中搜索同名技能
        for base_dir in all_dirs:
            if not base_dir.exists():
                continue
            
            try:
                # 使用 iter_skill_index_files 递归查找 SKILL.md 文件
                for skill_md_path in iter_skill_index_files(base_dir):
                    try:
                        content = skill_md_path.read_text(encoding='utf-8')
                        frontmatter, body = parse_frontmatter(content)
                        
                        # 检查技能名称是否匹配（支持 name 字段或目录名）
                        skill_md_name = frontmatter.get('name', '')
                        skill_dir_name = skill_md_path.parent.name
                        
                        if skill_md_name == skill_name or skill_dir_name == skill_name:
                            candidate = {
                                'name': skill_md_name or skill_dir_name,
                                'path': str(skill_md_path.parent),
                                'file': str(skill_md_path),
                                'directory': str(skill_md_path.parent),
                                'category': frontmatter.get('category', 'unknown'),
                                'version': frontmatter.get('version', 'unknown'),
                                'description': frontmatter.get('description', ''),
                                'author': frontmatter.get('author', ''),
                            }
                            
                            # 避免重复添加自身
                            if skill_md_path.parent != self.skill_paths.get(skill_name):
                                candidates.append(candidate)
                            
                    except Exception as e:
                        self._decision_logger.debug(f"解析技能文件失败 {skill_md_path}: {e}")
                        continue
                        
            except Exception as e:
                self._decision_logger.warning(f"遍历技能目录失败 {base_dir}: {e}")
                continue
        
        return candidates
    
    def patch_skill(
        self,
        skill_id: str,
        old_string: str,
        new_string: str,
        fuzzy: bool = False,
        replace_all: bool = False
    ) -> SkillResult:
        """
        修补技能内容
        
        Args:
            skill_id: 技能ID
            old_string: 要替换的旧文本
            new_string: 替换后的新文本
            fuzzy: 是否使用模糊匹配（默认 False）
            replace_all: 是否替换所有匹配项（默认 False）
        
        Returns:
            SkillResult: 包含成功状态、消息、替换次数等信息
        """
        # 1. 检查技能是否存在
        if skill_id not in self.skills:
            self._decision_logger.warning(f"技能不存在: {skill_id}")
            return SkillResult(
                success=False,
                output="",
                error=f"技能不存在: {skill_id}"
            )
        
        # 2. 获取技能路径
        if skill_id not in self.skill_paths:
            self._decision_logger.warning(f"技能无文件路径: {skill_id}")
            return SkillResult(
                success=False,
                output="",
                error=f"技能无文件路径（仅支持从目录导入的技能）: {skill_id}"
            )
        
        skill_path = Path(self.skill_paths[skill_id])
        skill_md = skill_path / "SKILL.md"
        
        # 路径安全检查：验证技能路径在允许范围内
        safety_error = validate_within_dir(skill_path, self._skills_dir)
        if safety_error:
            self._decision_logger.error(f"路径安全检查失败: {safety_error}")
            return SkillResult(
                success=False,
                output="",
                error=f"路径安全检查失败: 不允许访问该路径"
            )
        
        # 检查是否为外部目录的技能
        try:
            external_dirs = get_external_skills_dirs()
            for ext_dir in external_dirs:
                ext_safety = validate_within_dir(skill_path, ext_dir)
                if ext_safety is None:
                    # 路径在外部目录范围内
                    break
            else:
                # 如果所有外部目录检查都失败，但路径不在本地目录范围内
                if validate_within_dir(skill_path, self._skills_dir) is None:
                    pass  # 本地目录检查已通过
                else:
                    self._decision_logger.warning(f"技能路径不在任何允许的目录范围内: {skill_path}")
        except Exception as e:
            self._decision_logger.warning(f"外部目录验证跳过: {e}")
        
        if not skill_md.exists():
            # 尝试小写文件名
            skill_md_lower = skill_path / "skill.md"
            if skill_md_lower.exists():
                skill_md = skill_md_lower
            else:
                self._decision_logger.error(f"技能文件不存在: {skill_md}")
                return SkillResult(
                    success=False,
                    output="",
                    error=f"技能文件不存在: {skill_md}"
                )
        
        # 3. 读取技能内容
        try:
            content = skill_md.read_text(encoding='utf-8')
        except Exception as e:
            self._decision_logger.error(f"读取技能文件失败: {e}")
            return SkillResult(
                success=False,
                output="",
                error=f"读取技能文件失败: {str(e)}"
            )
        
        # 4. 执行替换
        if fuzzy:
            # 模糊匹配模式
            new_content, match_count, strategy, error_msg = fuzzy_find_and_replace(
                content, old_string, new_string, replace_all
            )
        else:
            # 精确匹配模式
            new_content, match_count, strategy, error_msg = fuzzy_find_and_replace(
                content, old_string, new_string, replace_all
            )
        
        # 检查是否找到匹配
        if strategy == "none":
            self._decision_logger.warning(f"未找到匹配内容: {skill_id}")
            return SkillResult(
                success=False,
                output="",
                error=error_msg or "未找到匹配内容",
                data={
                    "match_count": 0,
                    "strategy": strategy,
                    "skill_id": skill_id
                }
            )
        
        # 5. 原子写入更新后的内容
        try:
            # 先写入临时文件，再重命名（原子操作）
            temp_path = skill_md.with_suffix('.md.tmp')
            temp_path.write_text(new_content, encoding='utf-8')
            temp_path.replace(skill_md)
        except Exception as e:
            self._decision_logger.error(f"写入技能文件失败: {e}")
            # 清理临时文件
            if temp_path.exists():
                temp_path.unlink()
            return SkillResult(
                success=False,
                output="",
                error=f"写入技能文件失败: {str(e)}"
            )
        
        # 6. 返回结果
        output = f"成功替换 {match_count} 处"
        if strategy == "fuzzy":
            output += " (模糊匹配)"
        
        self._decision_logger.info(f"修补技能 {skill_id}: {output}")
        
        return SkillResult(
            success=True,
            output=output,
            data={
                "match_count": match_count,
                "strategy": strategy,
                "skill_id": skill_id
            }
        )
    
    def list_pinned_skills(self) -> List[SkillMetadata]:
        """列出所有固定技能
        
        Returns:
            固定技能的元数据列表
        """
        pinned_skills = []
        seen_ids = set()
        for skill in self.skills.values():
            metadata = skill.get_metadata()
            # 只返回原始技能（不返回别名），且避免重复
            if metadata.pinned and metadata.id not in seen_ids:
                seen_ids.add(metadata.id)
                pinned_skills.append(metadata)
        return pinned_skills
    
    def is_pinned(self, skill_id: str) -> bool:
        """检查技能是否固定
        
        Args:
            skill_id: 技能 ID
        
        Returns:
            是否已固定
        """
        if skill_id not in self.skills:
            return False
        return self.skills[skill_id].get_metadata().pinned
    
    def get_skill(self, skill_id: str) -> Optional[BaseSkill]:
        """Get a skill by ID, supports namespace:skill-name format."""
        # 先尝试直接查找
        if skill_id in self.skills:
            return self.skills[skill_id]
        # 尝试通过命名空间解析
        qualified = self._namespace.resolve(skill_id)
        if qualified:
            return self.skills.get(qualified.full_name) or self.skills.get(qualified.skill_name)
        return None
    
    def get_skill_by_namespace(self, skill_name: str, namespace: str = "default") -> Optional[BaseSkill]:
        """Get a skill by name within a specific namespace."""
        qualified_name = f"{namespace}:{skill_name}"
        qualified = self._namespace.resolve(qualified_name)
        if qualified:
            return self.skills.get(qualified.full_name) or self.skills.get(qualified.skill_name)
        return None
    
    def list_namespaced_skills(self, namespace: Optional[str] = None) -> List[Dict[str, str]]:
        """List all skills with their namespaces.
        
        Args:
            namespace: Filter by namespace, None for all
            
        Returns:
            List of dicts with skill_name, namespace, full_name
        """
        results = []
        for qualified in self._namespace.list_skills(namespace):
            results.append({
                "skill_name": qualified.skill_name,
                "namespace": qualified.namespace,
                "full_name": qualified.full_name,
            })
        return results
    
    def check_namespace_conflicts(self) -> Dict[str, List[Dict[str, str]]]:
        """Check for skills with conflicting names across namespaces.
        
        Returns:
            Dict mapping skill names to list of namespaces where they exist
        """
        conflicts = {}
        skill_map = {}  # skill_name -> list of namespaces
        
        for qualified in self._namespace.list_skills():
            name = qualified.skill_name
            if name not in skill_map:
                skill_map[name] = []
            skill_map[name].append({
                "namespace": qualified.namespace,
                "full_name": qualified.full_name,
            })
        
        # 只返回有冲突的（多个命名空间使用同一名称）
        for name, namespaces in skill_map.items():
            if len(namespaces) > 1:
                conflicts[name] = namespaces
        
        return conflicts
    
    def list_skills(self, category: Optional[str] = None) -> List[SkillMetadata]:
        """List all skills, optionally filtered by category."""
        if category:
            skill_ids = self.categories.get(category, [])
            return [self.skills[sid].get_metadata() for sid in skill_ids if sid in self.skills]
        
        return [skill.get_metadata() for skill in self.skills.values()]
    
    def get_categories(self) -> List[str]:
        """Get all categories."""
        return list(self.categories.keys())
    
    def get_skills_by_tag(self, tag: str) -> List[SkillMetadata]:
        """Get skills by tag."""
        skill_ids = self.tags.get(tag, [])
        return [self.skills[sid].get_metadata() for sid in skill_ids if sid in self.skills]
    
    def get_related_skills(self, skill_id: str) -> List[SkillMetadata]:
        """Get related skills for a given skill."""
        skill = self.get_skill(skill_id)
        if not skill:
            return []
        
        metadata = skill.get_metadata()
        related = []
        for related_id in metadata.related_skills:
            related_skill = self.get_skill(related_id)
            if related_skill:
                related.append(related_skill.get_metadata())
        return related
    
    # ============ 技能执行方法 ============
    
    async def execute_skill(self, skill_id: str, **kwargs) -> SkillResult:
        """Execute a skill by ID."""
        if self._explanation_depth == 'detailed':
            self._decision_logger.debug(f"execute_skill() 尝试执行技能: {skill_id}")
        
        skill = self.get_skill(skill_id)
        
        if not skill:
            self._decision_logger.warning(f"技能未找到: {skill_id}")
            return SkillResult(
                success=False,
                output="",
                error=f"Skill not found: {skill_id}"
            )
        
        metadata = skill.get_metadata()
        skill_class = metadata.name
        
        if not skill.validate_parameters(**kwargs):
            required_params = [p.name for p in metadata.parameters if p.required]
            self._decision_logger.warning(f"{skill_class}.validate_parameters() 失败，缺少必需参数: {', '.join(required_params)}")
            return SkillResult(
                success=False,
                output="",
                error=f"Missing required parameters: {', '.join(required_params)}"
            )
        
        if self._explanation_depth == 'detailed':
            self._decision_logger.debug(f"{skill_class}.validate_parameters() 验证通过")
            self._decision_logger.debug(f"{skill_class}.execute() 开始执行...")
        
        try:
            result = await skill.execute(**kwargs)
            
            self.record_usage(skill_id, result.success)
            
            if result.success:
                if self._explanation_depth == 'detailed':
                    self._decision_logger.debug(f"{skill_class}.execute() 执行成功")
                self._decision_logger.summary(f"✅ 技能 {skill_class} 执行成功")
            else:
                self._decision_logger.warning(f"{skill_class}.execute() 执行失败: {result.error}")
            
            return result
            
        except Exception as e:
            self.record_usage(skill_id, False)
            self._decision_logger.error(f"{skill_class}.execute() 执行异常: {str(e)}")
            return SkillResult(
                success=False,
                output="",
                error=f"Error executing skill: {str(e)}"
            )
    
    # ============ 技能导入功能 ============
    
    def import_skill_from_directory_structure(self, skills_dir: str = None) -> int:
        """
        从标准技能目录结构导入技能（Hermes 风格）
        
        目录结构:
        skills/
          category/
            skill_name/
              SKILL.md          # 技能元数据文档（YAML frontmatter + markdown）
              scripts/          # 辅助脚本
              assets/           # 资源文件
              references/       # 参考文档
        
        Args:
            skills_dir: 技能目录路径，默认为当前 profile 的技能目录
        
        Returns:
            成功导入的技能数量
        """
        # 使用 profile 技能目录或指定的目录
        skills_dir = skills_dir or str(self._skills_dir)
        
        if not os.path.isdir(skills_dir):
            self._decision_logger.warning(f"技能目录不存在: {skills_dir}，将跳过导入")
            return 0
        
        self._decision_logger.info(f"从技能目录导入: {skills_dir} (profile: {self._profile})")
        
        # 收集所有需要扫描的目录（本地 + 外部）
        all_skills_dirs = [(Path(skills_dir), "local")]
        
        try:
            external_dirs = get_external_skills_dirs()
            for ext_dir in external_dirs:
                if ext_dir.exists() and ext_dir.is_dir():
                    all_skills_dirs.append((ext_dir, "external"))
                    self._decision_logger.info(f"添加外部技能目录: {ext_dir}")
        except Exception as e:
            self._decision_logger.warning(f"获取外部技能目录失败: {e}")
        
        imported_count = 0
        
        # 遍历所有技能目录
        for current_dir, dir_type in all_skills_dirs:
            try:
                dir_count = self._import_from_single_directory(current_dir, dir_type)
                imported_count += dir_count
            except Exception as e:
                self._decision_logger.error(f"从目录导入技能失败 {current_dir}: {str(e)}")
        
        self._decision_logger.info(f"从标准目录结构成功导入 {imported_count} 个技能")
        return imported_count
    
    def _import_from_single_directory(self, skills_dir: Path, dir_type: str = "local") -> int:
        """
        从单个技能目录导入技能
        
        Args:
            skills_dir: 技能目录路径
            dir_type: 目录类型 ("local" 或 "external")
        
        Returns:
            成功导入的技能数量
        """
        imported_count = 0
        
        for category_dir in os.listdir(skills_dir):
            category_path = skills_dir / category_dir
            
            if not category_path.is_dir():
                continue
            
            for skill_dir in os.listdir(category_path):
                skill_path = category_path / skill_dir
                
                if not skill_path.is_dir():
                    continue
                
                # 优先从 skill.py 文件导入（Python 实现）
                skill_py = skill_path / "skill.py"
                if skill_py.is_file():
                    try:
                        dir_name = str(skill_py.parent)
                        file_name = skill_py.name
                        module_name = file_name[:-3]
                        
                        if dir_name not in sys.path:
                            sys.path.insert(0, dir_name)
                        
                        module = importlib.import_module(module_name)
                        
                        for name in dir(module):
                            obj = getattr(module, name)
                            if isinstance(obj, BaseSkill):
                                obj.get_metadata().source = "external" if dir_type == "external" else "user"
                                obj.get_metadata().category = category_dir
                                
                                # 安全扫描
                                scan_result = self._scan_skill_security(
                                    obj.get_metadata().id,
                                    skill_path,
                                    obj.get_metadata().source,
                                )
                                
                                if scan_result is None and self.is_skill_blocked(obj.get_metadata().id):
                                    self._decision_logger.warning(
                                        f"技能安全扫描阻止，跳过注册: {obj.get_metadata().id}"
                                    )
                                    continue
                                
                                self.register_skill(obj)
                                self.skill_paths[obj.get_metadata().id] = str(skill_path)
                                imported_count += 1
                                self._decision_logger.info(f"从 skill.py 导入技能: {obj.get_metadata().id}")
                        
                        if dir_name in sys.path:
                            sys.path.remove(dir_name)
                        
                        continue
                    except Exception as e:
                        self._decision_logger.error(f"从 skill.py 导入技能失败 {skill_dir}: {str(e)}")
                
                # 否则从 SKILL.md 文件创建（Hermes 风格）
                skill_md = skill_path / "SKILL.md"
                if not skill_md.is_file():
                    skill_md = skill_path / "skill.md"
                
                if not skill_md.is_file():
                    self._decision_logger.warning(f"跳过非标准技能目录（缺少 SKILL.md 和 skill.py）: {skill_dir}")
                    continue
                
                try:
                    skill = self._create_skill_from_hermes_md(str(skill_md))
                    if skill:
                        skill.get_metadata().source = "external" if dir_type == "external" else "user"
                        skill.get_metadata().category = category_dir
                        
                        # 安全扫描
                        scan_result = self._scan_skill_security(
                            skill.get_metadata().id,
                            skill_path,
                            skill.get_metadata().source,
                        )
                        
                        if scan_result is None and self.is_skill_blocked(skill.get_metadata().id):
                            self._decision_logger.warning(
                                f"技能安全扫描阻止，跳过注册: {skill.get_metadata().id}"
                            )
                            continue
                        
                        self.register_skill(skill)
                        self.skill_paths[skill.get_metadata().id] = str(skill_path)
                        imported_count += 1
                        self._decision_logger.info(f"从 Hermes 风格目录导入技能: {skill.get_metadata().id}")
                
                except Exception as e:
                    self._decision_logger.error(f"从目录导入技能失败 {skill_dir}: {str(e)}")
        
        return imported_count
    
    def _create_skill_from_hermes_md(self, md_path: str) -> Optional[BaseSkill]:
        """
        从 Hermes 风格的 SKILL.md 文件创建技能
        
        Hermes SKILL.md 格式:
        ---
        name: skill_name
        description: "Skill description"
        version: 1.0.0
        author: Hermes Agent
        license: MIT
        platforms: [linux, macos, windows]
        metadata:
          hermes:
            tags: [tag1, tag2]
            related_skills: [skill1, skill2]
        ---
        # Skill Documentation
        ...
        """
        try:
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()

            frontmatter, _ = parse_frontmatter(content)
            if frontmatter == {}:
                self._decision_logger.warning(f"SKILL.md 缺少 YAML frontmatter: {md_path}")
                return None
            
            skill_id = frontmatter.get('name', os.path.basename(os.path.dirname(md_path)))
            name = frontmatter.get('name', skill_id)
            description = frontmatter.get('description', '')
            version = frontmatter.get('version', '1.0.0')
            author = frontmatter.get('author', '')
            license = frontmatter.get('license', 'MIT')
            platforms = frontmatter.get('platforms', ['linux', 'macos', 'windows'])
            
            # 解析 metadata.hermes
            metadata = frontmatter.get('metadata', {}).get('hermes', {})
            tags = metadata.get('tags', [])
            related_skills = metadata.get('related_skills', [])
            
            # 从文档中提取示例
            examples = []
            example_section = re.search(r'##\s*(Examples|示例|使用示例)\s*\n((?:- .+\n?)+)', content)
            if example_section:
                examples = [line.strip('- ').strip('"').strip("'") 
                           for line in example_section.group(2).strip().split('\n') if line.strip()]
            
            # 创建技能类
            class HermesSkill(BaseSkill):
                _skill_id = skill_id
                _name = name
                _description = description
                _version = version
                _author = author
                _license = license
                _platforms = platforms
                _tags = tags
                _related_skills = related_skills
                _examples = examples
                _md_path = md_path
                
                def get_metadata(self) -> SkillMetadata:
                    return SkillMetadata(
                        id=self._skill_id,
                        name=self._name,
                        description=self._description,
                        category="general",
                        version=self._version,
                        author=self._author,
                        license=self._license,
                        platforms=self._platforms,
                        tags=self._tags,
                        related_skills=self._related_skills,
                        examples=self._examples
                    )
                
                async def execute(self, **kwargs) -> SkillResult:
                    # Hermes 风格技能的执行逻辑
                    # 可以调用 scripts 目录中的脚本
                    script_path = os.path.join(os.path.dirname(self._md_path), "scripts")
                    if os.path.isdir(script_path):
                        for script in os.listdir(script_path):
                            if script.endswith('.py'):
                                try:
                                    script_full_path = os.path.join(script_path, script)
                                    result = await self._run_script(script_full_path, kwargs)
                                    return result
                                except Exception as e:
                                    pass
                    
                    return SkillResult(
                        success=True,
                        output=f"技能 {self._name} 执行成功。详细用法请查看文档。"
                    )
                
                async def _run_script(self, script_path: str, kwargs: dict) -> SkillResult:
                    """运行技能脚本"""
                    import subprocess
                    cmd = ["python", script_path]
                    for key, value in kwargs.items():
                        cmd.append(f"--{key}")
                        cmd.append(str(value))
                    
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    return SkillResult(
                        success=result.returncode == 0,
                        output=result.stdout,
                        error=result.stderr if result.returncode != 0 else None
                    )
            
            return HermesSkill()
            
        except Exception as e:
            self._decision_logger.error(f"解析 SKILL.md 失败 {md_path}: {str(e)}")
            return None
    
    def import_skill_from_file(self, file_path: str) -> bool:
        """从 Python 文件导入技能"""
        if not os.path.isfile(file_path):
            self._decision_logger.error(f"技能文件不存在: {file_path}")
            return False
        
        try:
            dir_name = os.path.dirname(file_path)
            file_name = os.path.basename(file_path)
            module_name = file_name[:-3]
            
            if dir_name not in sys.path:
                sys.path.insert(0, dir_name)
            
            module = importlib.import_module(module_name)
            
            for name in dir(module):
                obj = getattr(module, name)
                if isinstance(obj, BaseSkill):
                    obj.get_metadata().source = "user"
                    self.register_skill(obj)
                    self._decision_logger.info(f"从文件导入技能: {obj.get_metadata().id}")
            
            if dir_name in sys.path:
                sys.path.remove(dir_name)
            
            return True
        except Exception as e:
            self._decision_logger.error(f"从文件导入技能失败: {str(e)}")
            return False
    
    def import_skills_from_directory(self, directory: str, recursive: bool = True) -> int:
        """从目录批量导入技能"""
        if not os.path.isdir(directory):
            self._decision_logger.error(f"技能目录不存在: {directory}")
            return 0
        
        imported_count = 0
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.py') and not file.startswith('_'):
                    file_path = os.path.join(root, file)
                    if self.import_skill_from_file(file_path):
                        imported_count += 1
            
            if not recursive:
                break
        
        self._decision_logger.info(f"从目录成功导入 {imported_count} 个技能")
        return imported_count
    
    def import_skill_from_module(self, module_path: str) -> bool:
        """从 Python 模块导入技能"""
        try:
            module = importlib.import_module(module_path)
            
            for name in dir(module):
                obj = getattr(module, name)
                if isinstance(obj, BaseSkill):
                    obj.get_metadata().source = "external"
                    self.register_skill(obj)
                    self._decision_logger.info(f"从模块导入技能: {obj.get_metadata().id}")
            
            return True
        except ImportError as e:
            self._decision_logger.error(f"导入模块失败: {str(e)}")
            return False
    
    def import_skills_from_json(self, json_path: str) -> int:
        """从 JSON 配置文件导入技能"""
        if not os.path.isfile(json_path):
            self._decision_logger.error(f"JSON 文件不存在: {json_path}")
            return 0
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                skills_data = json.load(f)
            
            imported_count = 0
            for skill_data in skills_data:
                skill = self._create_skill_from_config(skill_data)
                if skill:
                    skill.get_metadata().source = "user"
                    self.register_skill(skill)
                    imported_count += 1
            
            self._decision_logger.info(f"从 JSON 导入 {imported_count} 个技能")
            return imported_count
        except Exception as e:
            self._decision_logger.error(f"从 JSON 导入技能失败: {str(e)}")
            return 0
    
    def import_skills_from_yaml(self, yaml_path: str) -> int:
        """从 YAML 配置文件导入技能"""
        import yaml

        if not os.path.isfile(yaml_path):
            self._decision_logger.error(f"YAML 文件不存在: {yaml_path}")
            return 0

        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                skills_data = yaml.safe_load(f)
            
            imported_count = 0
            for skill_data in skills_data:
                skill = self._create_skill_from_config(skill_data)
                if skill:
                    skill.get_metadata().source = "user"
                    self.register_skill(skill)
                    imported_count += 1
            
            self._decision_logger.info(f"从 YAML 导入 {imported_count} 个技能")
            return imported_count
        except Exception as e:
            self._decision_logger.error(f"从 YAML 导入技能失败: {str(e)}")
            return 0
    
    def _create_skill_from_config(self, config: dict) -> Optional[BaseSkill]:
        """从配置字典创建技能实例"""
        try:
            skill_id = config.get('id')
            name = config.get('name', skill_id)
            description = config.get('description', '')
            category = config.get('category', 'general')
            aliases = config.get('aliases', [])
            examples = config.get('examples', [])
            requires_llm = config.get('requires_llm', False)
            requires_permission = config.get('requires_permission', False)
            version = config.get('version', '1.0.0')
            tags = config.get('tags', [])
            related_skills = config.get('related_skills', [])
            
            class ConfigSkill(BaseSkill):
                _config_id = skill_id
                _config_name = name
                _config_desc = description
                _config_category = category
                _config_aliases = aliases
                _config_examples = examples
                _config_requires_llm = requires_llm
                _config_requires_permission = requires_permission
                _config_version = version
                _config_tags = tags
                _config_related = related_skills
                _config_params = config.get('parameters', [])
                
                def get_metadata(self) -> SkillMetadata:
                    parameters = []
                    for p in self._config_params:
                        param_type = str
                        if p.get('type') == 'int':
                            param_type = int
                        elif p.get('type') == 'float':
                            param_type = float
                        elif p.get('type') == 'bool':
                            param_type = bool
                        
                        parameters.append(SkillParameter(
                            name=p['name'],
                            type=param_type,
                            description=p.get('description', ''),
                            required=p.get('required', True),
                            default=p.get('default'),
                            prompt=p.get('prompt', '')
                        ))
                    
                    return SkillMetadata(
                        id=self._config_id,
                        name=self._config_name,
                        description=self._config_desc,
                        category=self._config_category,
                        parameters=parameters,
                        requires_llm=self._config_requires_llm,
                        requires_permission=self._config_requires_permission,
                        aliases=self._config_aliases,
                        examples=self._config_examples,
                        version=self._config_version,
                        tags=self._config_tags,
                        related_skills=self._config_related
                    )
                
                async def execute(self, **kwargs) -> SkillResult:
                    action = config.get('action', '')
                    if action:
                        try:
                            if action.startswith('command:'):
                                import subprocess
                                cmd = action[8:].format(**kwargs)
                                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                                return SkillResult(
                                    success=result.returncode == 0,
                                    output=result.stdout,
                                    error=result.stderr if result.returncode != 0 else None
                                )
                            elif action.startswith('python:'):
                                code = action[7:].format(**kwargs)
                                exec_globals = {}
                                exec(code, exec_globals)
                                return SkillResult(
                                    success=True,
                                    output=str(exec_globals.get('result', ''))
                                )
                        except Exception as e:
                            return SkillResult(
                                success=False,
                                output="",
                                error=str(e)
                            )
                    
                    return SkillResult(
                        success=True,
                        output=f"技能 {self._config_name} 执行成功"
                    )
            
            return ConfigSkill()
        except Exception as e:
            self._decision_logger.error(f"从配置创建技能失败: {str(e)}")
            return None


skill_manager = SkillManager()


def skill(id: str, name: str, description: str, category: str = 'general',
          requires_llm: bool = False, requires_permission: bool = False,
          aliases: List[str] = None, examples: List[str] = None,
          version: str = "1.0.0", tags: List[str] = None, related_skills: List[str] = None):
    """Decorator to register a class as a skill."""
    def decorator(cls: Type[BaseSkill]):
        instance = cls()
        instance._skill_id = id
        instance._skill_name = name
        instance._skill_description = description
        instance._skill_category = category
        instance._skill_requires_llm = requires_llm
        instance._skill_requires_permission = requires_permission
        instance._skill_aliases = aliases or []
        instance._skill_examples = examples or []
        instance._skill_version = version
        instance._skill_tags = tags or []
        instance._skill_related = related_skills or []
        
        sig = inspect.signature(instance.execute)
        parameters = []
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            param_type = param.annotation if param.annotation != inspect.Parameter.empty else str
            required = param.default == inspect.Parameter.empty
            default_val = None if required else param.default
            
            parameters.append(SkillParameter(
                name=param_name,
                type=param_type,
                description=f"Parameter {param_name}",
                required=required,
                default=default_val
            ))
        instance._skill_parameters = parameters
        
        skill_manager.register_skill(instance)
        return cls
    return decorator


# 注意: Greeting/Farewell/Help 等简单对话技能已移除
# 这些功能由 LLM 直接处理，不再需要硬编码
# 如需创建领域特定技能，请使用 @skill 装饰器或 SKILL.md 格式


class ToolWrapperSkill(BaseSkill):
    """Wrapper to convert a tool function into a skill."""
    
    def __init__(self, tool_func, name: str, description: str, parameters: list, category: str = "tools"):
        self._tool_func = tool_func
        self._tool_name = name
        self._description = description
        self._parameters = parameters
        self._category = category
    
    def get_metadata(self) -> SkillMetadata:
        aliases = []
        
        if self._tool_name in ("terminal", "execute_terminal"):
            aliases = ["terminal", "run_terminal", "execute_terminal"]
        
        params = []
        for p in self._parameters:
            params.append(SkillParameter(
                name=p["name"],
                type=str,
                description=p.get("description", ""),
                required=p.get("required", False)
            ))
        
        return SkillMetadata(
            id=f"tool_{self._tool_name}",
            name=f"Tool: {self._tool_name}",
            description=self._description,
            category=self._category,
            parameters=params,
            aliases=aliases,
            source="system"
        )
    
    async def execute(self, **kwargs) -> SkillResult:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: self._tool_func(**kwargs))
            
            if isinstance(result, dict):
                return SkillResult(
                    success=result.get("success", True),
                    output=result.get("output", str(result)),
                    error=result.get("error")
                )
            
            from tools import ToolResult
            if isinstance(result, ToolResult):
                return SkillResult(
                    success=result.success,
                    output=result.output,
                    error=result.error
                )
            
            return SkillResult(success=True, output=str(result))
        except Exception as e:
            return SkillResult(success=False, output="", error=str(e))


def register_tools_as_skills():
    """Register all tools from tools module as skills."""
    try:
        from tools import tool_registry
        
        # Check if list_tools exists, otherwise use available methods
        if hasattr(tool_registry, 'list_tools'):
            list_method = tool_registry.list_tools
        elif hasattr(tool_registry, 'list_toolsets'):
            # Wrap list_toolsets for compatibility
            list_method = lambda: [{"name": ts} for ts in tool_registry.list_toolsets()]
        else:
            list_method = lambda: []
        
        for tool_info in list_method():
            tool_name = tool_info["name"]
            tool = tool_registry.get(tool_name)
            
            if tool and callable(tool.get("func")):
                skill = ToolWrapperSkill(
                    tool_func=tool["func"],
                    name=tool_name,
                    description=tool.get("description", ""),
                    parameters=tool.get("parameters", []),
                    category="tool"
                )
                skill_manager.register_skill(skill)
                
    except (ImportError, AttributeError):
        pass


def load_skills_from_directory_structure():
    """自动从标准技能目录结构加载技能"""
    skill_manager.import_skill_from_directory_structure()


def init_skills():
    """显式初始化技能系统（在应用入口调用一次）"""
    register_tools_as_skills()
    load_skills_from_directory_structure()
