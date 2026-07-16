"""CLI config shim — backward-compat wrapper around common.config.

Re-exports all public symbols from common.config so CLI commands
and other callers that import from here work without modification.

🚪 Access - 💬 CLI - 配置管理（shim 层）
"""

from common.config import (
    # Core loading
    load_config,
    load_config_readonly,
    save_config,
    # Path helpers
    get_config_path,
    get_env_path,
    get_agentz_home,
    AGENT_Z_HOME,
    # Legacy compat
    get_config_value,
    set_config_value,
    DEFAULT_CONFIG,
    # Init helpers
    ensure_config_exists,
    is_configured,
    reset_config,
    # Install method
    detect_install_method,
    stamp_install_method,
    # Validator
    ConfigValidator,
    # Terminal bridge
    apply_terminal_config_to_env,
    TERMINAL_CONFIG_ENV_MAP,
    # Settings helpers
    get_settings,
    get_sessions_dir,
    get_memories_dir,
    get_logs_dir,
    get_config_dir,
    get_skills_dir,
    get_profile_skills_dir,
    get_current_profile,
    ensure_workspace_dirs,
    # Typed config getters
    get_llm_provider_config,
    get_model_config,
    get_terminal_config,
    get_browser_config,
    get_session_reset_policy,
    get_platform_config,
    get_stt_config,
    get_tts_config,
    get_memory_config,
    get_compression_config,
    get_debug_config,
    get_logging_config,
    get_skills_config,
    get_disabled_skills,
    get_external_skills_dirs,
    get_skills_external_dirs,
    # Constants
    DEFAULT_LLM_BASE_URLS,
)

__all__ = [
    "load_config",
    "load_config_readonly",
    "save_config",
    "get_config_path",
    "get_env_path",
    "get_agentz_home",
    "AGENT_Z_HOME",
    "get_config_value",
    "set_config_value",
    "DEFAULT_CONFIG",
    "ensure_config_exists",
    "is_configured",
    "reset_config",
    "detect_install_method",
    "stamp_install_method",
    "ConfigValidator",
    "apply_terminal_config_to_env",
    "TERMINAL_CONFIG_ENV_MAP",
    "get_settings",
    "get_sessions_dir",
    "get_memories_dir",
    "get_logs_dir",
    "get_config_dir",
    "get_skills_dir",
    "get_profile_skills_dir",
    "get_current_profile",
    "ensure_workspace_dirs",
    "get_llm_provider_config",
    "get_model_config",
    "get_terminal_config",
    "get_browser_config",
    "get_session_reset_policy",
    "get_platform_config",
    "get_stt_config",
    "get_tts_config",
    "get_memory_config",
    "get_compression_config",
    "get_debug_config",
    "get_logging_config",
    "get_skills_config",
    "get_disabled_skills",
    "get_external_skills_dirs",
    "get_skills_external_dirs",
    "DEFAULT_LLM_BASE_URLS",
]
