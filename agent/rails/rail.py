# 🧠 Decision - 🔧 Rail - Rail 基类定义

"""
Rail 机制 - 可插拔的安全检查和控制框架

Rail 是 jiuwenswarm 架构中的核心机制，提供：
1. 可插拔的安全检查
2. Checkpoint 暂停控制
3. 事件驱动的注入

参考 jiuwenswarm 的实现，设计思路：
- 每个 Rail 专注于单一功能
- 通过注册机制添加到 agent
- 在关键节点自动触发回调
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from common.logging_manager import get_decision_logger


class RailPriority(int, Enum):
    """Rail 优先级（数字越大优先级越高）"""
    LOW = 0
    NORMAL = 10
    HIGH = 20
    CRITICAL = 30


@dataclass
class RailContext:
    """Rail 执行上下文"""
    session_id: str
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class RailResult:
    """Rail 执行结果"""
    allowed: bool = True
    error: Optional[str] = None
    modified_args: Optional[Dict[str, Any]] = None
    injected_content: Optional[str] = None
    checkpoint_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class Rail(ABC):
    """
    Rail 基类
    
    所有 Rail 必须继承此类并实现相应的回调方法。
    Rail 在 agent 执行流程的关键节点被触发。
    
    生命周期：
    1. __init__ - 初始化
    2. on_register - 注册时调用（可选）
    3. before_llm_call - LLM 调用前（可选）
    4. after_llm_call - LLM 调用后（可选）
    5. before_tool_call - 工具调用前（可选）
    6. after_tool_call - 工具调用后（可选）
    7. on_checkpoint - Checkpoint 点（可选）
    8. on_interrupt - 中断请求时（可选）
    """
    
    name: str = "base_rail"
    description: str = "Base rail class"
    priority: RailPriority = RailPriority.NORMAL
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.logger = get_decision_logger(self.__class__.__name__, sublayer="rail")
        self._enabled = True
        self._context: Optional[RailContext] = None
    
    @property
    def enabled(self) -> bool:
        """Rail 是否启用"""
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool):
        """设置 Rail 启用状态"""
        self._enabled = value
    
    def set_context(self, context: RailContext):
        """设置执行上下文"""
        self._context = context
    
    def get_context(self) -> Optional[RailContext]:
        """获取执行上下文"""
        return self._context
    
    def on_register(self, agent: Any) -> None:
        """
        注册时调用
        
        Args:
            agent: Agent 实例
        """
        self.logger.debug(f"Rail '{self.name}' registered")
    
    async def before_llm_call(
        self, 
        messages: List[Dict[str, Any]], 
        model: str,
        **kwargs
    ) -> Optional[RailResult]:
        """
        LLM 调用前触发
        
        Args:
            messages: 消息列表
            model: 模型名称
            
        Returns:
            RailResult: 如果返回 allowed=False，会阻止 LLM 调用
        """
        return None
    
    async def after_llm_call(
        self, 
        messages: List[Dict[str, Any]], 
        response: Any,
        **kwargs
    ) -> Optional[RailResult]:
        """
        LLM 调用后触发
        
        Args:
            messages: 消息列表
            response: LLM 响应
            
        Returns:
            RailResult: 如果返回 injected_content，会注入到响应中
        """
        return None
    
    async def before_tool_call(
        self, 
        tool_name: str, 
        args: Dict[str, Any],
        **kwargs
    ) -> Optional[RailResult]:
        """
        工具调用前触发
        
        Args:
            tool_name: 工具名称
            args: 工具参数
            
        Returns:
            RailResult: 如果返回 modified_args，会修改工具参数
        """
        return None
    
    async def after_tool_call(
        self, 
        tool_name: str, 
        args: Dict[str, Any],
        result: Any,
        **kwargs
    ) -> Optional[RailResult]:
        """
        工具调用后触发
        
        Args:
            tool_name: 工具名称
            args: 工具参数
            result: 工具执行结果
            
        Returns:
            RailResult: 如果返回 injected_content，会注入到结果中
        """
        return None
    
    async def on_checkpoint(self, checkpoint_name: str) -> Optional[RailResult]:
        """
        Checkpoint 点触发
        
        Args:
            checkpoint_name: Checkpoint 名称
            
        Returns:
            RailResult: 如果返回 checkpoint_name，会设置暂停点
        """
        return None
    
    async def on_interrupt(self, interrupt_type: str) -> Optional[RailResult]:
        """
        中断请求时触发
        
        Args:
            interrupt_type: 中断类型 (pause/resume/abort)
            
        Returns:
            RailResult: 处理结果
        """
        return None
    
    def on_error(self, error: Exception, context: str = "") -> None:
        """
        错误发生时调用
        
        Args:
            error: 异常对象
            context: 错误上下文
        """
        self.logger.error(f"Rail '{self.name}' error in {context}: {error}")
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name}, enabled={self._enabled})>"
    
    def __lt__(self, other: "Rail") -> bool:
        return self.priority < other.priority
    
    def __eq__(self, other: "Rail") -> bool:
        return self.name == other.name


class InterruptType(str, Enum):
    """中断类型"""
    PAUSE = "pause"
    RESUME = "resume"
    ABORT = "abort"
    CANCEL = "cancel"


__all__ = [
    "Rail",
    "RailPriority",
    "RailContext",
    "RailResult",
    "InterruptType",
]