"""指令-结果分离压缩策略"""

from typing import List, Dict, Any, Tuple
from . import CompressionStrategy, CompressionStrategyType
from .config import InstructionResultConfig

class InstructionResultSeparationStrategy(CompressionStrategy):
    """将工具调用（指令）和结果分离，允许对结果进行更激进的裁剪"""
    
    def __init__(self, config: InstructionResultConfig = None):
        super().__init__(
            enabled=config.enabled if config else True,
            priority=config.priority if config else 18
        )
        self.config = config or InstructionResultConfig()
    
    @property
    def name(self) -> str:
        """策略名称."""
        return "instruction_result"
    
    @property
    def strategy_type(self) -> CompressionStrategyType:
        return CompressionStrategyType.INSTRUCTION_RESULT
    
    def score(self, message: Dict[str, Any]) -> float:
        """指令评分为高，结果评分根据长度调整"""
        role = message.get("role", "")
        
        if role == "assistant" and message.get("tool_calls"):
            return 1.0  # 指令必须保留
        
        if role == "tool":
            content = message.get("content", "") or ""
            # 短结果保留，长结果可压缩
            if len(content) < self.config.prune_threshold:
                return 1.0
            elif len(content) < self.config.prune_threshold * 3:
                return 0.6
            else:
                return 0.3
        
        return 0.5
    
    def should_apply(self, messages: List[Dict[str, Any]], context: "CompressionContext") -> bool:
        """判断是否应该应用此策略."""
        return self._enabled
    
    def apply(self, messages: List[Dict[str, Any]], context: "CompressionContext") -> List[Dict[str, Any]]:
        """应用策略处理消息."""
        return self.compress(messages, context)
    
    def compress(self, messages: List[Dict[str, Any]], context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """分离指令和结果，对结果进行选择性压缩"""
        if not messages:
            return messages
        
        result = []
        preserved_results = 0
        
        i = 0
        while i < len(messages):
            msg = messages[i]
            role = msg.get("role", "")
            
            if role == "assistant" and msg.get("tool_calls"):
                # 工具调用（指令）保留
                result.append(msg.copy())
            
            elif role == "tool":
                # 工具结果
                compressed_result = self._compress_result(msg, preserved_results)
                result.append(compressed_result)
                
                if not compressed_result.get("_result_pruned"):
                    preserved_results += 1
            
            else:
                result.append(msg.copy())
            
            i += 1
        
        return result
    
    def _compress_result(self, msg: Dict[str, Any], result_index: int) -> Dict[str, Any]:
        """压缩单个工具结果"""
        msg_copy = msg.copy()
        content = msg_copy.get("content", "") or ""
        
        # 保留前 N 个结果
        if result_index < self.config.preserve_first_n:
            msg_copy["_result_pruned"] = False
            return msg_copy
        
        # 检查是否需要裁剪
        if len(content) > self.config.prune_threshold:
            compressed = self._smart_truncate(content)
            msg_copy["content"] = compressed
            msg_copy["_result_pruned"] = True
            msg_copy["_original_length"] = len(content)
        else:
            msg_copy["_result_pruned"] = False
        
        return msg_copy
    
    def _smart_truncate(self, content: str) -> str:
        """智能截断内容"""
        # 如果是结构化内容（JSON/XML），只保留关键字段
        if content.strip().startswith('{') or content.strip().startswith('['):
            return self._truncate_structured(content)
        
        # 对于普通文本，保留开头和结尾
        if len(content) <= self.config.prune_threshold * 2:
            return content
        
        head_len = self.config.prune_threshold // 2
        tail_len = self.config.prune_threshold // 2
        
        return (
            content[:head_len] +
            f"\n... [{len(content) - head_len - tail_len} chars omitted] ...\n" +
            content[-tail_len:]
        )
    
    def _truncate_structured(self, content: str) -> str:
        """截断结构化内容（JSON等）"""
        try:
            import json
            data = json.loads(content)
            return json.dumps(data, indent=2, ensure_ascii=False)[:self.config.prune_threshold * 2]
        except (json.JSONDecodeError, ValueError):
            return self._smart_truncate(content)
    
    def separate_instruction_result(
        self, messages: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """将消息分离为指令和结果两部分"""
        instructions = []
        results = []
        
        for msg in messages:
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                instructions.append(msg)
            elif msg.get("role") == "tool":
                results.append(msg)
            else:
                # 非工具消息归入指令
                instructions.append(msg)
        
        return instructions, results
