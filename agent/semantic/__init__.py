#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Semantic Module - 基于 Hermes Holographic 的语义匹配实现

提供两种语义匹配方案：
1. HRR (Holographic Reduced Representations) - 基于相位编码的向量符号架构
2. Enhanced Jaccard - 增强的 Jaccard 相似度（无需 numpy）

参考 Hermes plugins/memory/holographic/ 实现。
"""

from .hrr import (
    encode_text,
    similarity,
    encode_atom,
    encode_fact,
    bundle,
    bind,
    unbind,
    _HAS_NUMPY,
)

from .semantic_retriever import (
    SemanticRetriever,
    SemanticRetriever as ChineseSemanticRetriever,
    RetrievalConfig,
    create_retriever,
)

__all__ = [
    "encode_text",
    "similarity",
    "encode_atom",
    "encode_fact",
    "bundle",
    "bind",
    "unbind",
    "_HAS_NUMPY",
    "SemanticRetriever",
    "ChineseSemanticRetriever",
    "RetrievalConfig",
    "create_retriever",
]
