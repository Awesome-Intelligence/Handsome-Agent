# 🧠 Decision - 🔧 Rail - Rail 管理器

"""
RailManager - Rails 统一管理器

负责：
1. Rails 注册和注销
2. 按优先级排序 Rails
3. 触发 Rails 回调
4. 中断/恢复控制
"""

import asyncio
import threading
from typing import Dict, List, Any, Optional, Type
from common.logging_manager import get_decision_logger
from agent.rails.rail import Rail, RailPriority, RailContext, RailResult, InterruptType


class RailManager:
    """
    Rails 统一管理器
    
    使用方式：
    1. 创建 RailManager 实例
    2. 调用 register_rail() 注册 Rails
    3. 在 agent 执行流程中调用 trigger_* 方法
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.logger = get_decision_logger("RailManager", sublayer="rail")
        
        self._rails: List[Rail] = []
        self._rail_by_name: Dict[str, Rail] = {}
        self._rail_lock = threading.Lock()
        
        self._pause_event: Optional[asyncio.Event] = None
        self._abort_requested = False
        self._current_context: Optional[RailContext] = None
    
    @property
    def rails(self) -> List[Rail]:
        """获取已注册的 Rails（按优先级排序）"""
        return sorted(self._rails, reverse=True)
    
    def register_rail(self, rail: Rail, agent: Any = None) -> None:
        """
        注册 Rail
        
        Args:
            rail: Rail 实例
            agent: Agent 实例（用于 on_register 回调）
        """
        with self._rail_lock:
            if rail.name in self._rail_by_name:
                self.logger.warning(f"Rail '{rail.name}' already registered, skipping")
                return
            
            self._rails.append(rail)
            self._rail_by_name[rail.name] = rail
            
            if self._pause_event is None:
                self._pause_event = asyncio.Event()
                self._pause_event.set()
        
        try:
            rail.on_register(agent)
            self.logger.info(f"Registered rail: {rail.name} (priority: {rail.priority})")
        except Exception as e:
            rail.on_error(e, "on_register")
    
    def unregister_rail(self, rail_name: str) -> bool:
        """
        注销 Rail
        
        Args:
            rail_name: Rail 名称
            
        Returns:
            bool: 是否成功注销
        """
        with self._rail_lock:
            if rail_name not in self._rail_by_name:
                return False
            
            rail = self._rail_by_name.pop(rail_name)
            self._rails = [r for r in self._rails if r.name != rail_name]
            self.logger.info(f"Unregistered rail: {rail_name}")
            return True
    
    def get_rail(self, rail_name: str) -> Optional[Rail]:
        """
        获取 Rail 实例
        
        Args:
            rail_name: Rail 名称
            
        Returns:
            Rail 实例或 None
        """
        return self._rail_by_name.get(rail_name)
    
    def enable_rail(self, rail_name: str) -> bool:
        """启用 Rail"""
        rail = self.get_rail(rail_name)
        if rail:
            rail.enabled = True
            return True
        return False
    
    def disable_rail(self, rail_name: str) -> bool:
        """禁用 Rail"""
        rail = self.get_rail(rail_name)
        if rail:
            rail.enabled = False
            return True
        return False
    
    def set_context(self, context: RailContext) -> None:
        """设置执行上下文"""
        self._current_context = context
        for rail in self.rails:
            rail.set_context(context)
    
    async def trigger_before_llm_call(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        **kwargs
    ) -> Optional[RailResult]:
        """触发所有 Rail 的 before_llm_call"""
        combined_result = RailResult()
        
        for rail in self.rails:
            if not rail.enabled:
                continue
            
            try:
                result = await rail.before_llm_call(messages, model, **kwargs)
                if result and not result.allowed:
                    combined_result.allowed = False
                    combined_result.error = result.error
                    self.logger.warning(f"Rail '{rail.name}' blocked LLM call: {result.error}")
                    break
                elif result and result.modified_args:
                    messages = result.modified_args
            except Exception as e:
                rail.on_error(e, "before_llm_call")
        
        return combined_result if not combined_result.allowed else None
    
    async def trigger_after_llm_call(
        self,
        messages: List[Dict[str, Any]],
        response: Any,
        **kwargs
    ) -> Optional[RailResult]:
        """触发所有 Rail 的 after_llm_call"""
        injected_messages = []
        
        for rail in self.rails:
            if not rail.enabled:
                continue
            
            try:
                result = await rail.after_llm_call(messages, response, **kwargs)
                if result and result.injected_content:
                    injected_messages.append(result.injected_content)
            except Exception as e:
                rail.on_error(e, "after_llm_call")
        
        if injected_messages:
            return RailResult(injected_content="\n".join(injected_messages))
        return None
    
    async def trigger_before_tool_call(
        self,
        tool_name: str,
        args: Dict[str, Any],
        **kwargs
    ) -> Optional[RailResult]:
        """触发所有 Rail 的 before_tool_call"""
        combined_result = RailResult()
        
        for rail in self.rails:
            if not rail.enabled:
                continue
            
            try:
                result = await rail.before_tool_call(tool_name, args, **kwargs)
                if result and not result.allowed:
                    combined_result.allowed = False
                    combined_result.error = result.error
                    self.logger.warning(f"Rail '{rail.name}' blocked tool '{tool_name}': {result.error}")
                    break
                elif result and result.modified_args:
                    args = result.modified_args
            except Exception as e:
                rail.on_error(e, f"before_tool_call({tool_name})")
        
        return combined_result if not combined_result.allowed else None
    
    async def trigger_after_tool_call(
        self,
        tool_name: str,
        args: Dict[str, Any],
        result: Any,
        **kwargs
    ) -> Optional[RailResult]:
        """触发所有 Rail 的 after_tool_call"""
        injected_content = []
        
        for rail in self.rails:
            if not rail.enabled:
                continue
            
            try:
                result = await rail.after_tool_call(tool_name, args, result, **kwargs)
                if result and result.injected_content:
                    injected_content.append(result.injected_content)
            except Exception as e:
                rail.on_error(e, f"after_tool_call({tool_name})")
        
        if injected_content:
            return RailResult(injected_content="\n".join(injected_content))
        return None
    
    async def trigger_checkpoint(self, checkpoint_name: str) -> None:
        """触发 checkpoint"""
        if self._pause_event is None:
            return
        
        await self._pause_event.wait()
        
        if self._abort_requested:
            self.logger.warning("Abort requested, raising CancelledError")
            raise asyncio.CancelledError("Agent abort requested")
        
        for rail in self.rails:
            if not rail.enabled:
                continue
            
            try:
                await rail.on_checkpoint(checkpoint_name)
            except Exception as e:
                rail.on_error(e, f"checkpoint({checkpoint_name})")
    
    def pause(self) -> None:
        """暂停所有 Rails"""
        if self._pause_event:
            self._pause_event.clear()
        self.logger.info("Rails paused")
    
    def resume(self) -> None:
        """恢复所有 Rails"""
        self._abort_requested = False
        if self._pause_event:
            self._pause_event.set()
        self.logger.info("Rails resumed")
    
    def abort(self) -> None:
        """中止所有 Rails"""
        self._abort_requested = True
        if self._pause_event:
            self._pause_event.set()
        self.logger.warning("Rails abort requested")
    
    def is_paused(self) -> bool:
        """检查是否已暂停"""
        return self._pause_event is not None and not self._pause_event.is_set()
    
    def is_aborted(self) -> bool:
        """检查是否已中止"""
        return self._abort_requested
    
    def get_summary(self) -> Dict[str, Any]:
        """获取 Rails 状态摘要"""
        return {
            "total_rails": len(self._rails),
            "enabled_rails": len([r for r in self._rails if r.enabled]),
            "rail_names": [r.name for r in self.rails],
            "is_paused": self.is_paused(),
            "is_aborted": self.is_aborted(),
        }


_global_managers: Dict[str, RailManager] = {}
_managers_lock = threading.Lock()


def get_rail_manager(session_id: str) -> RailManager:
    """获取或创建 RailManager 实例"""
    if session_id not in _global_managers:
        with _managers_lock:
            if session_id not in _global_managers:
                _global_managers[session_id] = RailManager(session_id)
    return _global_managers[session_id]


def reset_rail_manager(session_id: str) -> None:
    """重置 RailManager"""
    if session_id in _global_managers:
        with _managers_lock:
            if session_id in _global_managers:
                manager = _global_managers[session_id]
                manager.abort()
                del _global_managers[session_id]


__all__ = [
    "RailManager",
    "get_rail_manager",
    "reset_rail_manager",
]