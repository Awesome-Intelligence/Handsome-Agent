"""
向量存储 - 语义检索
使用 embedding 模型进行语义相似度搜索
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import numpy as np


@dataclass
class MemoryEntry:
    """记忆条目"""
    id: str
    content: str
    embedding: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = None
    timestamp: float = 0.0


class VectorStore(ABC):
    """向量存储抽象基类"""
    
    @abstractmethod
    async def add(self, entry: MemoryEntry) -> str:
        """添加记忆"""
        pass
    
    @abstractmethod
    async def search(self, query: str, top_k: int = 5) -> List[MemoryEntry]:
        """搜索相似记忆"""
        pass
    
    @abstractmethod
    async def delete(self, entry_id: str) -> bool:
        """删除记忆"""
        pass
    
    @abstractmethod
    async def update(self, entry_id: str, content: str) -> bool:
        """更新记忆"""
        pass


class SimpleVectorStore(VectorStore):
    """简单向量存储（基于 TF-IDF）"""
    
    def __init__(self, embedding_dim: int = 384):
        self.embedding_dim = embedding_dim
        self._entries: Dict[str, MemoryEntry] = {}
        self._embeddings: Dict[str, np.ndarray] = {}
    
    async def add(self, entry: MemoryEntry) -> str:
        """添加记忆 - 使用简单的词袋模型"""
        # 简化的 embedding 实现
        words = entry.content.lower().split()
        embedding = np.zeros(self.embedding_dim)
        for i, word in enumerate(words[:self.embedding_dim]):
            embedding[i] = hash(word) % 100 / 100.0
        
        entry.embedding = embedding
        self._entries[entry.id] = entry
        self._embeddings[entry.id] = embedding
        return entry.id
    
    async def search(self, query: str, top_k: int = 5) -> List[MemoryEntry]:
        """搜索相似记忆 - 使用余弦相似度"""
        # 生成查询向量
        words = query.lower().split()
        query_embedding = np.zeros(self.embedding_dim)
        for i, word in enumerate(words[:self.embedding_dim]):
            query_embedding[i] = hash(word) % 100 / 100.0
        
        # 计算相似度
        similarities = []
        for entry_id, embedding in self._embeddings.items():
            sim = self._cosine_similarity(query_embedding, embedding)
            similarities.append((entry_id, sim))
        
        # 排序并返回 top_k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return [self._entries[eid] for eid, _ in similarities[:top_k]]
    
    async def delete(self, entry_id: str) -> bool:
        """删除记忆"""
        if entry_id in self._entries:
            del self._entries[entry_id]
            del self._embeddings[entry_id]
            return True
        return False
    
    async def update(self, entry_id: str, content: str) -> bool:
        """更新记忆"""
        if entry_id in self._entries:
            entry = self._entries[entry_id]
            entry.content = content
            await self.add(entry)
            return True
        return False
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """计算余弦相似度"""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return np.dot(a, b) / (norm_a * norm_b)