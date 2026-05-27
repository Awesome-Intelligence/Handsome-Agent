#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Layer-Aware Logging Module for Handsome Agent
Provides logging with consistent layer names and emojis.
"""

import logging
from functools import lru_cache


LAYER_EMOJI = {
    "user": "👤",           # 用户层
    "control": "🎛️",        # 控制层
    "reasoning": "🧠",       # 推理层
    "llm": "🤖",             # LLM层
    "tools": "🔧",           # 工具层
    "storage": "💾",        # 存储层
}

LAYER_NAMES = {
    "user": "用户层",
    "control": "控制层",
    "reasoning": "推理层",
    "llm": "LLM层",
    "tools": "工具层",
    "storage": "存储层",
}


class LayerLoggerAdapter:
    """Logger adapter that automatically adds module name to log messages."""
    
    def __init__(self, layer: str, module: str = None):
        self.layer = layer
        self.module = module or ""
        emoji = LAYER_EMOJI.get(layer, "📋")
        name = LAYER_NAMES.get(layer, layer)
        self._logger = logging.getLogger(f"{emoji} {name}")
    
    def _format_msg(self, msg: str) -> str:
        """Add module name to message if available."""
        if self.module:
            return f"[{self.module}] {msg}"
        return msg
    
    def debug(self, msg: str, *args, **kwargs):
        self._logger.debug(self._format_msg(msg), *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        self._logger.info(self._format_msg(msg), *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        self._logger.warning(self._format_msg(msg), *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        self._logger.error(self._format_msg(msg), *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs):
        self._logger.critical(self._format_msg(msg), *args, **kwargs)


class LayerLogger:
    """Layer-aware logger factory."""
    
    _loggers = {}
    
    @classmethod
    @lru_cache(maxsize=32)
    def get_logger(cls, layer: str, module: str = None) -> LayerLoggerAdapter:
        """Get a logger with the specified layer name and optional module name."""
        return LayerLoggerAdapter(layer, module)
    
    @classmethod
    def clear_cache(cls):
        """Clear the logger cache."""
        cls._loggers.clear()
        cls.get_logger.cache_clear()


def get_layer_logger(layer: str, module: str = None) -> LayerLoggerAdapter:
    """Get a logger for the specified layer.
    
    Args:
        layer: The layer name (user, control, reasoning, llm, tools, storage)
        module: Optional module/class name to include in log messages
    
    Returns:
        LayerLoggerAdapter that prefixes messages with module name
    """
    return LayerLogger.get_logger(layer, module)


def user_logger() -> logging.Logger:
    """Get logger for user layer."""
    return get_layer_logger("user")

def control_logger() -> logging.Logger:
    """Get logger for control layer."""
    return get_layer_logger("control")

def reasoning_logger() -> logging.Logger:
    """Get logger for reasoning layer."""
    return get_layer_logger("reasoning")

def llm_logger() -> logging.Logger:
    """Get logger for LLM layer."""
    return get_layer_logger("llm")

def tools_logger() -> logging.Logger:
    """Get logger for tools layer."""
    return get_layer_logger("tools")

def storage_logger() -> logging.Logger:
    """Get logger for storage layer."""
    return get_layer_logger("storage")
