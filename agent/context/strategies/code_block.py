"""代码块智能压缩策略"""

from typing import List, Dict, Any, Tuple
from . import CompressionStrategy, CompressionStrategyType
from .config import CodeBlockConfig
import re


class CodeBlockStrategy(CompressionStrategy):
    """智能压缩代码块内容，保留关键结构"""
    
    def __init__(self, config: CodeBlockConfig = None):
        super().__init__(
            enabled=config.enabled if config else True,
            priority=config.priority if config else 15
        )
        self.config = config or CodeBlockConfig()
        self._name = "code_block"
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def strategy_type(self) -> CompressionStrategyType:
        return CompressionStrategyType.CODE_BLOCK
    
    def should_apply(self, messages: List[Dict[str, Any]], context) -> bool:
        """判断是否应该应用此策略"""
        if not self.enabled:
            return False
        for msg in messages:
            content = msg.get("content", "") or ""
            if self._has_code_block(content):
                return True
        return False
    
    def score(self, message: Dict[str, Any]) -> float:
        """评估消息中代码块的重要程度"""
        content = message.get("content", "") or ""
        code_blocks = self._extract_code_blocks(content)
        
        if not code_blocks:
            return 0.0
        
        # 有代码块的消息评分为正
        importance = min(1.0, 0.5 + len(code_blocks) * 0.1)
        
        # 检查是否包含 TODO/FIXME
        for block in code_blocks:
            if any(kw in block.upper() for kw in self.config.preserve_comments):
                return 1.0
        
        return importance
    
    def _extract_code_blocks(self, content: str) -> List[str]:
        """提取所有代码块"""
        pattern = r'```[\s\S]*?```'
        return re.findall(pattern, content)
    
    def apply(self, messages: List[Dict[str, Any]], context) -> List[Dict[str, Any]]:
        """应用策略处理消息"""
        return self.compress(messages)
    
    def compress(self, messages: List[Dict[str, Any]], context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """压缩消息中的代码块"""
        if not messages:
            return messages
        
        result = []
        for msg in messages:
            msg_copy = msg.copy()
            content = msg_copy.get("content", "") or ""
            
            if content and self._has_code_block(content):
                compressed_content = self._smart_code_compression(content)
                msg_copy["content"] = compressed_content
                msg_copy["_code_compressed"] = compressed_content != content
            
            result.append(msg_copy)
        
        return result
    
    def _has_code_block(self, content: str) -> bool:
        """检查内容是否包含代码块"""
        return '```' in content or '`' in content
    
    def _smart_code_compression(self, content: str) -> str:
        """智能压缩代码块"""
        # 处理 markdown 代码块
        result = []
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # 代码块开始
            if line.strip().startswith('```'):
                # 提取语言标识
                lang_match = re.match(r'```(\w*)', line.strip())
                lang = lang_match.group(1) if lang_match else ''
                
                # 找到代码块结束
                block_lines = [line]
                j = i + 1
                while j < len(lines) and not lines[j].strip().startswith('```'):
                    block_lines.append(lines[j])
                    j += 1
                
                if j < len(lines):
                    block_lines.append(lines[j])  # 结束标记
                
                # 压缩代码块
                compressed_block = self._compress_code_block(block_lines, lang)
                result.extend(compressed_block)
                i = j + 1
            else:
                # 非代码块行保留
                result.append(line)
                i += 1
        
        return '\n'.join(result)
    
    def _compress_code_block(self, lines: List[str], lang: str) -> List[str]:
        """压缩单个代码块"""
        if len(lines) <= 3:
            return lines
        
        result = [lines[0]]  # 保留开始标记
        
        # 判断代码类型
        code_lines = lines[1:-1] if len(lines) > 1 else []
        
        # 提取需要保留的行
        preserved = []
        skipped = 0
        
        for line in code_lines:
            stripped = line.strip()
            
            # 保留关键行
            if self._is_preserve_line(stripped, lang):
                preserved.append(line)
            # 保留空行（保持结构）
            elif not stripped:
                preserved.append(line)
            else:
                skipped += 1
        
        # 如果超过限制，进行进一步压缩
        if len(preserved) > self.config.max_preserved_lines:
            preserved = self._aggressive_compress(preserved)
        
        result.extend(preserved)
        
        # 添加省略提示
        if skipped > 3:
            indent = self._get_indent(lines[1] if len(lines) > 1 else '')
            result.append(f"{indent}# ... {skipped} lines omitted ...")
        
        result.append(lines[-1])  # 保留结束标记
        
        return result
    
    def _is_preserve_line(self, line: str, lang: str) -> bool:
        """判断是否为需要保留的行"""
        if not line:
            return True
        
        if line.startswith('#') or line.startswith('//'):
            if any(kw in line.upper() for kw in self.config.preserve_comments):
                return True
        
        for kw in self.config.preserve_keywords:
            if kw in line:
                return True
        
        # 括号平衡保留（结构行）
        if line.strip() in ['{', '}', '[', ']', '(', ')', 'begin', 'end', 'then', 'do']:
            return True
        
        return False
    
    def _get_indent(self, line: str) -> str:
        """获取行的缩进"""
        return line[:len(line) - len(line.lstrip())]
    
    def _aggressive_compress(self, lines: List[str]) -> List[str]:
        """激进压缩：只保留关键行"""
        result = []
        in_multiline = False
        
        for line in lines:
            stripped = line.strip()
            
            # 保留函数/类定义
            if re.match(r'(def|class|function|interface|struct|enum)\s+\w+', stripped):
                result.append(line)
                in_multiline = True
            # 保留 import
            elif re.match(r'(import|from|require|include)\s+', stripped):
                result.append(line)
            # 保留注释
            elif stripped.startswith('#') or stripped.startswith('//'):
                result.append(line)
            # 保留 docstring 开头
            elif '"""' in stripped or "'''" in stripped:
                result.append(line)
                if stripped.endswith('"""') or stripped.endswith("'''"):
                    in_multiline = False
            elif stripped.endswith('"""') or stripped.endswith("'''"):
                result.append(line)
                in_multiline = False
        
        return result if result else lines[:self.config.max_preserved_lines]
