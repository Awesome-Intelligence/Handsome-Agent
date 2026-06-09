"""Stream Consumer - 流式消费者接口和实现

定义消费者接口和常用消费者实现。
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Any
from .events import StreamEvent, StreamEventType, DeltaEvent, CompleteEvent


class StreamConsumer(ABC):
    """流式消费者基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """消费者名称（唯一标识）"""
        pass

    @abstractmethod
    async def on_event(self, event: StreamEvent) -> None:
        """处理流式事件"""
        pass

    async def on_start(self) -> None:
        """流式开始回调（可选实现）"""
        pass

    async def on_end(self) -> None:
        """流式结束回调（可选实现）"""
        pass

    async def on_error(self, error: Exception) -> None:
        """错误处理（可选实现）"""
        pass


class ConsoleConsumer(StreamConsumer):
    """控制台消费者 - 实时输出到终端"""

    # ANSI 颜色
    C_GRAY = "\033[90m"
    C_BLUE = "\033[94m"
    C_GREEN = "\033[92m"
    C_YELLOW = "\033[93m"
    C_RED = "\033[91m"
    C_CYAN = "\033[96m"
    C_RESET = "\033[0m"
    
    # 工具状态图标
    ICON_TOOL = "🔧"
    ICON_RUNNING = "⚡"
    ICON_SUCCESS = "✅"
    ICON_ERROR = "❌"
    ICON_START = "▶"

    def __init__(
        self,
        prefix: str = "",
        suffix: str = "",
        color: Optional[str] = None,
        show_icons: bool = True,
        compact: bool = False,
    ):
        """
        Args:
            prefix: 输出前缀
            suffix: 输出后缀
            color: ANSI 颜色代码（如 "\\033[32m"）
            show_icons: 是否显示图标
            compact: 紧凑模式（单行输出）
        """
        self._prefix = prefix
        self._suffix = suffix
        self._color = color
        self._show_icons = show_icons
        self._compact = compact
        self._current_tool: Optional[str] = None

    @property
    def name(self) -> str:
        return "console"

    async def on_event(self, event: StreamEvent) -> None:
        if event.type == StreamEventType.DELTA:
            text = event.text or ""
            if self._color:
                print(f"{self._color}{self._prefix}{text}{self._suffix}\033[0m", end="", flush=True)
            else:
                print(f"{self._prefix}{text}{self._suffix}", end="", flush=True)
                
        elif event.type == StreamEventType.REASONING:
            text = event.text or ""
            if self._show_icons:
                print(f"{self.C_GRAY}[🤔] {text}{self.C_RESET}", end="", flush=True)
            else:
                print(f"{self.C_GRAY}{text}{self.C_RESET}", end="", flush=True)
                
        elif event.type == StreamEventType.TOOL_START:
            tool_name = event.data.get('tool_name', 'unknown')
            params = event.data.get('tool_input', {})
            self._current_tool = tool_name
            
            if self._compact:
                if self._show_icons:
                    print(f" {self.C_CYAN}{self.ICON_RUNNING} {tool_name}{self.C_RESET}", end="", flush=True)
                else:
                    print(f" {self.C_CYAN}[tool] {tool_name}{self.C_RESET}", end="", flush=True)
            else:
                params_str = self._format_params(params)
                if self._show_icons:
                    print(f"\n{self.C_BLUE}{self.ICON_TOOL} 工具开始: {tool_name}{self.C_RESET}")
                    if params_str:
                        print(f"   参数: {params_str}")
                else:
                    print(f"\n{self.C_BLUE}┌─ Tool: {tool_name}{self.C_RESET}")
                    if params_str:
                        print(f"   Args: {params_str}")
                    print(f"{self.C_BLUE}└{'─' * 40}{self.C_RESET}")
                    
        elif event.type == StreamEventType.TOOL_END:
            tool_name = event.data.get('tool_name', 'unknown')
            output = event.data.get('tool_output', {})
            self._current_tool = None
            
            if self._compact:
                if self._show_icons:
                    print(f" {self.C_GREEN}{self.ICON_SUCCESS}{self.C_RESET}", flush=True)
                else:
                    print(f" {self.C_GREEN}[done]{self.C_RESET}", flush=True)
            else:
                result_str = self._format_result(output)
                if self._show_icons:
                    print(f"{self.C_GREEN}{self.ICON_SUCCESS} 工具完成: {tool_name}{self.C_RESET}")
                    if result_str:
                        print(f"   结果: {result_str}")
                else:
                    print(f"{self.C_GREEN}└─ Done: {tool_name}{self.C_RESET}")
                    
        elif event.type == StreamEventType.COMPLETE:
            print()  # 换行
            
        elif event.type == StreamEventType.ERROR:
            error_type = event.data.get('error_type', 'Error')
            if self._show_icons:
                print(f"\n{self.C_RED}{self.ICON_ERROR} {error_type}: {event.message}{self.C_RESET}")
            else:
                print(f"\n{self.C_RED}[error] {event.message}{self.C_RESET}")

    def _format_params(self, params: dict) -> str:
        """格式化参数显示"""
        if not params:
            return ""
        if isinstance(params, dict):
            # 简化显示，只显示前几个参数
            items = list(params.items())[:3]
            parts = [f"{k}={self._truncate(str(v), 30)}" for k, v in items]
            suffix = "..." if len(params) > 3 else ""
            return ", ".join(parts) + suffix
        return self._truncate(str(params), 50)
    
    def _format_result(self, result: dict) -> str:
        """格式化结果显示"""
        if not result:
            return ""
        if isinstance(result, dict):
            # 检查是否有 success 或 error 字段
            if 'success' in result:
                return "success=True" if result['success'] else "success=False"
            if 'error' in result:
                return f"error: {self._truncate(str(result['error']), 50)}"
            # 显示前几个键
            items = list(result.items())[:2]
            parts = [f"{k}={self._truncate(str(v), 25)}" for k, v in items]
            suffix = "..." if len(result) > 2 else ""
            return ", ".join(parts) + suffix
        return self._truncate(str(result), 50)
    
    def _truncate(self, s: str, max_len: int) -> str:
        """截断字符串"""
        if len(s) > max_len:
            return s[:max_len-3] + "..."
        return s

    async def on_start(self) -> None:
        if self._compact:
            print(f"{self.C_GRAY}[stream]{self.C_RESET}", end="", flush=True)
        else:
            print(f"{self.C_GRAY}┌{'─' * 50}┐{self.C_RESET}")
            print(f"{self.C_GRAY}│ Stream started{' ' * 33}│{self.C_RESET}")
            print(f"{self.C_GRAY}└{'─' * 50}┘{self.C_RESET}")

    async def on_end(self) -> None:
        if not self._compact:
            print(f"{self.C_GRAY}┌{'─' * 50}┐{self.C_RESET}")
            print(f"{self.C_GRAY}│ Stream completed{' ' * 30}│{self.C_RESET}")
            print(f"{self.C_GRAY}└{'─' * 50}┘{self.C_RESET}")


class BufferedConsumer(StreamConsumer):
    """缓冲消费者 - 收集所有内容后一次性输出"""

    def __init__(self):
        self._buffer: str = ""
        self._reasoning_buffer: str = ""
        self._complete: bool = False

    @property
    def name(self) -> str:
        return "buffered"

    @property
    def content(self) -> str:
        """获取累积的内容"""
        return self._buffer

    @property
    def reasoning(self) -> str:
        """获取累积的推理内容"""
        return self._reasoning_buffer

    @property
    def is_complete(self) -> bool:
        return self._complete

    async def on_event(self, event: StreamEvent) -> None:
        if event.type == StreamEventType.DELTA:
            self._buffer += event.text or ""
        elif event.type == StreamEventType.REASONING:
            self._reasoning_buffer += event.text or ""
        elif event.type == StreamEventType.COMPLETE:
            self._complete = True

    def reset(self) -> None:
        """重置缓冲区"""
        self._buffer = ""
        self._reasoning_buffer = ""
        self._complete = False


class CallbackConsumer(StreamConsumer):
    """回调消费者 - 将事件转发到自定义回调"""

    def __init__(
        self,
        name: str,
        on_delta: Optional[callable] = None,
        on_reasoning: Optional[callable] = None,
        on_tool: Optional[callable] = None,
        on_complete: Optional[callable] = None,
        on_error: Optional[callable] = None,
    ):
        self._name = name
        self._on_delta = on_delta
        self._on_reasoning = on_reasoning
        self._on_tool = on_tool
        self._on_complete = on_complete
        self._on_error = on_error

    @property
    def name(self) -> str:
        return self._name

    async def on_event(self, event: StreamEvent) -> None:
        if event.type == StreamEventType.DELTA:
            if self._on_delta:
                self._on_delta(event.text or "", event)
        elif event.type == StreamEventType.REASONING:
            if self._on_reasoning:
                self._on_reasoning(event.text or "", event)
        elif event.type in (StreamEventType.TOOL_START, StreamEventType.TOOL_END):
            if self._on_tool:
                self._on_tool(event)
        elif event.type == StreamEventType.COMPLETE:
            if self._on_complete:
                self._on_complete(event)


class WebSocketConsumer(StreamConsumer):
    """WebSocket 消费者 - 推送事件到 Web 前端"""

    def __init__(self, connections: List[Any] = None):
        """
        Args:
            connections: WebSocket 连接列表，每个连接需要有 send_json 方法
        """
        self._connections = connections or []

    @property
    def name(self) -> str:
        return "websocket"

    def add_connection(self, conn: Any) -> None:
        """添加 WebSocket 连接"""
        self._connections.append(conn)

    def remove_connection(self, conn: Any) -> None:
        """移除 WebSocket 连接"""
        if conn in self._connections:
            self._connections.remove(conn)

    async def on_event(self, event: StreamEvent) -> None:
        payload = event.to_dict()
        for conn in self._connections:
            try:
                await conn.send_json(payload)
            except Exception:
                # 连接断开时移除
                self.remove_connection(conn)

    async def on_start(self) -> None:
        await self._broadcast({"type": "stream.start", "data": {}})

    async def on_end(self) -> None:
        await self._broadcast({"type": "stream.end", "data": {}})

    async def _broadcast(self, payload: dict) -> None:
        for conn in list(self._connections):
            try:
                await conn.send_json(payload)
            except Exception:
                self.remove_connection(conn)


class LoggerConsumer(StreamConsumer):
    """日志消费者 - 将流式输出记录到日志"""

    def __init__(self, logger):
        self._logger = logger
        self._buffer = ""

    @property
    def name(self) -> str:
        return "logger"

    async def on_event(self, event: StreamEvent) -> None:
        if event.type == StreamEventType.DELTA:
            self._buffer += event.text or ""
        elif event.type == StreamEventType.COMPLETE:
            self._logger.info(f"Stream complete: {self._buffer[:500]}...")
            self._buffer = ""


class CompositeConsumer(StreamConsumer):
    """组合消费者 - 将多个消费者组合在一起"""

    def __init__(self, consumers: List[StreamConsumer] = None):
        self._consumers = consumers or []

    @property
    def name(self) -> str:
        return "composite"

    def add(self, consumer: StreamConsumer) -> None:
        """添加消费者"""
        self._consumers.append(consumer)

    def remove(self, name: str) -> None:
        """移除消费者"""
        self._consumers = [c for c in self._consumers if c.name != name]

    async def on_event(self, event: StreamEvent) -> None:
        for consumer in self._consumers:
            try:
                await consumer.on_event(event)
            except Exception as e:
                # 单个消费者失败不影响其他消费者
                await consumer.on_error(e)

    async def on_start(self) -> None:
        for consumer in self._consumers:
            try:
                await consumer.on_start()
            except Exception:
                pass

    async def on_end(self) -> None:
        for consumer in self._consumers:
            try:
                await consumer.on_end()
            except Exception:
                pass

    async def on_error(self, error: Exception) -> None:
        for consumer in self._consumers:
            try:
                await consumer.on_error(error)
            except Exception:
                pass