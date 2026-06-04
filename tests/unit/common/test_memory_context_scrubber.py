#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory Context Scrubber Tests
"""

import pytest
import pytest_asyncio
from common.memory_context_scrubber import (
    MemoryContextScrubber,
    ScrubberStats,
    build_memory_context_block,
    sanitize_context,
    get_global_scrubber,
    reset_global_scrubber,
)
from common.streaming_scrubber_wrapper import scrub_stream


class TestMemoryContextScrubber:
    """测试 MemoryContextScrubber"""

    def test_basic_filtering(self):
        """基本过滤测试"""
        scrubber = MemoryContextScrubber()

        # 正常文本应该可见
        result = scrubber.feed("Hello, world!")
        assert result == "Hello, world!"

        # 记忆上下文应该被过滤
        result = scrubber.feed("<memory-context>\nRemember: user likes coffee\n</memory-context>")
        assert result == ""

        # 记忆上下文后的文本应该可见
        result = scrubber.feed("What else?")
        assert result == "What else?"

    def test_partial_tag_handling(self):
        """部分标签处理测试"""
        scrubber = MemoryContextScrubber()

        # 模拟流式传输：部分标签
        result = scrubber.feed("Hello <memor")
        assert result == "Hello "

        # 继续输入
        result = scrubber.feed("y-context>")
        assert result == ""

        # 输入内容
        result = scrubber.feed("Hidden content")
        assert result == ""

        # 结束标签
        result = scrubber.feed("</memory-context>")
        assert result == ""

        # 结束后的文本
        result = scrubber.feed("Visible again")
        assert result == "Visible again"

    def test_streaming_chunks(self):
        """流式块测试"""
        scrubber = MemoryContextScrubber()

        chunks = [
            "<memory",
            "-context",
            ">\n",
            "This is",
            " hidden",
            "\n</memory",
            "-context",
            ">\n",
            "Hello!",
        ]

        visible_parts = []
        for chunk in chunks:
            visible = scrubber.feed(chunk)
            visible_parts.append(visible)

        result = "".join(visible_parts).strip()
        assert result == "Hello!"
        assert scrubber.get_stats().spans_filtered >= 1

    def test_flush_behavior(self):
        """刷新行为测试"""
        scrubber = MemoryContextScrubber()

        # 输入一些可见内容到缓冲区
        scrubber.feed("Hello ")
        scrubber._buf = "Hello "

        # flush 应该返回剩余的可见内容
        trailing = scrubber.flush()
        assert trailing == "Hello "

    def test_flush_in_span(self):
        """span 内刷新测试"""
        scrubber = MemoryContextScrubber()

        # 进入记忆上下文
        scrubber.feed("<memory-context>")

        # 在 span 中 flush 应该返回空字符串
        trailing = scrubber.flush()
        assert trailing == ""
        assert not scrubber.is_in_context()

    def test_reset(self):
        """重置测试"""
        scrubber = MemoryContextScrubber()

        scrubber.feed("<memory-context>hidden</memory-context>visible")
        scrubber.reset()

        # 重置后应该正常工作
        result = scrubber.feed("Hello after reset")
        assert result == "Hello after reset"

    def test_multiple_contexts(self):
        """多个记忆上下文测试"""
        scrubber = MemoryContextScrubber()

        # 第一个上下文
        result = scrubber.feed("Start <memory-context>first</memory-context> middle")
        assert result == "Start  middle"

        # 第二个上下文
        result = scrubber.feed("<memory-context>second</memory-context> end")
        assert result == " end"

    def test_nested_tags_not_expected(self):
        """嵌套标签不应被处理（简单模式）"""
        scrubber = MemoryContextScrubber()

        text = "Hello <memory-context>inner</memory-context> world"
        result = scrubber.feed(text)
        # 由于标签被识别，整个 span 都会被过滤
        assert result in ["Hello ", "Hello  world"]


class TestBuildMemoryContextBlock:
    """测试记忆上下文块构建"""

    def test_empty_content(self):
        """空内容测试"""
        assert build_memory_context_block("") == ""
        assert build_memory_context_block("   ") == ""
        assert build_memory_context_block(None) == ""

    def test_basic_block(self):
        """基本块测试"""
        content = "User likes coffee"
        block = build_memory_context_block(content)

        assert "<memory-context>" in block
        assert "</memory-context>" in block
        assert content in block
        assert "[System note:" in block


class TestSanitizeContext:
    """测试上下文清理"""

    def test_basic_sanitization(self):
        """基本清理测试"""
        text = """Hello world
<memory-context>
Important memory
</memory-context>
Goodbye
"""
        result = sanitize_context(text)
        assert "<memory-context>" not in result
        assert "</memory-context>" not in result
        assert "Hello world" in result
        assert "Goodbye" in result

    def test_inline_context(self):
        """行内上下文测试"""
        text = "Hello <memory-context>hidden</memory-context> world"
        result = sanitize_context(text)
        assert result == "Hello  world"

    def test_no_context(self):
        """无上下文测试"""
        text = "Just normal text"
        result = sanitize_context(text)
        assert result == text


class TestGlobalScrubber:
    """测试全局 Scrubber"""

    def test_singleton(self):
        """单例测试"""
        scrubber1 = get_global_scrubber()
        scrubber2 = get_global_scrubber()
        assert scrubber1 is scrubber2

    def test_reset(self):
        """重置测试"""
        reset_global_scrubber()
        scrubber = get_global_scrubber()
        scrubber.feed("test")
        reset_global_scrubber()

        # 重置后应该可以正常工作
        result = scrubber.feed("Hello")
        assert result == "Hello"


class TestStreamingScrubberWrapper:
    """测试流式 Scrubber 包装器"""

    @pytest.mark.asyncio
    async def test_basic_stream(self):
        """基本流测试"""

        async def mock_stream():
            chunks = [
                "Hello ",
                "<memory-context>hidden</memory-context>",
                "world!",
            ]
            for chunk in chunks:
                yield chunk

        scrubber = MemoryContextScrubber()
        visible_chunks = []
        async for visible in scrub_stream(mock_stream(), scrubber):
            visible_chunks.append(visible)

        result = "".join(visible_chunks)
        assert result == "Hello world!"

    @pytest.mark.asyncio
    async def test_partial_tag_stream(self):
        """部分标签流测试"""

        async def mock_stream():
            chunks = [
                "Hi ",
                "<memory-context",
                ">",
                "secret",
                "</memory-context",
                ">",
                "!",
            ]
            for chunk in chunks:
                yield chunk

        scrubber = MemoryContextScrubber()
        visible_chunks = []
        async for visible in scrub_stream(mock_stream(), scrubber):
            visible_chunks.append(visible)

        result = "".join(visible_chunks)
        assert result == "Hi !"


class TestScrubberStats:
    """测试统计信息"""

    def test_stats_tracking(self):
        """统计跟踪测试"""
        scrubber = MemoryContextScrubber()

        scrubber.feed("Hello ")
        scrubber.feed("<memory-context>hidden</memory-context>")
        scrubber.feed(" world")

        stats = scrubber.get_stats()
        assert stats.chunks_processed == 3
        assert stats.spans_filtered >= 1  # 完整 span 被过滤
        assert stats.characters_filtered > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])