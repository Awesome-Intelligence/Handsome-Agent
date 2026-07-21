#!/usr/bin/env python3
# 🚪 Access - 🚪 Gateway - 网关核心

"""
Gateway Core - Abstract Interface
Does not directly call Agent, instead sends requests to Brain Service
"""

from abc import ABC, abstractmethod
from typing import Optional, Callable, Awaitable
from dataclasses import dataclass

from .message import StandardMessage, MessageChannel
from common.logging_manager import get_access_logger


logger = get_access_logger("Gateway")


@dataclass
class GatewayConfig:
    """Gateway 配置"""
    name: str = "AgentGateway"
    host: str = "0.0.0.0"
    port: int = 8000
    brain_service_url: str = "http://localhost:8000"
    max_concurrent_sessions: int = 100
    session_timeout_seconds: int = 3600
    enable_cors: bool = True
    api_key: Optional[str] = None


class BaseGateway(ABC):
    """Base class for Gateway"""

    def __init__(self, config: GatewayConfig):
        self.config = config
        self.logger = get_access_logger(self.__class__.__name__)
        self._message_handler: Optional[Callable[[StandardMessage], Awaitable[StandardMessage]]] = None

    @abstractmethod
    async def start(self) -> None:
        pass

    @abstractmethod
    async def stop(self) -> None:
        pass

    @abstractmethod
    async def send_message(self, message: StandardMessage) -> StandardMessage:
        pass

    def set_message_handler(self, handler: Callable[[StandardMessage], Awaitable[StandardMessage]]) -> None:
        self._message_handler = handler

    async def _handle_message(self, message: StandardMessage) -> StandardMessage:
        if self._message_handler is None:
            raise RuntimeError("Message handler not set. Please connect to Brain Service first.")
        self.logger.info(f"Handling message from {message.channel}: {message.user_id}")
        return await self._message_handler(message)


class Gateway(BaseGateway):
    """Gateway 主类 - 协调各渠道适配器"""

    def __init__(self, config: GatewayConfig):
        super().__init__(config)
        # 用 string key 桥接 MessageChannel（旧） 和 Platform（Hermes 新）
        self._adapters: dict[str, "BaseAdapter"] = {}
        self._running = False

    def register_adapter(self, channel_or_adapter, adapter=None) -> None:
        """注册渠道适配器。

        支持两种调用方式：
        - register_adapter(MessageChannel.WEIXIN, adapter)  # 旧风格
        - register_adapter(hermes_adapter)  # 新风格（从 adapter.platform 取 key）
        """
        from .platforms.base import BasePlatformAdapter

        if adapter is None:
            # channel_or_adapter 本身就是 adapter
            adapter = channel_or_adapter
            # Hermes BasePlatformAdapter.platform 是 Platform enum，用 value 作为 string key
            platform = getattr(adapter, "platform", None)
            if platform is not None:
                channel_key = platform.value if hasattr(platform, "value") else str(platform)
            else:
                # 旧风格 BaseAdapter
                channel_key = getattr(adapter, "channel", None)
                channel_key = channel_key.value if hasattr(channel_key, "value") else str(channel_key) if channel_key else None
            if not channel_key:
                raise ValueError("Adapter has no platform or channel attribute")
        else:
            # channel_or_adapter 是 MessageChannel enum 或 string
            channel_key = channel_or_adapter.value if hasattr(channel_or_adapter, "value") else str(channel_or_adapter)

        self._adapters[channel_key] = adapter
        self.logger.info(f"Registered adapter for channel: {channel_key}")

    async def start(self) -> None:
        self.logger.info(f"Starting Gateway: {self.config.name}")
        for key, adapter in self._adapters.items():
            if adapter is not None:
                self.logger.info(f"Starting adapter: {key}")
                await adapter.start()
        self._running = True
        self.logger.info("Gateway started successfully")

    async def stop(self) -> None:
        self.logger.info("Stopping Gateway...")
        for key, adapter in self._adapters.items():
            if adapter is not None:
                await adapter.stop()
        self._running = False
        self.logger.info("Gateway stopped")

    async def send_message(self, message: StandardMessage) -> StandardMessage:
        channel_key = message.channel.value if hasattr(message.channel, "value") else str(message.channel)
        if channel_key not in self._adapters:
            raise ValueError(f"No adapter registered for channel: {channel_key}")
        adapter = self._adapters[channel_key]
        if adapter is None:
            raise ValueError(f"Adapter for {channel_key} is None (registered but not set)")
        return await adapter.send(message)


# 旧的 BaseAdapter（兼容旧渠道） - 不再用于新渠道
class BaseAdapter(ABC):
    """Abstract base class for channel adapters (legacy, for backward compat)."""

    def __init__(self, gateway: BaseGateway, channel: MessageChannel):
        self.gateway = gateway
        self.channel = channel
        self.logger = get_access_logger(f"{__name__}.{channel}")

    @abstractmethod
    async def start(self) -> None:
        pass

    @abstractmethod
    async def stop(self) -> None:
        pass

    @abstractmethod
    async def send(self, message: StandardMessage) -> StandardMessage:
        pass
