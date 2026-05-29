#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整的日志管理模块 - Handsome Agent

提供统一的日志管理功能，包括：
- 多级别日志控制（简洁/适中/详细）
- 多输出目标（控制台、文件）
- 日志轮转功能
- 结构化日志支持
- 模块级别日志控制
- 统一的日志API

日志级别：
- brief: 只输出警告和错误
- moderate: 输出汇总日志和关键信息
- detailed: 输出所有日志

日志层架构：
- Access Layer (🚪): 用户接入层
- Decision Layer (🧠): 决策层
- Execution Layer (⚡): 执行层
"""

import logging
import logging.handlers
import sys
import os
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from functools import lru_cache


class LogConfig:
    """日志配置类"""
    
    def __init__(self):
        # 日志级别配置
        self.log_level: str = "moderate"
        self.console_enabled: bool = True
        self.file_enabled: bool = False
        self.file_path: str = "logs/handsome-agent.log"
        self.max_file_size: int = 10 * 1024 * 1024  # 10MB
        self.backup_count: int = 5
        self.enable_structured_logging: bool = False
        
        # 模块级别配置（可单独控制每个模块的日志级别）
        self.module_levels: Dict[str, int] = {}
        
        # 日志格式配置
        self.console_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        self.file_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s"
        self.date_format: str = "%Y-%m-%d %H:%M:%S"


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        
        # 添加额外字段
        if hasattr(record, "layer"):
            log_entry["layer"] = record.layer
        if hasattr(record, "module_name"):
            log_entry["module_name"] = record.module_name
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        
        return json.dumps(log_entry, ensure_ascii=False)


# 保存原始的 Logger 类
_original_logger_class = logging.Logger

class ConfiguredLogger(_original_logger_class):
    """自定义 Logger 类，确保新创建的 logger 使用正确的级别"""
    
    def __init__(self, name, level=logging.NOTSET):
        super().__init__(name, level)
        # 获取当前配置的日志级别
        try:
            manager = LogManager.get_instance()
            if hasattr(manager, '_current_level'):
                self.setLevel(manager._current_level)
        except Exception:
            # 如果无法获取配置，使用 root logger 的级别
            self.setLevel(logging.root.level)

class LogManager:
    """日志管理器 - 单例模式"""
    
    _instance = None
    _config: LogConfig = None
    _loggers: Dict[str, logging.Logger] = {}
    _handlers: List[logging.Handler] = []
    _current_level: int = logging.CRITICAL + 1  # 默认不输出日志
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._config = LogConfig()
            # 设置自定义的 Logger 类
            logging.setLoggerClass(ConfiguredLogger)
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> "LogManager":
        """获取日志管理器实例"""
        if cls._instance is None:
            cls._instance = LogManager()
        return cls._instance
    
    def configure(self, config: Dict[str, Any]) -> None:
        """配置日志管理器"""
        # 基础配置
        if "log_level" in config:
            self._config.log_level = config["log_level"]
        
        if "console_enabled" in config:
            self._config.console_enabled = config["console_enabled"]
        
        if "file_enabled" in config:
            self._config.file_enabled = config["file_enabled"]
        
        if "file_path" in config:
            self._config.file_path = config["file_path"]
        
        if "max_file_size" in config:
            self._config.max_file_size = config["max_file_size"]
        
        if "backup_count" in config:
            self._config.backup_count = config["backup_count"]
        
        if "enable_structured_logging" in config:
            self._config.enable_structured_logging = config["enable_structured_logging"]
        
        # 模块级别配置
        if "module_levels" in config:
            self._config.module_levels.update(config["module_levels"])
        
        # 初始化日志系统
        self._init_logging()
    
    def _init_logging(self) -> None:
        """初始化日志系统"""
        # 获取日志级别
        level = self._get_log_level(self._config.log_level)
        
        # 移除旧的处理器
        self._cleanup_handlers()
        
        # 创建格式化器
        if self._config.enable_structured_logging:
            formatter = StructuredFormatter(datefmt=self._config.date_format)
        else:
            formatter = logging.Formatter(
                fmt=self._config.console_format,
                datefmt=self._config.date_format
            )
        
        # 控制台处理器
        if self._config.console_enabled:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            console_handler.setFormatter(formatter)
            logging.root.addHandler(console_handler)
            self._handlers.append(console_handler)
        
        # 文件处理器（带轮转）
        if self._config.file_enabled:
            # 确保目录存在
            log_dir = os.path.dirname(self._config.file_path)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
            
            file_handler = logging.handlers.RotatingFileHandler(
                filename=self._config.file_path,
                maxBytes=self._config.max_file_size,
                backupCount=self._config.backup_count,
                encoding="utf-8"
            )
            file_handler.setLevel(level)
            
            # 文件使用更详细的格式
            if self._config.enable_structured_logging:
                file_formatter = StructuredFormatter(datefmt=self._config.date_format)
            else:
                file_formatter = logging.Formatter(
                    fmt=self._config.file_format,
                    datefmt=self._config.date_format
                )
            file_handler.setFormatter(file_formatter)
            logging.root.addHandler(file_handler)
            self._handlers.append(file_handler)
        
        # 设置 root logger 级别
        logging.root.setLevel(level)
        
        # 设置所有已存在的 logger 级别
        for logger_name in list(logging.Logger.manager.loggerDict.keys()):
            logger = logging.getLogger(logger_name)
            # 对于普通 logger，设置级别（如果没有专门的模块级别配置）
            if logger_name not in self._config.module_levels:
                logger.setLevel(level)
        
        # 设置模块级别
        self._apply_module_levels()
        
        # 保存当前级别，以便新创建的 logger 可以使用
        self._current_level = level
    
    def _cleanup_handlers(self) -> None:
        """清理所有处理器"""
        for handler in self._handlers:
            handler.close()
            if handler in logging.root.handlers:
                logging.root.removeHandler(handler)
        self._handlers.clear()
    
    def _apply_module_levels(self) -> None:
        """应用模块级别配置"""
        for module_name, level in self._config.module_levels.items():
            logger = logging.getLogger(module_name)
            logger.setLevel(level)
    
    def _get_log_level(self, level_str: str) -> int:
        """将字符串级别转换为 logging 级别"""
        level_map = {
            "brief": logging.CRITICAL + 1,  # 高于所有级别，不输出任何日志
            "moderate": logging.INFO,
            "detailed": logging.DEBUG,
            "warning": logging.WARNING,
            "info": logging.INFO,
            "debug": logging.DEBUG,
            "error": logging.ERROR,
            "critical": logging.CRITICAL,
        }
        return level_map.get(level_str.lower(), logging.INFO)
    
    def get_logger(self, name: str, layer: Optional[str] = None) -> logging.Logger:
        """获取指定名称的 logger"""
        if name not in self._loggers:
            logger = logging.getLogger(name)
            # 设置正确的日志级别
            level = self._get_log_level(self._config.log_level)
            logger.setLevel(level)
            
            # 如果有模块级别配置，应用它
            if name in self._config.module_levels:
                logger.setLevel(self._config.module_levels[name])
            
            # 添加 layer 属性
            if layer:
                logger.layer = layer
            
            self._loggers[name] = logger
        
        return self._loggers[name]
    
    def set_log_level(self, level: str) -> None:
        """动态设置日志级别"""
        self._config.log_level = level
        self._init_logging()
        
        # 同步更新 LayerLogger 的日志级别（保持向后兼容）
        try:
            from .layer_logger import LayerLogger
            LayerLogger.set_log_level(level)
        except ImportError:
            pass
    
    def set_module_level(self, module_name: str, level: str) -> None:
        """设置特定模块的日志级别"""
        log_level = self._get_log_level(level)
        self._config.module_levels[module_name] = log_level
        
        # 更新已存在的 logger
        if module_name in self._loggers:
            self._loggers[module_name].setLevel(log_level)
    
    def enable_file_logging(self, enabled: bool) -> None:
        """启用/禁用文件日志"""
        self._config.file_enabled = enabled
        self._init_logging()
    
    def get_current_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return {
            "log_level": self._config.log_level,
            "console_enabled": self._config.console_enabled,
            "file_enabled": self._config.file_enabled,
            "file_path": self._config.file_path,
            "max_file_size": self._config.max_file_size,
            "backup_count": self._config.backup_count,
            "enable_structured_logging": self._config.enable_structured_logging,
            "module_levels": self._config.module_levels,
        }


# 日志层定义
LOG_LAYERS = {
    "access": {"emoji": "🚪", "name": "接入层"},
    "decision": {"emoji": "🧠", "name": "决策层"},
    "execution": {"emoji": "⚡", "name": "执行层"},
    "system": {"emoji": "🔧", "name": "系统层"},
    "llm": {"emoji": "🤖", "name": "LLM层"},
    "tool": {"emoji": "🛠️", "name": "工具层"},
    "postprocess": {"emoji": "📝", "name": "后处理层"},
    "memory": {"emoji": "💾", "name": "记忆检索层"},
    "intent": {"emoji": "🎯", "name": "意图识别层"},
    "routing": {"emoji": "🔀", "name": "路由层"},
    "tool_select": {"emoji": "🔧", "name": "工具选择层"},
}


class LayerLogger:
    """分层日志封装器"""
    
    def __init__(self, name: str, layer: str = "system"):
        self._name = name
        self._layer = layer
        self._layer_info = LOG_LAYERS.get(layer, {"emoji": "📋", "name": layer})
        self._logger = LogManager.get_instance().get_logger(f"{self._layer_info['emoji']} [{self._layer_info['name']}]", layer)
        
        # 创建显示名称
        self._display_name = f"{self._layer_info['emoji']} [{self._layer_info['name']}]"
    
    def _format_msg(self, msg: str) -> str:
        """格式化日志消息（不添加额外前缀）"""
        return msg
    
    def debug(self, msg: str, **kwargs):
        """DEBUG级别日志 - 详细执行步骤（仅detailed模式显示）"""
        extra = kwargs.pop('extra', {})
        extra['layer'] = self._layer
        self._logger.debug(self._format_msg(msg), extra=extra, **kwargs)
    
    def info(self, msg: str, **kwargs):
        """INFO级别日志 - 汇总日志（moderate和detailed模式显示）"""
        extra = kwargs.pop('extra', {})
        extra['layer'] = self._layer
        self._logger.info(self._format_msg(msg), extra=extra, **kwargs)
    
    def summary(self, msg: str, **kwargs):
        """汇总日志 - 只在 moderate 和 detailed 模式显示（使用 INFO 级别）"""
        extra = kwargs.pop('extra', {})
        extra['layer'] = self._layer
        self._logger.info(self._format_msg(msg), extra=extra, **kwargs)
    
    def warning(self, msg: str, **kwargs):
        """WARNING级别日志 - 警告信息（所有模式显示）"""
        extra = kwargs.pop('extra', {})
        extra['layer'] = self._layer
        self._logger.warning(self._format_msg(msg), extra=extra, **kwargs)
    
    def error(self, msg: str, exc_info: bool = False, **kwargs):
        """ERROR级别日志 - 错误信息（所有模式显示）"""
        extra = kwargs.pop('extra', {})
        extra['layer'] = self._layer
        self._logger.error(self._format_msg(msg), exc_info=exc_info, extra=extra, **kwargs)
    
    def critical(self, msg: str, exc_info: bool = False, **kwargs):
        """CRITICAL级别日志 - 严重错误（所有模式显示）"""
        extra = kwargs.pop('extra', {})
        extra['layer'] = self._layer
        self._logger.critical(self._format_msg(msg), exc_info=exc_info, extra=extra, **kwargs)
    
    def log(self, level: int, msg: str, **kwargs):
        """自定义级别日志"""
        extra = kwargs.pop('extra', {})
        extra['layer'] = self._layer
        self._logger.log(level, self._format_msg(msg), extra=extra, **kwargs)


# 全局便捷函数
@lru_cache(maxsize=64)
def get_logger(name: str, layer: str = "system") -> LayerLogger:
    """获取分层日志器"""
    return LayerLogger(name, layer)


def get_access_logger(name: str = "access") -> LayerLogger:
    """获取接入层日志器"""
    return LayerLogger(name, "access")


def get_decision_logger(name: str = "decision") -> LayerLogger:
    """获取决策层日志器"""
    return LayerLogger(name, "decision")


def get_execution_logger(name: str = "execution") -> LayerLogger:
    """获取执行层日志器"""
    return LayerLogger(name, "execution")


def get_llm_logger(name: str = "llm") -> LayerLogger:
    """获取LLM层日志器"""
    return LayerLogger(name, "llm")


def get_tool_logger(name: str = "tool") -> LayerLogger:
    """获取工具层日志器"""
    return LayerLogger(name, "tool")


def get_access_logger(name: str = "access") -> LayerLogger:
    """获取接入层日志器"""
    return LayerLogger(name, "access")


def get_postprocess_logger(name: str = "postprocess") -> LayerLogger:
    """获取后处理层日志器"""
    return LayerLogger(name, "postprocess")


def get_memory_logger(name: str = "memory") -> LayerLogger:
    """获取记忆检索层日志器"""
    return LayerLogger(name, "memory")


def configure_logging(config: Optional[Dict[str, Any]] = None) -> None:
    """配置日志系统
    
    Args:
        config: 日志配置字典，或日志级别字符串（如 "brief", "moderate", "detailed"）
    """
    # 如果传入的是字符串（旧的调用方式），转换为字典
    if isinstance(config, str):
        config = {"log_level": config}
    
    if config is None:
        config = {}
    
    log_level = config.get("log_level", "moderate")
    
    if log_level == "brief":
        # brief 模式：添加 NullHandler 来阻止所有日志
        for handler in logging.root.handlers[:]:
            if not isinstance(handler, logging.NullHandler):
                logging.root.removeHandler(handler)
        logging.root.addHandler(logging.NullHandler())
        logging.root.setLevel(logging.CRITICAL + 1)
        return
    
    # 默认配置
    default_config = {
        "log_level": log_level,
        "console_enabled": True,
        "file_enabled": False,
        "file_path": "logs/handsome-agent.log",
        "max_file_size": 10 * 1024 * 1024,
        "backup_count": 5,
        "enable_structured_logging": False,
    }
    
    # 合并配置
    default_config.update(config)
    
    # 移除 NullHandler（如果有）
    for handler in logging.root.handlers[:]:
        if isinstance(handler, logging.NullHandler):
            logging.root.removeHandler(handler)
    
    # 初始化日志管理器
    LogManager.get_instance().configure(default_config)


def set_log_level(level: str) -> None:
    """设置全局日志级别"""
    LogManager.get_instance().set_log_level(level)


def get_log_level() -> str:
    """获取当前日志级别"""
    config = LogManager.get_instance().get_current_config()
    return config["log_level"]


def setup_logging_from_config(config: Dict[str, Any]) -> None:
    """从配置字典设置日志"""
    # 处理旧的配置格式（兼容 layer_logger）
    if "explanation_depth" in config:
        config.setdefault("log_level", config["explanation_depth"])
    
    if "preferences" in config and "explanation_depth" in config["preferences"]:
        config.setdefault("log_level", config["preferences"]["explanation_depth"])
    
    configure_logging(config)


# 模块导出
__all__ = [
    "LogManager",
    "LogConfig",
    "LayerLogger",
    "get_logger",
    "get_access_logger",
    "get_decision_logger",
    "get_execution_logger",
    "get_llm_logger",
    "get_tool_logger",
    "get_postprocess_logger",
    "get_memory_logger",
    "configure_logging",
    "set_log_level",
    "get_log_level",
    "setup_logging_from_config",
    "LOG_LAYERS",
]
