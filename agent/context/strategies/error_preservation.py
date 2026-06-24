"""错误信息保护策略"""

from typing import List, Dict, Any, Set
from . import CompressionStrategy, CompressionStrategyType
from .config import ErrorPreservationConfig
import re

class ErrorPreservationStrategy(CompressionStrategy):
    """错误信息保护策略"""
    
    def __init__(self, config: ErrorPreservationConfig = None):
        super().__init__(
            enabled=config.enabled if config else True,
            priority=config.priority if config else 30  # 高优先级
        )
        self.config = config or ErrorPreservationConfig()
        self._compile_patterns()
    
    @property
    def name(self) -> str:
        """策略名称."""
        return "error_preservation"
    
    def should_apply(self, messages: List[Dict[str, Any]], context: "CompressionContext") -> bool:
        """判断是否应该应用此策略."""
        return self._enabled
    
    def apply(self, messages: List[Dict[str, Any]], context: "CompressionContext") -> List[Dict[str, Any]]:
        """应用策略处理消息."""
        return self.compress(messages, context)
    
    def _compile_patterns(self):
        """预编译错误模式"""
        self._patterns = []
        for pattern in self.config.error_patterns:
            try:
                self._patterns.append(re.compile(pattern, re.IGNORECASE | re.MULTILINE))
            except re.error:
                # 如果正则无效，使用纯文本匹配
                self._patterns.append(re.compile(re.escape(pattern), re.IGNORECASE))
    
    @property
    def strategy_type(self) -> CompressionStrategyType:
        return CompressionStrategyType.ERROR_PRESERVATION
    
    def score(self, message: Dict[str, Any]) -> float:
        """评估消息中错误信息的重要程度"""
        content = message.get("content", "") or ""
        errors = self.extract_errors(content)
        
        if not errors:
            return 0.0
        
        # 有错误信息的消息必须保留
        return 1.0
    
    def extract_errors(self, content: str) -> List[str]:
        """从内容中提取所有错误信息"""
        errors = []
        
        for pattern in self._patterns:
            matches = pattern.findall(content)
            errors.extend(matches if isinstance(matches, list) else [matches])
        
        # 去重
        return list(dict.fromkeys(errors))
    
    def compress(self, messages: List[Dict[str, Any]], context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """保护错误信息，标记包含错误的消息"""
        if not messages:
            return messages
        
        # 收集所有错误信息
        all_errors: Set[str] = set()
        error_messages_indices = []
        
        result = []
        for i, msg in enumerate(messages):
            msg_copy = msg.copy()
            content = msg_copy.get("content", "") or ""
            
            errors = self.extract_errors(content)
            if errors:
                all_errors.update(errors)
                error_messages_indices.append(i)
                msg_copy["_has_error"] = True
                msg_copy["_errors_in_message"] = errors
            else:
                msg_copy["_has_error"] = False
            
            result.append(msg_copy)
        
        # 将所有错误信息存入 context
        context = context or {}
        context["_protected_errors"] = list(all_errors)
        
        return result
    
    def protect_errors_in_compression(
        self, 
        original: str, 
        compressed: str,
        protected_errors: List[str] = None
    ) -> str:
        """确保压缩后仍保留关键错误信息"""
        protected_errors = protected_errors or []
        
        if not protected_errors:
            return compressed
        
        # 检查每个错误是否还在压缩后的内容中
        missing_errors = []
        for error in protected_errors:
            # 简单检查：提取前50个字符作为关键字
            key = error[:min(50, len(error))].strip()
            if key and key not in compressed:
                missing_errors.append(error)
        
        # 添加缺失的错误信息
        if missing_errors:
            error_section = "\n\n## Protected Error Context\n" + "\n".join(missing_errors)
            compressed = compressed + error_section
        
        return compressed
    
    def extract_error_context(self, content: str, error: str, context_lines: int = 3) -> str:
        """提取错误信息的上下文（前后的行）"""
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            if error in line:
                # 返回错误行及上下文
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                return '\n'.join(lines[start:end])
        
        return error
    
    def categorize_errors(self, content: str) -> Dict[str, List[str]]:
        """对错误进行分类"""
        categories = {
            "syntax": [],
            "runtime": [],
            "import": [],
            "assertion": [],
            "other": []
        }
        
        patterns = {
            "syntax": [r"SyntaxError", r"IndentationError", r"TabError"],
            "runtime": [r"RuntimeError", r"TypeError", r"ValueError", r"AttributeError", r"KeyError", r"IndexError"],
            "import": [r"ImportError", r"ModuleNotFoundError", r"ImportModuleNotFoundError"],
            "assertion": [r"AssertionError", r"AssertionFailed"],
        }
        
        for error_type, type_patterns in patterns.items():
            for pattern in type_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    errors = self.extract_errors(content)
                    categories[error_type].extend(errors)
        
        # 其他错误
        all_extracted = set()
        for errors in categories.values():
            all_extracted.update(errors)
        
        other_errors = [e for e in self.extract_errors(content) if e not in all_extracted]
        categories["other"].extend(other_errors)
        
        return categories
