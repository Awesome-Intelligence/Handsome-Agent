"""Consumer Registry - 消费者注册表

管理流式消费者的注册、注销和查找。
"""

from typing import Dict, List, Optional
from threading import RLock

from .consumer import StreamConsumer


class ConsumerRegistry:
    """消费者注册表

    线程安全的消费者管理器，支持注册、注销、查找和广播。

    用法::

        registry = ConsumerRegistry()

        # 注册消费者
        registry.register(ConsoleConsumer())
        registry.register(WebSocketConsumer())

        # 广播事件
        await registry.broadcast(event)

        # 查找消费者
        console = registry.get("console")
    """

    def __init__(self):
        self._consumers: Dict[str, StreamConsumer] = {}
        self._lock = RLock()

    @property
    def names(self) -> List[str]:
        """获取所有已注册消费者名称"""
        with self._lock:
            return list(self._consumers.keys())

    @property
    def all(self) -> List[StreamConsumer]:
        """获取所有已注册消费者"""
        with self._lock:
            return list(self._consumers.values())

    @property
    def count(self) -> int:
        """获取消费者数量"""
        with self._lock:
            return len(self._consumers)

    def register(self, consumer: StreamConsumer) -> None:
        """注册消费者

        如果同名消费者已存在，会被替换。

        Args:
            consumer: 流式消费者实例
        """
        with self._lock:
            self._consumers[consumer.name] = consumer

    def unregister(self, name: str) -> Optional[StreamConsumer]:
        """注销消费者

        Args:
            name: 消费者名称

        Returns:
            被注销的消费者，如果不存在则返回 None
        """
        with self._lock:
            return self._consumers.pop(name, None)

    def get(self, name: str) -> Optional[StreamConsumer]:
        """获取消费者

        Args:
            name: 消费者名称

        Returns:
            消费者实例，如果不存在则返回 None
        """
        with self._lock:
            return self._consumers.get(name)

    def has(self, name: str) -> bool:
        """检查消费者是否存在

        Args:
            name: 消费者名称
        """
        with self._lock:
            return name in self._consumers

    async def broadcast(self, event) -> None:
        """广播事件到所有消费者

        单个消费者失败不影响其他消费者。

        Args:
            event: 流式事件
        """
        consumers = self.all
        for consumer in consumers:
            try:
                await consumer.on_event(event)
            except Exception as e:
                try:
                    await consumer.on_error(e)
                except Exception:
                    pass

    async def notify_start(self) -> None:
        """通知所有消费者流式开始"""
        consumers = self.all
        for consumer in consumers:
            try:
                await consumer.on_start()
            except Exception:
                pass

    async def notify_end(self) -> None:
        """通知所有消费者流式结束"""
        consumers = self.all
        for consumer in consumers:
            try:
                await consumer.on_end()
            except Exception:
                pass

    def clear(self) -> None:
        """清空所有消费者"""
        with self._lock:
            self._consumers.clear()


class ConsumerScope:
    """消费者作用域

    临时注册消费者，退出作用域时自动注销。
    用于流式调用期间临时添加消费者。

    用法::

        registry = ConsumerRegistry()

        # 临时添加消费者
        async with ConsumerScope(registry, WebSocketConsumer()):
            await registry.broadcast(event)
    """

    def __init__(
        self,
        registry: ConsumerRegistry,
        consumer: StreamConsumer,
        auto_start: bool = True,
        auto_end: bool = True,
    ):
        self._registry = registry
        self._consumer = consumer
        self._auto_start = auto_start
        self._auto_end = auto_end
        self._started = False

    async def __aenter__(self) -> StreamConsumer:
        self._registry.register(self._consumer)
        if self._auto_start:
            await self._consumer.on_start()
            self._started = True
        return self._consumer

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._auto_end and self._started:
            await self._consumer.on_end()
        self._registry.unregister(self._consumer.name)


class ConsumerGroup:
    """消费者组

    将多个消费者分组，方便批量管理。

    用法::

        group = ConsumerGroup("output")
        group.add(ConsoleConsumer())
        group.add(LoggerConsumer(logger))

        registry = ConsumerRegistry()
        registry.register(group)
    """

    def __init__(self, name: str):
        self._name = name
        self._consumers: List[StreamConsumer] = []

    @property
    def name(self) -> str:
        return self._name

    def add(self, consumer: StreamConsumer) -> None:
        """添加消费者到组"""
        self._consumers.append(consumer)

    def remove(self, consumer_name: str) -> None:
        """从组中移除消费者"""
        self._consumers = [c for c in self._consumers if c.name != consumer_name]

    @property
    def consumers(self) -> List[StreamConsumer]:
        """获取组内所有消费者"""
        return list(self._consumers)

    async def on_event(self, event) -> None:
        """向组内所有消费者广播事件"""
        for consumer in self._consumers:
            try:
                await consumer.on_event(event)
            except Exception:
                pass

    async def on_start(self) -> None:
        """通知组内所有消费者开始"""
        for consumer in self._consumers:
            try:
                await consumer.on_start()
            except Exception:
                pass

    async def on_end(self) -> None:
        """通知组内所有消费者结束"""
        for consumer in self._consumers:
            try:
                await consumer.on_end()
            except Exception:
                pass

    async def on_error(self, error: Exception) -> None:
        """通知组内所有消费者错误"""
        for consumer in self._consumers:
            try:
                await consumer.on_error(error)
            except Exception:
                pass