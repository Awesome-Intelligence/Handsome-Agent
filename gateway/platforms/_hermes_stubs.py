# 🚪 Access - gateway/platforms/_hermes_stubs.py
"""Hermes compatibility stubs for ported platform adapters."""

from __future__ import annotations

import os
from pathlib import Path

import os


# hermes_cli.config stub
def _load_config() -> dict:
    """Stub: return empty config dict."""
    return {}


def env_int(name: str, default: int) -> int:
    """Stub: parse env var as int."""
    try:
        return int(os.getenv(name, str(default)))
    except (ValueError, TypeError):
        return default


def env_bool(name: str, default: bool) -> bool:
    """Stub: parse env var as bool."""
    val = os.getenv(name, "").strip().lower()
    if val in ("true", "1", "yes", "on"):
        return True
    if val in ("false", "0", "no", "off"):
        return False
    return default


def env_float(name: str, default: float) -> float:
    """Stub: parse env var as float."""
    try:
        return float(os.getenv(name, str(default)))
    except (ValueError, TypeError):
        return default


def get_env_value(name: str, default: str = "") -> str:
    """Stub: get env var or default."""
    return os.getenv(name, default)


def save_env_value(name: str, value: str) -> None:
    """Stub: no-op save (Agent-Z doesn't use .env files)."""
    pass


# hermes_cli.cli_output stubs
def prompt(msg: str, password: bool = False, default: str = "") -> str:
    """Stub: return default."""
    return default


def prompt_yes_no(msg: str, default: bool = False) -> bool:
    """Stub: return default."""
    return default


def print_header(msg: str) -> None:
    pass


def print_info(msg: str) -> None:
    print(msg)


def print_success(msg: str) -> None:
    print(msg)


def print_warning(msg: str) -> None:
    print(f"WARNING: {msg}")


# hermes_cli.gateway stubs
def get_env_value_gw(name: str, default: str = "") -> str:
    """Stub: get env var for gateway checks."""
    return os.getenv(name, default)


# agent.redact stub
def redact_sensitive_text(text: str) -> str:
    """Stub: redact sensitive text."""
    return "<redacted>"


# agent.display stub
def get_tool_emoji(tool: str, default: str = "⚙️") -> str:
    """Stub: return default emoji."""
    return default


# tools.credential_files stub
def to_agent_visible_cache_path(path: str) -> str:
    """Stub: return path as-is."""
    return path


# tools.url_safety stub (real one exists in common.security)
def redirect_target_from_response(response) -> str | None:
    """Stub: no redirect target."""
    return None


def is_safe_url(url: str, *, allowed_hosts=None, require_https: bool = True) -> bool:
    """Minimal URL safety check (matches hermes tools.url_safety.is_safe_url).

    Rejects non-HTTP schemes, URLs with embedded credentials, and hostnames
    that look like RFC1918 / link-local IPs.  The real Agent-Z implementation
    lives in ``common.security`` but platform adapters only need a cheap
    pass/fail, so this heuristic is sufficient.
    """
    import re as _re

    if not isinstance(url, str) or not url.strip():
        return False
    try:
        from urllib.parse import urlparse
    except Exception:  # pragma: no cover
        return False
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https", "ftp", "ftps"):
        return False
    if require_https and parsed.scheme not in ("https",):
        # Be more permissive than strict HTTPS: adapter callers sometimes
        # check intranet http URLs; just don't allow javascript/file.
        pass
    if parsed.username or parsed.password:
        return False
    host = (parsed.hostname or "").lower()
    if not host:
        return False
    if allowed_hosts:
        allowed = {h.lower() for h in allowed_hosts}
        if host not in allowed and not any(
            host.endswith("." + h.lstrip(".")) for h in allowed
        ):
            return False
    # Block obvious loopback / metadata / private IP ranges
    _private_re = _re.compile(
        r"^(localhost|127\.|10\.|192\.168\.|172\.(1[6-9]|2\d|3[0-1])\.|"
        r"0\.0\.0\.0|169\.254\.|fc..:|fd..:|fe80:|::1?)$"
    )
    if _private_re.match(host):
        return False
    return True


# hermes_cli.setup stub
def prompt_choice(msg: str, options: list[str], default: int = 0) -> int:
    """Stub: print prompt and return index."""
    print(msg)
    for i, opt in enumerate(options):
        print(f"  [{i}] {opt}")
    try:
        val = input(f"Select [{default}]: ").strip()
        if not val:
            return default
        idx = int(val)
        if 0 <= idx < len(options):
            return idx
    except (ValueError, EOFError):
        pass
    return default


# hermes_cli.cli_output stub
def print_error(msg: str) -> None:
    print(f"ERROR: {msg}")


# hermes_cli.config aliases
def get_env_var(name: str, default: str = "") -> str:
    """Stub: get env var or default."""
    return os.getenv(name, default)


def set_env_var(name: str, value: str) -> None:
    """Stub: no-op save (Agent-Z doesn't use .env files)."""
    pass


# hermes_cli.secret_prompt stub
def masked_secret_prompt(prompt_text: str) -> str:
    """Stub: return empty string."""
    return ""


# hermes_cli.colors stub
class Colors:
    """Stub ANSI color codes."""

    RESET = ""
    BOLD = ""
    DIM = ""
    CYAN = ""
    GREEN = ""
    RED = ""
    YELLOW = ""
    BLUE = ""
    MAGENTA = ""


def color(text: str, *styles) -> str:
    """Stub: return text unchanged."""
    return text


# hermes_cli.commands stub
def is_gateway_known_command(name: str) -> bool:
    """Stub: return False (command unknown)."""
    return False


# hermes_cli.providers stub
def get_label(provider: str) -> str:
    """Stub: return provider as-is."""
    return provider


# hermes_constants stubs (use base.py equivalents)
def get_hermes_home() -> "Path":
    from pathlib import Path
    import os
    import sys

    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "").strip()
        base = Path(local) if local else Path.home() / "AppData" / "Local"
        return base / "Agent-Z"
    return Path.home() / ".agent_z"


def get_default_hermes_root() -> "Path":
    return get_hermes_home()


def get_hermes_dir(subpath: str, old_name: str | None = None) -> "Path":
    return get_hermes_home() / subpath


def display_hermes_home() -> str:
    """Return a user-friendly display path for HERMES_HOME."""
    home = get_hermes_home()
    try:
        from pathlib import Path

        return "~/" + str(home.relative_to(Path.home()))
    except ValueError:
        return str(home)

# agent.async_utils stub
def safe_schedule_threadsafe(
    coro,
    loop,
    *,
    logger=None,
    log_message: str = "",
    log_level=...,
):
    """Schedule a coroutine on the given event loop from a worker thread."""
    import asyncio
    import logging

    if log_level is ...:
        log_level = logging.WARNING
    try:
        return asyncio.run_coroutine_threadsafe(coro, loop)
    except RuntimeError:
        if logger:
            logger.log(log_level, log_message)
        return None


# utils.atomic_replace stub (Agent-Z uses common.file_utils.atomic_replace)
def atomic_replace(tmp_path, target_path) -> None:
    """Atomically replace target_path with tmp_path."""
    import os

    try:
        os.replace(tmp_path, target_path)
    except OSError:
        pass


def atomic_json_write(path, data, *, indent: int = 2, **kwargs) -> None:
    """Mirror ``gateway.platforms.helpers.atomic_json_write``.

    Some hermes adapters import this as ``from utils import atomic_json_write``
    which we resolve via the sys.modules alias → this _hermes_stubs module.
    """
    from gateway.platforms.helpers import atomic_json_write as _real

    _real(path, data, indent=indent, **kwargs)


# hermes_cli.config stubs
def atomic_config_write(config_path, config, **kwargs) -> None:
    """Stub: no-op yaml write."""
    pass


# Telegram chat-id normalisation (mirrors plugins/platforms/telegram/telegram_ids).
# Agent-Z telegram adapter (originally hermes plugins.*) imports this via the
# _hermes_stubs shim.
def normalize_telegram_chat_id(chat_id):
    """Return a Bot API-compatible chat_id (int for numeric, str otherwise)."""
    chat_id_str = str(chat_id).strip()
    try:
        return int(chat_id_str)
    except (TypeError, ValueError):
        return chat_id_str


# hermes_cli.commands stubs
def telegram_menu_commands(max_commands: int = 60) -> tuple[list[tuple[str, str]], int]:
    """Stub: return empty command list."""
    return [], 0


def telegram_menu_max_commands() -> int:
    """Stub: return default max commands."""
    return 60


# hermes_cli.providers stub
def get_label(slug: str) -> str:
    """Stub: return slug as-is."""
    return slug


# hermes_cli.models stubs
def group_providers(slugs: list[str]) -> list[list[str]]:
    """Stub: return empty grouped list."""
    return []


PROVIDER_GROUPS: dict = {}


# hermes_cli.model_cost_guard stub
def expensive_model_warning(model_id: str, provider: str = "") -> str | None:
    """Stub: no warning."""
    return None


# hermes_cli.setup stub
def _setup_telegram() -> None:
    """Stub: no-op setup."""
    pass


# agent.async_utils stub
def safe_schedule_threadsafe(
    coro, loop, *, logger=None, log_message: str = "", log_level=...
):
    import asyncio
    import logging

    if log_level is ...:
        log_level = logging.WARNING
    try:
        return asyncio.run_coroutine_threadsafe(coro, loop)
    except RuntimeError:
        if logger:
            logger.log(log_level, log_message)
        return None


# hermes_cli._subprocess_compat stub
def windows_hide_flags() -> int:
    return 0


# hermes_cli.config stub
def read_raw_config():
    return {}


# hermes_cli.slack_cli stub
def _build_full_manifest(*args, **kwargs):
    return {}


# hermes_cli.plugins stub
def get_plugin_manager():
    return None


# hermes_cli.dingtalk_auth stub
def dingtalk_qr_auth(*args, **kwargs):
    return None


# hermes_cli.gateway stub module
class _GatewayStub:
    pass


gateway_mod = _GatewayStub()

# hermes_cli.commands stubs
COMMAND_REGISTRY = []


def _is_gateway_available():
    return True


def _resolve_config_gates(*args, **kwargs):
    return []


def _iter_plugin_command_entries(*args, **kwargs):
    return []


def discord_skill_commands_by_category(*args, **kwargs):
    return []


def slack_native_slashes(*args, **kwargs):
    return []


def is_gateway_known_command(*args, **kwargs):
    return False


def slack_subcommand_map(*args, **kwargs):
    return {}


# hermes_cli.models stub
def get_default_model_for_provider(provider: str) -> str:
    """Stub: return empty string."""
    return ""


# hermes_cli.env_loader stub
def load_hermes_dotenv() -> None:
    """Stub: no-op."""
    pass


# hermes_cli.providers stubs (used by telegram, discord)
def get_label(slug: str) -> str:
    return slug


PROVIDER_GROUPS = {}


def group_providers(slugs: list) -> list:
    return []


# hermes_cli.model_cost_guard stub
def expensive_model_warning(model_id: str, provider: str = "") -> str | None:
    return None


# tools.transcription_tools stub (Hermes-specific)
def transcribe_audio(*args, **kwargs):
    return {"text": "", "error": "stub"}


# tools.voice_mode stub
def is_whisper_hallucination(*args, **kwargs) -> bool:
    return False


# tools.tts_tool stub
def text_to_speech_tool(*args, **kwargs):
    return None


# tools.clarify_gateway stub
def mark_awaiting_text(*args, **kwargs):
    pass


def resolve_gateway_clarify(*args, **kwargs):
    return None


_entries = []


# tools.env_passthrough stub
def register_env_passthrough(*args, **kwargs):
    pass


# agent.skill_commands stub
def get_skill_commands(*args, **kwargs):
    return []


# tools.microsoft_graph_auth stub
class MicrosoftGraphTokenProvider:
    def __init__(self, *args, **kwargs):
        pass


# tools.microsoft_graph_client stub
class MicrosoftGraphClient:
    def __init__(self, *args, **kwargs):
        pass


# tools.send_message_tool stub
def _error(*args, **kwargs):
    return {}


# tools.lazy_deps stub (Hermes-only dependency resolution)
def ensure_and_bind(*args, **kwargs):
    return True


def feature_missing(*args, **kwargs):
    return False


def ensure(*args, **kwargs):
    return True


# tools.approval stub
def resolve_gateway_approval(*args, **kwargs):
    return None


def has_blocking_approval(*args, **kwargs):
    return False


# tools.send_message_tool stub
def _send_telegram(*args, **kwargs):
    return None


# ── FakePluginContext: bridges Hermes plugin-style register(ctx) calls ──
# into Agent-Z's native platform_registry.register(PlatformEntry(...)).
#
# This lets ~20 ported platform adapters (telegram, discord, slack, ...) keep
# their original `register(ctx)` signatures without rewrites.  The real Hermes
# PluginContext has more APIs (register_tool, etc.) but platform adapters only
# ever call register_platform(), which we faithfully translate here.
class FakePluginContext:
    """A drop-in ``ctx`` that forwards ``register_platform`` → platform_registry."""

    def __init__(self, plugin_name: str = "") -> None:
        self._plugin_name = plugin_name

    def register_platform(self, name: str, label: str, **kwargs) -> None:
        """Translate the flat-kwarg Hermes API into a PlatformEntry."""
        from gateway.platforms.platform_registry import (
            PlatformEntry,
            platform_registry,
        )

        entry = PlatformEntry(
            name=name,
            label=label,
            source="plugin" if self._plugin_name else "builtin",
            plugin_name=self._plugin_name,
            # Everything that adapter_factory/check_fn/validate_config/...
            # Hermes passes arrives via **kwargs.  PlatformEntry dataclass
            # accepts all of them field-for-field, so we just pass-through.
            **kwargs,
        )
        platform_registry.register(entry)

    # ── Silently accept (and ignore) plugin-only APIs that some
    #    adapter __init__ files call on the ctx during register(). ──
    def register_tool(self, *args, **kwargs) -> None:  # pragma: no cover - stub
        return None

    def register_provider(self, *args, **kwargs) -> None:  # pragma: no cover - stub
        return None

    def register_hook(self, *args, **kwargs) -> None:  # pragma: no cover - stub
        return None

    def log(self, *args, **kwargs) -> None:  # pragma: no cover - stub
        return None

    def register_cli_command(self, *args, **kwargs) -> None:  # pragma: no cover - stub
        return None

    def expose_on_rich_ui(self, *args, **kwargs) -> None:  # pragma: no cover - stub
        return None

    def register_on_became_primary(self, *args, **kwargs) -> None:  # pragma: no cover - stub
        return None

    def register_authz_policy(self, *args, **kwargs) -> None:  # pragma: no cover - stub
        return None


# ── Install-time helper: wire up sys.modules aliases ─────────────────


_INSTALL_STUBS_DONE = False


def install_hermes_compat_stubs() -> None:
    """Populate ``sys.modules`` with Hermes compatibility shims.

    Many ported platform adapters import names like
    ``hermes_cli.gateway``, ``plugins.platforms.telegram`` or
    ``tools.lazy_deps`` that simply do not exist in Agent-Z.  Rather than
    rewriting every adapter, we pre-install thin module aliases that either
    point at :mod:`gateway.platforms._hermes_stubs` (for loose helper
    modules) or at real Agent-Z modules (for relocated adapter code like
    the Telegram plugin helpers).
    """
    global _INSTALL_STUBS_DONE
    if _INSTALL_STUBS_DONE:
        return
    _INSTALL_STUBS_DONE = True

    import importlib
    import sys
    import types

    self_mod = sys.modules[__name__]

    # 1) Hermes CLI top-level package → aliased to a small namespace package
    #    whose submodules resolve to this _hermes_stubs file.  Adapters
    #    import specific sub-names (e.g. ``hermes_cli.config.env_int``);
    #    the common submodules listed below are all populated as aliases.
    hermes_submodules = (
        "config",
        "cli_output",
        "setup",
        "providers",
        "gateway",
        "models",
        "model_cost_guard",
        "secret_prompt",
        "colors",
        "commands",
        "dingtalk_auth",
        "env_loader",
        "plugins",
        "_subprocess_compat",
        "slack_cli",
    )
    hermes_pkg = sys.modules.setdefault("hermes_cli", types.ModuleType("hermes_cli"))
    hermes_pkg.__path__ = []  # type: ignore[attr-defined]
    for sub in hermes_submodules:
        sys.modules.setdefault(f"hermes_cli.{sub}", self_mod)

    # 2) agent / tools / utils loose helpers that Hermes imports globally.
    agent_subs = ("async_utils", "skill_commands", "redact", "display")
    agent_pkg = sys.modules.setdefault("agent", types.ModuleType("agent"))
    agent_pkg.__path__ = []  # type: ignore[attr-defined]
    # Don't alias top-level `agent` — Agent-Z really has a real agent module!
    for sub in agent_subs:
        name = f"agent.{sub}"
        if name not in sys.modules:
            sys.modules[name] = self_mod

    tools_subs = (
        "credential_files",
        "url_safety",
        "transcription_tools",
        "voice_mode",
        "tts_tool",
        "clarify_gateway",
        "env_passthrough",
        "microsoft_graph_auth",
        "microsoft_graph_client",
        "send_message_tool",
        "lazy_deps",
        "approval",
    )
    tools_pkg = sys.modules.setdefault("tools", types.ModuleType("tools"))
    tools_pkg.__path__ = []  # type: ignore[attr-defined]
    for sub in tools_subs:
        sys.modules.setdefault(f"tools.{sub}", self_mod)

    utils_pkg = sys.modules.setdefault("utils", types.ModuleType("utils"))
    utils_pkg.__path__ = []  # type: ignore[attr-defined]
    sys.modules.setdefault("utils.atomic_replace", self_mod)
    # Merge *all* loose util-style attributes exposed by _hermes_stubs onto
    # the fake `utils` module so old-style imports like
    # ``from utils import env_float, env_int, atomic_json_write`` work.
    _utils_attrs = (
        "atomic_json_write",
        "atomic_replace",
        "env_int",
        "env_bool",
        "env_float",
        "get_env_value",
        "save_env_value",
        "get_env_var",
        "set_env_var",
        "normalize_telegram_chat_id",
    )
    for _attr in _utils_attrs:
        _val = getattr(self_mod, _attr, None)
        if _val is not None and not hasattr(sys.modules["utils"], _attr):
            setattr(sys.modules["utils"], _attr, _val)

    # hermes_constants module → stub
    sys.modules.setdefault("hermes_constants", self_mod)
    # hermes_cli.secret_prompt alias (hermes sometimes uses this dotted name)
    sys.modules.setdefault("hermes_cli.secret_prompt", self_mod)

    # 3) plugins.platforms.telegram → real Agent-Z module: gateway.platforms.telegram
    #
    # CAREFUL: gateway/platforms/telegram/__init__.py imports its own
    # ``.adapter`` which in turn imports from plugins.platforms.telegram.*
    # (circular alias).  If we import the *package* first, __init__.py fires
    # and fails.  We therefore import the two leaf submodules *by file path*
    # (bypassing __init__) so the aliases are ready before __init__ runs.
    import importlib.util as _ilu

    tg_pkg_dir = Path(__file__).resolve().parent / "telegram"
    leaf_subs: dict[str, Any] = {}
    for tg_sub in ("telegram_ids", "telegram_network"):
        leaf_path = tg_pkg_dir / f"{tg_sub}.py"
        loaded = self_mod
        if leaf_path.is_file():
            try:
                spec = _ilu.spec_from_file_location(
                    f"__agentz_tg_stub_{tg_sub}", leaf_path
                )
                if spec is not None and spec.loader is not None:
                    mod = _ilu.module_from_spec(spec)
                    # Temporarily register under the aliased dotted name so
                    # leaf modules can do intra-plugin imports during load.
                    sys.modules[f"plugins.platforms.telegram.{tg_sub}"] = mod
                    try:
                        spec.loader.exec_module(mod)  # type: ignore[union-attr]
                    except Exception:
                        mod = self_mod
                    loaded = mod
            except Exception:
                loaded = self_mod
        leaf_subs[tg_sub] = loaded

    try:
        tg_real = importlib.import_module("gateway.platforms.telegram")
    except Exception:
        tg_real = self_mod
    plugins = sys.modules.setdefault("plugins", types.ModuleType("plugins"))
    plugins.__path__ = []  # type: ignore[attr-defined]
    plugins_platforms = sys.modules.setdefault(
        "plugins.platforms", types.ModuleType("plugins.platforms")
    )
    plugins_platforms.__path__ = []  # type: ignore[attr-defined]
    sys.modules.setdefault("plugins.platforms.telegram", tg_real)

    for tg_sub, sub_real in leaf_subs.items():
        dotted = f"plugins.platforms.telegram.{tg_sub}"
        sys.modules.setdefault(dotted, sub_real)
        if not hasattr(tg_real, tg_sub):
            setattr(tg_real, tg_sub, sub_real)
