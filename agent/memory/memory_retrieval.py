"""Enhanced Memory Retrieval - Enhanced Memory Retrieval System

Integrates vector search and keyword search to provide semantic-level memory retrieval.

Features:
1. Hybrid retrieval strategy (vector + keyword)
2. Unified retrieval from multiple memory sources
3. Intelligent ranking and deduplication
4. Memory relevance scoring
"""

import json
import time
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

from common.logging_manager import get_decision_logger


@dataclass
class RetrievalResult:
    """检索结果"""
    content: str
    source: str  # 记忆来源
    source_id: str  # 具体来源ID
    relevance_score: float  # 相关度分数 0.0 - 1.0
    retrieval_method: str  # 'vector', 'keyword', 'hybrid'
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseRetriever(ABC):
    """检索器抽象基类"""

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        limit: int = 5,
        **kwargs
    ) -> List[RetrievalResult]:
        """
        执行检索

        Args:
            query: 查询文本
            limit: 返回数量限制
            **kwargs: 其他参数

        Returns:
            检索结果列表
        """
        pass

    @abstractmethod
    async def add(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        """
        添加记忆到检索索引

        Args:
            content: 记忆内容
            metadata: 元数据
        """
        pass


class KeywordRetriever(BaseRetriever):
    """
    基于关键词的检索器

    简单但可靠的检索方式
    """

    def __init__(self):
        self.documents: List[Dict[str, Any]] = []
        self.doc_id_counter = 0
        self.logger = get_decision_logger(self.__class__.__name__)

    async def retrieve(
        self,
        query: str,
        limit: int = 5,
        **kwargs
    ) -> List[RetrievalResult]:
        """关键词检索"""
        results = []
        query_terms = query.lower().split()

        for doc in self.documents:
            content_lower = doc['content'].lower()

            # 计算匹配分数
            matches = 0
            for term in query_terms:
                if term in content_lower:
                    matches += 1

            if matches > 0:
                score = matches / len(query_terms)
                results.append(RetrievalResult(
                    content=doc['content'],
                    source=doc.get('source', 'unknown'),
                    source_id=doc.get('id', ''),
                    relevance_score=score,
                    retrieval_method='keyword',
                    metadata=doc.get('metadata', {})
                ))

        # 按分数排序
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:limit]

    async def add(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        """添加文档"""
        self.doc_id_counter += 1
        self.documents.append({
            'id': f"doc_{self.doc_id_counter}",
            'content': content,
            'source': metadata.get('source', 'unknown') if metadata else 'unknown',
            'metadata': metadata or {}
        })


class HybridRetriever(BaseRetriever):
    """
    混合检索器

    结合向量检索和关键词检索的优势
    """

    def __init__(
        self,
        use_vector: bool = True,
        vector_weight: float = 0.6,
        keyword_weight: float = 0.4,
        embedding_dim: int = 384
    ):
        """
        Args:
            use_vector: 是否使用向量检索
            vector_weight: 向量检索权重
            keyword_weight: 关键词检索权重
            embedding_dim: 向量维度
        """
        self.use_vector = use_vector
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight
        self.embedding_dim = embedding_dim

        self.keyword_retriever = KeywordRetriever()
        self.documents: Dict[str, Dict[str, Any]] = {}  # id -> doc
        self.logger = get_decision_logger(self.__class__.__name__)

        # Simple vector storage (production should use FAISS or ChromaDB)
        self.vectors: Dict[str, List[float]] = {}

    def _simple_embed(self, text: str) -> List[float]:
        """简单的文本嵌入（生产环境应该用真正的 embedding 模型）"""
        import hashlib
        words = text.lower().split()
        vector = [0.0] * self.embedding_dim

        for i, word in enumerate(words[:self.embedding_dim]):
            # 使用哈希生成伪随机但确定的向量
            word_hash = hashlib.md5(word.encode()).digest()
            for j in range(min(len(word_hash), self.embedding_dim)):
                vector[j] += (word_hash[j] / 255.0) * (1.0 / (i + 1))

        # 归一化
        norm = sum(v * v for v in vector) ** 0.5
        if norm > 0:
            vector = [v / norm for v in vector]

        return vector

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot / (norm1 * norm2)

    async def retrieve(
        self,
        query: str,
        limit: int = 5,
        **kwargs
    ) -> List[RetrievalResult]:
        """混合检索"""
        results_dict: Dict[str, RetrievalResult] = {}

        # 1. 关键词检索
        keyword_results = await self.keyword_retriever.retrieve(query, limit=limit * 2)
        for result in keyword_results:
            result.retrieval_method = 'keyword'
            result.relevance_score *= self.keyword_weight
            results_dict[result.source_id] = result

        # 2. 向量检索（如果启用）
        if self.use_vector and self.vectors:
            query_vector = self._simple_embed(query)

            vector_results = []
            for doc_id, doc_vector in self.vectors.items():
                similarity = self._cosine_similarity(query_vector, doc_vector)

                if similarity > 0.1:  # 阈值
                    doc = self.documents.get(doc_id)
                    if doc:
                        vector_results.append(RetrievalResult(
                            content=doc['content'],
                            source=doc.get('source', 'unknown'),
                            source_id=doc_id,
                            relevance_score=similarity * self.vector_weight,
                            retrieval_method='vector',
                            metadata=doc.get('metadata', {})
                        ))

            # 合并向量结果
            for result in vector_results:
                if result.source_id in results_dict:
                    # 已有关键词结果，合并分数
                    existing = results_dict[result.source_id]
                    existing.relevance_score += result.relevance_score
                    if existing.retrieval_method == 'keyword':
                        existing.retrieval_method = 'hybrid'
                else:
                    results_dict[result.source_id] = result

        # 转换为列表并排序
        results = list(results_dict.values())
        results.sort(key=lambda x: x.relevance_score, reverse=True)

        return results[:limit]

    async def add(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """添加文档并建立索引"""
        doc_id = f"doc_{len(self.documents) + 1}"

        doc = {
            'id': doc_id,
            'content': content,
            'source': metadata.get('source', 'unknown') if metadata else 'unknown',
            'metadata': metadata or {},
            'timestamp': time.time()
        }

        self.documents[doc_id] = doc

        # 添加到关键词检索器
        await self.keyword_retriever.add(content, metadata)

        # 计算并存储向量
        if self.use_vector:
            self.vectors[doc_id] = self._simple_embed(content)


class UnifiedMemoryRetriever:
    """
    统一记忆检索器

    从多个记忆源检索并整合结果
    """

    def __init__(self):
        self.retrievers: Dict[str, BaseRetriever] = {}
        self.logger = get_decision_logger(self.__class__.__name__)

    def register_retriever(self, name: str, retriever: BaseRetriever):
        """Register retriever"""
        self.retrievers[name] = retriever
        self.logger.info(f"Registered retriever: {name}")

    async def retrieve(
        self,
        query: str,
        sources: Optional[List[str]] = None,
        limit: int = 10,
        min_score: float = 0.1
    ) -> List[RetrievalResult]:
        """
        从多个源检索记忆

        Args:
            query: 查询文本
            sources: 要检索的源列表，None 表示全部
            limit: 总返回数量限制
            min_score: 最低分数阈值

        Returns:
            检索结果列表
        """
        results: List[RetrievalResult] = []

        # 确定要检索的源
        target_sources = sources if sources else list(self.retrievers.keys())

        # 并行检索所有源
        for source_name in target_sources:
            if source_name not in self.retrievers:
                self.logger.warning(f"Unknown retriever: {source_name}")
                continue

            try:
                retriever = self.retrievers[source_name]
                source_results = await retriever.retrieve(query, limit=limit)

                for result in source_results:
                    result.source = source_name
                    if result.relevance_score >= min_score:
                        results.append(result)

            except Exception as e:
                self.logger.error(f"Error retrieving from {source_name}: {e}")

        # 去重（基于内容相似度）
        unique_results = self._deduplicate(results)

        # 按分数排序
        unique_results.sort(key=lambda x: x.relevance_score, reverse=True)

        return unique_results[:limit]

    def _deduplicate(
        self,
        results: List[RetrievalResult]
    ) -> List[RetrievalResult]:
        """简单的去重"""
        seen_content = set()
        unique = []

        for result in results:
            # 使用内容前100个字符作为去重键
            dedup_key = result.content[:100].lower().strip()

            if dedup_key not in seen_content:
                seen_content.add(dedup_key)
                unique.append(result)

        return unique

    async def add_to_source(
        self,
        source: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """添加记忆到指定源"""
        if source not in self.retrievers:
            self.logger.warning(f"Unknown source: {source}")
            return False

        try:
            await self.retrievers[source].add(content, metadata)
            self.logger.info(f"Added memory to {source}")
            return True
        except Exception as e:
            self.logger.error(f"Error adding to {source}: {e}")
            return False


class MemoryRetrievalPipeline:
    """
    记忆检索流水线

    支持复杂的多阶段检索策略
    """

    def __init__(self):
        self.stages: List[Dict[str, Any]] = []
        self.logger = get_decision_logger(self.__class__.__name__)

    def add_stage(
        self,
        name: str,
        retriever: BaseRetriever,
        priority: int = 0
    ):
        """
        Add retrieval stage

        Args:
            name: 阶段名称
            retriever: 检索器
            priority: 优先级（数字越小越先执行）
        """
        self.stages.append({
            'name': name,
            'retriever': retriever,
            'priority': priority
        })

        # 按优先级排序
        self.stages.sort(key=lambda x: x['priority'])

    async def execute(
        self,
        query: str,
        max_results: int = 10
    ) -> Dict[str, List[RetrievalResult]]:
        """
        执行检索流水线

        Args:
            query: 查询文本
            max_results: 每个阶段最大结果数

        Returns:
            各阶段结果字典
        """
        all_results: Dict[str, List[RetrievalResult]] = {}

        for stage in self.stages:
            stage_name = stage['name']
            retriever = stage['retriever']

            try:
                results = await retriever.retrieve(query, limit=max_results)
                all_results[stage_name] = results

                self.logger.debug(
                    f"Stage '{stage_name}' returned {len(results)} results"
                )

            except Exception as e:
                self.logger.error(f"Error in stage '{stage_name}': {e}")
                all_results[stage_name] = []

        return all_results

    async def execute_with_aggregation(
        self,
        query: str,
        max_results: int = 10,
        aggregation_method: str = 'score_weighted'
    ) -> List[RetrievalResult]:
        """
        执行检索并聚合结果

        Args:
            query: 查询文本
            max_results: 最大结果数
            aggregation_method: 聚合方法
                - 'score_weighted': 按分数加权合并
                - 'priority_first': 按优先级取结果
                - 'union': 合并所有结果

        Returns:
            聚合后的结果列表
        """
        all_stage_results = await self.execute(query, max_results)

        if aggregation_method == 'priority_first':
            # 按优先级取第一个非空结果
            for stage in self.stages:
                results = all_stage_results.get(stage['name'], [])
                if results:
                    return results[:max_results]
            return []

        elif aggregation_method == 'union':
            # 合并所有结果
            combined: List[RetrievalResult] = []
            seen_ids = set()

            for results in all_stage_results.values():
                for result in results:
                    if result.source_id not in seen_ids:
                        combined.append(result)
                        seen_ids.add(result.source_id)

            combined.sort(key=lambda x: x.relevance_score, reverse=True)
            return combined[:max_results]

        else:  # 'score_weighted'
            # 按分数加权合并
            combined: Dict[str, RetrievalResult] = {}
            stage_count = len(all_stage_results)

            for stage_results in all_stage_results.values():
                for result in stage_results:
                    if result.source_id in combined:
                        # 累加分数
                        existing = combined[result.source_id]
                        existing.relevance_score += result.relevance_score
                        existing.metadata['stage_count'] = \
                            existing.metadata.get('stage_count', 1) + 1
                    else:
                        result.metadata['stage_count'] = 1
                        combined[result.source_id] = result

            # 平均分数
            for result in combined.values():
                count = result.metadata.get('stage_count', 1)
                result.relevance_score /= count

            results = list(combined.values())
            results.sort(key=lambda x: x.relevance_score, reverse=True)
            return results[:max_results]
