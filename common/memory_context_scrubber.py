"""Memory Context Scrubber - 流式响应记忆内容过滤器

防止记忆上下文在流式响应中泄漏到用户界面。

问题背景：
- 记忆上下文可能以 <memory-context>...</memory-context> 标签形式注入 prompt
- 模型在流式响应时可能在 chunk 边界处输出不完整的标签
- 不完整标签会导致内容泄漏或渲染错误

解决方案：
- 使用状态机检测和处理流式 chunk 中的记忆上下文
- 保留完整标签内的内容用于系统处理，但不显示给用户
- 处理不完整标签，防止内容泄漏

参考 Hermes 的 StreamingContextScrubber 实现。
"""

import re
from typing import Optional
from dataclasses import dataclass

from common.logging_manager import get_system_logger


@dataclass
class ScrubberStats:
    """过滤统计"""
    chunks_processed: int = 0
    chunks_filtered: int = 0
    characters_filtered: int = 0
    spans_filtered: int = 0


class MemoryContextScrubber:
    """
    流式响应记忆上下文过滤器

    使用状态机处理流式 chunk，防止记忆上下文泄漏：

    1. 检测 <memory-context> 标签边界
    2. 处理标签内内容（保留用于内部处理）
    3. 过滤标签后内容（不显示给用户）
    4. 处理不完整/部分标签

    用法::

        scrubber = MemoryContextScrubber()
        for delta in stream:
            visible = scrubber.feed(delta)
            if visible:
                emit(visible)
        trailing = scrubber.flush()
        if trailing:
            emit(trailing)
    """

    # 标签定义
    OPEN_TAG = "<memory-context>"
    CLOSE_TAG = "</memory-context>"

    # 系统提示前缀（用于标识记忆上下文）
    SYSTEM_NOTE_PREFIX = "[System note:"

    def __init__(self):
        self._in_span: bool = False  # 是否在记忆上下文中
        self._buf: str = ""  # 缓冲区
        self._stats = ScrubberStats()
        self._logger = get_system_logger("MemoryContextScrubber")

    def reset(self) -> None:
        """重置状态"""
        self._in_span = False
        self._buf = ""
        self._stats = ScrubberStats()

    def get_stats(self) -> ScrubberStats:
        """获取统计信息"""
        return self._stats

    def feed(self, text: str) -> str:
        """
        处理流式文本块

        Args:
            text: 输入的文本块

        Returns:
            可见（不过滤）的内容
        """
        if not text:
            return ""

        self._stats.chunks_processed += 1
        buf = self._buf + text
        self._buf = ""
        out_parts: list[str] = []

        while buf:
            if self._in_span:
                # 我们在记忆上下文中，寻找结束标签
                close_idx = self._find_tag(buf, self.CLOSE_TAG)
                if close_idx == -1:
                    # 没有找到结束标签
                    self._stats.chunks_filtered += 1
                    # 检查是否有部分结束标签
                    held = self._max_partial_suffix(buf, self.CLOSE_TAG)
                    if held:
                        self._buf = buf[-held:]
                        self._stats.characters_filtered += len(buf) - held
                    else:
                        self._buf = buf[-min(len(buf), 50):]  # 保留最后50字符以防部分标签
                        self._stats.characters_filtered += len(buf) - 50
                    return "".join(out_parts)

                # 找到结束标签
                self._stats.spans_filtered += 1
                self._stats.characters_filtered += close_idx + len(self.CLOSE_TAG)
                buf = buf[close_idx + len(self.CLOSE_TAG):]
                self._in_span = False

            else:
                # 不在记忆中，寻找开始标签（直接查找，不考虑块边界）
                open_idx = self._find_tag(buf, self.OPEN_TAG)
                if open_idx == -1:
                    # 没有开始标签
                    held = self._max_partial_suffix(buf, self.OPEN_TAG)
                    if held:
                        self._append_visible(out_parts, buf[:-held])
                        self._buf = buf[-held:]
                    else:
                        self._append_visible(out_parts, buf)
                    return "".join(out_parts)

                # 找到开始标签
                if open_idx > 0:
                    self._append_visible(out_parts, buf[:open_idx])

                # 进入记忆上下文（跳过标签）
                buf = buf[open_idx + len(self.OPEN_TAG):]
                self._in_span = True

        # 清理结果中的多余空白
        result = "".join(out_parts)
        return result.strip()

    def flush(self) -> str:
        """
        刷新缓冲区

        在流结束时调用，输出任何剩余的可见内容。
        如果仍在记忆上下文中，丢弃未完成的内容（更安全）。

        Returns:
            剩余可见内容
        """
        if self._in_span:
            # 在未关闭的 span 中，最安全的做法是丢弃
            self._logger.debug(
                f"Flushing in unclosed span - discarding {len(self._buf)} chars"
            )
            self._buf = ""
            self._in_span = False
            return ""

        tail = self._buf
        self._buf = ""
        return tail

    def is_in_context(self) -> bool:
        """检查是否正在处理记忆上下文"""
        return self._in_span

    def _find_tag(self, buf: str, tag: str) -> int:
        """查找标签位置（不区分大小写）"""
        return buf.lower().find(tag.lower())

    def _max_partial_suffix(self, buf: str, tag: str) -> int:
        """
        返回最长匹配 tag 前缀的 buf 后缀长度

        用于检测可能的标签片段
        """
        tag_lower = tag.lower()
        buf_lower = buf.lower()
        max_check = min(len(buf_lower), len(tag_lower) - 1)

        for i in range(max_check, 0, -1):
            if tag_lower.startswith(buf_lower[-i:]):
                return i

        return 0

    def _append_visible(self, out: list[str], text: str) -> None:
        """追加可见文本"""
        if text:
            out.append(text)


def build_memory_context_block(content: str) -> str:
    """
    构建记忆上下文块

    用于在 prefetch 时将记忆包装成特殊格式

    Args:
        content: 记忆内容

    Returns:
        包装后的内容
    """
    if not content or not content.strip():
        return ""

    return (
        f"{MemoryContextScrubber.OPEN_TAG}\n"
        f"{MemoryContextScrubber.SYSTEM_NOTE_PREFIX} "
        f"The following is recalled memory context, NOT new user input. "
        f"Treat as authoritative reference data.]\n\n"
        f"{content}\n"
        f"{MemoryContextScrubber.CLOSE_TAG}"
    )


def sanitize_context(text: str) -> str:
    """
    清理文本中的记忆上下文

    用于非流式处理的文本清理

    Args:
        text: 输入文本

    Returns:
        清理后的文本
    """
    # 移除标签
    text = re.sub(
        r'<\s*memory-context\s*>[\s\S]*?<\s*/\s*memory-context\s*>',
        '',
        text,
        flags=re.IGNORECASE
    )

    # 移除系统提示前缀
    text = re.sub(
        r'\[System note:\s*The following is recalled memory context.*?\]\s*',
        '',
        text,
        flags=re.IGNORECASE
    )

    # 清理空白
    text = re.sub(r'\n\n+', '\n\n', text)
    text = text.strip()

    return text


# 全局单例（用于简单场景）
_global_scrubber: Optional[MemoryContextScrubber] = None


def get_global_scrubber() -> MemoryContextScrubber:
    """获取全局 Scrubber 实例"""
    global _global_scrubber
    if _global_scrubber is None:
        _global_scrubber = MemoryContextScrubber()
    return _global_scrubber


def reset_global_scrubber() -> None:
    """重置全局 Scrubber"""
    global _global_scrubber
    if _global_scrubber:
        _global_scrubber.reset()


__all__ = [
    "MemoryContextScrubber",
    "ScrubberStats",
    "build_memory_context_block",
    "sanitize_context",
    "get_global_scrubber",
    "reset_global_scrubber",
]