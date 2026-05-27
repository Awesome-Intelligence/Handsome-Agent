#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Layer-Aware Logging Module for Handsome Agent
Provides logging with consistent layer names and emojis.
Three-layer architecture: Access / Decision / Execution
"""

import logging
from functools import lru_cache


LAYER_EMOJI = {
    "access": "🚪",           # 接入层
    "decision": "🧠",         # 决策层
    "execution": "⚡",        # 执行层
}

LAYER_NAMES = {
    "access": "接入层",
    "decision": "决策层",
    "execution": "执行层",
}

SUB_LAYER_NAMES = {
    "memory": "记忆检索层",
    "planning": "规划层",
    "reflection": "反思层",
    "post_process": "后处理层",
    "intent": "意图识别层",
    "routing": "路由层",
    "summarization": "摘要层",
    "tool_select": "工具选择层",
    "knowledge": "知识层",
}


class LayerLoggerAdapter:
    """Logger adapter that automatically adds module name to log messages."""
    
    def __init__(self, layer: str, module: str = None, sub_layer: str = None):
        self.layer = layer
        self.sub_layer = sub_layer
        self.module = module or ""
        emoji = LAYER_EMOJI.get(layer, "📋")
        layer_name = LAYER_NAMES.get(layer, layer)
        if sub_layer and sub_layer in SUB_LAYER_NAMES:
            full_layer_name = f"{layer_name}-{SUB_LAYER_NAMES[sub_layer]}"
        elif sub_layer:
            full_layer_name = f"{layer_name}-{sub_layer}"
        else:
            full_layer_name = layer_name
        self._logger = logging.getLogger(f"{emoji} {full_layer_name}")
        self._layer_display = f"{emoji} [{full_layer_name}]"
    
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
    @lru_cache(maxsize=64)
    def get_logger(cls, layer: str, module: str = None, sub_layer: str = None) -> LayerLoggerAdapter:
        """Get a logger with the specified layer name, module name, and optional sub-layer."""
        return LayerLoggerAdapter(layer, module, sub_layer)
    
    @classmethod
    def clear_cache(cls):
        """Clear the logger cache."""
        cls._loggers.clear()
        cls.get_logger.cache_clear()


def get_layer_logger(layer: str, module: str = None, sub_layer: str = None) -> LayerLoggerAdapter:
    """Get a logger for the specified layer.
    
    Args:
        layer: The layer name (access, decision, execution)
        module: Optional module/class name to include in log messages
        sub_layer: Optional sub-layer name (memory, planning, reflection, post_process, 
                   intent, routing, summarization, tool_select, knowledge)
    
    Returns:
        LayerLoggerAdapter that prefixes messages with module name and layer info
    """
    return LayerLogger.get_logger(layer, module, sub_layer)


def access_logger() -> logging.Logger:
    """Get logger for access layer."""
    return get_layer_logger("access")


def decision_logger() -> logging.Logger:
    """Get logger for decision layer."""
    return get_layer_logger("decision")


def execution_logger() -> logging.Logger:
    """Get logger for execution layer."""
    return get_layer_logger("execution")


def user_logger() -> logging.Logger:
    """Get logger for user layer (deprecated - use access_logger)."""
    return get_layer_logger("access")


def control_logger() -> logging.Logger:
    """Get logger for control layer (deprecated - use decision_logger)."""
    return get_layer_logger("decision")


def reasoning_logger() -> logging.Logger:
    """Get logger for reasoning layer (deprecated - use decision_logger)."""
    return get_layer_logger("decision")


def llm_logger() -> logging.Logger:
    """Get logger for LLM layer (deprecated - use decision_logger)."""
    return get_layer_logger("decision")


def tools_logger() -> logging.Logger:
    """Get logger for tools layer (deprecated - use execution_logger)."""
    return get_layer_logger("execution")


def storage_logger() -> logging.Logger:
    """Get logger for storage layer (deprecated - use execution_logger)."""
    return get_layer_logger("execution")