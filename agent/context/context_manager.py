#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Context Manager - 统一的上下文管理入口

整合 ContextCompressor 和 ContextBuilder，提供统一的上下文构建流程。
所有 LLM 调用都必须经过此入口，确保上下文处理的一致性。

架构职责：
- ContextManager：协调层，负责压缩和构建的编排
- ContextCompressor：压缩层，负责所有压缩逻辑（判断 + 执行）
- ContextBuilder：构建层，负责三层结构 + 工具 Schema 构建

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
    from agent.memory.memory_manager import MemoryManager


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
class BuildPartsResult:
    """三层结构构建结果"""
    parts: Dict[str, str]          # 包含 stable/context/volatile 的字典
    user_message: str             # 用户消息
    compressed: bool              # 是否进行了压缩
    original_count: int           # 原始消息数
    compressed_count: int         # 压缩后消息数
    purpose: ContextPurpose       # 构建目的


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
    上下文协调器 - 编排压缩和构建逻辑
    
    职责：
    - 协调压缩（委托给 ContextCompressor）
    - 协调构建（委托给 ContextBuilder）
    - 提供统一的上下文构建入口
    
    注意：所有压缩逻辑由 ContextCompressor 全权负责，ContextManager 不包含任何压缩判断。
    
    使用方式：
    ```python
    manager = ContextManager(
        context_compressor=compressor,
        context_builder=builder,
        memory_store=memory_store
    )
    
    result = await manager.build_messages(
        user_message="你好",
        conversation_history=history,
        purpose=ContextPurpose.DIRECT_RESPONSE,
        tools=tools
    )
    
    response = await llm_provider.generate(
        result.messages
    )
    ```
    
    日志子层：💾 Context
    """
    
    def __init__(
        self,
        context_compressor: Optional["ContextCompressor"] = None,
        context_builder: Optional["ContextBuilder"] = None,
        memory_manager: Optional["MemoryManager"] = None,
    ):
        """
        Args:
            context_compressor: 上下文压缩器（负责所有压缩逻辑）
            context_builder: 上下文构建器（负责三层结构构建）
            memory_manager: 记忆管理器（用于预取和系统提示）
        """
        self.logger = get_decision_logger(self.__class__.__name__, sublayer="context")
        self._context_compressor = context_compressor
        self._context_builder = context_builder
        self._memory_manager = memory_manager
        
        self.logger.debug("ContextManager initialized")
    
    @property
    def compressor(self) -> Optional["ContextCompressor"]:
        """获取压缩器引用"""
        return self._context_compressor
    
    @property
    def builder(self) -> Optional["ContextBuilder"]:
        """获取构建器引用"""
        return self._context_builder
    
    def set_context_compressor(self, compressor: "ContextCompressor") -> None:
        """设置上下文压缩器"""
        self._context_compressor = compressor
    
    def set_context_builder(self, builder: "ContextBuilder") -> None:
        """设置上下文构建器"""
        self._context_builder = builder
    
    def set_memory_manager(self, memory_manager: "MemoryManager") -> None:
        """设置记忆管理器"""
        self._memory_manager = memory_manager
    
    # =========================================================================
    # 压缩接口 - 完全委托给 ContextCompressor
    # =========================================================================
    
    def compress(
        self,
        messages: List[Dict[str, Any]],
        estimated_tokens: int = None,
    ) -> List[Dict[str, Any]]:
        """
        压缩对话历史（协调层职责 + 委托给 ContextCompressor）
        
        职责边界：
        - ContextManager（协调层）：
            1. 调用 memory_manager.on_pre_compress() 获取记忆预取上下文
            2. 委托压缩判断给 Compressor
        - ContextCompressor（压缩层）：
            全权负责压缩（判断 + 执行），不再持有 memory_manager 引用
        
        这是 Hermes 风格的设计：记忆相关逻辑保留在协调层。
        
        Args:
            messages: 原始消息列表
            estimated_tokens: 预估的 token 数（传递给 Compressor）
            
        Returns:
            压缩后的消息列表（如果不需要压缩或 Compressor 不可用则返回原始消息）
        """
        if not self._context_compressor:
            return messages
        
        try:
            # 协调层职责：在压缩前获取记忆预取上下文
            # 这是 Hermes 的做法：记忆逻辑在协调层处理，压缩层只做压缩
            memory_prefetch_context = self._get_memory_prefetch_context(messages)
            
            # 委托给 Compressor，传递记忆预取上下文
            return self._context_compressor.compress(
                messages,
                estimated_tokens,
                memory_prefetch_context=memory_prefetch_context,
            )
        except Exception as e:
            self.logger.warning(f"Compression failed, using original: {e}")
            return messages
    
    def _get_memory_prefetch_context(self, messages: List[Dict[str, Any]]) -> str:
        """
        从记忆管理器获取预取上下文（协调层职责）
        
        职责分离：
        - ContextManager（协调层）：负责调用记忆管理器
        - ContextCompressor（压缩层）：只接收预取结果，不持有记忆管理器
        
        Args:
            messages: 即将被压缩的消息列表
            
        Returns:
            记忆预取上下文字符串
        """
        if not self._memory_manager:
            return ""
        
        try:
            # 调用 memory_manager 的 on_pre_compress 方法
            return self._memory_manager.on_pre_compress(messages)
        except Exception as e:
            self.logger.debug(f"Memory pre-fetch failed: {e}")
        
        return ""
    
    def should_compress(self, estimated_tokens: int = None) -> bool:
        """
        判断是否需要压缩（委托给 ContextCompressor）
        
        压缩判断逻辑完全由 ContextCompressor 负责。
        
        Args:
            estimated_tokens: 预估的 token 数
            
        Returns:
            是否需要压缩
        """
        if not self._context_compressor:
            return False
        
        # 委托给 Compressor 的 should_compress 方法
        return self._context_compressor.should_compress(estimated_tokens)
    
    def get_compression_stats(self) -> Dict[str, Any]:
        """
        获取压缩统计信息（委托给 ContextCompressor）
        
        Returns:
            压缩统计信息
        """
        if not self._context_compressor:
            return {}
        
        if hasattr(self._context_compressor, 'get_compression_stats'):
            return self._context_compressor.get_compression_stats()
        return {}
    
    # =========================================================================
    # 记忆与用户画像接口 - 协调层职责
    # =========================================================================
    
    def _get_user_profile(self) -> str:
        """
        获取用户画像（协调层职责）
        
        职责分离：
        - ContextManager（协调层）：负责调用 MemoryManager 获取用户画像
        - ContextBuilder（构建层）：只接收用户画像参数，不持有 MemoryManager
        
        Returns:
            用户画像内容，如果无则返回空字符串
        """
        if not self._memory_manager:
            return ""
        
        try:
            return self._memory_manager.build_system_prompt()
        except Exception as e:
            self.logger.debug(f"Failed to get user profile: {e}")
            return ""
    
    def _prefetch_memories(self, user_message: str = "") -> str:
        """
        从记忆管理器预取相关记忆上下文（协调层职责）
        
        职责分离：
        - ContextManager：协调层，负责预取时机和组装
        - ContextBuilder：构建层，只负责组装传入的上下文
        
        Args:
            user_message: 用户消息（用于相关性判断）
            
        Returns:
            预取的记忆上下文，如果无记忆则返回空字符串
        """
        if not self._memory_manager:
            return ""
        
        try:
            # 使用 MemoryManager 构建系统提示块
            memory_context = self._memory_manager.build_system_prompt()
            if memory_context:
                # 添加记忆上下文标记（参考 Hermes 的 <memory-context> 格式）
                return f"<memory-context>\n{memory_context}\n</memory-context>"
        except Exception as e:
            self.logger.debug(f"Memory pre-fetch failed: {e}")
        
        return ""
    
    def on_session_end(self, messages: List[Dict[str, Any]]) -> None:
        """
        在会话结束时通知记忆管理器持久化待定修改。

        协调层职责：
        - ContextManager（协调层）：负责调用 MemoryManager 的 on_session_end
        - MemoryManager 负责遍历所有 Providers 调用其 on_session_end

        Args:
            messages: 完整对话历史
        """
        if not self._memory_manager:
            return
        
        try:
            self._memory_manager.on_session_end(messages)
            self.logger.debug("ContextManager: notified memory manager of session end")
        except Exception as e:
            self.logger.warning(f"Failed to notify memory manager of session end: {e}")
    
    # =========================================================================
    # 构建接口 - 委托给 ContextBuilder
    # =========================================================================
    
    async def build_parts(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        purpose: ContextPurpose = ContextPurpose.DIRECT_RESPONSE,
        tools: Optional[Dict[str, Any]] = None,
        include_tools: bool = None,
        model: str = None
    ) -> BuildPartsResult:
        """
        构建上下文的三层结构（Hermes 风格）
        
        三层架构：
        - stable: Agent 身份 + 能力 + 工具指导 + 技能索引 + 模型特定指导（会话级缓存）
        - context: 用户画像 + 项目上下文（配置相关）
        - volatile: 记忆预取 + 时间戳（每次变化）
        
        Args:
            user_message: 用户消息
            conversation_history: 对话历史
            purpose: 上下文构建目的
            tools: 工具字典
            include_tools: 是否包含工具列表
            model: 模型名称
            
        Returns:
            BuildPartsResult: 包含三层结构和元数据
        """
        self.logger.debug(
            f"ContextManager.build_parts() called with purpose={purpose.value}"
        )
        
        # 1. 自动上下文压缩（委托给 Compressor）
        original_count = len(conversation_history) if conversation_history else 0
        processed_history = self.compress(conversation_history) if conversation_history else None
        compressed_count = len(processed_history) if processed_history else original_count
        compressed = compressed_count < original_count
        
        # 2. 获取用户画像（协调层职责）
        # 用户画像由 MemoryManager 提供，传递给构建层
        user_profile = self._get_user_profile()
        if user_profile:
            self.logger.debug(f"User profile loaded: {len(user_profile)} chars")
        
        # 3. 记忆预取（协调层职责）
        # 预取相关记忆，在调用构建器之前完成
        memory_context = self._prefetch_memories(user_message)
        if memory_context:
            self.logger.debug(f"Memory pre-fetched: {len(memory_context)} chars")
        
        # 4. 设置工具到 context_builder（如果调用方指定了 include_tools=True）
        # 注意：工具包含由调用方通过 include_tools 参数决定
        if self._context_builder and tools and include_tools:
            self._context_builder.set_tools(tools)
        
        # 5. 调用 context_builder.build_parts() 获取三层结构
        # ContextBuilder.build_parts() 负责构建，如果失败会抛出异常
        # 传入用户画像和记忆上下文，构建层只负责组装
        parts: Dict[str, str] = {"stable": "", "context": "", "volatile": ""}
        
        if self._context_builder:
            parts = self._context_builder.build_parts(
                user_message=user_message,
                model=model,
                memory_context=memory_context,
                user_profile=user_profile,
            )
            
            self.logger.info(
                f"Three-layer parts built: stable={len(parts['stable'])} chars, "
                f"context={len(parts['context'])} chars, "
                f"volatile={len(parts['volatile'])} chars"
            )
        else:
            # ContextBuilder 不可用时，记录警告
            # 降级逻辑由调用方处理
            self.logger.warning("ContextBuilder not available")
        
        return BuildPartsResult(
            parts=parts,
            user_message=user_message,
            compressed=compressed,
            original_count=original_count,
            compressed_count=compressed_count,
            purpose=purpose
        )
    
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
        
        # 1. 自动上下文压缩（委托给 Compressor）
        original_count = len(conversation_history) if conversation_history else 0
        processed_history = self.compress(conversation_history) if conversation_history else None
        compressed_count = len(processed_history) if processed_history else original_count
        compressed = compressed_count < original_count
        
        # 2. 获取用户画像（协调层职责）
        # 用户画像由 MemoryManager 提供，传递给构建层
        user_profile = self._get_user_profile()
        
        # 3. 记忆预取（协调层职责）
        memory_context = self._prefetch_memories(user_message)
        
        # 4. 设置工具到 context_builder（如果调用方指定了 include_tools=True）
        # 注意：工具包含由调用方通过 include_tools 参数决定
        if self._context_builder and tools and include_tools:
            self._context_builder.set_tools(tools)
        
        # 5. 使用 ContextBuilder 构建消息列表
        # ContextBuilder.build_messages() 负责构建，如果失败会抛出异常
        # 传入用户画像和记忆上下文，构建层只负责组装
        if self._context_builder:
            messages = self._context_builder.build_messages(
                conversation_history=processed_history,
                include_tools=include_tools and bool(tools),
                user_message=user_message,
                model=model,
                memory_context=memory_context,
                user_profile=user_profile,
            )
            
            self.logger.info(
                f"Message list built: {len(messages)} messages, "
                f"include_tools={include_tools}, compressed={compressed}"
            )
        else:
            # ContextBuilder 不可用时，记录警告
            # 降级逻辑由调用方处理
            self.logger.warning("ContextBuilder not available")
            messages = []
        
        return BuildMessagesResult(
            messages=messages,
            compressed=compressed,
            original_count=original_count,
            compressed_count=compressed_count,
            purpose=purpose
        )