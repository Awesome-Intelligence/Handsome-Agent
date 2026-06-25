"""
辅助 LLM 客户端 - 用于内部组件（如 ContextCompressor）的 LLM 调用
🧠 Decision - 🤖 LLM - 辅助客户端

参考 Hermes Agent 的 auxiliary_client.py 实现。

功能：
- 提供独立的 LLM 调用接口，不依赖外部传入的 client
- 自动从配置解析 provider 并调用
- 支持超时、重试等错误处理
"""

import asyncio
import time
from typing import Optional, Dict, Any, List

from common.logging_manager import get_execution_logger

logger = get_execution_logger("AuxiliaryLLM")

# 默认超时时间（秒）
DEFAULT_TIMEOUT = 120.0


def _get_provider_from_config(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """从配置中获取 provider 信息

    Args:
        config: 包含 provider, base_url, api_key 等的配置字典

    Returns:
        Provider 配置字典，失败返回 None
    """
    from .factory import LLMFactory
    from .providers.base import ProviderConfig

    provider_name = config.get("provider", "")
    if not provider_name:
        return None

    api_key = config.get("api_key", "")
    base_url = config.get("base_url", "")
    model = config.get("model", "")
    api_mode = config.get("api_mode", "")

    try:
        provider_class = None
        for name in LLMFactory._providers:
            if name == provider_name.lower():
                provider_class = LLMFactory._providers[name]
                break

        if provider_class is None:
            logger.debug(f"Provider '{provider_name}' not found")
            return None

        provider_config = ProviderConfig(
            api_key=api_key,
            base_url=base_url,
            model=model or LLMFactory._default_models.get(provider_name.lower(), ""),
        )

        client = provider_class(provider_config)
        return client

    except Exception as e:
        logger.debug(f"Failed to create provider client: {e}")
        return None


def call_llm(
    messages: List[Dict[str, str]],
    *,
    task: str = "general",
    model: Optional[str] = None,
    provider: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    api_mode: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: float = 0.3,
    timeout: float = DEFAULT_TIMEOUT,
    main_runtime: Optional[Dict[str, Any]] = None,
    llm_client: Any = None,
) -> Any:
    """
    同步调用 LLM

    Args:
        messages: 消息列表
        task: 任务类型（用于日志标识）
        model: 模型名称
        provider: Provider 名称
        base_url: API 基础 URL
        api_key: API 密钥
        api_mode: API 模式
        max_tokens: 最大 token 数
        temperature: 温度参数
        timeout: 超时时间
        main_runtime: 主运行时配置（优先级低于直接参数）
        llm_client: 已存在的 LLM client（优先使用）

    Returns:
        LLM 响应对象

    Raises:
        RuntimeError: 无可用 provider 时抛出
    """
    if llm_client is not None:
        client = llm_client
    else:
        # 合并配置：直接参数优先于 main_runtime
        runtime = main_runtime or {}
        effective_config = {
            "model": model or runtime.get("model"),
            "provider": provider or runtime.get("provider"),
            "base_url": base_url or runtime.get("base_url"),
            "api_key": api_key or runtime.get("api_key"),
            "api_mode": api_mode or runtime.get("api_mode"),
        }

        client = _get_provider_from_config(effective_config)

        if client is None:
            raise RuntimeError("no LLM provider configured for auxiliary call")

    start_time = time.time()

    try:
        # 构建 prompt（从 messages 提取）
        prompt = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                prompt = content
                break

        response = asyncio.run(
            client.generate(
                prompt=prompt,
                system_prompt=None,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        )

        elapsed = time.time() - start_time
        logger.debug(
            f"[{task}] Auxiliary LLM call completed in {elapsed:.2f}s"
        )

        return response

    except Exception as e:
        elapsed = time.time() - start_time
        logger.warning(
            f"[{task}] Auxiliary LLM call failed after {elapsed:.2f}s: {e}"
        )
        raise


async def acall_llm(
    messages: List[Dict[str, str]],
    *,
    task: str = "general",
    model: Optional[str] = None,
    provider: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    api_mode: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: float = 0.3,
    timeout: float = DEFAULT_TIMEOUT,
    main_runtime: Optional[Dict[str, Any]] = None,
    llm_client: Any = None,
) -> Any:
    """
    异步调用 LLM

    Args:
        messages: 消息列表
        task: 任务类型（用于日志标识）
        其他参数同 call_llm

    Returns:
        LLM 响应对象

    Raises:
        RuntimeError: 无可用 provider 时抛出
    """
    if llm_client is not None:
        client = llm_client
    else:
        runtime = main_runtime or {}
        effective_config = {
            "model": model or runtime.get("model"),
            "provider": provider or runtime.get("provider"),
            "base_url": base_url or runtime.get("base_url"),
            "api_key": api_key or runtime.get("api_key"),
            "api_mode": api_mode or runtime.get("api_mode"),
        }

        client = _get_provider_from_config(effective_config)

        if client is None:
            raise RuntimeError("no LLM provider configured for auxiliary call")

    start_time = time.time()

    try:
        # 构建 prompt
        prompt = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                prompt = content
                break

        response = await client.generate(
            prompt=prompt,
            system_prompt=None,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        elapsed = time.time() - start_time
        logger.debug(
            f"[{task}] Auxiliary LLM call completed in {elapsed:.2f}s"
        )

        return response

    except Exception as e:
        elapsed = time.time() - start_time
        logger.warning(
            f"[{task}] Auxiliary LLM call failed after {elapsed:.2f}s: {e}"
        )
        raise
