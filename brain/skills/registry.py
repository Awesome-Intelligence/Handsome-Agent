"""
技能注册表
管理所有可用技能
"""

from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from .matcher import SkillDefinition


@dataclass
class SkillsRegistry:
    """技能注册表"""
    _skills: Dict[str, SkillDefinition] = field(default_factory=dict)
    _executors: Dict[str, Callable] = field(default_factory=dict)
    
    def register(self, skill: SkillDefinition) -> None:
        """注册技能"""
        self._skills[skill.skill_id] = skill
    
    def register_executor(self, skill_id: str, executor: Callable) -> None:
        """注册技能执行器"""
        self._executors[skill_id] = executor
    
    def get(self, skill_id: str) -> Optional[SkillDefinition]:
        """获取技能"""
        return self._skills.get(skill_id)
    
    def list_all(self) -> List[SkillDefinition]:
        """列出所有技能"""
        return list(self._skills.values())
    
    def unregister(self, skill_id: str) -> bool:
        """取消注册"""
        if skill_id in self._skills:
            del self._skills[skill_id]
            if skill_id in self._executors:
                del self._executors[skill_id]
            return True
        return False
    
    def clear(self) -> None:
        """清空注册表"""
        self._skills.clear()
        self._executors.clear()