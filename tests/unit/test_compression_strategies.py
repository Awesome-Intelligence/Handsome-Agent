#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""压缩策略单元测试"""

import pytest
from typing import List, Dict, Any

from agent.context.strategies import (
    KeywordPriorityStrategy,
    TurnImportanceStrategy,
    CodeBlockStrategy,
    PathPreservationStrategy,
    SemanticMergeStrategy,
    ErrorPreservationStrategy,
    AdaptiveCompressionStrategy,
    InstructionResultSeparationStrategy,
    KeywordPriorityConfig,
    TurnImportanceConfig,
    CodeBlockConfig,
    PathPreservationConfig,
    SemanticMergeConfig,
    ErrorPreservationConfig,
    AdaptiveCompressionConfig,
    InstructionResultConfig,
)


class TestKeywordPriorityStrategy:
    """关键词优先级策略测试"""
    
    def test_high_priority_keywords(self):
        """高优先级关键词应得高分"""
        strategy = KeywordPriorityStrategy()
        
        msg_error = {"content": "Error: something went wrong", "role": "user"}
        msg_success = {"content": "ok, done", "role": "user"}
        
        assert strategy.score(msg_error) > strategy.score(msg_success)
    
    def test_keyword_level_classification(self):
        """关键词级别分类"""
        strategy = KeywordPriorityStrategy()
        
        msg_high = {"content": "The error occurred in the function", "role": "user"}
        msg_medium = {"content": "I created a new file", "role": "user"}
        msg_low = {"content": "Thanks, great, good job", "role": "user"}
        
        result = strategy.apply([msg_high, msg_medium, msg_low], context=None)
        
        assert result[0]["_keyword_priority_level"] == "high"
        assert result[1]["_keyword_priority_level"] == "medium"
        assert result[2]["_keyword_priority_level"] == "low"
    
    def test_empty_content(self):
        """空内容应有默认分数"""
        strategy = KeywordPriorityStrategy()
        msg = {"content": "", "role": "user"}
        assert strategy.score(msg) == 0.5


class TestTurnImportanceStrategy:
    """轮次重要性策略测试"""
    
    def test_tool_call_scoring(self):
        """工具调用应增加分数"""
        strategy = TurnImportanceStrategy()
        
        msg_no_tool = {"content": "Hello", "role": "assistant"}
        msg_with_tool = {
            "content": "I'll help you",
            "role": "assistant",
            "tool_calls": [{"id": "1", "function": {"name": "read_file"}}]
        }
        
        assert strategy.score(msg_with_tool) > strategy.score(msg_no_tool)
    
    def test_error_in_content(self):
        """错误信息应增加分数"""
        strategy = TurnImportanceStrategy()
        
        msg_normal = {"content": "Here's the result", "role": "assistant"}
        msg_error = {"content": "Error: Exception occurred", "role": "assistant"}
        
        assert strategy.score(msg_error) > strategy.score(msg_normal)
    
    def test_code_block_scoring(self):
        """代码块应增加分数"""
        strategy = TurnImportanceStrategy()
        
        msg_no_code = {"content": "Just a text message", "role": "assistant"}
        msg_with_code = {
            "content": "```python\ndef hello():\n    pass\n```",
            "role": "assistant"
        }
        
        assert strategy.score(msg_with_code) > strategy.score(msg_no_code)


class TestCodeBlockStrategy:
    """代码块压缩策略测试"""
    
    def test_code_block_extraction(self):
        """提取代码块"""
        strategy = CodeBlockStrategy()
        
        content = "Here is code:\n```python\ndef foo():\n    return 1\n```\nEnd"
        blocks = strategy._extract_code_blocks(content)
        
        assert len(blocks) == 1
        assert "def foo" in blocks[0]
    
    def test_smart_code_compression(self):
        """智能代码压缩"""
        strategy = CodeBlockStrategy()
        
        content = """```python
import os
import sys

def hello():
    print("hello")
    print("world")
    return True

class Test:
    def method(self):
        pass
```"""
        
        compressed = strategy._smart_code_compression(content)
        # 压缩后应保留关键行
        assert "import os" in compressed or "import" in compressed
        assert "def hello" in compressed


class TestPathPreservationStrategy:
    """路径保护策略测试"""
    
    def test_unix_path_extraction(self):
        """提取 Unix 路径"""
        strategy = PathPreservationStrategy()
        
        content = "Check /path/to/project/src/main.py"
        paths = strategy.extract_paths(content)
        
        assert len(paths) > 0
        assert any("main.py" in p for p in paths)
    
    def test_windows_path_extraction(self):
        """提取 Windows 路径"""
        strategy = PathPreservationStrategy()
        
        content = r"Reading from C:\Users\test\Documents\file.py"
        paths = strategy.extract_paths(content)
        
        assert len(paths) > 0
    
    def test_path_marking(self):
        """路径标记"""
        strategy = PathPreservationStrategy()
        
        msg = {"content": "Working on /src/app/main.py", "role": "user"}
        result = strategy.apply([msg], context=None)
        
        assert result[0]["_has_paths"] == True


class TestSemanticMergeStrategy:
    """语义合并策略测试"""
    
    def test_similarity_calculation(self):
        """相似度计算"""
        strategy = SemanticMergeStrategy()
        
        s1 = "Hello, how are you?"
        s2 = "Hello, how are you?"
        s3 = "Goodbye, see you later"
        
        sim_same = strategy._calculate_similarity(s1, s2)
        sim_diff = strategy._calculate_similarity(s1, s3)
        
        assert sim_same > sim_diff
        assert sim_same > 0.8
    
    def test_message_merging(self):
        """消息合并"""
        strategy = SemanticMergeStrategy(
            SemanticMergeConfig(similarity_threshold=0.8)
        )
        
        msg1 = {"content": "Hello, how are you?", "role": "user"}
        msg2 = {"content": "Hello, how are you?", "role": "user"}
        msg3 = {"content": "Goodbye", "role": "user"}
        
        result = strategy.compress([msg1, msg2, msg3])
        
        # 前两条应该被合并
        assert len(result) == 2
        assert result[0].get("_merged_from_count") == 2


class TestErrorPreservationStrategy:
    """错误保护策略测试"""
    
    def test_error_extraction(self):
        """错误提取"""
        strategy = ErrorPreservationStrategy()
        
        content = """Traceback (most recent call last):
  File "test.py", line 10, in main
    raise ValueError("test error")
ValueError: test error"""
        
        errors = strategy.extract_errors(content)
        
        assert len(errors) > 0
        assert any("Traceback" in e or "Error" in e for e in errors)
    
    def test_error_marking(self):
        """错误标记"""
        strategy = ErrorPreservationStrategy()
        
        msg_error = {"content": "Error: Exception occurred", "role": "assistant"}
        msg_normal = {"content": "All good", "role": "assistant"}
        
        result = strategy.compress([msg_error, msg_normal])
        
        assert result[0]["_has_error"] == True
        assert result[1]["_has_error"] == False


class TestAdaptiveCompressionStrategy:
    """自适应压缩策略测试"""
    
    def test_tier_determination(self):
        """层级确定"""
        strategy = AdaptiveCompressionStrategy()
        
        assert strategy.determine_tier(5000) == strategy.TIER_NONE
        assert strategy.determine_tier(10000) == strategy.TIER_PRUNE
        assert strategy.determine_tier(25000) == strategy.TIER_LIGHT
        assert strategy.determine_tier(50000) == strategy.TIER_AGGRESSIVE
    
    def test_tier_strategies(self):
        """层级策略选择"""
        strategy = AdaptiveCompressionStrategy()
        
        prune_strategies = strategy.get_tier_strategies(strategy.TIER_PRUNE)
        aggressive_strategies = strategy.get_tier_strategies(strategy.TIER_AGGRESSIVE)
        
        assert "keyword_priority" in prune_strategies
        assert len(aggressive_strategies) > len(prune_strategies)


class TestInstructionResultSeparationStrategy:
    """指令-结果分离策略测试"""
    
    def test_separation(self):
        """指令和结果分离"""
        strategy = InstructionResultSeparationStrategy()
        
        messages = [
            {"role": "assistant", "content": "I'll read the file", "tool_calls": [{"id": "1", "function": {"name": "read_file"}}]},
            {"role": "tool", "tool_call_id": "1", "content": "File contents here"},
        ]
        
        instructions, results = strategy.separate_instruction_result(messages)
        
        assert len(instructions) == 1
        assert len(results) == 1
    
    def test_result_pruning(self):
        """结果裁剪"""
        strategy = InstructionResultSeparationStrategy(
            InstructionResultConfig(preserve_first_n=1, prune_threshold=20)
        )
        
        msg_short = {"role": "tool", "tool_call_id": "1", "content": "Short"}
        msg_long = {"role": "tool", "tool_call_id": "2", "content": "A" * 100}
        
        result = strategy.compress([msg_short, msg_long])
        
        # 短结果应保留，长结果应被裁剪
        assert result[0].get("_result_pruned") == False
        assert result[1].get("_result_pruned") == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
