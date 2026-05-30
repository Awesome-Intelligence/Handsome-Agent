#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整的日志管理模块 - Handsome Agent

参考 OpenClaw 的日志系统设计，提供：
- 多级别日志控制（brief/moderate/detailed）
- 多输出目标（控制台、文件 JSONL）
- 控制台样式（pretty/compact/json）
- 子系统自动颜色分配
- 日志层架构（主层 + 子层）
"""

import logging
import logging.handlers
import sys
import os
import json
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from functools import lru_cache
from pathlib import Path
import threading


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

# 控制台样式颜色（用于子系统）
SUBSYSTEM_COLORS = ["cyan", "green", "yellow", "blue", "magenta", "red"]

# 控制台样式枚举
class ConsoleStyle:
    PRETTY = "pretty"
    COMPACT = "compact"
    JSON = "json"


class LogConfig:
    """日志配置类"""
    
    def __init__(self):
        self.log_level: str = "moderate"
        self.console_enabled: bool = True
        self.file_enabled: bool = False
        self.file_path: str = "logs/handsome-agent.log"
        self.console_style: str = ConsoleStyle.PRETTY
        self.max_file_size: int = 10 * 1024 * 1024
        self.backup_count: int = 5
        self.module_levels: Dict[str, int] = {}
        self.date_format: str = "%Y-%m-%d %H:%M:%S"


def _get_subsystem_color(subsystem: str) -> Tuple[int, int, int]:
    """根据 subsystem 名称生成一致的 RGB 颜色"""
    hash_val = int(hashlib.md5(subsystem.encode()).hexdigest()[:6], 16)
    r = (hash_val >> 16) & 0xFF
    g = (hash_val >> 8) & 0xFF
    b = hash_val & 0xFF
    return (r, g, b)


def _get_ansi_color(r: int, g: int, b: int) -> str:
    """将 RGB 转换为 ANSI 256 色"""
    return f"\033[38;5;{16 + 36 * (r // 51) + 6 * (g // 51) + (b // 51)}m"


class ColoredFormatter(logging.Formatter):
    """带颜色的格式化器"""
    
    def __init__(self, style: str = ConsoleStyle.PRETTY, date_format: str = "%Y-%m-%d %H:%M:%S"):
        super().__init__(datefmt=date_format)
        self.style = style
        self.date_format = date_format
        
        # ANSI 颜色代码
        self.COLORS = {
            "black": "\033[30m",
            "red": "\033[31m",
            "green": "\033[32m",
            "yellow": "\033[33m",
            "blue": "\033[34m",
            "magenta": "\033[35m",
            "cyan": "\033[36m",
            "white": "\033[37m",
            "reset": "\033[0m",
            "dim": "\033[2m",
        }
    
    def _colorize_subsystem(self, subsystem: str, text: str) -> str:
        """为 subsystem 添加颜色"""
        r, g, b = _get_subsystem_color(subsystem)
        color = _get_ansi_color(r, g, b)
        return f"{color}{text}{self.COLORS['reset']}"
    
    def _format_pretty(self, record: logging.LogRecord) -> str:
        """Pretty 格式：带时间戳、层级，无颜色"""
        timestamp = datetime.fromtimestamp(record.created).strftime(self.date_format)
        
        # 获取 subsystem（logger name）
        subsystem = record.name if record.name else "root"
        
        # 获取日志级别（无颜色）
        level = record.levelname
        
        # 格式化消息
        message = record.getMessage()
        
        return f"{timestamp} - {subsystem} - {level} - {message}"
    
    def _format_compact(self, record: logging.LogRecord) -> str:
        """Compact 格式：无时间戳，紧凑"""
        level = record.levelname[:1]
        subsystem = record.name if record.name else "root"
        message = record.getMessage()
        
        return f"[{subsystem}] {level}: {message}"
    
    def _format_json(self, record: logging.LogRecord) -> str:
        """JSON 格式：结构化输出"""
        log_entry = {
            "ts": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "subsystem": record.name,
            "message": record.getMessage(),
        }
        
        # 添加额外字段
        if hasattr(record, "layer"):
            log_entry["layer"] = record.layer
        if hasattr(record, "session_id"):
            log_entry["session_id"] = record.session_id
        if hasattr(record, "agent_id"):
            log_entry["agent_id"] = record.agent_id
            
        return json.dumps(log_entry, ensure_ascii=False)
    
    def format(self, record: logging.LogRecord) -> str:
        if self.style == ConsoleStyle.COMPACT:
            return self._format_compact(record)
        elif self.style == ConsoleStyle.JSON:
            return self._format_json(record)
        else:  # PRETTY
            return self._format_pretty(record)


class JSONLFileHandler(logging.Handler):
    """JSONL 文件处理器"""
    
    def __init__(self, filename: str, max_bytes: int = 10 * 1024 * 1024, backup_count: int = 5):
        super().__init__()
        
        self.filename = Path(filename)
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        
        # 确保目录存在
        self.filename.parent.mkdir(parents=True, exist_ok=True)
        
        # 文件锁（用于多线程安全）
        self._lock = threading.Lock()
        
        # 打开文件
        self._file = open(self.filename, 'a', encoding='utf-8')
    
    def emit(self, record: logging.LogRecord) -> None:
        """输出日志到文件"""
        try:
            with self._lock:
                # 检查文件大小
                self._file.seek(0, 2)  # 移到文件末尾
                if self._file.tell() >= self.max_bytes:
                    self._rotate()
                
                # 构建 JSON 日志
                log_entry = {
                    "ts": datetime.fromtimestamp(record.created).isoformat(),
                    "level": record.levelname,
                    "subsystem": record.name,
                    "message": record.getMessage(),
                }
                
                # 添加额外字段
                if hasattr(record, "layer"):
                    log_entry["layer"] = record.layer
                if hasattr(record, "session_id"):
                    log_entry["session_id"] = record.session_id
                if hasattr(record, "agent_id"):
                    log_entry["agent_id"] = record.agent_id
                    
                # 写入文件
                self._file.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
                self._file.flush()
                
        except Exception:
            self.handleError(record)
    
    def _rotate(self) -> None:
        """轮转日志文件"""
        self._file.close()
        
        # 移动旧文件
        for i in range(self.backup_count - 1, 0, -1):
            old_file = self.filename.with_suffix(f".{i}")
            new_file = self.filename.with_suffix(f".{i + 1}")
            if old_file.exists():
                old_file.rename(new_file)
        
        # 重命名当前文件
        self._file = self.filename.with_suffix(".1")
        if self._file.exists():
            self._file.unlink()
        
        # 打开新文件
        self._file = open(self.filename, 'a', encoding='utf-8')
    
    def close(self) -> None:
        """关闭文件"""
        with self._lock:
            if hasattr(self, '_file') and self._file:
                self._file.close()
        super().close()


# 恢复原始的 Logger 类
_original_logger_class = logging.Logger

class ConfiguredLogger(_original_logger_class):
    """自定义 Logger 类"""
    
    def __init__(self, name, level=logging.NOTSET):
        super().__init__(name, level)
        try:
            manager = LogManager.get_instance()
            if hasattr(manager, '_current_level'):
                self.setLevel(manager._current_level)
        except Exception:
            self.setLevel(logging.root.level)


class LogManager:
    """日志管理器 - 单例模式"""
    
    _instance = None
    _config: LogConfig = None
    _loggers: Dict[str, logging.Logger] = {}
    _handlers: List[logging.Handler] = []
    _current_level: int = logging.CRITICAL + 1
    _console_handler: Optional[ColoredFormatter] = None
    _file_handler: Optional[JSONLFileHandler] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._config = LogConfig()
            logging.setLoggerClass(ConfiguredLogger)
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> "LogManager":
        if cls._instance is None:
            cls._instance = LogManager()
        return cls._instance
    
    def configure(self, config: Dict[str, Any]) -> None:
        """配置日志管理器"""
        if "log_level" in config:
            self._config.log_level = config["log_level"]
        if "console_enabled" in config:
            self._config.console_enabled = config["console_enabled"]
        if "file_enabled" in config:
            self._config.file_enabled = config["file_enabled"]
        if "file_path" in config:
            self._config.file_path = config["file_path"]
        if "console_style" in config:
            self._config.console_style = config["console_style"]
        if "max_file_size" in config:
            self._config.max_file_size = config["max_file_size"]
        if "backup_count" in config:
            self._config.backup_count = config["backup_count"]
        if "module_levels" in config:
            self._config.module_levels.update(config["module_levels"])
        
        self._init_logging()
    
    def _init_logging(self) -> None:
        """初始化日志系统"""
        level = self._get_log_level(self._config.log_level)
        
        # 清理旧处理器
        self._cleanup_handlers()
        
        # 创建控制台格式化器
        console_formatter = ColoredFormatter(
            style=self._config.console_style,
            date_format=self._config.date_format
        )
        
        # 控制台处理器
        if self._config.console_enabled:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            console_handler.setFormatter(console_formatter)
            logging.root.addHandler(console_handler)
            self._handlers.append(console_handler)
            self._console_handler = console_handler
        
        # JSONL 文件处理器
        if self._config.file_enabled:
            self._file_handler = JSONLFileHandler(
                filename=self._config.file_path,
                max_bytes=self._config.max_file_size,
                backup_count=self._config.backup_count
            )
            self._file_handler.setLevel(level)
            
            # 文件不需要 ColoredFormatter，使用基本格式化
            file_formatter = logging.Formatter(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt=self._config.date_format
            )
            self._file_handler.setFormatter(file_formatter)
            logging.root.addHandler(self._file_handler)
            self._handlers.append(self._file_handler)
        
        # 设置 root logger 级别
        logging.root.setLevel(level)
        logging.root.propagate = False
        
        # 更新现有 logger
        for logger_name in list(logging.Logger.manager.loggerDict.keys()):
            logger = logging.getLogger(logger_name)
            if logger_name not in self._config.module_levels:
                logger.setLevel(level)
            
            # 更新所有 handler 的 formatter
            console_formatter = ColoredFormatter(
                style=self._config.console_style,
                date_format=self._config.date_format
            )
            for handler in logger.handlers:
                if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                    handler.setFormatter(console_formatter)
        
        self._apply_module_levels()
        self._current_level = level
    
    def _cleanup_handlers(self) -> None:
        """清理所有处理器"""
        for handler in self._handlers:
            handler.close()
            if handler in logging.root.handlers:
                logging.root.removeHandler(handler)
        
        # 清理所有 logger 的 handler（不包括 root logger 的）
        for logger_name in list(logging.Logger.manager.loggerDict.keys()):
            logger = logging.getLogger(logger_name)
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
        
        self._handlers.clear()
    
    def _apply_module_levels(self) -> None:
        """应用模块级别配置"""
        for module_name, level in self._config.module_levels.items():
            logger = logging.getLogger(module_name)
            logger.setLevel(level)
    
    def _get_log_level(self, level_str: str) -> int:
        """将字符串级别转换为 logging 级别"""
        level_map = {
            "brief": logging.CRITICAL + 1,
            "moderate": logging.INFO,
            "detailed": logging.DEBUG,
            "warning": logging.WARNING,
            "info": logging.INFO,
            "debug": logging.DEBUG,
            "error": logging.ERROR,
            "trace": logging.DEBUG - 1,
        }
        return level_map.get(level_str, logging.INFO)
    
    def get_logger(self, name: str, layer: str = None) -> logging.Logger:
        """获取指定名称的 logger"""
        if name not in self._loggers:
            self._loggers[name] = logging.getLogger(name)
            self._loggers[name].setLevel(self._current_level)
            
            # 如果指定了 layer，记录到日志中
            if layer:
                self._loggers[name].layer = layer
        
        return self._loggers[name]
    
    def get_current_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return {
            "log_level": self._config.log_level,
            "console_enabled": self._config.console_enabled,
            "file_enabled": self._config.file_enabled,
            "file_path": self._config.file_path,
            "console_style": self._config.console_style,
        }


@lru_cache(maxsize=128)
def get_logger(name: str, layer: str = None) -> logging.Logger:
    """获取指定名称的 logger（带缓存）"""
    return LogManager.get_instance().get_logger(name, layer)


class LayerLogger:
    """分层日志封装器"""
    
    def __init__(self, name: str, layer: str = "system"):
        self._name = name
        self._layer = layer
        self._layer_info = LOG_LAYERS.get(layer, {"emoji": "📋", "name": layer})
        self._logger = LogManager.get_instance().get_logger(f"{self._layer_info['emoji']} [{self._layer_info['name']}]", layer)
        
        # 获取 layer emoji 用于消息中
        self._layer_emoji = self._layer_info['emoji']
        self._layer_name = self._layer_info['name']
    
    def _format_msg(self, msg: str) -> str:
        """格式化日志消息"""
        return msg
    
    def debug(self, msg: str, **kwargs):
        extra = kwargs.pop('extra', {})
        extra['layer'] = self._layer
        self._logger.debug(self._format_msg(msg), extra=extra, **kwargs)
    
    def info(self, msg: str, **kwargs):
        extra = kwargs.pop('extra', {})
        extra['layer'] = self._layer
        self._logger.info(self._format_msg(msg), extra=extra, **kwargs)
    
    def summary(self, msg: str, **kwargs):
        """汇总日志 - 在 moderate 和 detailed 模式显示（使用 INFO 级别）"""
        extra = kwargs.pop('extra', {})
        extra['layer'] = self._layer
        self._logger.info(self._format_msg(msg), extra=extra, **kwargs)
    
    def warning(self, msg: str, **kwargs):
        extra = kwargs.pop('extra', {})
        extra['layer'] = self._layer
        self._logger.warning(self._format_msg(msg), extra=extra, **kwargs)
    
    def error(self, msg: str, exc_info: bool = False, **kwargs):
        extra = kwargs.pop('extra', {})
        extra['layer'] = self._layer
        self._logger.error(self._format_msg(msg), exc_info=exc_info, extra=extra, **kwargs)


# 便捷的日志器获取函数
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

def get_postprocess_logger(name: str = "postprocess") -> LayerLogger:
    """获取后处理层日志器"""
    return LayerLogger(name, "postprocess")

def get_memory_logger(name: str = "memory") -> LayerLogger:
    """获取记忆检索层日志器"""
    return LayerLogger(name, "memory")


def configure_logging(config: Optional[Dict[str, Any]] = None) -> None:
    """配置日志系统
    
    Args:
        config: 日志配置字典，支持的键：
            - log_level: brief/moderate/detailed
            - console_enabled: 是否启用控制台输出
            - file_enabled: 是否启用文件输出
            - file_path: 日志文件路径
            - console_style: pretty/compact/json
            - max_file_size: 最大文件大小
            - backup_count: 备份文件数量
    """
    if isinstance(config, str):
        config = {"log_level": config}
    if config is None:
        config = {}
    
    log_level = config.get("log_level", "moderate")
    
    if log_level == "brief":
        for handler in logging.root.handlers[:]:
            if not isinstance(handler, logging.NullHandler):
                logging.root.removeHandler(handler)
        logging.root.addHandler(logging.NullHandler())
        logging.root.setLevel(logging.CRITICAL + 1)
        return
    
    LogManager.get_instance().configure(config)


def set_log_level(level: str) -> None:
    """设置日志级别"""
    config = {"log_level": level}
    LogManager.get_instance().configure(config)


def get_log_level() -> str:
    """获取当前日志级别"""
    config = LogManager.get_instance().get_current_config()
    return config["log_level"]


def setup_logging_from_config(config: Dict[str, Any]) -> None:
    """从配置字典设置日志"""
    if "explanation_depth" in config:
        config.setdefault("log_level", config["explanation_depth"])
    if "preferences" in config and "explanation_depth" in config["preferences"]:
        config.setdefault("log_level", config["preferences"]["explanation_depth"])
    configure_logging(config)


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
    "ConsoleStyle",
]