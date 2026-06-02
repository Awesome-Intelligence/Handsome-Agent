"""Enhanced Memory System

Multi-layered memory system integrating working, session, persistent, and episodic memory.
Inspired by Hermes Agent's multi-layered memory design:
1. Working Memory - Current context
2. Session Memory - Current session history
3. Persistent Memory - Cross-session knowledge
4. Episodic Memory - Important event records

Features:
1. Layered memory management
2. Automatic memory consolidation
3. Intelligent retrieval
4. Memory compression and archival
"""

import json
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from common.logging_manager import get_decision_logger

from .builtin_memory import BuiltinMemoryProvider
from .markdown_memory import MarkdownMemoryStore, MemoryCurator, MemoryEntry
from .memory_retrieval import (
    HybridRetriever,
    UnifiedMemoryRetriever,
    RetrievalResult
)
from .context_compressor import ContextCompressionManager


class MemoryType(Enum):
    """Memory type enumeration"""
    WORKING = "working"  # Working memory
    SESSION = "session"  # Session memory
    PERSISTENT = "persistent"  # Persistent memory
    EPISODIC = "episodic"  # Episodic memory


@dataclass
class MemoryItem:
    """Memory item"""
    id: str
    content: str
    memory_type: MemoryType
    timestamp: float = field(default_factory=time.time)
    importance: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'content': self.content,
            'memory_type': self.memory_type.value,
            'timestamp': self.timestamp,
            'importance': self.importance,
            'metadata': self.metadata,
            'session_id': self.session_id
        }


class EnhancedMemorySystem:
    """
    Enhanced multi-layered memory system

    Integrates various memory storage and retrieval mechanisms with unified interface
    """

    def __init__(
        self,
        session_id: Optional[str] = None,
        enable_vector_search: bool = True,
        enable_auto_curation: bool = True,
        max_working_items: int = 20,
        max_session_items: int = 100
    ):
        """
        Args:
            session_id: Current session ID
            enable_vector_search: Enable vector search
            enable_auto_curation: Enable auto curation
            max_working_items: Maximum working memory items
            max_session_items: Maximum session memory items
        """
        self.session_id = session_id
        self.enable_vector_search = enable_vector_search
        self.enable_auto_curation = enable_auto_curation

        # Memory storage
        self.markdown_store = MarkdownMemoryStore()
        self.curator = MemoryCurator(
            self.markdown_store,
            min_importance=0.3,
            max_entries_per_category=100
        )

        # Retrieval system
        self.retriever = UnifiedMemoryRetriever()
        if enable_vector_search:
            self.hybrid_retriever = HybridRetriever(use_vector=True)
            self.retriever.register_retriever('hybrid', self.hybrid_retriever)

        # Context compression
        self.compression_manager = ContextCompressionManager()

        # In-memory working memory
        self.working_memory: List[MemoryItem] = []
        self.max_working_items = max_working_items

        # Session memory
        self.session_memory: List[MemoryItem] = []
        self.max_session_items = max_session_items

        self.logger = get_decision_logger(self.__class__.__name__)

    def add_working_memory(
        self,
        content: str,
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        添加工作记忆

        Args:
            content: 记忆内容
            importance: 重要性 (0.0 - 1.0)
            metadata: 元数据

        Returns:
            记忆 ID
        """
        memory_id = f"working_{int(time.time() * 1000)}"

        item = MemoryItem(
            id=memory_id,
            content=content,
            memory_type=MemoryType.WORKING,
            importance=importance,
            metadata=metadata or {},
            session_id=self.session_id
        )

        self.working_memory.append(item)

        # 限制工作记忆大小
        if len(self.working_memory) > self.max_working_items:
            self._consolidate_working_memory()

        self.logger.debug(f"Added working memory: {memory_id}")
        return memory_id

    def _consolidate_working_memory(self):
        """整理工作记忆，将重要内容转移到会话记忆"""
        if not self.working_memory:
            return

        # 按重要性排序
        sorted_items = sorted(
            self.working_memory,
            key=lambda x: x.importance,
            reverse=True
        )

        # 保留最重要的部分
        kept = sorted_items[:self.max_working_items // 2]
        to_archive = sorted_items[self.max_working_items // 2:]

        # 将重要的移到会话记忆
        for item in to_archive:
            if item.importance >= 0.6:
                item.memory_type = MemoryType.SESSION
                self.add_session_memory(
                    content=item.content,
                    importance=item.importance,
                    metadata={**item.metadata, 'archived_from': 'working'}
                )

        self.working_memory = kept
        self.logger.debug(
            f"Consolidated working memory: kept {len(kept)}, archived {len(to_archive)}"
        )

    def add_session_memory(
        self,
        content: str,
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        添加会话记忆

        Args:
            content: 记忆内容
            importance: 重要性
            metadata: 元数据

        Returns:
            记忆 ID
        """
        memory_id = f"session_{int(time.time() * 1000)}"

        item = MemoryItem(
            id=memory_id,
            content=content,
            memory_type=MemoryType.SESSION,
            importance=importance,
            metadata=metadata or {},
            session_id=self.session_id
        )

        self.session_memory.append(item)

        # 持久化到 Markdown 存储
        self.markdown_store.store(
            MemoryEntry(
                id=memory_id,
                content=content,
                category='sessions',
                importance=importance,
                metadata=metadata or {}
            )
        )

        # 添加到检索索引
        if self.enable_vector_search and hasattr(self, 'hybrid_retriever'):
            import asyncio
            asyncio.create_task(
                self.hybrid_retriever.add(
                    content,
                    {'source': 'session', 'memory_id': memory_id}
                )
            )

        # 限制会话记忆大小
        if len(self.session_memory) > self.max_session_items:
            self._prune_session_memory()

        self.logger.debug(f"Added session memory: {memory_id}")
        return memory_id

    def _prune_session_memory(self):
        """修剪会话记忆，移除低重要性的旧条目"""
        if not self.session_memory:
            return

        # 按时间和重要性排序
        sorted_items = sorted(
            self.session_memory,
            key=lambda x: (x.importance, x.timestamp),
            reverse=True
        )

        # 保留最重要的部分
        self.session_memory = sorted_items[:self.max_session_items]

        self.logger.debug(
            f"Pruned session memory: now {len(self.session_memory)} items"
        )

    def add_persistent_memory(
        self,
        content: str,
        category: str = "general",
        importance: float = 0.7,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        添加持久记忆（跨会话）

        Args:
            content: 记忆内容
            category: 分类
            importance: 重要性
            metadata: 元数据

        Returns:
            记忆 ID
        """
        memory_id = f"persistent_{int(time.time() * 1000)}"

        item = MemoryItem(
            id=memory_id,
            content=content,
            memory_type=MemoryType.PERSISTENT,
            importance=importance,
            metadata={**(metadata or {}), 'category': category}
        )

        # 持久化到 Markdown 存储
        self.markdown_store.store(
            MemoryEntry(
                id=memory_id,
                content=content,
                category=category,
                importance=importance,
                metadata=metadata or {}
            )
        )

        # 添加到检索索引
        if self.enable_vector_search and hasattr(self, 'hybrid_retriever'):
            import asyncio
            asyncio.create_task(
                self.hybrid_retriever.add(
                    content,
                    {'source': 'persistent', 'memory_id': memory_id, 'category': category}
                )
            )

        self.logger.info(f"Added persistent memory: {memory_id} in {category}")
        return memory_id

    async def retrieve(
        self,
        query: str,
        memory_types: Optional[List[MemoryType]] = None,
        limit: int = 10,
        use_semantic: bool = True
    ) -> List[RetrievalResult]:
        """
        检索记忆

        Args:
            query: 查询文本
            memory_types: 要检索的记忆类型，None 表示全部
            limit: 返回数量限制
            use_semantic: 是否使用语义检索

        Returns:
            检索结果列表
        """
        results: List[RetrievalResult] = []

        # 1. 语义检索（如果启用）
        if use_semantic and self.enable_vector_search and hasattr(self, 'hybrid_retriever'):
            semantic_results = await self.retriever.retrieve(
                query,
                sources=['hybrid'] if 'hybrid' in self.retriever.retrievers else None,
                limit=limit
            )
            results.extend(semantic_results)

        # 2. 工作记忆快速检索
        if memory_types is None or MemoryType.WORKING in memory_types:
            for item in self.working_memory:
                if query.lower() in item.content.lower():
                    results.append(RetrievalResult(
                        content=item.content,
                        source='working_memory',
                        source_id=item.id,
                        relevance_score=0.8,
                        retrieval_method='keyword',
                        timestamp=item.timestamp,
                        metadata=item.metadata
                    ))

        # 3. 会话记忆检索
        if memory_types is None or MemoryType.SESSION in memory_types:
            for item in self.session_memory:
                if query.lower() in item.content.lower():
                    results.append(RetrievalResult(
                        content=item.content,
                        source='session_memory',
                        source_id=item.id,
                        relevance_score=0.7,
                        retrieval_method='keyword',
                        timestamp=item.timestamp,
                        metadata=item.metadata
                    ))

        # 4. 持久记忆检索（Markdown 存储）
        if memory_types is None or MemoryType.PERSISTENT in memory_types:
            md_results = self.markdown_store.retrieve(query, limit=limit)
            for entry, score in md_results:
                results.append(RetrievalResult(
                    content=entry.content,
                    source='persistent_memory',
                    source_id=entry.id,
                    relevance_score=score,
                    retrieval_method='keyword',
                    timestamp=entry.timestamp,
                    metadata=entry.metadata
                ))

        # 去重和排序
        seen = set()
        unique_results = []
        for r in results:
            if r.source_id not in seen:
                seen.add(r.source_id)
                unique_results.append(r)

        unique_results.sort(key=lambda x: x.relevance_score, reverse=True)
        return unique_results[:limit]

    def get_context_for_prompt(
        self,
        query: Optional[str] = None,
        max_items: int = 10,
        include_types: Optional[List[MemoryType]] = None
    ) -> str:
        """
        生成用于 Prompt 的记忆上下文

        Args:
            query: 可选的查询，用于检索相关记忆
            max_items: 最大返回条目数
            include_types: 要包含的记忆类型

        Returns:
            格式化的记忆上下文字符串
        """
        context_parts = []

        # 1. 工作记忆（始终包含最新的）
        if include_types is None or MemoryType.WORKING in include_types:
            working = self.working_memory[-5:] if self.working_memory else []
            if working:
                context_parts.append("## Recent Context")
                for item in working:
                    context_parts.append(f"- {item.content}")

        # 2. 会话记忆（最近的）
        if include_types is None or MemoryType.SESSION in include_types:
            session = self.session_memory[-10:] if self.session_memory else []
            if session:
                context_parts.append("\n## Session History")
                for item in session:
                    time_str = time.strftime(
                        '%H:%M',
                        time.localtime(item.timestamp)
                    )
                    context_parts.append(f"[{time_str}] {item.content[:100]}")

        if not context_parts:
            return ""

        return "\n".join(context_parts)

    def save_session(self):
        """保存当前会话"""
        # 保存会话记忆到 Markdown
        messages = []
        for item in self.session_memory:
            messages.append({
                'role': 'assistant',
                'content': item.content,
                'timestamp': item.timestamp,
                'metadata': item.metadata
            })

        if messages and self.session_id:
            self.markdown_store.save_session(
                self.session_id,
                messages,
                {'memory_count': len(messages)}
            )

        self.logger.info(f"Saved session: {self.session_id}")

    def curate_memories(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        整理记忆

        Args:
            dry_run: 是否仅预览

        Returns:
            整理统计
        """
        if not self.enable_auto_curation:
            return {'status': 'disabled'}

        return self.curator.curate(dry_run=dry_run)

    def get_memory_stats(self) -> Dict[str, Any]:
        """获取记忆统计信息"""
        return {
            'working_memory': {
                'count': len(self.working_memory),
                'max': self.max_working_items
            },
            'session_memory': {
                'count': len(self.session_memory),
                'max': self.max_session_items
            },
            'compression_stats': self.compression_manager.get_compression_stats(),
            'auto_curation': self.enable_auto_curation,
            'vector_search': self.enable_vector_search
        }
