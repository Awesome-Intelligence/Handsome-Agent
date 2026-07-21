# 🚪 Access - gateway/platforms/__init__.py
"""Platform adapter package with auto-discovery.

Exports:
    discover_and_register_all_platforms() — walks every adapter under this
        package (directory-based *and* single-file based) and invokes their
        ``register()`` / ``register(ctx)`` entry point so the central
        ``platform_registry`` gets populated *without* the caller having to
        hardcode an if/elif chain per platform.

Usage::

    from gateway.platforms import discover_and_register_all_platforms
    discover_and_register_all_platforms()
    # → platform_registry.all_entries() now lists every available adapter.
"""

from __future__ import annotations

import importlib
import inspect
import logging
import sys
from pathlib import Path
from typing import Iterable

from gateway.platforms.platform_registry import (
    PlatformEntry,
    PlatformRegistry,
    platform_registry,
)

__all__ = [
    "PlatformEntry",
    "PlatformRegistry",
    "platform_registry",
    "discover_and_register_all_platforms",
    "ensure_discovered",
]

logger = logging.getLogger(__name__)

# Single-file platform modules shipped at the package root (gateway/platforms/*.py)
# instead of inside their own sub-directory.  These also expose a ``register``
# callable matching the sub-directory convention.
_SINGLE_FILE_PLATFORMS = (
    "weixin",
    "webhook",
    "msgraph_webhook",
    "bluebubbles",
    "signal",
    "whatsapp_cloud",
    "yuanbao",
)

# Modules / directories inside gateway/platforms that are NOT adapters and
# must *not* be imported as platforms during discovery.
_DISCOVERY_BLACKLIST = frozenset(
    {
        "__init__",
        "base",
        "platform_registry",
        "_hermes_stubs",
        "_http_client_limits",
        "helpers",
        "signal_format",
        "whatsapp_common",
        "yuanbao_proto",
        "yuanbao_media",
        "yuanbao_sticker",
    }
)

_discovered = False


def _invoke_register(module, plugin_name: str) -> bool:
    """Call ``module.register(...)`` handling both signatures.

    Two adapter conventions coexist in the ported codebase:

    * **New (Agent-Z native)**: ``def register() -> None`` — used by feishu,
      dingtalk, wecom.  The function internally instantiates a
      ``PlatformEntry`` and calls ``platform_registry.register`` directly.
    * **Legacy (Hermes plugin)**: ``def register(ctx) -> None`` — used by
      telegram, discord, slack, etc.  The function is agnostic about the
      registry; we hand it a :class:`FakePluginContext` that translates
      ``ctx.register_platform(...)`` into the native call.

    Returns True when a ``register`` symbol was actually found and invoked
    without raising, False otherwise.
    """
    register_fn = getattr(module, "register", None)
    if not callable(register_fn):
        return False

    try:
        signature = inspect.signature(register_fn)
    except (TypeError, ValueError):
        signature = None

    if signature is None:
        # Fallback: introspect by positional-parameter count via getfullargspec,
        # which handles C-backed / wrapped callables ``inspect.signature``
        # can't parse.
        try:
            argspec = inspect.getfullargspec(register_fn)
            positional_count = len(argspec.args) - (
                1 if (argspec.args and argspec.args[0] in {"self", "cls"}) else 0
            )
        except TypeError:
            positional_count = 0
        needs_ctx = positional_count >= 1
    else:
        # A register that *only* accepts keyword-only args still counts as
        # "no context needed".
        needs_ctx = any(
            param.kind
            in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
            and param.default is inspect.Parameter.empty
            for param in signature.parameters.values()
        )

    try:
        if needs_ctx:
            from gateway.platforms._hermes_stubs import FakePluginContext

            register_fn(FakePluginContext(plugin_name=plugin_name))
        else:
            register_fn()
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(
            "register() for platform plugin %r failed: %s",
            plugin_name or module.__name__,
            exc,
            exc_info=True,
        )
        return False
    return True


def _iter_subdir_platforms(package_root: Path) -> Iterable[tuple[str, Path]]:
    """Yield ``(module_dotpath, directory)`` for every subdir adapter."""
    package_dotted = __name__  # "gateway.platforms"
    for child in sorted(package_root.iterdir()):
        if not child.is_dir():
            continue
        if (child / "__pycache__").exists() and not (child / "__init__.py").exists():
            continue
        init_file = child / "__init__.py"
        if not init_file.is_file():
            continue
        if child.name.startswith(("_", ".")):
            continue
        if child.name in _DISCOVERY_BLACKLIST:
            continue
        yield f"{package_dotted}.{child.name}", child


def _iter_single_file_platforms(package_root: Path) -> Iterable[str]:
    """Yield dotted module names for single-file root adapter modules."""
    package_dotted = __name__
    for name in _SINGLE_FILE_PLATFORMS:
        candidate = package_root / f"{name}.py"
        if candidate.is_file():
            yield f"{package_dotted}.{name}"


def discover_and_register_all_platforms() -> int:
    """Import every adapter under ``gateway.platforms`` and run ``register``.

    The call is idempotent: subsequent invocations short-circuit (protected by
    ``_discovered``) so callers can safely invoke this from multiple code paths
    without paying the import cost twice.

    Returns the number of platform modules whose ``register`` function was
    actually dispatched (not the count of resulting registry entries, because
    one module can in principle register multiple entries — today none do).
    """
    global _discovered
    if _discovered:
        return 0

    # Before importing any platform adapter, install Hermes-compat shims so
    # that old-style imports like ``hermes_cli.*`` / ``tools.*`` /
    # ``plugins.platforms.telegram`` resolve cleanly.
    from gateway.platforms._hermes_stubs import install_hermes_compat_stubs

    install_hermes_compat_stubs()

    package_root = Path(__file__).resolve().parent
    dispatched = 0

    # ── 1. Sub-directory based adapters (feishu/, telegram/, …) ─────────
    for module_dotted, directory in _iter_subdir_platforms(package_root):
        plugin_name = directory.name
        try:
            module = importlib.import_module(module_dotted)
        except Exception as exc:
            logger.debug(
                "Skipping platform %s: import failed: %s", plugin_name, exc
            )
            continue
        if _invoke_register(module, plugin_name=plugin_name):
            dispatched += 1

    # ── 2. Single-file adapters (weixin.py, webhook.py, …) ─────────────
    for module_dotted in _iter_single_file_platforms(package_root):
        plugin_name = module_dotted.rsplit(".", 1)[-1]
        try:
            module = importlib.import_module(module_dotted)
        except Exception as exc:
            logger.debug(
                "Skipping single-file platform %s: import failed: %s",
                plugin_name,
                exc,
            )
            continue
        if _invoke_register(module, plugin_name=plugin_name):
            dispatched += 1

    _discovered = True
    logger.info(
        "Platform discovery finished: dispatched register() for %d module(s); "
        "registry now contains %d entry(ies).",
        dispatched,
        len(platform_registry.all_entries()),
    )
    return dispatched


def ensure_discovered() -> None:
    """Cheap idempotent alias — callers use this at the top of entry points."""
    if not _discovered:
        discover_and_register_all_platforms()
