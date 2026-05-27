#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill Manager Module - Inspired by Hermes Agent's skill system.

This module provides a unified framework for managing and executing skills.
Skills are self-contained units of functionality that can be dynamically loaded
and executed by the agent.
"""

import inspect
import asyncio
from typing import Dict, List, Optional, Any, Callable, Union, Type
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging

from .layer_logger import get_layer_logger


@dataclass
class SkillParameter:
    """Definition of a skill parameter."""
    name: str
    type: Type
    description: str
    required: bool = True
    default: Any = None


@dataclass
class SkillMetadata:
    """Metadata for a skill."""
    id: str
    name: str
    description: str
    category: str
    parameters: List[SkillParameter] = field(default_factory=list)
    requires_llm: bool = False
    requires_permission: bool = False
    aliases: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)


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


class SkillManager:
    """
    Manages the registration, discovery, and execution of skills.
    
    Attributes:
        skills: Dictionary of registered skills
        categories: Dictionary mapping categories to skill lists
    """
    
    def __init__(self):
        self.skills: Dict[str, BaseSkill] = {}
        self.categories: Dict[str, List[str]] = {}
        self.logger = logging.getLogger(self.__class__.__name__)
        self._decision_logger = get_layer_logger("decision", "SkillManager")
        self._execution_logger = get_layer_logger("execution", "SkillManager")
    
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
        
        self.logger.info(f"Registered skill: {metadata.id} ({metadata.name})")
    
    def unregister_skill(self, skill_id: str):
        """Unregister a skill."""
        if skill_id in self.skills:
            metadata = self.skills[skill_id].get_metadata()
            
            if metadata.category in self.categories:
                if skill_id in self.categories[metadata.category]:
                    self.categories[metadata.category].remove(skill_id)
            
            for alias in metadata.aliases:
                if alias in self.skills:
                    del self.skills[alias]
            
            del self.skills[skill_id]
            self.logger.info(f"Unregistered skill: {skill_id}")
    
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
    
    async def discover_skills(self, intent: str, query: str = "") -> List[SkillMetadata]:
        """Discover relevant skills based on intent and query."""
        relevant_skills = []
        query_lower = query.lower()
        
        decision = self._decision_logger
        decision.info(f"⚙️ [决策层] 开始技能发现:")
        decision.info(f"  ├─ 意图: {intent}")
        decision.info(f"  ├─ 查询: {query[:50]}...")
        decision.info(f"  └─ 总技能数: {len(self.skills)}")
        
        for skill_id, skill in self.skills.items():
            metadata = skill.get_metadata()
            
            if any(s.id == metadata.id for s in relevant_skills):
                continue
            
            is_relevant = False
            match_reason = ""
            
            description_lower = metadata.description.lower()
            if intent in description_lower or intent in query_lower:
                is_relevant = True
                match_reason = "意图匹配"
            
            for alias in metadata.aliases:
                alias_lower = alias.lower()
                if alias_lower in query_lower or alias_lower == intent:
                    is_relevant = True
                    match_reason = f"别名 '{alias}' 匹配"
                    break
            
            for example in metadata.examples:
                if example.lower() in query_lower:
                    is_relevant = True
                    match_reason = f"示例 '{example}' 匹配"
                    break
            
            if is_relevant:
                decision.info(f"  ✓ 发现技能: {metadata.id} - {match_reason}")
                relevant_skills.append(metadata)
        
        decision.info(f"  └─ 发现 {len(relevant_skills)} 个相关技能")
        
        return relevant_skills
    
    async def execute_skill(self, skill_id: str, **kwargs) -> SkillResult:
        """Execute a skill by ID."""
        decision = self._decision_logger
        execution = self._execution_logger
        
        execution.info(f"execute_skill() 尝试执行技能: {skill_id}")
        decision.info(f"execute_skill() 尝试执行技能: {skill_id}")
        
        skill = self.get_skill(skill_id)
        
        if not skill:
            execution.warning(f"技能未找到: {skill_id}")
            decision.warning(f"技能未找到: {skill_id}")
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
            decision.warning(f"{skill_class}.validate_parameters() 失败")
            return SkillResult(
                success=False,
                output="",
                error=f"Missing required parameters: {', '.join(required_params)}"
            )
        
        execution.info(f"{skill_class}.validate_parameters() 验证通过")
        execution.info(f"{skill_class}.execute() 开始执行...")
        
        try:
            result = await skill.execute(**kwargs)
            
            if result.success:
                execution.info(f"{skill_class}.execute() 执行成功 (输出长度: {len(result.output) if result.output else 0} 字符)")
                decision.info(f"{skill_class}.execute() 执行成功")
            else:
                execution.warning(f"{skill_class}.execute() 执行失败: {result.error}")
                decision.warning(f"{skill_class}.execute() 执行失败: {result.error}")
            
            return result
            
        except Exception as e:
            execution.error(f"{skill_class}.execute() 执行异常: {str(e)}", exc_info=True)
            decision.error(f"{skill_class}.execute() 执行异常: {str(e)}")
            return SkillResult(
                success=False,
                output="",
                error=f"Error executing skill: {str(e)}"
            )


skill_manager = SkillManager()


def skill(id: str, name: str, description: str, category: str = 'general',
          requires_llm: bool = False, requires_permission: bool = False,
          aliases: List[str] = None, examples: List[str] = None):
    """
    Decorator to register a class as a skill.
    
    Usage:
        @skill('file_reader', 'File Reader', 'Read file contents', category='files')
        class FileReaderSkill(BaseSkill):
            ...
    """
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
    examples=[
        'Hello',
        'Hi there',
        '你好'
    ]
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
            examples=self._skill_examples
        )
    
    async def execute(self, message: str = "") -> SkillResult:
        greetings = ['hello', 'hi', '你好', '嗨', 'good morning', 'good afternoon']
        message_lower = message.lower()
        
        if any(g in message_lower for g in greetings):
            return SkillResult(
                success=True,
                output="你好！我是你的智能助手。有什么我可以帮助你的吗？"
            )
        else:
            return SkillResult(
                success=True,
                output="很高兴与你交谈！"
            )


@skill(
    id='farewell',
    name='Farewell',
    description='Handle farewells and goodbyes',
    category='conversation',
    examples=[
        'Goodbye',
        'See you later',
        '再见'
    ]
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
            examples=self._skill_examples
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
    examples=[
        'Help',
        'What can you do?',
        'Show commands'
    ]
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
            examples=self._skill_examples
        )
    
    async def execute(self) -> SkillResult:
        categories = skill_manager.get_categories()
        output = "我可以帮助你完成以下任务：\n\n"
        
        for category in categories:
            skills = skill_manager.list_skills(category)
            if skills:
                output += f"**{category.capitalize()}:**\n"
                for skill_meta in skills:
                    output += f"- {skill_meta.name}: {skill_meta.description}\n"
                output += "\n"
        
        output += "你可以直接向我提问，或者使用工具来完成文件操作、终端命令等任务。"
        
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
        
        return SkillMetadata(
            id=f"tool_{self._tool_name}",
            name=f"Tool: {self._tool_name}",
            description=self._description,
            category=self._category,
            parameters=[
                SkillParameter(
                    name=p["name"],
                    type=str,
                    description=p.get("description", ""),
                    required=p.get("required", False)
                )
                for p in self._parameters
            ],
            aliases=aliases
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


register_tools_as_skills()