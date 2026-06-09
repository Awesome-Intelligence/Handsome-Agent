"""Streaming Output - 带推理过滤的流式输出

集成 StreamingThinkScrubber 和 StreamEmitter，
提供带推理内容分离的流式输出功能。
"""

from typing import Optional, Callable, List
from .emitter import StreamEmitter
from .consumer import StreamConsumer, ConsoleConsumer, BufferedConsumer
from .registry import ConsumerRegistry
from .events import StreamEvent, ReasoningEvent
from .think_scrubber import StreamingThinkScrubber


class StreamingOutput:
    """
    带推理过滤的流式输出器
    
    自动过滤 <think> 等标签，提取推理内容供单独显示。
    
    用法::
    
        output = StreamingOutput()
        output.start()
        
        # 处理流式文本
        for chunk in llm_stream():
            output.emit_delta(chunk)
        
        output.complete()
        output.stop()
    """
    
    def __init__(
        self,
        registry: Optional[ConsumerRegistry] = None,
        console_consumer: bool = True,
        show_thinking: bool = True,
        compact: bool = False,
    ):
        """
        Args:
            registry: 消费者注册表
            console_consumer: 是否添加控制台消费者
            show_thinking: 是否显示推理内容
            compact: 是否使用紧凑模式
        """
        self._registry = registry or ConsumerRegistry()
        self._show_thinking = show_thinking
        self._emitter = StreamEmitter(self._registry)
        self._scrubber = StreamingThinkScrubber()
        
        # 收集的推理内容
        self._thinking_parts: List[str] = []
        
        if console_consumer:
            console = ConsoleConsumer(compact=compact)
            self._registry.register(console)
    
    @property
    def emitter(self) -> StreamEmitter:
        """获取流式发射器"""
        return self._emitter
    
    @property
    def registry(self) -> ConsumerRegistry:
        """获取消费者注册表"""
        return self._registry
    
    def start(self):
        """启动流式输出"""
        self._emitter.start()
        self._scrubber.reset()
        self._thinking_parts.clear()
    
    def stop(self):
        """停止流式输出"""
        self._emitter.stop()
    
    def emit_delta(self, text: str) -> None:
        """
        发射增量文本，自动过滤推理标签
        
        Args:
            text: 文本增量
        """
        if not text:
            return
        
        visible, thinking = self._scrubber.feed(text)
        
        # 发射可见内容
        if visible:
            self._emitter.emit_delta(visible)
        
        # 发射推理内容
        if thinking and self._show_thinking:
            self._thinking_parts.append(thinking)
            self._emitter.emit_reasoning(thinking)
    
    def emit_text(self, text: str) -> None:
        """发射完整文本（非流式）"""
        if not text:
            return
        
        visible, thinking = self._scrubber.feed(text)
        remaining_visible, remaining_thinking = self._scrubber.flush()
        
        full_visible = visible + remaining_visible
        full_thinking = thinking or remaining_thinking
        
        if full_visible:
            self._emitter.emit_delta(full_visible)
        
        if full_thinking and self._show_thinking:
            self._thinking_parts.append(full_thinking)
            self._emitter.emit_reasoning(full_thinking)
    
    def complete(self, final_text: str = ""):
        """完成流式输出"""
        # 刷新剩余内容
        if final_text:
            self.emit_text(final_text)
        else:
            visible, thinking = self._scrubber.flush()
            if visible:
                self._emitter.emit_delta(visible)
            if thinking and self._show_thinking:
                self._thinking_parts.append(thinking)
                self._emitter.emit_reasoning(thinking)
        
        # 发射完成事件
        full_thinking = "\n".join(self._thinking_parts) if self._thinking_parts else None
        self._emitter.emit_complete(
            text=final_text or self._get_accumulated_visible(),
            reasoning=full_thinking
        )
    
    def _get_accumulated_visible(self) -> str:
        """获取累积的可见内容"""
        # 从 BufferedConsumer 获取
        buffered = self._registry.get("buffered")
        if buffered and hasattr(buffered, 'content'):
            return buffered.content
        return ""
    
    def get_thinking(self) -> str:
        """获取累积的推理内容"""
        return "\n".join(self._thinking_parts)
    
    def interrupt(self):
        """请求中断"""
        self._emitter.interrupt()
    
    @property
    def is_interrupted(self) -> bool:
        """检查是否被中断"""
        return self._emitter.is_interrupted


def create_streaming_output(
    console_consumer: bool = True,
    show_thinking: bool = True,
    compact: bool = False,
) -> StreamingOutput:
    """
    创建流式输出器（便捷函数）
    
    Args:
        console_consumer: 是否添加控制台消费者
        show_thinking: 是否显示推理内容
        compact: 是否使用紧凑模式
        
    Returns:
        StreamingOutput 实例
    """
    return StreamingOutput(
        console_consumer=console_consumer,
        show_thinking=show_thinking,
        compact=compact,
    )


# 导出主要组件
__all__ = [
    "StreamingOutput",
    "StreamingThinkScrubber",
    "create_streaming_output",
    "strip_thinking_tags",
    "extract_thinking_content",
    "extract_thinking_tags",
]