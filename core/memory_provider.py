"""MemoryProvider — 抽象基类，定义记忆提供者接口

参考 Hermes 的多层记忆架构：
- 支持多个记忆提供者（内置 + 外部插件）
- 生命周期管理：initialize → prefetch → sync_turn → shutdown
- 支持工具调用和会话钩子

Lifecycle (called by MemoryManager):
  initialize()          — 连接、创建资源、预热
  system_prompt_block()  — 系统提示中的静态文本
  prefetch(query)        — 每回合前的后台回忆
  sync_turn(user, asst)  — 每回合后的异步写入
  get_tool_schemas()     — 暴露给模型的工具schema
  handle_tool_call()     — 处理工具调用
  shutdown()             — 优雅退出

Optional hooks (override to opt in):
  on_turn_start(turn, message) — 每回合开始时调用
  on_session_end(messages)     — 会话结束时调用
  on_session_switch(new_session_id) — 会话切换时调用
  on_pre_compress(messages)    — 上下文压缩前调用
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class MemoryProvider(ABC):
    """抽象基类 - 记忆提供者"""

    @property
    @abstractmethod
    def name(self) -> str:
        """提供者名称（如 'builtin', 'honcho', 'hindsight'）"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """返回是否已配置好并准备就绪"""
        pass

    @abstractmethod
    def initialize(self, session_id: str, **kwargs) -> None:
        """初始化会话
        
        kwargs 包含:
          - hermes_home (str): HERMES_HOME 目录路径
          - platform (str): "cli", "telegram", "discord", "cron" 等
          - agent_context (str): "primary", "subagent", "cron", "flush"
          - agent_identity (str): 配置文件名称
          - user_id (str): 平台用户标识
        """
        pass

    def system_prompt_block(self) -> str:
        """返回要包含在系统提示中的文本"""
        return ""

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        """为即将到来的回合回忆相关上下文
        
        返回格式化的上下文文本，或空字符串
        """
        return ""

    def queue_prefetch(self, query: str, *, session_id: str = "") -> None:
        """为下一回合排队后台回忆"""
        pass

    def sync_turn(self, user_content: str, assistant_content: str, *, session_id: str = "") -> None:
        """将完成的回合持久化到后端"""
        pass

    @abstractmethod
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """返回此提供者暴露的工具schema
        
        每个schema遵循OpenAI函数调用格式：
        {"name": "...", "description": "...", "parameters": {...}}
        """
        pass

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str:
        """处理工具调用"""
        raise NotImplementedError(f"Provider {self.name} does not handle tool {tool_name}")

    def shutdown(self) -> None:
        """优雅关闭 - 刷新队列、关闭连接"""
        pass

    # -- 可选钩子 --

    def on_turn_start(self, turn_number: int, message: str, **kwargs) -> None:
        """每回合开始时调用"""
        pass

    def on_session_end(self, messages: List[Dict[str, Any]]) -> None:
        """会话结束时调用（显式退出或超时）"""
        pass

    def on_session_switch(
        self,
        new_session_id: str,
        *,
        parent_session_id: str = "",
        reset: bool = False,
        **kwargs,
    ) -> None:
        """会话ID切换时调用"""
        pass

    def on_pre_compress(self, messages: List[Dict[str, Any]]) -> str:
        """上下文压缩前调用，返回要保留的文本"""
        return ""

    def on_delegation(self, task: str, result: str, *,
                      child_session_id: str = "", **kwargs) -> None:
        """子代理完成任务时在父代理上调用"""
        pass

    def get_config_schema(self) -> List[Dict[str, Any]]:
        """返回配置字段schema"""
        return []

    def save_config(self, values: Dict[str, Any], hermes_home: str) -> None:
        """保存配置"""
        pass
