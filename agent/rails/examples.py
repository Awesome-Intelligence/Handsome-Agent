# 🧠 Decision - 🔧 Rail - Rail 集成示例

"""
Rail 集成示例

展示如何在 Agent 中集成 Rail 机制：

1. 基本集成（推荐方式）
2. 在工具调用中集成 Rail
3. 在 LLM 调用中集成 Rail
4. 自定义 Rail 示例

子层标识：🔧 Rail
主层：🧠 Decision
"""

from typing import Dict, Any, List, Optional
from agent.rails import (
    Rail,
    RailManager,
    RailContext,
    RailResult,
    RailPriority,
    get_rail_manager,
    TaskEventRail,
)


def setup_agent_rails(session_id: str, agent: Any) -> RailManager:
    """
    设置 Agent 的 Rails
    
    在 Agent 初始化时调用此函数来设置 Rails
    
    Args:
        session_id: 会话 ID
        agent: Agent 实例
        
    Returns:
        RailManager 实例
    """
    manager = get_rail_manager(session_id)
    
    manager.register_rail(TaskEventRail(session_id), agent)
    
    return manager


class RailEnabledAgentMixin:
    """
    Rail 启用的 Agent Mixin
    
    如果你的 Agent 类需要集成 Rail，可以继承此 Mixin
    """
    
    def __init__(self, *args, enable_rails: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self._enable_rails = enable_rails
        self._rail_manager = None
        
        if self._enable_rails and hasattr(self, 'session_id'):
            self._setup_rails()
    
    def _setup_rails(self):
        """设置 Rails"""
        self._rail_manager = setup_agent_rails(self.session_id, self)
    
    async def _trigger_before_tool(self, tool_name: str, args: Dict) -> Optional[RailResult]:
        """触发工具调用前 Rail"""
        if not self._rail_manager:
            return None
        return await self._rail_manager.trigger_before_tool_call(tool_name, args)
    
    async def _trigger_after_tool(self, tool_name: str, args: Dict, result: Any) -> Optional[RailResult]:
        """触发工具调用后 Rail"""
        if not self._rail_manager:
            return None
        return await self._rail_manager.trigger_after_tool_call(tool_name, args, result)
    
    async def _trigger_checkpoint(self, checkpoint_name: str) -> None:
        """触发 Checkpoint"""
        if self._rail_manager:
            await self._rail_manager.trigger_checkpoint(checkpoint_name)


class PermissionsRail(Rail):
    """
    权限检查 Rail 示例
    
    在工具调用前检查权限
    """
    
    name = "permissions"
    description = "Tool permission checking"
    priority = RailPriority.CRITICAL
    
    def __init__(self, session_id: str, allowed_tools: Optional[List[str]] = None):
        super().__init__(session_id)
        self.allowed_tools = allowed_tools or []
    
    async def before_tool_call(
        self,
        tool_name: str,
        args: Dict[str, Any],
        **kwargs
    ) -> Optional[RailResult]:
        """工具调用前检查权限"""
        if self.allowed_tools and tool_name not in self.allowed_tools:
            return RailResult(
                allowed=False,
                error=f"Tool '{tool_name}' is not allowed"
            )
        return None


class CostControlRail(Rail):
    """
    成本控制 Rail 示例
    
    监控 LLM 调用成本
    """
    
    name = "cost_control"
    description = "LLM cost monitoring and control"
    priority = RailPriority.HIGH
    
    def __init__(self, session_id: str, max_cost: float = 10.0):
        super().__init__(session_id)
        self.max_cost = max_cost
        self.total_cost = 0.0
    
    async def after_llm_call(
        self,
        messages: List[Dict[str, Any]],
        response: Any,
        **kwargs
    ) -> Optional[RailResult]:
        """LLM 调用后计算成本"""
        if hasattr(response, 'usage'):
            cost = self._calculate_cost(response.usage)
            self.total_cost += cost
            
            self.logger.info(f"Cost: ${self.total_cost:.4f} / ${self.max_cost:.4f}")
            
            if self.total_cost > self.max_cost:
                self.logger.warning(f"Cost limit exceeded: ${self.total_cost:.4f} > ${self.max_cost:.4f}")
        
        return None
    
    def _calculate_cost(self, usage: Dict) -> float:
        """计算成本（示例）"""
        prompt_tokens = usage.get('prompt_tokens', 0)
        completion_tokens = usage.get('completion_tokens', 0)
        
        return (prompt_tokens * 0.00001 + completion_tokens * 0.00003)


class ContextCompressionRail(Rail):
    """
    上下文压缩 Rail 示例
    
    在消息过多时触发压缩
    """
    
    name = "context_compression"
    description = "Context compression triggering"
    priority = RailPriority.NORMAL
    
    def __init__(self, session_id: str, max_messages: int = 50):
        super().__init__(session_id)
        self.max_messages = max_messages
    
    async def before_llm_call(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        **kwargs
    ) -> Optional[RailResult]:
        """LLM 调用前检查是否需要压缩"""
        if len(messages) > self.max_messages:
            self.logger.info(
                f"Message count ({len(messages)}) exceeds limit ({self.max_messages}), "
                "context compression should be triggered"
            )
        return None


def register_example_rails(session_id: str) -> RailManager:
    """
    注册示例 Rails
    
    展示如何注册多个 Rails
    """
    manager = get_rail_manager(session_id)
    
    manager.register_rail(TaskEventRail(session_id))
    manager.register_rail(PermissionsRail(session_id))
    manager.register_rail(CostControlRail(session_id, max_cost=5.0))
    manager.register_rail(ContextCompressionRail(session_id, max_messages=40))
    
    return manager


__all__ = [
    "setup_agent_rails",
    "RailEnabledAgentMixin",
    "PermissionsRail",
    "CostControlRail",
    "ContextCompressionRail",
    "register_example_rails",
]