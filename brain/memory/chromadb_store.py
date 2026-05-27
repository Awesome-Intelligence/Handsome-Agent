"""ChromaDB 向量存储集成"""
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import uuid


@dataclass
class MemoryEntry:
    """记忆条目"""
    id: str
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = None


class ChromaDBVectorStore:
    """ChromaDB 向量存储实现"""
    
    def __init__(
        self,
        persist_directory: str = "./chroma_db",
        collection_name: str = "handsome_agent_memory",
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self._client = None
        self._collection = None
    
    async def initialize(self) -> None:
        """初始化 ChromaDB"""
        try:
            import chromadb
            from chromadb.config import Settings
            
            self._client = chromadb.Client(Settings(
                persist_directory=self.persist_directory,
                anonymized_telemetry=False
            ))
            
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name
            )
            
            return True
        except ImportError:
            print("ChromaDB 未安装，使用简单向量存储替代")
            return False
        except Exception as e:
            print(f"ChromaDB 初始化失败: {e}")
            return False
    
    async def add(self, entry: MemoryEntry) -> str:
        """添加记忆"""
        if not self._collection:
            return entry.id
        
        try:
            self._collection.add(
                documents=[entry.content],
                ids=[entry.id],
                metadatas=[entry.metadata or {}]
            )
            self._client.persist()
            return entry.id
        except Exception as e:
            print(f"添加记忆失败: {e}")
            return entry.id
    
    async def search(
        self,
        query: str,
        top_k: int = 5
    ) -> List[MemoryEntry]:
        """搜索相似记忆"""
        if not self._collection:
            return []
        
        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=top_k
            )
            
            entries = []
            if results and results.get("documents"):
                for i, doc in enumerate(results["documents"][0]):
                    entries.append(MemoryEntry(
                        id=results["ids"][0][i],
                        content=doc,
                        metadata=results.get("metadatas", [[{}]])[0][i]
                    ))
            
            return entries
        except Exception as e:
            print(f"搜索失败: {e}")
            return []
    
    async def delete(self, entry_id: str) -> bool:
        """删除记忆"""
        if not self._collection:
            return False
        
        try:
            self._collection.delete(ids=[entry_id])
            self._client.persist()
            return True
        except Exception as e:
            print(f"删除记忆失败: {e}")
            return False


class SimpleVectorStore:
    """简单向量存储（基于词频）"""
    
    def __init__(self, embedding_dim: int = 384):
        self.embedding_dim = embedding_dim
        self._entries: Dict[str, MemoryEntry] = {}
        self._embeddings: Dict[str, List[float]] = {}
    
    async def add(self, entry: MemoryEntry) -> str:
        """添加记忆"""
        words = entry.content.lower().split()
        embedding = [hash(w) % 100 / 100.0 for w in words[:self.embedding_dim]]
        while len(embedding) < self.embedding_dim:
            embedding.append(0.0)
        
        entry.embedding = embedding
        self._entries[entry.id] = entry
        self._embeddings[entry.id] = embedding
        return entry.id
    
    async def search(self, query: str, top_k: int = 5) -> List[MemoryEntry]:
        """搜索相似记忆"""
        words = query.lower().split()
        query_embedding = [hash(w) % 100 / 100.0 for w in words[:self.embedding_dim]]
        while len(query_embedding) < self.embedding_dim:
            query_embedding.append(0.0)
        
        similarities = []
        for entry_id, embedding in self._embeddings.items():
            sim = self._cosine_similarity(query_embedding, embedding)
            similarities.append((entry_id, sim))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        return [self._entries[eid] for eid, _ in similarities[:top_k]]
    
    async def delete(self, entry_id: str) -> bool:
        """删除记忆"""
        if entry_id in self._entries:
            del self._entries[entry_id]
            del self._embeddings[entry_id]
            return True
        return False
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """计算余弦相似度"""
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)


class VectorStoreFactory:
    """向量存储工厂"""
    
    @staticmethod
    async def create(
        use_chromadb: bool = True,
        **kwargs
    ) -> Any:
        """创建向量存储实例"""
        if use_chromadb:
            store = ChromaDBVectorStore(**kwargs)
            success = await store.initialize()
            if success:
                return store
            print("回退到简单向量存储")
        
        return SimpleVectorStore()