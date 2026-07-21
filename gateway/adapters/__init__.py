"""
adapters - 渠道适配器子模块

提供多种渠道适配器：
- HTTPAdapter: HTTP 网关适配器
- CLIAdapter: 命令行交互适配器
- OpenAIAdapter: OpenAI 兼容 API 适配器 (从 api/ 迁移)
- WeixinAdapter: 微信个人号适配器 (iLink Bot API)
"""

from .http_adapter import HTTPAdapter
from .cli_adapter import CLIAdapter
from .openai_adapter import (
    OpenAIAdapter,
    create_openai_adapter,
    create_api_server,  # 向后兼容别名
    check_api_server_requirements,
    AIOHTTP_AVAILABLE,
)
from .weixin_adapter import WeixinAdapter, qr_login, AIOHTTP_AVAILABLE as WEIXIN_AIOHTTP_AVAILABLE

__all__ = [
    "HTTPAdapter",
    "CLIAdapter",
    "OpenAIAdapter",
    "create_openai_adapter",
    "create_api_server",  # 向后兼容
    "check_api_server_requirements",
    "AIOHTTP_AVAILABLE",
    "WeixinAdapter",
    "qr_login",
    "WEIXIN_AIOHTTP_AVAILABLE",
]