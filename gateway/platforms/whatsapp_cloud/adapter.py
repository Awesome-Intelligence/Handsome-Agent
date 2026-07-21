# 🚪 Access - 🚪 Gateway - whatsapp_cloud/adapter.py
"""
WhatsApp Cloud API adapter — official Meta WhatsApp Business Platform.

This adapter is a *complement* to ``whatsapp.py`` (the Baileys bridge), not
a replacement. The two are independent:

- ``whatsapp.py``      — unofficial Baileys bridge, personal accounts, no
                         public URL needed, account-ban risk.
- ``whatsapp_cloud.py`` (this file) — official Meta Cloud API, Business
                         account required, public webhook URL required,
                         token-based auth.

Both share gating / mention / formatting behavior via ``WhatsAppBehaviorMixin``.

Phase scope (this file evolves across phases):
- Phase 2 — outbound text via Graph API + webhook server with verify-token
            handshake.
- Phase 3 — X-Hub-Signature-256 HMAC verification (raw body, constant-time)
            + wamid replay protection + dispatch via handle_message. Phase 3
            adapter is end-to-end usable for text DMs.
- Phase 4 — media upload + send (image/video/audio/document), inbound
            media download via the Graph media endpoint, voice-note opus
            conversion via ffmpeg with graceful MP3 fallback when ffmpeg
            isn't on PATH. Document text injection for readable types.
- Phase 5 — 24-hour conversation window + template fallback.

Required env vars to enable the adapter:
- WHATSAPP_CLOUD_PHONE_NUMBER_ID  (the Graph URL path component)
- WHATSAPP_CLOUD_ACCESS_TOKEN     (System User permanent token)

Optional / Phase-3+:
- WHATSAPP_CLOUD_APP_ID
- WHATSAPP_CLOUD_APP_SECRET       (HMAC key for X-Hub-Signature-256)
- WHATSAPP_CLOUD_WABA_ID          (analytics / future use)
- WHATSAPP_CLOUD_VERIFY_TOKEN     (hub.verify_token shared secret)
- WHATSAPP_CLOUD_WEBHOOK_HOST     (default 0.0.0.0)
- WHATSAPP_CLOUD_WEBHOOK_PORT     (default 8090)
- WHATSAPP_CLOUD_WEBHOOK_PATH     (default /whatsapp/webhook)
- WHATSAPP_CLOUD_API_VERSION      (default v20.0)
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import mimetypes
import os
import re
import shutil
import uuid
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from aiohttp import web

    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    web = None  # type: ignore[assignment]

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    httpx = None  # type: ignore[assignment]

from gateway.config import PlatformConfig
from gateway.session import Platform
from gateway.platforms.base import (
    BasePlatformAdapter,
    MessageEvent,
    MessageType,
    SendResult,
)
from gateway.platforms.whatsapp_common import WhatsAppBehaviorMixin
from gateway import rich_sent_store

logger = logging.getLogger(__name__)


DEFAULT_API_VERSION = "v20.0"
DEFAULT_WEBHOOK_HOST = "0.0.0.0"
DEFAULT_WEBHOOK_PORT = 8090
DEFAULT_WEBHOOK_PATH = "/whatsapp/webhook"
GRAPH_API_BASE = "https://graph.facebook.com"
WEBHOOK_MAX_BODY_BYTES = 3 * 1024 * 1024
WAMID_DEDUP_CACHE_SIZE = 5000
INTERACTIVE_STATE_CACHE_SIZE = 1000

_MEDIA_SIZE_LIMITS = {
    "image": 5 * 1024 * 1024,
    "video": 16 * 1024 * 1024,
    "audio": 16 * 1024 * 1024,
    "document": 100 * 1024 * 1024,
    "sticker": 100 * 1024,
}

_DEFAULT_MIME = {
    "image": "image/jpeg",
    "video": "video/mp4",
    "audio": "audio/mpeg",
    "document": "application/octet-stream",
    "sticker": "image/webp",
}

_FFMPEG_PATH = shutil.which("ffmpeg")

_WHATSAPP_MIME_EXTENSION_OVERRIDES: Dict[str, str] = {
    "audio/ogg": ".ogg",
    "audio/x-opus+ogg": ".ogg",
    "audio/opus": ".ogg",
    "audio/mp4": ".m4a",
    "audio/x-m4a": ".m4a",
    "image/jpeg": ".jpg",
}


async def _read_limited_request_body(request: Any, max_bytes: int) -> bytes:
    """Read at most ``max_bytes`` from an aiohttp request body."""
    try:
        body = await request.content.readexactly(max_bytes + 1)
    except asyncio.IncompleteReadError as exc:
        body = exc.partial
    if len(body) > max_bytes:
        raise ValueError("payload too large")
    return body


def _ext_for_mime(mime: str) -> Optional[str]:
    """Resolve a mime type to the file extension we want on disk."""
    if not mime:
        return None
    primary = mime.split(";")[0].strip().lower()
    override = _WHATSAPP_MIME_EXTENSION_OVERRIDES.get(primary)
    if override:
        return override
    return mimetypes.guess_extension(primary) or None


def _get_hermes_home() -> Path:
    """Return the platform-native default Agent-Z home path."""
    import os

    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA", "").strip()
        base = Path(local) if local else Path.home() / "AppData" / "Local"
        return base / "Agent-Z"
    return Path.home() / ".agent_z"


_INBOUND_MEDIA_CACHE = Path(_get_hermes_home() / "platforms/whatsapp_cloud/media")


def check_whatsapp_cloud_requirements() -> bool:
    """Return whether transport dependencies are available."""
    return AIOHTTP_AVAILABLE and HTTPX_AVAILABLE


class WhatsAppCloudAdapter(WhatsAppBehaviorMixin, BasePlatformAdapter):
    """WhatsApp Business Cloud API adapter."""

    splits_long_messages = True

    def __init__(self, config: PlatformConfig):
        super().__init__(config, Platform.WHATSAPP_CLOUD)
        extra = config.extra or {}

        self._phone_number_id: str = str(extra.get("phone_number_id", "")).strip()
        self._access_token: str = str(extra.get("access_token", "")).strip()
        self._app_id: str = str(extra.get("app_id", "")).strip()
        self._app_secret: str = str(extra.get("app_secret", "")).strip()
        self._waba_id: str = str(extra.get("waba_id", "")).strip()
        self._verify_token: str = str(extra.get("verify_token", "")).strip()

        self._webhook_host: str = str(extra.get("webhook_host", DEFAULT_WEBHOOK_HOST))
        self._webhook_port: int = int(extra.get("webhook_port", DEFAULT_WEBHOOK_PORT))
        self._webhook_path: str = self._normalize_path(
            extra.get("webhook_path", DEFAULT_WEBHOOK_PATH)
        )
        self._health_path: str = self._normalize_path(
            extra.get("health_path", "/health")
        )

        self._api_version: str = str(extra.get("api_version", DEFAULT_API_VERSION))

        self._reply_prefix: Optional[str] = extra.get("reply_prefix")
        self._allow_from: set[str] = self._normalize_allow_ids(
            self._coerce_allow_list(
                extra.get("allow_from")
                or extra.get("allowFrom")
                or os.getenv("WHATSAPP_CLOUD_ALLOW_FROM")
                or os.getenv("WHATSAPP_CLOUD_ALLOWED_USERS")
            )
        )
        _allow_all_optin = str(
            os.getenv("WHATSAPP_CLOUD_ALLOW_ALL_USERS", "")
        ).strip().lower() in {"true", "1", "yes"}
        _default_dm_policy = (
            "open"
            if _allow_all_optin
            else ("allowlist" if self._allow_from else "open")
        )
        self._dm_policy: str = (
            str(
                extra.get("dm_policy")
                or os.getenv("WHATSAPP_CLOUD_DM_POLICY")
                or os.getenv("WHATSAPP_DM_POLICY")
                or _default_dm_policy
            )
            .strip()
            .lower()
        )
        self._group_policy: str = (
            str(
                extra.get("group_policy")
                or os.getenv("WHATSAPP_CLOUD_GROUP_POLICY")
                or os.getenv("WHATSAPP_GROUP_POLICY", "open")
            )
            .strip()
            .lower()
        )
        self._group_allow_from: set[str] = self._normalize_allow_ids(
            self._coerce_allow_list(
                extra.get("group_allow_from")
                or extra.get("groupAllowFrom")
                or os.getenv("WHATSAPP_CLOUD_GROUP_ALLOW_FROM")
            )
        )
        self._mention_patterns = self._compile_mention_patterns()

        self._seen_wamids: "OrderedDict[str, bool]" = OrderedDict()
        self._duplicate_count: int = 0
        self._accepted_count: int = 0
        self._rejected_signature_count: int = 0

        self._warned_no_ffmpeg: bool = False

        self._last_inbound_wamid_by_chat: "OrderedDict[str, str]" = OrderedDict()

        self._clarify_state: "OrderedDict[str, str]" = OrderedDict()
        self._exec_approval_state: "OrderedDict[str, str]" = OrderedDict()
        self._slash_confirm_state: "OrderedDict[str, str]" = OrderedDict()

        self._runner = None
        self._http_client: Optional["httpx.AsyncClient"] = None

    @staticmethod
    def _normalize_path(path: Any) -> str:
        raw = str(path or "").strip() or "/"
        return raw if raw.startswith("/") else f"/{raw}"

    def _graph_url(self, path: str) -> str:
        if path.startswith("/"):
            path = path[1:]
        return f"{GRAPH_API_BASE}/{self._api_version}/{self._phone_number_id}/{path}"

    @staticmethod
    def _bounded_put(cache: "OrderedDict[str, str]", key: str, value: str) -> None:
        cache[key] = value
        while len(cache) > INTERACTIVE_STATE_CACHE_SIZE:
            cache.popitem(last=False)

    def _effective_reply_prefix(self) -> str:
        if self._reply_prefix is not None:
            return self._reply_prefix.replace("\\n", "\n")
        return ""

    @staticmethod
    def _normalize_allow_ids(ids: set[str]) -> set[str]:
        normalized: set[str] = set()
        for entry in ids:
            bare = entry.split("@", 1)[0]
            digits = re.sub(r"\D", "", bare)
            normalized.add(digits or entry)
        return normalized

    def _is_dm_allowed(self, sender_id: str) -> bool:
        if self._dm_policy == "allowlist":
            bare = re.sub(r"\D", "", str(sender_id).split("@", 1)[0])
            return (bare or sender_id) in self._allow_from
        return super()._is_dm_allowed(sender_id)

    def _open_dm_opted_in(self) -> bool:
        if str(os.getenv("WHATSAPP_CLOUD_ALLOW_ALL_USERS", "")).strip().lower() in {
            "true",
            "1",
            "yes",
        }:
            return True
        return super()._open_dm_opted_in()

    async def connect(self, *, is_reconnect: bool = False) -> bool:
        if not check_whatsapp_cloud_requirements():
            self._set_fatal_error(
                "whatsapp_cloud_deps_missing",
                "aiohttp and httpx are required for whatsapp_cloud",
                retryable=False,
            )
            return False
        if not self._phone_number_id or not self._access_token:
            self._set_fatal_error(
                "whatsapp_cloud_unconfigured",
                "WHATSAPP_CLOUD_PHONE_NUMBER_ID and WHATSAPP_CLOUD_ACCESS_TOKEN are required.",
                retryable=False,
            )
            return False

        self._http_client = httpx.AsyncClient(timeout=30.0)

        app = web.Application(client_max_size=WEBHOOK_MAX_BODY_BYTES)
        app.router.add_get(self._health_path, self._handle_health)
        app.router.add_get(self._webhook_path, self._handle_verify)
        app.router.add_post(self._webhook_path, self._handle_webhook)

        self._runner = web.AppRunner(app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self._webhook_host, self._webhook_port)
        await site.start()

        self._mark_connected()
        logger.info(
            "[whatsapp_cloud] Listening on %s:%d%s (Graph %s, phone_id=%s)",
            self._webhook_host,
            self._webhook_port,
            self._webhook_path,
            self._api_version,
            self._phone_number_id,
        )
        if not self._verify_token:
            logger.warning("[whatsapp_cloud] WHATSAPP_CLOUD_VERIFY_TOKEN is not set")
        if not self._app_secret:
            logger.warning("[whatsapp_cloud] WHATSAPP_CLOUD_APP_SECRET is not set")
        return True

    async def disconnect(self) -> None:
        if self._runner is not None:
            try:
                await self._runner.cleanup()
            except Exception:
                logger.exception("[whatsapp_cloud] webhook server cleanup failed")
            self._runner = None
        if self._http_client is not None:
            try:
                await self._http_client.aclose()
            except Exception:
                logger.exception("[whatsapp_cloud] http client close failed")
            self._http_client = None
        self._mark_disconnected()

    async def send(
        self,
        chat_id: str,
        content: str,
        reply_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SendResult:
        if self._http_client is None:
            return SendResult(success=False, error="Not connected")
        if not content or not content.strip():
            return SendResult(success=True, message_id=None)

        formatted = self.format_message(content)
        chunks = self.truncate_message(formatted, self._outgoing_chunk_limit())

        url = self._graph_url("messages")
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

        last_message_id: Optional[str] = None
        for idx, chunk in enumerate(chunks):
            payload: Dict[str, Any] = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": chat_id,
                "type": "text",
                "text": {"body": chunk, "preview_url": True},
            }
            if reply_to and idx == 0:
                payload["context"] = {"message_id": reply_to}
            try:
                resp = await self._http_client.post(url, headers=headers, json=payload)
            except Exception as exc:
                logger.exception("[whatsapp_cloud] send failed")
                return SendResult(success=False, error=str(exc))

            if resp.status_code != 200:
                try:
                    body = resp.json()
                except Exception:
                    body = {"raw": resp.text[:500]}
                error_msg = self._format_graph_error(body, resp.status_code)
                logger.warning(
                    "[whatsapp_cloud] send rejected (status=%d): %s",
                    resp.status_code,
                    error_msg,
                )
                return SendResult(success=False, error=error_msg)

            try:
                data = resp.json()
                ids = data.get("messages") or []
                if ids:
                    last_message_id = ids[0].get("id")
            except Exception:
                pass

        if last_message_id:
            rich_sent_store.record(chat_id, last_message_id, formatted)

        return SendResult(success=True, message_id=last_message_id)

    async def send_typing(self, chat_id: str, metadata=None) -> None:
        if self._http_client is None:
            return
        wamid = self._last_inbound_wamid_by_chat.get(chat_id)
        if not wamid:
            return

        url = self._graph_url("messages")
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": wamid,
            "typing_indicator": {"type": "text"},
        }
        try:
            resp = await self._http_client.post(url, headers=headers, json=payload)
        except Exception:
            return
        if resp.status_code != 200:
            try:
                body = resp.json()
                code = ((body or {}).get("error") or {}).get("code")
            except Exception:
                code = None
            if code == 131009:
                logger.info(
                    "[whatsapp_cloud] typing/read indicator rejected: wamid %s likely older than 30 days",
                    wamid,
                )

    async def _post_interactive(
        self,
        chat_id: str,
        interactive_body: Dict[str, Any],
        reply_to: Optional[str] = None,
    ) -> SendResult:
        if self._http_client is None:
            return SendResult(success=False, error="Not connected")

        url = self._graph_url("messages")
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": chat_id,
            "type": "interactive",
            "interactive": interactive_body,
        }
        if reply_to:
            payload["context"] = {"message_id": reply_to}

        try:
            resp = await self._http_client.post(url, headers=headers, json=payload)
        except Exception as exc:
            logger.exception("[whatsapp_cloud] interactive send failed")
            return SendResult(success=False, error=str(exc))

        if resp.status_code != 200:
            try:
                body = resp.json()
            except Exception:
                body = {"raw": resp.text[:500]}
            error_msg = self._format_graph_error(body, resp.status_code)
            logger.warning(
                "[whatsapp_cloud] interactive rejected (status=%d): %s",
                resp.status_code,
                error_msg,
            )
            return SendResult(success=False, error=error_msg)

        last_message_id: Optional[str] = None
        try:
            data = resp.json()
            ids = data.get("messages") or []
            if ids:
                last_message_id = ids[0].get("id")
        except Exception:
            pass
        return SendResult(success=True, message_id=last_message_id)

    @staticmethod
    def _truncate_button_label(text: str, limit: int = 20) -> str:
        text = str(text or "").strip()
        if len(text) <= limit:
            return text
        return text[: max(1, limit - 1)] + "…"

    @staticmethod
    def _truncate_body(text: str, limit: int = 1024) -> str:
        text = str(text or "")
        if len(text) <= limit:
            return text
        return text[: limit - 3] + "..."

    async def send_clarify(
        self,
        chat_id: str,
        question: str,
        choices: Optional[list],
        clarify_id: str,
        session_key: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SendResult:
        if self._http_client is None:
            return SendResult(success=False, error="Not connected")

        question = (question or "").strip()
        reply_to = (metadata or {}).get("reply_to_message_id") if metadata else None

        if not choices:
            return await self.send(chat_id, f"? {question}", reply_to=reply_to)

        choices_list = [str(c).strip() for c in choices[:10] if str(c).strip()]
        option_lines = "\n".join(f"{i + 1}. {c}" for i, c in enumerate(choices_list))
        body_text = self._truncate_body(f"? {question}\n\n{option_lines}")

        if len(choices_list) <= 3:
            buttons = [
                {
                    "type": "reply",
                    "reply": {
                        "id": f"cl:{clarify_id}:{idx}",
                        "title": self._truncate_button_label(str(idx + 1)),
                    },
                }
                for idx in range(len(choices_list))
            ]
            interactive: Dict[str, Any] = {
                "type": "button",
                "body": {"text": body_text},
                "action": {"buttons": buttons},
            }
        else:
            rows = []
            for idx, choice_text in enumerate(choices_list):
                rows.append(
                    {
                        "id": f"cl:{clarify_id}:{idx}",
                        "title": self._truncate_button_label(f"{idx + 1}", limit=24),
                        "description": self._truncate_button_label(
                            choice_text, limit=72
                        ),
                    }
                )
            rows.append(
                {
                    "id": f"cl:{clarify_id}:other",
                    "title": "✏️ Other",
                    "description": "Type your own answer",
                }
            )
            interactive = {
                "type": "list",
                "body": {"text": body_text},
                "action": {
                    "button": "Choose",
                    "sections": [{"title": "Options", "rows": rows}],
                },
            }

        result = await self._post_interactive(chat_id, interactive, reply_to=reply_to)
        if result.success:
            self._bounded_put(self._clarify_state, clarify_id, session_key)
        return result

    async def send_exec_approval(
        self,
        chat_id: str,
        command: str,
        session_key: str,
        description: str = "dangerous command",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SendResult:
        if self._http_client is None:
            return SendResult(success=False, error="Not connected")

        cmd_preview = command if len(command) <= 800 else command[:800] + "..."
        body_text = self._truncate_body(
            f"⚠️ *Command Approval Required*\n\n```\n{cmd_preview}\n```\n\nReason: {description}"
        )

        approval_id = uuid.uuid4().hex[:12]
        reply_to = (metadata or {}).get("reply_to_message_id") if metadata else None

        interactive = {
            "type": "button",
            "body": {"text": body_text},
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": f"appr:{approval_id}:approve",
                            "title": "✅ Approve",
                        },
                    },
                    {
                        "type": "reply",
                        "reply": {"id": f"appr:{approval_id}:deny", "title": "❌ Deny"},
                    },
                ],
            },
        }

        result = await self._post_interactive(chat_id, interactive, reply_to=reply_to)
        if result.success:
            self._bounded_put(self._exec_approval_state, approval_id, session_key)
        return result

    async def send_slash_confirm(
        self,
        chat_id: str,
        title: str,
        message: str,
        session_key: str,
        confirm_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SendResult:
        if self._http_client is None:
            return SendResult(success=False, error="Not connected")

        body_text = self._truncate_body(f"*{title}*\n\n{message}")
        reply_to = (metadata or {}).get("reply_to_message_id") if metadata else None

        interactive = {
            "type": "button",
            "body": {"text": body_text},
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": f"sc:once:{confirm_id}",
                            "title": "✅ Approve Once",
                        },
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": f"sc:always:{confirm_id}",
                            "title": "🔒 Always",
                        },
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": f"sc:cancel:{confirm_id}",
                            "title": "❌ Cancel",
                        },
                    },
                ],
            },
        }

        result = await self._post_interactive(chat_id, interactive, reply_to=reply_to)
        if result.success:
            self._bounded_put(self._slash_confirm_state, confirm_id, session_key)
        return result

    @staticmethod
    def _format_graph_error(body: Dict[str, Any], status_code: int) -> str:
        err = (body or {}).get("error") or {}
        message = err.get("message") or body.get("raw") or "unknown error"
        code = err.get("code")
        if code is not None:
            return f"graph error {code} (HTTP {status_code}): {message}"
        return f"HTTP {status_code}: {message}"

    async def get_chat_info(self, chat_id: str) -> Dict[str, Any]:
        return {"name": chat_id, "type": "dm"}

    async def _upload_media(
        self,
        file_path: str,
        media_kind: str,
        mime_type: Optional[str] = None,
    ) -> tuple[Optional[str], Optional[str]]:
        if self._http_client is None:
            return None, "Not connected"
        if not os.path.exists(file_path):
            return None, f"File not found: {file_path}"

        size = os.path.getsize(file_path)
        cap = _MEDIA_SIZE_LIMITS.get(media_kind, _MEDIA_SIZE_LIMITS["document"])
        if size > cap:
            return None, (
                f"File {os.path.basename(file_path)} is {size} bytes; "
                f"Cloud API {media_kind} cap is {cap} bytes"
            )

        if not mime_type:
            mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = _DEFAULT_MIME.get(media_kind, "application/octet-stream")

        url = self._graph_url("media")
        headers = {"Authorization": f"Bearer {self._access_token}"}
        try:
            with open(file_path, "rb") as fh:
                files = {
                    "file": (os.path.basename(file_path), fh, mime_type),
                    "messaging_product": (None, "whatsapp"),
                    "type": (None, mime_type),
                }
                resp = await self._http_client.post(url, headers=headers, files=files)
        except Exception as exc:
            logger.exception("[whatsapp_cloud] media upload failed")
            return None, str(exc)

        if resp.status_code != 200:
            try:
                body = resp.json()
            except Exception:
                body = {"raw": resp.text[:500]}
            return None, self._format_graph_error(body, resp.status_code)

        try:
            data = resp.json()
            media_id = data.get("id")
        except Exception:
            media_id = None
        if not media_id:
            return None, "Upload response missing 'id'"
        return media_id, None

    async def _send_media(
        self,
        chat_id: str,
        media_kind: str,
        *,
        media_id: Optional[str] = None,
        media_link: Optional[str] = None,
        caption: Optional[str] = None,
        filename: Optional[str] = None,
        reply_to: Optional[str] = None,
    ) -> SendResult:
        if self._http_client is None:
            return SendResult(success=False, error="Not connected")
        if bool(media_id) == bool(media_link):
            return SendResult(
                success=False,
                error="Exactly one of media_id or media_link must be set",
            )

        url = self._graph_url("messages")
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

        media_block: Dict[str, Any] = {}
        if media_id:
            media_block["id"] = media_id
        else:
            media_block["link"] = media_link
        if caption and media_kind in {"image", "video", "document"}:
            media_block["caption"] = caption
        if filename and media_kind == "document":
            media_block["filename"] = filename

        payload: Dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": chat_id,
            "type": media_kind,
            media_kind: media_block,
        }
        if reply_to:
            payload["context"] = {"message_id": reply_to}

        try:
            resp = await self._http_client.post(url, headers=headers, json=payload)
        except Exception as exc:
            logger.exception("[whatsapp_cloud] media send failed")
            return SendResult(success=False, error=str(exc))

        if resp.status_code != 200:
            try:
                body = resp.json()
            except Exception:
                body = {"raw": resp.text[:500]}
            error_msg = self._format_graph_error(body, resp.status_code)
            logger.warning(
                "[whatsapp_cloud] media send rejected (status=%d, kind=%s): %s",
                resp.status_code,
                media_kind,
                error_msg,
            )
            return SendResult(success=False, error=error_msg)

        try:
            data = resp.json()
            ids = data.get("messages") or []
            wamid = ids[0].get("id") if ids else None
        except Exception:
            wamid = None
        return SendResult(success=True, message_id=wamid)

    async def _send_media_from_path_or_link(
        self,
        chat_id: str,
        source: str,
        media_kind: str,
        *,
        caption: Optional[str] = None,
        filename: Optional[str] = None,
        reply_to: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> SendResult:
        if source.startswith(("http://", "https://")):
            return await self._send_media(
                chat_id,
                media_kind,
                media_link=source,
                caption=caption,
                filename=filename,
                reply_to=reply_to,
            )
        media_id, err = await self._upload_media(source, media_kind, mime_type)
        if err:
            return SendResult(success=False, error=err)
        return await self._send_media(
            chat_id,
            media_kind,
            media_id=media_id,
            caption=caption,
            filename=filename,
            reply_to=reply_to,
        )

    async def send_image(
        self,
        chat_id: str,
        image_url: str,
        caption: Optional[str] = None,
        reply_to: Optional[str] = None,
        **kwargs,
    ) -> SendResult:
        return await self._send_media_from_path_or_link(
            chat_id, image_url, "image", caption=caption, reply_to=reply_to
        )

    async def send_image_file(
        self,
        chat_id: str,
        image_path: str,
        caption: Optional[str] = None,
        reply_to: Optional[str] = None,
        **kwargs,
    ) -> SendResult:
        return await self._send_media_from_path_or_link(
            chat_id, image_path, "image", caption=caption, reply_to=reply_to
        )

    async def send_video(
        self,
        chat_id: str,
        video_path: str,
        caption: Optional[str] = None,
        reply_to: Optional[str] = None,
        **kwargs,
    ) -> SendResult:
        return await self._send_media_from_path_or_link(
            chat_id, video_path, "video", caption=caption, reply_to=reply_to
        )

    async def send_voice(
        self,
        chat_id: str,
        audio_path: str,
        caption: Optional[str] = None,
        reply_to: Optional[str] = None,
        **kwargs,
    ) -> SendResult:
        source = audio_path
        mime_type: Optional[str] = None

        is_local_mp3 = (
            not audio_path.startswith(("http://", "https://"))
            and audio_path.lower().endswith(".mp3")
            and os.path.exists(audio_path)
        )
        if is_local_mp3:
            opus_path = await self._convert_to_opus(audio_path)
            if opus_path:
                try:
                    result = await self._send_media_from_path_or_link(
                        chat_id,
                        opus_path,
                        "audio",
                        caption=caption,
                        reply_to=reply_to,
                        mime_type="audio/ogg; codecs=opus",
                    )
                finally:
                    try:
                        os.unlink(opus_path)
                    except OSError:
                        pass
                return result
            mime_type = "audio/mpeg"

        return await self._send_media_from_path_or_link(
            chat_id,
            source,
            "audio",
            caption=caption,
            reply_to=reply_to,
            mime_type=mime_type,
        )

    async def send_document(
        self,
        chat_id: str,
        file_path: str,
        caption: Optional[str] = None,
        file_name: Optional[str] = None,
        reply_to: Optional[str] = None,
        **kwargs,
    ) -> SendResult:
        return await self._send_media_from_path_or_link(
            chat_id,
            file_path,
            "document",
            caption=caption,
            filename=file_name or os.path.basename(file_path),
            reply_to=reply_to,
        )

    async def _convert_to_opus(self, mp3_path: str) -> Optional[str]:
        if not _FFMPEG_PATH:
            self._warn_once_no_ffmpeg()
            return None

        out_path = mp3_path.rsplit(".", 1)[0] + ".ogg"
        try:
            proc = await asyncio.create_subprocess_exec(
                _FFMPEG_PATH,
                "-y",
                "-i",
                mp3_path,
                "-c:a",
                "libopus",
                "-b:a",
                "32k",
                "-vbr",
                "on",
                "-application",
                "voip",
                out_path,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0 or not Path(out_path).exists():
                logger.error(
                    "[whatsapp_cloud] ffmpeg opus conversion failed "
                    "(returncode=%s): %s",
                    proc.returncode,
                    (stderr or b"").decode("utf-8", errors="replace")[:500],
                )
                return None
            return out_path
        except Exception:
            logger.exception("[whatsapp_cloud] ffmpeg subprocess raised")
            return None

    def _warn_once_no_ffmpeg(self) -> None:
        if self._warned_no_ffmpeg:
            return
        self._warned_no_ffmpeg = True
        logger.warning(
            "[whatsapp_cloud] ffmpeg not found on PATH — voice messages will "
            "be delivered as MP3 audio attachments"
        )

    async def _download_media_to_cache(
        self,
        media_id: str,
        *,
        ext_hint: Optional[str] = None,
    ) -> tuple[Optional[str], Optional[str]]:
        if self._http_client is None:
            return None, None

        media_id = str(media_id).strip()
        if not re.fullmatch(r"[A-Za-z0-9._-]+", media_id):
            logger.warning(
                "[whatsapp_cloud] refusing malformed media id %r", media_id[:64]
            )
            return None, None
        headers = {"Authorization": f"Bearer {self._access_token}"}

        try:
            meta_resp = await self._http_client.get(
                f"{GRAPH_API_BASE}/{self._api_version}/{media_id}",
                headers=headers,
            )
        except Exception:
            logger.exception(
                "[whatsapp_cloud] media metadata fetch raised (id=%s)", media_id
            )
            return None, None
        if meta_resp.status_code != 200:
            logger.warning(
                "[whatsapp_cloud] media metadata fetch failed (id=%s, status=%d)",
                media_id,
                meta_resp.status_code,
            )
            return None, None

        try:
            meta = meta_resp.json()
        except Exception:
            return None, None
        temp_url = meta.get("url")
        mime = meta.get("mime_type") or ""
        if not temp_url:
            return None, None

        try:
            blob_resp = await self._http_client.get(temp_url, headers=headers)
        except Exception:
            logger.exception(
                "[whatsapp_cloud] media bytes fetch raised (id=%s)", media_id
            )
            return None, None
        if blob_resp.status_code != 200:
            logger.warning(
                "[whatsapp_cloud] media bytes fetch failed (id=%s, status=%d)",
                media_id,
                blob_resp.status_code,
            )
            return None, None

        ext = ext_hint
        if not ext and mime:
            ext = _ext_for_mime(mime)
        if not ext:
            ext = ".bin"

        _INBOUND_MEDIA_CACHE.mkdir(parents=True, exist_ok=True)
        out_path = _INBOUND_MEDIA_CACHE / f"{media_id}{ext}"
        try:
            out_path.write_bytes(blob_resp.content)
        except OSError:
            logger.exception(
                "[whatsapp_cloud] failed to write cached media (id=%s)", media_id
            )
            return None, None

        return str(out_path), mime or None

    async def _handle_health(self, request: "web.Request") -> "web.Response":
        return web.json_response(
            {
                "status": "ok",
                "platform": self.platform.value,
                "phone_number_id": self._phone_number_id,
                "webhook_path": self._webhook_path,
                "verify_token_configured": bool(self._verify_token),
                "app_secret_configured": bool(self._app_secret),
                "ffmpeg_present": _FFMPEG_PATH is not None,
                "accepted": self._accepted_count,
                "duplicates": self._duplicate_count,
                "rejected_signature": self._rejected_signature_count,
            }
        )

    async def _handle_verify(self, request: "web.Request") -> "web.Response":
        if not self._verify_token:
            return web.Response(status=503, text="verify_token not configured")

        mode = request.query.get("hub.mode", "")
        token = request.query.get("hub.verify_token", "")
        challenge = request.query.get("hub.challenge", "")

        if mode != "subscribe":
            return web.Response(status=400, text="bad mode")

        import hmac as _hmac

        if not _hmac.compare_digest(token, self._verify_token):
            return web.Response(status=403, text="verify_token mismatch")
        if not challenge:
            return web.Response(status=400, text="missing challenge")
        return web.Response(text=challenge, content_type="text/plain")

    async def _handle_webhook(self, request: "web.Request") -> "web.Response":
        try:
            raw = await _read_limited_request_body(
                request,
                WEBHOOK_MAX_BODY_BYTES,
            )
        except ValueError:
            return web.Response(status=413)
        except Exception:
            return web.Response(status=400)

        if not self._app_secret:
            logger.error("[whatsapp_cloud] webhook POST refused: app_secret unset")
            return web.Response(status=503, text="app_secret not configured")

        signature_header = request.headers.get("X-Hub-Signature-256", "")
        if not self._verify_signature(raw, signature_header):
            self._rejected_signature_count += 1
            logger.warning(
                "[whatsapp_cloud] rejected webhook: invalid X-Hub-Signature-256"
            )
            return web.Response(status=401)

        import json as _json

        try:
            payload = _json.loads(raw)
        except Exception:
            logger.warning("[whatsapp_cloud] webhook body is not valid JSON")
            return web.Response(status=400)

        if not isinstance(payload, dict):
            return web.Response(status=400)

        await self._dispatch_payload(payload)
        return web.Response(status=200)

    def _verify_signature(self, raw_body: bytes, header: str) -> bool:
        if not self._app_secret or not header:
            return False
        if not header.startswith("sha256="):
            return False
        expected_hex = header[len("sha256=") :].strip()
        if not expected_hex:
            return False
        computed = hmac.new(
            self._app_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(computed.lower(), expected_hex.lower())

    def _dedup_wamid(self, wamid: str) -> bool:
        if not wamid:
            return True
        if wamid in self._seen_wamids:
            self._duplicate_count += 1
            return False
        self._seen_wamids[wamid] = True
        while len(self._seen_wamids) > WAMID_DEDUP_CACHE_SIZE:
            self._seen_wamids.popitem(last=False)
        return True

    async def _dispatch_payload(self, payload: Dict[str, Any]) -> None:
        if payload.get("object") != "whatsapp_business_account":
            logger.debug(
                "[whatsapp_cloud] ignoring non-WABA payload (object=%r)",
                payload.get("object"),
            )
            return
        for entry in payload.get("entry") or []:
            if not isinstance(entry, dict):
                continue
            for change in entry.get("changes") or []:
                if not isinstance(change, dict):
                    continue
                if change.get("field") != "messages":
                    continue
                value = change.get("value") or {}
                contacts = value.get("contacts") or []
                metadata = value.get("metadata") or {}
                contacts_by_waid: Dict[str, str] = {}
                for contact in contacts:
                    if not isinstance(contact, dict):
                        continue
                    wa_id = str(contact.get("wa_id") or "").strip()
                    profile = contact.get("profile") or {}
                    name = str(profile.get("name") or "").strip()
                    if wa_id:
                        contacts_by_waid[wa_id] = name

                for raw_message in value.get("messages") or []:
                    if not isinstance(raw_message, dict):
                        continue
                    wamid = str(raw_message.get("id") or "").strip()
                    if not self._dedup_wamid(wamid):
                        logger.debug(
                            "[whatsapp_cloud] duplicate wamid %s, skipping",
                            wamid,
                        )
                        continue
                    try:
                        event = await self._build_message_event_from_cloud(
                            raw_message, contacts_by_waid, metadata
                        )
                    except Exception:
                        logger.exception(
                            "[whatsapp_cloud] failed to build event for wamid %s",
                            wamid,
                        )
                        continue
                    if event is None:
                        continue
                    self._accepted_count += 1
                    try:
                        await self.handle_message(event)
                    except Exception:
                        logger.exception(
                            "[whatsapp_cloud] handle_message raised for wamid %s",
                            wamid,
                        )

                for status in value.get("statuses") or []:
                    if isinstance(status, dict):
                        logger.debug(
                            "[whatsapp_cloud] status %s for %s",
                            status.get("status"),
                            status.get("id"),
                        )

    async def _dispatch_interactive_reply(
        self,
        raw_message: Dict[str, Any],
        contacts_by_waid: Dict[str, str],
    ) -> bool:
        inter = raw_message.get("interactive") or {}
        inner = inter.get("button_reply") or inter.get("list_reply") or {}
        button_id = str(inner.get("id") or "").strip()
        if not button_id:
            return False

        if button_id.startswith("cl:"):
            parts = button_id.split(":", 2)
            if len(parts) != 3:
                return False
            _, clarify_id, choice = parts
            session_key = self._clarify_state.pop(clarify_id, None)
            if not session_key:
                logger.info(
                    "[whatsapp_cloud] clarify tap with no matching state (clarify_id=%s)",
                    clarify_id,
                )
                return False
            if choice == "other":
                try:
                    from tools.clarify_gateway import mark_awaiting_text

                    flipped = mark_awaiting_text(clarify_id)
                except Exception:
                    flipped = False
                if not flipped:
                    logger.info(
                        "[whatsapp_cloud] clarify 'Other' tap but entry missing (clarify_id=%s)",
                        clarify_id,
                    )
                    return False
                self._clarify_state[clarify_id] = session_key
                try:
                    await self.send(
                        str(raw_message.get("from") or ""),
                        "✏️ Type your answer:",
                    )
                except Exception:
                    logger.exception("[whatsapp_cloud] clarify other-prompt failed")
                return True
            try:
                idx = int(choice)
            except ValueError:
                logger.warning(
                    "[whatsapp_cloud] clarify tap had non-int choice: %r",
                    choice,
                )
                self._clarify_state[clarify_id] = session_key
                return False
            response_text = str(inner.get("title") or str(idx + 1))
            try:
                from tools.clarify_gateway import resolve_gateway_clarify

                resolved = resolve_gateway_clarify(clarify_id, response_text)
            except Exception:
                resolved = None
            if not resolved:
                logger.info(
                    "[whatsapp_cloud] clarify resolver reported no waiter (clarify_id=%s)",
                    clarify_id,
                )
                return False
            return True

        if button_id.startswith("appr:"):
            parts = button_id.split(":", 2)
            if len(parts) != 3:
                return False
            _, approval_id, choice = parts
            session_key = self._exec_approval_state.pop(approval_id, None)
            if not session_key:
                logger.info(
                    "[whatsapp_cloud] approval tap with no matching state (approval_id=%s)",
                    approval_id,
                )
                return False
            if choice not in ("approve", "deny"):
                self._exec_approval_state[approval_id] = session_key
                return False
            try:
                from tools.approval import resolve_gateway_approval

                resolve_gateway_approval(session_key, choice)
            except Exception:
                logger.warning("[whatsapp_cloud] approval resolver unavailable")
            confirm_text = "✅ Approved." if choice == "approve" else "❌ Denied."
            try:
                await self.send(str(raw_message.get("from") or ""), confirm_text)
            except Exception:
                logger.exception("[whatsapp_cloud] approval confirm failed")
            return True

        if button_id.startswith("sc:"):
            parts = button_id.split(":", 2)
            if len(parts) != 3:
                return False
            _, choice, confirm_id = parts
            session_key = self._slash_confirm_state.pop(confirm_id, None)
            if not session_key:
                logger.info(
                    "[whatsapp_cloud] slash_confirm tap with no matching state (confirm_id=%s)",
                    confirm_id,
                )
                return False
            if choice not in ("once", "always", "cancel"):
                self._slash_confirm_state[confirm_id] = session_key
                return False
            try:
                from tools import slash_confirm as _slash_confirm_mod

                result_text = await _slash_confirm_mod.resolve(
                    session_key, confirm_id, choice
                )
            except Exception:
                logger.exception("[whatsapp_cloud] slash_confirm.resolve failed")
                return True
            if result_text:
                try:
                    await self.send(str(raw_message.get("from") or ""), result_text)
                except Exception:
                    logger.exception("[whatsapp_cloud] slash_confirm reply failed")
            return True

        return False

    async def _build_message_event_from_cloud(
        self,
        raw_message: Dict[str, Any],
        contacts_by_waid: Dict[str, str],
        metadata: Dict[str, Any],
    ) -> Optional[MessageEvent]:
        msg_type_str = str(raw_message.get("type") or "text").lower()

        if msg_type_str == "interactive":
            handled = await self._dispatch_interactive_reply(
                raw_message, contacts_by_waid
            )
            if handled:
                return None

        body = ""
        if msg_type_str == "text":
            text = raw_message.get("text") or {}
            body = str(text.get("body") or "")
        elif msg_type_str in {"button", "interactive"}:
            if msg_type_str == "button":
                body = str((raw_message.get("button") or {}).get("text") or "")
            else:
                inter = raw_message.get("interactive") or {}
                inner = inter.get("button_reply") or inter.get("list_reply") or {}
                body = str(inner.get("title") or "")
        elif msg_type_str in {
            "image",
            "video",
            "audio",
            "voice",
            "document",
            "sticker",
        }:
            inner = raw_message.get(msg_type_str) or {}
            body = str(inner.get("caption") or "")

        message_type = {
            "text": MessageType.TEXT,
            "image": MessageType.PHOTO,
            "video": MessageType.VIDEO,
            "audio": MessageType.VOICE,
            "voice": MessageType.VOICE,
            "document": MessageType.DOCUMENT,
            "sticker": MessageType.PHOTO,
            "button": MessageType.TEXT,
            "interactive": MessageType.TEXT,
            "location": MessageType.TEXT,
            "contacts": MessageType.TEXT,
        }.get(msg_type_str, MessageType.TEXT)

        sender_id = str(raw_message.get("from") or "").strip()
        sender_name = contacts_by_waid.get(sender_id, "")

        chat_field = raw_message.get("chat")
        if chat_field:
            logger.warning(
                "[whatsapp_cloud] received group-shaped message — group support not yet implemented"
            )
            return None

        chat_id = sender_id

        gating_data = {
            "chatId": chat_id,
            "senderId": sender_id,
            "isGroup": False,
            "body": body,
        }
        if not self._should_process_message(gating_data):
            return None

        media_urls: list[str] = []
        media_types: list[str] = []
        if msg_type_str in {"image", "video", "audio", "voice", "document", "sticker"}:
            inner = raw_message.get(msg_type_str) or {}
            media_id = str(inner.get("id") or "").strip()
            inbound_mime = str(inner.get("mime_type") or "").strip()
            if media_id:
                ext_hint = None
                if inbound_mime:
                    ext_hint = _ext_for_mime(inbound_mime)
                local_path, dl_mime = await self._download_media_to_cache(
                    media_id, ext_hint=ext_hint
                )
                if local_path:
                    media_urls.append(local_path)
                    media_types.append(
                        dl_mime or inbound_mime or "application/octet-stream"
                    )
                else:
                    logger.warning(
                        "[whatsapp_cloud] failed to download inbound %s (id=%s)",
                        msg_type_str,
                        media_id,
                    )
                if msg_type_str == "document":
                    fname = str(inner.get("filename") or "").strip()
                    if fname and not body:
                        body = f"[Document: {fname}]"

        MAX_TEXT_INJECT_BYTES = 100 * 1024
        if msg_type_str == "document" and media_urls:
            for doc_path in media_urls:
                ext = Path(doc_path).suffix.lower()
                if ext in {
                    ".txt",
                    ".md",
                    ".csv",
                    ".json",
                    ".xml",
                    ".yaml",
                    ".yml",
                    ".log",
                    ".py",
                    ".js",
                    ".ts",
                    ".html",
                    ".css",
                }:
                    try:
                        file_size = Path(doc_path).stat().st_size
                        if file_size > MAX_TEXT_INJECT_BYTES:
                            continue
                        content = Path(doc_path).read_text(
                            encoding="utf-8", errors="replace"
                        )
                        display_name = Path(doc_path).name
                        injection = f"[Content of {display_name}]:\n{content}"
                        body = f"{injection}\n\n{body}" if body else injection
                    except OSError:
                        logger.exception(
                            "[whatsapp_cloud] failed to read document text: %s",
                            doc_path,
                        )

        context = raw_message.get("context") or {}
        reply_to_id = str(context.get("id") or "").strip() or None
        reply_to_text: Optional[str] = None
        reply_to_is_own = False
        if reply_to_id:
            reply_to_text = rich_sent_store.lookup(chat_id, reply_to_id)
            quoted_from = str(context.get("from") or "").strip()
            our_number = str(metadata.get("display_phone_number") or "").strip()
            if quoted_from and our_number:
                reply_to_is_own = quoted_from == our_number

        source = self.build_source(
            chat_id=chat_id,
            chat_name=sender_name or chat_id,
            chat_type="dm",
            user_id=sender_id,
            user_name=sender_name or None,
        )

        wamid = str(raw_message.get("id") or "") or None
        if wamid and chat_id:
            self._bounded_put(self._last_inbound_wamid_by_chat, chat_id, wamid)
            if body:
                rich_sent_store.record(chat_id, wamid, body)

        return MessageEvent(
            text=body,
            message_type=message_type,
            source=source,
            raw_message=raw_message,
            message_id=wamid,
            reply_to_message_id=reply_to_id,
            reply_to_text=reply_to_text,
            reply_to_is_own_message=reply_to_is_own,
            media_urls=media_urls,
            media_types=media_types,
        )


# ---------------------------------------------------------------------------
# Plugin registration
# ---------------------------------------------------------------------------


def check_requirements() -> bool:
    """Return whether WhatsApp Cloud can be used."""
    return check_whatsapp_cloud_requirements()


def validate_config(config: PlatformConfig) -> bool:
    """Validate that the platform config has phone_number_id and access_token."""
    extra = getattr(config, "extra", {}) or {}
    phone_id = (
        os.getenv("WHATSAPP_CLOUD_PHONE_NUMBER_ID")
        or extra.get("phone_number_id")
        or ""
    )
    token = os.getenv("WHATSAPP_CLOUD_ACCESS_TOKEN") or extra.get("access_token") or ""
    return bool(phone_id and token)


def is_connected(config: PlatformConfig) -> bool:
    """Return True if WhatsApp Cloud is configured."""
    return validate_config(config)


def _build_adapter(config: PlatformConfig) -> WhatsAppCloudAdapter:
    """Factory for WhatsAppCloudAdapter."""
    return WhatsAppCloudAdapter(config)


def register(ctx) -> None:
    """Plugin entry point — called by the Hermes plugin system."""
    ctx.register_platform(
        name="whatsapp_cloud",
        label="WhatsApp Cloud",
        adapter_factory=_build_adapter,
        check_fn=check_requirements,
        validate_config=validate_config,
        is_connected=is_connected,
        required_env=["WHATSAPP_CLOUD_PHONE_NUMBER_ID", "WHATSAPP_CLOUD_ACCESS_TOKEN"],
        install_hint="No extra packages needed (aiohttp + httpx are already installed)",
        max_message_length=4096,
        emoji="📱",
        pii_safe=False,
        allow_update_command=True,
        platform_hint=(
            "You are chatting via WhatsApp. Keep responses concise. "
            "Markdown is supported: *bold*, _italic_, ```code```. "
            "Images, audio, and documents can be sent natively."
        ),
    )
