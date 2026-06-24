"""语义相似度合并策略"""

from typing import List, Dict, Any, Tuple
from difflib import SequenceMatcher
from . import CompressionStrategy, CompressionStrategyType
from .config import SemanticMergeConfig

class SemanticMergeStrategy(CompressionStrategy):
    """基于语义相似度的消息合并策略"""
    
    def __init__(self, config: SemanticMergeConfig = None):
        super().__init__(
            enabled=config.enabled if config else True,
            priority=config.priority if config else 25
        )
        self.config = config or SemanticMergeConfig()
    
    @property
    def name(self) -> str:
        """策略名称."""
        return "semantic_merge"
    
    @property
    def strategy_type(self) -> CompressionStrategyType:
        return CompressionStrategyType.SEMANTIC_MERGE
    
    def score(self, message: Dict[str, Any]) -> float:
        """评分主要基于是否有可合并的相似消息（需要上下文）"""
        return 0.5
    
    def should_apply(self, messages: List[Dict[str, Any]], context: "CompressionContext") -> bool:
        """判断是否应该应用此策略."""
        return self._enabled and len(messages) >= 2
    
    def apply(self, messages: List[Dict[str, Any]], context: "CompressionContext") -> List[Dict[str, Any]]:
        """应用策略处理消息."""
        return self.compress(messages, context)
    
    def compress(self, messages: List[Dict[str, Any]], context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """合并语义相似的连续消息"""
        if not messages or len(messages) < 2:
            return messages
        
        result = []
        i = 0
        
        while i < len(messages):
            current = messages[i]
            similar_batch = [current]
            
            # 查找后续相似的消息
            j = i + 1
            merge_count = 0
            while j < len(messages) and merge_count < self.config.max_merge_count:
                next_msg = messages[j]
                
                # 只合并相同角色的消息
                if next_msg.get("role") != current.get("role"):
                    break
                
                similarity = self._calculate_similarity(
                    current.get("content", ""),
                    next_msg.get("content", "")
                )
                
                if similarity >= self.config.similarity_threshold:
                    similar_batch.append(next_msg)
                    merge_count += 1
                    j += 1
                else:
                    break
            
            if len(similar_batch) > 1:
                # 合并消息
                merged = self._merge_messages(similar_batch)
                result.append(merged)
            else:
                result.append(current)
            
            i = j if len(similar_batch) > 1 else i + 1
        
        # 标记被合并的消息数
        original_count = len(messages)
        merged_count = len(result)
        context = context or {}
        context["_semantic_merged"] = original_count - merged_count
        
        return result
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算两个文本的语义相似度"""
        if not text1 or not text2:
            return 0.0
        
        # 基础相似度
        ratio = SequenceMatcher(None, text1, text2).ratio()
        
        # 考虑长度差异的惩罚
        len1, len2 = len(text1), len(text2)
        if len1 > 0 and len2 > 0:
            len_ratio = min(len1, len2) / max(len1, len2)
            ratio *= (0.7 + 0.3 * len_ratio)
        
        return ratio
    
    def _merge_messages(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """合并多条相似消息"""
        if not messages:
            return {}
        
        # 选择最长的内容作为基础
        merged = max(messages, key=lambda m: len(m.get("content", "") or ""))
        merged = merged.copy()
        
        # 统计合并信息
        merged["_merged_from_count"] = len(messages)
        merged["_merged_roles"] = [m.get("role") for m in messages]
        
        # 如果有工具调用，合并它们
        all_tool_calls = []
        for msg in messages:
            tool_calls = msg.get("tool_calls", [])
            if tool_calls:
                all_tool_calls.extend(tool_calls if isinstance(tool_calls, list) else [tool_calls])
        
        if all_tool_calls:
            merged["tool_calls"] = all_tool_calls
        
        return merged
    
    def get_merge_candidates(self, messages: List[Dict[str, Any]]) -> List[Tuple[int, int, float]]:
        """获取所有可合并的消息对及其相似度"""
        candidates = []
        
        for i in range(len(messages) - 1):
            for j in range(i + 1, min(i + self.config.max_merge_count + 1, len(messages))):
                if messages[i].get("role") != messages[j].get("role"):
                    continue
                
                similarity = self._calculate_similarity(
                    messages[i].get("content", ""),
                    messages[j].get("content", "")
                )
                
                if similarity >= self.config.similarity_threshold:
                    candidates.append((i, j, similarity))
        
        return candidates
