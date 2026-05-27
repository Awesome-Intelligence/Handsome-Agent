"""adapters - 渠道适配器子模块"""
from .http_adapter import HTTPAdapter
from .cli_adapter import CLIAdapter

__all__ = ["HTTPAdapter", "CLIAdapter"]