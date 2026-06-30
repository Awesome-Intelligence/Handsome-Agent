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
    """记忆配置

    包含所有记忆系统相关的配置项：
    - enabled: 是否启用记忆功能（总开关）
    - builtin_enabled: 是否启用内置记忆（通过 BuiltinMemoryProvider）
    - external_provider: 外部 Provider 名称（可选，为 None 则不加载）
    - max_entries: 最大记忆条目数限制
    - memory_char_limit: Agent 记忆（MEMORY.md）的字符限制
    - user_char_limit: 用户画像（USER.md）的字符限制

    语义检索配置：
    - semantic_retrieval_enabled: 是否启用语义检索（可选功能）
    - semantic_max_results: 语义检索返回的最大结果数
    - semantic_min_score: 语义检索最低相似度阈值

    自动总结配置 (Curator)：
    - curator_enabled: 是否启用自动记忆总结
    - curator_message_threshold: 触发总结的消息数阈值
    - curator_idle_threshold_seconds: 空闲超时触发总结
    - curator_auto_user_summary: 自动总结用户偏好
    - curator_auto_memory_summary: 自动总结环境信息
    - curator_max_entries_per_summary: 每次总结最大条目数
    - curator_check_duplicates: 是否检查重复条目
    - curator_use_auxiliary_model: 使用辅助模型进行总结

    检索策略配置：
    - retrieval_layer1_threshold: 第一层高置信度阈值
    - retrieval_layer2_threshold: 第二层宽松阈值
    - retrieval_short_length: 短记忆阈值（字符数）
    - retrieval_short_limit: 短记忆最多返回数量
    - retrieval_total_limit: 总返回数量限制
    - retrieval_fts_weight: FTS5 权重
    - retrieval_jaccard_weight: Jaccard 权重
    - retrieval_hrr_weight: HRR 语义权重
    - retrieval_keyword_min_overlap: 关键词最小重叠数

    使用示例：
        config = MemoryConfig()  # 默认配置
        config = MemoryConfig(
            enabled=True,
            builtin_enabled=True,
            external_provider=None,  # 不加载外部 Provider
            memory_char_limit=2200,
            semantic_retrieval_enabled=True,
            curator_enabled=True,
            retrieval_total_limit=10,  # 增加返回数量
            retrieval_fts_weight=0.4,   # 调整检索权重
        )

    注意：
    - 向量存储和嵌入模型：当前使用本地 HRR 实现，无需外部服务
    - CuratorConfig 已整合到此配置中，保持向后兼容
    """
    enabled: bool = True           # 总开关
    builtin_enabled: bool = True    # 内置 Provider 开关
    external_provider: Optional[str] = None  # 外部 Provider 名称，为 None 则不加载
    max_entries: int = 1000
    memory_char_limit: int = 2200   # Agent 记忆字符限制
    user_char_limit: int = 1375    # 用户画像字符限制

    # 语义检索配置
    semantic_retrieval_enabled: bool = False  # 默认关闭
    semantic_max_results: int = 5              # 最大结果数
    semantic_min_score: float = 0.3           # 最低相似度

    # =========================================================
    # Curator 自动总结配置（v9.3.0+）
    # 这些配置会被 MemoryCurator 使用
    # =========================================================
    curator_enabled: bool = True  # 启用自动总结
    curator_message_threshold: int = 20  # 消息数阈值
    curator_idle_threshold_seconds: float = 300  # 空闲超时（秒）
    curator_auto_user_summary: bool = True  # 自动总结用户偏好
    curator_auto_memory_summary: bool = True  # 自动总结环境信息
    curator_max_entries_per_summary: int = 3  # 每次总结最大条目数
    curator_min_entry_length: int = 20  # 最小条目长度
    curator_max_entry_length: int = 500  # 最大条目长度
    curator_check_duplicates: bool = True  # 检查重复条目
    curator_use_auxiliary_model: bool = True  # 使用辅助模型

    # =========================================================
    # 检索策略配置（v9.3.0+）
    # 控制预取和检索的行为
    # =========================================================
    # 分层预取配置
    retrieval_layer1_threshold: float = 0.3  # 第一层高置信度阈值
    retrieval_layer2_threshold: float = 0.1  # 第二层宽松阈值
    retrieval_short_length: int = 50  # 短记忆阈值（字符数）
    retrieval_short_limit: int = 2  # 短记忆最多返回数量
    retrieval_total_limit: int = 5  # 总返回数量限制

    # 检索权重配置（语义检索启用时生效）
    retrieval_fts_weight: float = 0.3  # FTS5 权重
    retrieval_jaccard_weight: float = 0.3  # Jaccard 权重
    retrieval_hrr_weight: float = 0.4  # HRR 语义权重

    # 关键词检索配置（语义检索禁用时使用）
    retrieval_keyword_min_overlap: int = 1  # 最小关键词重叠数


# =============================================================================
# Context 压缩常量（必须在 CompressionConfig 之前定义）
# =============================================================================

# 压缩阈值：上下文使用达到此比例时触发压缩
DEFAULT_COMPRESSION_THRESHOLD = 0.75

# 摘要比例：压缩后保留的 token 比例
DEFAULT_SUMMARY_RATIO = 0.20

# 头部保护：保留前 N 条消息（system + 初始交互）
DEFAULT_PROTECT_FIRST_N = 3

# 尾部保护：保留后 N 条消息
DEFAULT_PROTECT_LAST_N = 6

# 最小摘要 token 数
MIN_SUMMARY_TOKENS = 2000

# 摘要 token 上限
SUMMARY_TOKENS_CEILING = 12000

# 摘要失败冷却时间（秒）
SUMMARY_FAILURE_COOLDOWN_SECONDS = 600


@dataclass
class CompressionConfig:
    """Context 压缩配置"""
    enabled: bool = True
    threshold: float = DEFAULT_COMPRESSION_THRESHOLD  # 0.75
    summary_model: str = "openai/gpt-4o-mini"


@dataclass
class DebugConfig:
    """Debug 配置"""
    web_tools: bool = False
    vision_tools: bool = False
    moa_tools: bool = False
    image_tools: bool = False


@dataclass
class LoggingConfig:
    """文件日志配置"""
    file_enabled: bool = False
    max_file_size: int = 10 * 1024 * 1024
    backup_count: int = 5
    rotation: str = "daily"


class Settings(BaseSettings):
    """应用配置"""
    
    app_name: str = "HandsomeAgent"
    app_version: str = "1.0.0"
    debug: bool = False
    
    handsome_home: str = str(HANDSOME_HOME)
    
    brain_service_host: str = "0.0.0.0"
    brain_service_port: int = 8000  # 统一使用 8000 端口 (合并 api/ 到 gateway/)
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
    })
    
    compression: Dict[str, Any] = Field(default_factory=lambda: {
        "enabled": True,
        "threshold": 0.85,
    })
    
    debug_tools: Dict[str, Any] = Field(default_factory=lambda: {
        "web_tools": False,
        "vision_tools": False,
    })
    
    logging: Dict[str, Any] = Field(default_factory=lambda: {
        "file_enabled": False,
        "max_file_size": 50 * 1024 * 1024,
        "backup_count": 30,  # 保留30天
        "rotation": "daily",
    })

    # Tool Loop Guardrail 配置（参考 Hermes）
    # 用于防止 Agent 在工具调用时陷入无限循环
    tool_loop_guardrail: Dict[str, Any] = Field(default_factory=lambda: {
        "warnings_enabled": True,  # 是否启用警告
        "hard_stop_enabled": False,  # 是否启用硬停止（阻止工具执行）
        "warn_after": {
            "exact_failure": 2,  # 完全相同的调用失败 2 次后警告
            "same_tool_failure": 3,  # 同一工具失败 3 次后警告
            "idempotent_no_progress": 2,  # 幂等工具无进展 2 次后警告
        },
        "hard_stop_after": {
            "exact_failure": 5,  # 完全相同的调用失败 5 次后阻止
            "same_tool_failure": 8,  # 同一工具失败 8 次后停止
            "idempotent_no_progress": 5,  # 幂等工具无进展 5 次后阻止
        },
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
        max_entries=config.get("max_entries", 1000),
        memory_char_limit=config.get("memory_char_limit", 2200),
        user_char_limit=config.get("user_char_limit", 1375),
        # 语义检索配置
        semantic_retrieval_enabled=config.get("semantic_retrieval_enabled", False),
        semantic_max_results=config.get("semantic_max_results", 5),
        semantic_min_score=config.get("semantic_min_score", 0.3),
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


def get_logging_config() -> LoggingConfig:
    """获取日志配置"""
    config = get_settings().logging
    return LoggingConfig(
        file_enabled=config.get("file_enabled", False),
        max_file_size=config.get("max_file_size", 10 * 1024 * 1024),
        backup_count=config.get("backup_count", 5),
        rotation=config.get("rotation", "daily"),
    )