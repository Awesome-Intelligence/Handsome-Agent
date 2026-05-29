#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Layer-Aware Logging Module for Handsome Agent
Provides logging with consistent layer names and emojis.
Three-layer architecture: Access / Decision / Execution

支持三级日志模式：
- brief: 只输出警告和错误（简洁模式）
- moderate: 只输出汇总日志（适中模式）
- detailed: 输出所有日志（详细模式）
"""

import logging
import sys
from functools import lru_cache
from typing import Optional


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

LOG_LEVELS = {
    "brief": logging.CRITICAL + 1,  # 简洁模式：不输出任何日志
    "moderate": logging.INFO,       # 适中模式：输出汇总日志
    "detailed": logging.DEBUG,     # 详细模式：输出所有日志
}

LOG_LEVEL_DESCRIPTIONS = {
    "brief": "简洁模式（只显示警告和错误）",
    "moderate": "适中模式（显示关键信息）",
    "detailed": "详细模式（显示所有处理步骤）",
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
        
        # 禁用 propagate，防止日志重复输出到 root handler
        self._logger.propagate = False
        
        # 添加独立的 handler（不使用 root handler）
        self._handler = None
        self._update_handler()
    
    def _update_handler(self):
        """更新 handler 的日志级别"""
        # 移除旧的 handler
        if self._handler is not None:
            if self._handler in self._logger.handlers:
                self._logger.removeHandler(self._handler)
            self._handler.close()
        
        # 创建新的 handler
        self._handler = logging.StreamHandler(sys.stdout)
        self._handler.setLevel(LayerLogger._log_level)
        self._handler.setFormatter(logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        self._logger.addHandler(self._handler)
        self._logger.setLevel(LayerLogger._log_level)
    
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
    """Layer-aware logger factory with log level control."""
    
    _loggers = {}
    _log_level = logging.CRITICAL + 1  # 默认不输出日志（等待配置）
    _summary_mode = False
    
    @classmethod
    def set_log_level(cls, level: str = "detailed"):
        """设置日志级别.
        
        Args:
            level: 日志级别
                - "brief": 只输出警告和错误
                - "moderate": 只输出汇总日志
                - "detailed": 输出所有日志
        """
        cls._log_level = LOG_LEVELS.get(level, logging.DEBUG)
        cls._update_all_loggers_level()
    
    @classmethod
    def set_summary_mode(cls, enabled: bool = True):
        """设置汇总模式.
        
        汇总模式下，只输出关键日志（如流程汇总、错误等）
        """
        cls._summary_mode = enabled
        cls._update_all_loggers_level()
    
    @classmethod
    def _update_all_loggers_level(cls):
        """更新所有 logger 的级别."""
        # 更新 LayerLogger._loggers 中的 logger
        for logger in cls._loggers.values():
            if hasattr(logger, '_logger'):
                logger._logger.setLevel(cls._log_level)
                if hasattr(logger, '_update_handler'):
                    logger._update_handler()
        
        # 更新所有已创建的 logger（包括 LayerLoggerAdapter 创建的）
        for logger_name in list(logging.Logger.manager.loggerDict.keys()):
            logger = logging.getLogger(logger_name)
            logger.setLevel(cls._log_level)
    
    @classmethod
    @lru_cache(maxsize=64)
    def get_logger(cls, layer: str, module: str = None, sub_layer: str = None) -> LayerLoggerAdapter:
        """Get a logger with the specified layer name, module name, and optional sub-layer."""
        logger = LayerLoggerAdapter(layer, module, sub_layer)
        # 设置正确的日志级别
        logger._logger.setLevel(cls._log_level)
        return logger
    
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


def configure_logging(depth: str = "detailed") -> None:
    """配置日志系统.
    
    Args:
        depth: 日志详细程度
            - "brief": 只输出警告和错误
            - "moderate": 只输出汇总日志
            - "detailed": 输出所有日志（默认）
    """
    level = LOG_LEVELS.get(depth, logging.DEBUG)
    
    # 重置 logging 配置
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 显式设置 root logger 级别
    logging.root.setLevel(level)
    
    # 设置所有已有 logger 的级别（包括子 logger）并禁用 propagate
    for logger_name, logger in logging.Logger.manager.loggerDict.items():
        if isinstance(logger, logging.Logger):
            logger.propagate = False
            if depth in ["brief", "moderate"]:
                logger.setLevel(level)
                for handler in logger.handlers:
                    handler.setLevel(level)
            else:
                logger.setLevel(logging.DEBUG)
                for handler in logger.handlers:
                    handler.setLevel(logging.DEBUG)
    
    # 另外，强制设置特定的 logger 级别，确保它们不输出不需要的信息
    if depth in ["brief", "moderate"]:
        restricted_loggers = [
            "Session",
            "SessionManager",
            "IntentClassifier",
        ]
        for logger_name in restricted_loggers:
            restricted_logger = logging.getLogger(logger_name)
            restricted_logger.setLevel(logging.WARNING)
            for handler in restricted_logger.handlers:
                handler.setLevel(logging.WARNING)
    
    LayerLogger.set_log_level(depth)
    
    return level


def get_log_level_description() -> str:
    """获取当前日志级别的描述."""
    for name, desc in LOG_LEVEL_DESCRIPTIONS.items():
        if LayerLogger._log_level == LOG_LEVELS[name]:
            return f"{name}: {desc}"
    return "unknown"


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