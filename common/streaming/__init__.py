"""Streaming - 流式输出多消费者架构

提供流式输出的事件定义、消费者接口和发射器。

用法::

    from common.streaming import (
        StreamEmitter,
        ConsumerRegistry,
        ConsoleConsumer,
        WebSocketConsumer,
        create_stream_emitter,
    )

    # 创建发射器
    emitter, registry = create_stream_emitter()

    # 注册更多消费者
    registry.register(WebSocketConsumer())

    # 启动广播
    emitter.start()

    # 模拟 LLM 流式输出
    for chunk in llm_stream():
        emitter.emit_delta(chunk)

    emitter.emit_complete(full_text)
    emitter.stop()

事件类型::

    - StreamEventType.DELTA: 内容增量
    - StreamEventType.REASONING: 推理过程
    - StreamEventType.TOOL_START / TOOL_END: 工具执行
    - StreamEventType.COMPLETE: 完成
    - StreamEventType.ERROR: 错误

消费者类型::

    - ConsoleConsumer: 控制台输出
    - BufferedConsumer: 缓冲收集
    - CallbackConsumer: 自定义回调
    - WebSocketConsumer: Web 前端
    - LoggerConsumer: 日志记录
    - CompositeConsumer: 组合消费者
"""

from .events import (
    StreamEvent,
    StreamEventType,
    DeltaEvent,
    ReasoningEvent,
    ToolEvent,
    CompleteEvent,
    ErrorEvent,
    PlanStartEvent,
    PlanProgressEvent,
    PlanCompleteEvent,
)

from .consumer import (
    StreamConsumer,
    ConsoleConsumer,
    BufferedConsumer,
    CallbackConsumer,
    WebSocketConsumer,
    LoggerConsumer,
    CompositeConsumer,
)

from .registry import (
    ConsumerRegistry,
    ConsumerScope,
    ConsumerGroup,
)

from .emitter import (
    StreamEmitter,
    AsyncStreamEmitter,
    create_stream_emitter,
)

from .think_scrubber import (
    StreamingThinkScrubber,
    strip_thinking_tags,
    extract_thinking_content,
    extract_thinking_tags,
)

from .streaming_output import (
    StreamingOutput,
    create_streaming_output,
)

from .gateway import (
    TUIGateway,
    Session,
    StreamMessage,
    MessageType,
    create_gateway,
)


__all__ = [
    # 事件
    "StreamEvent",
    "StreamEventType",
    "DeltaEvent",
    "ReasoningEvent",
    "ToolEvent",
    "CompleteEvent",
    "ErrorEvent",
    "PlanStartEvent",
    "PlanProgressEvent",
    "PlanCompleteEvent",
    # 消费者
    "StreamConsumer",
    "ConsoleConsumer",
    "BufferedConsumer",
    "CallbackConsumer",
    "WebSocketConsumer",
    "LoggerConsumer",
    "CompositeConsumer",
    # 注册表
    "ConsumerRegistry",
    "ConsumerScope",
    "ConsumerGroup",
    # 发射器
    "StreamEmitter",
    "AsyncStreamEmitter",
    "create_stream_emitter",
    # 推理过滤
    "StreamingThinkScrubber",
    "strip_thinking_tags",
    "extract_thinking_content",
    "extract_thinking_tags",
    # 集成输出
    "StreamingOutput",
    "create_streaming_output",
    # TUI 网关
    "TUIGateway",
    "Session",
    "StreamMessage",
    "MessageType",
    "create_gateway",
]