"""Streaming Scrubber Wrapper - 流式响应安全包装器

包装异步迭代器，自动过滤流式响应中的记忆上下文内容。

这个模块提供了一个包装类，可以包装任何异步迭代器，
在流式传输过程中自动应用 MemoryContextScrubber 过滤。

用法::

    # 直接包装
    wrapped = StreamingScrubberWrapper(self.generate_stream(...), scrubber)
    async for chunk in wrapped:
        yield chunk

    # 或使用辅助函数
    async for chunk in scrub_stream(self.generate_stream(...), scrubber):
        yield chunk
"""

from typing import AsyncIterator, TypeVar, Generic, Optional, Callable
from dataclasses import dataclass

from .memory_context_scrubber import MemoryContextScrubber, ScrubberStats


T = TypeVar('T')


@dataclass
class StreamResult(Generic[T]):
    """流式结果"""
    delta: T  # delta 内容
    visible: str  # 可见（过滤后）内容
    stats: ScrubberStats  # 统计信息
    is_final: bool  # 是否是最终块


class StreamingScrubberWrapper(Generic[T]):
    """
    流式响应 Scrubber 包装器

    包装异步迭代器，自动应用记忆上下文过滤：

    1. 逐块处理流式数据
    2. 应用 MemoryContextScrubber 过滤
    3. 返回 (原始 delta, 可见内容, 统计) 元组

    用法::

        scrubber = MemoryContextScrubber()
        wrapped = StreamingScrubberWrapper(stream, scrubber)

        async for result in wrapped:
            if result.is_final:
                log_stats(result.stats)
            if result.visible:
                yield result.visible
    """

    def __init__(
        self,
        stream: AsyncIterator[T],
        scrubber: Optional[MemoryContextScrubber] = None,
        extract_text: Optional[Callable[[T, T], str]] = None,
        initial_content: T = ""
    ):
        """
        初始化包装器

        Args:
            stream: 原始异步迭代器
            scrubber: Scrubber 实例（可选，会自动创建）
            extract_text: 从 chunk 提取文本的函数 (chunk, accumulated) -> str
            initial_content: 累积内容的初始值
        """
        self._stream = stream
        self._scrubber = scrubber or MemoryContextScrubber()
        self._extract_text = extract_text or self._default_extract_text
        self._accumulated = initial_content
        self._done = False

    @staticmethod
    def _default_extract_text(chunk, accumulated) -> str:
        """默认文本提取：从 chunk 获取文本内容"""
        if hasattr(chunk, 'delta'):
            return chunk.delta
        if hasattr(chunk, 'content'):
            return chunk.content
        if isinstance(chunk, dict):
            return chunk.get('delta', chunk.get('content', ''))
        if isinstance(chunk, str):
            return chunk
        return str(chunk)

    def __aiter__(self):
        return self

    async def __anext__(self):
        # 获取下一个 chunk
        try:
            chunk = await self._stream.__anext__()
        except StopAsyncIteration:
            # 处理最后的缓冲内容
            trailing = self._scrubber.flush()
            if trailing:
                self._done = True
                return trailing
            raise StopAsyncIteration

        # 提取文本并应用 scrubber
        text = self._extract_text(chunk, self._accumulated)
        self._accumulated = text
        visible = self._scrubber.feed(text)

        # 检查是否是最终块
        is_final = (
            getattr(chunk, 'finish', False) or
            getattr(chunk, 'finish_reason', None) == 'stop' or
            (isinstance(chunk, dict) and chunk.get('finish', False))
        )

        return StreamResult(
            delta=chunk,
            visible=visible,
            stats=self._scrubber.get_stats(),
            is_final=is_final
        )

    def get_scrubber(self) -> MemoryContextScrubber:
        """获取 Scrubber 实例"""
        return self._scrubber

    def reset(self) -> None:
        """重置内部状态"""
        self._scrubber.reset()
        self._accumulated = ""
        self._done = False


async def scrub_stream(
    stream: AsyncIterator,
    scrubber: Optional[MemoryContextScrubber] = None,
) -> AsyncIterator[str]:
    """
    辅助函数：过滤流式响应，返回可见内容

    用法::

        scrubber = MemoryContextScrubber()
        async for visible in scrub_stream(provider.generate_stream(...), scrubber):
            yield visible
    """
    wrapper = StreamingScrubberWrapper(stream, scrubber)
    async for result in wrapper:
        yield result.visible


async def scrub_stream_with_stats(
    stream: AsyncIterator,
    scrubber: Optional[MemoryContextScrubber] = None,
) -> AsyncIterator[StreamResult]:
    """
    辅助函数：过滤流式响应，返回完整结果

    用法::

        scrubber = MemoryContextScrubber()
        async for result in scrub_stream_with_stats(provider.generate_stream(...), scrubber):
            print(result.visible, result.is_final)
    """
    wrapper = StreamingScrubberWrapper(stream, scrubber)
    async for result in wrapper:
        yield result


def create_safe_stream_wrapper(
    stream: AsyncIterator,
    scrubber: Optional[MemoryContextScrubber] = None,
) -> StreamingScrubberWrapper:
    """
    创建安全的流式包装器（兼容异步迭代器协议）

    这是创建包装器的推荐方式，因为它正确处理异步迭代器协议。
    """
    return StreamingScrubberWrapper(stream, scrubber)


__all__ = [
    "StreamingScrubberWrapper",
    "StreamResult",
    "scrub_stream",
    "scrub_stream_with_stats",
    "create_safe_stream_wrapper",
]