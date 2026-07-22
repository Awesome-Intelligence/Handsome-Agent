"""
adapters - 渠道适配器子模块

提供多种渠道适配器：
- OpenAIAdapter: OpenAI 兼容 API 适配器 (从 api/ 迁移)
"""

from .openai_adapter import (
    OpenAIAdapter,
    create_openai_adapter,
    check_api_server_requirements,
    AIOHTTP_AVAILABLE,
)

__all__ = [
    "OpenAIAdapter",
    "create_openai_adapter",
    "check_api_server_requirements",
    "AIOHTTP_AVAILABLE",
]
