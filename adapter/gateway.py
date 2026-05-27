"""
Gateway 核心 - 抽象接口
不直接调用 Agent，而是发请求到 Brain Service
"""

from abc import ABC, abstractmethod
from typing import Optional, Callable, Awaitable
from dataclasses import dataclass
import logging

from .message import StandardMessage, MessageChannel


logger = logging.getLogger(__name__)


@dataclass
class GatewayConfig:
    """Gateway 配置"""
    name: str = "HandsomeAgentGateway"
    host: str = "0.0.0.0"
    port: int = 8000
    brain_service_url: str = "http://localhost:8001"
    max_concurrent_sessions: int = 100
    session_timeout_seconds: int = 3600
    enable_cors: bool = True
    api_key: Optional[str] = None


class BaseGateway(ABC):
    """Gateway 抽象基类"""
    
    def __init__(self, config: GatewayConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._message_handler: Optional[Callable[[StandardMessage], Awaitable[StandardMessage]]] = None
    
    @abstractmethod
    async def start(self) -> None:
        """启动 Gateway"""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """停止 Gateway"""
        pass
    
    @abstractmethod
    async def send_message(self, message: StandardMessage) -> StandardMessage:
        """发送消息"""
        pass
    
    def set_message_handler(self, handler: Callable[[StandardMessage], Awaitable[StandardMessage]]) -> None:
        """设置消息处理器 - 由 Brain Service 调用"""
        self._message_handler = handler
    
    async def _handle_message(self, message: StandardMessage) -> StandardMessage:
        """处理消息的内部方法"""
        if self._message_handler is None:
            raise RuntimeError("Message handler not set. Please connect to Brain Service first.")
        
        self.logger.info(f"Handling message from {message.channel}: {message.user_id}")
        return await self._message_handler(message)


class Gateway(BaseGateway):
    """Gateway 主类 - 协调各渠道适配器"""
    
    def __init__(self, config: GatewayConfig):
        super().__init__(config)
        self._adapters: dict[MessageChannel, "BaseAdapter"] = {}
        self._running = False
    
    def register_adapter(self, channel: MessageChannel, adapter: "BaseAdapter") -> None:
        """注册渠道适配器"""
        self._adapters[channel] = adapter
        self.logger.info(f"Registered adapter for channel: {channel}")
    
    async def start(self) -> None:
        """启动 Gateway 和所有适配器"""
        self.logger.info(f"Starting Gateway: {self.config.name}")
        
        for channel, adapter in self._adapters.items():
            self.logger.info(f"Starting adapter: {channel}")
            await adapter.start()
        
        self._running = True
        self.logger.info("Gateway started successfully")
    
    async def stop(self) -> None:
        """停止 Gateway 和所有适配器"""
        self.logger.info("Stopping Gateway...")
        
        for channel, adapter in self._adapters.items():
            await adapter.stop()
        
        self._running = False
        self.logger.info("Gateway stopped")
    
    async def send_message(self, message: StandardMessage) -> StandardMessage:
        """发送消息到指定渠道"""
        channel = message.channel
        
        if channel not in self._adapters:
            raise ValueError(f"No adapter registered for channel: {channel}")
        
        adapter = self._adapters[channel]
        return await adapter.send(message)


class BaseAdapter(ABC):
    """渠道适配器抽象基类"""
    
    def __init__(self, gateway: BaseGateway, channel: MessageChannel):
        self.gateway = gateway
        self.channel = channel
        self.logger = logging.getLogger(f"{__name__}.{channel}")
    
    @abstractmethod
    async def start(self) -> None:
        """启动适配器"""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """停止适配器"""
        pass
    
    @abstractmethod
    async def send(self, message: StandardMessage) -> StandardMessage:
        """发送消息"""
        pass
    
    @abstractmethod
    async def receive(self) -> StandardMessage:
        """接收消息"""
        pass