# 🚪 Access - gateway/platforms/_http_client_limits.py
"""Shared HTTP client factory for long-lived platform adapters.

Ported from Hermes agent - https://github.com/NousResearch/hermes-agent
"""

from __future__ import annotations

import os

try:
    import httpx
except ImportError:  # pragma: no cover — optional dep
    httpx = None  # type: ignore[assignment]


_DEFAULT_KEEPALIVE_EXPIRY_S = 2.0
_DEFAULT_MAX_KEEPALIVE = 10


def platform_httpx_limits() -> "httpx.Limits | None":
    """Return ``httpx.Limits`` tuned for persistent platform-adapter clients.

    Returns ``None`` when httpx isn't importable, so callers can fall
    back to httpx's built-in default without a hard dependency on this
    helper being reachable.
    """
    if httpx is None:
        return None

    def _env_float(name: str, default: float) -> float:
        raw = os.environ.get(name, "").strip()
        if not raw:
            return default
        try:
            val = float(raw)
        except (TypeError, ValueError):
            return default
        return val if val > 0 else default

    def _env_int(name: str, default: int) -> int:
        raw = os.environ.get(name, "").strip()
        if not raw:
            return default
        try:
            val = int(raw)
        except (TypeError, ValueError):
            return default
        return val if val > 0 else default

    keepalive_expiry = _env_float(
        "HERMES_GATEWAY_HTTPX_KEEPALIVE_EXPIRY", _DEFAULT_KEEPALIVE_EXPIRY_S
    )
    max_keepalive = _env_int(
        "HERMES_GATEWAY_HTTPX_MAX_KEEPALIVE", _DEFAULT_MAX_KEEPALIVE
    )

    return httpx.Limits(
        max_keepalive_connections=max_keepalive,
        keepalive_expiry=keepalive_expiry,
    )
