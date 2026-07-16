#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""设置管理器 - 负责设置加载、保存和变更通知

与 CLI 共享同一份配置文件: ~/.agent_z/config.json
"""

from __future__ import annotations

import threading
from typing import Callable, Optional, Any

# i18n 支持
try:
    from common.i18n import get_i18n
except ImportError:

    def get_i18n():
        class SimpleI18n:
            def t(self, key, default=None, **kwargs):
                return default or key

        return SimpleI18n()


# 日志支持
try:
    from common.logging_manager import get_access_logger
except ImportError:
    import logging

    logging.basicConfig(level=logging.INFO)

    def get_access_logger(*args, **kwargs):
        return logging.getLogger("Agent")


class SettingsManager:
    """设置管理器 - 单例模式

    负责:
    - 从 CLI 配置加载设置
    - 保存设置到 CLI 配置 (config.json)
    - 设置变更通知
    """

    _instance: Optional["SettingsManager"] = None
    _lock = threading.RLock()

    def __init__(self):
        """初始化设置管理器"""
        self._settings = None  # 延迟加载
        self._listeners: list[Callable] = []
        self._dirty: bool = False
        self._logger = get_access_logger("SettingsManager", sublayer="tui")
        self._cli_config_module = None
        self._init_cli_config()

    def _init_cli_config(self) -> None:
        """初始化配置模块（自 v8.x 起从 common.config 加载，跨 cli/tui 共享）"""
        try:
            from common.config import load_config, save_config

            self._cli_config_module = {
                "load": load_config,
                "save": save_config,
            }
            self._logger.debug("Config module loaded from common.config")
        except ImportError as e:
            self._logger.warning(f"Failed to import common.config: {e}")
            self._cli_config_module = None

    def _load(self) -> None:
        """加载设置"""
        # 导入在这里进行，避免循环导入
        from tui.views.settings.models import SettingsDocument, TUI_DEFAULTS

        # 加载 CLI 配置
        cli_config = {}
        if self._cli_config_module:
            try:
                cli_config = self._cli_config_module["load"]()
                self._logger.debug("Loaded CLI config")
            except Exception as e:
                self._logger.warning(f"Failed to load CLI config: {e}")

        # 合并 TUI 默认值（如果 CLI 配置中没有）
        for key, value in TUI_DEFAULTS.items():
            if key not in cli_config:
                cli_config[key] = value

        self._settings = SettingsDocument.from_dict(cli_config)
        self._logger.debug("Settings loaded")

    @classmethod
    def get_instance(cls) -> "SettingsManager":
        """获取单例实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def save(self) -> bool:
        """保存设置到文件

        Returns:
            True if save succeeded
        """
        from tui.views.settings.models import SettingsDocument

        if not isinstance(self._settings, SettingsDocument):
            self._settings = SettingsDocument()

        try:
            # 转换为 CLI 配置格式
            cli_config = self._settings.to_dict()

            # 保存到 config.json
            if self._cli_config_module:
                self._cli_config_module["save"](cli_config)
                self._logger.info("Config saved to ~/.agent_z/config.json")

            self._dirty = False

            # 通知监听器
            self._notify_listeners()
            return True
        except Exception as e:
            self._logger.error(f"Failed to save settings: {e}")
            return False

    def get_settings(self):
        """获取当前设置

        Returns:
            SettingsDocument 实例
        """
        if self._settings is None:
            self._load()
        return self._settings

    def update(self, **kwargs) -> None:
        """更新设置

        Args:
            **kwargs: 要更新的设置键值对 (支持点号路径如 "llm.provider")
        """
        from tui.views.settings.models import SettingsDocument

        if self._settings is None:
            self._load()

        for key, value in kwargs.items():
            if "." in key:
                # 点号路径，如 "llm.provider"
                self._update_nested(key, value)
            elif hasattr(self._settings, key):
                setattr(self._settings, key, value)
                self._dirty = True
            else:
                self._logger.warning(f"Unknown setting key: {key}")

        if self._dirty:
            self._notify_listeners()

    def _update_nested(self, key_path: str, value: Any) -> None:
        """更新嵌套设置

        Args:
            key_path: 点号分隔的路径，如 "llm.provider"
            value: 要设置的值
        """
        parts = key_path.split(".")
        current = self._settings

        # 导航到父对象
        for part in parts[:-1]:
            if hasattr(current, part):
                current = getattr(current, part)
            elif isinstance(current, dict) and part in current:
                current = current[part]
            else:
                self._logger.warning(f"Unknown path: {key_path}")
                return

        # 设置值
        final_key = parts[-1]
        if hasattr(current, final_key):
            setattr(current, final_key, value)
            self._dirty = True
        elif isinstance(current, dict):
            current[final_key] = value
            self._dirty = True

    def update_category(self, category: str, **kwargs) -> None:
        """更新指定分类的设置

        Args:
            category: 分类 ID (如 "display", "llm", "model" 等)
            **kwargs: 要更新的设置
        """
        if self._settings is None:
            self._load()

        if hasattr(self._settings, category):
            category_obj = getattr(self._settings, category)
            for key, value in kwargs.items():
                if hasattr(category_obj, key):
                    setattr(category_obj, key, value)
                    self._dirty = True
                else:
                    self._logger.warning(f"Unknown {category} setting key: {key}")
        else:
            self._logger.warning(f"Unknown category: {category}")

        if self._dirty:
            self._notify_listeners()

    def add_listener(self, callback: Callable) -> None:
        """添加设置变更监听器

        Args:
            callback: 回调函数，接收 SettingsDocument 参数
        """
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback: Callable) -> None:
        """移除设置变更监听器

        Args:
            callback: 要移除的回调函数
        """
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self) -> None:
        """通知所有监听器"""
        for listener in self._listeners:
            try:
                listener(self._settings)
            except Exception as e:
                self._logger.error(f"Error in settings listener: {e}")

    def reset_to_defaults(self, category: Optional[str] = None) -> None:
        """重置设置为默认值

        Args:
            category: 要重置的分类，None 表示全部重置
        """
        from tui.views.settings.models import (
            SettingsDocument,
            LLMConfig,
            ModelSettingsConfig,
            DisplayConfig,
            PreferencesConfig,
            SessionConfig,
            MemoryConfig,
            TerminalConfig,
            ToolConfig,
            LoggingConfig,
            AgentConfig,
            SessionResetConfig,
            CompressionConfig,
            IntentMode,
            TUI_DEFAULTS,
        )

        if self._settings is None:
            self._load()

        if category is None:
            # 重置全部
            defaults = {
                "llm": LLMConfig(),
                "model_settings": ModelSettingsConfig(),
                "display": DisplayConfig(),
                "preferences": PreferencesConfig(),
                "session": SessionConfig(),
                "memory": MemoryConfig(),
                "terminal": TerminalConfig(),
                "tools": ToolConfig(),
                "logging": LoggingConfig(),
                "agent": AgentConfig(),
                "session_reset": SessionResetConfig(),
                "compression": CompressionConfig(),
                "intent_mode": IntentMode.LLM,
            }
            for key, value in defaults.items():
                setattr(self._settings, key, value)
            self._logger.info("All settings reset to defaults")
        else:
            # 重置单个分类
            defaults_map = {
                "display": DisplayConfig(),
                "llm": LLMConfig(),
                "model_settings": ModelSettingsConfig(),
                "terminal": TerminalConfig(),
                "preferences": PreferencesConfig(),
                "session": SessionConfig(),
                "memory": MemoryConfig(),
                "tools": ToolConfig(),
                "logging": LoggingConfig(),
                "agent": AgentConfig(),
                "session_reset": SessionResetConfig(),
                "compression": CompressionConfig(),
                "intent_mode": IntentMode.LLM,
            }
            if category in defaults_map:
                setattr(self._settings, category, defaults_map[category])
                self._logger.info(f"Category '{category}' reset to defaults")
            else:
                self._logger.warning(f"Unknown category to reset: {category}")
                return

        self._dirty = True
        self._notify_listeners()

    def is_dirty(self) -> bool:
        """检查是否有未保存的更改"""
        return self._dirty

    def reload(self) -> None:
        """重新加载设置"""
        self._load()
        self._logger.info("Settings reloaded")


def get_settings_manager() -> SettingsManager:
    """获取设置管理器单例"""
    return SettingsManager.get_instance()
