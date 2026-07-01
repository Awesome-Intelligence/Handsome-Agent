#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill Recommender - 简化的技能推荐系统

功能：
1. 基于关键词匹配的推荐 - 根据用户描述匹配技能
2. 基于使用频率的推荐 - 推荐使用最多的技能
3. 基于历史上下文的推荐 - 根据当前会话历史推荐相关技能

🚪 Access - 📋 Skills - Recommendations
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from common.logging_manager import get_decision_logger

logger = get_decision_logger("SkillRecommender")

# 停用词列表
STOP_WORDS = frozenset({
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个",
    "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好",
    "自己", "这", "那", "里", "为", "什么", "可以", "这个", "那个", "吗", "呢",
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "shall", "can", "need", "dare",
    "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
    "into", "through", "during", "before", "after", "above", "below",
})


@dataclass
class SkillInfo:
    """技能信息"""
    skill_id: str
    name: str
    description: str
    tags: List[str] = field(default_factory=list)
    category: str = ""
    usage_count: int = 0
    last_used_at: Optional[str] = None
    state: str = "active"


@dataclass
class RecommendationScore:
    """推荐评分结果"""
    skill: SkillInfo
    total_score: float
    matched_keywords: List[str] = field(default_factory=list)


@dataclass
class RecommenderConfig:
    """推荐系统配置"""
    max_results: int = 5
    frequency_weight: float = 0.3
    similarity_weight: float = 0.5
    history_weight: float = 0.2


class SkillRecommender:
    """
    简化版技能推荐系统

    使用简单的关键词匹配和频率统计进行推荐。
    """

    def __init__(
        self,
        config: Optional[RecommenderConfig] = None,
    ):
        self.config = config or RecommenderConfig()
        self._skills: Dict[str, SkillInfo] = {}
        self._max_frequency: int = 0

    def _tokenize(self, text: str) -> List[str]:
        """分词"""
        if not text:
            return []
        text = text.lower()
        words = re.findall(r'[\w\u4e00-\u9fff]+', text)
        return [w for w in words if w not in STOP_WORDS and len(w) > 1]

    def add_skill(self, skill: SkillInfo) -> None:
        """添加技能"""
        self._skills[skill.skill_id] = skill
        if skill.usage_count > self._max_frequency:
            self._max_frequency = skill.usage_count

    def add_skills(self, skills: List[SkillInfo]) -> None:
        """批量添加技能"""
        for skill in skills:
            self.add_skill(skill)

    def clear_skills(self) -> None:
        """清除所有技能"""
        self._skills.clear()
        self._max_frequency = 0

    def _calculate_keyword_match(
        self,
        query_terms: set[str],
        skill: SkillInfo,
    ) -> tuple[float, list[str]]:
        """计算关键词匹配分数"""
        if not query_terms:
            return 0.0, []

        # 收集技能的所有文本
        skill_texts = [skill.name, skill.description]
        skill_texts.extend(skill.tags)

        skill_terms: set[str] = set()
        for text in skill_texts:
            skill_terms.update(self._tokenize(text))

        matched = query_terms & skill_terms
        if not matched:
            return 0.0, []

        # 简单评分：匹配词数 / 查询词数
        score = len(matched) / len(query_terms)
        return score, list(matched)

    def _calculate_frequency_score(self, skill: SkillInfo) -> float:
        """计算频率评分"""
        if self._max_frequency == 0:
            return 0.0
        return skill.usage_count / self._max_frequency

    def recommend_by_description(
        self,
        description: str,
        top_n: Optional[int] = None,
    ) -> List[RecommendationScore]:
        """基于描述推荐技能"""
        if top_n is None:
            top_n = self.config.max_results

        if not description or not self._skills:
            return []

        query_terms = set(self._tokenize(description))
        results: List[RecommendationScore] = []

        for skill in self._skills.values():
            if skill.state != "active":
                continue

            similarity, matched = self._calculate_keyword_match(query_terms, skill)
            if similarity <= 0:
                continue

            frequency = self._calculate_frequency_score(skill)
            total = (
                frequency * self.config.frequency_weight +
                similarity * self.config.similarity_weight
            )

            results.append(RecommendationScore(
                skill=skill,
                total_score=total,
                matched_keywords=matched,
            ))

        results.sort(key=lambda x: -x.total_score)
        return results[:top_n]

    def recommend_by_history(
        self,
        history_skill_ids: List[str],
        top_n: Optional[int] = None,
    ) -> List[RecommendationScore]:
        """基于历史使用的技能推荐"""
        if top_n is None:
            top_n = self.config.max_results

        if not history_skill_ids or not self._skills:
            return []

        history_set = set(history_skill_ids)
        results: List[RecommendationScore] = []

        for skill in self._skills.values():
            if skill.state != "active":
                continue

            # 直接匹配
            if skill.skill_id in history_set:
                history_score = 1.0
            else:
                # 名称相似度
                history_score = 0.0
                for hist_id in history_set:
                    if hist_id.lower() in skill.name.lower() or skill.name.lower() in hist_id.lower():
                        history_score = 0.7
                        break

            if history_score == 0:
                continue

            frequency = self._calculate_frequency_score(skill)
            total = (
                frequency * self.config.frequency_weight +
                history_score * self.config.history_weight
            )

            results.append(RecommendationScore(
                skill=skill,
                total_score=total,
                matched_keywords=[],
            ))

        results.sort(key=lambda x: -x.total_score)
        return results[:top_n]

    def recommend(
        self,
        description: str = "",
        history_skill_ids: Optional[List[str]] = None,
        top_n: Optional[int] = None,
    ) -> List[RecommendationScore]:
        """综合推荐"""
        if top_n is None:
            top_n = self.config.max_results

        if not description and not history_skill_ids:
            return self.recommend_top_frequent(top_n)

        results: Dict[str, RecommendationScore] = {}

        if description:
            desc_results = self.recommend_by_description(description, top_n=top_n)
            for result in desc_results:
                results[result.skill.skill_id] = result

        if history_skill_ids:
            history_results = self.recommend_by_history(history_skill_ids, top_n=top_n)
            for result in history_results:
                if result.skill.skill_id in results:
                    existing = results[result.skill.skill_id]
                    existing.total_score += result.total_score * 0.5
                else:
                    results[result.skill.skill_id] = result

        sorted_results = sorted(results.values(), key=lambda x: -x.total_score)
        return sorted_results[:top_n]

    def recommend_top_frequent(self, top_n: Optional[int] = None) -> List[RecommendationScore]:
        """推荐使用频率最高的技能"""
        if top_n is None:
            top_n = self.config.max_results

        results: List[RecommendationScore] = []
        for skill in self._skills.values():
            if skill.state != "active":
                continue
            frequency = self._calculate_frequency_score(skill)
            if frequency > 0:
                results.append(RecommendationScore(
                    skill=skill,
                    total_score=frequency,
                    matched_keywords=[],
                ))

        results.sort(key=lambda x: -x.total_score)
        return results[:top_n]

    def get_skill_by_id(self, skill_id: str) -> Optional[SkillInfo]:
        """根据 ID 获取技能"""
        return self._skills.get(skill_id)

    def get_all_skills(self) -> List[SkillInfo]:
        """获取所有技能"""
        return list(self._skills.values())


# 全局实例
_global_recommender: Optional[SkillRecommender] = None


def get_skill_recommender() -> SkillRecommender:
    """获取全局 SkillRecommender 实例"""
    global _global_recommender
    if _global_recommender is None:
        _global_recommender = SkillRecommender()
    return _global_recommender


def create_recommender_from_skills(
    skills_data: List[Dict[str, Any]],
) -> SkillRecommender:
    """从技能数据创建推荐器"""
    recommender = SkillRecommender()

    for data in skills_data:
        skill = SkillInfo(
            skill_id=data.get("skill_id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            category=data.get("category", ""),
            usage_count=data.get("usage_count", 0),
            last_used_at=data.get("last_used_at"),
            state=data.get("state", "active"),
        )
        recommender.add_skill(skill)

    return recommender


__all__ = [
    "SkillRecommender",
    "SkillInfo",
    "RecommendationScore",
    "RecommenderConfig",
    "get_skill_recommender",
    "create_recommender_from_skills",
]
