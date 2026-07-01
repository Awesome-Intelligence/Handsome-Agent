#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Context Halver - 智能上下文压缩

基于技能相关性智能管理对话上下文，减少 token 消耗同时保留重要信息。

核心功能：
1. 技能相关性评分 - 基于关键词和技能描述计算消息与技能的相关度
2. 上下文压缩 - 优先保留高相关性消息，压缩/删除低相关性消息
3. 智能保留策略 - 系统消息、最近消息、高评分消息始终保留

🚪 Access - 📋 Skills - Context
"""

from __future__ import annotations

import re
import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from common.logging_manager import get_decision_logger

logger = get_decision_logger("ContextHalver")

# 停用词列表（常见无意义词）
STOP_WORDS = frozenset({
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个",
    "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好",
    "自己", "这", "那", "里", "为", "什么", "可以", "这个", "那个", "吗", "呢",
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "shall", "can", "need", "dare",
    "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
    "into", "through", "during", "before", "after", "above", "below",
    "between", "under", "again", "further", "then", "once", "here",
    "there", "when", "where", "why", "how", "all", "each", "few",
    "more", "most", "other", "some", "such", "no", "nor", "not",
    "only", "own", "same", "so", "than", "too", "very", "just",
})


@dataclass
class SkillContext:
    """技能上下文信息"""
    skill_id: str
    name: str
    description: str
    keywords: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class MessageScore:
    """消息评分结果"""
    message: Dict[str, Any]
    score: float
    reason: str
    index: int


@dataclass
class HalverConfig:
    """上下文半减法配置"""
    max_context_ratio: float = 0.5  # 最大保留上下文比例
    min_context_messages: int = 10  # 最小保留消息数
    skill_relevance_threshold: float = 0.3  # 技能相关性阈值
    recent_messages_preserve: int = 5  # 始终保留的最近消息数
    system_message_preserve: bool = True  # 始终保留系统消息
    compress_instead_of_delete: bool = True  # 压缩而非删除


class ContextHalver:
    """
    上下文半减法器

    基于技能相关性智能压缩对话上下文，保留高价值信息同时减少 token 消耗。

    使用方式：
    ```python
    halver = ContextHalver(config=HalverConfig(
        max_context_ratio=0.5,
        min_context_messages=10,
    ))
    halver.add_skill(SkillContext(
        skill_id="code-review",
        name="Code Review",
        description="Review code for bugs and improvements",
        keywords=["bug", "fix", "review"],
    ))
    compressed = halver.halve(messages, target_ratio=0.5)
    ```
    """

    def __init__(
        self,
        config: Optional[HalverConfig] = None,
        skills: Optional[List[SkillContext]] = None,
    ):
        self.config = config or HalverConfig()
        self._skills: List[SkillContext] = skills or []
        self._skill_keywords: Dict[str, Set[str]] = {}
        self._document_frequencies: Dict[str, int] = defaultdict(int)
        self._total_documents: int = 0
        self._rebuild_keyword_index()

    def _rebuild_keyword_index(self) -> None:
        """重建技能关键词索引"""
        self._skill_keywords.clear()
        self._document_frequencies.clear()
        self._total_documents = len(self._skills)

        for skill in self._skills:
            keywords = self._extract_keywords(skill)
            self._skill_keywords[skill.skill_id] = keywords

            # 更新文档频率
            for kw in keywords:
                self._document_frequencies[kw] += 1

    def _extract_keywords(self, skill: SkillContext) -> Set[str]:
        """从技能信息中提取关键词"""
        keywords: Set[str] = set()

        # 从名称提取
        for word in self._tokenize(skill.name):
            if word and word not in STOP_WORDS:
                keywords.add(word)

        # 从描述提取
        for word in self._tokenize(skill.description):
            if word and word not in STOP_WORDS:
                keywords.add(word)

        # 从标签提取
        for tag in skill.tags:
            for word in self._tokenize(tag):
                if word and word not in STOP_WORDS:
                    keywords.add(word)

        # 从预设关键词提取
        for kw in skill.keywords:
            for word in self._tokenize(kw):
                if word:
                    keywords.add(word)

        return keywords

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """分词（简单实现）"""
        if not text:
            return []
        # 转小写，提取字母数字组合
        text = text.lower()
        words = re.findall(r'[\w\u4e00-\u9fff]+', text)
        return words

    def add_skill(self, skill: SkillContext) -> None:
        """添加技能上下文"""
        self._skills.append(skill)
        self._rebuild_keyword_index()

    def add_skills(self, skills: List[SkillContext]) -> None:
        """批量添加技能"""
        self._skills.extend(skills)
        self._rebuild_keyword_index()

    def clear_skills(self) -> None:
        """清除所有技能"""
        self._skills.clear()
        self._rebuild_keyword_index()

    def _calculate_idf(self, term: str) -> float:
        """计算逆文档频率"""
        df = self._document_frequencies.get(term, 0)
        if df == 0:
            return 0.0
        return math.log(self._total_documents / df)

    def score_message(self, message: Dict[str, Any], index: int) -> MessageScore:
        """
        对单条消息进行技能相关性评分

        评分因素：
        1. 内容与技能关键词的 TF-IDF 相似度
        2. 消息角色（系统消息得高分）
        3. 消息类型（工具调用结果特殊处理）
        """
        content = message.get("content", "") or ""
        role = message.get("role", "") or ""
        msg_type = message.get("type", "") or ""

        # 系统消息始终高分
        if role == "system" or msg_type == "system":
            return MessageScore(
                message=message,
                score=1.0,
                reason="system_message",
                index=index,
            )

        # 工具调用消息中等分数
        if role == "tool" or msg_type == "tool":
            tool_name = message.get("name", "") or ""
            if tool_name:
                # 检查工具名是否与技能相关
                tool_words = set(self._tokenize(tool_name))
                skill_words = set()
                for kw_set in self._skill_keywords.values():
                    skill_words.update(kw_set)
                overlap = len(tool_words & skill_words)
                if overlap > 0:
                    return MessageScore(
                        message=message,
                        score=0.6 + min(overlap * 0.1, 0.3),
                        reason=f"tool_with_skill_overlap({overlap})",
                        index=index,
                    )
            return MessageScore(
                message=message,
                score=0.4,
                reason="tool_call",
                index=index,
            )

        # 普通消息计算 TF-IDF 相似度
        content_words = set(self._tokenize(content))
        content_words -= STOP_WORDS

        if not content_words:
            return MessageScore(
                message=message,
                score=0.1,
                reason="empty_content",
                index=index,
            )

        # 计算与所有技能的相似度
        max_similarity = 0.0
        best_reason = "no_match"

        for skill_id, skill_words in self._skill_keywords.items():
            if not skill_words:
                continue

            # TF: 词在内容中出现的频率
            tf = len(content_words & skill_words) / len(content_words) if content_words else 0

            # IDF: 使用平均 IDF
            idf_values = [self._calculate_idf(w) for w in (content_words & skill_words)]
            avg_idf = sum(idf_values) / len(idf_values) if idf_values else 0

            # TF-IDF 相似度
            similarity = tf * (1 + avg_idf)

            if similarity > max_similarity:
                max_similarity = similarity
                best_reason = f"match_with_{skill_id}"

        # 归一化分数到 0-1 范围
        normalized_score = min(max_similarity * 2, 1.0)

        return MessageScore(
            message=message,
            score=normalized_score,
            reason=best_reason,
            index=index,
        )

    def score_all_messages(
        self,
        messages: List[Dict[str, Any]],
    ) -> List[MessageScore]:
        """对所有消息进行评分"""
        scores: List[MessageScore] = []

        total = len(messages)
        for i, msg in enumerate(messages):
            score = self.score_message(msg, i)

            # 最近消息加分
            if i >= total - self.config.recent_messages_preserve:
                score.score = max(score.score, 0.8)

            scores.append(score)

        return scores

    def halve(
        self,
        messages: List[Dict[str, Any]],
        target_ratio: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        执行上下文半减法

        Args:
            messages: 原始消息列表
            target_ratio: 目标保留比例（可选，使用配置默认值）

        Returns:
            压缩后的消息列表
        """
        if not messages:
            return []

        if target_ratio is None:
            target_ratio = self.config.max_context_ratio

        total = len(messages)
        target_count = max(
            self.config.min_context_messages,
            int(total * target_ratio)
        )

        # 如果消息数已经小于目标数，直接返回
        if total <= target_count:
            return messages.copy()

        # 对所有消息评分
        scores = self.score_all_messages(messages)

        # 确定必须保留的消息索引
        must_preserve: Set[int] = set()
        for score in scores:
            # 系统消息
            if self.config.system_message_preserve:
                role = score.message.get("role", "") or ""
                msg_type = score.message.get("type", "") or ""
                if role == "system" or msg_type == "system":
                    must_preserve.add(score.index)
                    continue

            # 最近消息
            if score.index >= total - self.config.recent_messages_preserve:
                must_preserve.add(score.index)
                continue

            # 高评分消息
            if score.score >= 0.7:
                must_preserve.add(score.index)

        # 如果必须保留的数量已经超过目标，保持原样
        if len(must_preserve) >= target_count:
            return [m for i, m in enumerate(messages) if i in must_preserve]

        # 按分数排序，准备删除低分消息
        deletable_scores = [s for s in scores if s.index not in must_preserve]
        deletable_scores.sort(key=lambda x: x.score)

        # 计算需要删除的数量
        preserve_count = len(must_preserve)
        delete_count = total - target_count

        # 选择最低分的消息删除
        to_delete: Set[int] = set()
        for score in deletable_scores[:delete_count]:
            to_delete.add(score.index)

        # 构建结果
        result: List[Dict[str, Any]] = []
        for i, msg in enumerate(messages):
            if i in to_delete:
                # 如果启用压缩，用占位符替换
                if self.config.compress_instead_of_delete:
                    result.append({
                        "role": "system",
                        "content": f"[{len(result)} 条低相关消息已压缩]",
                        "type": "compressed",
                        "_compressed": True,
                        "_original_indices": [idx for idx in to_delete if idx < i],
                    })
                continue
            result.append(msg)

        logger.debug(
            f"Context halving: {total} -> {len(result)} messages "
            f"(ratio: {len(result)/total:.2%}, preserved: {preserve_count}, "
            f"compressed: {len(to_delete)})"
        )

        return result

    def get_skill_relevance_report(
        self,
        messages: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        获取技能相关性报告

        用于调试和可视化技能与上下文的匹配情况。
        """
        scores = self.score_all_messages(messages)

        # 按分数分组
        high_relevance = [s for s in scores if s.score >= 0.5]
        medium_relevance = [s for s in scores if 0.3 <= s.score < 0.5]
        low_relevance = [s for s in scores if s.score < 0.3]

        return {
            "total_messages": len(messages),
            "skill_count": len(self._skills),
            "skills": [
                {
                    "skill_id": s.skill_id,
                    "name": s.name,
                    "keyword_count": len(self._skill_keywords.get(s.skill_id, set())),
                }
                for s in self._skills
            ],
            "relevance_distribution": {
                "high": len(high_relevance),
                "medium": len(medium_relevance),
                "low": len(low_relevance),
            },
            "top_scores": [
                {
                    "index": s.index,
                    "score": round(s.score, 3),
                    "reason": s.reason,
                    "content_preview": (s.message.get("content", "") or "")[:100],
                }
                for s in sorted(scores, key=lambda x: -x.score)[:5]
            ],
        }


# 全局实例
_global_halver: Optional[ContextHalver] = None


def get_context_halver() -> ContextHalver:
    """获取全局 ContextHalver 实例"""
    global _global_halver
    if _global_halver is None:
        _global_halver = ContextHalver()
    return _global_halver


__all__ = [
    "ContextHalver",
    "SkillContext",
    "MessageScore",
    "HalverConfig",
    "get_context_halver",
]
