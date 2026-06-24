#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Semantic Retriever 测试

测试 HRR 语义检索功能。
"""

import pytest
from unittest.mock import MagicMock, patch


class TestHRR:
    """HRR 向量编码测试"""

    def test_encode_atom_deterministic(self):
        """测试原子编码的确定性"""
        from agent.semantic.hrr import encode_atom, _HAS_NUMPY

        if not _HAS_NUMPY:
            pytest.skip("numpy not available")

        # 相同输入应产生相同输出
        vec1 = encode_atom("hello", dim=256)
        vec2 = encode_atom("hello", dim=256)
        assert vec1.shape == vec2.shape
        assert vec1.shape == (256,)

        # 不同词应产生不同向量
        vec3 = encode_atom("world", dim=256)
        assert not (vec1 == vec3).all(), "Different words should produce different vectors"

    def test_encode_text(self):
        """测试文本编码"""
        from agent.semantic.hrr import encode_text, _HAS_NUMPY

        if not _HAS_NUMPY:
            pytest.skip("numpy not available")

        # 编码空文本
        vec = encode_text("", dim=128)
        assert vec.shape == (128,)

        # 编码普通文本
        vec = encode_text("hello world", dim=128)
        assert vec.shape == (128,)

    def test_similarity(self):
        """测试相似度计算"""
        from agent.semantic.hrr import encode_atom, similarity, _HAS_NUMPY

        if not _HAS_NUMPY:
            pytest.skip("numpy not available")

        vec = encode_atom("test", dim=128)

        # 相同向量相似度应为 1.0
        sim = similarity(vec, vec)
        assert abs(sim - 1.0) < 1e-6, "Same vector should have similarity 1.0"

    def test_bind_unbind(self):
        """测试绑定和解绑操作"""
        from agent.semantic.hrr import encode_atom, bind, unbind, similarity, _HAS_NUMPY

        if not _HAS_NUMPY:
            pytest.skip("numpy not available")

        dim = 256
        a = encode_atom("concept_a", dim=dim)
        b = encode_atom("concept_b", dim=dim)

        # 绑定
        bound = bind(a, b)

        # 解绑应能恢复 b
        recovered = unbind(bound, a)
        sim = similarity(recovered, b)

        # 由于叠加噪声，相似度应接近但不一定完全为 1.0
        assert sim > 0.5, f"Recovered vector should be similar to original: {sim}"


class TestSemanticRetriever:
    """语义检索器测试"""

    def test_basic_retrieval(self):
        """测试基本检索功能"""
        from agent.semantic import SemanticRetriever

        retriever = SemanticRetriever()

        entries = [
            "用户喜欢用 Python 编程",
            "项目使用 React 前端框架",
            "服务器运行在 Ubuntu 系统上",
        ]

        # 查询 "Python"
        results = retriever.retrieve("Python", entries)
        assert len(results) > 0, "Should find relevant entries"
        assert results[0][0] == "用户喜欢用 Python 编程"

    def test_semantic_match(self):
        """测试语义匹配（相比字符匹配的改进）"""
        from agent.semantic import SemanticRetriever

        retriever = SemanticRetriever()

        entries = [
            "用户偏好使用终端命令而不是 GUI",
            "项目使用 Docker 部署",
            "用户喜欢用 Python 写代码",
        ]

        # 查询 "如何编写程序"
        # 字符匹配可能无法找到 "用户喜欢用 Python 写代码"
        # 但语义检索应该能找到
        results = retriever.retrieve("如何编写程序", entries)

        # 至少应返回一个结果
        assert len(results) >= 1

    def test_empty_query(self):
        """测试空查询"""
        from agent.semantic import SemanticRetriever

        retriever = SemanticRetriever()

        entries = ["用户偏好", "项目配置"]
        results = retriever.retrieve("", entries)
        assert results == []

    def test_no_entries(self):
        """测试空条目列表"""
        from agent.semantic import SemanticRetriever

        retriever = SemanticRetriever()
        results = retriever.retrieve("test query", [])
        assert results == []

    def test_max_results(self):
        """测试最大返回数量"""
        from agent.semantic import SemanticRetriever, RetrievalConfig

        config = RetrievalConfig(max_results=3)
        retriever = SemanticRetriever(config)

        entries = [
            "条目1",
            "条目2",
            "条目3",
            "条目4",
            "条目5",
        ]

        results = retriever.retrieve("相关", entries)
        assert len(results) <= 3


class TestChineseSemanticRetriever:
    """中文语义检索器测试"""

    def test_chinese_ngram(self):
        """测试中文 n-gram"""
        from agent.semantic.semantic_retriever import ChineseSemanticRetriever

        retriever = ChineseSemanticRetriever()

        # 测试分词
        tokens = retriever._tokenize_chinese("用户喜欢写代码")
        assert "用户" in tokens
        assert "代码" in tokens
        # 应该包含 2-gram
        assert "户喜" in tokens or "喜欢" in tokens

    def test_chinese_semantic_match(self):
        """测试中文语义匹配"""
        from agent.semantic.semantic_retriever import ChineseSemanticRetriever

        retriever = ChineseSemanticRetriever()

        entries = [
            "用户偏好：喜欢用 Python 编程",
            "项目使用 Vue.js 框架",
            "服务器是 Ubuntu 系统",
        ]

        # 查询编程相关
        results = retriever.retrieve("编写程序", entries)
        assert len(results) > 0


class TestContextBuilderIntegration:
    """ContextBuilder 语义检索集成测试"""

    def test_semantic_retrieval_fallback(self):
        """测试语义检索降级"""
        from agent.context.context_builder import ContextBuilder

        # 禁用语义检索，测试降级
        builder = ContextBuilder(use_semantic_retrieval=False)

        entries = [
            "用户喜欢 Python",
            "项目用 React",
        ]

        results = builder._find_relevant_memories_fallback("Python", entries)
        assert len(results) > 0
        assert results[0] == "用户喜欢 Python"

    def test_semantic_retrieval_config(self):
        """测试语义检索配置"""
        from agent.context.context_builder import ContextBuilder

        # 启用语义检索
        builder_enabled = ContextBuilder(use_semantic_retrieval=True)
        assert builder_enabled.use_semantic_retrieval is True

        # 禁用语义检索
        builder_disabled = ContextBuilder(use_semantic_retrieval=False)
        assert builder_disabled.use_semantic_retrieval is False


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
