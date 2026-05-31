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
from typing import Dict, List, Optional, Any, Callable, Union, Type
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging
from collections import defaultdict

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from .logging_manager import get_decision_logger, get_execution_logger


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
    usage_count: int = 0
    last_used: Optional[str] = None
    version: str = "1.0.0"
    author: str = ""
    license: str = "MIT"
    platforms: List[str] = field(default_factory=lambda: ["linux", "macos", "windows"])
    tags: List[str] = field(default_factory=list)
    related_skills: List[str] = field(default_factory=list)


@dataclass
class SkillResult:
    """Result of skill execution."""
    success: bool
    output: str
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SkillRecommendation:
    """推荐的技能及其匹配信息"""
    skill_id: str
    name: str
    description: str
    confidence: float
    matched_by: str
    required_params: Dict[str, str]
    suggested_params: Dict[str, Any]


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
    
    Supports Hermes-style progressive skill discovery:
    - Context-aware matching
    - History-based recommendations
    - Automatic parameter inference
    - Multi-turn skill invocation
    - Tag-based discovery
    - Related skills recommendation
    """
    
    def __init__(self, explanation_depth: str = "detailed"):
        self.skills: Dict[str, BaseSkill] = {}
        self.categories: Dict[str, List[str]] = {}
        self.tags: Dict[str, List[str]] = {}  # tag -> skill_ids
        self.skill_paths: Dict[str, str] = {}  # skill_id -> directory path
        self._explanation_depth = explanation_depth
        self._decision_logger = get_decision_logger("SkillManager")
        self._execution_logger = get_execution_logger("SkillManager")
        self._detailed_logger = get_execution_logger("SkillManager")
        
        # 渐进式发现相关
        self._skill_usage_history: List[Dict[str, Any]] = []
        self._context_keywords: Dict[str, int] = defaultdict(int)
        self._intent_history: List[str] = []
        self._skill_co_occurrence: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    
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
        
        self._decision_logger.info(f"Registered skill: {metadata.id} ({metadata.name})")
    
    def unregister_skill(self, skill_id: str):
        """Unregister a skill."""
        if skill_id in self.skills:
            metadata = self.skills[skill_id].get_metadata()
            
            if metadata.category in self.categories:
                if skill_id in self.categories[metadata.category]:
                    self.categories[metadata.category].remove(skill_id)
            
            for tag in metadata.tags:
                if tag in self.tags and skill_id in self.tags[tag]:
                    self.tags[tag].remove(skill_id)
            
            for alias in metadata.aliases:
                if alias in self.skills:
                    del self.skills[alias]
            
            del self.skills[skill_id]
            self._decision_logger.info(f"Unregistered skill: {skill_id}")
    
    def get_skill(self, skill_id: str) -> Optional[BaseSkill]:
        """Get a skill by ID."""
        return self.skills.get(skill_id)
    
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
    
    # ============ 渐进式技能发现 (Hermes Style) ============
    
    def _update_context(self, query: str, intent: str = ""):
        """更新上下文信息"""
        self._intent_history.append(intent)
        if len(self._intent_history) > 20:
            self._intent_history = self._intent_history[-20:]
        
        keywords = query.lower().split()
        for keyword in keywords:
            if len(keyword) >= 2:
                self._context_keywords[keyword] += 1
    
    def _calculate_context_similarity(self, skill: BaseSkill, query: str) -> float:
        """计算技能与当前上下文的相似度（Hermes 风格）"""
        metadata = skill.get_metadata()
        score = 0.0
        query_lower = query.lower()
        
        # 描述匹配
        if query_lower in metadata.description.lower():
            score += 0.2
        
        # 名称匹配
        if query_lower in metadata.name.lower():
            score += 0.15
        
        # 示例匹配
        for example in metadata.examples:
            if example.lower() in query_lower:
                score += 0.2
                break
        
        # 别名匹配
        for alias in metadata.aliases:
            if alias.lower() in query_lower:
                score += 0.2
                break
        
        # 标签匹配
        for tag in metadata.tags:
            if tag.lower() in query_lower:
                score += 0.1
                break
        
        # 历史上下文匹配（关键词频率）
        for keyword, freq in self._context_keywords.items():
            if keyword in metadata.description.lower() or keyword in metadata.name.lower():
                score += 0.05 * min(freq / 5, 1)
        
        # 意图历史匹配
        for past_intent in self._intent_history[-5:]:
            if past_intent and (past_intent.lower() in metadata.description.lower() or 
                               past_intent.lower() in metadata.name.lower()):
                score += 0.05
                break
        
        return min(score, 1.0)
    
    async def discover_skills(self, intent: str, query: str = "", 
                             context: Optional[List[Dict[str, Any]]] = None,
                             tags: Optional[List[str]] = None) -> List[SkillRecommendation]:
        """
        渐进式发现相关技能（Hermes 风格）
        
        Args:
            intent: 用户意图
            query: 用户查询
            context: 对话历史上下文
            tags: 标签过滤
        
        Returns:
            按置信度排序的技能推荐列表
        """
        self._update_context(query, intent)
        
        recommendations = []
        query_lower = query.lower()
        
        decision = self._decision_logger
        if self._explanation_depth == 'detailed':
            decision.info(f"🧠 [决策层] 渐进式技能发现:")
            decision.info(f"  ├─ 意图: {intent}")
            decision.info(f"  ├─ 查询: {query[:50]}...")
            decision.info(f"  └─ 总技能数: {len(self.skills)}")
        
        processed_skills = set()
        
        for skill_id, skill in self.skills.items():
            metadata = skill.get_metadata()
            
            if metadata.id in processed_skills:
                continue
            processed_skills.add(metadata.id)
            
            if tags:
                skill_tags = set(metadata.tags)
                if not skill_tags.intersection(tags):
                    continue
            
            confidence = self._calculate_context_similarity(skill, query)
            
            if confidence < 0.05:
                continue
            
            matched_by = "context"
            if intent in metadata.description.lower():
                matched_by = "intent"
            elif any(alias.lower() in query_lower for alias in metadata.aliases):
                matched_by = "alias"
            elif any(example.lower() in query_lower for example in metadata.examples):
                matched_by = "example"
            elif any(tag.lower() in query_lower for tag in metadata.tags):
                matched_by = "tag"
            
            missing_params = skill.get_missing_parameters()
            required_params = {}
            for param_name in missing_params:
                param = next((p for p in metadata.parameters if p.name == param_name), None)
                if param:
                    required_params[param_name] = param.prompt or param.description
            
            suggested_params = self._infer_parameters(skill, query, context)
            
            recommendations.append(SkillRecommendation(
                skill_id=metadata.id,
                name=metadata.name,
                description=metadata.description,
                confidence=confidence,
                matched_by=matched_by,
                required_params=required_params,
                suggested_params=suggested_params
            ))
        
        recommendations.sort(key=lambda x: x.confidence, reverse=True)
        
        if self._explanation_depth == 'detailed':
            decision.info(f"  └─ 发现 {len(recommendations)} 个相关技能")
        else:
            decision.summary(f"🧠 [决策层] 发现 {len(recommendations)} 个相关技能")
        
        return recommendations
    
    def _infer_parameters(self, skill: BaseSkill, query: str, 
                          context: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """从查询和上下文中推断参数值（Hermes 风格）"""
        metadata = skill.get_metadata()
        inferred = {}
        
        for param in metadata.parameters:
            if param.name.lower() in query.lower():
                words = query.lower().split()
                try:
                    idx = words.index(param.name.lower())
                    if idx + 1 < len(words):
                        inferred[param.name] = words[idx + 1]
                except ValueError:
                    pass
            
            if context and param.name not in inferred:
                for msg in reversed(context[-5:]):
                    if param.name.lower() in msg.get('content', '').lower():
                        words = msg['content'].lower().split()
                        try:
                            idx = words.index(param.name.lower())
                            if idx + 1 < len(words):
                                inferred[param.name] = words[idx + 1]
                                break
                        except ValueError:
                            pass
        
        return inferred
    
    async def recommend_and_execute(self, intent: str, query: str, 
                                   context: Optional[List[Dict[str, Any]]] = None,
                                   auto_confirm: bool = False) -> SkillResult:
        """渐进式技能推荐与执行（Hermes 风格）"""
        recommendations = await self.discover_skills(intent, query, context)
        
        if not recommendations:
            return SkillResult(
                success=False,
                output="",
                error="未找到匹配的技能"
            )
        
        best_match = recommendations[0]
        
        if best_match.confidence < 0.25:
            return SkillResult(
                success=False,
                output=f"不确定你想要做什么。你是想{best_match.description}吗？",
                error="低置信度匹配"
            )
        
        decision = self._decision_logger
        decision.summary(f"🧠 [决策层] 选择技能: {best_match.name} (置信度: {best_match.confidence:.2f})")
        
        skill = self.get_skill(best_match.skill_id)
        if not skill:
            return SkillResult(
                success=False,
                output="",
                error=f"技能不存在: {best_match.skill_id}"
            )
        
        params = best_match.suggested_params.copy()
        
        if best_match.required_params:
            if self._explanation_depth == 'detailed':
                decision.info(f"  └─ 需要额外参数: {list(best_match.required_params.keys())}")
            
            if not auto_confirm:
                param_hints = "\n".join([
                    f"- {name}: {desc}" 
                    for name, desc in best_match.required_params.items()
                ])
                return SkillResult(
                    success=False,
                    output=f"需要一些信息来执行此操作:\n{param_hints}",
                    error="缺少参数",
                    metadata={
                        'skill_id': best_match.skill_id,
                        'missing_params': best_match.required_params
                    }
                )
        
        return await self.execute_skill(best_match.skill_id, **params)
    
    def record_usage(self, skill_id: str, success: bool):
        """记录技能使用情况（用于渐进式学习）"""
        skill = self.get_skill(skill_id)
        if skill:
            metadata = skill.get_metadata()
            metadata.usage_count += 1
            metadata.last_used = str(asyncio.get_event_loop().time())
            
            self._skill_usage_history.append({
                'skill_id': skill_id,
                'success': success,
                'timestamp': metadata.last_used
            })
            
            if len(self._skill_usage_history) > 100:
                self._skill_usage_history = self._skill_usage_history[-100:]
    
    def record_co_occurrence(self, skill_id1: str, skill_id2: str):
        """记录技能共现关系"""
        self._skill_co_occurrence[skill_id1][skill_id2] += 1
        self._skill_co_occurrence[skill_id2][skill_id1] += 1
    
    # ============ 技能执行方法 ============
    
    async def execute_skill(self, skill_id: str, **kwargs) -> SkillResult:
        """Execute a skill by ID."""
        decision = self._decision_logger
        execution = self._execution_logger
        
        if self._explanation_depth == 'detailed':
            execution.debug(f"execute_skill() 尝试执行技能: {skill_id}")
        
        skill = self.get_skill(skill_id)
        
        if not skill:
            execution.warning(f"技能未找到: {skill_id}")
            return SkillResult(
                success=False,
                output="",
                error=f"Skill not found: {skill_id}"
            )
        
        metadata = skill.get_metadata()
        skill_class = metadata.name
        
        if not skill.validate_parameters(**kwargs):
            required_params = [p.name for p in metadata.parameters if p.required]
            execution.warning(f"{skill_class}.validate_parameters() 失败，缺少必需参数: {', '.join(required_params)}")
            return SkillResult(
                success=False,
                output="",
                error=f"Missing required parameters: {', '.join(required_params)}"
            )
        
        if self._explanation_depth == 'detailed':
            execution.debug(f"{skill_class}.validate_parameters() 验证通过")
            execution.debug(f"{skill_class}.execute() 开始执行...")
        
        try:
            result = await skill.execute(**kwargs)
            
            self.record_usage(skill_id, result.success)
            
            if result.success:
                if self._explanation_depth == 'detailed':
                    execution.debug(f"{skill_class}.execute() 执行成功")
                decision.summary(f"✅ 技能 {skill_class} 执行成功")
            else:
                decision.warning(f"{skill_class}.execute() 执行失败: {result.error}")
            
            return result
            
        except Exception as e:
            self.record_usage(skill_id, False)
            decision.error(f"{skill_class}.execute() 执行异常: {str(e)}")
            return SkillResult(
                success=False,
                output="",
                error=f"Error executing skill: {str(e)}"
            )
    
    # ============ 技能导入功能 ============
    
    def import_skill_from_directory_structure(self, skills_dir: str = "skills") -> int:
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
            skills_dir: 技能目录路径，默认为 'skills'
        
        Returns:
            成功导入的技能数量
        """
        if not os.path.isdir(skills_dir):
            self._decision_logger.error(f"技能目录不存在: {skills_dir}")
            return 0
        
        imported_count = 0
        
        for category_dir in os.listdir(skills_dir):
            category_path = os.path.join(skills_dir, category_dir)
            
            if not os.path.isdir(category_path):
                continue
            
            for skill_dir in os.listdir(category_path):
                skill_path = os.path.join(category_path, skill_dir)
                
                if not os.path.isdir(skill_path):
                    continue
                
                # 优先从 skill.py 文件导入（Python 实现）
                skill_py = os.path.join(skill_path, "skill.py")
                if os.path.isfile(skill_py):
                    try:
                        dir_name = os.path.dirname(skill_py)
                        file_name = os.path.basename(skill_py)
                        module_name = file_name[:-3]
                        
                        if dir_name not in sys.path:
                            sys.path.insert(0, dir_name)
                        
                        module = importlib.import_module(module_name)
                        
                        for name in dir(module):
                            obj = getattr(module, name)
                            if isinstance(obj, BaseSkill):
                                obj.get_metadata().source = "user"
                                obj.get_metadata().category = category_dir
                                self.register_skill(obj)
                                self.skill_paths[obj.get_metadata().id] = skill_path
                                imported_count += 1
                                self._decision_logger.info(f"从 skill.py 导入技能: {obj.get_metadata().id}")
                        
                        if dir_name in sys.path:
                            sys.path.remove(dir_name)
                        
                        continue
                    except Exception as e:
                        self._decision_logger.error(f"从 skill.py 导入技能失败 {skill_dir}: {str(e)}")
                
                # 否则从 SKILL.md 文件创建（Hermes 风格）
                skill_md = os.path.join(skill_path, "SKILL.md")
                if not os.path.isfile(skill_md):
                    skill_md = os.path.join(skill_path, "skill.md")
                
                if not os.path.isfile(skill_md):
                    self._decision_logger.warning(f"跳过非标准技能目录（缺少 SKILL.md 和 skill.py）: {skill_dir}")
                    continue
                
                try:
                    skill = self._create_skill_from_hermes_md(skill_md)
                    if skill:
                        skill.get_metadata().source = "user"
                        skill.get_metadata().category = category_dir
                        self.register_skill(skill)
                        self.skill_paths[skill.get_metadata().id] = skill_path
                        imported_count += 1
                        self._decision_logger.info(f"从 Hermes 风格目录导入技能: {skill.get_metadata().id}")
                
                except Exception as e:
                    self._decision_logger.error(f"从目录导入技能失败 {skill_dir}: {str(e)}")
        
        self._decision_logger.info(f"从标准目录结构成功导入 {imported_count} 个技能")
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
            
            # 解析 YAML frontmatter
            match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
            if not match:
                self._decision_logger.warning(f"SKILL.md 缺少 YAML frontmatter: {md_path}")
                return None
            
            yaml_content = match.group(1)
            if YAML_AVAILABLE:
                frontmatter = yaml.safe_load(yaml_content)
            else:
                frontmatter = self._parse_yaml_fallback(yaml_content)
            
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
    
    def _parse_yaml_fallback(self, yaml_content: str) -> dict:
        """简单的 YAML 解析回退（当 PyYAML 不可用时）"""
        result = {}
        lines = yaml_content.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line or line.startswith('#'):
                i += 1
                continue
            
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                # 处理列表
                if value.startswith('['):
                    # 单行列表
                    if value.endswith(']'):
                        items = value[1:-1].split(',')
                        result[key] = [item.strip().strip('"').strip("'") for item in items if item.strip()]
                    else:
                        # 多行列表
                        items = []
                        i += 1
                        while i < len(lines):
                            list_line = lines[i].strip()
                            if list_line.endswith(']'):
                                if '-' in list_line:
                                    items.append(list_line.replace('-', '').replace(']', '').strip())
                                break
                            if '-' in list_line:
                                items.append(list_line.replace('-', '').strip())
                            i += 1
                        result[key] = items
                else:
                    # 简单值
                    result[key] = value.strip('"').strip("'")
            
            i += 1
        
        return result
    
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
        if not YAML_AVAILABLE:
            self._decision_logger.error("PyYAML 未安装，请先安装: pip install pyyaml")
            return 0
        
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


@skill(
    id='greeting',
    name='Greeting',
    description='Handle greetings and introductions',
    category='conversation',
    examples=['Hello', 'Hi there', '你好'],
    tags=['conversation', 'hello', 'greeting']
)
class GreetingSkill(BaseSkill):
    """Skill for handling greetings."""
    
    def get_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id=self._skill_id,
            name=self._skill_name,
            description=self._skill_description,
            category=self._skill_category,
            parameters=self._skill_parameters,
            requires_llm=self._skill_requires_llm,
            requires_permission=self._skill_requires_permission,
            aliases=self._skill_aliases,
            examples=self._skill_examples,
            version=self._skill_version,
            tags=self._skill_tags,
            source="system"
        )
    
    async def execute(self, message: str = "") -> SkillResult:
        """
        Execute greeting skill.
        
        DEPRECATED: 应该使用 LLM 来判断意图和生成响应
        """
        # 简化：直接返回友好响应
        # 不再使用硬编码关键词判断
        return SkillResult(
            success=True,
            output="你好！我是你的智能助手。有什么我可以帮助你的吗？"
        )


@skill(
    id='farewell',
    name='Farewell',
    description='Handle farewells and goodbyes',
    category='conversation',
    examples=['Goodbye', 'See you later', '再见'],
    tags=['conversation', 'goodbye', 'farewell']
)
class FarewellSkill(BaseSkill):
    """Skill for handling farewells."""
    
    def get_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id=self._skill_id,
            name=self._skill_name,
            description=self._skill_description,
            category=self._skill_category,
            parameters=self._skill_parameters,
            requires_llm=self._skill_requires_llm,
            requires_permission=self._skill_requires_permission,
            aliases=self._skill_aliases,
            examples=self._skill_examples,
            version=self._skill_version,
            tags=self._skill_tags,
            source="system"
        )
    
    async def execute(self) -> SkillResult:
        return SkillResult(
            success=True,
            output="再见！祝你有美好的一天！"
        )


@skill(
    id='help',
    name='Help',
    description='Show available commands and skills',
    category='system',
    examples=['Help', 'What can you do?', 'Show commands'],
    tags=['help', 'system', 'commands']
)
class HelpSkill(BaseSkill):
    """Skill for showing help information."""
    
    def get_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            id=self._skill_id,
            name=self._skill_name,
            description=self._skill_description,
            category=self._skill_category,
            parameters=self._skill_parameters,
            requires_llm=self._skill_requires_llm,
            requires_permission=self._skill_requires_permission,
            aliases=self._skill_aliases,
            examples=self._skill_examples,
            version=self._skill_version,
            tags=self._skill_tags,
            source="system"
        )
    
    async def execute(self) -> SkillResult:
        categories = skill_manager.get_categories()
        output = "我可以帮助你完成以下任务：\n\n"
        
        for category in categories:
            skills = skill_manager.list_skills(category)
            if skills:
                output += f"**{category.capitalize()}:**\n"
                for skill_meta in skills:
                    source_tag = ""
                    if skill_meta.source == "user":
                        source_tag = " 📥"
                    elif skill_meta.source == "external":
                        source_tag = " 🌐"
                    usage_tag = f" (使用 {skill_meta.usage_count} 次)" if skill_meta.usage_count > 0 else ""
                    version_tag = f" v{skill_meta.version}" if skill_meta.version else ""
                    tag_str = f" [{', '.join(skill_meta.tags[:3])}]" if skill_meta.tags else ""
                    output += f"- {skill_meta.name}{source_tag}{version_tag}{usage_tag}{tag_str}: {skill_meta.description}\n"
                output += "\n"
        
        output += "你可以直接向我提问，我会自动发现并调用合适的技能。"
        
        return SkillResult(
            success=True,
            output=output
        )


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
        
        if self._tool_name == "terminal":
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
        
        for tool_info in tool_registry.list_tools():
            tool_name = tool_info["name"]
            tool = tool_registry.get(tool_name)
            
            if tool and callable(tool["func"]):
                skill = ToolWrapperSkill(
                    tool_func=tool["func"],
                    name=tool_name,
                    description=tool["description"],
                    parameters=tool["parameters"],
                    category="tool"
                )
                skill_manager.register_skill(skill)
                
    except ImportError:
        pass


def load_skills_from_directory_structure():
    """自动从标准技能目录结构加载技能"""
    skill_manager.import_skill_from_directory_structure()


register_tools_as_skills()
load_skills_from_directory_structure()
