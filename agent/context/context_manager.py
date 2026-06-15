#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Context Manager - 统一的上下文管理入口

整合 ContextCompressor 和 ContextBuilder，提供统一的上下文构建流程。
所有 LLM 调用都必须经过此入口，确保上下文处理的一致性。

功能：
1. 自动上下文压缩（基于阈值检测）
2. 统一的系统提示构建（使用 ContextBuilder）
3. 支持多种调用场景（工具选择、直接回复、模式判断等）
4. 记忆预取（Hermes 风格）

参考 Hermes 的 build_api_kwargs() 统一入口设计。

日志子层：💾 Context
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Any, TYPE_CHECKING
from enum import Enum

from common.logging_manager import get_decision_logger

if TYPE_CHECKING:
    from agent.context.context_compressor import ContextCompressor
    from agent.context.context_builder import ContextBuilder
    from tools.memory_tool import MemoryStore


class ContextPurpose(Enum):
    """上下文构建的目的"""
    # 模式判断：判断是否使用 ReAct 模式
    MODE_DECISION = "mode_decision"
    # 工具选择：选择合适的工具
    TOOL_SELECTION = "tool_selection"
    # 直接回复：生成直接回复
    DIRECT_RESPONSE = "direct_response"
    # 澄清回复：需要用户澄清
    CLARIFICATION = "clarification"
    # 工具执行后总结：工具执行后生成自然语言回复
    TOOL_RESULT_SUMMARY = "tool_result_summary"
    # ReAct 循环：ReAct 模式的推理循环
    REACT_LOOP = "react_loop"
    # 消息列表构建：构建标准消息列表格式
    MESSAGES_BUILD = "messages_build"


@dataclass
class BuildResult:
    """构建结果"""
    system_prompt: str          # 完整的系统提示词
    user_message: str          # 用户消息
    compressed: bool           # 是否进行了压缩
    original_count: int         # 原始消息数
    compressed_count: int       # 压缩后消息数
    memory_prefetch: bool       # 是否进行了记忆预取
    purpose: ContextPurpose     # 构建目的


@dataclass
class BuildMessagesResult:
    """消息列表构建结果"""
    messages: List[Dict[str, Any]]  # 标准消息列表
    compressed: bool                 # 是否进行了压缩
    original_count: int             # 原始消息数
    compressed_count: int           # 压缩后消息数
    purpose: ContextPurpose          # 构建目的


class ContextManager:
    """
    统一的上下文管理器
    
    整合压缩和构建逻辑，所有 LLM 调用都必须经过此入口。
    
    使用方式：
    ```python
    manager = ContextManager(
        context_compressor=compressor,
        context_builder=builder,
        memory_store=memory_store
    )
    
    result = await manager.build(
        user_message="你好",
        conversation_history=history,
        purpose=ContextPurpose.DIRECT_RESPONSE,
        tools=tools
    )
    
    response = await llm_provider.generate(
        result.user_message,
        system_prompt=result.system_prompt
    )
    ```
    
    日志子层：💾 Context
    """
    
    # 压缩阈值：对话历史超过此数量时触发压缩
    COMPRESSION_THRESHOLD = 10
    
    def __init__(
        self,
        context_compressor: Optional["ContextCompressor"] = None,
        context_builder: Optional["ContextBuilder"] = None,
        memory_store: Optional["MemoryStore"] = None,
        compression_threshold: int = None
    ):
        """
        Args:
            context_compressor: 上下文压缩器
            context_builder: 上下文构建器
            memory_store: 记忆存储（用于预取）
            compression_threshold: 压缩阈值（消息数），默认 COMPRESSION_THRESHOLD
        """
        self.logger = get_decision_logger(self.__class__.__name__, sublayer="context")
        self._context_compressor = context_compressor
        self._context_builder = context_builder
        self._memory_store = memory_store
        self._compression_threshold = compression_threshold or self.COMPRESSION_THRESHOLD
        
        self.logger.debug(
            f"ContextManager initialized (compression_threshold={self._compression_threshold})"
        )
    
    def set_context_compressor(self, compressor: "ContextCompressor") -> None:
        """设置上下文压缩器"""
        self._context_compressor = compressor
    
    def set_context_builder(self, builder: "ContextBuilder") -> None:
        """设置上下文构建器"""
        self._context_builder = builder
    
    def set_memory_store(self, memory_store: "MemoryStore") -> None:
        """设置记忆存储"""
        self._memory_store = memory_store
    
    async def build(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        purpose: ContextPurpose = ContextPurpose.DIRECT_RESPONSE,
        tools: Optional[Dict[str, Any]] = None,
        include_tools: bool = None,
        model: str = None
    ) -> BuildResult:
        """
        构建完整的上下文（统一的入口）
        
        Args:
            user_message: 用户消息
            conversation_history: 对话历史
            purpose: 上下文构建目的
            tools: 工具字典（用于工具选择场景）
            include_tools: 是否包含工具列表（默认根据 purpose 自动判断）
            model: 模型名称（用于模型特定指导）
            
        Returns:
            BuildResult: 包含系统提示词和元数据
        """
        self.logger.debug(f"ContextManager.build() called with purpose={purpose.value}")
        
        # 1. 自动上下文压缩（如果需要）
        processed_history = conversation_history
        compressed = False
        original_count = len(conversation_history) if conversation_history else 0
        compressed_count = original_count
        
        # 根据 purpose 和历史长度决定是否压缩
        should_compress = self._should_compress(conversation_history, purpose)
        
        if should_compress and self._context_compressor:
            try:
                # compress() 是同步方法，直接调用
                processed_history = self._context_compressor.compress(
                    conversation_history
                )
                compressed_count = len(processed_history) if processed_history else 0
                compressed = True
                
                self.logger.info(
                    f"Context compressed: {original_count} -> {compressed_count} messages "
                    f"(purpose={purpose.value})"
                )
            except Exception as e:
                self.logger.warning(f"Context compression failed, using original: {e}")
                processed_history = conversation_history
                compressed_count = original_count
        
        # 2. 根据 purpose 确定是否包含工具
        if include_tools is None:
            include_tools = self._should_include_tools(purpose)
        
        # 3. 使用 ContextBuilder 构建系统提示
        system_prompt = ""
        memory_prefetch = False
        
        if self._context_builder:
            # 设置工具（如果需要）
            if tools and include_tools:
                self._context_builder.set_tools(tools)
            
            try:
                system_prompt = self._context_builder.build_system_prompt(
                    conversation_history=processed_history,
                    include_tools=include_tools and bool(tools),
                    user_message=user_message,
                    model=model
                )
                memory_prefetch = self._context_builder.enable_memory_prefetch
                
                self.logger.info(
                    f"System prompt built: {len(system_prompt)} chars, "
                    f"include_tools={include_tools}, memory_prefetch={memory_prefetch}"
                )
            except Exception as e:
                self.logger.error(f"Failed to build system prompt: {e}")
                system_prompt = ""
        else:
            # 降级：使用简单的历史拼接
            system_prompt = self._build_fallback_prompt(
                processed_history, user_message, include_tools, tools
            )
        
        return BuildResult(
            system_prompt=system_prompt,
            user_message=user_message,
            compressed=compressed,
            original_count=original_count,
            compressed_count=compressed_count,
            memory_prefetch=memory_prefetch,
            purpose=purpose
        )
    
    def _should_compress(
        self,
        conversation_history: Optional[List[Dict[str, Any]]],
        purpose: ContextPurpose
    ) -> bool:
        """
        判断是否需要进行上下文压缩
        
        规则：
        - 历史消息数超过阈值时压缩
        - 某些 purpose 不需要压缩（如 MODE_DECISION 已有自己的压缩逻辑）
        """
        # MODE_DECISION 使用自己的压缩逻辑，跳过
        if purpose == ContextPurpose.MODE_DECISION:
            return False
        
        # 没有历史或历史太少，不需要压缩
        if not conversation_history:
            return False
        
        if len(conversation_history) <= self._compression_threshold:
            return False
        
        return True
    
    def _should_include_tools(self, purpose: ContextPurpose) -> bool:
        """
        根据目的判断是否包含工具列表
        """
        return purpose in (
            ContextPurpose.TOOL_SELECTION,
            ContextPurpose.REACT_LOOP,
        )
    
    def _build_fallback_prompt(
        self,
        conversation_history: Optional[List[Dict]],
        user_message: str,
        include_tools: bool,
        tools: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        构建降级提示词（当 ContextBuilder 不可用时）
        """
        parts = []
        
        # 身份定义
        parts.append("You are a helpful AI assistant.")
        
        # 对话历史
        if conversation_history:
            history_context = "\n\nRecent conversation:\n"
            for msg in conversation_history[-6:]:
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')[:200]
                history_context += f"- {role}: {content}\n"
            parts.append(history_context)
        
        # 工具列表
        if include_tools and tools:
            import json
            tools_schema = []
            for tool_name, tool in tools.items():
                tools_schema.append({
                    'name': tool_name,
                    'description': getattr(tool, 'description', ''),
                    'parameters': getattr(tool, 'parameters', {})
                })
            parts.append(f"Available tools:\n{json.dumps(tools_schema, ensure_ascii=False, indent=2)}")
        
        return "\n\n".join(parts)
    
    async def build_with_messages(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        purpose: ContextPurpose = ContextPurpose.DIRECT_RESPONSE,
        tools: Optional[Dict[str, Any]] = None,
        include_tools: bool = None,
        model: str = None
    ) -> List[Dict[str, str]]:
        """
        构建消息列表格式的上下文（用于某些 API）
        
        返回：
            [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
        """
        result = await self.build(
            user_message=user_message,
            conversation_history=conversation_history,
            purpose=purpose,
            tools=tools,
            include_tools=include_tools,
            model=model
        )
        
        messages = [
            {"role": "system", "content": result.system_prompt},
            {"role": "user", "content": result.user_message}
        ]
        
        return messages
    
    async def build_messages(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        purpose: ContextPurpose = ContextPurpose.MESSAGES_BUILD,
        tools: Optional[Dict[str, Any]] = None,
        include_tools: bool = None,
        model: str = None
    ) -> BuildMessagesResult:
        """
        构建标准消息列表格式的上下文（统一入口）
        
        集成 ContextBuilder 的 build_messages() 方法，支持上下文压缩。
        压缩后的历史以消息列表格式返回，摘要作为消息列表的一部分。
        
        Args:
            user_message: 用户消息
            conversation_history: 对话历史
            purpose: 上下文构建目的（默认 MESSAGES_BUILD）
            tools: 工具字典（用于工具选择场景）
            include_tools: 是否包含工具列表（默认根据 purpose 自动判断）
            model: 模型名称（用于模型特定指导）
            
        Returns:
            BuildMessagesResult: 包含消息列表和元数据
        """
        self.logger.debug(
            f"ContextManager.build_messages() called with purpose={purpose.value}"
        )
        
        # 1. 自动上下文压缩（如果需要）
        processed_history = conversation_history
        compressed = False
        original_count = len(conversation_history) if conversation_history else 0
        compressed_count = original_count
        
        # 根据 purpose 和历史长度决定是否压缩
        should_compress = self._should_compress(conversation_history, purpose)
        
        if should_compress and self._context_compressor:
            try:
                # compress() 是同步方法，直接调用
                processed_history = self._context_compressor.compress(
                    conversation_history
                )
                compressed_count = len(processed_history) if processed_history else 0
                compressed = True
                
                self.logger.info(
                    f"Context compressed: {original_count} -> {compressed_count} messages "
                    f"(purpose={purpose.value})"
                )
            except Exception as e:
                self.logger.warning(f"Context compression failed, using original: {e}")
                processed_history = conversation_history
                compressed_count = original_count
        
        # 2. 根据 purpose 确定是否包含工具
        if include_tools is None:
            include_tools = self._should_include_tools(purpose)
        
        # 3. 使用 ContextBuilder 构建消息列表
        messages: List[Dict[str, Any]] = []
        
        if self._context_builder:
            # 设置工具（如果需要）
            if tools and include_tools:
                self._context_builder.set_tools(tools)
            
            try:
                # 集成 ContextBuilder 的 build_messages() 方法
                messages = self._context_builder.build_messages(
                    conversation_history=processed_history,
                    include_tools=include_tools and bool(tools),
                    user_message=user_message,
                    model=model
                )
                
                # 如果进行了压缩，需要将摘要注入到消息中
                if compressed and self._context_compressor:
                    messages = self._inject_compression_summary(messages, original_count, compressed_count)
                
                self.logger.info(
                    f"Message list built: {len(messages)} messages, "
                    f"include_tools={include_tools}, compressed={compressed}"
                )
            except Exception as e:
                self.logger.error(f"Failed to build message list: {e}")
                messages = self._build_fallback_messages(user_message, processed_history, include_tools, tools)
        else:
            # 降级：使用简单的消息列表构建
            messages = self._build_fallback_messages(user_message, processed_history, include_tools, tools)
        
        return BuildMessagesResult(
            messages=messages,
            compressed=compressed,
            original_count=original_count,
            compressed_count=compressed_count,
            purpose=purpose
        )
    
    def _inject_compression_summary(
        self,
        messages: List[Dict[str, Any]],
        original_count: int,
        compressed_count: int
    ) -> List[Dict[str, Any]]:
        """
        将压缩摘要注入到消息列表中
        
        摘要作为独立消息注入到 system 消息之后，体现上下文压缩的效果。
        注意：ContextCompressor.compress() 已经将摘要作为消息列表的一部分，
        此方法用于添加压缩统计信息。
        
        Args:
            messages: 原始消息列表
            original_count: 原始消息数
            compressed_count: 压缩后消息数
            
        Returns:
            包含压缩摘要消息的消息列表
        """
        if not messages:
            return messages
        
        # 构建压缩统计消息
        compression_info = (
            f"[Context Compression: {original_count} messages compressed to "
            f"{compressed_count} messages. Earlier conversation is summarized above.]"
        )
        
        # 找到 system 消息的位置，在其后插入压缩统计消息
        insert_idx = 0
        if messages and messages[0].get("role") == "system":
            insert_idx = 1
        
        # 构建压缩统计消息
        compression_msg = {"role": "system", "content": compression_info}
        
        # 插入到 system 消息之后
        messages.insert(insert_idx, compression_msg)
        
        return messages
    
    def _build_fallback_messages(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict]],
        include_tools: bool,
        tools: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        构建降级消息列表（当 ContextBuilder 不可用时）
        """
        messages: List[Dict[str, Any]] = []
        
        # 系统消息
        system_parts = ["You are a helpful AI assistant."]
        
        # 工具列表
        if include_tools and tools:
            import json
            tools_schema = []
            for tool_name, tool in tools.items():
                tools_schema.append({
                    "name": tool_name,
                    "description": getattr(tool, "description", ""),
                    "parameters": getattr(tool, "parameters", {})
                })
            system_parts.append(f"Available tools:\n{json.dumps(tools_schema, ensure_ascii=False, indent=2)}")
        
        messages.append({"role": "system", "content": "\n\n".join(system_parts)})
        
        # 对话历史
        if conversation_history:
            for msg in conversation_history[-6:]:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")[:200]
                if role in ("user", "assistant", "system"):
                    messages.append({"role": role, "content": content})
        
        return messages