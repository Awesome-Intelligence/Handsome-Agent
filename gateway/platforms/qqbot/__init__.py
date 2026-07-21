"""
QQBot platform package.

Re-exports the main adapter symbols from ``adapter.py`` (the original
``qqbot.py``) so that **all existing import paths remain unchanged**::

    from gateway.platforms.qqbot import QQAdapter          # works
    from gateway.platforms.qqbot import check_qq_requirements  # works

New modules:
    - ``constants`` — shared constants (API URLs, timeouts, message types)
    - ``utils`` — User-Agent builder, config helpers
    - ``crypto`` — AES-256-GCM key generation and decryption
    - ``onboard`` — QR-code scan-to-configure flow
"""

# -- Adapter (original qqbot.py) ------------------------------------------
from .adapter import (  # noqa: F401
    QQAdapter,
    QQCloseError,
    check_qq_requirements,
    _coerce_list,
    _ssrf_redirect_guard,
)

# -- Onboard (QR-code scan-to-configure) -----------------------------------
from .onboard import (  # noqa: F401
    BindStatus,
    build_connect_url,
    qr_register,
)
from .crypto import decrypt_secret, generate_bind_key  # noqa: F401

# -- Utils -----------------------------------------------------------------
from .utils import build_user_agent, get_api_headers, coerce_list  # noqa: F401

# -- Chunked upload --------------------------------------------------------
from .chunked_upload import (  # noqa: F401
    ChunkedUploader,
    UploadDailyLimitExceededError,
    UploadFileTooLargeError,
)

# -- Inline keyboards ------------------------------------------------------
from .keyboards import (  # noqa: F401
    ApprovalRequest,
    ApprovalSender,
    InlineKeyboard,
    InteractionEvent,
    build_approval_keyboard,
    build_approval_text,
    build_update_prompt_keyboard,
    parse_approval_button_data,
    parse_interaction_event,
    parse_update_prompt_button_data,
)

__all__ = [
    # adapter
    "QQAdapter",
    "QQCloseError",
    "check_qq_requirements",
    "_coerce_list",
    "_ssrf_redirect_guard",
    # onboard
    "BindStatus",
    "build_connect_url",
    "qr_register",
    # crypto
    "decrypt_secret",
    "generate_bind_key",
    # utils
    "build_user_agent",
    "get_api_headers",
    "coerce_list",
    # chunked upload
    "ChunkedUploader",
    "UploadDailyLimitExceededError",
    "UploadFileTooLargeError",
    # keyboards
    "ApprovalRequest",
    "ApprovalSender",
    "InlineKeyboard",
    "InteractionEvent",
    "build_approval_keyboard",
    "build_approval_text",
    "build_update_prompt_keyboard",
    "parse_approval_button_data",
    "parse_interaction_event",
    "parse_update_prompt_button_data",
    # gateway registration
    "register",
]


# ---------------------------------------------------------------------------
# Gateway registry integration
# ---------------------------------------------------------------------------

# QQBot uses HTTPX for REST calls and AIOHTTP for gateway webhook servers — most
# of the real traffic goes through the SDK websocket stack.
_AIOHTTP_OK = False
try:
    import aiohttp  # noqa: F401
    _AIOHTTP_OK = True
except Exception:
    _AIOHTTP_OK = False

_HTTPX_OK = False
try:
    import httpx  # noqa: F401
    _HTTPX_OK = True
except Exception:
    _HTTPX_OK = False


def _check_qqbot_runtime() -> bool:
    return _AIOHTTP_OK and _HTTPX_OK and check_qq_requirements()


def _build_qqbot_adapter(config):
    """Construct a QQAdapter from a PlatformConfig."""
    return QQAdapter(config)


def _qqbot_apply_yaml_config(yaml_cfg: dict, env_overrides: dict):
    """Extract QQ-specific ``extra`` fields from config.yaml.

    The top-level key looked up is ``gateway.platforms.qqbot`` (mirroring
    Hermes' ``platforms.qqbot`` layout).  Anything nested under ``extra``
    is forwarded verbatim to the adapter constructor as ``config.extra``.
    """
    platforms_cfg = (yaml_cfg.get("gateway") or {}).get("platforms") or yaml_cfg.get(
        "platforms"
    ) or {}
    qq_cfg = platforms_cfg.get("qqbot") or {}
    extra = dict(qq_cfg.get("extra") or qq_cfg)
    import os

    for k_env, k_cfg in (
        ("QQ_APP_ID", "app_id"),
        ("QQ_CLIENT_SECRET", "client_secret"),
        ("QQ_BOT_TOKEN", "bot_token"),
        ("QQ_SANDBOX", "sandbox"),
    ):
        v_env = os.getenv(k_env)
        if v_env and extra.get(k_cfg) in (None, ""):
            extra[k_cfg] = v_env
    return {"extra": extra} if extra else None


def register() -> None:
    """Register the QQ Bot platform with the Agent-Z gateway registry."""
    from gateway.platforms.platform_registry import PlatformEntry, platform_registry

    platform_registry.register(
        PlatformEntry(
            name="qqbot",
            label="QQ Bot (official Tencent)",
            adapter_factory=_build_qqbot_adapter,
            check_fn=_check_qqbot_runtime,
            required_env=["QQ_APP_ID", "QQ_CLIENT_SECRET"],
            install_hint="pip install aiohttp httpx  "
            "(run ``hermes qqbot setup`` or ``agentz qqbot setup`` for QR onboarding)",
            setup_fn=qr_register,
            apply_yaml_config_fn=_qqbot_apply_yaml_config,
            allowed_users_env="QQ_ALLOWED_USERS",
            allow_all_env="QQ_ALLOW_ALL_USERS",
            cron_deliver_env_var="QQ_HOME_CHANNEL",
            max_message_length=3000,
            emoji="🐧",
            allow_update_command=True,
        )
    )
