"""配置管理

统一配置系统：YAML 文件 + 环境变量覆盖。
参考 Hermes 配置设计，支持：
- 单一 YAML 配置文件 (~/.handsome_agent/config.yaml)
- 环境变量覆盖 (HANDSOME_* 前缀)
- .env 文件合并
- 完整的 Agent/Terminal/Provider/LLM 配置

🚪 Access - 💬 CLI - 配置管理（统一版本）
"""

from __future__ import annotations

import copy
import json
import logging
import os
import platform
import re
import threading
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

_IS_WINDOWS = platform.system() == "Windows"

# =============================================================================
# Paths
# =============================================================================


def get_default_handsome_home() -> Path:
    """Get the default HANDSOME_HOME directory."""
    home = os.environ.get("HOME") or os.environ.get("USERPROFILE")
    if home:
        return Path(home) / ".handsome_agent"
    return Path(".") / ".handsome_agent"


HANDSOME_HOME = Path(os.environ.get("HANDSOME_HOME", get_default_handsome_home()))


def get_handsome_home() -> Path:
    """Get the HANDSOME_HOME directory (alias for backward compat)."""
    return HANDSOME_HOME


def get_config_path() -> Path:
    """Get the config YAML file path."""
    home = HANDSOME_HOME
    home.mkdir(parents=True, exist_ok=True)
    return home / "config.yaml"


def get_env_path() -> Path:
    """Get the .env file path."""
    home = HANDSOME_HOME
    home.mkdir(parents=True, exist_ok=True)
    return home / ".env"


# =============================================================================
# Provider 默认 Base URL
# =============================================================================

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
# Default Config — Hermes-style schema
# =============================================================================

DEFAULT_CONFIG: dict[str, Any] = {
    # Primary model: "" means use the first configured provider's default
    "model": "",
    # Named provider overrides: provider_name -> {api_key, base_url, model}
    "providers": {},
    # Fallback chains: [{provider, model, base_url}, ...]
    "fallback_providers": [],
    "llm": {
        "provider": "",
        "model": "",
        "api_key": "",
        "base_url": "",
    },
    "model_settings": {
        "name": "",
        "context_window": 128000,
        "temperature": 0.7,
        "max_tokens": 4096,
        # 辅助任务专用模型（空则用主模型）
        "compression_model": "",
        "title_model": "",
        "synthesis_model": "",
        "memory_model": "",
        "auxiliary_model": "",
    },
    "agent": {
        # Maximum conversation turns before forcing stop.
        "max_turns": 90,
        # Inactivity timeout for agent execution (seconds). 0 = unlimited.
        "gateway_timeout": 1800,
        # Graceful drain timeout for restart (seconds). 0 = interrupt immediately.
        "restart_drain_timeout": 0,
        # App-level API retry attempts before surfacing failure.
        "api_max_retries": 3,
        # Tool-use enforcement: "auto" (gpt/codex), true/false, or list of model substrings.
        "tool_use_enforcement": "auto",
        # Intent-ack continuation: "auto", true, false, or list of model substrings.
        "intent_ack_continuation": "auto",
        # Finish the job guidance — prevents stopping after stub.
        "task_completion_guidance": True,
        # Parallel tool call batching guidance.
        "parallel_tool_call_guidance": True,
        # Local env toolchain probe in system prompt.
        "environment_probe": True,
        # Environment hint for hosted deployments.
        "environment_hint": "",
        # Coding posture: "auto", "focus", "on", "off"
        "coding_context": "auto",
        # Standing operator instructions for coding posture.
        "coding_instructions": "",
        # Append guidance when verify finds unverified code edits.
        "verify_guidance": True,
        # Max consecutive verify nudges per turn.
        "max_verify_nudges": 3,
        # Verification closure: "auto", true, false.
        "verify_on_stop": "auto",
        # Inactivity warning threshold (seconds). 0 = disabled.
        "gateway_timeout_warning": 900,
        # Max wait time for clarify-tool response from user (seconds).
        "clarify_timeout": 3600,
        # Periodic "still working" notification interval (seconds). 0 = disabled.
        "gateway_notify_interval": 180,
        # Image input mode: "auto", "native", "text"
        "image_input_mode": "auto",
        # Disabled toolsets: list of toolset names to suppress.
        "disabled_toolsets": [],
        # Goal judge timeout (seconds).
        "judge_timeout": 30.0,
        # Goal judge max output tokens.
        "judge_max_tokens": 4096,
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
        "docker_env": [],
        "ssh_host": None,
        "ssh_user": None,
        "ssh_port": 22,
        "ssh_key": None,
        "daemon_term_grace_seconds": 2.0,
        "persistent_shell": False,
    },
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
        "threshold": 0.75,
    },
    "memory": {
        "enabled": True,
        "builtin_enabled": True,
        "external_provider": None,
        "max_entries": 1000,
        "memory_char_limit": 2200,
        "user_char_limit": 1375,
        "semantic_retrieval_enabled": False,
        "semantic_max_results": 5,
        "semantic_min_score": 0.3,
        "curator_enabled": True,
        "curator_message_threshold": 20,
        "curator_idle_threshold_seconds": 300,
        "curator_auto_user_summary": True,
        "curator_auto_memory_summary": True,
        "curator_max_entries_per_summary": 3,
        "curator_min_entry_length": 20,
        "curator_max_entry_length": 500,
        "curator_check_duplicates": True,
        "curator_use_auxiliary_model": True,
        "retrieval_layer1_threshold": 0.3,
        "retrieval_layer2_threshold": 0.1,
        "retrieval_short_length": 50,
        "retrieval_short_limit": 2,
        "retrieval_total_limit": 5,
        "retrieval_fts_weight": 0.3,
        "retrieval_jaccard_weight": 0.3,
        "retrieval_hrr_weight": 0.4,
    },
    "skills": {
        "external_dirs": [],
        "disabled": [],
        "platform_disabled": {},
        "auto_sync": True,
        "track_usage": True,
        "stale_threshold_days": 90,
    },
    "session_reset": {
        "mode": "both",
        "at_hour": 4,
        "idle_minutes": 1440,
        "notify": True,
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
    "browser": {
        "enabled": False,
        "provider": "browserbase",
        "api_key": None,
        "project_id": None,
        "proxies": True,
        "advanced_stealth": False,
        "session_timeout": 300,
        "inactivity_timeout": 120,
    },
    "stt": {
        "enabled": False,
        "provider": "local",
        "model": "base",
    },
    "tts": {
        "enabled": False,
        "provider": "openai",
        "model": "tts-1",
        "voice": "alloy",
    },
    "logging": {
        "file_enabled": False,
        "max_file_size": 10 * 1024 * 1024,
        "backup_count": 5,
        "rotation": "daily",
    },
    "debug_tools": {
        "web_tools": False,
        "vision_tools": False,
        "moa_tools": False,
        "image_tools": False,
    },
    "platforms": {},
}

# Legacy JSON config field mappings for migration
_LEGACY_JSON_MIGRATION_MAP = {
    "llm": "llm",
    "model": "model_settings",
    "goal.max_turns": ("agent", "max_turns"),
    "goal.judge_timeout": ("agent", "judge_timeout"),
    "goal.judge_max_tokens": ("agent", "judge_max_tokens"),
    "goal.enabled": ("agent", "enabled"),
    "goal.judge_model": ("agent", "judge_model"),
    "terminal": "terminal",
    "session": "session",
    "memory": "memory",
    "display": "display",
    "preferences": "preferences",
    "auxiliary": "auxiliary",
}

# =============================================================================
# Thread-safe config cache
# =============================================================================

_CONFIG_LOCK = threading.RLock()
_CONFIG_CACHE: dict[str, Any] = {}
_LAST_LOAD_STATS: tuple[int, int, int, int] = (0, 0, 0, 0)  # mtime_ns, size, env_hash


def _get_file_stats(path: Path) -> tuple[int, int]:
    """Get file stats (mtime_ns, size)."""
    try:
        st = path.stat()
        return st.st_mtime_ns, st.st_size
    except OSError:
        return 0, 0


def _env_hash() -> int:
    """Hash of relevant env vars for cache invalidation."""
    relevant = {k: v for k, v in os.environ.items() if k.startswith("HANDSOME_")}
    # ponytail: frozenset is fine for the tiny HANDSOME_* env set; string join is slightly cheaper
    return hash("".join(f"{k}={v};" for k, v in sorted(relevant.items())))


def _load_from_yaml(path: Path) -> dict:
    """Load config from YAML file."""
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        logger.warning(f"Failed to parse {path}: {e}. Using default config.")
        return {}


def _save_to_yaml(path: Path, config: dict):
    """Save config to YAML file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, sort_keys=False)


def _deep_merge(base: dict, overlay: dict) -> dict:
    """Deep merge overlay dict into base dict (mutates base)."""
    for key, value in overlay.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _expand_env_vars(config: dict) -> dict:
    """Expand ${VAR} and ${VAR:-default} in string values."""
    pattern = re.compile(r"\$\{([^}:]+)(?::-(.*?))?\}")

    def _expand_value(value: Any) -> Any:
        if isinstance(value, str):

            def replacer(m: re.Match) -> str:
                var_name, default = m.group(1), m.group(2)
                return os.environ.get(
                    var_name, default if default is not None else m.group(0)
                )

            return pattern.sub(replacer, value)
        elif isinstance(value, dict):
            return {k: _expand_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [_expand_value(item) for item in value]
        return value

    return _expand_value(config)


def _load_dotenv() -> dict:
    """Load .env file and return as dict."""
    env_path = get_env_path()
    if not env_path.exists():
        return {}
    result = {}
    try:
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    result[key.strip()] = value.strip().strip("\"'")
    except OSError:
        pass
    return result


def _apply_dotenv_overlay(config: dict, dotenv: dict) -> dict:
    """Apply dotenv key=value pairs to config (HANDSOME_* prefix stripped)."""
    prefix = "HANDSOME_"
    for key, value in dotenv.items():
        if not key.startswith(prefix):
            continue
        # Handle nested keys: HANDSOME_TERMINAL__BACKEND -> terminal.backend
        rest = key[len(prefix) :]
        parts = rest.split("__")
        target = config
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
        target[parts[-1]] = value
    return config


# =============================================================================
# Migration: JSON -> YAML
# =============================================================================


def _migrate_json_to_yaml() -> bool:
    """Migrate legacy config.json to config.yaml. Returns True if migration happened."""
    json_path = HANDSOME_HOME / "config.json"
    yaml_path = HANDSOME_HOME / "config.yaml"
    if json_path.exists() and not yaml_path.exists():
        try:
            with open(json_path, encoding="utf-8") as f:
                json_config = json.load(f)
        except (json.JSONDecodeError, OSError):
            return False

        migrated = _deep_merge(copy.deepcopy(DEFAULT_CONFIG), {})
        for legacy_path, yaml_path_or_tuple in _LEGACY_JSON_MIGRATION_MAP.items():
            parts = legacy_path.split(".")
            value = json_config
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part, None)
                else:
                    value = None
                    break

            if value is not None:
                if isinstance(yaml_path_or_tuple, tuple):
                    # e.g., ("agent", "max_turns")
                    target = migrated
                    for key in yaml_path_or_tuple[:-1]:
                        if key not in target:
                            target[key] = {}
                        target = target[key]
                    target[yaml_path_or_tuple[-1]] = value
                else:
                    # e.g., "terminal" -> migrated["terminal"]
                    migrated[yaml_path_or_tuple] = value

        _save_to_yaml(yaml_path, migrated)
        logger.info(f"Migrated legacy config.json to config.yaml")
        return True
    return False


# =============================================================================
# Config loading — Hermes pattern
# =============================================================================


def load_config(use_cache: bool = True) -> dict:
    """Load configuration from YAML.

    Args:
        use_cache: If True, return cached config when file unchanged.

    Returns:
        Configuration dict with defaults merged in.
    """
    return _load_config_impl(want_deepcopy=True, use_cache=use_cache)


def load_config_readonly() -> dict:
    """Fast-path for callers that ONLY READ config.

    Returns the cached dict directly WITHOUT deepcopy.
    Mutations corrupt the cache — only use when certain no writes occur.
    """
    return _load_config_impl(want_deepcopy=False, use_cache=True)


def _load_config_impl(*, want_deepcopy: bool, use_cache: bool) -> dict:
    global _CONFIG_CACHE, _LAST_LOAD_STATS
    with _CONFIG_LOCK:
        yaml_path = get_config_path()
        current_stats = _get_file_stats(yaml_path)
        current_env_hash = _env_hash()

        if use_cache:
            if (
                current_stats == (_LAST_LOAD_STATS[0], _LAST_LOAD_STATS[1])
                and current_env_hash == _LAST_LOAD_STATS[2]
                and _CONFIG_CACHE
            ):
                return copy.deepcopy(_CONFIG_CACHE) if want_deepcopy else _CONFIG_CACHE

        # Migration check
        _migrate_json_to_yaml()

        # Load file
        file_config = _load_from_yaml(yaml_path)

        # Merge with defaults
        config = _deep_merge(copy.deepcopy(DEFAULT_CONFIG), file_config)

        # Apply dotenv overlay
        dotenv = _load_dotenv()
        if dotenv:
            _apply_dotenv_overlay(config, dotenv)

        # Expand env var references in values
        config = _expand_env_vars(config)

        # Update cache
        _CONFIG_CACHE = config
        _LAST_LOAD_STATS = (current_stats[0], current_stats[1], current_env_hash, 0)

        return copy.deepcopy(config) if want_deepcopy else config


def save_config(config: dict):
    """Save configuration to YAML file."""
    global _CONFIG_CACHE, _LAST_LOAD_STATS
    yaml_path = get_config_path()
    with _CONFIG_LOCK:
        _save_to_yaml(yaml_path, config)
        _CONFIG_CACHE = config
        _LAST_LOAD_STATS = (*_get_file_stats(yaml_path), _env_hash(), 0)


# =============================================================================
# Dot-access helpers (backward compat)
# =============================================================================


def get_settings() -> dict:
    """Get current config as a dict (alias for backward compat)."""
    return load_config()


def get_config_value(key_path: str, default: Any = None) -> Any:
    """Get a configuration value by dot-separated key path.

    Args:
        key_path: Dot-separated key path (e.g., 'llm.provider')
        default: Default value if key not found.
    """
    config = load_config()
    parts = key_path.split(".")
    current = config
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return default
    return current


def set_config_value(key_path: str, value: Any):
    """Set a configuration value by dot-separated key path."""
    config = load_config()
    parts = key_path.split(".")
    current = config
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value
    save_config(config)


# =============================================================================
# Terminal env bridge (Hermes pattern)
# =============================================================================

TERMINAL_CONFIG_ENV_MAP: dict[str, str] = {
    "backend": "TERMINAL_ENV",
    "modal_mode": "TERMINAL_MODAL_MODE",
    "cwd": "TERMINAL_CWD",
    "timeout": "TERMINAL_TIMEOUT",
    "lifetime_seconds": "TERMINAL_LIFETIME_SECONDS",
    "docker_image": "TERMINAL_DOCKER_IMAGE",
    "docker_mount_cwd_to_workspace": "TERMINAL_DOCKER_MOUNT_CWD_TO_WORKSPACE",
    "docker_run_as_host_user": "TERMINAL_DOCKER_RUN_AS_HOST_USER",
    "docker_volumes": "TERMINAL_DOCKER_VOLUMES",
    "docker_network": "TERMINAL_DOCKER_NETWORK",
    "docker_extra_args": "TERMINAL_DOCKER_EXTRA_ARGS",
    "docker_env": "TERMINAL_DOCKER_ENV",
    "ssh_host": "TERMINAL_SSH_HOST",
    "ssh_user": "TERMINAL_SSH_USER",
    "ssh_port": "TERMINAL_SSH_PORT",
    "ssh_key": "TERMINAL_SSH_KEY",
    "persistent_shell": "TERMINAL_PERSISTENT_SHELL",
    "daemon_term_grace_seconds": "TERMINAL_DAEMON_TERM_GRACE_SECONDS",
}


def _terminal_env_value(value: Any) -> str:
    if isinstance(value, (list, dict)):
        return json.dumps(value)
    return str(value)


def apply_terminal_config_to_env(
    *,
    env: Optional[dict[str, str]] = None,
    config: Optional[dict[str, Any]] = None,
) -> dict[str, str]:
    """Bridge terminal.* config keys to env vars for child processes."""
    target = os.environ if env is None else env
    cfg = config if config is not None else load_config_readonly()
    terminal_cfg = cfg.get("terminal", {}) if isinstance(cfg, dict) else {}

    for cfg_key, env_var in TERMINAL_CONFIG_ENV_MAP.items():
        if cfg_key not in terminal_cfg:
            continue
        value = terminal_cfg[cfg_key]
        if cfg_key == "cwd":
            raw_cwd = str(value or "").strip()
            if raw_cwd in {".", "auto", "cwd"}:
                continue
            if isinstance(value, str):
                value = os.path.expanduser(value)
        if env_var not in target:
            target[env_var] = _terminal_env_value(value)
    return target


# =============================================================================
# Config path helpers
# =============================================================================


def reset_config():
    """Reset configuration to defaults."""
    save_config(copy.deepcopy(DEFAULT_CONFIG))


def ensure_config_exists():
    """Ensure config file exists with defaults."""
    yaml_path = get_config_path()
    if not yaml_path.exists():
        save_config(copy.deepcopy(DEFAULT_CONFIG))


def is_configured() -> bool:
    """Check if LLM is configured."""
    config = load_config()
    llm = config.get("llm", {})
    provider = llm.get("provider", "")
    model = llm.get("model", "") or config.get("model_settings", {}).get("name", "")
    return bool(provider and provider != "none" and model)


# =============================================================================
# Install method detection
# =============================================================================


def detect_install_method() -> str:
    """Detect how Handsome Agent was installed. Returns 'pip', 'git', 'docker', or 'source'."""
    home = HANDSOME_HOME
    stamp = home / ".install_method"
    try:
        method = stamp.read_text(encoding="utf-8").strip().lower()
        if method:
            return method
    except OSError:
        pass
    project_root = Path(__file__).parent.parent.resolve()
    if (project_root / ".git").is_dir():
        return "git"
    if os.path.exists("/.dockerenv") or os.path.exists("/run/.containerenv"):
        return "docker"
    return "pip"


def stamp_install_method(method: str):
    """Write the install method stamp."""
    home = HANDSOME_HOME
    home.mkdir(parents=True, exist_ok=True)
    stamp = home / ".install_method"
    try:
        stamp.write_text(method + "\n", encoding="utf-8")
    except OSError:
        pass


# =============================================================================
# Compression constants (used by context_compressor, context_engine, token_estimator)
# =============================================================================

DEFAULT_COMPRESSION_THRESHOLD = 0.75
DEFAULT_SUMMARY_RATIO = 0.20
DEFAULT_PROTECT_FIRST_N = 3
DEFAULT_PROTECT_LAST_N = 6
MIN_SUMMARY_TOKENS = 2000
SUMMARY_TOKENS_CEILING = 12000
SUMMARY_FAILURE_COOLDOWN_SECONDS = 600


# =============================================================================
# Backward-compat dataclass types (used by memory_store, memory_curator)
# These are lightweight wrappers around dict values from get_*_config() helpers.
# =============================================================================

from dataclasses import dataclass, field


@dataclass
class MemoryConfig:
    """Memory config (backward-compat wrapper). Instances are plain dict-like containers."""

    enabled: bool = True
    builtin_enabled: bool = True
    external_provider: Optional[str] = None
    max_entries: int = 1000
    memory_char_limit: int = 2200
    user_char_limit: int = 1375
    semantic_retrieval_enabled: bool = False
    semantic_max_results: int = 5
    semantic_min_score: float = 0.3
    curator_enabled: bool = True
    curator_message_threshold: int = 20
    curator_idle_threshold_seconds: float = 300
    curator_auto_user_summary: bool = True
    curator_auto_memory_summary: bool = True
    curator_max_entries_per_summary: int = 3
    curator_min_entry_length: int = 20
    curator_max_entry_length: int = 500
    curator_check_duplicates: bool = True
    curator_use_auxiliary_model: bool = True
    retrieval_layer1_threshold: float = 0.3
    retrieval_layer2_threshold: float = 0.1
    retrieval_short_length: int = 50
    retrieval_short_limit: int = 2
    retrieval_total_limit: int = 5
    retrieval_fts_weight: float = 0.3
    retrieval_jaccard_weight: float = 0.3
    retrieval_hrr_weight: float = 0.4

    @classmethod
    def from_dict(cls, d: Optional[dict] = None) -> "MemoryConfig":
        if d is None:
            return cls()
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass
class TerminalConfig:
    """Terminal config (backward-compat wrapper)."""

    backend: str = "local"
    timeout: int = 60
    cwd: Optional[str] = None
    lifetime_seconds: int = 300
    docker_image: Optional[str] = None
    ssh_host: Optional[str] = None
    ssh_user: Optional[str] = None
    ssh_port: int = 22
    ssh_key: Optional[str] = None

    @classmethod
    def from_dict(cls, d: Optional[dict] = None) -> "TerminalConfig":
        if d is None:
            return cls()
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in d.items() if k in known})


# =============================================================================
# Dataclass-style config helpers (backward compat with existing call sites)
# =============================================================================


def get_sessions_dir() -> Path:
    return HANDSOME_HOME / "sessions"


def get_memories_dir() -> Path:
    return HANDSOME_HOME / "memories"


def get_logs_dir() -> Path:
    return HANDSOME_HOME / "logs"


def get_config_dir() -> Path:
    return HANDSOME_HOME


def get_skills_dir() -> Path:
    config = load_config()
    skills_cfg = config.get("skills", {})
    external = skills_cfg.get("external_dirs", [])
    if external and isinstance(external, list) and len(external) > 0:
        return Path(external[0])
    return HANDSOME_HOME / "skills"


def get_profile_skills_dir(profile: str = "default") -> Path:
    if profile == "default":
        return HANDSOME_HOME / "skills"
    return HANDSOME_HOME / "profiles" / profile / "skills"


def get_current_profile() -> str:
    env_profile = os.environ.get("HANDSOME_PROFILE")
    if env_profile:
        return env_profile
    profiles_dir = HANDSOME_HOME / "profiles"
    link = profiles_dir / "current"
    if link.is_symlink():
        return link.resolve().name
    return "default"


def ensure_workspace_dirs():
    for dir_path in [
        HANDSOME_HOME,
        get_sessions_dir(),
        get_memories_dir(),
        get_logs_dir(),
        get_config_dir(),
        get_skills_dir(),
    ]:
        dir_path.mkdir(parents=True, exist_ok=True)


def get_llm_provider_config(provider: str) -> dict:
    """Get named provider config."""
    config = load_config()
    providers = config.get("providers", {})
    if provider in providers:
        return dict(providers[provider])
    return {}


def resolve_llm_credentials(
    provider: str, config: Optional[dict] = None
) -> tuple[str, str, str, str]:
    """Resolve LLM credentials for a provider.

    Returns (api_key, base_url, model, provider_model) preferring
    provider-specific config over the legacy llm.* top-level keys.

    Args:
        provider: Provider name (e.g. 'minimax').
        config: Optional pre-loaded config dict to avoid re-loading.

    Returns:
        (api_key, base_url, effective_model, provider_from_config)
    """
    if config is None:
        config = load_config()

    pconf = config.get("providers", {}).get(provider, {})
    llm = config.get("llm", {})

    api_key = pconf.get("api_key") or llm.get("api_key", "")
    base_url = pconf.get("base_url") or llm.get("base_url") or ""
    model = pconf.get("model") or llm.get("model", "")
    # provider-level model overrides the top-level model
    provider_model = pconf.get("model") or model

    return api_key, base_url, provider_model, provider


def get_model_config() -> dict:
    """Get model config."""
    config = load_config()
    return dict(config.get("model_settings", {}))


def get_terminal_config() -> dict:
    """Get terminal config."""
    config = load_config()
    return dict(config.get("terminal", {}))


def get_browser_config() -> dict:
    """Get browser config."""
    config = load_config()
    return dict(config.get("browser", {}))


def get_session_reset_policy() -> dict:
    """Get session reset policy."""
    config = load_config()
    return dict(config.get("session_reset", {}))


def get_platform_config(platform: str) -> dict:
    """Get platform config."""
    config = load_config()
    platforms = config.get("platforms", {})
    return dict(platforms.get(platform, {})) if platform in platforms else {}


def get_stt_config() -> dict:
    """Get STT config."""
    config = load_config()
    return dict(config.get("stt", {}))


def get_tts_config() -> dict:
    """Get TTS config."""
    config = load_config()
    return dict(config.get("tts", {}))


def get_memory_config() -> dict:
    """Get memory config."""
    config = load_config()
    return dict(config.get("memory", {}))


def get_compression_config() -> dict:
    """Get compression config."""
    config = load_config()
    return dict(config.get("compression", {}))


def get_debug_config() -> dict:
    """Get debug config."""
    config = load_config()
    return dict(config.get("debug_tools", {}))


def get_logging_config() -> dict:
    """Get logging config."""
    config = load_config()
    return dict(config.get("logging", {}))


def get_skills_config() -> dict:
    """Get skills config."""
    config = load_config()
    return dict(config.get("skills", {}))


def get_disabled_skills(platform: Optional[str] = None) -> list[str]:
    """Get list of disabled skills."""
    config = load_config()
    skills_cfg = config.get("skills", {})
    disabled = list(skills_cfg.get("disabled", []))
    if platform:
        platform_disabled = skills_cfg.get("platform_disabled", {}).get(platform, [])
        disabled = list(set(disabled + platform_disabled))
    return disabled


def get_external_skills_dirs() -> list[Path]:
    """Get external skills directories."""
    config = load_config()
    skills_cfg = config.get("skills", {})
    dirs = []
    for dir_path in skills_cfg.get("external_dirs", []):
        path = Path(dir_path).expanduser()
        if path.exists():
            dirs.append(path)
    return dirs


def get_skills_external_dirs() -> list[str]:
    """Get external skills dirs as strings."""
    config = load_config()
    skills_cfg = config.get("skills", {})
    external_dirs = skills_cfg.get("external_dirs", [])
    if isinstance(external_dirs, str):
        return [external_dirs]
    return list(external_dirs) if external_dirs else []


# =============================================================================
# Config validator (backward compat)
# =============================================================================


class ConfigValidator:
    """Configuration validator."""

    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def validate(self) -> bool:
        """Validate configuration."""
        self.errors.clear()
        self.warnings.clear()
        config = load_config()
        llm = config.get("llm", {})
        if not llm.get("provider"):
            self.warnings.append("LLM provider not configured")
        if not llm.get("model") and not config.get("model_settings", {}).get("name"):
            self.warnings.append("Model not configured")
        if llm.get("provider") not in ("none", "") and not llm.get("api_key"):
            self.warnings.append(
                "API key not set for provider: " + llm.get("provider", "")
            )
        return len(self.errors) == 0

    def get_report(self) -> str:
        """Get validation report."""
        lines = []
        if self.errors:
            lines.append("Errors:")
            for error in self.errors:
                lines.append(f"  ✗ {error}")
        if self.warnings:
            lines.append("\nWarnings:")
            for warning in self.warnings:
                lines.append(f"  ⚠ {warning}")
        if not self.errors and not self.warnings:
            lines.append("✓ Configuration is valid")
        return "\n".join(lines)
