"""CLI 命令行适配器"""
import sys
import asyncio
from typing import Optional, AsyncIterator
from ..gateway import BaseAdapter, GatewayConfig, BaseGateway
from ..message import StandardMessage, MessageChannel

# 延迟导入避免循环依赖
_streaming_printed = False


def _get_streaming_printer():
    """延迟导入流式打印函数"""
    global _streaming_printed
    if not _streaming_printed:
        from cli.cli_output import StreamingPrinter, print_stream_start, print_stream_chunk, print_stream_end
        _streaming_printed = True
    from cli.cli_output import StreamingPrinter, print_stream_start, print_stream_chunk, print_stream_end
    return StreamingPrinter, print_stream_start, print_stream_chunk, print_stream_end


class CLIAdapter(BaseAdapter):
    """命令行适配器"""

    def __init__(self, gateway: BaseGateway, config: GatewayConfig, user_id: str = "cli_user"):
        super().__init__(gateway, MessageChannel.CLI)
        self.config = config
        self.user_id = user_id
        self.session_id = "cli_session"
        self._running = False

    async def start(self) -> None:
        """启动 CLI 适配器"""
        self._running = True
        self.logger.info("CLI adapter started")

    async def stop(self) -> None:
        """停止 CLI 适配器"""
        self._running = False

    async def send(self, message: StandardMessage) -> StandardMessage:
        """发送消息 - 打印到控制台"""
        # 检查是否为流式响应
        if message.metadata.get("is_streaming"):
            await self._send_streaming(message)
        else:
            print(f"\n🤖 Assistant: {message.content.text}")
        return message

    async def _send_streaming(self, message: StandardMessage) -> None:
        """流式发送消息 - 逐步打印到控制台"""
        StreamingPrinter, print_stream_start, print_stream_chunk, print_stream_end = _get_streaming_printer()

        # 获取流式内容来源
        stream_chunks = message.metadata.get("stream_chunks", [])
        stream_async = message.metadata.get("stream_async")

        printer = StreamingPrinter(prefix="🤖")

        if stream_async and hasattr(stream_async, "__aiter__"):
            # 异步迭代器模式
            printer.start()
            try:
                async for chunk in stream_async:
                    delta = chunk.get("delta", "") or chunk.get("content", "")
                    if delta:
                        printer.print(delta)
            except Exception as e:
                self.logger.error(f"Streaming error: {e}")
            finally:
                printer.finish()
        elif stream_chunks:
            # 预加载的 chunks 列表模式
            printer.start()
            for chunk in stream_chunks:
                delta = chunk.get("delta", "") or chunk.get("content", "")
                if delta:
                    printer.print(delta)
            printer.finish()
        else:
            # 降级：直接打印文本
            print(f"\n🤖 Assistant: {message.content.text}")

    async def receive(self) -> StandardMessage:
        """接收消息 - 从控制台读取"""
        try:
            user_input = input("\n👤 You: ")
            if user_input.lower() in ['exit', 'quit', 'q']:
                self._running = False
                return None

            return StandardMessage(
                channel=MessageChannel.CLI,
                user_id=self.user_id,
                session_id=self.session_id,
                content={"type": "text", "text": user_input},
            )
        except (EOFError, KeyboardInterrupt):
            self._running = False
            return None

    async def run_interactive(self) -> None:
        """运行交互式 CLI"""
        print("=" * 50)
        print("  Handsome Agent CLI")
        print("  Type 'exit' to quit")
        print("=" * 50)

        await self.start()

        while self._running:
            message = await self.receive()
            if message is None:
                break
            if not message.content.text:
                continue

            response = await self.gateway._handle_message(message)
            await self.send(response)

        await self.stop()
        print("\nGoodbye!")