#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""设置数据模型 - 与 CLI 配置共享同一份配置文件

配置文件路径: ~/.handsome_agent/config.json
"""

from __future__ import annotations

from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field

# ============================================================
# 枚举类型 (与 CLI 保持一致)
# ============================================================

class Language(str, Enum):
    """显示语言"""
    ZH = "zh"
    EN = "en"

class ExplanationDepth(str, Enum):
    """响应详细程度"""
    BRIEF = "brief"
    MODERATE = "moderate"
    DETAILED = "detailed"

class ResponseFormat(str, Enum):
    """响应格式"""
    MARKDOWN = "markdown"
    PLAIN = "plain"

class IntentMode(str, Enum):
    """意图识别模式"""
    LLM = "llm"
    HYBRID = "hybrid"
    KEYWORD = "keyword"

class SessionResetMode(str, Enum):
    """会话重置模式"""
    BOTH = "both"
    DAILY = "daily"
    IDLE = "idle"
    NONE = "none"

class TerminalBackend(str, Enum):
    """终端执行后端"""
    LOCAL = "local"
    DOCKER = "docker"

# ============================================================
# CLI 配置默认值 (与 cli/config/config.py 保持一致)
# ============================================================

DEFAULT_CONFIG = {
    "llm": {
        "provider": "",
        "model": "",
        "api_key": "",
        "base_url": "",
    },
    "model": {
        "name": "",
        "context_window": 128000,
        "temperature": 0.7,
        "max_tokens": 4096,
    },
    "display": {
        "verbose": False,
        "show_reasoning": False,
        "language": "zh",
    },
    "preferences": {
        "explanation_depth": "detailed",
        "response_format": "markdown",
        "log_level": "info",
    },
    "session": {
        "enabled": True,
        "storage": "memory",
    },
    "memory": {
        "enabled": False,
        "type": "none",
    },
    "terminal": {
        "backend": "local",
    },
}

# ============================================================
# TUI 专用默认值 (不存储在 config.json 中)
# ============================================================

TUI_DEFAULTS = {
    "tools": {
        "stt_enabled": False,
        "tts_enabled": False,
        "browser_enabled": False,
        "web_debug": False,
        "vision_debug": False,
    },
    "logging": {
        "file_enabled": False,
    },
    "agent": {
        "max_iterations": 10,
        "timeout_seconds": 60.0,
    },
    "session_reset": {
        "mode": "both",
    },
    "compression": {
        "enabled": True,
    },
    "intent_mode": "llm",
}

# ============================================================
# 设置分类模型 (与 CLI 配置结构对应)
# ============================================================

class LLMConfig(BaseModel):
    """LLM 配置 (对应 config.llm)"""
    provider: str = ""
    model: str = ""
    api_key: str = ""
    base_url: str = ""

class ModelConfig(BaseModel):
    """模型配置 (对应 config.model)"""
    name: str = ""
    context_window: int = Field(default=128000, ge=1000, le=1000000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1, le=32000)

class DisplayConfig(BaseModel):
    """显示配置 (对应 config.display)"""
    verbose: bool = False
    show_reasoning: bool = False
    language: Language = Language.ZH

class PreferencesConfig(BaseModel):
    """偏好配置 (对应 config.preferences)"""
    explanation_depth: ExplanationDepth = ExplanationDepth.DETAILED
    response_format: ResponseFormat = ResponseFormat.MARKDOWN
    log_level: str = "info"

class SessionConfig(BaseModel):
    """会话配置 (对应 config.session)"""
    enabled: bool = True
    storage: str = "memory"

class MemoryConfig(BaseModel):
    """记忆配置 (对应 config.memory)"""
    enabled: bool = False
    type: str = "none"

class TerminalConfig(BaseModel):
    """终端配置 (对应 config.terminal)"""
    backend: TerminalBackend = TerminalBackend.LOCAL

class ToolConfig(BaseModel):
    """工具配置 (TUI 专用)"""
    stt_enabled: bool = False
    tts_enabled: bool = False
    browser_enabled: bool = False
    web_debug: bool = False
    vision_debug: bool = False

class LoggingConfig(BaseModel):
    """日志配置 (TUI 专用)"""
    file_enabled: bool = False

class AgentConfig(BaseModel):
    """Agent 配置 (TUI 专用)"""
    max_iterations: int = Field(default=10, ge=1, le=100)
    timeout_seconds: float = Field(default=60.0, ge=1.0, le=600.0)

class SessionResetConfig(BaseModel):
    """会话重置配置 (TUI 专用)"""
    mode: SessionResetMode = SessionResetMode.BOTH

class CompressionConfig(BaseModel):
    """压缩配置 (TUI 专用)"""
    enabled: bool = True

class AboutInfo(BaseModel):
    """关于信息 (只读)"""
    version: str = "1.0.0"
    license: str = "MIT"

# ============================================================
# 完整设置文档
# ============================================================

class SettingsDocument(BaseModel):
    """完整设置文档 - 包含 CLI 配置和 TUI 专用配置"""
    # CLI 共享配置
    llm: LLMConfig = LLMConfig()
    model: ModelConfig = ModelConfig()
    display: DisplayConfig = DisplayConfig()
    preferences: PreferencesConfig = PreferencesConfig()
    session: SessionConfig = SessionConfig()
    memory: MemoryConfig = MemoryConfig()
    terminal: TerminalConfig = TerminalConfig()

    # TUI 专用配置
    tools: ToolConfig = ToolConfig()
    logging: LoggingConfig = LoggingConfig()
    agent: AgentConfig = AgentConfig()
    session_reset: SessionResetConfig = SessionResetConfig()
    compression: CompressionConfig = CompressionConfig()
    intent_mode: IntentMode = IntentMode.LLM

    # 关于信息
    about: AboutInfo = AboutInfo()

    @classmethod
    def from_cli_config(cls, cli_config: dict) -> "SettingsDocument":
        """从 CLI 配置创建 SettingsDocument

        Args:
            cli_config: CLI load_config() 返回的配置字典
        """
        return cls(
            llm=LLMConfig(**cli_config.get("llm", {})),
            model=ModelConfig(**cli_config.get("model", {})),
            display=DisplayConfig(**cli_config.get("display", {})),
            preferences=PreferencesConfig(**cli_config.get("preferences", {})),
            session=SessionConfig(**cli_config.get("session", {})),
            memory=MemoryConfig(**cli_config.get("memory", {})),
            terminal=TerminalConfig(**cli_config.get("terminal", {})),
            tools=ToolConfig(**cli_config.get("tools", TUI_DEFAULTS["tools"])),
            logging=LoggingConfig(**cli_config.get("logging", TUI_DEFAULTS["logging"])),
            agent=AgentConfig(**cli_config.get("agent", TUI_DEFAULTS["agent"])),
            session_reset=SessionResetConfig(**cli_config.get("session_reset", TUI_DEFAULTS["session_reset"])),
            compression=CompressionConfig(**cli_config.get("compression", TUI_DEFAULTS["compression"])),
            intent_mode=IntentMode(cli_config.get("intent_mode", TUI_DEFAULTS["intent_mode"])),
        )

    def to_cli_config(self) -> dict:
        """转换为 CLI 配置格式

        Returns:
            可用于 CLI save_config() 的完整字典
        """
        config = self.model_dump()

        # 移除 about（只读信息不保存）
        config.pop("about", None)

        return config

# ============================================================
# 分类元数据
# ============================================================

class CategoryMeta:
    """分类元数据"""

    CATEGORIES = [
        ("language", "🌐", "语言", "display"),
        ("llm", "🤖", "大模型", "llm"),
        ("model", "🔧", "模型参数", "model"),
        ("terminal", "💻", "终端", "terminal"),
        ("agent", "⚙️", "Agent", "agent"),
        ("session", "🔄", "会话", "session"),
        ("intent", "🧠", "意图识别", "intent_mode"),
        ("preferences", "📝", "响应偏好", "preferences"),
        ("tools", "🛠️", "工具", "tools"),
        ("logging", "📄", "日志", "logging"),
        ("about", "ℹ️", "关于", "about"),
    ]

    @classmethod
    def get_category(cls, category_id: str) -> tuple:
        """获取分类元数据"""
        for cat in cls.CATEGORIES:
            if cat[0] == category_id:
                return cat
        return None

    @classmethod
    def get_all_categories(cls) -> list:
        """获取所有分类"""
        return cls.CATEGORIES

    @classmethod
    def get_first_category(cls) -> str:
        """获取第一个分类 ID"""
        return cls.CATEGORIES[0][0]

    @classmethod
    def get_next_category(cls, current: str) -> str:
        """获取下一个分类 ID"""
        ids = [c[0] for c in cls.CATEGORIES]
        idx = ids.index(current) if current in ids else -1
        return ids[(idx + 1) % len(ids)]

    @classmethod
    def get_prev_category(cls, current: str) -> str:
        """获取上一个分类 ID"""
        ids = [c[0] for c in cls.CATEGORIES]
        idx = ids.index(current) if current in ids else 0
        return ids[(idx - 1) % len(ids)]
