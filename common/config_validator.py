"""Pydantic 配置验证模块

将现有的 dataclass 配置迁移到 Pydantic，提供：
- 类型验证
- 字段约束
- 嵌套模型验证
- 环境变量绑定

参考 Pydantic v2 最佳实践。
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_default_handsome_home() -> Path:
    """Get the default HANDSOME_HOME directory."""
    home = os.environ.get("HOME") or os.environ.get("USERPROFILE")
    if home:
        return Path(home) / ".handsome_agent"
    return Path(".") / ".handsome_agent"


HANDSOME_HOME = Path(os.environ.get("HANDSOME_HOME", get_default_handsome_home()))

# Provider 默认 Base URL
DEFAULT_LLM_BASE_URLS = {
    "minimax": "https://api.minimaxi.com/v1",
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com/chat",
    "openrouter": "https://openrouter.ai/api/v1",
    "siliconflow": "https://api.siliconflow.cn/v1",
    "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "groq": "https://api.groq.com/openai/v1",
    "zhipu": "https://open.bigmodel.cn/api/paas/v4",
}


# =============================================================================
# Provider 配置
# =============================================================================

class LLMProviderConfig(BaseModel):
    """LLM Provider 配置

    提供 API Key、Base URL、模型等配置验证。
    """

    api_key: Optional[str] = Field(None, description="API Key")
    base_url: Optional[str] = Field(None, description="API Base URL")
    model: Optional[str] = Field(None, description="模型名称")
    enabled: bool = Field(False, description="是否启用")

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: Optional[str]) -> Optional[str]:
        """验证 base_url 格式。"""
        if v is None:
            return v
        if not v.startswith(("http://", "https://")):
            raise ValueError("base_url must start with http:// or https://")
        return v.rstrip("/")


# =============================================================================
# 模型配置
# =============================================================================

class ModelConfig(BaseModel):
    """模型配置"""

    default: str = Field("openai/gpt-4o-mini", description="默认模型")
    fallback: Optional[str] = Field(None, description="备用模型")
    max_tokens: int = Field(4096, ge=1, le=128000, description="最大 token 数")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="温度参数")
    context_window: int = Field(128000, ge=1, description="上下文窗口大小")

    @field_validator("default", "fallback")
    @classmethod
    def validate_model_format(cls, v: Optional[str]) -> Optional[str]:
        """验证模型名称格式。"""
        if v is None:
            return v
        if "/" not in v:
            raise ValueError("Model name should be in format 'provider/model-name'")
        return v


# =============================================================================
# Terminal 配置
# =============================================================================

class TerminalConfig(BaseModel):
    """Terminal 工具配置"""

    backend: str = Field("local", description="后端类型")
    timeout: int = Field(60, ge=1, le=3600, description="超时时间（秒）")
    cwd: Optional[str] = Field(None, description="工作目录")
    lifetime_seconds: int = Field(300, ge=1, le=3600, description="生命周期（秒）")
    docker_image: Optional[str] = Field(None, description="Docker 镜像")
    ssh_host: Optional[str] = Field(None, description="SSH 主机")
    ssh_user: Optional[str] = Field(None, description="SSH 用户")
    ssh_port: int = Field(22, ge=1, le=65535, description="SSH 端口")
    ssh_key: Optional[str] = Field(None, description="SSH 密钥路径")

    @model_validator(mode="after")
    def validate_ssh_config(self) -> "TerminalConfig":
        """验证 SSH 配置完整性。"""
        if self.ssh_host:
            if not self.ssh_user:
                raise ValueError("ssh_user is required when ssh_host is set")
        return self

    @field_validator("backend")
    @classmethod
    def validate_backend(cls, v: str) -> str:
        """验证后端类型。"""
        valid_backends = {"local", "docker", "ssh"}
        if v not in valid_backends:
            raise ValueError(f"backend must be one of {valid_backends}")
        return v


# =============================================================================
# Browser 配置
# =============================================================================

class BrowserConfig(BaseModel):
    """Browser 工具配置"""

    enabled: bool = Field(False, description="是否启用")
    provider: str = Field("browserbase", description="Provider 类型")
    api_key: Optional[str] = Field(None, description="API Key")
    project_id: Optional[str] = Field(None, description="项目 ID")
    proxies: bool = Field(True, description="是否使用代理")
    advanced_stealth: bool = Field(False, description="高级隐身模式")
    session_timeout: int = Field(300, ge=30, le=3600, description="会话超时（秒）")
    inactivity_timeout: int = Field(120, ge=10, le=3600, description="空闲超时（秒）")


# =============================================================================
# Skills 配置
# =============================================================================

class SkillsConfig(BaseModel):
    """技能系统配置"""

    external_dirs: List[str] = Field(default_factory=list, description="外部技能目录")
    disabled: List[str] = Field(default_factory=list, description="禁用的技能")
    platform_disabled: Dict[str, List[str]] = Field(default_factory=dict, description="平台禁用的技能")
    auto_sync: bool = Field(True, description="自动同步")
    track_usage: bool = Field(True, description="跟踪使用情况")
    stale_threshold_days: int = Field(90, ge=1, le=365, description="陈旧阈值（天）")

    @field_validator("external_dirs")
    @classmethod
    def validate_dirs(cls, v: List[str]) -> List[str]:
        """验证目录路径格式。"""
        validated = []
        for d in v:
            # 只检查路径格式，不检查存在性
            if not d.startswith("/") and not (len(d) > 1 and d[1] == ":"):
                raise ValueError(f"external_dirs must be absolute paths: {d}")
            validated.append(d)
        return validated


# =============================================================================
# Session 重置策略
# =============================================================================

class SessionResetPolicy(BaseModel):
    """Session 重置策略"""

    mode: str = Field("both", description="重置模式")
    at_hour: int = Field(4, ge=0, le=23, description="定时重置小时")
    idle_minutes: int = Field(1440, ge=1, le=10080, description="空闲超时（分钟）")
    notify: bool = Field(True, description="是否通知")

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        """验证模式。"""
        valid_modes = {"time", "idle", "both", "never"}
        if v not in valid_modes:
            raise ValueError(f"mode must be one of {valid_modes}")
        return v


# =============================================================================
# Platform 配置
# =============================================================================

class PlatformConfig(BaseModel):
    """Platform 配置"""

    enabled: bool = Field(False, description="是否启用")
    token: Optional[str] = Field(None, description="认证 Token")
    api_key: Optional[str] = Field(None, description="API Key")
    home_channel: Optional[str] = Field(None, description="主频道")
    allowed_users: Optional[List[str]] = Field(None, description="允许的用户列表")
    require_mention: bool = Field(False, description="是否需要 @ 提及")


# =============================================================================
# STT/TTS 配置
# =============================================================================

class STTConfig(BaseModel):
    """语音转文字配置"""

    enabled: bool = Field(False, description="是否启用")
    provider: str = Field("local", description="Provider 类型")
    model: str = Field("base", description="模型名称")


class TTSConfig(BaseModel):
    """文字转语音配置"""

    enabled: bool = Field(False, description="是否启用")
    provider: str = Field("openai", description="Provider 类型")
    model: str = Field("tts-1", description="模型名称")
    voice: str = Field("alloy", description="语音角色")


# =============================================================================
# Memory 配置
# =============================================================================

class MemoryConfig(BaseModel):
    """记忆配置

    包含所有记忆系统相关的配置项。
    """

    enabled: bool = Field(True, description="是否启用记忆功能")
    builtin_enabled: bool = Field(True, description="是否启用内置记忆")
    external_provider: Optional[str] = Field(None, description="外部 Provider 名称")
    max_entries: int = Field(1000, ge=1, le=10000, description="最大记忆条目数")
    memory_char_limit: int = Field(2200, ge=100, le=10000, description="Agent 记忆字符限制")
    user_char_limit: int = Field(1375, ge=100, le=10000, description="用户画像字符限制")

    # 语义检索配置
    semantic_retrieval_enabled: bool = Field(False, description="是否启用语义检索")
    semantic_max_results: int = Field(5, ge=1, le=50, description="最大结果数")
    semantic_min_score: float = Field(0.3, ge=0.0, le=1.0, description="最低相似度")

    # Curator 自动总结配置
    curator_enabled: bool = Field(True, description="启用自动总结")
    curator_message_threshold: int = Field(20, ge=1, description="消息数阈值")
    curator_idle_threshold_seconds: float = Field(300, ge=10, description="空闲超时（秒）")
    curator_auto_user_summary: bool = Field(True, description="自动总结用户偏好")
    curator_auto_memory_summary: bool = Field(True, description="自动总结环境信息")
    curator_max_entries_per_summary: int = Field(3, ge=1, le=10, description="每次总结最大条目数")
    curator_min_entry_length: int = Field(20, ge=1, description="最小条目长度")
    curator_max_entry_length: int = Field(500, ge=50, description="最大条目长度")
    curator_check_duplicates: bool = Field(True, description="检查重复条目")
    curator_use_auxiliary_model: bool = Field(True, description="使用辅助模型")

    # 检索策略配置
    retrieval_layer1_threshold: float = Field(0.3, ge=0.0, le=1.0, description="第一层阈值")
    retrieval_layer2_threshold: float = Field(0.1, ge=0.0, le=1.0, description="第二层阈值")
    retrieval_short_length: int = Field(50, ge=1, description="短记忆阈值")
    retrieval_short_limit: int = Field(2, ge=1, description="短记忆最多返回数量")
    retrieval_total_limit: int = Field(5, ge=1, description="总返回数量限制")

    # 检索权重配置
    retrieval_fts_weight: float = Field(0.3, ge=0.0, le=1.0, description="FTS5 权重")
    retrieval_jaccard_weight: float = Field(0.3, ge=0.0, le=1.0, description="Jaccard 权重")
    retrieval_hrr_weight: float = Field(0.4, ge=0.0, le=1.0, description="HRR 语义权重")

    # 关键词检索配置
    retrieval_keyword_min_overlap: int = Field(1, ge=1, description="最小关键词重叠数")

    @model_validator(mode="after")
    def validate_weights(self) -> "MemoryConfig":
        """验证检索权重总和为 1。"""
        total = self.retrieval_fts_weight + self.retrieval_jaccard_weight + self.retrieval_hrr_weight
        if abs(total - 1.0) > 0.01:
            raise ValueError(
                f"Retrieval weights must sum to 1.0, got {total}"
            )
        return self


# =============================================================================
# Context 压缩配置
# =============================================================================

class CompressionConfig(BaseModel):
    """Context 压缩配置"""

    enabled: bool = Field(True, description="是否启用压缩")
    threshold: float = Field(0.75, ge=0.1, le=0.99, description="压缩阈值")
    summary_model: str = Field("openai/gpt-4o-mini", description="摘要模型")


# =============================================================================
# Debug 配置
# =============================================================================

class DebugConfig(BaseModel):
    """Debug 配置"""

    web_tools: bool = Field(False, description="启用 Web 工具")
    vision_tools: bool = Field(False, description="启用视觉工具")
    moa_tools: bool = Field(False, description="启用 MOA 工具")
    image_tools: bool = Field(False, description="启用图片工具")


# =============================================================================
# Logging 配置
# =============================================================================

class LoggingConfig(BaseModel):
    """文件日志配置"""

    file_enabled: bool = Field(False, description="是否启用文件日志")
    max_file_size: int = Field(10 * 1024 * 1024, ge=1024, description="最大文件大小（字节）")
    backup_count: int = Field(5, ge=1, le=20, description="备份文件数量")
    rotation: str = Field("daily", description="轮转策略")

    @field_validator("rotation")
    @classmethod
    def validate_rotation(cls, v: str) -> str:
        """验证轮转策略。"""
        valid = {"daily", "hourly", "midnight", "size"}
        if v not in valid:
            raise ValueError(f"rotation must be one of {valid}")
        return v


# =============================================================================
# 应用设置
# =============================================================================

class Settings(BaseSettings):
    """应用配置

    使用 Pydantic Settings 进行环境变量绑定和配置管理。
    """

    model_config = SettingsConfigDict(
        env_prefix="HANDSOME_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    # 基本信息
    app_name: str = Field("HandsomeAgent", description="应用名称")
    app_version: str = Field("1.0.0", description="应用版本")
    debug: bool = Field(False, description="调试模式")

    # 路径配置
    handsome_home: Path = Field(default=HANDSOME_HOME, description="应用主目录")

    # 服务配置
    brain_service_host: str = Field("0.0.0.0", description="服务主机")
    brain_service_port: int = Field(8000, ge=1, le=65535, description="服务端口")
    gateway_host: str = Field("0.0.0.0", description="网关主机")
    gateway_port: int = Field(8000, ge=1, le=65535, description="网关端口")
    executor_port: int = Field(8002, ge=1, le=65535, description="执行器端口")

    # 数据库配置
    db_path: Path = Field(default=HANDSOME_HOME / "handsome_agent.db", description="数据库路径")

    # 安全配置
    api_key: Optional[str] = Field(None, description="API Key")
    allowed_origins: List[str] = Field(default_factory=lambda: ["*"], description="允许的来源")

    # 技能配置
    skills_dir: Path = Field(default=HANDSOME_HOME / "skills", description="技能目录")

    # 执行配置
    max_iterations: int = Field(10, ge=1, le=1000, description="最大迭代次数")
    timeout_seconds: float = Field(60.0, ge=1.0, le=3600.0, description="超时时间（秒）")

    # 命令过滤
    allowed_commands: List[str] = Field(
        default_factory=lambda: ["git", "npm", "pip", "python", "mkdir", "ls", "cat", "echo"],
        description="允许的命令"
    )
    blocked_patterns: List[str] = Field(
        default_factory=lambda: ["rm -rf /", "curl | sh", "mkfs", "dd if="],
        description="阻止的模式"
    )

    # 嵌套配置（使用 Dict 类型，解析后应为 Pydantic 模型）
    llm_providers: Dict[str, Any] = Field(default_factory=dict, description="LLM Providers")
    model: Dict[str, Any] = Field(
        default_factory=lambda: {
            "default": "openai/gpt-4o-mini",
            "max_tokens": 4096,
            "temperature": 0.7,
        },
        description="模型配置"
    )
    terminal: Dict[str, Any] = Field(
        default_factory=lambda: {
            "backend": "local",
            "timeout": 60,
            "lifetime_seconds": 300,
        },
        description="终端配置"
    )
    browser: Dict[str, Any] = Field(
        default_factory=lambda: {
            "enabled": False,
            "proxies": True,
        },
        description="浏览器配置"
    )
    session_reset: Dict[str, Any] = Field(
        default_factory=lambda: {
            "mode": "both",
            "at_hour": 4,
            "idle_minutes": 1440,
            "notify": True,
        },
        description="会话重置配置"
    )

    @computed_field
    @property
    def sessions_dir(self) -> Path:
        """获取会话目录。"""
        return self.handsome_home / "sessions"

    @computed_field
    @property
    def memories_dir(self) -> Path:
        """获取记忆目录。"""
        return self.handsome_home / "memories"

    @computed_field
    @property
    def logs_dir(self) -> Path:
        """获取日志目录。"""
        return self.handsome_home / "logs"

    def get_model_config(self) -> ModelConfig:
        """获取解析后的模型配置。"""
        return ModelConfig(**self.model)

    def get_terminal_config(self) -> TerminalConfig:
        """获取解析后的终端配置。"""
        return TerminalConfig(**self.terminal)

    def get_browser_config(self) -> BrowserConfig:
        """获取解析后的浏览器配置。"""
        return BrowserConfig(**self.browser)

    def get_session_reset_policy(self) -> SessionResetPolicy:
        """获取解析后的会话重置策略。"""
        return SessionResetPolicy(**self.session_reset)

    def get_memory_config(self) -> MemoryConfig:
        """获取解析后的记忆配置。

        默认使用内置 MemoryConfig，也可通过环境变量配置。
        """
        return MemoryConfig()

    @field_validator("db_path", "skills_dir", "handsome_home", mode="before")
    @classmethod
    def validate_paths(cls, v: Union[str, Path]) -> Path:
        """验证路径格式。"""
        if isinstance(v, str):
            return Path(v)
        return v


# =============================================================================
# 配置缓存
# =============================================================================

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """获取单例配置实例。"""
    return Settings()


def get_sessions_dir() -> Path:
    """获取会话目录。"""
    return get_settings().sessions_dir


def get_memories_dir() -> Path:
    """获取记忆目录。"""
    return get_settings().memories_dir


def get_logs_dir() -> Path:
    """获取日志目录。"""
    return get_settings().logs_dir


def get_config_dir() -> Path:
    """获取配置目录。"""
    return get_settings().handsome_home


def get_skills_dir() -> Path:
    """获取技能目录。"""
    return get_settings().skills_dir


def get_model_config() -> ModelConfig:
    """获取模型配置。"""
    return get_settings().get_model_config()


def get_terminal_config() -> TerminalConfig:
    """获取终端配置。"""
    return get_settings().get_terminal_config()


def get_browser_config() -> BrowserConfig:
    """获取浏览器配置。"""
    return get_settings().get_browser_config()


def get_session_reset_policy() -> SessionResetPolicy:
    """获取会话重置策略。"""
    return get_settings().get_session_reset_policy()


def get_memory_config() -> MemoryConfig:
    """获取记忆配置。"""
    return get_settings().get_memory_config()


def get_compression_config() -> CompressionConfig:
    """获取压缩配置。"""
    return CompressionConfig()


def get_debug_config() -> DebugConfig:
    """获取 Debug 配置。"""
    return DebugConfig()


def get_logging_config() -> LoggingConfig:
    """获取日志配置。"""
    return LoggingConfig()


def get_skills_config() -> SkillsConfig:
    """获取技能配置。"""
    return SkillsConfig()
