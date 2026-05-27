"""CLI 命令行适配器"""
import sys
from typing import Optional
from ..gateway import BaseAdapter, GatewayConfig, BaseGateway
from ..message import StandardMessage, MessageChannel


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
        print(f"\n🤖 Assistant: {message.content.text}")
        return message
    
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