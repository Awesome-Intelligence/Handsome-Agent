"""配置管理

统一配置系统：YAML 文件 + 环境变量覆盖。
参考 Hermes 配置设计，支持：
- 单一 YAML 配置文件 (~/.agent_z/config.yaml)
- 环境变量覆盖 (AGENT_Z_* 前缀)
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
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

_IS_WINDOWS = platform.system() == "Windows"

# Env var names that influence how the next subprocess executes or relocate
# Agent-Z state — never writable through ``set_config_value`` / .env writers.
# Defence in depth against a future dashboard/CLI writer planting RCE or
# state-relocation values. Mirrors Hermes' _ENV_VAR_NAME_DENYLIST.
_ENV_VAR_NAME_DENYLIST: frozenset = frozenset({
    # Loader / linker
    "LD_PRELOAD", "LD_LIBRARY_PATH", "LD_AUDIT", "LD_DEBUG",
    "DYLD_INSERT_LIBRARIES", "DYLD_LIBRARY_PATH", "DYLD_FRAMEWORK_PATH",
    # Python
    "PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONUSERBASE",
    "PYTHONEXECUTABLE", "PYTHONNOUSERSITE",
    # Node
    "NODE_OPTIONS", "NODE_PATH",
    # General
    "PATH", "SHELL", "BROWSER", "EDITOR", "VISUAL", "PAGER",
    # Git
    "GIT_SSH_COMMAND", "GIT_EXEC_PATH", "GIT_SHELL",
    # Agent-Z runtime location — never via writer.
    "AGENT_Z_HOME", "AGENT_Z_PROFILE", "AGENT_Z_CONFIG", "AGENT_Z_ENV",
})

# Track which (config_path, mtime_ns, size) tuples we've already warned about
# so concurrent CLI/gateway loads of a broken config.yaml don't spam stderr
# every call. Cleared automatically when the file changes (different mtime).
_CONFIG_PARSE_WARNED: set = set()

# =============================================================================
# Paths
# =============================================================================


def get_default_agent_z_home() -> Path:
    """Get the default AGENT_Z_HOME directory."""
    home = os.environ.get("HOME") or os.environ.get("USERPROFILE")
    if home:
        return Path(home) / ".agent_z"
    return Path(".") / ".agent_z"


AGENT_Z_HOME = Path(os.environ.get("AGENT_Z_HOME", get_default_agent_z_home()))


def get_agent_z_home() -> Path:
    """Get the AGENT_Z_HOME directory (alias for backward compat)."""
    return AGENT_Z_HOME


# Alias for backward compatibility (without underscore)
get_agentz_home = get_agent_z_home


def get_config_path() -> Path:
    """Get the config YAML file path."""
    home = AGENT_Z_HOME
    home.mkdir(parents=True, exist_ok=True)
    return home / "config.yaml"


def get_env_path() -> Path:
    """Get the .env file path."""
    home = AGENT_Z_HOME
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
    # Named provider overrides: provider_name -> {api_key, base_url, model}
    "providers": {},
    # Fallback chains: [{provider, model, base_url}, ...]
    "fallback_providers": [],
    "llm": {
        "provider": "",
        "model": "",
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
        # Freshness window for auto-continue note after gateway crash (seconds).
        # After a crash/restart/SIGTERM mid-run, the next message gets a
        # "[System note: your previous turn was interrupted]" prepended.
        # Stale markers (transcript hours/days old) can revive unrelated old tasks.
        # This window is the max age of the last transcript row for which we
        # still inject the continue note. Set 0 to always inject.
        "gateway_auto_continue_freshness": 3600,
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
        # HOME handling for host tool subprocesses:
        #   auto    — host keeps real OS-user HOME; containers use AGENT_Z_HOME/home (default)
        #   real    — force the real OS-user HOME
        #   profile — force AGENT_Z_HOME/home when it exists
        "home_mode": "auto",
        # Extra files to source in the login shell when building the
        # per-session environment snapshot. Use this when tools like nvm,
        # pyenv, asdf need files that a bash login shell would skip.
        # Paths support ~ and ${VAR}. Missing files are silently skipped.
        "shell_init_files": [],
        # When true, Hermes sources ~/.profile, ~/.bash_profile, ~/.bashrc
        # in the login shell used to build the environment snapshot.
        "auto_source_bashrc": True,
        # Container resource limits (docker, singularity, modal, daytona — ignored for local/ssh)
        "container_cpu": 1,
        "container_memory": 5120,       # MB (default 5GB)
        "container_disk": 51200,        # MB (default 50GB)
        "container_persistent": True,   # Persist filesystem across sessions
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
        "threshold": 0.50,            # compress when context usage exceeds this ratio
        "target_ratio": 0.20,         # fraction of threshold to preserve as recent tail
        "protect_last_n": 20,        # minimum recent messages to keep uncompressed
        "hygiene_hard_message_limit": 5000,  # gateway session-hygiene force-compress threshold by message count
        "protect_first_n": 3,         # non-system head messages always preserved verbatim
        "abort_on_summary_failure": False,  # When True, auto-compression that fails aborts the run
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
        # Timeout for browser commands in seconds (screenshot, navigate, etc.)
        "command_timeout": 30,
        # Auto-record browser sessions as WebM videos
        "record_sessions": False,
        # Allow navigating to private/internal IPs (localhost, 192.168.x.x, etc.)
        "allow_private_urls": False,
        # Browser engine for local mode: "auto", "lightpanda", "chrome"
        "engine": "auto",
        # When a cloud provider is set, auto-spawn local Chromium for LAN/localhost URLs
        "auto_local_for_private_urls": True,
        # Optional persistent CDP endpoint for attaching to an existing Chromium/Chrome
        "cdp_url": "",
        # Allow browser_console(expression=...) to use sensitive JS primitives
        "allow_unsafe_evaluate": False,
        # CDP supervisor — dialog + frame detection via persistent WebSocket.
        # Active only when a CDP-capable backend is attached (Browserbase or local Chrome).
        "dialog_policy": "must_respond",  # must_respond | auto_dismiss | auto_accept
        "dialog_timeout_s": 300,  # Safety auto-dismiss after N seconds under must_respond
        # Camofox — anti-detection Firefox configuration
        "camofox": {
            "managed_persistence": False,  # Stable profile-scoped userId
            "user_id": "",
            "session_key": "",
            "adopt_existing_tab": False,
            # Rewrite loopback URLs to host alias inside Docker Camofox
            "rewrite_loopback_urls": False,
            "loopback_host_alias": "host.docker.internal",
        },
    },
    "web": {
        "backend": "",           # shared fallback — applies to both search and extract
        "search_backend": "",    # per-capability override for web_search (e.g. "searxng")
        "extract_backend": "",   # per-capability override for web_extract (e.g. "native")
        "extract_char_limit": 15000,  # per-page char budget for web_extract
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
    # Filesystem checkpoints — automatic snapshots before destructive file ops.
    # When enabled, the agent takes a snapshot of the working directory once
    # per conversation turn (on first write_file/patch call). Use /rollback
    # to restore.
    "checkpoints": {
        "enabled": False,
        "max_snapshots": 20,           # Max checkpoints per working directory
        "max_total_size_mb": 500,      # Hard ceiling on ~/.agent_z/checkpoints/ size
        "max_file_size_mb": 10,        # Skip files larger than this when staging
        "auto_prune": True,            # Sweep orphans/stale at startup
        "retention_days": 7,
        "delete_orphans": True,
        "min_interval_hours": 24,
    },
    # Hard cap (chars) for a single automatic context file such as SOUL.md,
    # AGENTS.md, CLAUDE.md, .agent_z.md before Hermes applies head/tail
    # truncation. null (default) lets the cap scale with model's context window.
    "context_file_max_chars": None,
    # Maximum characters returned by a single read_file call. Reads that exceed
    # this are rejected with guidance to use offset+limit.
    "file_read_max_chars": 100_000,
    # Seconds to wait at agent-build time for in-flight MCP server discovery
    # to finish before the agent snapshots its tool list. MCP discovery runs
    # in a background thread so a slow/dead server can't freeze startup.
    "mcp_discovery_timeout": 1.5,
    # Tool-output truncation thresholds.
    "tool_output": {
        "max_bytes": 50_000,        # terminal_tool output cap in chars
        "max_lines": 2000,          # read_file pagination cap
        "max_line_length": 2000,    # per-line cap for line-numbered view
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
# Cache signature = (mtime_ns, size, env_ref_snapshot_dict_id).
# The snapshot is a frozendict-like view of ``{VAR: current_env_value}`` for
# every ``${VAR}`` referenced anywhere in the merged config — so when an
# external ``.env`` rotation or in-process ``os.environ`` mutation changes a
# referenced variable, the next ``load_config()`` correctly invalidates the
# cache instead of returning stale expanded values.
_LAST_LOAD_STATS: tuple[int, int, int] = (0, 0, 0)
_LAST_ENV_SNAPSHOT: dict[str, Optional[str]] = {}


def _get_file_stats(path: Path) -> tuple[int, int]:
    """Get file stats (mtime_ns, size)."""
    try:
        st = path.stat()
        return st.st_mtime_ns, st.st_size
    except OSError:
        return 0, 0


# ponytail: also detects ${AGENTZ_*}-prefixed refs that match Hermes-style
# conventions, but the writer-prefix check in the previous code missed plain
# $FOO refs. The snapshot approach below catches every ${...} reference.
_ENV_REF_PATTERN = re.compile(r"\$\{([^}:]+)(?::-(.*?))?\}")


def _extract_env_refs(value: Any, refs: Optional[set] = None) -> set:
    """Walk a config tree and collect every ``${VAR}`` variable name.

    Used to build the env snapshot that drives cache invalidation: if any
    of these names change in ``os.environ`` between loads, the cached
    expanded config is stale and must be rebuilt.
    """
    if refs is None:
        refs = set()
    if isinstance(value, str):
        for m in _ENV_REF_PATTERN.finditer(value):
            refs.add(m.group(1))
    elif isinstance(value, dict):
        for v in value.values():
            _extract_env_refs(v, refs)
    elif isinstance(value, list):
        for item in value:
            _extract_env_refs(item, refs)
    return refs


def _env_snapshot(config: dict) -> dict[str, Optional[str]]:
    """Snapshot ``{VAR: current os.environ value}`` for every ``${VAR}`` in config."""
    refs = _extract_env_refs(config)
    return {name: os.environ.get(name) for name in refs}


def _backup_corrupt_config(config_path: Path) -> Optional[Path]:
    """Snapshot a broken config.yaml to ``config.yaml.corrupt.<ts>.bak``.

    On YAML parse failure ``_load_from_yaml`` falls back to defaults and the
    user's broken file stays on disk untouched. If the user later runs the
    setup wizard or ``set_config_value`` (both rewrite config.yaml), the
    broken-but-recoverable content is gone for good. This snapshot preserves
    it so the user can diff/repair it. Best-effort — any failure is swallowed
    so backup problems never block config loading.

    Returns the backup path on success, else ``None``. Symlinks are not
    followed/copied to avoid clobbering whatever a malicious/misconfigured
    symlink points at.
    """
    try:
        if config_path.is_symlink():
            return None
        st = config_path.stat()
        if st.st_size == 0:
            return None
        ts = time.strftime("%Y%m%d-%H%M%S")
        backup_path = config_path.with_name(
            f"{config_path.name}.corrupt.{ts}.bak"
        )
        if backup_path.exists():
            return None
        # Dedup: same-second siblings of identical size are likely the same
        # corruption already preserved.
        sibling_baks = list(
            config_path.parent.glob(f"{config_path.name}.corrupt.*.bak")
        )
        for existing in sibling_baks:
            try:
                if existing.stat().st_size == st.st_size:
                    return None
            except OSError:
                continue
        shutil.copy2(config_path, backup_path)
        return backup_path
    except Exception:
        return None


def _warn_config_parse_failure(config_path: Path, exc: Exception) -> None:
    """Surface a config.yaml parse failure to user, log, and stderr.

    Without this, a YAML parse error silently falls back to defaults and the
    user loses every override (providers, model, terminal, ...) with no
    visible signal. We warn once per (path, mtime_ns, size) so re-loading
    the same broken file doesn't spam, and re-warn automatically when the
    file changes.
    """
    try:
        st = config_path.stat()
        key = (str(config_path), st.st_mtime_ns, st.st_size)
    except OSError:
        key = (str(config_path), 0, 0)
    if key in _CONFIG_PARSE_WARNED:
        return
    _CONFIG_PARSE_WARNED.add(key)

    backup_path = _backup_corrupt_config(config_path)
    msg = (
        f"Failed to parse {config_path}: {exc}. "
        "Falling back to default config — every user override "
        "(providers, model, terminal, ...) is being IGNORED. "
        "Fix the YAML and restart."
    )
    if backup_path is not None:
        msg += f" A copy of the corrupted file was saved to {backup_path}."
    logger.warning(msg)
    try:
        sys.stderr.write(f"⚠️  Agent-Z config: {msg}\n")
        sys.stderr.flush()
    except Exception:
        pass


def _load_from_yaml(path: Path) -> dict:
    """Load config from YAML file."""
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        _warn_config_parse_failure(path, e)
        return {}


def _atomic_yaml_write(path: Path, config: dict) -> None:
    """Write YAML atomically: tmp file in the same dir + os.replace.

    Avoids half-written files when the process is killed mid-write. The
    tmp lives next to the target so ``os.replace`` is atomic on the same
    filesystem (POSIX rename, Windows MoveFileEx with REPLACE_EXISTING).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    # NamedTemporaryFile with delete=False gives us a unique name; we
    # replace-and-cleanup explicitly below.
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True, sort_keys=False)
        os.replace(tmp_name, path)
    except Exception:
        # Best-effort cleanup of the orphan tmp so the directory doesn't
        # accumulate them across crashes.
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _save_to_yaml(path: Path, config: dict):
    """Save config to YAML file (atomic)."""
    _atomic_yaml_write(path, config)


def _reject_denylisted_env_key(key: str) -> None:
    """Raise if ``key`` is in :data:`_ENV_VAR_NAME_DENYLIST`.

    Names that influence subprocess execution (LD_PRELOAD, PYTHONPATH, PATH,
    EDITOR, ...) or Agent-Z runtime location (AGENT_Z_HOME, ...) cannot be
    persisted via the config writer. If a legitimate override is genuinely
    needed, edit ``~/.agent_z/config.yaml`` or ``~/.agent_z/.env`` directly.
    """
    if key in _ENV_VAR_NAME_DENYLIST:
        raise ValueError(
            f"Environment variable {key!r} is on the writer denylist. "
            "Names that influence subprocess execution (LD_PRELOAD, "
            "PYTHONPATH, PATH, EDITOR, ...) or Agent-Z runtime location "
            "(AGENT_Z_HOME, ...) cannot be persisted via the config writer. "
            "If you really need this, edit ~/.agent_z/config.yaml or "
            "~/.agent_z/.env directly."
        )


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
    """Apply dotenv key=value pairs to config (AGENTZ_* prefix stripped)."""
    prefix = "AGENTZ_"
    for key, value in dotenv.items():
        if not key.startswith(prefix):
            continue
        # Handle nested keys: AGENTZ_TERMINAL__BACKEND -> terminal.backend
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
    json_path = AGENT_Z_HOME / "config.json"
    yaml_path = AGENT_Z_HOME / "config.yaml"
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
    global _CONFIG_CACHE, _LAST_LOAD_STATS, _LAST_ENV_SNAPSHOT
    with _CONFIG_LOCK:
        yaml_path = get_config_path()
        current_stats = _get_file_stats(yaml_path)

        # Migration check (idempotent — only writes on first migration).
        _migrate_json_to_yaml()

        # Build the candidate merged config to scan for env refs. On cache
        # miss we need the snapshot of the FRESH config; on cache hit we
        # need a snapshot of whatever the CURRENT expanded config would
        # reference, which is the cached one. Computing it on the cached
        # value lets us detect env drift without re-running yaml + merge.
        if use_cache and _CONFIG_CACHE:
            current_snapshot = _env_snapshot(_CONFIG_CACHE)
            cache_match = (
                current_stats == (_LAST_LOAD_STATS[0], _LAST_LOAD_STATS[1])
                and current_snapshot == _LAST_ENV_SNAPSHOT
            )
            if cache_match:
                return copy.deepcopy(_CONFIG_CACHE) if want_deepcopy else _CONFIG_CACHE

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

        # Update cache + env snapshot
        new_snapshot = _env_snapshot(config)
        _CONFIG_CACHE = config
        _LAST_LOAD_STATS = current_stats
        _LAST_ENV_SNAPSHOT = new_snapshot

        return copy.deepcopy(config) if want_deepcopy else config


def save_config(config: dict):
    """Save configuration to YAML file (atomic on disk)."""
    global _CONFIG_CACHE, _LAST_LOAD_STATS, _LAST_ENV_SNAPSHOT
    yaml_path = get_config_path()
    with _CONFIG_LOCK:
        _save_to_yaml(yaml_path, config)
        _CONFIG_CACHE = config
        _LAST_LOAD_STATS = _get_file_stats(yaml_path)
        _LAST_ENV_SNAPSHOT = _env_snapshot(config)


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
    """Set a configuration value by dot-separated key path.

    Raises ``ValueError`` if the final key segment matches a denylisted env
    name (LD_PRELOAD, PYTHONPATH, PATH, EDITOR, AGENT_Z_HOME, ...). Defends
    against a future dashboard / API writer planting RCE or state-relocation
    values via a dot-path that ends in one of those names.
    """
    if not key_path:
        raise ValueError("key_path must be non-empty")
    parts = key_path.split(".")
    leaf = parts[-1]
    # Only reject leaf names that look like env-var-shaped identifiers so
    # benign config keys (e.g. "model_settings.context_window") still pass.
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", leaf):
        _reject_denylisted_env_key(leaf)
    config = load_config()
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
    "docker_forward_env": "TERMINAL_DOCKER_FORWARD_ENV",
    "container_cpu": "TERMINAL_CONTAINER_CPU",
    "container_memory": "TERMINAL_CONTAINER_MEMORY",
    "container_disk": "TERMINAL_CONTAINER_DISK",
    "container_persistent": "TERMINAL_CONTAINER_PERSISTENT",
    "ssh_host": "TERMINAL_SSH_HOST",
    "ssh_user": "TERMINAL_SSH_USER",
    "ssh_port": "TERMINAL_SSH_PORT",
    "ssh_key": "TERMINAL_SSH_KEY",
    "persistent_shell": "TERMINAL_PERSISTENT_SHELL",
    "daemon_term_grace_seconds": "TERMINAL_DAEMON_TERM_GRACE_SECONDS",
    "home_mode": "TERMINAL_HOME_MODE",
    "shell_init_files": "TERMINAL_SHELL_INIT_FILES",
    "auto_source_bashrc": "TERMINAL_AUTO_SOURCE_BASHRC",
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
    """Detect how Agent-Z was installed. Returns 'pip', 'git', 'docker', or 'source'."""
    home = AGENT_Z_HOME
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
    home = AGENT_Z_HOME
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
    return AGENT_Z_HOME / "sessions"


def get_memories_dir() -> Path:
    return AGENT_Z_HOME / "memories"


def get_logs_dir() -> Path:
    return AGENT_Z_HOME / "logs"


def get_config_dir() -> Path:
    return AGENT_Z_HOME


def get_skills_dir() -> Path:
    config = load_config()
    skills_cfg = config.get("skills", {})
    external = skills_cfg.get("external_dirs", [])
    if external and isinstance(external, list) and len(external) > 0:
        return Path(external[0])
    return AGENT_Z_HOME / "skills"


def get_profile_skills_dir(profile: str = "default") -> Path:
    if profile == "default":
        return AGENT_Z_HOME / "skills"
    return AGENT_Z_HOME / "profiles" / profile / "skills"


def get_current_profile() -> str:
    env_profile = os.environ.get("AGENT_Z_PROFILE")
    if env_profile:
        return env_profile
    profiles_dir = AGENT_Z_HOME / "profiles"
    link = profiles_dir / "current"
    if link.is_symlink():
        return link.resolve().name
    return "default"


def ensure_workspace_dirs():
    for dir_path in [
        AGENT_Z_HOME,
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

    api_key = pconf.get("api_key") or ""
    base_url = pconf.get("base_url") or ""
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
        provider = llm.get("provider", "")
        if provider and provider != "none":
            pconf = config.get("providers", {}).get(provider, {})
            if not pconf.get("api_key"):
                self.warnings.append(
                    f"API key not set for provider: {provider}"
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
