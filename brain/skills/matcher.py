"""
技能匹配器
根据用户意图匹配合适的技能
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class SkillMatch:
    """技能匹配结果"""
    skill_id: str
    skill_name: str
    confidence: float
    description: str


class SkillsMatcher:
    """技能匹配器"""
    
    def __init__(self, registry: "SkillsRegistry"):
        self.registry = registry
    
    async def match(self, user_intent: str, context: Dict[str, Any] = None) -> List[SkillMatch]:
        """
        根据用户意图匹配技能
        
        匹配策略：
        1. 关键词匹配
        2. 语义相似度匹配（如果有 embedding）
        """
        context = context or {}
        user_intent_lower = user_intent.lower()
        
        matches = []
        all_skills = self.registry.list_all()
        
        for skill in all_skills:
            confidence = self._calculate_confidence(user_intent_lower, skill)
            if confidence > 0.3:  # 阈值
                matches.append(SkillMatch(
                    skill_id=skill.skill_id,
                    skill_name=skill.name,
                    confidence=confidence,
                    description=skill.description,
                ))
        
        # 按置信度排序
        matches.sort(key=lambda x: x.confidence, reverse=True)
        return matches[:5]  # 返回 top 5
    
    def _calculate_confidence(self, intent: str, skill: "SkillDefinition") -> float:
        """计算匹配置信度"""
        confidence = 0.0
        
        # 1. 关键词匹配
        keywords = skill.metadata.get("keywords", [])
        for keyword in keywords:
            if keyword.lower() in intent:
                confidence += 0.3
        
        # 2. 技能名称匹配
        if skill.name.lower() in intent:
            confidence += 0.4
        
        # 3. 描述匹配
        if any(word in intent for word in skill.description.lower().split()[:5]):
            confidence += 0.2
        
        return min(confidence, 1.0)


@dataclass
class SkillDefinition:
    """技能定义"""
    skill_id: str
    name: str
    description: str
    command: str
    metadata: Dict[str, Any]