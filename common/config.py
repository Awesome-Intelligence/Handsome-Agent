"""配置管理

参考 Hermes 和 OpenClaw 的配置设计，支持：
- 多种 LLM Provider
- Terminal/Browser 工具配置
- Session 管理
- Platform 集成
- STT/TTS 配置
- Memory 配置
- Context Compression
"""
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, List, Dict, Any
from pathlib import Path
from dataclasses import dataclass, field
import os


def get_default_handsome_home() -> Path:
    """Get the default HANDSOME_HOME directory."""
    home = os.environ.get('HOME') or os.environ.get('USERPROFILE')
    if home:
        return Path(home) / ".handsome_agent"
    return Path(".") / ".handsome_agent"


HANDSOME_HOME = Path(os.environ.get("HANDSOME_HOME", get_default_handsome_home()))


# =============================================================================
# Provider 默认 Base URL
# =============================================================================

# Provider 默认 Base URL（可通过环境变量覆盖）
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


@dataclass
class LLMProviderConfig:
    """LLM Provider 配置"""
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    enabled: bool = False


@dataclass
class ModelConfig:
    """模型配置"""
    default: str = "openai/gpt-4o-mini"
    fallback: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    context_window: int = 128000


@dataclass
class TerminalConfig:
    """Terminal 工具配置"""
    backend: str = "local"
    timeout: int = 60
    cwd: Optional[str] = None
    lifetime_seconds: int = 300
    docker_image: Optional[str] = None
    ssh_host: Optional[str] = None
    ssh_user: Optional[str] = None
    ssh_port: int = 22
    ssh_key: Optional[str] = None


@dataclass
class BrowserConfig:
    """Browser 工具配置"""
    enabled: bool = False
    provider: str = "browserbase"
    api_key: Optional[str] = None
    project_id: Optional[str] = None
    proxies: bool = True
    advanced_stealth: bool = False
    session_timeout: int = 300
    inactivity_timeout: int = 120


@dataclass
class SessionResetPolicy:
    """Session 重置策略"""
    mode: str = "both"
    at_hour: int = 4
    idle_minutes: int = 1440
    notify: bool = True


@dataclass
class PlatformConfig:
    """Platform 配置"""
    enabled: bool = False
    token: Optional[str] = None
    api_key: Optional[str] = None
    home_channel: Optional[str] = None
    allowed_users: Optional[List[str]] = None
    require_mention: bool = False


@dataclass
class STTConfig:
    """语音转文字配置"""
    enabled: bool = False
    provider: str = "local"
    model: str = "base"


@dataclass
class TTSConfig:
    """文字转语音配置"""
    enabled: bool = False
    provider: str = "openai"
    model: str = "tts-1"
    voice: str = "alloy"


@dataclass
class MemoryConfig:
    """记忆配置"""
    enabled: bool = True
    vector_store: str = "sqlite"
    embedding_model: str = "text-embedding-3-small"
    max_entries: int = 1000
    summary_threshold: int = 10


@dataclass
class CompressionConfig:
    """Context 压缩配置"""
    enabled: bool = True
    threshold: float = 0.85
    summary_model: str = "openai/gpt-4o-mini"


@dataclass
class DebugConfig:
    """Debug 配置"""
    web_tools: bool = False
    vision_tools: bool = False
    moa_tools: bool = False
    image_tools: bool = False


class Settings(BaseSettings):
    """应用配置"""
    
    app_name: str = "HandsomeAgent"
    app_version: str = "1.0.0"
    debug: bool = False
    
    handsome_home: str = str(HANDSOME_HOME)
    
    brain_service_host: str = "0.0.0.0"
    brain_service_port: int = 8001
    gateway_host: str = "0.0.0.0"
    gateway_port: int = 8000
    executor_port: int = 8002
    
    db_path: str = str(HANDSOME_HOME / "handsome_agent.db")
    
    api_key: Optional[str] = None
    allowed_origins: List[str] = Field(default_factory=lambda: ["*"])
    
    skills_dir: str = str(HANDSOME_HOME / "skills")
    
    max_iterations: int = 10
    timeout_seconds: float = 60.0
    
    allowed_commands: List[str] = Field(
        default_factory=lambda: ["git", "npm", "pip", "python", "mkdir", "ls", "cat", "echo"]
    )
    blocked_patterns: List[str] = Field(
        default_factory=lambda: ["rm -rf /", "curl | sh", "mkfs", "dd if="]
    )
    
    llm_providers: Dict[str, Any] = Field(default_factory=dict)
    model: Dict[str, Any] = Field(default_factory=lambda: {
        "default": "openai/gpt-4o-mini",
        "max_tokens": 4096,
        "temperature": 0.7,
    })
    
    terminal: Dict[str, Any] = Field(default_factory=lambda: {
        "backend": "local",
        "timeout": 60,
        "lifetime_seconds": 300,
    })
    
    browser: Dict[str, Any] = Field(default_factory=lambda: {
        "enabled": False,
        "proxies": True,
    })
    
    session_reset: Dict[str, Any] = Field(default_factory=lambda: {
        "mode": "both",
        "at_hour": 4,
        "idle_minutes": 1440,
    })
    
    platforms: Dict[str, Any] = Field(default_factory=dict)
    
    stt: Dict[str, Any] = Field(default_factory=lambda: {
        "enabled": False,
        "provider": "local",
    })
    
    tts: Dict[str, Any] = Field(default_factory=lambda: {
        "enabled": False,
        "provider": "openai",
    })
    
    memory: Dict[str, Any] = Field(default_factory=lambda: {
        "enabled": True,
        "vector_store": "sqlite",
    })
    
    compression: Dict[str, Any] = Field(default_factory=lambda: {
        "enabled": True,
        "threshold": 0.85,
    })
    
    debug_tools: Dict[str, Any] = Field(default_factory=lambda: {
        "web_tools": False,
        "vision_tools": False,
    })
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "."


@lru_cache()
def get_settings() -> Settings:
    """获取配置（单例）"""
    return Settings()


def get_sessions_dir() -> Path:
    """获取会话保存目录"""
    return Path(get_settings().handsome_home) / "sessions"


def get_memories_dir() -> Path:
    """获取记忆保存目录"""
    return Path(get_settings().handsome_home) / "memories"


def get_logs_dir() -> Path:
    """获取日志保存目录"""
    return Path(get_settings().handsome_home) / "logs"


def get_config_dir() -> Path:
    """获取配置保存目录"""
    return Path(get_settings().handsome_home) / "config"


def get_skills_dir() -> Path:
    """获取技能目录"""
    return Path(get_settings().skills_dir)


def ensure_workspace_dirs():
    """确保工作区目录存在"""
    for dir_path in [
        Path(get_settings().handsome_home),
        get_sessions_dir(),
        get_memories_dir(),
        get_logs_dir(),
        get_config_dir(),
        get_skills_dir(),
    ]:
        dir_path.mkdir(parents=True, exist_ok=True)


def get_llm_provider_config(provider: str) -> LLMProviderConfig:
    """获取指定 provider 的配置"""
    providers = get_settings().llm_providers
    if provider in providers:
        config = providers[provider]
        return LLMProviderConfig(
            api_key=config.get("api_key"),
            base_url=config.get("base_url"),
            model=config.get("model"),
            enabled=config.get("enabled", False),
        )
    return LLMProviderConfig()


def get_terminal_config() -> TerminalConfig:
    """获取 Terminal 配置"""
    config = get_settings().terminal
    return TerminalConfig(
        backend=config.get("backend", "local"),
        timeout=config.get("timeout", 60),
        cwd=config.get("cwd"),
        lifetime_seconds=config.get("lifetime_seconds", 300),
        docker_image=config.get("docker_image"),
        ssh_host=config.get("ssh_host"),
        ssh_user=config.get("ssh_user"),
        ssh_port=config.get("ssh_port", 22),
        ssh_key=config.get("ssh_key"),
    )


def get_browser_config() -> BrowserConfig:
    """获取 Browser 配置"""
    config = get_settings().browser
    return BrowserConfig(
        enabled=config.get("enabled", False),
        provider=config.get("provider", "browserbase"),
        api_key=config.get("api_key"),
        project_id=config.get("project_id"),
        proxies=config.get("proxies", True),
        advanced_stealth=config.get("advanced_stealth", False),
        session_timeout=config.get("session_timeout", 300),
        inactivity_timeout=config.get("inactivity_timeout", 120),
    )


def get_session_reset_policy() -> SessionResetPolicy:
    """获取 Session 重置策略"""
    config = get_settings().session_reset
    return SessionResetPolicy(
        mode=config.get("mode", "both"),
        at_hour=config.get("at_hour", 4),
        idle_minutes=config.get("idle_minutes", 1440),
        notify=config.get("notify", True),
    )


def get_platform_config(platform: str) -> PlatformConfig:
    """获取指定 platform 的配置"""
    platforms = get_settings().platforms
    if platform in platforms:
        config = platforms[platform]
        return PlatformConfig(
            enabled=config.get("enabled", False),
            token=config.get("token"),
            api_key=config.get("api_key"),
            home_channel=config.get("home_channel"),
            allowed_users=config.get("allowed_users"),
            require_mention=config.get("require_mention", False),
        )
    return PlatformConfig()


def get_stt_config() -> STTConfig:
    """获取 STT 配置"""
    config = get_settings().stt
    return STTConfig(
        enabled=config.get("enabled", False),
        provider=config.get("provider", "local"),
        model=config.get("model", "base"),
    )


def get_tts_config() -> TTSConfig:
    """获取 TTS 配置"""
    config = get_settings().tts
    return TTSConfig(
        enabled=config.get("enabled", False),
        provider=config.get("provider", "openai"),
        model=config.get("model", "tts-1"),
        voice=config.get("voice", "alloy"),
    )


def get_memory_config() -> MemoryConfig:
    """获取 Memory 配置"""
    config = get_settings().memory
    return MemoryConfig(
        enabled=config.get("enabled", True),
        vector_store=config.get("vector_store", "sqlite"),
        embedding_model=config.get("embedding_model", "text-embedding-3-small"),
        max_entries=config.get("max_entries", 1000),
        summary_threshold=config.get("summary_threshold", 10),
    )


def get_compression_config() -> CompressionConfig:
    """获取 Compression 配置"""
    config = get_settings().compression
    return CompressionConfig(
        enabled=config.get("enabled", True),
        threshold=config.get("threshold", 0.85),
        summary_model=config.get("summary_model", "openai/gpt-4o-mini"),
    )


def get_debug_config() -> DebugConfig:
    """获取 Debug 配置"""
    config = get_settings().debug_tools
    return DebugConfig(
        web_tools=config.get("web_tools", False),
        vision_tools=config.get("vision_tools", False),
        moa_tools=config.get("moa_tools", False),
        image_tools=config.get("image_tools", False),
    )


def get_model_config() -> ModelConfig:
    """获取 Model 配置"""
    config = get_settings().model
    return ModelConfig(
        default=config.get("default", "openai/gpt-4o-mini"),
        fallback=config.get("fallback"),
        max_tokens=config.get("max_tokens", 4096),
        temperature=config.get("temperature", 0.7),
        context_window=config.get("context_window", 128000),
    )