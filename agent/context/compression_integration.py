# 🧠 Decision - 📊 Context - 压缩集成模块

"""
Compression Integration - 上下文压缩与 Agent 集成

提供压缩功能的完整集成：
1. 创建压缩引擎和 Rail
2. 集成到 Agent 主循环
3. 提供压缩状态查询

Usage:
    from agent.context.compression_integration import CompressionIntegration

    integration = CompressionIntegration(
        session_id="xxx",
        model="gpt-4o",
        llm_client=llm_provider,
    )

    # 在 Agent 循环中
    messages = await integration.before_llm_call(messages, model)
    response = await llm.generate(messages)
    await integration.after_llm_call(messages, response)
"""

from typing import Any, Dict, List, Optional

from common.logging_manager import get_decision_logger
from agent.context.compression_config import CompressionConfig, get_config
from agent.context.context_compressor import ContextCompressor
from agent.context.token_estimator import estimate_messages_tokens_rough
from agent.rails.context_compression_rail import ContextCompressionRail, CompressionRailManager
from agent.rails.rail import RailResult

logger = get_decision_logger(__name__, sublayer="context")


class CompressionIntegration:
    """
    上下文压缩集成器

    将压缩功能集成到 Agent 执行流程中。

    使用示例：
    ```python
    integration = CompressionIntegration(
        session_id="xxx",
        model="gpt-4o",
        llm_client=llm_client,
    )

    # 在 LLM 调用前
    integration.before_llm_call(messages, model)
    if integration.should_compress():
        messages = integration.compress(messages)

    # 调用 LLM
    response = await llm.generate(messages)

    # 在 LLM 调用后
    integration.after_llm_call(messages, response)
    ```
    """

    def __init__(
        self,
        session_id: str,
        model: str = "gpt-4o",
        llm_client: Any = None,
        config: Optional[CompressionConfig] = None,
        quiet_mode: bool = False,
        memory_manager: Any = None,  # 🧠 Memory Manager for on_pre_compress
    ):
        """
        Args:
            session_id: 会话 ID
            model: 主模型名称
            llm_client: LLM 客户端（用于摘要生成）
            config: 压缩配置（默认从环境变量加载）
            quiet_mode: 静默模式
        """
        self.session_id = session_id
        self.model = model
        self.llm_client = llm_client
        self.config = config or get_config()
        self.quiet_mode = quiet_mode
        self.memory_manager = memory_manager  # 🧠 Memory Manager for on_pre_compress

        self._compressor: Optional[ContextCompressor] = None
        self._rail: Optional[ContextCompressionRail] = None
        self._rail_manager: Optional[CompressionRailManager] = None
        self._last_prompt_tokens = 0
        self._last_completion_tokens = 0
        self._pending_compression = False
        self._focus_topic: Optional[str] = None

        self._init_components()

    def _init_components(self) -> None:
        """初始化压缩组件"""
        if not self.config.enabled:
            logger.debug("Compression is disabled")
            return

        self._compressor = ContextCompressor(
            model=self.model,
            threshold_percent=self.config.threshold_percent,
            protect_first_n=self.config.protect_first_n,
            protect_last_n=self.config.protect_last_n,
            summary_target_ratio=self.config.summary_target_ratio,
            quiet_mode=self.config.quiet_mode or self.quiet_mode,
            summary_model=self.config.summary_model,
            base_url=self.config.base_url,
            api_key=self.config.api_key,
            provider=self.config.provider,
            llm_client=self.llm_client,
            memory_manager=self.memory_manager,  # 🧠 Memory Manager for on_pre_compress
        )

        self._rail_manager = CompressionRailManager(self.session_id)
        self._rail = self._rail_manager.create_rail(
            compressor=self._compressor,
            llm_client=self.llm_client,
            enabled=True,
            auto_compress=self.config.auto_compress,
            threshold_percent=self.config.threshold_percent,
        )

        if not self.quiet_mode:
            logger.info(
                f"Compression integration initialized: "
                f"model={self.model}, "
                f"threshold={self.config.threshold_percent * 100:.0f}%, "
                f"auto={self.config.auto_compress}"
            )

    @property
    def compressor(self) -> Optional[ContextCompressor]:
        """获取压缩引擎"""
        return self._compressor

    @property
    def rail(self) -> Optional[ContextCompressionRail]:
        """获取压缩 Rail"""
        return self._rail

    @property
    def rail_manager(self) -> Optional[CompressionRailManager]:
        """获取 Rail 管理器"""
        return self._rail_manager

    def set_llm_client(self, client: Any) -> None:
        """设置 LLM 客户端"""
        self.llm_client = client
        if self._compressor:
            self._compressor.set_llm_client(client)
        if self._rail:
            self._rail.set_llm_client(client)

    def request_compression(self, focus_topic: Optional[str] = None) -> None:
        """
        请求压缩

        Args:
            focus_topic: 可选的聚焦主题
        """
        self._pending_compression = True
        self._focus_topic = focus_topic
        if self._rail:
            self._rail.request_compression(focus_topic)
        logger.info(f"Compression requested (focus: {focus_topic or 'none'})")

    def should_compress(self, messages: List[Dict[str, Any]]) -> bool:
        """
        检查是否应该压缩

        Args:
            messages: 消息列表

        Returns:
            是否应该压缩
        """
        if not self._compressor or not self.config.enabled:
            return False

        if not self.config.auto_compress and not self._pending_compression:
            return False

        current_tokens = estimate_messages_tokens_rough(messages)
        return self._compressor.should_compress(current_tokens)

    def compress(
        self,
        messages: List[Dict[str, Any]],
        current_tokens: Optional[int] = None,
        focus_topic: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        执行压缩

        Args:
            messages: 消息列表
            current_tokens: 当前 token 数（可选，自动计算）
            focus_topic: 聚焦主题（可选）

        Returns:
            压缩后的消息列表
        """
        if not self._compressor:
            return messages

        if current_tokens is None:
            current_tokens = estimate_messages_tokens_rough(messages)

        actual_topic = focus_topic or self._focus_topic

        try:
            compressed = self._compressor.compress(
                messages,
                current_tokens=current_tokens,
                focus_topic=actual_topic,
            )

            self._pending_compression = False
            self._focus_topic = None

            new_tokens = estimate_messages_tokens_rough(compressed)
            saved = current_tokens - new_tokens

            if not self.quiet_mode:
                logger.info(
                    f"Compression complete: {len(messages)} -> {len(compressed)} "
                    f"messages (~{saved} tokens saved)"
                )

            return compressed

        except Exception as e:
            logger.error(f"Compression failed: {e}")
            return messages

    def compress_simple(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        简单压缩（不使用 LLM）

        Args:
            messages: 消息列表

        Returns:
            压缩后的消息列表
        """
        if not self._compressor:
            return messages

        try:
            return self._compressor.compress_simple(messages)
        except Exception as e:
            logger.error(f"Simple compression failed: {e}")
            return messages

    async def before_llm_call(
        self,
        messages: List[Dict[str, Any]],
        model: str,
    ) -> List[Dict[str, Any]]:
        """
        LLM 调用前处理

        Args:
            messages: 消息列表
            model: 模型名称

        Returns:
            处理后的消息列表（可能被压缩）
        """
        if not self.config.enabled:
            return messages

        if not self.should_compress(messages):
            return messages

        current_tokens = estimate_messages_tokens_rough(messages)

        if not self.quiet_mode:
            logger.info(
                f"Pre-LLM compression: ~{current_tokens} tokens "
                f"(threshold: {self._compressor.threshold_tokens})"
            )

        return self.compress(messages, current_tokens=current_tokens)

    async def after_llm_call(
        self,
        messages: List[Dict[str, Any]],
        response: Any,
    ) -> None:
        """
        LLM 调用后处理

        Args:
            messages: 消息列表
            response: LLM 响应
        """
        if not self.config.enabled:
            return

        try:
            if hasattr(response, 'usage') and response.usage:
                usage = response.usage
                self._last_prompt_tokens = usage.get('prompt_tokens', 0)
                self._last_completion_tokens = usage.get('completion_tokens', 0)

                if self._compressor:
                    self._compressor.update_from_response(usage)
            elif hasattr(response, 'last_prompt_tokens'):
                self._last_prompt_tokens = response.last_prompt_tokens
                self._last_completion_tokens = response.last_completion_tokens

        except Exception as e:
            logger.debug(f"Could not extract token usage: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """
        获取压缩统计信息

        Returns:
            压缩统计字典
        """
        stats = {
            "enabled": self.config.enabled,
            "auto_compress": self.config.auto_compress,
            "pending_compression": self._pending_compression,
            "last_prompt_tokens": self._last_prompt_tokens,
            "last_completion_tokens": self._last_completion_tokens,
        }

        if self._compressor:
            stats.update({
                "compression_count": self._compressor.compression_count,
                "context_length": self._compressor.context_length,
                "threshold_tokens": self._compressor.threshold_tokens,
                "ineffective_count": self._compressor._ineffective_compression_count,
            })

        return stats

    def get_status(self) -> Dict[str, Any]:
        """
        获取压缩状态

        Returns:
            状态字典
        """
        return {
            "enabled": self.config.enabled,
            "auto_compress": self.config.auto_compress,
            "initialized": self._compressor is not None,
            "stats": self.get_stats(),
        }


def create_integration(
    session_id: str,
    model: str = "gpt-4o",
    llm_client: Any = None,
    config: Optional[CompressionConfig] = None,
    memory_manager: Any = None,  # 🧠 Memory Manager for on_pre_compress
) -> CompressionIntegration:
    """
    创建压缩集成器（便捷函数）

    Args:
        session_id: 会话 ID
        model: 模型名称
        llm_client: LLM 客户端
        config: 压缩配置
        memory_manager: Memory Manager 实例

    Returns:
        CompressionIntegration 实例
    """
    return CompressionIntegration(
        session_id=session_id,
        model=model,
        llm_client=llm_client,
        config=config,
        memory_manager=memory_manager,
    )


__all__ = [
    "CompressionIntegration",
    "create_integration",
]