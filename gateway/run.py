#!/usr/bin/env python3
# 🚪 Access - Gateway entry point for messaging platform integrations.
"""
Agent-Z Gateway Runner (minimal portable implementation).

Provides :class:`GatewayRunner` — the main lifecycle controller that:

1. Discovers every registered platform adapter via ``discover_and_register_all_platforms()``.
2. Loads enabled platforms from ``config.yaml`` (the ``gateway.platforms:`` section) and/or
   environment-variable auto-detection (uses each PlatformEntry's ``env_enablement_fn`` +
   required_env presence as a weak enablement signal).
3. Instantiates the adapters, wires their inbound :class:`MessageEvent` callback to our
   :meth:`_handle_message` handler, and calls ``await adapter.connect()``.
4. For every incoming message: resolves a session key → pulls or creates a cached
   :class:`agent.agent.Agent` → streams the agent reply back through the originating
   platform adapter.

This module deliberately targets the **smallest feature surface** required to unblock
"feishu / wecom / weixin actually talk to the agent".  Hermes-tier features
(slash commands, pairing/authz, session SQLite, delivery router, voice TTS, kanban
notifiers, scale-to-zero, restart drain, /update, provider-error redaction filters, …)
are *not* present here — see the ``P1`` migration items on the project roadmap.

Usage::

    # From code
    from gateway.run import GatewayRunner, start_gateway
    runner = GatewayRunner()
    asyncio.run(runner.start())

    # From CLI (use the convenience entry point)
    python -m gateway.run
    agentz gateway run   # or this, after gateway_cli.py is updated
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── Ensure project-relative imports work when run as a script ─────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from common.logging_manager import get_access_logger, set_module_log_level

logger = get_access_logger("run")
# The gateway daemon can run for weeks; gate transient platform-load warnings
# at DEBUG so the first human-readable line is "Starting Agent-Z Gateway".
set_module_log_level("gateway.platforms", logging.INFO)


# ── Cache tuning for per-session Agent instances ──────────────────────
_AGENT_CACHE_MAX_SIZE = 128
_AGENT_CACHE_IDLE_TTL_SECS = 3600.0
_PLATFORM_CONNECT_TIMEOUT_SECS = 30.0


# ─────────────────────────────────────────────────────────────────────
# Public helpers
# ─────────────────────────────────────────────────────────────────────

def build_session_key_safe(source: Any) -> str:
    """Thin wrapper around :func:`gateway.session.build_session_key`.

    Never raises — falls back to a string repr so a single malformed event
    can never take down the event loop.
    """
    try:
        from gateway.session import build_session_key

        return build_session_key(source)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("build_session_key failed (%s); falling back to repr", exc)
        return f"anon:{repr(source)}"


def _resolve_platform_enum(name: str) -> Any:
    """Resolve a platform slug ("feishu", "telegram") into a Platform enum member.

    Preference order:
    1. ``Platform(name)`` — matches the ``value`` attribute (canonical for Agent-Z).
    2. ``Platform[name.upper()]`` — falls back to the enum *member name* (used by
       some legacy YAMLs spelling ``feishu`` as ``FEISHU``).
    3. ``None`` — when the string is genuinely unknown.  The caller skips the
       platform rather than crashing the gateway.
    """
    from gateway.session import Platform

    slug = str(name or "").strip().lower()
    if not slug:
        return None
    for member in Platform:
        if member.value == slug:
            return member
    # Fallback: check enum member name (case-insensitive)
    for member in Platform:
        if member.name.lower() == slug:
            return member
    return None


# ─────────────────────────────────────────────────────────────────────
# GatewayRunner
# ─────────────────────────────────────────────────────────────────────

@dataclass
class _AgentCacheSlot:
    agent: Any
    config_signature: str
    last_used_ts: float


# Sentinel used to distinguish "caller did not pass pairing_store" from
# "caller explicitly passed None (disable PairingStore)".
_PAIRING_STORE_UNSET: Any = object()


class GatewayRunner:
    """Minimal gateway lifecycle controller.

    Public surface:

    * :meth:`start` — connect every enabled adapter and block until shutdown.
    * :meth:`stop` — gracefully disconnect every adapter and drain background tasks.
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        *,
        agent_factory=None,
        pairing_store: Any = _PAIRING_STORE_UNSET,
    ) -> None:
        # ── 1. Platform discovery (idempotent) ─────────────────────────
        from gateway.platforms import ensure_discovered, platform_registry

        ensure_discovered()
        self._registry = platform_registry

        # ── 2. Load / normalise gateway config ────────────────────────
        self.config: Dict[str, Any] = config if config is not None else {}
        if not self.config:
            try:
                from common.config import load_config

                self.config = load_config(use_cache=True) or {}
            except Exception as exc:
                logger.warning("load_config() failed, using empty gateway config: %s", exc)
                self.config = {}
        self._gateway_cfg: Dict[str, Any] = self.config.get("gateway") or {}

        self._platforms_cfg: Dict[str, Any] = self._gateway_cfg.get("platforms") or {}
        if not isinstance(self._platforms_cfg, dict):
            self._platforms_cfg = {}

        # Session storage directory — only used to pass a path into adapters that
        # want a session_store binding.  *This* runner does not open an SQLite DB
        # here; the P1 SessionStore migration activates it later.
        from gateway.platforms._hermes_stubs import get_hermes_home

        self._sessions_dir: Path = Path(get_hermes_home()) / "gateway_sessions"
        self._sessions_dir.mkdir(parents=True, exist_ok=True)

        # ── 3. Per-session Agent LRU cache ────────────────────────────
        self._agent_cache: "OrderedDict[str, _AgentCacheSlot]" = OrderedDict()
        self._agent_cache_lock: Any = None
        try:
            import threading as _t

            self._agent_cache_lock = _t.Lock()
        except Exception:  # pragma: no cover - threading is always available
            self._agent_cache_lock = None

        # Agent constructor override point — tests inject fake Agents here.
        # ``None`` → use the real :class:`agent.agent.Agent` + :func:`create_agent_from_config`.
        self._agent_factory = agent_factory

        # ── 4. Adapter bookkeeping ────────────────────────────────────
        self.adapters: Dict[Any, Any] = {}  # Platform -> BasePlatformAdapter
        # Reverse lookup so _handle_message can find the originating adapter from
        # a MessageEvent.source.platform value (adapters are few, O(n) scan is fine).
        self._adapter_by_platform_slug: Dict[str, Any] = {}

        self._running: bool = False
        self._shutdown_event: Optional[asyncio.Event] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._background_tasks: set = set()

        # ── 5. P1: pairing + authz ------------------------------------
        # PairingStore is the authorization backstop: when an allowlist env var
        # isn't configured, the gateway falls back to "code-based approval".
        # Three call-site shapes:
        #   - omitted (default sentinel)   → auto-install default PairingStore
        #   - explicitly passed a store    → use it as-is
        #   - explicitly passed None      → disable PairingStore entirely
        if pairing_store is _PAIRING_STORE_UNSET:
            try:
                from gateway.pairing import get_default_pairing_store
                self.pairing_store = get_default_pairing_store()
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("PairingStore init failed, authz will be open-gateway only: %s", exc)
                self.pairing_store = None
        else:
            self.pairing_store = pairing_store  # can be None to intentionally disable
        self.session_store: Optional[Any] = None  # P1 SQLite-backed gateway session store
        self.hooks: Optional[Any] = None  # Reserved for plugin-style inbound/outbound hooks

    # ── Config resolution --------------------------------------------------

    def _iter_enabled_platforms(self) -> List[Tuple[str, Dict[str, Any]]]:
        """Return a flat list of ``(slug, extra_kwargs)`` for every *enabled* platform.

        Enablement rules (first match wins):
        1. Explicit ``gateway.platforms.<slug>: {enabled: true, ...}`` in config.yaml.
        2. :class:`PlatformEntry.env_enablement_fn` returns a non-empty extra dict
           (means the env vars for the platform are present).
        3. :class:`PlatformEntry.required_env` — every listed env var is set and
           non-empty (cheap heuristic so ``TELEGRAM_BOT_TOKEN=xxx agentz gateway run``
           does the right thing *without* writing a config file).
        """
        results: List[Tuple[str, Dict[str, Any]]] = []
        seen: set = set()

        # Pass 1 — explicit YAML entries
        for slug, entry in self._platforms_cfg.items():
            if slug in seen:
                continue
            if entry is None:
                entry = {}
            if not isinstance(entry, dict):
                # Allow ``gateway.platforms.feishu: true`` as a shorthand
                if entry is True:
                    entry = {}
                else:
                    logger.warning("gateway.platforms.%s is not a dict; skipping", slug)
                    continue
            enabled = entry.pop("enabled", True)
            if not enabled:
                continue
            seen.add(slug)
            results.append((slug, dict(entry)))

        # Pass 2 — env-driven auto-enablement for any PlatformEntry not yet seen
        for pe in self._registry.all_entries():
            if pe.name in seen:
                continue
            extra: Optional[Dict[str, Any]] = None
            if callable(pe.env_enablement_fn):
                try:
                    extra = pe.env_enablement_fn() or None
                except Exception as exc:
                    logger.debug("env_enablement_fn for %s failed: %s", pe.name, exc)
            if extra:
                seen.add(pe.name)
                results.append((pe.name, dict(extra)))
                continue
            # Fallback: required_env heuristic
            req_env = list(pe.required_env or [])
            if req_env and all(os.getenv(v, "").strip() for v in req_env):
                seen.add(pe.name)
                results.append((pe.name, {}))
        return results

    def _materialise_platform_configs(self) -> Dict[Any, Any]:
        """Translate ``_iter_enabled_platforms()`` → ``{Platform: PlatformConfig}``."""
        from gateway.config import PlatformConfig

        out: Dict[Any, Any] = {}
        for slug, extra in self._iter_enabled_platforms():
            platform_enum = _resolve_platform_enum(slug)
            if platform_enum is None:
                logger.warning(
                    "Skipping unknown platform %r — not in the Platform enum. "
                    "Add it to gateway/session.py first.",
                    slug,
                )
                continue
            out[platform_enum] = PlatformConfig(
                platform=platform_enum,
                enabled=True,
                extra=dict(extra or {}),
            )
        return out

    # ── Agent cache --------------------------------------------------------

    def _agent_config_signature(self) -> str:
        """Hash the current LLM-related config so a cache miss rebuilds the Agent.

        This is intentionally coarse.  Changes to the top-level ``model:`` pointer,
        the provider list, or the ``auxiliary:`` section invalidate the cache.
        """
        try:
            llm_cfg = (
                self.config.get("model") or self.config.get("llm") or {}
            )
            provider_list = self.config.get("providers") or {}
            aux_cfg = self.config.get("auxiliary") or {}
        except Exception:
            return ""
        raw = f"{llm_cfg!r}|{provider_list!r}|{aux_cfg!r}"
        import hashlib

        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]

    def _enforce_agent_cache_cap(self) -> None:
        """Pop LRU entries until we fit under the max-size cap and idle TTL."""
        if self._agent_cache_lock is not None:
            self._agent_cache_lock.acquire()
        try:
            now = time.time()
            # 1. TTL pass
            stale_keys = [
                k
                for k, v in self._agent_cache.items()
                if (now - v.last_used_ts) > _AGENT_CACHE_IDLE_TTL_SECS
            ]
            for k in stale_keys:
                self._agent_cache.pop(k, None)
            # 2. Size pass (OrderedDict is LRU-ordered; popitem(last=False) = oldest)
            while len(self._agent_cache) > _AGENT_CACHE_MAX_SIZE:
                self._agent_cache.popitem(last=False)
        finally:
            if self._agent_cache_lock is not None:
                self._agent_cache_lock.release()

    def _create_agent_for_session(self, session_key: str) -> Optional[Any]:
        """Build a brand-new Agent for ``session_key``.

        Uses the injected ``_agent_factory`` first (unit tests).  Otherwise
        the real :func:`create_agent_from_config` and, if that returns None
        because LLM credentials are missing, falls back to a manually wired
        :class:`agent.agent.Agent` with the resolved provider.
        """
        if self._agent_factory is not None:
            try:
                return self._agent_factory(session_key)
            except Exception as exc:
                logger.error("injected agent_factory failed: %s", exc, exc_info=True)
                return None

        try:
            from agent.agent import Agent, create_agent_from_config

            agent = create_agent_from_config()
            if agent is not None:
                return agent
        except Exception as exc:
            logger.warning(
                "create_agent_from_config failed (session=%s): %s",
                session_key,
                exc,
                exc_info=True,
            )

        # Last-ditch: instantiate directly from the provider env bridge.
        # Some deployments only export env vars (AGENTZ_LLM_PROVIDER / _API_KEY / …)
        # without a config.yaml on disk.
        try:
            from common.config import (
                get_settings,
                resolve_llm_credentials,
            )
            from agent.llm.factory import LLMFactory
            from agent.agent import Agent

            settings = get_settings()
            provider = (
                os.getenv("AGENTZ_LLM_PROVIDER")
                or os.getenv("LLM_PROVIDER")
                or getattr(settings, "llm_provider", None)
                or None
            )
            if provider:
                try:
                    api_key, base_url, model, _ = resolve_llm_credentials(
                        provider, self.config
                    )
                except Exception:
                    api_key = os.getenv("AGENTZ_LLM_API_KEY") or os.getenv(
                        "LLM_API_KEY", ""
                    )
                    base_url = os.getenv("AGENTZ_LLM_BASE_URL") or os.getenv(
                        "LLM_BASE_URL", ""
                    )
                    model = os.getenv("AGENTZ_LLM_MODEL") or os.getenv("LLM_MODEL", "")
                if provider and model and api_key:
                    llm_provider = LLMFactory.create(
                        provider=provider,
                        api_key=api_key,
                        model=model,
                        base_url=base_url,
                    )
                    return Agent(
                        llm_provider=llm_provider,
                        enable_session=False,  # gateway uses its own session keys
                        debug_logs=False,
                    )
        except Exception as exc:
            logger.error(
                "env-only agent construction failed (session=%s): %s",
                session_key,
                exc,
                exc_info=True,
            )
        return None

    def _get_or_create_agent_for_session(self, session_key: str) -> Optional[Any]:
        """Cache hit → bump LRU.  Cache miss → construct and insert."""
        signature = self._agent_config_signature()
        if self._agent_cache_lock is not None:
            self._agent_cache_lock.acquire()
        try:
            slot = self._agent_cache.get(session_key)
            if slot is not None and slot.config_signature == signature:
                slot.last_used_ts = time.time()
                self._agent_cache.move_to_end(session_key)
                return slot.agent
        finally:
            if self._agent_cache_lock is not None:
                self._agent_cache_lock.release()

        # Cache miss — construct outside the lock to avoid serialising LLM-init I/O
        agent = self._create_agent_for_session(session_key)
        if agent is None:
            return None
        if self._agent_cache_lock is not None:
            self._agent_cache_lock.acquire()
        try:
            self._agent_cache[session_key] = _AgentCacheSlot(
                agent=agent,
                config_signature=signature,
                last_used_ts=time.time(),
            )
        finally:
            if self._agent_cache_lock is not None:
                self._agent_cache_lock.release()
        # Opportunistic prune *after* insertion so another task's get-or-create
        # racing with us does not silently grow the set past the cap.
        self._enforce_agent_cache_cap()
        return agent

    # ── Message handling ---------------------------------------------------

    @staticmethod
    def _resolve_platform_slug(source: Any) -> Optional[str]:
        """Return the lower-cased platform slug string from any ``source`` object.

        Accepts either a ``Platform`` enum (reads ``.value``) or a plain string.
        Returns ``None`` for anything else — callers are expected to treat
        ``None`` as "cannot gate this event; drop rather than crash".
        """
        platform_enum = getattr(source, "platform", None) if source is not None else None
        slug_val = getattr(platform_enum, "value", None)
        if isinstance(slug_val, str) and slug_val.strip():
            return slug_val.strip().lower()
        if isinstance(platform_enum, str) and platform_enum.strip():
            return platform_enum.strip().lower()
        return None

    @staticmethod
    def _resolve_sender_id(source: Any) -> Optional[str]:
        """Best-effort ``sender_id`` extraction; used for allowlist / pairing lookups."""
        if source is None:
            return None
        for attr in ("sender_id", "user_id", "from_user", "from_id"):
            v = getattr(source, attr, None)
            if isinstance(v, str) and v.strip():
                return v.strip()
            if isinstance(v, int):
                return str(v)
        return None

    def _is_user_authorized(self, source: Any) -> bool:
        """Decide whether an inbound event's sender is allowed to use the agent.

        Authorization union (first TRUE wins):
          1. ``<PLATFORM>_ALLOW_ALL_USERS=true/1/yes`` → open-gateway mode for this platform.
          2. Sender ID present in ``<PLATFORM>_ALLOWED_USERS`` env allowlist (comma-separated).
          3. Sender ID present in the PairingStore's approved list for the platform.
          4. Platform unknown OR PairingStore unavailable → TRUE (fail-open; a misconfigured
             PairingStore installation should not silently lock out every user).
        """
        slug = self._resolve_platform_slug(source)
        if not slug:
            return True
        sender_id = self._resolve_sender_id(source)

        # 1. Allow-all env override.
        entry = self._registry.get(slug) if self._registry is not None else None
        allow_all_env: Optional[str] = None
        allowed_users_env: Optional[str] = None
        if entry is not None:
            allow_all_env = getattr(entry, "allow_all_env", None)
            allowed_users_env = getattr(entry, "allowed_users_env", None)
        if allow_all_env:
            val = os.getenv(allow_all_env, "").strip().lower()
            if val in {"1", "true", "yes", "on", "*"}:
                return True

        # 2. Allowlist env (comma-separated user IDs).
        if sender_id and allowed_users_env:
            raw = os.getenv(allowed_users_env, "").strip()
            if raw:
                ids = [u.strip() for u in raw.split(",") if u.strip()]
                if "*" in ids or sender_id in ids:
                    return True

        # 3. PairingStore approved list.
        if sender_id and self.pairing_store is not None:
            try:
                if self.pairing_store.is_approved(slug, sender_id):
                    return True
            except Exception as exc:  # noqa: BLE001 — documented fail-open below
                logger.warning(
                    "pairing_store.is_approved(%s, %s) raised %s; treating as authorized",
                    slug,
                    sender_id,
                    type(exc).__name__,
                )

        # 4. Fail-open when we genuinely have no way to authorize (e.g. no env allowlist
        # and no PairingStore).  Operators can opt into strict mode by setting
        # AGENTZ_GATEWAY_STRICT_AUTHZ=1, in which case this becomes False.
        strict = os.getenv("AGENTZ_GATEWAY_STRICT_AUTHZ", "").strip().lower() in {"1", "true", "yes", "on"}
        if strict:
            return False
        # If there is *no* way to deny (neither env allowlist nor PairingStore can
        # reject), then stay open.  If there IS a PairingStore or allowlist env
        # configured but the sender didn't match any rule, deny so pairing kicks in.
        has_any_authz_signal = bool(
            (allowed_users_env and os.getenv(allowed_users_env, "").strip())
            or self.pairing_store is not None
            or (allow_all_env and os.getenv(allow_all_env, "").strip())
        )
        if has_any_authz_signal:
            return False
        return True

    def _build_pairing_prompt(self, source: Any, sender_name: str = "") -> str:
        """For an unauthorized sender: issue/reuse a pending pairing code and prompt."""
        slug = self._resolve_platform_slug(source) or "unknown"
        sender_id = self._resolve_sender_id(source) or "anon"
        code: Optional[str] = None
        if self.pairing_store is not None:
            try:
                code = self.pairing_store.generate_code(slug, sender_id, sender_name)
            except Exception as exc:
                logger.warning("pairing_store.generate_code(%s, %s) failed: %s", slug, sender_id, exc)
        if code:
            lines = [
                "🔒 您尚未通过授权。请发送此配对码给机器人管理员审批：",
                f"       配对码：{code}",
                "       有效期：1 小时",
                "管理员通过后，您可以直接继续对话。",
            ]
            return "\n".join(lines)
        # No code available (rate-limit / platform lockout / no pairing store):
        return (
            "🔒 当前账号未授权。请联系机器人管理员在允许名单中添加您的用户 ID，"
            "或稍后再试以获取新的配对码（如已达到请求速率上限，请等待 10 分钟）。"
        )

    def _adapter_for_event(self, event: Any) -> Optional[Any]:
        """Given a :class:`MessageEvent`, find the adapter it originated from."""
        source = getattr(event, "source", None)
        platform_enum = getattr(source, "platform", None) if source is not None else None
        slug: Optional[str] = getattr(platform_enum, "value", None)
        if not slug:
            return None
        return self._adapter_by_platform_slug.get(str(slug))

    async def _handle_message(self, event: Any) -> None:
        """Core inbound path: MessageEvent → Agent → platform reply.

        Designed to never raise unhandled exceptions.  A failure talking to
        one user must not crash the whole gateway process.
        """
        if event is None:
            return
        text = (getattr(event, "text", None) or "").strip()
        if not text:
            logger.debug("Dropping empty MessageEvent")
            return

        source = getattr(event, "source", None)
        session_key = build_session_key_safe(source)
        adapter = self._adapter_for_event(event)
        if adapter is None:
            logger.warning(
                "Could not resolve originating adapter for session %s; "
                "event will be dropped.",
                session_key,
            )
            return

        chat_id = getattr(source, "chat_id", None) if source is not None else None
        if not chat_id:
            logger.warning("MessageEvent for %s has no chat_id; skipping reply", session_key)
            return

        # ── Authorization (pairing / allowlist / open-gateway) ────────
        if not self._is_user_authorized(source):
            sender_name = ""
            try:
                sender_name = str(getattr(source, "sender_name", "") or getattr(event, "sender_name", "")).strip()
            except Exception:
                sender_name = ""
            prompt = self._build_pairing_prompt(source, sender_name=sender_name)
            await self._safe_send(
                adapter,
                chat_id,
                prompt,
                reply_to=getattr(event, "message_id", None),
            )
            return

        # ── Resolve agent ──────────────────────────────────────────────
        agent = self._get_or_create_agent_for_session(session_key)
        if agent is None:
            await self._safe_send(
                adapter,
                chat_id,
                "⚠️ Agent not configured — LLM provider credentials are missing. "
                "Set them via config.yaml or the Settings screen, then restart the gateway.",
                reply_to=getattr(event, "message_id", None),
            )
            return

        # ── Show typing indicator (best-effort) ────────────────────────
        try:
            typing_fn = getattr(adapter, "send_typing", None)
            if callable(typing_fn):
                await typing_fn(chat_id)
        except Exception:  # pragma: no cover - platform-side
            pass

        # ── Call agent.chat (streaming) ────────────────────────────────
        chunks: List[str] = []
        last_stream_edit_ts: float = 0.0
        stream_message_id: Optional[str] = None
        min_edit_interval: float = float(
            os.getenv("AGENTZ_GATEWAY_STREAM_EDIT_INTERVAL", "1.0")
        )

        def _stream_chunk(delta: str) -> None:
            nonlocal last_stream_edit_ts, stream_message_id
            if not delta:
                return
            chunks.append(delta)
            now = time.time()
            # We do not *edit* the adapter message from inside the callback because
            # the callback runs inside agent._setup_default_stream()'s thread pool;
            # instead we simply accumulate and, when there is a configured stream
            # consumer in common/streaming, it handles edit timing.  For this
            # minimal runner we just rely on the final send() below.
            #
            # If the adapter exposes an async-friendly edit_message and the user
            # explicitly enables AGENTZ_GATEWAY_EDIT_STREAM=true, we schedule a
            # best-effort coalesced edit via call_soon_threadsafe.
            if (
                os.getenv("AGENTZ_GATEWAY_EDIT_STREAM", "").strip().lower()
                in ("1", "true", "yes", "on")
                and self._loop is not None
                and (now - last_stream_edit_ts) >= min_edit_interval
            ):
                last_stream_edit_ts = now
                full_so_far = "".join(chunks)
                msg_id_ref = {"id": stream_message_id}

                async def _do_edit(content: str, mid_ref: dict) -> None:
                    nonlocal stream_message_id
                    try:
                        if mid_ref.get("id"):
                            await adapter.edit_message(
                                chat_id, mid_ref["id"], content
                            )
                        else:
                            r = await adapter.send(chat_id, content)
                            if getattr(r, "success", False) and getattr(
                                r, "message_id", None
                            ):
                                mid_ref["id"] = r.message_id
                                stream_message_id = r.message_id
                    except Exception:
                        pass

                asyncio.run_coroutine_threadsafe(
                    _do_edit(full_so_far, msg_id_ref), self._loop
                )

        try:
            response = await agent.chat(
                text,
                enable_stream=True,
                stream_callback=_stream_chunk,
            )
            reply_text: str = (
                getattr(response, "content", None)
                if response is not None
                else None
            ) or "".join(chunks)
            if not reply_text.strip():
                reply_text = "(no response)"
        except Exception as exc:
            logger.error(
                "Agent.chat failed for session %s: %s",
                session_key,
                exc,
                exc_info=True,
            )
            reply_text = (
                "⚠️ Something went wrong while generating a reply. "
                "Please try again in a moment; the gateway logs have the details."
            )

        # ── Send final reply (or edit the streamed one if applicable) ──
        if (
            stream_message_id
            and getattr(adapter, "edit_message", None) is not None
        ):
            try:
                r = await adapter.edit_message(
                    chat_id, stream_message_id, reply_text, finalize=True
                )
                if getattr(r, "success", False):
                    return
            except Exception as exc:  # pragma: no cover
                logger.debug(
                    "final edit_message failed for %s: %s; falling back to send",
                    session_key,
                    exc,
                )
        await self._safe_send(
            adapter,
            chat_id,
            reply_text,
            reply_to=getattr(event, "message_id", None),
        )

    @staticmethod
    async def _safe_send(adapter: Any, chat_id: str, content: str, **kwargs) -> None:
        """Send a reply through the platform adapter — never raises.

        Tries the canonical ``adapter.send()`` first (BasePlatformAdapter API),
        then falls back to ``send_message`` / ``send_text`` aliases used by
        some hand-rolled adapters and test doubles.  This lets the runner work
        with a broader adapter surface without paying a per-message runtime
        import cost.
        """
        if not content:
            return
        last_exc: Optional[BaseException] = None
        for method_name in ("send", "send_message", "send_text"):
            fn = getattr(adapter, method_name, None)
            if not callable(fn):
                continue
            try:
                result = await fn(chat_id, content, **kwargs)
                # If the adapter returns a SendResult with success=False, still
                # log something so operators can spot platform errors.
                if result is not None and getattr(result, "success", True) is False:
                    logger.warning(
                        "%s.%s reported non-success for chat=%s: %s",
                        type(adapter).__name__,
                        method_name,
                        chat_id,
                        getattr(result, "error", None),
                    )
                return
            except Exception as exc:  # noqa: BLE001 — we surface last_exc after fallback chain
                last_exc = exc
        # If we reach here *all* attempts failed (or no method existed).
        plat_label = getattr(adapter, "platform", None)
        if plat_label is None:
            plat_label = type(adapter).__name__
        if last_exc is None:
            logger.error(
                "No usable send method on adapter %s (chat=%s). "
                "Expected send(chat_id, content, **kwargs) or send_message/send_text.",
                plat_label,
                chat_id,
            )
        else:
            logger.error(
                "send failed on adapter %s (chat=%s): %s",
                plat_label,
                chat_id,
                last_exc,
                exc_info=True,
            )

    # ── Lifecycle: start / stop -------------------------------------------

    async def _connect_adapter_with_timeout(
        self, adapter: Any, platform_enum: Any
    ) -> bool:
        try:
            coro = adapter.connect()
            return bool(
                await asyncio.wait_for(
                    coro, timeout=_PLATFORM_CONNECT_TIMEOUT_SECS
                )
            )
        except asyncio.TimeoutError:
            logger.error(
                "Timed out after %ss connecting to %s",
                _PLATFORM_CONNECT_TIMEOUT_SECS,
                getattr(platform_enum, "value", str(platform_enum)),
            )
            return False
        except Exception as exc:
            logger.error(
                "connect() failed for %s: %s",
                getattr(platform_enum, "value", str(platform_enum)),
                exc,
                exc_info=True,
            )
            return False

    async def start(self) -> bool:
        """Start every configured platform adapter and block until shutdown.

        Returns True when the gateway started cleanly and at least one adapter
        came up successfully; False otherwise.
        """
        logger.info("Starting Agent-Z Gateway (minimal runner)...")
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = asyncio.get_event_loop_policy().get_event_loop()

        self._shutdown_event = asyncio.Event()
        # Loop-level safety net so a transient Telegram/Signal network error on
        # an unrelated task never takes out the gateway process (#31066 class).
        self._loop.set_exception_handler(_gateway_loop_exception_handler)

        platform_configs = self._materialise_platform_configs()
        if not platform_configs:
            installed = sorted(e.name for e in self._registry.all_entries())
            logger.warning(
                "No platforms were enabled.  Either add entries under "
                "`gateway.platforms.<name>:` in config.yaml, or export the "
                "corresponding env vars (e.g. TELEGRAM_BOT_TOKEN). "
                "Installed/known platforms: %s",
                installed,
            )

        connected_count = 0
        for platform_enum, pconfig in platform_configs.items():
            slug = getattr(platform_enum, "value", str(platform_enum))
            adapter = self._registry.create_adapter(slug, pconfig)
            if adapter is None:
                logger.warning(
                    "create_adapter returned None for %s — check that its Python "
                    "dependencies are installed (pip install …) and that the "
                    "configured credentials pass validate_config().",
                    slug,
                )
                continue
            # Wire lifecycle + session hooks
            try:
                adapter.set_message_handler(self._handle_message)
            except Exception as exc:
                logger.debug(
                    "set_message_handler not accepted by %s: %s", slug, exc
                )
            for setter_name, setter_value in (
                ("set_session_store", getattr(self, "session_store", None)),
            ):
                setter = getattr(adapter, setter_name, None)
                if callable(setter) and setter_value is not None:
                    try:
                        setter(setter_value)
                    except Exception:
                        pass
            logger.info("Connecting to %s...", slug)
            ok = await self._connect_adapter_with_timeout(adapter, platform_enum)
            if ok:
                self.adapters[platform_enum] = adapter
                self._adapter_by_platform_slug[slug] = adapter
                connected_count += 1
                logger.info("  ✓ %s connected", slug)
            else:
                logger.warning("  ✗ %s failed to connect", slug)

        if not self.adapters:
            logger.error(
                "Gateway exiting — no platform adapters were able to connect."
            )
            return False

        self._running = True
        logger.info(
            "Gateway is UP — %d/%d adapter(s) connected. "
            "Press Ctrl+C (or send SIGTERM) to shut down.",
            connected_count,
            len(platform_configs),
        )

        # ── Register signal handlers for clean shutdown ────────────────
        def _signal_handler() -> None:
            if not self._shutdown_event.is_set():
                logger.info("Shutdown signal received — draining...")
                self._shutdown_event.set()

        try:
            self._loop.add_signal_handler(signal.SIGINT, _signal_handler)
            self._loop.add_signal_handler(signal.SIGTERM, _signal_handler)
        except (NotImplementedError, AttributeError, RuntimeError):
            # Windows Proactor loop / embedded loops don't support add_signal_handler
            pass

        # ── Idle watcher (cache + health keepalive) ────────────────────
        async def _idle_watcher() -> None:
            while self._running:
                try:
                    await asyncio.sleep(60.0)
                    self._enforce_agent_cache_cap()
                except asyncio.CancelledError:
                    return
                except Exception as exc:  # pragma: no cover
                    logger.debug("_idle_watcher tick failed: %s", exc)

        watcher_task = self._loop.create_task(_idle_watcher())
        self._background_tasks.add(watcher_task)
        watcher_task.add_done_callback(self._background_tasks.discard)

        # ── Block until shutdown ───────────────────────────────────────
        try:
            await self._shutdown_event.wait()
        finally:
            await self.stop()
        return True

    async def stop(self) -> None:
        """Disconnect every adapter and drain pending tasks."""
        if not self._running:
            return
        self._running = False
        if self._shutdown_event and not self._shutdown_event.is_set():
            self._shutdown_event.set()
        logger.info("Stopping gateway (%d adapter(s))...", len(self.adapters))
        for platform_enum, adapter in list(self.adapters.items()):
            slug = getattr(platform_enum, "value", str(platform_enum))
            try:
                await asyncio.wait_for(adapter.disconnect(), timeout=5.0)
                logger.info("  ✓ disconnected %s", slug)
            except asyncio.TimeoutError:
                logger.warning("  ✗ %s disconnect timed out", slug)
            except Exception as exc:
                logger.warning("  ✗ %s disconnect failed: %s", slug, exc)
        self.adapters.clear()
        self._adapter_by_platform_slug.clear()
        for t in list(self._background_tasks):
            if not t.done():
                t.cancel()
        if self._background_tasks:
            try:
                await asyncio.gather(*self._background_tasks, return_exceptions=True)
            except Exception:
                pass
        self._background_tasks.clear()


# ── Module-level helpers ------------------------------------------------

def _gateway_loop_exception_handler(
    loop: asyncio.AbstractEventLoop, context: Dict[str, Any]
) -> None:
    """Swallow transient network errors; forward anything else to the default handler.

    Mirrors ``_gateway_loop_exception_handler`` in Hermes' gateway/run.py so a
    single Telegram ``TimedOut`` on a poll task can never kill the gateway.
    """
    from gateway.platforms._hermes_stubs import get_env_value

    exc = context.get("exception")
    if exc is not None and _is_transient_network_error(exc):
        message = context.get("message") or "transient network error"
        task = context.get("future") or context.get("task")
        task_name = ""
        if task is not None:
            try:
                task_name = (
                    task.get_name() if hasattr(task, "get_name") else repr(task)
                )
            except Exception:
                task_name = repr(task)
        logger.warning(
            "Gateway swallowed transient network error from %s: %s: %s",
            task_name or "<unknown task>",
            type(exc).__name__,
            exc,
        )
        return
    loop.default_exception_handler(context)


_TRANSIENT_CLASS_NAMES = frozenset(
    {
        "TimedOut",
        "NetworkError",
        "ReadError",
        "WriteError",
        "ConnectError",
        "ConnectTimeout",
        "ReadTimeout",
        "WriteTimeout",
        "PoolTimeout",
        "RemoteProtocolError",
        "ServerDisconnectedError",
        "ClientConnectorError",
        "ClientOSError",
    }
)


def _is_transient_network_error(exc: BaseException) -> bool:
    seen: set = set()
    cur: Optional[BaseException] = exc
    depth = 0
    while cur is not None and depth < 12:
        ident = id(cur)
        if ident in seen:
            break
        seen.add(ident)
        depth += 1
        if type(cur).__name__ in _TRANSIENT_CLASS_NAMES:
            return True
        cur = cur.__cause__ or cur.__context__
    return False


# Module-level import-time side-effects ------------------------------------------------
#
# Install SIGINT/SIGTERM handler lazily so module-level import in a non-gateway
# context (e.g. TUI importing platform_registry) does not steal signals.
import signal as _signal  # noqa: E402


def start_gateway(config: Optional[Dict[str, Any]] = None) -> bool:
    """Module-level convenience entry point (matches Hermes' function name)."""
    runner = GatewayRunner(config=config)
    return asyncio.run(runner.start())


if __name__ == "__main__":
    # Minimal ``python -m gateway.run`` entry point.  ``agentz gateway run`` is
    # the more ergonomic wrapper added in gateway_cli.py.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    try:
        ok = start_gateway()
    except KeyboardInterrupt:
        ok = True
    sys.exit(0 if ok else 1)
