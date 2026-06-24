#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Context Engine Module - 与 Hermes Agent 兼容的上下文压缩引擎基类

本模块提供可插拔的上下文管理，支持上下文压缩、摘要和检索。

设计参考 Hermes Agent 的 ContextEngine：

架构：
- ContextEngine: 压缩引擎抽象基类（不包含存储）
- ContextCompressor: 内置压缩实现
- 第三方引擎（如 LCM）可通过插件系统替换

生命周期：
1. 引擎实例化并注册
2. on_session_start() 在对话开始时调用
3. update_from_response() 在每次 API 响应后调用
4. should_compress() 在每次对话轮次后检查
5. compress() 在 should_compress() 返回 True 时调用
6. on_session_end() 在真正的会话边界（CLI 退出、/reset、gateway 会话过期）调用

Usage:
    from agent.context.context_engine import ContextEngine

    class MyContextEngine(ContextEngine):
        @property
        def name(self) -> str:
            return "my_engine"

        def update_from_response(self, usage):
            ...

        def should_compress(self, prompt_tokens=None):
            ...

        def compress(self, messages, current_tokens=None, focus_topic=None):
            ...
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from common.config import (
    DEFAULT_COMPRESSION_THRESHOLD,
    DEFAULT_PROTECT_FIRST_N,
    DEFAULT_PROTECT_LAST_N,
)


class ContextEngine(ABC):
    """
    上下文压缩引擎基类

    所有上下文引擎必须实现此类。

    职责：
    1. 判断是否需要压缩 (should_compress)
    2. 执行压缩 (compress)
    3. 更新 token 统计 (update_from_response)
    4. 可选：提供工具 schema 供 Agent 调用

    注意：不负责消息存储，消息由调用方管理。
    """

    # -- Identity ----------------------------------------------------------

    @property
    @abstractmethod
    def name(self) -> str:
        """短标识符（如 'compressor', 'lcm'）"""

    # -- Token state (子类必须维护，供调用方读取) ------------

    last_prompt_tokens: int = 0
    last_completion_tokens: int = 0
    last_total_tokens: int = 0
    threshold_tokens: int = 0
    context_length: int = 0
    compression_count: int = 0

    # -- Compaction parameters (子类可通过 __init__ 或 property 覆盖) --------
    #
    # protect_first_n 语义：系统提示之外的非系统头部消息数量，
    # 默认 3 保持历史 "system + first 3 non-system messages" 的头部形状。

    threshold_percent: float = DEFAULT_COMPRESSION_THRESHOLD
    protect_first_n: int = DEFAULT_PROTECT_FIRST_N
    protect_last_n: int = DEFAULT_PROTECT_LAST_N

    # -- Core interface ----------------------------------------------------

    @abstractmethod
    def update_from_response(self, usage: Dict[str, Any]) -> None:
        """
        从 LLM 响应更新 token 使用统计

        Args:
            usage: LLM 响应中的 usage 字典
        """

    @abstractmethod
    def should_compress(self, prompt_tokens: Optional[int] = None) -> bool:
        """
        判断是否需要压缩

        Args:
            prompt_tokens: 当前 prompt 的 token 数

        Returns:
            是否需要压缩
        """

    @abstractmethod
    def compress(
        self,
        messages: List[Dict[str, Any]],
        current_tokens: Optional[int] = None,
        focus_topic: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        压缩消息列表并返回新的消息列表

        这是主要入口点。引擎接收完整消息列表并返回（可能更短的）列表，
        使其适合在上下文预算内。实现可以自由地摘要、构建 DAG 或做任何事情，
        只要返回的列表是有效的 OpenAI 格式消息序列。

        Args:
            messages: 原始消息列表
            current_tokens: 当前 token 数估计
            focus_topic: 聚焦主题（可选）。支持 guided compression 的引擎应优先保留
                与此主题相关的信息。不支持的引擎可以忽略此参数。
        """

    # -- Optional: pre-flight check ----------------------------------------

    def should_compress_preflight(self, messages: List[Dict[str, Any]]) -> bool:
        """
        API 调用前的快速粗略检查（尚无真实 token 计数）

        默认返回 False（跳过预检）。如果引擎可以进行廉价估算则覆盖此方法。

        Args:
            messages: 消息列表

        Returns:
            是否应该在 API 调用前触发压缩
        """
        return False

    # -- Optional: manual /compress preflight ------------------------------

    def has_content_to_compress(self, messages: List[Dict[str, Any]]) -> bool:
        """
        快速检查：消息列表中是否有可以压缩的内容

        用于 gateway ``/compress`` 命令作为预检保护——
        返回 False 让 gateway 报告"尚无内容可压缩"而无需进行 LLM 调用。

        默认返回 True（始终尝试）。有廉价方式内省头部/尾部边界的引擎
        应在记录仍完全受保护时覆盖此方法返回 False。

        Args:
            messages: 消息列表

        Returns:
            是否有内容可以压缩
        """
        return True

    # -- Optional: session lifecycle ---------------------------------------

    def on_session_start(self, session_id: str, **kwargs) -> None:
        """
        会话开始时调用

        使用此方法加载会话的持久化状态（DAG、存储等）。
        kwargs 可能包括 hermes_home、platform、model 等。

        Args:
            session_id: 会话 ID
            **kwargs: 其他上下文参数
        """
        pass

    def on_session_end(self, session_id: str, messages: List[Dict[str, Any]]) -> None:
        """
        在真正的会话边界调用（CLI 退出、/reset、gateway 会话过期）

        使用此方法刷新状态、关闭 DB 连接等。
        不是每个对话轮次都调用——只在会话真正结束时调用。

        Args:
            session_id: 会话 ID
            messages: 完整的对话历史
        """
        pass

    def on_session_reset(self) -> None:
        """在 /new 或 /reset 时调用。重置会话状态"""
        self.last_prompt_tokens = 0
        self.last_completion_tokens = 0
        self.last_total_tokens = 0
        self.compression_count = 0

    # -- Optional: tools ---------------------------------------------------

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        返回此引擎提供给 Agent 的工具 schema

        默认返回空列表（无工具）。LCM 等引擎可在此返回
        lcm_grep、lcm_describe、lcm_expand 等工具的 schema。

        Returns:
            OpenAI 格式的工具 schema 列表
        """
        return []

    def handle_tool_call(
        self,
        name: str,
        args: Dict[str, Any],
        **kwargs
    ) -> str:
        """
        处理来自 Agent 的工具调用

        仅对 get_tool_schemas() 返回的工具名调用。
        必须返回 JSON 字符串。

        kwargs 可能包括：
          messages: 当前内存中的消息列表（用于实时摄取）

        Args:
            name: 工具名称
            args: 工具参数

        Returns:
            JSON 字符串格式的结果
        """
        import json
        return json.dumps({"error": f"Unknown context engine tool: {name}"})

    # -- Optional: status / display ----------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """
        返回用于显示/日志的状态字典

        默认返回 run_agent.py 期望的标准字段。

        Returns:
            包含状态信息的字典
        """
        return {
            "last_prompt_tokens": self.last_prompt_tokens,
            "last_completion_tokens": self.last_completion_tokens,
            "last_total_tokens": self.last_total_tokens,
            "threshold_tokens": self.threshold_tokens,
            "context_length": self.context_length,
            "usage_percent": (
                min(100, self.last_prompt_tokens / self.context_length * 100)
                if self.context_length else 0
            ),
            "compression_count": self.compression_count,
        }

    # -- Optional: model switch support ------------------------------------

    def update_model(
        self,
        model: str,
        context_length: int,
        base_url: str = "",
        api_key: str = "",
        provider: str = "",
        api_mode: str = "",
    ) -> None:
        """
        用户切换模型或激活回退时调用

        默认更新 context_length 并根据 threshold_percent 重新计算 threshold_tokens。
        如果引擎需要更多操作（如重新计算 DAG 预算、切换摘要模型）则覆盖此方法。

        Args:
            model: 新模型名称
            context_length: 新模型的上下文长度
            base_url: API 基础 URL
            api_key: API 密钥
            provider: 提供商名称
            api_mode: API 模式
        """
        self.context_length = context_length
        self.threshold_tokens = int(context_length * self.threshold_percent)
