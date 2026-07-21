# 🚪 Access - gateway/platforms/platform_registry.py
"""
Platform Adapter Registry

Allows platform adapters (built-in and plugin) to self-register so the gateway
can discover and instantiate them without hardcoded if/elif chains.
Ported from Hermes agent - https://github.com/NousResearch/hermes-agent
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

# Re-export the Platform enum for platform adapters that import it via
# ``from gateway.platforms.platform_registry import Platform`` (hermes compat).
from gateway.session import Platform  # noqa: F401 - re-export

logger = logging.getLogger(__name__)


@dataclass
class PlatformEntry:
    """Metadata and factory for a single platform adapter."""

    name: str
    label: str
    adapter_factory: Callable[[Any], Any]
    check_fn: Callable[[], bool]
    validate_config: Optional[Callable[[Any], bool]] = None
    is_connected: Optional[Callable[[Any], bool]] = None
    required_env: list = field(default_factory=list)
    install_hint: str = ""
    setup_fn: Optional[Callable[[], None]] = None
    source: str = "plugin"
    plugin_name: str = ""
    allowed_users_env: str = ""
    allow_all_env: str = ""
    max_message_length: int = 0
    pii_safe: bool = False
    emoji: str = "🔌"
    allow_update_command: bool = True
    platform_hint: str = ""
    env_enablement_fn: Optional[Callable[[], Optional[dict]]] = None
    apply_yaml_config_fn: Optional[Callable[[dict, dict], Optional[dict]]] = None
    cron_deliver_env_var: str = ""
    standalone_sender_fn: Optional[Callable[..., Awaitable[dict]]] = None


class PlatformRegistry:
    """Central registry of platform adapters."""

    def __init__(self) -> None:
        self._entries: dict[str, PlatformEntry] = {}
        self._deferred: dict[str, Callable[[], None]] = {}

    def register_deferred(self, name: str, loader: Callable[[], None]) -> None:
        if name in self._entries:
            return
        self._deferred[name] = loader

    def _resolve(self, name: str) -> None:
        loader = self._deferred.pop(name, None)
        if loader is None:
            return
        try:
            loader()
        except Exception as e:
            logger.warning(
                "Deferred load of platform '%s' failed: %s",
                name,
                e,
                exc_info=True,
            )

    def _resolve_all(self) -> None:
        if not self._deferred:
            return
        for name in list(self._deferred):
            self._resolve(name)

    def register(self, entry: PlatformEntry) -> None:
        self._deferred.pop(entry.name, None)
        if entry.name in self._entries:
            prev = self._entries[entry.name]
            logger.info(
                "Platform '%s' re-registered (was %s, now %s)",
                entry.name,
                prev.source,
                entry.source,
            )
        self._entries[entry.name] = entry
        logger.debug("Registered platform adapter: %s (%s)", entry.name, entry.source)

    def unregister(self, name: str) -> bool:
        self._deferred.pop(name, None)
        return self._entries.pop(name, None) is not None

    def get(self, name: str) -> Optional[PlatformEntry]:
        if name not in self._entries:
            self._resolve(name)
        return self._entries.get(name)

    def all_entries(self) -> list[PlatformEntry]:
        self._resolve_all()
        return list(self._entries.values())

    def plugin_entries(self) -> list[PlatformEntry]:
        self._resolve_all()
        return [e for e in self._entries.values() if e.source == "plugin"]

    def is_registered(self, name: str) -> bool:
        return name in self._entries or name in self._deferred

    def create_adapter(self, name: str, config: Any) -> Optional[Any]:
        if name not in self._entries:
            self._resolve(name)
        entry = self._entries.get(name)
        if entry is None:
            return None

        if not entry.check_fn():
            hint = f" ({entry.install_hint})" if entry.install_hint else ""
            logger.warning(
                "Platform '%s' requirements not met%s",
                entry.label,
                hint,
            )
            return None

        if entry.validate_config is not None:
            try:
                if not entry.validate_config(config):
                    logger.warning(
                        "Platform '%s' config validation failed",
                        entry.label,
                    )
                    return None
            except Exception as e:
                logger.warning(
                    "Platform '%s' config validation error: %s",
                    entry.label,
                    e,
                )
                return None

        try:
            adapter = entry.adapter_factory(config)
            return adapter
        except Exception as e:
            logger.error(
                "Failed to create adapter for platform '%s': %s",
                entry.label,
                e,
                exc_info=True,
            )
            return None


# Module-level singleton
platform_registry = PlatformRegistry()
