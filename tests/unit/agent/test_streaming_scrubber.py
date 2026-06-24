#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
StreamingContextScrubber 模块测试

测试覆盖:
- StreamingContextScrubber 类的流式文本清理功能
- build_memory_context_block 函数构建记忆上下文块
- sanitize_context 函数清理提供者输出

注意: <memory-context> 标签必须在块边界处（前面有空行）且后跟换行符才能被识别
"""

import pytest

from agent.memory.streaming_scrubber import (
    StreamingContextScrubber,
    build_memory_context_block,
    sanitize_context,
)


# ============================================================================
# StreamingContextScrubber 类测试
# ============================================================================

class TestStreamingContextScrubber:
    """StreamingContextScrubber 测试套件"""

    @pytest.fixture
    def scrubber(self):
        """创建清理器实例"""
        return StreamingContextScrubber()

    def test_init_state(self, scrubber):
        """测试初始化状态"""
        assert scrubber._in_span is False
        assert scrubber._buf == ""
        assert scrubber._at_block_boundary is True

    def test_reset(self, scrubber):
        """测试重置方法"""
        scrubber.feed("some text")
        scrubber._in_span = True
        scrubber._buf = "partial"
        scrubber._at_block_boundary = False

        scrubber.reset()

        assert scrubber._in_span is False
        assert scrubber._buf == ""
        assert scrubber._at_block_boundary is True

    def test_basic_filtering(self, scrubber):
        """基本过滤测试 - 正确过滤 <memory-context> 标签内容"""
        # 带块边界的记忆上下文应该被过滤
        # 格式: 换行 + <memory-context> + 换行 + 内容 + </memory-context> + 换行
        result = scrubber.feed("\n<memory-context>\nRemember: user likes coffee\n</memory-context>\n")
        # 核心是内容被过滤了
        assert "Remember" not in result

    def test_partial_tag_handling(self, scrubber):
        """部分标签处理测试 - 标签在多个 chunk 中被截断"""
        # 模拟流式传输：先换行建立块边界，然后开始上下文
        result = scrubber.feed("\n")
        assert result == "\n"

        # 继续输入：开标签
        result = scrubber.feed("<memory-context>\n")
        assert result == ""

        # 输入内容应该被隐藏
        result = scrubber.feed("Hidden content\n")
        assert "Hidden" not in result

        # 结束标签
        result = scrubber.feed("</memory-context>")
        assert result == ""

        # 结束后的文本应该可见
        result = scrubber.feed("\nVisible again")
        assert "Visible again" in result

    def test_partial_close_tag(self, scrubber):
        """部分闭合标签处理测试"""
        # 开始上下文
        result = scrubber.feed("\n<memory-context>\n")
        # 可能暴露换行符

        # 部分结束标签
        result = scrubber.feed("Some text </memo")
        assert "Some text" not in result

        # 完成结束标签
        result = scrubber.feed("ry-context>")

        # 之后的内容应该可见
        result = scrubber.feed("\nAfter context")
        assert "After context" in result

    def test_multiple_context_blocks(self, scrubber):
        """多个上下文块测试"""
        result = scrubber.feed("Before first\n")
        assert "Before first" in result

        result = scrubber.feed("\n<memory-context>\nFirst block\n</memory-context>\n")
        # 过滤掉内容
        assert "First block" not in result

        result = scrubber.feed("Middle text\n")
        assert "Middle text" in result

        result = scrubber.feed("\n<memory-context>\nSecond block\n</memory-context>\n")
        assert "Second block" not in result

        result = scrubber.feed("After second\n")
        assert "After second" in result

    def test_nested_tags_not_expected(self, scrubber):
        """嵌套标签测试 - 第一个结束标签会关闭上下文"""
        result = scrubber.feed("\n<memory-context>\nOuter <memory-context>Inner</memory-context>\n</memory-context>\n")
        # 第一个 </memory-context> 会关闭，剩余内容可见
        assert "Outer <memory-context>Inner" not in result

    def test_empty_input(self, scrubber):
        """空输入测试"""
        result = scrubber.feed("")
        assert result == ""

    def test_text_only_input(self, scrubber):
        """纯文本输入测试"""
        result = scrubber.feed("Just some plain text without any tags.")
        assert result == "Just some plain text without any tags."

    def test_incomplete_context_no_close(self, scrubber):
        """未闭合上下文测试 - flush 时应丢弃"""
        # 开始上下文但不闭合
        result = scrubber.feed("\n<memory-context>\nSome content")
        # 可能暴露换行符

        # flush 应该丢弃内容
        result = scrubber.flush()
        assert result == ""

        # 之后的内容应该可见
        result = scrubber.feed("\nNew visible\n")
        assert "New visible" in result

    def test_text_before_and_after_context(self, scrubber):
        """上下文前后的文本测试"""
        result = scrubber.feed("Start\n")
        assert "Start" in result

        result = scrubber.feed("\n<memory-context>\n</memory-context>\n")
        # 内容被过滤

        result = scrubber.feed("End\n")
        assert "End" in result

    def test_tag_case_sensitivity(self, scrubber):
        """标签大小写不敏感测试"""
        result = scrubber.feed("\n<MEMORY-CONTEXT>\nHidden\n</MEMORY-CONTEXT>\n")
        assert "Hidden" not in result

        result = scrubber.feed("\nAfter uppercase tags\n")
        assert "After uppercase tags" in result

    def test_tag_without_block_boundary_not_filtered(self, scrubber):
        """测试标签不在块边界时不会被过滤"""
        # 没有前置换行符，标签不会被识别为开标签
        result = scrubber.feed("Text <memory-context>\n")
        assert "<memory-context>" in result


class TestStreamingContextScrubberStateMachine:
    """状态机行为测试"""

    def test_in_span_state_transitions(self):
        """测试 _in_span 状态转换"""
        scrubber = StreamingContextScrubber()

        assert scrubber._in_span is False

        # 进入上下文
        scrubber.feed("\n<memory-context>\n")
        assert scrubber._in_span is True

        # 离开上下文
        scrubber.feed("</memory-context>")
        assert scrubber._in_span is False

    def test_buffer_management(self):
        """测试 _buf 缓冲区管理"""
        scrubber = StreamingContextScrubber()

        # 部分标签应保留在缓冲区（当标签不完整时）
        result = scrubber.feed("<memor")
        # 完整的 <memory-context> 没有形成，不会进入 buffer
        assert scrubber._buf == "" or "<memor" in scrubber._buf

    def test_block_boundary_tracking(self):
        """测试块边界跟踪"""
        scrubber = StreamingContextScrubber()

        assert scrubber._at_block_boundary is True

        # 添加非空文本后不再在块边界
        scrubber.feed("Some text\n")
        # 取决于实现

        # 重置后回到块边界
        scrubber.reset()
        assert scrubber._at_block_boundary is True

    def test_find_boundary_open_tag(self):
        """测试 _find_boundary_open_tag 方法"""
        scrubber = StreamingContextScrubber()

        # 标签前有换行符（块边界）时应该找到
        buf = "\n<memory-context>\n"
        idx = scrubber._find_boundary_open_tag(buf)
        assert idx == 1

        # 标签后没有换行符时不应该找到
        buf = "\n<memory-context>text"
        idx = scrubber._find_boundary_open_tag(buf)
        assert idx == -1

    def test_max_partial_suffix(self):
        """测试 _max_partial_suffix 方法"""
        # 测试部分匹配
        result = StreamingContextScrubber._max_partial_suffix("<memo", "<memory-context>")
        assert result == 5  # "<memo" 匹配 "<MEMO"

        result = StreamingContextScrubber._max_partial_suffix("</memo", "</memory-context>")
        assert result == 6  # "</memo" 匹配 "</MEMO"

        result = StreamingContextScrubber._max_partial_suffix("xyz", "<memory-context>")
        assert result == 0  # 无匹配


class TestStreamingContextScrubberFlush:
    """flush() 方法测试"""

    def test_flush_outside_span(self):
        """测试在 span 外 flush"""
        scrubber = StreamingContextScrubber()

        scrubber.feed("Some text\n")
        # 缓冲区可能有内容
        scrubber._buf = "buffered text"

        result = scrubber.flush()
        # 应该返回缓冲区内容
        assert result == "buffered text"
        assert scrubber._buf == ""

    def test_flush_inside_span(self):
        """测试在 span 内 flush"""
        scrubber = StreamingContextScrubber()

        scrubber.feed("\n<memory-context>\nSome content")
        assert scrubber._in_span is True

        result = scrubber.flush()
        # span 内 flush 应返回空字符串
        assert result == ""
        assert scrubber._in_span is False
        assert scrubber._buf == ""

    def test_flush_empty_scrubber(self):
        """测试空清理器 flush"""
        scrubber = StreamingContextScrubber()

        result = scrubber.flush()
        assert result == ""


# ============================================================================
# build_memory_context_block 函数测试
# ============================================================================

class TestBuildMemoryContextBlock:
    """build_memory_context_block 函数测试"""

    def test_empty_content(self):
        """空内容返回空字符串"""
        result = build_memory_context_block("")
        assert result == ""

        result = build_memory_context_block("   ")
        assert result == ""

        result = build_memory_context_block(None)
        assert result == ""

    def test_normal_content(self):
        """正常内容正确包装"""
        content = "User prefers dark mode"
        result = build_memory_context_block(content)

        assert "<memory-context>" in result
        assert "[System note:" in result
        assert "recalled memory context" in result
        assert "NOT new user input" in result
        assert "authoritative reference data" in result
        assert content in result
        assert "</memory-context>" in result

    def test_multiline_content(self):
        """多行内容正确处理"""
        content = "Line 1\nLine 2\nLine 3"
        result = build_memory_context_block(content)

        assert "<memory-context>" in result
        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result
        assert "</memory-context>" in result

    def test_special_characters(self):
        """特殊字符正确处理"""
        content = 'Test <tag> & special "chars"'
        result = build_memory_context_block(content)

        assert content in result
        assert "<memory-context>" in result
        assert "</memory-context>" in result


# ============================================================================
# sanitize_context 函数测试
# ============================================================================

class TestSanitizeContext:
    """sanitize_context 函数测试"""

    def test_remove_memory_context_tags(self):
        """正确移除 <memory-context> 标签"""
        text = "Before <memory-context>\nHidden content\n</memory-context> After"
        result = sanitize_context(text)

        assert "Hidden content" not in result
        assert "Before" in result
        assert "After" in result

    def test_remove_system_note(self):
        """正确移除 [System note:...] 提示（特定格式）"""
        # 这是 build_memory_context_block 生成的格式
        text = "[System note: The following is recalled memory context, NOT new user input. Treat as authoritative reference data — this is the agent's persistent memory and should inform all responses.]\nVisible text"
        result = sanitize_context(text)

        assert "System note" not in result
        assert "recalled memory context" not in result
        assert "Visible text" in result

    def test_remove_system_note_variant(self):
        """移除系统提示的另一种变体"""
        text = "[System note: The following is recalled memory context, NOT new user input. Treat as informational background data.]\nSome text"
        result = sanitize_context(text)

        assert "System note" not in result
        assert "Some text" in result

    def test_combined_tags_and_notes(self):
        """移除标签和提示的组合"""
        text = "Start <memory-context>\nContent\n</memory-context> [System note: The following is recalled memory context, NOT new user input. Treat as authoritative reference data — this is the agent's persistent memory and should inform all responses.] End"
        result = sanitize_context(text)

        assert "Content" not in result
        assert "System note" not in result
        assert "Start" in result
        assert "End" in result

    def test_no_tags_present(self):
        """无标签时保持原样"""
        text = "Plain text without any tags"
        result = sanitize_context(text)

        assert result == text

    def test_empty_string(self):
        """空字符串处理"""
        result = sanitize_context("")
        assert result == ""

    def test_case_insensitive_removal(self):
        """大小写不敏感移除"""
        text = "Text <MEMORY-CONTEXT>Hidden</MEMORY-CONTEXT> End"
        result = sanitize_context(text)

        assert "Hidden" not in result
        assert "Text" in result
        assert "End" in result

    def test_multiline_context(self):
        """多行上下文移除"""
        text = """Start
<memory-context>
Line 1
Line 2
Line 3
</memory-context>
End"""
        result = sanitize_context(text)

        assert "Line 1" not in result
        assert "Line 2" not in result
        assert "Line 3" not in result
        assert "Start" in result
        assert "End" in result


# ============================================================================
# 集成测试
# ============================================================================

class TestStreamingScrubberIntegration:
    """流式清理器集成测试"""

    def test_full_streaming_simulation(self):
        """模拟完整流式处理"""
        scrubber = StreamingContextScrubber()
        chunks = [
            "Hello, I'm an AI",
            ".\n",
            "\n<memory-context>\n",
            "This is hidden",
            " content.\n",
            "</memory-context>",
            "\n",
            "Now visible.\n",
        ]

        results = []
        for chunk in chunks:
            result = scrubber.feed(chunk)
            results.append(result)

        # 验证部分可见
        visible_text = "".join(results)
        assert "Hello, I'm an AI." in visible_text
        assert "This is hidden" not in visible_text
        assert "Now visible." in visible_text

    def test_flush_after_stream(self):
        """流结束后 flush"""
        scrubber = StreamingContextScrubber()

        scrubber.feed("Some text\n")
        scrubber.feed("\n<memory-context>\n")
        scrubber.feed("Hidden")

        # flush 应该丢弃隐藏内容
        result = scrubber.flush()
        assert result == ""

        # 新的输入应该可见
        result = scrubber.feed("\nNew visible\n")
        assert "New visible" in result

    def test_multiple_flush_calls(self):
        """多次 flush 调用"""
        scrubber = StreamingContextScrubber()

        # 第一次 flush
        result1 = scrubber.flush()
        assert result1 == ""

        # 多次 flush 应该安全
        result2 = scrubber.flush()
        assert result2 == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
