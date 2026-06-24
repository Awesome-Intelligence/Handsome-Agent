#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory Provider Module - 统一 Provider 基类 (参考 Hermes Agent)

本模块定义内存 Provider 抽象接口和内置实现。

架构说明:
- MemoryProvider: 抽象基类，所有 Provider 必须实现（与 Hermes 命名一致）
- BuiltinMemoryProvider: 内置记忆 Provider (通过 MemoryStore)

流式上下文工具已移至 streaming_scrubber.py:
- StreamingContextScrubber: 流式输出清理器
- sanitize_context(): 上下文清理工具函数
- build_memory_context_block(): 记忆上下文块构建

设计参考:
- Hermes Agent 的 memory_provider.py
"""

from __future__ import annotations

import re
from typing import List, Dict, Optional, Any, TYPE_CHECKING
from abc import ABC, abstractmethod

if TYPE_CHECKING:
    from agent.memory.memory_store import MemoryStore

# 从 streaming_scrubber 导入流式上下文工具（保持向后兼容）
from agent.memory.streaming_scrubber import (
    ScrubberStats,
    StreamingContextScrubber,
    build_memory_context_block,
    sanitize_context,
)

# 从 semantic_retriever 导入统一分词函数（避免重复实现）
from agent.semantic.semantic_retriever import tokenize_text

# 使用统一的日志管理器
from common.logging_manager import get_memory_logger

logger = get_memory_logger("MemoryProvider")


# ============================================================================
# Trivial Prompt Filtering (参考 Hermes Honcho 插件)
# ============================================================================

# 无意义输入正则表达式（参考 Hermes: honcho/__init__.py, supermemory/__init__.py）
_TRIVIAL_PROMPT_RE = re.compile(
    r'^(yes|no|ok|okay|sure|thanks|thank you|y|n|yep|nope|yeah|nah|'
    r'continue|go ahead|do it|proceed|got it|cool|nice|great|done|next|lgtm|k|'
    r'ty|thx|np)\.?$',
    re.IGNORECASE,
)


def is_trivial_prompt(text: str) -> bool:
    """
    检查输入是否是无意义的 trivial prompt。

    参考 Hermes 的 _is_trivial_prompt 实现，用于过滤：
    - 肯定回复: yes, ok, sure, proceed, lgtm
    - 否定回复: no, nope, nah
    - 感谢/礼貌: thanks, thank you
    - 确认/理解: got it, cool, nice, great, done
    - 指令/继续: continue, go ahead, do it, next
    - 斜杠命令: /help, /new (starts with "/")
    - 网络缩写: ty, thx, np

    Args:
        text: 待检查的文本

    Returns:
        True 如果是 trivial prompt，否则 False
    """
    if not text:
        return True
    stripped = text.strip()
    if not stripped:
        return True
    # 过滤斜杠命令
    if stripped.startswith("/"):
        return True
    # 匹配 trivial 词汇
    if _TRIVIAL_PROMPT_RE.match(stripped):
        return True
    return False


# ============================================================================
# Memory Provider Base Class (统一实现，参考 Hermes)
# ============================================================================

class MemoryProvider(ABC):
    """
    内存 Provider 抽象基类（与 Hermes 命名一致）。

    所有内存 Provider 必须实现此接口，提供跨会话的持久化记忆能力。

    生命周期方法 (必须实现):
    1. name - Provider 标识符
    2. is_available() - 检查 Provider 是否可用
    3. initialize() - 会话初始化
    4. get_tool_schemas() - 返回工具 schema

    生命周期方法 (可选实现):
    5. system_prompt_block() - 返回系统提示文本
    6. prefetch() - 预取相关上下文
    7. queue_prefetch() - 队列后台召回
    8. sync_turn() - 同步完成的轮次
    9. handle_tool_call() - 处理工具调用
    10. shutdown() - 清理退出

    可选钩子:
    - on_turn_start()
    - on_session_end()
    - on_session_switch()
    - on_pre_compress()
    - on_memory_write()
    - on_delegation()
    - get_config_schema()
    - save_config()

    使用示例:
        class MyMemoryProvider(MemoryProvider):
            @property
            def name(self) -> str:
                return "my_provider"

            def is_available(self) -> bool:
                return True

            def initialize(self, session_id: str, **kwargs) -> None:
                self._session_id = session_id

            def get_tool_schemas(self) -> List[Dict[str, Any]]:
                return []
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier for this provider (e.g. 'builtin', 'honcho', 'hindsight')."""

    # -- Core lifecycle (implement these) ------------------------------------

    @abstractmethod
    def is_available(self) -> bool:
        """
        Return True if this provider is configured, has credentials, and is ready.

        Called during agent init to decide whether to activate the provider.
        Should not make network calls — just check config and installed deps.
        """

    @abstractmethod
    def initialize(self, session_id: str, **kwargs) -> None:
        """
        Initialize for a session.

        Called once at agent startup. May create resources (banks, tables),
        establish connections, start background threads, etc.

        kwargs always include:
          - hermes_home (str): The active HERMES_HOME directory path. Use this
            for profile-scoped storage instead of hardcoding ``~/.handsome_agent``.
          - platform (str): "cli", "telegram", "discord", "cron", etc.

        kwargs may also include:
          - agent_context (str): "primary", "subagent", "cron", or "flush".
            Providers should skip writes for non-primary contexts.
          - agent_identity (str): Profile name (e.g. "coder"). Use for
            per-profile provider identity scoping.
          - agent_workspace (str): Shared workspace name (e.g. "handsome").
          - parent_session_id (str): For subagents, the parent's session_id.
          - user_id (str): Platform user identifier (gateway sessions).
        """

    @abstractmethod
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        Return tool schemas this provider exposes.

        Each schema follows the OpenAI function calling format:
        {"name": "...", "description": "...", "parameters": {...}}

        Return empty list if this provider has no tools (context-only).
        """

    def system_prompt_block(self) -> str:
        """
        Return text to include in the system prompt.

        Called during system prompt assembly. Return empty string to skip.
        This is for STATIC provider info (instructions, status). Prefetched
        recall context is injected separately via prefetch().
        """
        return ""

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        """
        Recall relevant context for the upcoming turn.

        Called before each API call. Return formatted text to inject as
        context, or empty string if nothing relevant. Implementations
        should be fast — use background threads for the actual recall
        and return cached results here.

        session_id is provided for providers serving concurrent sessions.
        Providers that don't need per-session scoping can ignore it.
        """
        return ""

    def queue_prefetch(self, query: str, *, session_id: str = "") -> None:
        """
        Queue a background recall for the NEXT turn.

        Called after each turn completes. The result will be consumed
        by prefetch() on the next turn. Default is no-op — providers
        that do background prefetching should override this.
        """
        pass

    def sync_turn(self, user_content: str, assistant_content: str, *, session_id: str = "") -> None:
        """
        Persist a completed turn to the backend.

        Called after each turn. Should be non-blocking — queue for
        background processing if the backend has latency.
        """
        pass

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str:
        """
        Handle a tool call for one of this provider's tools.

        Must return a JSON string (the tool result).
        Only called for tool names returned by get_tool_schemas().
        """
        raise NotImplementedError(f"Provider {self.name} does not handle tool {tool_name}")

    def shutdown(self) -> None:
        """Clean shutdown — flush queues, close connections."""
        pass

    # -- Optional hooks (override to opt in) ---------------------------------

    def on_turn_start(self, turn_number: int, message: str, **kwargs) -> None:
        """
        Called at the start of each turn with the user message.

        Use for turn-counting, scope management, periodic maintenance.

        kwargs may include: remaining_tokens, model, platform, tool_count.
        Providers use what they need; extras are ignored.
        """
        pass

    def on_session_end(self, messages: List[Dict[str, Any]]) -> None:
        """
        会话结束时持久化所有待定修改。

        Args:
            messages: 完整对话历史（用于可能的会话总结）
        """
        try:
            self.memory_store.flush_to_disk()
            self._logger.debug("BuiltinMemoryProvider: flushed pending writes to disk on session end")
        except Exception as e:
            self._logger.error(f"Failed to flush memory on session end: {e}")

    def on_session_switch(
        self,
        new_session_id: str,
        *,
        parent_session_id: str = "",
        reset: bool = False,
        **kwargs,
    ) -> None:
        """
        Called when the agent switches session_id mid-process.

        Fires on ``/resume``, ``/branch``, ``/reset``, ``/new`` (CLI), the
        gateway equivalents, and context compression — any path that
        reassigns ``AIAgent.session_id`` without tearing the provider down.

        Providers that cache per-session state in ``initialize()``
        (``_session_id``, ``_document_id``, accumulated turn buffers,
        counters) should update or reset that state here so subsequent
        writes land in the correct session's record.

        Parameters
        ----------
        new_session_id:
            The session_id the agent just switched to.
        parent_session_id:
            The previous session_id, if meaningful — set for ``/branch``
            (fork lineage), context compression (continuation lineage),
            and ``/resume`` (the session we're leaving). Empty string
            when no lineage applies.
        reset:
            ``True`` when this is a genuinely new conversation, not a
            resumption of an existing one. Fired by ``/reset`` / ``/new``.
            Providers should flush accumulated per-session buffers
            (``_turn_counter``, etc.) when this is set. ``False`` for
            ``/resume`` / ``/branch`` / compression where the logical
            conversation continues under the new id.

        Default is no-op for backward compatibility.
        """
        pass

    def on_pre_compress(self, messages: List[Dict[str, Any]]) -> str:
        """
        Called before context compression discards old messages.

        Use to extract insights from messages about to be compressed.
        messages is the list that will be summarized/discarded.

        Return text to include in the compression summary prompt so the
        compressor preserves provider-extracted insights. Return empty
        string for no contribution (backwards-compatible default).
        """
        return ""

    def on_delegation(
        self,
        task: str,
        result: str,
        *,
        child_session_id: str = "",
        **kwargs
    ) -> None:
        """
        Called on the PARENT agent when a subagent completes.

        The parent's memory provider gets the task+result pair as an
        observation of what was delegated and what came back. The subagent
        itself has no provider session (skip_memory=True).

        Args:
            task: the delegation prompt
            result: the subagent's final response
            child_session_id: the subagent's session_id
        """
        pass

    def on_memory_write(
        self,
        action: str,
        target: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Called when the built-in memory tool writes an entry.

        Args:
            action: 'add', 'replace', or 'remove'
            target: 'memory' or 'user'
            content: the entry content
            metadata: structured provenance for the write, when available. Common
              keys include ``write_origin``, ``execution_context``, ``session_id``,
              ``parent_session_id``, ``platform``, and ``tool_name``.

        Use to mirror built-in memory writes to your backend.
        """
        pass

    # -- Config management (参考 Hermes) -------------------------------------

    def get_config_schema(self) -> List[Dict[str, Any]]:
        """
        Return config fields this provider needs for setup.

        Used by 'memory setup' to walk the user through configuration.
        Each field is a dict with:
          key:         config key name (e.g. 'api_key', 'mode')
          description: human-readable description
          secret:      True if this should go to .env (default: False)
          required:    True if required (default: False)
          default:     default value (optional)
          choices:     list of valid values (optional)
          url:         URL where user can get this credential (optional)
          env_var:     explicit env var name for secrets (default: auto-generated)

        Return empty list if no config needed (e.g. local-only providers).
        """
        return []

    def save_config(self, values: Dict[str, Any], hermes_home: str) -> None:
        """
        Write non-secret config to the provider's native location.

        Called by 'memory setup' after collecting user inputs.
        ``values`` contains only non-secret fields (secrets go to .env).
        ``hermes_home`` is the active HERMES_HOME directory path.

        Providers with native config files (JSON, YAML) should override
        this to write to their expected location. Providers that use only
        env vars can leave the default (no-op).

        All new memory provider plugins MUST implement either:
        - save_config() for native config file formats, OR
        - use only env vars (in which case get_config_schema() fields
          should all have ``env_var`` set and this method stays no-op).
        """
        pass


# ============================================================================
# Builtin Memory Provider (参考 Hermes - 真正的 Provider 插件)
# ============================================================================

class BuiltinMemoryProvider(MemoryProvider):
    """
    内置记忆 Provider - 真正的 Provider 插件实现。

    仿照 Hermes Agent 的架构设计，通过 MemoryStore 提供：
    - MEMORY.md: Agent 个人笔记
    - USER.md: 用户画像信息

    架构说明:
    - 作为 Provider 插件实现，与外部 Provider 地位平等
    - MemoryManager 通过此 Provider 访问 MemoryStore
    - 支持威胁检测、原子写入、外部漂移检测
    - 支持语义检索增强预取功能

    语义检索 (v9.1.0):
    - 集成 SemanticRetriever 实现语义级检索
    - 替代简单的关键词匹配
    - 支持配置启用/禁用
    - 默认关闭以保持向后兼容

    与旧实现的区别 (v9.0.0):
    - 不再由 MemoryManager 直接持有 MemoryStore
    - 通过 Provider 接口统一访问
    - 与 Hermes 架构保持一致

    统一初始化 (v9.2.0):
    - 推荐使用 from_config() 类方法创建实例
    - 简化配置初始化流程
    - 添加预取缓存机制 (v9.2.0+)
    """

    # 缓存配置
    DEFAULT_CACHE_SIZE = 50  # 默认缓存大小

    # 类级别 logger（避免每个实例重复创建）
    _logger = get_memory_logger("BuiltinMemoryProvider")

    # 类级别默认分层配置
    DEFAULT_LAYER_CONFIG = {
        "max_score": 0.3,  # 第一层：高置信度阈值
        "min_score": 0.1,  # 第二层：宽松阈值
        "short_length": 50,  # 短记忆阈值（字符数）
        "short_limit": 2,  # 短记忆最多返回数量
        "total_limit": 5,  # 总返回数量限制
    }

    def __init__(
        self,
        memory_store: "MemoryStore" = None,
        semantic_retriever: "SemanticRetriever" = None,
        enable_semantic_retrieval: bool = False,
        cache_size: int = None,
        layer_config: Dict[str, Any] = None,
    ):
        """
        初始化 BuiltinMemoryProvider。

        Args:
            memory_store: MemoryStore 实例（可选，懒加载）
            semantic_retriever: SemanticRetriever 实例（可选，用于语义检索）
            enable_semantic_retrieval: 是否启用语义检索（如果 retriever 提供则自动启用）
            cache_size: 预取缓存大小（默认 50，设为 0 禁用缓存）
            layer_config: 分层预取配置（可选，用于覆盖默认配置）
        """
        self._memory_store = memory_store
        self._semantic_retriever = semantic_retriever
        self._enable_semantic_retrieval = enable_semantic_retrieval or (semantic_retriever is not None)
        self._session_id = ""

        # 预取缓存
        self._cache_size = cache_size if cache_size is not None else self.DEFAULT_CACHE_SIZE
        self._prefetch_cache: Dict[str, str] = {}  # query_hash -> result
        self._cache_access_order: List[str] = []  # LRU 访问顺序
        self._cache_hits = 0
        self._cache_misses = 0

        # 分层预取配置（v9.3.0+，支持实例级别配置）
        self._layer_config = layer_config or self.DEFAULT_LAYER_CONFIG.copy()

    @classmethod
    def from_config(cls, config: "MemoryConfig") -> "BuiltinMemoryProvider":
        """
        从 MemoryConfig 创建 BuiltinMemoryProvider 实例。

        统一初始化入口，一行代码完成所有组件创建：
        - MemoryStore: 从配置创建
        - SemanticRetriever: 如果启用则自动创建

        Args:
            config: MemoryConfig 配置对象

        Returns:
            配置好的 BuiltinMemoryProvider 实例
        """
        from agent.memory.memory_store import MemoryStore

        # 从配置创建 MemoryStore
        memory_store = MemoryStore.from_config(config)

        # 如果启用语义检索，创建检索器
        semantic_retriever = None
        if config.semantic_retrieval_enabled:
            try:
                from agent.semantic.semantic_retriever import SemanticRetriever, RetrievalConfig

                retrieval_config = RetrievalConfig(
                    max_results=config.semantic_max_results,
                    jaccard_min_overlap=config.semantic_min_score,
                    # 检索权重配置（v9.3.0+）
                    fts_weight=config.retrieval_fts_weight,
                    jaccard_weight=config.retrieval_jaccard_weight,
                    hrr_weight=config.retrieval_hrr_weight,
                )
                semantic_retriever = SemanticRetriever(config=retrieval_config)
            except Exception as e:
                logger.warning(f"Failed to create semantic retriever: {e}")

        return cls(
            memory_store=memory_store,
            semantic_retriever=semantic_retriever,
            enable_semantic_retrieval=config.semantic_retrieval_enabled,
            # 传递检索策略配置（v9.3.0+）
            layer_config={
                "max_score": config.retrieval_layer1_threshold,
                "min_score": config.retrieval_layer2_threshold,
                "short_length": config.retrieval_short_length,
                "short_limit": config.retrieval_short_limit,
                "total_limit": config.retrieval_total_limit,
            },
        )

    # -- Cache Management ----------------------------------------------------

    def _get_cache_key(self, query: str) -> str:
        """
        生成缓存键。

        使用查询的小写规范化形式作为键，避免大小写差异导致重复缓存。

        Args:
            query: 查询文本

        Returns:
            缓存键
        """
        return query.lower().strip()

    def _get_from_cache(self, cache_key: str) -> Optional[str]:
        """
        从缓存获取结果（LRU 更新）。

        Args:
            cache_key: 缓存键

        Returns:
            缓存的结果，如果未命中返回 None
        """
        if self._cache_size <= 0:
            return None

        result = self._prefetch_cache.get(cache_key)
        if result is not None:
            # LRU: 更新访问顺序
            if cache_key in self._cache_access_order:
                self._cache_access_order.remove(cache_key)
            self._cache_access_order.append(cache_key)
            self._cache_hits += 1
            self._logger.debug(f"Cache hit for query: {cache_key[:30]}...")
            return result

        self._cache_misses += 1
        return None

    def _put_to_cache(self, cache_key: str, result: str) -> None:
        """
        将结果放入缓存（LRU 淘汰）。

        Args:
            cache_key: 缓存键
            result: 要缓存的结果
        """
        if self._cache_size <= 0:
            return

        # 如果已存在，更新访问顺序
        if cache_key in self._prefetch_cache:
            if cache_key in self._cache_access_order:
                self._cache_access_order.remove(cache_key)
            self._cache_access_order.append(cache_key)
            self._prefetch_cache[cache_key] = result
            return

        # 如果缓存已满，淘汰最久未使用的
        while len(self._prefetch_cache) >= self._cache_size:
            if self._cache_access_order:
                oldest = self._cache_access_order.pop(0)
                self._prefetch_cache.pop(oldest, None)
                self._logger.debug(f"Cache evicted: {oldest[:30]}...")

        # 添加新条目
        self._prefetch_cache[cache_key] = result
        self._cache_access_order.append(cache_key)

    def _invalidate_cache(self) -> None:
        """使缓存失效（在记忆内容改变时调用）。"""
        if self._prefetch_cache:
            self._logger.debug(
                f"Cache invalidated ({len(self._prefetch_cache)} entries cleared)"
            )
        self._prefetch_cache.clear()
        self._cache_access_order.clear()

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息。

        Returns:
            缓存统计字典
        """
        total = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total if total > 0 else 0.0

        return {
            "cache_size": self._cache_size,
            "cache_entries": len(self._prefetch_cache),
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate": f"{hit_rate:.2%}",
        }

    def enable_semantic_retrieval(
        self,
        retriever: "SemanticRetriever" = None,
        config: "MemoryConfig" = None,
    ) -> None:
        """
        启用语义检索功能。

        可以通过两种方式启用：
        1. 直接提供 retriever 实例
        2. 通过 MemoryConfig 自动创建

        Args:
            retriever: SemanticRetriever 实例
            config: MemoryConfig 配置（包含 semantic_retrieval_enabled 等设置）
        """
        if retriever:
            self._semantic_retriever = retriever
            self._enable_semantic_retrieval = True
            self._logger.info("Semantic retrieval enabled with provided retriever")
            return

        # 通过配置启用
        if config and hasattr(config, "semantic_retrieval_enabled"):
            if not config.semantic_retrieval_enabled:
                self._logger.info("Semantic retrieval disabled in config")
                return

            # 自动创建语义检索器
            try:
                from agent.semantic import SemanticRetriever
                from agent.semantic.semantic_retriever import RetrievalConfig

                # 创建检索配置
                retrieval_config = RetrievalConfig(
                    max_results=getattr(config, "semantic_max_results", 5),
                    jaccard_min_overlap=getattr(config, "semantic_min_score", 0.3),
                )

                self._semantic_retriever = SemanticRetriever(config=retrieval_config)
                self._enable_semantic_retrieval = True
                self._logger.info(
                    f"Semantic retrieval enabled with config "
                    f"(max_results={retrieval_config.max_results}, "
                    f"min_score={retrieval_config.jaccard_min_overlap})"
                )
            except Exception as e:
                self._logger.warning(f"Failed to enable semantic retrieval: {e}")
                self._enable_semantic_retrieval = False

    @property
    def name(self) -> str:
        return "builtin"

    @property
    def is_semantic_retrieval_enabled(self) -> bool:
        """检查语义检索是否启用"""
        return self._enable_semantic_retrieval and self._semantic_retriever is not None

    @property
    def memory_store(self) -> "MemoryStore":
        """获取 MemoryStore 实例（懒加载，仅创建实例）"""
        if self._memory_store is None:
            from agent.memory.memory_store import MemoryStore
            self._memory_store = MemoryStore()
        return self._memory_store

    def get_memory_store(self) -> "MemoryStore":
        """获取 MemoryStore 的显式方法"""
        return self.memory_store

    def is_available(self) -> bool:
        """内置 Provider 始终可用"""
        return True

    def initialize(self, session_id: str, **kwargs) -> None:
        """
        初始化 - 加载记忆并创建快照。

        Args:
            session_id: 会话 ID
            **kwargs: 可选参数，包含：
                - config: MemoryConfig 配置对象（用于自动启用语义检索）
                - memory_config: 兼容性别名
        """
        self._session_id = session_id

        # 初始化 MemoryStore
        try:
            if self._memory_store is None:
                from agent.memory.memory_store import MemoryStore
                self._memory_store = MemoryStore()
            self._memory_store.load_from_disk()

            # 注册为观察者：当记忆内容改变时自动使缓存失效
            self._memory_store.add_observer(self._on_memory_store_changed)

            # 冻结系统提示快照（参考 Hermes）
            # 会话开始时冻结，之后的写入不会影响快照（保持前缀缓存稳定）
            self._memory_store.freeze_snapshot()

            # 自动启用语义检索（如果配置中启用）
            config = kwargs.get("config") or kwargs.get("memory_config")
            if config and not self._enable_semantic_retrieval:
                self.enable_semantic_retrieval(config=config)

            self._logger.info(f"BuiltinMemoryProvider initialized for session {session_id}")
            if self._enable_semantic_retrieval:
                self._logger.info("Semantic retrieval is enabled")
        except Exception as e:
            self._logger.error(f"Failed to initialize BuiltinMemoryProvider: {e}")
            raise

    def _on_memory_store_changed(self, action: str, target: str, content: str) -> None:
        """
        观察者回调：当 MemoryStore 内容改变时使缓存失效。

        Args:
            action: 操作类型 ('add', 'replace', 'remove')
            target: 目标类型 ('memory' 或 'user')
            content: 变化的条目内容
        """
        self._logger.debug(f"MemoryStore changed: {action} on {target}")
        self._invalidate_cache()

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """返回 memory 工具 schema"""
        from agent.memory.memory_store import MEMORY_SCHEMA
        return [MEMORY_SCHEMA]

    def get_config_schema(self) -> List[Dict[str, Any]]:
        """内置 Provider 不需要配置"""
        return []

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str:
        """处理 memory 工具调用

        委托给 memory_tool 函数处理，使用 self.memory_store 确保数据一致性。

        注意：写入操作（add/replace/remove）会使预取缓存失效。
        """
        if tool_name != "memory":
            raise NotImplementedError(f"BuiltinMemoryProvider does not handle {tool_name}")

        action = args.get("action", "")

        from agent.memory.memory_store import memory_tool
        result = memory_tool(
            action=action,
            target=args.get("target", "memory"),
            content=args.get("content"),
            old_text=args.get("old_text"),
            store=self.memory_store,
        )

        # 写入操作会使缓存失效
        if action in ("add", "replace", "remove"):
            self._invalidate_cache()
            self._logger.debug(f"Cache invalidated due to {action} operation")

        return result

    def system_prompt_block(self) -> str:
        """
        返回格式化的记忆块。

        使用 MemoryStore 冻结的快照，保证会话内一致性。
        会话开始时调用 freeze_snapshot() 冻结，之后的写入不会影响此快照。
        """
        return self.memory_store.get_snapshot()

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        """
        预取与查询相关的记忆。

        分层预取策略（参考 Hermes v9.3.0）：
        - Layer 1: 高置信度检索（严格阈值 max_score）
        - Layer 2: 宽松检索（低阈值 min_score）+ 短记忆补充
        - 合并去重，限制最终数量

        缓存机制 (v9.2.0+):
        - 相同查询只计算一次
        - LRU 淘汰策略
        - 记忆内容改变时自动失效

        Trivial Prompt 过滤 (v9.3.0+):
        - 跳过 trivial 输入（如 yes/no/ok）以节省 tokens
        - 跳过斜杠命令（如 /help）

        Args:
            query: 查询文本
            session_id: 会话 ID（可选）

        Returns:
            格式化的记忆上下文块
        """
        # 过滤 trivial prompt（参考 Hermes）
        if is_trivial_prompt(query):
            return ""

        # 检查缓存
        cache_key = self._get_cache_key(query)
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result

        try:
            result = self.memory_store.read("memory")
            entries = result.get("entries", [])

            if not entries:
                return ""

            # 分层预取
            if self._enable_semantic_retrieval and self._semantic_retriever:
                relevant = self._layered_prefetch(query, entries)
            else:
                relevant = self._keyword_prefetch(query, entries)

            if not relevant:
                return ""

            # 格式化为带标签的块（最多 5 条）
            context = "\n".join(f"- {e}" for e in relevant[:5])
            result_str = build_memory_context_block(context)

            # 缓存结果
            self._put_to_cache(cache_key, result_str)

            return result_str

        except Exception as e:
            self._logger.warning(f"Prefetch failed: {e}")
            return ""

    def _layered_prefetch(self, query: str, entries: List[str]) -> List[str]:
        """
        分层预取（参考 Hermes 策略）。

        分层策略：
        1. Layer 1: 高置信度检索 - 使用配置的阈值
        2. Layer 2: 短记忆补充 - 放宽阈值，优先返回短记忆

        配置来源（按优先级）：
        1. 实例级别 _layer_config（通过构造函数或 from_config 设置）
        2. 类级别 DEFAULT_LAYER_CONFIG（默认配置）

        Args:
            query: 查询文本
            entries: 记忆条目列表

        Returns:
            合并后的相关记忆列表
        """
        max_score = self._layer_config["max_score"]
        min_score = self._layer_config["min_score"]
        short_length = self._layer_config["short_length"]
        short_limit = self._layer_config["short_limit"]
        total_limit = self._layer_config["total_limit"]

        # Layer 1: 高置信度检索
        layer1_results = self._semantic_prefetch(query, entries, min_score=max_score)
        self._logger.debug(
            f"Layer 1 (high confidence): {len(layer1_results)} entries"
        )

        # Layer 2: 短记忆宽松检索
        short_entries = [e for e in entries if len(e) < short_length]
        layer2_results = self._semantic_prefetch(query, short_entries, min_score=min_score)
        self._logger.debug(
            f"Layer 2 (short memory): {len(layer2_results)} entries from {len(short_entries)} short memories"
        )

        # 合并去重：Layer 1 完全保留，Layer 2 补充不在 Layer 1 中的
        combined = layer1_results[:total_limit]
        for entry in layer2_results:
            if entry not in combined and len(combined) < total_limit:
                combined.append(entry)

        self._logger.debug(
            f"Layered prefetch result: {len(combined)} entries "
            f"(Layer1={len(layer1_results)}, Layer2={len(layer2_results)})"
        )

        return combined

    def _semantic_prefetch(
        self,
        query: str,
        entries: List[str],
        min_score: Optional[float] = None,
    ) -> List[str]:
        """
        使用语义检索预取相关记忆。

        Args:
            query: 查询文本
            entries: 记忆条目列表
            min_score: 最低分数阈值（可选，默认为配置的 jaccard_min_overlap）

        Returns:
            相关的记忆条目列表，按相关性排序
        """
        try:
            # 使用语义检索器（传入 min_score）
            results = self._semantic_retriever.retrieve(query, entries, min_score=min_score)

            # 提取条目（按分数排序）
            if results:
                relevant = [entry for entry, score in results]
                self._logger.debug(
                    f"Semantic retrieval found {len(relevant)} relevant entries "
                    f"(min_score={min_score}) for query '{query[:50]}...'"
                )
                return relevant

            return []

        except Exception as e:
            self._logger.warning(f"Semantic prefetch failed, falling back to keyword: {e}")
            # 降级到关键词匹配
            return self._keyword_prefetch(query, entries)

    def _keyword_prefetch(self, query: str, entries: List[str]) -> List[str]:
        """
        使用关键词匹配预取相关记忆（回退策略）。

        使用统一的 tokenize_text 函数，确保与 SemanticRetriever 一致。

        Args:
            query: 查询文本
            entries: 记忆条目列表

        Returns:
            相关的记忆条目列表
        """
        # 使用统一分词函数（min_length=3 过滤短词）
        query_tokens = tokenize_text(query, min_length=3)
        relevant = []

        for entry in entries:
            entry_tokens = tokenize_text(entry, min_length=3)

            # 计算重叠 token 数
            overlap = len(query_tokens & entry_tokens)
            if overlap >= 1:
                relevant.append(entry)

        return relevant

    def on_pre_compress(self, messages: List[Dict[str, Any]]) -> str:
        """
        上下文压缩前提取洞察。

        从即将被压缩的消息中提取有价值的用户意图。
        使用启发式方法识别可能有价值的短消息，而非硬编码关键词。
        """
        if not messages:
            return ""

        insights = []
        for msg in messages[-10:]:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "user" and len(content) < 200:
                # 使用启发式方法识别可能有价值的短消息
                # - 非问句（不以?结尾）
                # - 非简单的确认/否定（长度大于10）
                # - 非纯标点符号
                is_question = content.strip().endswith("?")
                is_too_short = len(content.strip()) < 10
                is_punctuation_only = all(c in "，。！？、；：" for c in content.strip())

                if not is_question and not is_too_short and not is_punctuation_only:
                    # 进一步检查是否有实质内容
                    word_count = len(content.split())
                    if word_count >= 3:
                        insights.append(content[:100])

        if not insights:
            return ""

        return f"<memory_insights>\n- " + "\n- ".join(insights[:3]) + "\n</memory_insights>"

    def on_session_switch(
        self,
        new_session_id: str,
        *,
        parent_session_id: str = "",
        reset: bool = False,
        **kwargs
    ) -> None:
        """
        会话切换时重新冻结快照（与 Hermes 一致）。

        reset=True（新对话）：重新加载记忆并冻结快照。
        reset=False（继续会话）：重新冻结快照。
        """
        self._session_id = new_session_id

        # 重新加载记忆并冻结快照（与 Hermes 一致）
        self.memory_store.load_from_disk()
        self.memory_store.freeze_snapshot()
        self._logger.debug(
            f"Session switch ({'reset' if reset else 'continue'}), "
            "reloaded and froze snapshot"
        )

    def sync_turn(self, user_content: str, assistant_content: str, *, session_id: str = "") -> None:
        """
        内置 Provider 不自动同步，依赖显式记忆写入。
        """
        pass

    def on_memory_write(
        self,
        action: str,
        target: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        当内置记忆被写入时触发（用于外部 Provider 同步）。

        镜像内置记忆写入到外部 Provider。
        """
        self._logger.debug(f"Memory write event: {action} on {target}")


# ============================================================================
# Exports
# ============================================================================
# 注意: StreamingContextScrubber 等工具函数已移至 streaming_scrubber.py
# 此处从 streaming_scrubber 导入以保持向后兼容

__all__ = [
    # Base class (统一命名，与 Hermes 一致)
    'MemoryProvider',
    # Builtin Provider
    'BuiltinMemoryProvider',
    # Streaming utilities (从 streaming_scrubber 导入，保持向后兼容)
    'ScrubberStats',
    'StreamingContextScrubber',
    'sanitize_context',
    'build_memory_context_block',
]
