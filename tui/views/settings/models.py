#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""设置数据模型 - 与统一配置系统共享同一份 YAML 配置文件

配置文件路径: ~/.agent_z/config.yaml
"""

from __future__ import annotations

from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field

# ============================================================
# 枚举类型 (与统一配置保持一致)
# ============================================================


class Language(str, Enum):
    ZH = "zh"
    EN = "en"


class ExplanationDepth(str, Enum):
    BRIEF = "brief"
    MODERATE = "moderate"
    DETAILED = "detailed"


class ResponseFormat(str, Enum):
    MARKDOWN = "markdown"
    PLAIN = "plain"


class IntentMode(str, Enum):
    LLM = "llm"
    HYBRID = "hybrid"
    KEYWORD = "keyword"


class SessionResetMode(str, Enum):
    BOTH = "both"
    DAILY = "daily"
    IDLE = "idle"
    NEVER = "never"


class TerminalBackend(str, Enum):
    LOCAL = "local"
    DOCKER = "docker"
    SSH = "ssh"


class VerifyOnStop(str, Enum):
    AUTO = "auto"
    TRUE = "true"
    FALSE = "false"


class CodingContext(str, Enum):
    AUTO = "auto"
    FOCUS = "focus"
    ON = "on"
    OFF = "off"


class ImageInputMode(str, Enum):
    AUTO = "auto"
    NATIVE = "native"
    TEXT = "text"


# ============================================================
# CLI 配置默认值 (与 common/config.py DEFAULT_CONFIG 对齐)
# ============================================================

DEFAULT_CONFIG: dict[str, Any] = {
    "llm": {
        "provider": "",
        "model": "",
    },
    "model_settings": {
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
        "explanation_depth": "moderate",
        "response_format": "markdown",
        "log_level": "info",
    },
    "session": {
        "enabled": True,
        "storage": "memory",
    },
    "memory": {
        "enabled": True,
        "builtin_enabled": True,
        "external_provider": None,
        "semantic_retrieval_enabled": False,
    },
    "terminal": {
        "backend": "local",
        "modal_mode": "auto",
        "cwd": ".",
        "timeout": 180,
        "lifetime_seconds": 300,
        "docker_image": "nikolaik/python-nodejs:python3.11-nodejs20",
        "docker_mount_cwd_to_workspace": False,
        "docker_run_as_host_user": False,
        "docker_volumes": [],
        "docker_network": True,
        "docker_extra_args": [],
        "docker_env": {},
        "docker_forward_env": [],
        "singularity_image": "docker://nikolaik/python-nodejs:python3.11-nodejs20",
        "modal_image": "nikolaik/python-nodejs:python3.11-nodejs20",
        "daytona_image": "nikolaik/python-nodejs:python3.11-nodejs20",
        "ssh_host": None,
        "ssh_user": None,
        "ssh_port": 22,
        "ssh_key": None,
        "daemon_term_grace_seconds": 2.0,
        "persistent_shell": True,
        "home_mode": "auto",
        "shell_init_files": [],
        "auto_source_bashrc": True,
        "container_cpu": 1,
        "container_memory": 5120,
        "container_disk": 51200,
        "container_persistent": True,
    },
    "agent": {
        "max_turns": 90,
        "gateway_timeout": 1800,
        "restart_drain_timeout": 0,
        "api_max_retries": 3,
        "verify_on_stop": "auto",
        "coding_context": "auto",
        "coding_instructions": "",
        "tool_use_enforcement": "auto",
        "intent_ack_continuation": "auto",
        "parallel_tool_call_guidance": True,
        "task_completion_guidance": True,
        "environment_probe": True,
        "environment_hint": "",
        "clarify_timeout": 3600,
        "gateway_notify_interval": 180,
        "gateway_timeout_warning": 900,
        "max_verify_nudges": 3,
        "verify_guidance": True,
        "image_input_mode": "auto",
        "disabled_toolsets": [],
        "judge_timeout": 30.0,
        "judge_max_tokens": 4096,
        "gateway_auto_continue_freshness": 3600,
    },
    "providers": {},
    "fallback_providers": [],
    "tool_loop_guardrails": {
        "warnings_enabled": True,
        "hard_stop_enabled": False,
        "warn_after": {
            "exact_failure": 2,
            "same_tool_failure": 3,
            "idempotent_no_progress": 2,
        },
        "hard_stop_after": {
            "exact_failure": 5,
            "same_tool_failure": 8,
            "idempotent_no_progress": 5,
        },
    },
    "compression": {
        "enabled": True,
        "threshold": 0.50,
        "target_ratio": 0.20,
        "protect_last_n": 20,
        "hygiene_hard_message_limit": 5000,
        "protect_first_n": 3,
        "abort_on_summary_failure": False,
    },
    "session_reset": {
        "mode": "both",
        "at_hour": 4,
        "idle_minutes": 1440,
        "notify": True,
    },
    "stt": {"enabled": False, "provider": "local"},
    "tts": {"enabled": False, "provider": "openai"},
    "logging": {"file_enabled": False},
    "browser": {"enabled": False, "provider": "browserbase"},
}


# ============================================================
# TUI 专用默认值 (不存储在 config.yaml 中)
# ============================================================

TUI_DEFAULTS: dict[str, Any] = {
    "intent_mode": "llm",
}


# ============================================================
# 配置子模型
# ============================================================


class LLMConfig(BaseModel):
    """LLM 配置 (对应 config.llm)"""

    provider: str = ""
    model: str = ""


class ModelSettingsConfig(BaseModel):
    """模型参数配置 (对应 config.model_settings)"""

    name: str = ""
    context_window: int = Field(default=128000, ge=1000, le=1000000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1, le=32000)
    compression_model: str = ""
    title_model: str = ""
    synthesis_model: str = ""
    memory_model: str = ""
    auxiliary_model: str = ""


class DisplayConfig(BaseModel):
    """显示配置 (对应 config.display)"""

    verbose: bool = False
    show_reasoning: bool = False
    language: Language = Language.ZH


class PreferencesConfig(BaseModel):
    """偏好配置 (对应 config.preferences)"""

    explanation_depth: ExplanationDepth = ExplanationDepth.MODERATE
    response_format: ResponseFormat = ResponseFormat.MARKDOWN
    log_level: str = "info"


class SessionConfig(BaseModel):
    """会话配置 (对应 config.session)"""

    enabled: bool = True
    storage: str = "memory"


class MemoryConfig(BaseModel):
    """记忆配置 (对应 config.memory)"""

    enabled: bool = True
    builtin_enabled: bool = True
    external_provider: Optional[str] = None
    semantic_retrieval_enabled: bool = False


class TerminalConfig(BaseModel):
    """终端配置 (对应 config.terminal)"""

    backend: TerminalBackend = TerminalBackend.LOCAL
    modal_mode: str = "auto"
    cwd: str = "."
    timeout: int = Field(default=180, ge=1, le=3600)
    lifetime_seconds: int = Field(default=300, ge=1, le=3600)
    docker_image: Optional[str] = None
    docker_mount_cwd_to_workspace: bool = False
    docker_run_as_host_user: bool = False
    docker_volumes: list[str] = Field(default_factory=list)
    docker_network: bool = True
    docker_extra_args: list[str] = Field(default_factory=list)
    docker_env: dict[str, str] = Field(default_factory=dict)
    docker_forward_env: list[str] = Field(default_factory=list)
    singularity_image: Optional[str] = None
    modal_image: Optional[str] = None
    daytona_image: Optional[str] = None
    ssh_host: Optional[str] = None
    ssh_user: Optional[str] = None
    ssh_port: int = Field(default=22, ge=1, le=65535)
    ssh_key: Optional[str] = None
    daemon_term_grace_seconds: float = Field(default=2.0, ge=0.0)
    persistent_shell: bool = True
    home_mode: str = "auto"
    shell_init_files: list[str] = Field(default_factory=list)
    auto_source_bashrc: bool = True
    container_cpu: int = Field(default=1, ge=1, le=64)
    container_memory: int = Field(default=5120, ge=256, le=131072)
    container_disk: int = Field(default=51200, ge=1024, le=1048576)
    container_persistent: bool = True


class AgentConfig(BaseModel):
    """Agent 行为配置 (对应 config.agent)"""

    max_turns: int = Field(default=90, ge=1, le=500)
    gateway_timeout: int = Field(default=1800, ge=0, le=86400)
    restart_drain_timeout: int = Field(default=0, ge=0, le=3600)
    api_max_retries: int = Field(default=3, ge=0, le=10)
    verify_on_stop: VerifyOnStop = VerifyOnStop.AUTO
    coding_context: CodingContext = CodingContext.AUTO
    coding_instructions: str = ""
    tool_use_enforcement: str = "auto"
    intent_ack_continuation: str = "auto"
    parallel_tool_call_guidance: bool = True
    task_completion_guidance: bool = True
    environment_probe: bool = True
    environment_hint: str = ""
    clarify_timeout: int = Field(default=3600, ge=0, le=86400)
    gateway_notify_interval: int = Field(default=180, ge=0, le=3600)
    gateway_timeout_warning: int = Field(default=900, ge=0, le=3600)
    max_verify_nudges: int = Field(default=3, ge=0, le=10)
    verify_guidance: bool = True
    image_input_mode: ImageInputMode = ImageInputMode.AUTO
    disabled_toolsets: list[str] = Field(default_factory=list)
    judge_timeout: float = Field(default=30.0, ge=1.0, le=300.0)
    judge_max_tokens: int = Field(default=4096, ge=1, le=32000)
    gateway_auto_continue_freshness: int = Field(default=3600, ge=0, le=86400)


class ToolLoopWarningThresholds(BaseModel):
    """工具循环警告阈值"""

    exact_failure: int = Field(default=2, ge=1)
    same_tool_failure: int = Field(default=3, ge=1)
    idempotent_no_progress: int = Field(default=2, ge=1)


class ToolLoopHardStopThresholds(BaseModel):
    """工具循环硬停止阈值"""

    exact_failure: int = Field(default=5, ge=1)
    same_tool_failure: int = Field(default=8, ge=1)
    idempotent_no_progress: int = Field(default=5, ge=1)


class ToolLoopGuardrailConfig(BaseModel):
    """工具循环防护配置"""

    warnings_enabled: bool = True
    hard_stop_enabled: bool = False
    warn_after: ToolLoopWarningThresholds = Field(
        default_factory=ToolLoopWarningThresholds
    )
    hard_stop_after: ToolLoopHardStopThresholds = Field(
        default_factory=ToolLoopHardStopThresholds
    )


class ProviderItemConfig(BaseModel):
    """单个 Provider 配置"""

    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    enabled: bool = False


class FallbackProviderItem(BaseModel):
    """单个 Fallback Provider 条目"""

    provider: str = ""
    model: Optional[str] = None
    base_url: Optional[str] = None


class ProvidersConfig(BaseModel):
    """Providers 配置 (对应 config.providers)"""

    items: dict[str, ProviderItemConfig] = Field(default_factory=dict)


class FallbackProvidersConfig(BaseModel):
    """Fallback Providers 配置 (对应 config.fallback_providers)"""

    items: list[FallbackProviderItem] = Field(default_factory=list)


class CompressionConfig(BaseModel):
    """压缩配置 (对应 config.compression)"""

    enabled: bool = True
    threshold: float = Field(default=0.50, ge=0.1, le=0.99)
    target_ratio: float = Field(default=0.20, ge=0.05, le=0.95)
    protect_last_n: int = Field(default=20, ge=0)
    hygiene_hard_message_limit: int = Field(default=5000, ge=0)
    protect_first_n: int = Field(default=3, ge=0)
    abort_on_summary_failure: bool = False


class SessionResetConfig(BaseModel):
    """会话重置配置 (对应 config.session_reset)"""

    mode: SessionResetMode = SessionResetMode.BOTH
    at_hour: int = Field(default=4, ge=0, le=23)
    idle_minutes: int = Field(default=1440, ge=1, le=10080)
    notify: bool = True


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


class CamofoxConfig(BaseModel):
    """Camofox 反检测 Firefox 配置"""

    managed_persistence: bool = False
    user_id: str = ""
    session_key: str = ""
    adopt_existing_tab: bool = False
    rewrite_loopback_urls: bool = False
    loopback_host_alias: str = "host.docker.internal"


class BrowserConfig(BaseModel):
    """浏览器配置 (对应 config.browser)"""

    enabled: bool = False
    provider: str = "browserbase"
    api_key: Optional[str] = None
    project_id: Optional[str] = None
    proxies: bool = True
    advanced_stealth: bool = False
    session_timeout: int = Field(default=300, ge=30)
    inactivity_timeout: int = Field(default=120, ge=10)
    command_timeout: int = Field(default=30, ge=5)
    record_sessions: bool = False
    allow_private_urls: bool = False
    engine: str = "auto"
    auto_local_for_private_urls: bool = True
    cdp_url: str = ""
    allow_unsafe_evaluate: bool = False
    dialog_policy: str = "must_respond"
    dialog_timeout_s: int = Field(default=300, ge=0)
    camofox: CamofoxConfig = Field(default_factory=CamofoxConfig)


class WebConfig(BaseModel):
    """Web 配置 (对应 config.web)"""

    backend: str = ""
    search_backend: str = ""
    extract_backend: str = ""
    extract_char_limit: int = Field(default=15000, ge=100)


class CheckpointsConfig(BaseModel):
    """文件系统快照配置 (对应 config.checkpoints)"""

    enabled: bool = False
    max_snapshots: int = Field(default=20, ge=1)
    max_total_size_mb: int = Field(default=500, ge=0)
    max_file_size_mb: int = Field(default=10, ge=0)
    auto_prune: bool = True
    retention_days: int = Field(default=7, ge=1)
    delete_orphans: bool = True
    min_interval_hours: int = Field(default=24, ge=1)


class ToolOutputConfig(BaseModel):
    """工具输出截断配置 (对应 config.tool_output)"""

    max_bytes: int = Field(default=50000, ge=1000)
    max_lines: int = Field(default=2000, ge=10)
    max_line_length: int = Field(default=2000, ge=10)


class AboutInfo(BaseModel):
    """关于信息 (只读)"""

    version: str = "1.0.0"
    license: str = "MIT"


# ============================================================
# 完整设置文档
# ============================================================


class SettingsDocument(BaseModel):
    """完整设置文档 - 包含 YAML 配置和 TUI 专用配置"""

    # YAML 配置段
    llm: LLMConfig = LLMConfig()
    model_settings: ModelSettingsConfig = ModelSettingsConfig()
    display: DisplayConfig = DisplayConfig()
    preferences: PreferencesConfig = PreferencesConfig()
    session: SessionConfig = SessionConfig()
    memory: MemoryConfig = MemoryConfig()
    terminal: TerminalConfig = TerminalConfig()
    agent: AgentConfig = AgentConfig()
    providers: ProvidersConfig = ProvidersConfig()
    fallback_providers: FallbackProvidersConfig = FallbackProvidersConfig()
    tool_loop_guardrails: ToolLoopGuardrailConfig = ToolLoopGuardrailConfig()
    compression: CompressionConfig = CompressionConfig()
    session_reset: SessionResetConfig = SessionResetConfig()

    # TUI 专用配置
    tools: ToolConfig = ToolConfig()
    logging: LoggingConfig = LoggingConfig()
    intent_mode: IntentMode = IntentMode.LLM

    # YAML 扩展配置
    browser: BrowserConfig = BrowserConfig()
    web: WebConfig = WebConfig()
    checkpoints: CheckpointsConfig = CheckpointsConfig()
    tool_output: ToolOutputConfig = ToolOutputConfig()

    # 关于信息
    about: AboutInfo = AboutInfo()

    @classmethod
    def from_dict(cls, cfg: dict) -> "SettingsDocument":
        """从统一配置字典创建 SettingsDocument。

        Args:
            cfg: load_config() 返回的完整配置字典
        """
        # Providers: dict -> dict of ProviderItemConfig
        providers_raw = cfg.get("providers", {})
        providers_items = (
            {
                k: (
                    ProviderItemConfig(**v)
                    if isinstance(v, dict)
                    else ProviderItemConfig()
                )
                for k, v in providers_raw.items()
            }
            if providers_raw
            else {}
        )

        # Fallback providers: list -> list of FallbackProviderItem
        fallback_raw = cfg.get("fallback_providers", [])
        fallback_items = (
            [
                (
                    FallbackProviderItem(**item)
                    if isinstance(item, dict)
                    else FallbackProviderItem()
                )
                for item in fallback_raw
            ]
            if fallback_raw
            else []
        )

        # Tool loop guardrails
        tlr_raw = cfg.get("tool_loop_guardrails", {})
        tlr_warn = tlr_raw.get("warn_after", {}) if isinstance(tlr_raw, dict) else {}
        tlr_hard = (
            tlr_raw.get("hard_stop_after", {}) if isinstance(tlr_raw, dict) else {}
        )

        return cls(
            llm=LLMConfig(**cfg.get("llm", {})),
            model_settings=ModelSettingsConfig(**cfg.get("model_settings", {})),
            display=DisplayConfig(**cfg.get("display", {})),
            preferences=PreferencesConfig(**cfg.get("preferences", {})),
            session=SessionConfig(**cfg.get("session", {})),
            memory=MemoryConfig(**cfg.get("memory", {})),
            terminal=TerminalConfig(**cfg.get("terminal", {})),
            agent=AgentConfig(**cfg.get("agent", {})),
            providers=ProvidersConfig(items=providers_items),
            fallback_providers=FallbackProvidersConfig(items=fallback_items),
            tool_loop_guardrails=ToolLoopGuardrailConfig(
                warnings_enabled=(
                    tlr_raw.get("warnings_enabled", True)
                    if isinstance(tlr_raw, dict)
                    else True
                ),
                hard_stop_enabled=(
                    tlr_raw.get("hard_stop_enabled", False)
                    if isinstance(tlr_raw, dict)
                    else False
                ),
                warn_after=ToolLoopWarningThresholds(**tlr_warn),
                hard_stop_after=ToolLoopHardStopThresholds(**tlr_hard),
            ),
            compression=CompressionConfig(**cfg.get("compression", {})),
            session_reset=SessionResetConfig(**cfg.get("session_reset", {})),
            tools=ToolConfig(
                **cfg.get("tools", TUI_DEFAULTS.get("tools", {})),
                **(
                    {
                        "stt_enabled": False,
                        "tts_enabled": False,
                        "browser_enabled": False,
                        "web_debug": False,
                        "vision_debug": False,
                    }
                    if "tools" not in cfg
                    else {}
                ),
            ),
            logging=LoggingConfig(
                **cfg.get("logging", TUI_DEFAULTS.get("logging", {})),
                **{"file_enabled": False} if "logging" not in cfg else {},
            ),
            intent_mode=IntentMode(
                cfg.get("intent_mode", TUI_DEFAULTS.get("intent_mode", "llm"))
            ),
            browser=BrowserConfig(**cfg.get("browser", {})),
            web=WebConfig(**cfg.get("web", {})),
            checkpoints=CheckpointsConfig(**cfg.get("checkpoints", {})),
            tool_output=ToolOutputConfig(**cfg.get("tool_output", {})),
        )

    def to_dict(self) -> dict:
        """转换为统一配置字典。

        Returns:
            可用于 save_config() 的完整字典
        """
        import enum

        def _enum_safe(obj):
            """将 Enum 值转为字符串，避免 PyYAML 序列化产生 !!python/object 标签"""
            if isinstance(obj, enum.Enum):
                return obj.value
            if isinstance(obj, dict):
                return {k: _enum_safe(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_enum_safe(i) for i in obj]
            return obj

        config = _enum_safe(self.model_dump())

        # 移除 about（只读信息不保存）
        config.pop("about", None)

        # 展开 ProvidersConfig: {"items": {...}} -> {...}
        if "providers" in config and isinstance(config["providers"], dict):
            inner = config["providers"].get("items", {})
            config["providers"] = (
                {
                    k: (v.model_dump() if hasattr(v, "model_dump") else v)
                    for k, v in inner.items()
                }
                if inner
                else {}
            )

        # 展开 FallbackProvidersConfig: {"items": [...]} -> [...]
        if "fallback_providers" in config and isinstance(
            config["fallback_providers"], dict
        ):
            fb_inner = config["fallback_providers"].get("items", [])
            config["fallback_providers"] = (
                [
                    item.model_dump() if hasattr(item, "model_dump") else item
                    for item in fb_inner
                ]
                if fb_inner
                else []
            )

        # 展开 tool_loop_guardrails nested models
        if "tool_loop_guardrails" in config and isinstance(
            config["tool_loop_guardrails"], dict
        ):
            tlr = config["tool_loop_guardrails"]
            if hasattr(tlr, "model_dump"):
                config["tool_loop_guardrails"] = tlr.model_dump()

        return config


# ============================================================
# 分类元数据
# ============================================================


class CategoryMeta:
    """分类元数据"""

    CATEGORIES = [
        ("language", "🌐", "language", "display"),
        ("llm", "🤖", "llm", "llm"),
        ("model", "🔧", "model", "model_settings"),
        ("providers", "🔗", "llm", "providers"),
        ("fallback", "🔄", "fallback", "fallback_providers"),
        ("terminal", "💻", "terminal", "terminal"),
        ("agent", "⚙️", "agent", "agent"),
        ("tool_loop", "🔁", "agent", "tool_loop_guardrails"),
        ("session", "🔄", "session", "session"),
        ("memory", "💾", "session", "memory"),
        ("compression", "📦", "session", "compression"),
        ("session_reset", "🕐", "session", "session_reset"),
        ("intent", "🧠", "agent", "intent_mode"),
        ("preferences", "📝", "preferences", "preferences"),
        ("tools", "🛠️", "tools", "tools"),
        ("logging", "📄", "logging", "logging"),
        ("about", "ℹ️", "about", "about"),
    ]

    @classmethod
    def get_category(cls, category_id: str) -> tuple:
        for cat in cls.CATEGORIES:
            if cat[0] == category_id:
                return cat
        return None

    @classmethod
    def get_all_categories(cls) -> list:
        return cls.CATEGORIES

    @classmethod
    def get_first_category(cls) -> str:
        return cls.CATEGORIES[0][0]

    @classmethod
    def get_next_category(cls, current: str) -> str:
        ids = [c[0] for c in cls.CATEGORIES]
        idx = ids.index(current) if current in ids else -1
        return ids[(idx + 1) % len(ids)]

    @classmethod
    def get_prev_category(cls, current: str) -> str:
        ids = [c[0] for c in cls.CATEGORIES]
        idx = ids.index(current) if current in ids else 0
        return ids[(idx - 1) % len(ids)]
