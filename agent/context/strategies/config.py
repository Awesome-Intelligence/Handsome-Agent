#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
压缩策略配置类

提供各种压缩策略的配置数据类。
"""

from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class StrategyConfig:
    """策略配置基类"""
    enabled: bool = True
    priority: int = 0


@dataclass
class KeywordPriorityConfig(StrategyConfig):
    """关键词优先级策略配置"""
    high_priority_keywords: list = field(default_factory=lambda: [
        "error", "exception", "failed", "bug", "fix", "crash", "IMPORTANT", "TODO", "FIXME"
    ])
    medium_priority_keywords: list = field(default_factory=lambda: [
        "file", "path", "function", "class", "module", "config", "test", "import"
    ])
    low_priority_keywords: list = field(default_factory=lambda: [
        "ok", "success", "done", "complete", "thanks", "great", "good"
    ])


@dataclass
class TurnImportanceConfig(StrategyConfig):
    """轮次重要性策略配置"""
    tool_call_weight: float = 0.3
    error_weight: float = 0.5
    code_block_weight: float = 0.2
    user_request_weight: float = 0.3
    function_def_weight: float = 0.15
    length_penalty_threshold: int = 5000
    length_penalty: float = 0.2


@dataclass  
class CodeBlockConfig(StrategyConfig):
    """代码块压缩策略配置"""
    max_preserved_lines: int = 20
    preserve_keywords: list = field(default_factory=lambda: [
        "def ", "class ", "import ", "from ", "const ", "let ", "var ", "async ", "await "
    ])
    preserve_comments: list = field(default_factory=lambda: ["TODO", "FIXME", "HACK", "NOTE"])


@dataclass
class PathPreservationConfig(StrategyConfig):
    """路径保护策略配置"""
    file_extensions: list = field(default_factory=lambda: [
        ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".cpp", ".c", ".h", ".hpp",
        ".md", ".json", ".yaml", ".yml", ".toml", ".xml", ".html", ".css", ".sql"
    ])


@dataclass
class SemanticMergeConfig(StrategyConfig):
    """语义合并策略配置"""
    similarity_threshold: float = 0.8
    max_merge_count: int = 3


@dataclass
class ErrorPreservationConfig(StrategyConfig):
    """错误保护策略配置"""
    error_patterns: list = field(default_factory=lambda: [
        r"Traceback \(most recent call last\)",
        r"Error:.*",
        r"Exception:.*",
        r'at (?:line|column) \d+',
        r"Stack trace:.*",
        r"at .+\.py:\d+",
        r"AssertionError:.*"
    ])


@dataclass
class AdaptiveCompressionConfig(StrategyConfig):
    """自适应压缩策略配置"""
    tier_none_max: int = 8000
    tier_prune_max: int = 16000
    tier_light_max: int = 32000
    # 各层级启用的策略
    tier_strategies: Dict[str, list] = field(default_factory=lambda: {
        "none": [],
        "prune": ["keyword_priority", "code_block", "path_preservation"],
        "light": ["keyword_priority", "code_block", "path_preservation", "error_preservation"],
        "aggressive": ["keyword_priority", "turn_importance", "code_block", "path_preservation", "semantic_merge", "error_preservation"],
    })


@dataclass
class InstructionResultConfig(StrategyConfig):
    """指令-结果分离策略配置"""
    prune_threshold: int = 500  # 超过此长度的结果将被裁剪
    preserve_first_n: int = 3  # 保留前N个结果
