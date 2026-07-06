#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Semantic Retriever - 混合语义检索器

参考 Hermes plugins/memory/holographic/retrieval.py 实现

混合检索策略：
1. FTS5 全文搜索 - 获取候选结果
2. Jaccard 重排 - 基于 token 重叠
3. HRR 语义相似度 - 基于向量相似度
4. 信任加权 - 最终评分

无需外部嵌入 API，使用本地 HRR 计算。
"""

from typing import List, Dict, Any, Optional, Tuple
import re
import math
from dataclasses import dataclass, field

from .hrr import (
    encode_text,
    encode_query,
    similarity,
    _HAS_NUMPY,
    compute_similarity_normalized,
)

# 使用统一的日志管理器
from common.logging_manager import get_memory_logger

logger = get_memory_logger("SemanticRetriever")


@dataclass
class RetrievalConfig:
    """检索配置"""
    # 权重配置
    fts_weight: float = 0.3       # FTS5 权重
    jaccard_weight: float = 0.3   # Jaccard 权重
    hrr_weight: float = 0.4       # HRR 语义权重

    # HRR 配置
    hrr_dim: int = 512           # 向量维度
    hrr_min_similarity: float = 0.5  # HRR 最低相似度阈值

    # Jaccard 配置
    jaccard_min_overlap: float = 0.1  # 最低 Jaccard 分数

    # 输出配置
    max_results: int = 5         # 最大返回结果数


class SemanticRetriever:
    """
    混合语义检索器

    结合多种检索策略：
    1. FTS5 全文搜索（如果有索引）
    2. Jaccard 相似度
    3. HRR 向量语义相似度

    支持降级：无 numpy 时自动使用纯 Jaccard 方案。
    """

    def __init__(self, config: Optional[RetrievalConfig] = None):
        """
        初始化语义检索器

        Args:
            config: 检索配置
        """
        self.config = config or RetrievalConfig()
        self._setup_weights()

    def _setup_weights(self) -> None:
        """设置权重，自动降级"""
        if self.config.hrr_weight > 0 and not _HAS_NUMPY:
            logger.info("numpy not available, disabling HRR (using Jaccard only)")
            self.config.fts_weight = 0.4
            self.config.jaccard_weight = 0.6
            self.config.hrr_weight = 0.0

    def retrieve(
        self,
        query: str,
        entries: List[str],
        entities_per_entry: Optional[Dict[str, List[str]]] = None,
        min_score: Optional[float] = None,
    ) -> List[Tuple[str, float]]:
        """
        检索与查询相关的条目

        Args:
            query: 查询文本
            entries: 记忆条目列表
            entities_per_entry: 每个条目对应的实体字典（可选，用于 HRR 增强）
            min_score: 最低分数阈值（可选，默认为配置中的 jaccard_min_overlap）

        Returns:
            (条目, 分数) 列表，按分数降序排列
        """
        if not query or not entries:
            return []

        # 使用指定的 min_score 或配置的默认值
        effective_min_score = min_score if min_score is not None else self.config.jaccard_min_overlap

        query_lower = query.lower()
        query_tokens = self._tokenize(query_lower)
        query_vec = None

        # 预计算查询向量（如果启用 HRR）
        if self.config.hrr_weight > 0 and _HAS_NUMPY:
            try:
                query_vec = encode_query(query, self.config.hrr_dim)
            except Exception as e:
                logger.warning(f"HRR encoding failed: {e}, falling back to Jaccard only")
                query_vec = None

        scored_entries: List[Tuple[str, float]] = []

        for entry in entries:
            score = self._score_entry(
                entry=entry,
                query=query,
                query_tokens=query_tokens,
                query_vec=query_vec,
                entities=entities_per_entry.get(entry) if entities_per_entry else None,
                min_score=effective_min_score,
            )

            if score > 0:
                scored_entries.append((entry, score))

        # 按分数排序
        scored_entries.sort(key=lambda x: x[1], reverse=True)

        # 截取前 max_results 个
        return scored_entries[:self.config.max_results]

    def _score_entry(
        self,
        entry: str,
        query: str,
        query_tokens: set,
        query_vec,
        entities: Optional[List[str]] = None,
        min_score: Optional[float] = None,
    ) -> float:
        """
        计算单个条目的相关性分数

        Args:
            entry: 记忆条目
            query: 原始查询
            query_tokens: 查询 token 集合
            query_vec: 查询向量（HRR）
            entities: 实体列表
            min_score: 最低分数阈值（可选）

        Returns:
            相关性分数 [0, 1]，如果低于 min_score 返回 0.0
        """
        entry_lower = entry.lower()
        entry_tokens = self._tokenize(entry_lower)

        # 1. Jaccard 相似度
        jaccard_score = self._jaccard_similarity(query_tokens, entry_tokens)

        # 2. HRR 语义相似度
        hrr_score = 0.5  # 默认为中性分数
        if query_vec is not None and _HAS_NUMPY:
            try:
                if entities:
                    # 使用实体增强的 HRR 编码
                    entry_vec = encode_text_for_retrieval(entry, entities, self.config.hrr_dim)
                else:
                    entry_vec = encode_text(entry, self.config.hrr_dim)

                hrr_score = compute_similarity_normalized(query_vec, entry_vec)
            except Exception as e:
                logger.debug(f"HRR scoring failed for entry: {e}")

        # 3. 组合分数
        total_weight = (
            self.config.jaccard_weight
            + self.config.hrr_weight
            + self.config.fts_weight
        )

        if total_weight == 0:
            return 0.0

        combined_score = (
            self.config.jaccard_weight * jaccard_score
            + self.config.hrr_weight * hrr_score
        ) / (self.config.jaccard_weight + self.config.hrr_weight)

        # 短条目加分（简短条目通常是核心事实）
        length_bonus = self._length_bonus(entry)
        final_score = combined_score * (1.0 + length_bonus)

        # 使用动态 min_score 或配置的默认值进行过滤
        effective_min_score = min_score if min_score is not None else self.config.jaccard_min_overlap
        if final_score < effective_min_score:
            return 0.0

        return min(1.0, final_score)

    @staticmethod
    def _tokenize(text: str) -> set:
        """
        分词

        使用统一的 tokenize_text 函数，确保检索逻辑的一致性。

        Args:
            text: 文本

        Returns:
            token 集合（小写）
        """
        return tokenize_text(text, min_length=1)

    @staticmethod
    def _jaccard_similarity(set_a: set, set_b: set) -> float:
        """
        Jaccard 相似度系数

        Args:
            set_a: 集合 A
            set_b: 集合 B

        Returns:
            Jaccard 分数 [0, 1]
        """
        if not set_a or not set_b:
            return 0.0

        intersection = len(set_a & set_b)
        union = len(set_a | set_b)

        return intersection / union if union > 0 else 0.0

    @staticmethod
    def _length_bonus(entry: str, target_len: int = 100) -> float:
        """
        长度奖励 - 短条目优先

        较短的记忆条目通常是核心事实，值得优先返回。

        Args:
            entry: 记忆条目
            target_len: 目标长度

        Returns:
            长度奖励分数 [0, 0.5]
        """
        entry_len = len(entry)
        if entry_len <= 0:
            return 0.0

        # 越短奖励越高，最多 0.5
        bonus = max(0.0, min(0.5, (target_len - entry_len) / (2 * target_len)))
        return bonus


def encode_text_for_retrieval(
    text: str,
    entities: List[str],
    dim: int = 512
) -> "np.ndarray":
    """
    用于检索的文本编码

    结合文本和实体信息编码为向量。

    Args:
        text: 文本内容
        entities: 实体列表
        dim: 向量维度

    Returns:
        编码向量
    """
    # 尝试导入 hrr（可能未安装 numpy）
    try:
        from .hrr import encode_fact
        return encode_fact(text, entities, dim)
    except ImportError:
        # 降级到纯文本编码
        return encode_text(text, dim)


class ChineseSemanticRetriever(SemanticRetriever):
    """
    中文语义检索器

    针对中文文本优化的检索器：
    1. 使用字符级 n-gram 扩展 Jaccard
    2. 更好的中文分词处理
    """

    # 中文 n-gram 大小
    NGRAM_SIZE = 2

    @staticmethod
    def _tokenize_chinese(text: str) -> set:
        """
        中文分词 + n-gram

        使用正则分割 + n-gram 扩展，适合中英文混合文本。

        Args:
            text: 中文文本

        Returns:
            token 和 n-gram 集合（小写）
        """
        import re
        
        if not text:
            return set()

        tokens = set()
        text_lower = text.lower()

        # 1. 基础分词（按标点和空格分割）
        for word in re.split(r'[\s,.!?;:""''（）【】《》，。！？、：；]+', text_lower):
            word = word.strip()
            if not word:
                continue

            # 添加单词
            tokens.add(word)

            # 2. 字符级 n-gram（用于中文）
            if any('\u4e00' <= c <= '\u9fff' for c in word):
                chars = list(word)
                for i in range(len(chars) - ChineseSemanticRetriever.NGRAM_SIZE + 1):
                    ngram = ''.join(chars[i:i + ChineseSemanticRetriever.NGRAM_SIZE])
                    tokens.add(ngram)

        return tokens

    def _score_entry(
        self,
        entry: str,
        query: str,
        query_tokens: set,
        query_vec,
        entities: Optional[List[str]] = None,
        min_score: Optional[float] = None,
    ) -> float:
        """
        使用中文优化的评分
        """
        entry_lower = entry.lower()

        # 使用中文优化的分词
        entry_tokens = self._tokenize_chinese(entry_lower)

        # 扩展查询 token
        query_tokens_extended = self._tokenize_chinese(query.lower())

        # Jaccard 相似度（使用扩展 token）
        jaccard_score = self._jaccard_similarity(query_tokens_extended, entry_tokens)

        # HRR 语义相似度
        hrr_score = 0.5
        if query_vec is not None and _HAS_NUMPY:
            try:
                entry_vec = encode_text(entry, self.config.hrr_dim)
                hrr_score = compute_similarity_normalized(query_vec, entry_vec)
            except Exception:
                pass

        # 组合分数
        combined_score = (
            self.config.jaccard_weight * jaccard_score
            + self.config.hrr_weight * hrr_score
        ) / (self.config.jaccard_weight + self.config.hrr_weight)

        # 短条目加分
        length_bonus = self._length_bonus(entry)
        final_score = combined_score * (1.0 + length_bonus)

        return min(1.0, max(0.0, final_score))


def create_retriever(language: str = "auto") -> SemanticRetriever:
    """
    创建适合的检索器

    Args:
        language: 语言设置 ("auto", "chinese", "english")

    Returns:
        语义检索器实例
    """
    if language == "chinese":
        return ChineseSemanticRetriever()
    elif language == "english":
        return SemanticRetriever()
    else:
        # 自动检测：优先尝试中文检索器
        return ChineseSemanticRetriever()


# ============================================================================
# Module-level utilities (统一分词逻辑)
# ============================================================================

# 标点符号字符串（用于分词时去除）
_TOKENIZE_PUNCTUATION = ".,!?;:\"'()[]{}#@<>，。！？、：；""''（）【】《》"


def tokenize_text(text: str, min_length: int = 1) -> set:
    """
    统一分词工具函数

    确保检索逻辑的一致性，供其他模块使用（如 BuiltinMemoryProvider）。

    Args:
        text: 文本
        min_length: 最小 token 长度（默认 1，设置 > 1 可过滤短词）

    Returns:
        token 集合（小写）
    """
    if not text:
        return set()

    tokens = set()
    for word in text.split():
        cleaned = word.strip(_TOKENIZE_PUNCTUATION)
        if cleaned and len(cleaned) >= min_length:
            tokens.add(cleaned.lower())
    return tokens
