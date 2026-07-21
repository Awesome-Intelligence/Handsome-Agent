"""
Gateway - Production-ready API Gateway with authentication and rate limiting.
Zero external dependencies.

Heavy HTTP-server dependencies are lazily imported so that lightweight
sub-packages (``gateway.platforms`` used by the channel-gateway runtime)
can be imported without pulling in the full server dependency graph.
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - type hints only
    from .server import GatewayConfig as _GatewayConfig_T
    from .middleware import RateLimiter as _RateLimiter_T
    from .middleware import authenticate as _authenticate_T

__version__ = "1.0.0"
__all__ = [
    "GatewayConfig",
    "run_gateway",
    "RateLimiter",
    "authenticate",
    "rich_sent_store",
]


# ── Lazy server + middleware imports ──────────────────────────────────

def __getattr__(name: str):
    if name in ("GatewayConfig", "run_gateway"):
        from .server import GatewayConfig, run_gateway  # noqa: WPS433 - lazy
        if name == "GatewayConfig":
            return GatewayConfig
        return run_gateway
    if name in ("RateLimiter", "authenticate"):
        from .middleware import RateLimiter, authenticate  # noqa: WPS433
        if name == "RateLimiter":
            return RateLimiter
        return authenticate
    raise AttributeError(f"module 'gateway' has no attribute {name!r}")


class _RichSentStore:
    """Stub rich_sent_store for WhatsApp Cloud reply-to-text resolution.

    In Agent-Z, this is a no-op stub. The WhatsApp Cloud adapter
    uses this to index outbound message text so that when a user replies
    to one of our messages, we can resolve the quoted text. In Agent-Z
    this feature is not yet implemented.
    """

    def record(self, chat_id: str, message_id: str, text: str) -> None:
        pass

    def lookup(self, chat_id: str, message_id: str) -> Optional[str]:
        return None


rich_sent_store = _RichSentStore()
