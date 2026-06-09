"""Stream Emitter - 流式事件发射器

事件发射器负责收集流式数据并广播到所有注册的消费者。
"""

import time
import asyncio
from queue import Queue, Empty
from threading import Thread
from typing import Optional, Callable, Any

from .events import (
    StreamEvent,
    StreamEventType,
    DeltaEvent,
    ReasoningEvent,
    CompleteEvent,
    ErrorEvent,
    ToolEvent,
)
from .registry import ConsumerRegistry


class StreamEmitter:
    """
    流式事件发射器

    同步发射事件，异步广播到消费者。
    适用于从 LLM 流式回调中发射事件。

    用法::

        emitter = StreamEmitter(registry)

        # 方式1: 自动管理线程
        emitter.start()

        # 模拟 LLM 流式输出
        for chunk in llm_stream():
            emitter.emit_delta(chunk)

        emitter.emit_complete(full_text)
        emitter.stop()

        # 方式2: 手动异步广播
        emitter.emit(DeltaEvent("hello"))
        await emitter.flush()  # 等待广播完成
    """

    def __init__(
        self,
        registry: Optional[ConsumerRegistry] = None,
        auto_start: bool = False,
    ):
        """
        Args:
            registry: 消费者注册表（可选，会自动创建）
            auto_start: 是否在初始化时自动启动
        """
        self._registry = registry or ConsumerRegistry()
        self._queue: Queue = Queue()
        self._running = False
        self._thread: Optional[Thread] = None
        self._interrupt_requested = False  # 中断请求标志

        if auto_start:
            self.start()
    
    @property
    def registry(self) -> ConsumerRegistry:
        """获取消费者注册表"""
        return self._registry
    
    def interrupt(self):
        """请求中断"""
        self._interrupt_requested = True
        # 清空队列，让广播线程尽快退出
        with self._queue.mutex:
            self._queue.queue.clear()
    
    def clear_interrupt(self):
        """清除中断标志"""
        self._interrupt_requested = False
    
    @property
    def is_interrupted(self) -> bool:
        """检查是否请求了中断"""
        return self._interrupt_requested

    def emit(self, event: StreamEvent) -> None:
        """同步发射事件（线程安全）

        Args:
            event: 流式事件
        """
        if event.timestamp == 0:
            event.timestamp = time.time()
        self._queue.put(event)

    def emit_delta(self, text: str, rendered: Optional[str] = None) -> None:
        """发射增量事件

        Args:
            text: 内容文本
            rendered: 渲染后的文本（可选）
        """
        self.emit(DeltaEvent(text, rendered))

    def emit_reasoning(self, text: str) -> None:
        """发射推理事件

        Args:
            text: 推理内容
        """
        self.emit(ReasoningEvent(text))

    def emit_tool_start(self, tool_name: str, tool_input: Optional[dict] = None) -> None:
        """发射工具开始事件

        Args:
            tool_name: 工具名称
            tool_input: 工具输入参数
        """
        self.emit(ToolEvent(
            event_type=StreamEventType.TOOL_START,
            tool_name=tool_name,
            tool_input=tool_input,
        ))

    def emit_tool_end(
        self,
        tool_name: str,
        tool_output: Optional[dict] = None,
    ) -> None:
        """发射工具结束事件

        Args:
            tool_name: 工具名称
            tool_output: 工具输出结果
        """
        self.emit(ToolEvent(
            event_type=StreamEventType.TOOL_END,
            tool_name=tool_name,
            tool_output=tool_output,
        ))

    def emit_complete(
        self,
        text: str,
        usage: Optional[dict] = None,
        reasoning: Optional[str] = None,
    ) -> None:
        """发射完成事件

        Args:
            text: 完整内容
            usage: token 使用统计
            reasoning: 推理过程（如果有）
        """
        self.emit(CompleteEvent(text, usage, reasoning))

    def emit_error(self, message: str, error_type: Optional[str] = None) -> None:
        """发射错误事件

        Args:
            message: 错误消息
            error_type: 错误类型
        """
        self.emit(ErrorEvent(message, error_type))

    def start(self) -> None:
        """启动异步广播线程"""
        if self._running:
            return
        self._running = True
        self._thread = Thread(target=self._broadcast_loop, daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 1.0) -> None:
        """停止广播

        Args:
            timeout: 等待线程结束的超时时间
        """
        self._running = False
        if self._thread:
            self._thread.join(timeout=timeout)
            self._thread = None

    def _broadcast_loop(self) -> None:
        """广播循环（在独立线程中运行）"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            while self._running:
                try:
                    event = self._queue.get(timeout=0.05)
                    loop.run_until_complete(self._broadcast_event(event))
                except Empty:
                    continue
                except Exception as e:
                    print(f"Broadcast error: {e}")
        finally:
            loop.close()

    async def _broadcast_event(self, event: StreamEvent) -> None:
        """异步广播单个事件"""
        try:
            await self._registry.broadcast(event)
        except Exception as e:
            print(f"Error broadcasting event: {e}")

    async def flush(self) -> None:
        """等待队列清空（异步）"""
        while not self._queue.empty():
            await asyncio.sleep(0.05)

    def is_running(self) -> bool:
        """检查广播线程是否运行中"""
        return self._running

    def clear(self) -> None:
        """清空队列"""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except Empty:
                break


class AsyncStreamEmitter:
    """
    异步流式事件发射器

    纯异步实现，适用于已在线程中运行的场景。

    用法::

        emitter = AsyncStreamEmitter(registry)

        async for chunk in llm_stream():
            await emitter.emit_delta(chunk)

        await emitter.emit_complete(full_text)
    """

    def __init__(self, registry: Optional[ConsumerRegistry] = None):
        self._registry = registry or ConsumerRegistry()
        self._queue: asyncio.Queue = asyncio.Queue()

    @property
    def registry(self) -> ConsumerRegistry:
        return self._registry

    async def emit(self, event: StreamEvent) -> None:
        """异步发射事件"""
        if event.timestamp == 0:
            event.timestamp = time.time()
        await self._queue.put(event)

    async def emit_delta(self, text: str, rendered: Optional[str] = None) -> None:
        await self.emit(DeltaEvent(text, rendered))

    async def emit_reasoning(self, text: str) -> None:
        await self.emit(ReasoningEvent(text))

    async def emit_complete(
        self,
        text: str,
        usage: Optional[dict] = None,
        reasoning: Optional[str] = None,
    ) -> None:
        await self.emit(CompleteEvent(text, usage, reasoning))

    async def emit_error(self, message: str, error_type: Optional[str] = None) -> None:
        await self.emit(ErrorEvent(message, error_type))

    async def run(self) -> None:
        """事件消费循环"""
        while True:
            event = await self._queue.get()
            if event is None:
                break
            await self._registry.broadcast(event)

    async def broadcast(self) -> None:
        """启动后台广播任务"""
        asyncio.create_task(self.run())

    async def flush(self) -> None:
        """等待队列清空"""
        while not self._queue.empty():
            await asyncio.sleep(0.05)


def create_stream_emitter(
    include_console: bool = True,
) -> tuple[StreamEmitter, ConsumerRegistry]:
    """
    创建流式发射器（带默认消费者）

    Args:
        include_console: 是否包含控制台消费者

    Returns:
        (emitter, registry) 元组
    """
    from .consumer import ConsoleConsumer

    registry = ConsumerRegistry()
    if include_console:
        registry.register(ConsoleConsumer())

    emitter = StreamEmitter(registry)
    return emitter, registry