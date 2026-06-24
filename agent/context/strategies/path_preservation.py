"""文件路径保护策略"""

from typing import List, Dict, Any, Set
from . import CompressionStrategy, CompressionStrategyType
from .config import PathPreservationConfig
import re


class PathPreservationStrategy(CompressionStrategy):
    """保护和提取文件路径信息的策略"""
    
    def __init__(self, config: PathPreservationConfig = None):
        super().__init__(
            enabled=config.enabled if config else True,
            priority=config.priority if config else 12
        )
        self.config = config or PathPreservationConfig()
        self._name = "path_preservation"
        self._compile_patterns()
    
    def _compile_patterns(self):
        """预编译路径模式"""
        self._patterns = [
            # Unix 风格路径
            re.compile(r'(?:/[\w\.\-]+)+\.(?:py|js|ts|tsx|jsx|java|cpp|c|h|hpp|go|rs|rb|php|cs|swift|kt)'),
            # Windows 风格路径
            re.compile(r'[A-Za-z]:\\(?:[\w\.\-]+\\)*[\w\.\-]+\.(?:py|js|ts|java|cpp|c|h|md|json|yaml|yml|toml|xml|html|css|sql)'),
            # 相对路径
            re.compile(r'(?:[\.\/]?[\w\.\-]+\/)*[\w\.\-]+\.(?:py|js|ts|md|json|yaml|yml|toml)'),
            # URL 路径
            re.compile(r'https?://[^\s]+\.(?:py|js|ts|md|json|yaml|yml)'),
        ]
        
        # 扩展名快速查找
        self._ext_set = set(self.config.file_extensions)
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def strategy_type(self) -> CompressionStrategyType:
        return CompressionStrategyType.PATH_PRESERVATION
    
    def should_apply(self, messages: List[Dict[str, Any]], context) -> bool:
        """判断是否应该应用此策略"""
        if not self.enabled:
            return False
        for msg in messages:
            content = msg.get("content", "") or ""
            if self.extract_paths(content):
                return True
        return False
    
    def score(self, message: Dict[str, Any]) -> float:
        """评估消息中路径的重要程度"""
        content = message.get("content", "") or ""
        paths = self.extract_paths(content)
        
        if not paths:
            return 0.0
        
        # 有路径的消息评分
        return min(1.0, 0.4 + len(paths) * 0.1)
    
    def extract_paths(self, content: str) -> List[str]:
        """从内容中提取所有文件路径"""
        paths = set()
        
        # 方法1：正则匹配
        for pattern in self._patterns:
            matches = pattern.findall(content)
            paths.update(matches)
        
        # 方法2：按扩展名快速查找
        for ext in self._ext_set:
            # 查找包含该扩展名的所有位置
            idx = 0
            while True:
                idx = content.find(ext, idx)
                if idx == -1:
                    break
                
                # 向左扩展
                start = idx
                while start > 0 and content[start - 1] not in ' \n\r\t"\'<>{},':
                    start -= 1
                
                # 向右扩展
                end = idx + len(ext)
                while end < len(content) and content[end] not in ' \n\r\t"\'<>{},':
                    end += 1
                
                path = content[start:end].strip()
                if len(path) > 3 and ('/' in path or '\\' in path or path.startswith('.')):
                    paths.add(path)
                
                idx += 1
        
        return list(paths)
    
    def apply(self, messages: List[Dict[str, Any]], context) -> List[Dict[str, Any]]:
        """应用策略处理消息"""
        return self.compress(messages, context.__dict__ if hasattr(context, '__dict__') else None)
    
    def compress(self, messages: List[Dict[str, Any]], context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """提取和保护路径信息"""
        if not messages:
            return messages
        
        # 收集所有路径
        all_paths: Set[str] = set()
        for msg in messages:
            content = msg.get("content", "") or ""
            all_paths.update(self.extract_paths(content))
        
        context = context or {}
        context["_protected_paths"] = list(all_paths)
        
        # 标记包含路径的消息
        result = []
        for msg in messages:
            msg_copy = msg.copy()
            content = msg_copy.get("content", "") or ""
            paths = self.extract_paths(content)
            msg_copy["_has_paths"] = len(paths) > 0
            msg_copy["_paths_in_message"] = paths
            result.append(msg_copy)
        
        return result
    
    def protect_path_content(self, content: str, protected_paths: List[str]) -> str:
        """确保路径相关内容被保护"""
        if not protected_paths:
            return content
        
        lines = content.split('\n')
        protected_lines = []
        
        for line in lines:
            if any(path in line for path in protected_paths):
                protected_lines.append(line)
            elif line.strip().startswith('#') or not line.strip():
                # 保留空行和注释
                protected_lines.append(line)
            else:
                protected_lines.append(line)
        
        return '\n'.join(protected_lines)
