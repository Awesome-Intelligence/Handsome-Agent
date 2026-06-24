#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
流式上下文清理器模块

提供流式文本清理功能，用于处理可能包含拆分的记忆上下文标签的流式输出。

主要组件:
- StreamingContextScrubber: 流式输出清理器，处理 memory-context 标签
- ScrubberStats: 统计信息数据类
- build_memory_context_block(): 记忆上下文块构建
- sanitize_context(): 上下文清理工具函数

日志子层：🧹 StreamingScrubber
"""

from __future__ import annotations

import re as _re
from dataclasses import dataclass as _dataclass
from typing import List

from common.logging_manager import get_memory_logger

logger = get_memory_logger("StreamingContextScrubber")


# ============================================================================
# Data Classes
# ============================================================================


@_dataclass
class ScrubberStats:
    """流式清理器统计信息"""
    chunks_processed: int = 0  # 处理的 chunk 数量
    spans_filtered: int = 0  # 过滤的 span 数量
    characters_filtered: int = 0  # 过滤的字符数量


# ============================================================================
# Streaming Context Scrubber
# ============================================================================


class StreamingContextScrubber:
    """
    流式文本的状态化清理器。

    用于处理可能包含拆分的 memory-context 标签跨 chunk 边界的流式文本。
    确保 <memory-context> 和 </memory-context> 标签正确配对，
    不将未闭合的上下文块暴露给用户可见输出。
    """

    _OPEN_TAG: str = "<memory-context>"
    _CLOSE_TAG: str = "</memory-context>"

    def __init__(self) -> None:
        self._in_span: bool = False
        self._buf: str = ""
        self._at_block_boundary: bool = True
        # 统计信息
        self._chunks_processed: int = 0
        self._spans_filtered: int = 0
        self._characters_filtered: int = 0

    def reset(self) -> None:
        """重置清理器状态。"""
        self._in_span = False
        self._buf = ""
        self._at_block_boundary = True
        # 重置统计
        self._chunks_processed = 0
        self._spans_filtered = 0
        self._characters_filtered = 0
        logger.debug("StreamingContextScrubber 已重置")

    def get_stats(self) -> ScrubberStats:
        """获取统计信息"""
        return ScrubberStats(
            chunks_processed=self._chunks_processed,
            spans_filtered=self._spans_filtered,
            characters_filtered=self._characters_filtered,
        )

    def feed(self, text: str) -> str:
        """
        返回文本经过清理后的可见部分。

        Args:
            text: 输入的流式文本片段

        Returns:
            清理后的可见文本
        """
        self._chunks_processed += 1

        if not text:
            return ""
        buf = self._buf + text
        self._buf = ""
        out: List[str] = []

        while buf:
            if self._in_span:
                idx = buf.lower().find(self._CLOSE_TAG)
                if idx == -1:
                    held = self._max_partial_suffix(buf, self._CLOSE_TAG)
                    # 统计过滤的字符（span 内容，不包括可能的部分闭合标签）
                    filtered_chars = len(buf) - held
                    self._characters_filtered += filtered_chars
                    self._buf = buf[-held:] if held else ""
                    return "".join(out)
                # 找到闭合标签，span 结束
                span_content_len = idx
                self._spans_filtered += 1
                self._characters_filtered += span_content_len + len(self._CLOSE_TAG)
                buf = buf[idx + len(self._CLOSE_TAG):]
                self._in_span = False
            else:
                idx = self._find_boundary_open_tag(buf)
                if idx == -1:
                    held = (
                        self._max_pending_open_suffix(buf)
                        or self._max_partial_suffix(buf, self._OPEN_TAG)
                    )
                    if held:
                        self._append_visible(out, buf[:-held])
                        self._buf = buf[-held:]
                    else:
                        self._append_visible(out, buf)
                    return "".join(out)
                if idx > 0:
                    self._append_visible(out, buf[:idx])
                # 统计开标签字符
                self._characters_filtered += len(self._OPEN_TAG)
                buf = buf[idx + len(self._OPEN_TAG):]
                self._in_span = True

        return "".join(out)

    def flush(self) -> str:
        """
        在流结束时发出任何保留的缓冲区内容。

        Returns:
            保留的尾部文本，如果仍在上下文中则返回空字符串
        """
        if self._in_span:
            logger.debug("flush: 丢弃未闭合的上下文块")
            self._buf = ""
            self._in_span = False
            return ""
        tail = self._buf
        self._buf = ""
        return tail

    @staticmethod
    def _max_partial_suffix(buf: str, tag: str) -> int:
        """
        返回 buf 后缀中与 tag 前缀匹配的最大长度（不区分大小写）。

        Args:
            buf: 输入缓冲区
            tag: 目标标签

        Returns:
            匹配的后缀长度
        """
        tag_lower = tag.lower()
        buf_lower = buf.lower()
        max_check = min(len(buf_lower), len(tag_lower) - 1)
        for i in range(max_check, 0, -1):
            if tag_lower.startswith(buf_lower[-i:]):
                return i
        return 0

    def _find_boundary_open_tag(self, buf: str) -> int:
        """
        仅在块状跨度开始处找到开标签。

        Args:
            buf: 输入缓冲区

        Returns:
            标签起始位置，未找到返回 -1
        """
        buf_lower = buf.lower()
        search_start = 0
        while True:
            idx = buf_lower.find(self._OPEN_TAG, search_start)
            if idx == -1:
                return -1
            if self._is_block_boundary(buf, idx) and self._has_block_opener_suffix(buf, idx):
                return idx
            search_start = idx + 1

    def _max_pending_open_suffix(self, buf: str) -> int:
        """
        保持完整的边界标签，直到后续字符确认它。

        Args:
            buf: 输入缓冲区

        Returns:
            应保留的后缀长度
        """
        if not buf.lower().endswith(self._OPEN_TAG):
            return 0
        idx = len(buf) - len(self._OPEN_TAG)
        if not self._is_block_boundary(buf, idx):
            return 0
        return len(self._OPEN_TAG)

    def _has_block_opener_suffix(self, buf: str, idx: int) -> bool:
        """
        检查标签后是否有块分隔符。

        Args:
            buf: 输入缓冲区
            idx: 标签起始位置

        Returns:
            是否有块分隔符
        """
        after_idx = idx + len(self._OPEN_TAG)
        if after_idx >= len(buf):
            return False
        return buf[after_idx] in "\r\n"

    def _is_block_boundary(self, buf: str, idx: int) -> bool:
        """
        检查指定位置是否为块边界。

        Args:
            buf: 输入缓冲区
            idx: 检查位置

        Returns:
            是否为块边界
        """
        if idx == 0:
            return self._at_block_boundary
        preceding = buf[:idx]
        last_newline = preceding.rfind("\n")
        if last_newline == -1:
            return self._at_block_boundary and preceding.strip() == ""
        return preceding[last_newline + 1:].strip() == ""

    def _append_visible(self, out: List[str], text: str) -> None:
        """
        向可见输出追加文本。

        Args:
            out: 输出列表
            text: 要追加的文本
        """
        if not text:
            return
        out.append(text)
        self._update_block_boundary(text)

    def _update_block_boundary(self, text: str) -> None:
        """
        更新块边界状态。

        Args:
            text: 新追加的文本
        """
        last_newline = text.rfind("\n")
        if last_newline != -1:
            self._at_block_boundary = text[last_newline + 1:].strip() == ""
        else:
            self._at_block_boundary = self._at_block_boundary and text.strip() == ""


# ============================================================================
# Utility Functions
# ============================================================================

# 预编译的正则表达式
_INTERNAL_CONTEXT_RE = _re.compile(
    r'<\s*memory-context\s*>[\s\S]*?</\s*memory-context\s*>',
    _re.IGNORECASE,
)
_INTERNAL_NOTE_RE = _re.compile(
    r'\[System note:\s*The following is recalled memory context,\s*NOT new user input\.\s*Treat as (?:informational background data|authoritative reference data[^\]]*)\.\]\s*',
    _re.IGNORECASE,
)


def build_memory_context_block(raw_context: str) -> str:
    """
    将预取的记忆包装在带系统说明的栅格块中。

    Args:
        raw_context: 原始记忆上下文内容

    Returns:
        包装后的记忆上下文块，如果内容为空则返回空字符串
    """
    if not raw_context or not raw_context.strip():
        return ""
    return (
        "<memory-context>\n"
        "[System note: The following is recalled memory context, "
        "NOT new user input. Treat as authoritative reference data — "
        "this is the agent's persistent memory and should inform all responses.]\n\n"
        f"{raw_context}\n"
        "</memory-context>"
    )


def sanitize_context(text: str) -> str:
    """
    从提供者输出中剥离栅格标签、注入的上下文块和系统提示。

    Args:
        text: 提供者的原始输出

    Returns:
        清理后的文本
    """
    text = _INTERNAL_CONTEXT_RE.sub('', text)
    text = _INTERNAL_NOTE_RE.sub('', text)
    return text


# ============================================================================
# Global Scrubber (用于兼容旧代码)
# ============================================================================

# 全局清理器实例
_global_scrubber: StreamingContextScrubber | None = None


def get_global_scrubber() -> StreamingContextScrubber:
    """
    获取全局流式清理器实例。

    Returns:
        全局 StreamingContextScrubber 实例
    """
    global _global_scrubber
    if _global_scrubber is None:
        _global_scrubber = StreamingContextScrubber()
    return _global_scrubber


def reset_global_scrubber() -> None:
    """重置全局清理器"""
    global _global_scrubber
    if _global_scrubber is not None:
        _global_scrubber.reset()
    _global_scrubber = None


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    'ScrubberStats',
    'StreamingContextScrubber',
    'build_memory_context_block',
    'sanitize_context',
    'get_global_scrubber',
    'reset_global_scrubber',
]
