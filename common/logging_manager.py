#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Logging Manager Module - Handsome Agent

Based on OpenClaw's logging system design, provides:
- Multi-level log control (brief/moderate/detailed)
- Multi-output targets (console, JSONL file)
- Console styles (pretty/compact/json)
- Automatic subsystem color assignment
- Log layer architecture (main layer + sublayer)
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


# Log layer definitions
LOG_LAYERS = {
    # Three-tier architecture main layers
    "access": {"emoji": "🚪", "name": "Access"},
    "decision": {"emoji": "🧠", "name": "Decision"},
    "execution": {"emoji": "🏃", "name": "Execution"},
    
    # System-level auxiliary layer
    "system": {"emoji": "🔧", "name": "System"},
}

# Sub-layer definitions (for distinguishing modules within main layers)
SUB_LAYERS = {
    # Decision layer submodules
    "memory": {"emoji": "💾", "name": "Memory"},
    "skills": {"emoji": "📋", "name": "Skills"},
    "task": {"emoji": "✅", "name": "Task"},
    "trajectory": {"emoji": "📝", "name": "Trajectory"},
    "curator": {"emoji": "🔬", "name": "Curator"},
    "context": {"emoji": "📊", "name": "Context"},
    "llm": {"emoji": "🤖", "name": "LLM"},
    "tool_select": {"emoji": "🔧", "name": "ToolSelect"},
    
    # Execution layer submodules
    "tool_exec": {"emoji": "🛠️", "name": "ToolExec"},
    "shell_exec": {"emoji": "🐚", "name": "ShellExec"},
    "docker_exec": {"emoji": "🐳", "name": "DockerExec"},
    
    # Access layer submodules
    "api": {"emoji": "🌐", "name": "API"},
    "cli": {"emoji": "💬", "name": "CLI"},
    "gateway": {"emoji": "🚪", "name": "Gateway"},
}

# Console style colors (for subsystems)
SUBSYSTEM_COLORS = ["cyan", "green", "yellow", "blue", "magenta", "red"]

# Console style enum
class ConsoleStyle:
    PRETTY = "pretty"
    COMPACT = "compact"
    JSON = "json"


class LogConfig:
    """Log configuration class"""
    
    def __init__(self):
        from common.config import get_logs_dir
        self.log_level: str = "moderate"
        self.console_enabled: bool = True
        self.file_enabled: bool = False
        self.file_path: str = str(get_logs_dir() / "handsome-agent.log")
        self.console_style: str = ConsoleStyle.PRETTY
        self.console_show_time: bool = True  # 控制台是否显示时间
        self.max_file_size: int = 50 * 1024 * 1024  # 50MB per file
        self.backup_count: int = 30  # Keep 30 days of logs
        self.rotation: str = "daily"  # "daily"
        self.module_levels: Dict[str, int] = {}
        self.date_format: str = "%Y-%m-%d %H:%M:%S"

        # 默认禁用第三方库的 DEBUG 日志，避免过多的网络请求细节
        self._setup_third_party_log_levels()

    def _setup_third_party_log_levels(self) -> None:
        """设置第三方库的日志级别，减少过多输出"""
        # 网络请求库 - 设置为 WARNING 避免过多 HTTP 调试信息
        third_party_levels = {
            "httpx": logging.WARNING,
            "httpcore": logging.WARNING,
            "httpcore.connection": logging.WARNING,
            "httpcore.http11": logging.WARNING,
            "httpcore.http2": logging.WARNING,
            "urllib3": logging.WARNING,
            "requests": logging.WARNING,
            "aiohttp": logging.WARNING,
            "charset_normalizer": logging.WARNING,
            "certifi": logging.WARNING,
            # LLM SDK
            "openai": logging.WARNING,
            "anthropic": logging.WARNING,
            "litellm": logging.WARNING,
            "vllm": logging.WARNING,
            "tenacity": logging.WARNING,
            # 其他常见第三方库
            "http": logging.WARNING,
            "asyncio": logging.WARNING,
        }
        self.module_levels.update(third_party_levels)


def _get_subsystem_color(subsystem: str) -> Tuple[int, int, int]:
    """Generate consistent RGB color based on subsystem name"""
    hash_val = int(hashlib.md5(subsystem.encode()).hexdigest()[:6], 16)
    r = (hash_val >> 16) & 0xFF
    g = (hash_val >> 8) & 0xFF
    b = hash_val & 0xFF
    return (r, g, b)


def _get_ansi_color(r: int, g: int, b: int) -> str:
    """Convert RGB to ANSI 256 color"""
    return f"\033[38;5;{16 + 36 * (r // 51) + 6 * (g // 51) + (b // 51)}m"


class ColoredFormatter(logging.Formatter):
    """Colorful log formatter"""
    
    def __init__(self, style: str = ConsoleStyle.PRETTY, date_format: str = "%Y-%m-%d %H:%M:%S", show_time: bool = True):
        super().__init__(datefmt=date_format)
        self.style = style
        self.date_format = date_format
        self.show_time = show_time
        
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
        """Add color to subsystem"""
        r, g, b = _get_subsystem_color(subsystem)
        color = _get_ansi_color(r, g, b)
        return f"{color}{text}{self.COLORS['reset']}"
    
    def _format_pretty(self, record: logging.LogRecord) -> str:
        """Pretty 格式：带/不带时间戳、层级，根据级别着色"""
        if self.show_time:
            timestamp = datetime.fromtimestamp(record.created).strftime(self.date_format) + " - "
        else:
            timestamp = ""
        
        # 获取 subsystem（logger name）
        subsystem = record.name if record.name else "root"
        
        # 获取日志级别
        level = record.levelname
        level_colored = level
        
        # 根据日志级别着色
        if record.levelno == logging.DEBUG:
            # DEBUG 整行灰色（dim）- 在任何背景上都清晰
            dim = self.COLORS['dim']
            reset = self.COLORS['reset']
            return f"{dim}{timestamp}{level} - {subsystem} - {record.getMessage()}{reset}"
        elif record.levelno == logging.ERROR:
            # 红色 - 在任何背景上都清晰
            level_colored = f"{self.COLORS['red']}{level}{self.COLORS['reset']}"
        elif record.levelno == logging.WARNING:
            # 黄色 - 警告级别
            level_colored = f"{self.COLORS['yellow']}{level}{self.COLORS['reset']}"
        # INFO 保持默认（白色/无色）
        
        # 格式化消息
        message = record.getMessage()
        
        return f"{timestamp}{level_colored} - {subsystem} - {message}"
    
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
    """JSONL file handler with daily rotation and automatic splitting if too large"""
    
    def __init__(self, filename: str, max_bytes: int = 50 * 1024 * 1024, backup_count: int = 30, rotation: str = "daily"):
        super().__init__()
        
        self.base_filename = Path(filename)
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.rotation = rotation
        
        # Current date for daily rotation
        self._current_date = datetime.now().strftime("%Y-%m-%d")
        self._daily_index = 0  # Index for files within same day
        
        # Ensure directory exists
        self.base_filename.parent.mkdir(parents=True, exist_ok=True)
        
        # File lock (for thread safety)
        self._lock = threading.Lock()
        
        # Get current filename and open file
        self.filename = self._get_filename()
        self._file = open(self.filename, 'a', encoding='utf-8')
    
    def _get_filename(self) -> Path:
        """Get current log filename based on rotation mode"""
        if self.rotation == "daily":
            if self._daily_index == 0:
                return self.base_filename.parent / f"{self.base_filename.stem}-{self._current_date}{self.base_filename.suffix}"
            else:
                return self.base_filename.parent / f"{self.base_filename.stem}-{self._current_date}_{self._daily_index}{self.base_filename.suffix}"
        return self.base_filename
    
    def emit(self, record: logging.LogRecord) -> None:
        """Emit log to file"""
        try:
            with self._lock:
                # Check daily rotation
                if self.rotation == "daily":
                    current_date = datetime.now().strftime("%Y-%m-%d")
                    if current_date != self._current_date:
                        # New day, reset
                        self._rotate()
                        self._current_date = current_date
                        self._daily_index = 0
                        self.filename = self._get_filename()
                        self._file = open(self.filename, 'a', encoding='utf-8')
                    else:
                        # Check size within same day
                        self._file.seek(0, 2)
                        if self._file.tell() >= self.max_bytes:
                            self._daily_index += 1
                            self._rotate()
                            self.filename = self._get_filename()
                            self._file = open(self.filename, 'a', encoding='utf-8')
                
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
        """Rotate log file - close current file, cleanup old files"""
        self._file.close()
        
        # Cleanup old log files based on backup_count (days to keep)
        if self.rotation == "daily":
            self._cleanup_old_files()
    
    def _cleanup_old_files(self) -> None:
        """Clean up log files older than backup_count days"""
        try:
            import time
            pattern = f"{self.base_filename.stem}-*.log"
            cutoff_time = time.time() - (self.backup_count * 24 * 60 * 60)
            
            for old_file in self.base_filename.parent.glob(pattern):
                if old_file.stat().st_mtime < cutoff_time:
                    old_file.unlink()
        except Exception:
            pass
    
    def close(self) -> None:
        """Close file"""
        with self._lock:
            if hasattr(self, '_file') and self._file:
                self._file.close()
        super().close()


# Restore original Logger class
_original_logger_class = logging.Logger

class ConfiguredLogger(_original_logger_class):
    """Custom Logger class"""
    
    def __init__(self, name, level=logging.NOTSET):
        super().__init__(name, level)
        try:
            manager = LogManager.get_instance()
            if hasattr(manager, '_current_level'):
                self.setLevel(manager._current_level)
        except Exception:
            self.setLevel(logging.root.level)


class LogManager:
    """Log Manager - Singleton pattern"""
    
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
        """Configure log manager"""
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
        if "console_show_time" in config:
            self._config.console_show_time = config["console_show_time"]
        if "max_file_size" in config:
            self._config.max_file_size = config["max_file_size"]
        if "backup_count" in config:
            self._config.backup_count = config["backup_count"]
        if "rotation" in config:
            self._config.rotation = config["rotation"]
        if "module_levels" in config:
            self._config.module_levels.update(config["module_levels"])
        
        self._init_logging()
    
    def _init_logging(self) -> None:
        """Initialize logging system"""
        level = self._get_log_level(self._config.log_level)
        
        # Cleanup old handlers
        self._cleanup_handlers()
        
        # Create console formatter
        console_formatter = ColoredFormatter(
            style=self._config.console_style,
            date_format=self._config.date_format,
            show_time=self._config.console_show_time
        )
        
        # Console handler
        if self._config.console_enabled:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            console_handler.setFormatter(console_formatter)
            logging.root.addHandler(console_handler)
            self._handlers.append(console_handler)
            self._console_handler = console_handler
        
        # JSONL file handler
        if self._config.file_enabled:
            self._file_handler = JSONLFileHandler(
                filename=self._config.file_path,
                max_bytes=self._config.max_file_size,
                backup_count=self._config.backup_count,
                rotation=self._config.rotation
            )
            self._file_handler.setLevel(level)
            
            # File doesn't need ColoredFormatter, use basic formatter
            file_formatter = logging.Formatter(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt=self._config.date_format
            )
            self._file_handler.setFormatter(file_formatter)
            logging.root.addHandler(self._file_handler)
            self._handlers.append(self._file_handler)
        
        # Set root logger level
        logging.root.setLevel(level)
        logging.root.propagate = False
        
        # Update existing loggers
        for logger_name in list(logging.Logger.manager.loggerDict.keys()):
            logger = logging.getLogger(logger_name)
            if logger_name not in self._config.module_levels:
                logger.setLevel(level)
            
            # Update formatter for all handlers
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
        """Cleanup all handlers"""
        for handler in self._handlers:
            handler.close()
            if handler in logging.root.handlers:
                logging.root.removeHandler(handler)
        
        # Cleanup handlers for all loggers (except root logger)
        for logger_name in list(logging.Logger.manager.loggerDict.keys()):
            logger = logging.getLogger(logger_name)
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
        
        self._handlers.clear()
    
    def _apply_module_levels(self) -> None:
        """Apply module level configuration"""
        for module_name, level in self._config.module_levels.items():
            logger = logging.getLogger(module_name)
            logger.setLevel(level)
    
    def _get_log_level(self, level_str: str) -> int:
        """Convert string level to logging level"""
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
        """Get logger with specified name"""
        if name not in self._loggers:
            self._loggers[name] = logging.getLogger(name)
            self._loggers[name].setLevel(self._current_level)
            
            # If layer is specified, record it in logger
            if layer:
                self._loggers[name].layer = layer
        
        return self._loggers[name]
    
    def get_current_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        return {
            "log_level": self._config.log_level,
            "console_enabled": self._config.console_enabled,
            "file_enabled": self._config.file_enabled,
            "file_path": self._config.file_path,
            "console_style": self._config.console_style,
        }


@lru_cache(maxsize=128)
def get_logger(name: str, layer: str = None) -> logging.Logger:
    """Get logger with specified name (cached)"""
    return LogManager.get_instance().get_logger(name, layer)


class LayerLogger:
    """Layered logger wrapper
    
    Log format specification:
    - With sublayer: INFO - [🧠Decision] - [/🤖LLM] - (ModuleName) message
    - Without sublayer: INFO - [🧠Decision] - (ModuleName) message
    
    Parameters:
        name: Module name (e.g., class name)
        layer: Main layer identifier (e.g., "access", "decision", "execution")
        sublayer: Sublayer identifier (optional, from SUB_LAYERS)
    """
    
    def __init__(self, name: str, layer: str = "system", sublayer: str = None):
        self._name = name
        self._layer = layer
        self._sublayer = sublayer
        
        # 获取主层信息
        self._layer_info = LOG_LAYERS.get(layer, {"emoji": "📋", "name": layer})
        self._logger = LogManager.get_instance().get_logger(f"[{self._layer_info['emoji']}{self._layer_info['name']}]", layer)
        
        # 获取主层 emoji 和名称
        self._layer_emoji = self._layer_info['emoji']
        self._layer_name = self._layer_info['name']
        
        # 获取子层信息（如果有）
        self._sublayer_info = SUB_LAYERS.get(sublayer) if sublayer else None
    
    def _format_msg(self, msg: str) -> str:
        """Format log message
        
        Format:
        - With sublayer: [/💾SublayerName] - (ModuleName) message
        - Without sublayer: (ModuleName) message
        """
        if self._sublayer_info:
            sublayer_emoji = self._sublayer_info['emoji']
            sublayer_name = self._sublayer_info['name']
            return f"[/{sublayer_emoji}{sublayer_name}] - ({self._name}) {msg}"
        else:
            return f"({self._name}) {msg}"
    
    def debug(self, *args, **kwargs):
        """Debug log - displayed in detailed mode only."""
        # 格式化消息（支持多个参数）
        if len(args) == 1:
            msg = str(args[0])
        else:
            msg = " ".join(str(arg) for arg in args)
        extra = kwargs.pop('extra', {})
        extra['layer'] = self._layer
        self._logger.debug(self._format_msg(msg), extra=extra, **kwargs)
    
    def info(self, msg: str, **kwargs):
        extra = kwargs.pop('extra', {})
        extra['layer'] = self._layer
        self._logger.info(self._format_msg(msg), extra=extra, **kwargs)
    
    def summary(self, msg: str, **kwargs):
        """Summary log - displayed in moderate and detailed modes (uses INFO level)"""
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


# Convenient logger getter functions
def get_access_logger(name: str = "access", sublayer: str = None) -> LayerLogger:
    """Get access layer logger"""
    return LayerLogger(name, "access", sublayer)

def get_decision_logger(name: str = "decision", sublayer: str = None) -> LayerLogger:
    """Get decision layer logger"""
    return LayerLogger(name, "decision", sublayer)

def get_execution_logger(name: str = "execution", sublayer: str = None) -> LayerLogger:
    """Get execution layer logger"""
    return LayerLogger(name, "execution", sublayer)

def get_llm_logger(name: str = "llm", sublayer: str = None) -> LayerLogger:
    """Get LLM layer logger (LLM is a sublayer under Decision layer)"""
    return LayerLogger(name, "decision", "llm")

def get_system_logger(name: str = "system", sublayer: str = None) -> LayerLogger:
    """Get system layer logger"""
    return LayerLogger(name, "system", sublayer)

def get_tool_logger(name: str = "tool", sublayer: str = None) -> LayerLogger:
    """Get tool layer logger (Tool is a sublayer under Execution layer)"""
    return LayerLogger(name, "execution", "tool_exec")

def get_postprocess_logger(name: str = "postprocess", sublayer: str = None) -> LayerLogger:
    """Get postprocess layer logger"""
    return LayerLogger(name, "decision", sublayer)

def get_memory_logger(name: str = "memory", sublayer: str = None) -> LayerLogger:
    """Get memory layer logger (Memory is a sublayer under Decision layer)"""
    return LayerLogger(name, "decision", "memory")

def get_task_logger(name: str = "task", sublayer: str = None) -> LayerLogger:
    """Get task layer logger"""
    return LayerLogger(name, "decision", sublayer)


def configure_logging(config: Optional[Dict[str, Any]] = None) -> None:
    """Configure logging system
    
    Args:
        config: Log configuration dictionary, supported keys:
            - log_level: brief/moderate/detailed
            - console_enabled: Enable console output
            - file_enabled: Enable file output
            - file_path: Log file path
            - console_style: pretty/compact/json
            - max_file_size: Maximum file size
            - backup_count: Number of backup files
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
    "get_task_logger",
    "configure_logging",
    "set_log_level",
    "get_log_level",
    "setup_logging_from_config",
    "LOG_LAYERS",
    "ConsoleStyle",
]