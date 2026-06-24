#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory Manager Module - Inspired by Hermes Agent

This module orchestrates memory operations across multiple providers.
Built-in memory is now handled through BuiltinMemoryProvider (v8.0.0+).

Key Features (from Hermes):
1. Multi-provider orchestration - manage multiple memory providers
2. Prefetch - recall relevant context before each turn
3. Sync - persist completed turns to all providers
4. Lifecycle hooks - on_session_switch, on_pre_compress, etc.
5. Builtin Provider - handles built-in memory through Provider interface

架构说明 (v8.0.0+):
- 内置记忆通过 BuiltinMemoryProvider 处理
- MemoryStore 由 BuiltinMemoryProvider 持有
- MemoryManager 仅负责 Provider 编排
- 保持外部 Provider 的注册机制以支持扩展
"""

from typing import List, Dict, Optional, Any, TYPE_CHECKING

from common.logging_manager import get_decision_logger
from .memory_provider import MemoryProvider, BuiltinMemoryProvider
from .memory_store import MemoryStore, MEMORY_SCHEMA

logger = get_decision_logger("MemoryManager")


class MemoryManager:
    """
    Memory Manager that orchestrates memory operations across providers.

    Inspired by Hermes Agent's memory_manager.py, this class:
    1. Manages BuiltinMemoryProvider (handles built-in memory)
    2. Manages external providers with unified interface
    3. Routes tool calls to appropriate providers
    4. Coordinates lifecycle hooks across all providers

    使用方式:
        # 方式 1: 使用统一初始化（推荐）
        config = MemoryConfig(semantic_retrieval_enabled=True)
        manager = MemoryManager.from_config(config)
        manager.initialize(session_id="xxx")

        # 方式 2: 手动初始化
        manager = MemoryManager()
        manager.initialize(session_id="xxx")

        # 系统提示（通过 BuiltinMemoryProvider）
        prompt_parts.append(manager.build_system_prompt())

        # 预取（所有 providers）
        context = manager.prefetch_all(user_message, session_id=session_id)

        # 工具调用
        result = manager.handle_tool_call("memory", {"action": "read", "target": "memory"})

        # 外部 Provider（如需要）
        manager.add_provider(ExternalMemoryProvider())
    """

    def __init__(self):
        # 内部持有的 BuiltinMemoryProvider
        self._builtin_provider: Optional[BuiltinMemoryProvider] = None
        # 外部 providers
        self._providers: List[MemoryProvider] = []
        # 工具名称到 provider 的映射
        self._tool_to_provider: Dict[str, MemoryProvider] = {}
        self._session_id: str = ""
        self._initialized: bool = False
        self._config = None  # 持有配置引用
        self.logger = get_decision_logger(self.__class__.__name__)

    @classmethod
    def from_config(cls, config: "MemoryConfig") -> "MemoryManager":
        """
        从 MemoryConfig 创建 MemoryManager 实例。

        统一初始化入口，一行代码完成所有组件创建：
        - BuiltinMemoryProvider: 如果启用则自动创建
        - 外部 Provider: 如果配置则自动加载

        Args:
            config: MemoryConfig 配置对象

        Returns:
            配置好的 MemoryManager 实例
        """
        manager = cls()
        manager._config = config

        # 如果启用内置 Provider，从配置创建
        if config.enabled and config.builtin_enabled:
            manager._builtin_provider = BuiltinMemoryProvider.from_config(config)
            manager.logger.info("BuiltinMemoryProvider created from config")

        # 如果配置了外部 Provider，懒加载
        if config.enabled and config.external_provider:
            # 延迟加载外部 Provider
            manager.logger.info(f"External provider '{config.external_provider}' configured (lazy load on init)")

        return manager

    @property
    def config(self) -> Optional["MemoryConfig"]:
        """获取当前配置"""
        return self._config

    # -- Builtin Provider Access -----------------------------------------------

    @property
    def builtin_provider(self) -> Optional[BuiltinMemoryProvider]:
        """
        获取内置 BuiltinMemoryProvider。

        注意：如果通过 from_config() 创建时禁用了内置 Provider，
        或 MemoryConfig.builtin_enabled=False，此属性可能返回 None。
        """
        return self._builtin_provider

    @property
    def is_builtin_enabled(self) -> bool:
        """检查内置 Provider 是否启用"""
        return self._builtin_provider is not None

    @property
    def memory_store(self) -> Optional[MemoryStore]:
        """获取 MemoryStore（通过 BuiltinMemoryProvider）。
        
        如果内置 Provider 未启用，返回 None。
        """
        if self._builtin_provider is None:
            return None
        return self._builtin_provider.get_memory_store()

    # -- Initialization --------------------------------------------------------

    def initialize(self, session_id: str, **kwargs) -> None:
        """
        初始化所有 memory providers。

        支持两种初始化方式：
        1. 通过 from_config() 创建后调用（推荐）
        2. 直接调用，会自动创建默认组件

        Args:
            session_id: 当前会话 ID
            **kwargs: 其他上下文，包含：
                - config: MemoryConfig 配置对象（可选，用于兼容旧代码）
                - memory_config: 兼容性别名
                - platform, hermes_home 等其他上下文
        """
        self._session_id = session_id
        self._initialized = True

        # 优先使用已有配置（通过 from_config 创建）
        if self._config is None:
            # 从 kwargs 获取配置或使用默认
            self._config = kwargs.get("config") or kwargs.get("memory_config")
            
            # 如果有配置但没有初始化 Provider，重新初始化
            if self._config and self._builtin_provider is None:
                if self._config.enabled and self._config.builtin_enabled:
                    self._builtin_provider = BuiltinMemoryProvider.from_config(self._config)
                    self.logger.info("BuiltinMemoryProvider created on initialize")

        # 初始化内置 BuiltinMemoryProvider
        if self._builtin_provider is not None:
            try:
                self._builtin_provider.initialize(session_id, **kwargs)
                self.logger.info(f"MemoryManager initialized for session {session_id}")
            except Exception as e:
                self.logger.error(f"Failed to initialize BuiltinMemoryProvider: {e}")

        # 加载外部 Provider（如果配置了但还未加载）
        if self._config and self._config.enabled and self._config.external_provider:
            if not any(p.name == self._config.external_provider for p in self._providers):
                if self.load_external_provider(self._config.external_provider):
                    self.logger.info(f"External provider '{self._config.external_provider}' loaded")

        # 初始化外部 Providers
        for provider in self._providers:
            try:
                provider.initialize(session_id, **kwargs)
            except Exception as e:
                self.logger.warning(
                    f"Memory provider '{provider.name}' initialize failed: {e}"
                )

    # -- System Prompt --------------------------------------------------------

    def build_system_prompt(self) -> str:
        """
        构建系统提示词块。

        优先级：
        1. 内置 BuiltinMemoryProvider（如果启用）
        2. 外部 Providers

        Returns:
            合并的系统提示文本
        """
        blocks = []

        # 内置 BuiltinMemoryProvider
        if self._builtin_provider is not None:
            try:
                block = self._builtin_provider.system_prompt_block()
                if block and block.strip():
                    blocks.append(block)
            except Exception as e:
                self.logger.warning(f"BuiltinMemoryProvider system_prompt_block() failed: {e}")

        # 外部 Providers
        for provider in self._providers:
            try:
                block = provider.system_prompt_block()
                if block and block.strip():
                    blocks.append(block)
            except Exception as e:
                self.logger.warning(
                    f"Memory provider '{provider.name}' system_prompt_block() failed: {e}"
                )

        return "\n\n".join(blocks)

    # -- Prefetch / Recall ---------------------------------------------------

    def prefetch_all(self, query: str, session_id: str = "") -> str:
        """
        从所有来源收集预取上下文。

        Args:
            query: 用户消息或任务描述
            session_id: 当前会话 ID

        Returns:
            合并的上下文文本
        """
        sid = session_id or self._session_id
        parts = []

        # 内置 BuiltinMemoryProvider 预取
        if self._builtin_provider is not None:
            try:
                result = self._builtin_provider.prefetch(query, session_id=sid)
                if result and result.strip():
                    parts.append(result)
            except Exception as e:
                self.logger.debug(f"BuiltinMemoryProvider prefetch failed: {e}")

        # 外部 Providers
        for provider in self._providers:
            try:
                result = provider.prefetch(query, session_id=sid)
                if result and result.strip():
                    parts.append(result)
            except Exception as e:
                self.logger.debug(
                    f"Memory provider '{provider.name}' prefetch failed: {e}"
                )

        return "\n\n".join(parts)

    def queue_prefetch_all(self, query: str, session_id: str = "") -> None:
        """
        队列后台预取（仅外部 Provider）。

        Args:
            query: 查询内容
            session_id: 当前会话 ID
        """
        sid = session_id or self._session_id
        for provider in self._providers:
            try:
                provider.queue_prefetch(query, session_id=sid)
            except Exception as e:
                self.logger.debug(
                    f"Memory provider '{provider.name}' queue_prefetch failed: {e}"
                )

    # -- Sync ----------------------------------------------------------------

    def sync_all(self, user_content: str, assistant_content: str, session_id: str = "") -> None:
        """
        同步完成的对话轮次到所有 providers。

        Args:
            user_content: 用户消息
            assistant_content: 助手回复
            session_id: 当前会话 ID
        """
        sid = session_id or self._session_id
        for provider in self._providers:
            try:
                provider.sync_turn(user_content, assistant_content, session_id=sid)
            except Exception as e:
                self.logger.warning(
                    f"Memory provider '{provider.name}' sync_turn failed: {e}"
                )

    # -- Lifecycle Hooks -----------------------------------------------------

    def on_turn_start(self, turn_number: int, message: str, **kwargs) -> None:
        """
        通知所有 providers 新一轮开始。

        Args:
            turn_number: 当前轮次号
            message: 用户消息
            **kwargs: 其他上下文
        """
        # 内置 Provider
        if self._builtin_provider is not None:
            try:
                self._builtin_provider.on_turn_start(turn_number, message, **kwargs)
            except Exception as e:
                self.logger.debug(f"BuiltinMemoryProvider on_turn_start failed: {e}")

        # 外部 Providers
        for provider in self._providers:
            try:
                provider.on_turn_start(turn_number, message, **kwargs)
            except Exception as e:
                self.logger.debug(
                    f"Memory provider '{provider.name}' on_turn_start failed: {e}"
                )

    def on_session_end(self, messages: List[Dict[str, Any]]) -> None:
        """
        通知所有 providers 会话结束。

        Args:
            messages: 完整对话历史
        """
        # 内置 Provider
        if self._builtin_provider is not None:
            try:
                self._builtin_provider.on_session_end(messages)
            except Exception as e:
                self.logger.debug(f"BuiltinMemoryProvider on_session_end failed: {e}")

        # 外部 Providers
        for provider in self._providers:
            try:
                provider.on_session_end(messages)
            except Exception as e:
                self.logger.debug(
                    f"Memory provider '{provider.name}' on_session_end failed: {e}"
                )

    def on_session_switch(
        self,
        new_session_id: str,
        parent_session_id: str = "",
        reset: bool = False,
        **kwargs
    ) -> None:
        """
        通知所有 providers 会话 ID 变更。

        Args:
            new_session_id: 新会话 ID
            parent_session_id: 旧会话 ID
            reset: 是否是真正的重置
        """
        if not new_session_id:
            return

        self._session_id = new_session_id

        # 内置 Provider
        if self._builtin_provider is not None:
            try:
                self._builtin_provider.on_session_switch(
                    new_session_id,
                    parent_session_id=parent_session_id,
                    reset=reset,
                    **kwargs
                )
            except Exception as e:
                self.logger.debug(f"BuiltinMemoryProvider on_session_switch failed: {e}")

        # 外部 Providers
        for provider in self._providers:
            try:
                provider.on_session_switch(
                    new_session_id,
                    parent_session_id=parent_session_id,
                    reset=reset,
                    **kwargs
                )
            except Exception as e:
                self.logger.debug(
                    f"Memory provider '{provider.name}' on_session_switch failed: {e}"
                )

    def on_pre_compress(self, messages: List[Dict[str, Any]]) -> str:
        """
        在上下文压缩前通知所有 providers。

        Args:
            messages: 将被压缩的消息列表

        Returns:
            合并的文本
        """
        parts = []

        # 内置 Provider
        if self._builtin_provider is not None:
            try:
                result = self._builtin_provider.on_pre_compress(messages)
                if result and result.strip():
                    parts.append(result)
            except Exception as e:
                self.logger.debug(f"BuiltinMemoryProvider on_pre_compress failed: {e}")

        # 外部 Providers
        for provider in self._providers:
            try:
                result = provider.on_pre_compress(messages)
                if result and result.strip():
                    parts.append(result)
            except Exception as e:
                self.logger.debug(
                    f"Memory provider '{provider.name}' on_pre_compress failed: {e}"
                )

        return "\n\n".join(parts)

    def on_memory_write(
        self,
        action: str,
        target: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        通知外部 providers 内置记忆工具写入。

        Args:
            action: 'add', 'replace', or 'remove'
            target: 'memory' or 'user'
            content: 内容
            metadata: 元数据
        """
        for provider in self._providers:
            if provider.name == "builtin":
                continue
            try:
                provider.on_memory_write(action, target, content, metadata)
            except Exception as e:
                self.logger.debug(
                    f"Memory provider '{provider.name}' on_memory_write failed: {e}"
                )

    def on_delegation(
        self,
        task: str,
        result: str,
        child_session_id: str = "",
        **kwargs
    ) -> None:
        """
        通知所有 providers 子 agent 完成。

        Args:
            task: 任务描述
            result: 结果
            child_session_id: 子 agent 会话 ID
        """
        # 内置 Provider
        try:
            self.builtin_provider.on_delegation(task, result, child_session_id=child_session_id, **kwargs)
        except Exception as e:
            self.logger.debug(f"BuiltinMemoryProvider on_delegation failed: {e}")

        # 外部 Providers
        for provider in self._providers:
            try:
                provider.on_delegation(task, result, child_session_id=child_session_id, **kwargs)
            except Exception as e:
                self.logger.debug(
                    f"Memory provider '{provider.name}' on_delegation failed: {e}"
                )

    def shutdown_all(self) -> None:
        """关闭所有 providers。"""
        # 外部 Providers（逆序关闭）
        for provider in reversed(self._providers):
            try:
                provider.shutdown()
            except Exception as e:
                self.logger.warning(
                    f"Memory provider '{provider.name}' shutdown failed: {e}"
                )

        # 内置 Provider
        if self._builtin_provider is not None:
            try:
                self._builtin_provider.shutdown()
            except Exception as e:
                self.logger.warning(f"BuiltinMemoryProvider shutdown failed: {e}")

    # -- Provider Registration -----------------------------------------------

    def add_provider(self, provider: MemoryProvider) -> None:
        """
        注册外部 memory provider。

        注意：
        - 内置记忆由 BuiltinMemoryProvider 处理
        - 仅支持一个外部 provider
        - 外部 provider 不应注册 'memory' 工具（已被内置占用）

        Args:
            provider: Provider 实例
        """
        # 检查是否是内置 provider
        is_builtin = provider.name == "builtin"

        # 检查现有外部 provider
        has_external = any(p.name != "builtin" for p in self._providers)
        if not is_builtin and has_external:
            self.logger.warning(
                f"Rejected memory provider '{provider.name}' — external provider "
                f"already registered. Only one external memory provider is allowed."
            )
            return

        self._providers.append(provider)

        # 索引工具名称
        for schema in provider.get_tool_schemas():
            tool_name = schema.get("name", "")
            if tool_name and tool_name not in self._tool_to_provider:
                self._tool_to_provider[tool_name] = provider
            elif tool_name in self._tool_to_provider:
                self.logger.warning(
                    f"Memory tool name conflict: '{tool_name}' already registered"
                )

        self.logger.info(
            f"Memory provider '{provider.name}' registered, "
            f"total providers: {len(self._providers)}"
        )

    def load_external_provider(
        self,
        name: str,
        config: Dict[str, Any] = None,
        validate: bool = True,
    ) -> bool:
        """
        动态加载外部 memory provider。

        从 plugins.memory 目录加载指定名称的 Provider 并注册。
        支持配置校验和错误处理。

        Args:
            name: Provider 名称
            config: Provider 配置字典（用于校验）
            validate: 是否进行配置校验

        Returns:
            True 如果加载成功

        Raises:
            ProviderNotFoundError: Provider 未找到
            ProviderUnavailableError: Provider 不可用
            ProviderConfigError: Provider 配置错误
        """
        from plugins.memory import (
            load_memory_provider,
            diagnose_provider,
            validate_provider_config,
            handle_provider_error,
            ProviderNotFoundError,
            ProviderUnavailableError,
            ProviderConfigError,
        )
        
        try:
            # 1. 诊断 Provider
            diagnostics = diagnose_provider(name)
            
            if diagnostics.status.value == "not_found":
                available = self._get_available_providers()
                suggestion = f"Available: {', '.join(available)}" if available else "No external providers found"
                raise ProviderNotFoundError(
                    name,
                    suggestion=suggestion
                )
            
            # 2. 加载 Provider
            provider = load_memory_provider(name)
            if provider is None:
                raise ProviderLoadError(name, Exception(diagnostics.error or "Unknown load error"))
            
            # 3. 配置校验（如果提供了配置）
            if validate and config:
                validation_result = validate_provider_config(name, config)
                if not validation_result.is_valid:
                    raise ProviderConfigError(name, validation_result.errors)
                
                # 记录警告
                for warning in validation_result.warnings:
                    self.logger.warning(f"Provider '{name}' config warning: {warning}")
            
            # 4. 检查是否可用
            if not diagnostics.is_available:
                reason = diagnostics.error or "Provider reported unavailable"
                raise ProviderUnavailableError(name, reason)
            
            # 5. 检查是否有工具冲突
            self._check_tool_conflicts(provider, name)
            
            # 6. 注册 provider
            self.add_provider(provider)
            
            self.logger.info(
                f"Successfully loaded external provider '{name}' "
                f"with {len(diagnostics.available_tools)} tools"
            )
            return True
            
        except ProviderNotFoundError:
            raise
        except ProviderUnavailableError:
            raise
        except ProviderConfigError:
            raise
        except ImportError as e:
            self.logger.error(f"Plugin system not available: {e}")
            raise ProviderNotFoundError(
                name,
                suggestion="Install required dependencies or use built-in memory"
            )
        except ProviderLoadError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to load external provider '{name}': {e}")
            # 尝试优雅降级
            success, fallback, msg = handle_provider_error(e, name)
            if success and fallback:
                self.logger.info(msg)
                return True
            raise ProviderLoadError(name, e)
    
    def _check_tool_conflicts(self, provider: MemoryProvider, name: str) -> None:
        """
        检查 Provider 工具是否与现有工具冲突。
        
        Args:
            provider: Provider 实例
            name: Provider 名称
        """
        try:
            for schema in provider.get_tool_schemas():
                tool_name = schema.get("name")
                if not tool_name:
                    continue
                
                # 检查与内置 memory 工具冲突
                if tool_name == "memory":
                    self.logger.warning(
                        f"Provider '{name}' declares 'memory' tool which conflicts "
                        f"with built-in memory. Tool will be skipped."
                    )
                    continue
                
                # 检查与其他 Provider 冲突
                if tool_name in self._tool_to_provider:
                    existing = self._tool_to_provider[tool_name]
                    self.logger.warning(
                        f"Tool '{tool_name}' from '{name}' conflicts with "
                        f"'{existing.name}'. Skipping duplicate."
                    )
        except Exception as e:
            self.logger.debug(f"Tool conflict check failed: {e}")
    
    def _get_available_providers(self) -> List[str]:
        """
        获取所有可用 Provider 的名称列表。
        
        Returns:
            Provider 名称列表
        """
        from plugins.memory import discover_memory_providers
        
        try:
            providers = discover_memory_providers()
            return [
                name for name, available, _ in providers
                if available
            ]
        except Exception:
            return []

    @property
    def providers(self) -> List[MemoryProvider]:
        """所有注册的 providers（包括内置）。"""
        result = []
        if self._builtin_provider is not None:
            result.append(self._builtin_provider)
        result.extend(self._providers)
        return result

    def get_provider(self, name: str) -> Optional[MemoryProvider]:
        """获取指定名称的 provider。"""
        if self._builtin_provider and self._builtin_provider.name == name:
            return self._builtin_provider
        for p in self._providers:
            if p.name == name:
                return p
        return None

    # -- Tool Routing --------------------------------------------------------

    def get_all_tool_schemas(self) -> List[Dict[str, Any]]:
        """收集所有 providers 的工具 schema。"""
        schemas = []
        seen = set()

        # 内置 memory 工具（通过 BuiltinMemoryProvider）
        if "memory" not in seen:
            schemas.append(MEMORY_SCHEMA)
            seen.add("memory")

        # 外部 providers
        for provider in self._providers:
            try:
                for schema in provider.get_tool_schemas():
                    name = schema.get("name", "")
                    if name and name not in seen:
                        schemas.append(schema)
                        seen.add(name)
            except Exception as e:
                self.logger.warning(
                    f"Memory provider '{provider.name}' get_tool_schemas failed: {e}"
                )

        return schemas

    def get_all_tool_names(self) -> set:
        """返回所有工具名称集合。"""
        names = set(self._tool_to_provider.keys())
        names.add("memory")  # 内置 memory 工具
        return names

    def has_tool(self, tool_name: str) -> bool:
        """检查是否有处理该工具的 provider。"""
        if tool_name == "memory":
            return self._builtin_provider is not None  # 只有启用时才可用
        return tool_name in self._tool_to_provider

    def handle_tool_call(
        self,
        tool_name: str,
        args: Dict[str, Any],
        **kwargs
    ) -> str:
        """
        处理工具调用。

        Args:
            tool_name: 工具名称
            args: 工具参数
            **kwargs: 其他上下文

        Returns:
            JSON 字符串结果
        """
        from agent.memory.memory_store import tool_error

        # 内置 memory 工具 -> BuiltinMemoryProvider
        if tool_name == "memory":
            if self._builtin_provider is None:
                return tool_error("Builtin memory provider is not enabled")
            return self._builtin_provider.handle_tool_call(tool_name, args, **kwargs)

        # 外部 providers
        provider = self._tool_to_provider.get(tool_name)
        if provider is None:
            return tool_error(f"No memory provider handles tool '{tool_name}'")

        try:
            return provider.handle_tool_call(tool_name, args, **kwargs)
        except Exception as e:
            self.logger.error(
                f"Memory provider '{provider.name}' handle_tool_call({tool_name}) failed: {e}"
            )
            return tool_error(f"Memory tool '{tool_name}' failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息。"""
        # 统计实际可用的 provider 数量
        builtin_count = 1 if self._builtin_provider is not None else 0
        provider_count = builtin_count + len(self._providers)
        
        stats = {
            "provider_count": provider_count,
            "provider_names": [p.name for p in self.providers],
            "tool_count": len(self._tool_to_provider) + builtin_count,
            "current_session": self._session_id,
            "initialized": self._initialized,
            "builtin_enabled": self.is_builtin_enabled,
        }
        
        # 添加配置信息（如果有）
        if self._config:
            stats["config"] = {
                "enabled": self._config.enabled,
                "builtin_enabled": self._config.builtin_enabled,
                "external_provider": self._config.external_provider,
                "semantic_retrieval_enabled": self._config.semantic_retrieval_enabled,
            }
        
        return stats
