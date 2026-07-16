#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAI-compatible API Adapter for Agent-Z Gateway.

This adapter provides an OpenAI-compatible API server that can be used with
any OpenAI-compatible frontend (Open WebUI, LobeChat, LibreChat, etc.).

Exposes an HTTP server with endpoints:
- POST /v1/chat/completions        - OpenAI Chat Completions format
- POST /v1/responses               - OpenAI Responses API format
- GET  /v1/models                  - lists Agent-Z as an available model
- GET  /v1/capabilities            - machine-readable API capabilities
- POST /v1/runs                    - start a run, returns run_id immediately (202)
- GET  /v1/runs/{run_id}           - retrieve current run status
- GET  /v1/runs/{run_id}/events    - SSE stream of structured lifecycle events
- POST /v1/runs/{run_id}/approval  - resolve a pending run approval
- POST /v1/runs/{run_id}/stop      - interrupt a running agent
- GET  /health                     - health check
- GET  /health/detailed           - rich status for cross-container dashboard probing

迁移自 api/api_server.py，合并到 gateway/ 目录下。
"""

# 🚪 Access - Gateway - OpenAI-compatible API Adapter

import asyncio
import hashlib
import hmac
import json
import logging
import os
import re
import sqlite3
import time
import uuid
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from aiohttp import web

    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    web = None  # type: ignore[assignment]

from common.logging_manager import get_execution_logger

logger = get_execution_logger(__name__)

# Default settings
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000  # 统一使用 8000 端口
MAX_STORED_RESPONSES = 100
MAX_REQUEST_BYTES = 10_000_000  # 10 MB
CHAT_COMPLETIONS_SSE_KEEPALIVE_SECONDS = 30.0
MAX_NORMALIZED_TEXT_LENGTH = 65_536  # 64 KB cap
MAX_CONTENT_LIST_SIZE = 1_000  # Max items when content is an array


def _coerce_port(value: Any, default: int = DEFAULT_PORT) -> int:
    """Parse a listen port without letting malformed env/config values crash startup."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


_TRUE_REQUEST_BOOL_STRINGS = frozenset({"1", "true", "yes", "on"})
_FALSE_REQUEST_BOOL_STRINGS = frozenset({"0", "false", "no", "off"})


def _coerce_request_bool(value: Any, default: bool = False) -> bool:
    """Normalize boolean-like API payload values."""
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in _TRUE_REQUEST_BOOL_STRINGS:
            return True
        if normalized in _FALSE_REQUEST_BOOL_STRINGS:
            return False
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    return default


def _normalize_chat_content(
    content: Any, *, _max_depth: int = 10, _depth: int = 0,
) -> str:
    """Normalize OpenAI chat message content into a plain text string.

    Some clients send content as an array of typed parts instead of a plain string.
    This function flattens those into a single string.
    """
    if _depth > _max_depth:
        return ""
    if content is None:
        return ""
    if isinstance(content, str):
        return content[:MAX_NORMALIZED_TEXT_LENGTH] if len(content) > MAX_NORMALIZED_TEXT_LENGTH else content

    if isinstance(content, list):
        parts: List[str] = []
        items = content[:MAX_CONTENT_LIST_SIZE] if len(content) > MAX_CONTENT_LIST_SIZE else content
        for item in items:
            if isinstance(item, str):
                if item:
                    parts.append(item[:MAX_NORMALIZED_TEXT_LENGTH])
            elif isinstance(item, dict):
                item_type = str(item.get("type") or "").strip().lower()
                if item_type in {"text", "input_text", "output_text"}:
                    text = item.get("text", "")
                    if text:
                        try:
                            parts.append(str(text)[:MAX_NORMALIZED_TEXT_LENGTH])
                        except Exception:
                            pass
            elif isinstance(item, list):
                nested = _normalize_chat_content(item, _max_depth=_max_depth, _depth=_depth + 1)
                if nested:
                    parts.append(nested)
            if sum(len(p) for p in parts) >= MAX_NORMALIZED_TEXT_LENGTH:
                break
        result = "\n".join(parts)
        return result[:MAX_NORMALIZED_TEXT_LENGTH] if len(result) > MAX_NORMALIZED_TEXT_LENGTH else result

    try:
        result = str(content)
        return result[:MAX_NORMALIZED_TEXT_LENGTH] if len(result) > MAX_NORMALIZED_TEXT_LENGTH else result
    except Exception:
        return ""


# Content part type aliases
_TEXT_PART_TYPES = frozenset({"text", "input_text", "output_text"})
_IMAGE_PART_TYPES = frozenset({"image_url", "input_image"})
_FILE_PART_TYPES = frozenset({"file", "input_file"})


def _normalize_multimodal_content(content: Any) -> Any:
    """Validate and normalize multimodal content for the API server."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content[:MAX_NORMALIZED_TEXT_LENGTH] if len(content) > MAX_NORMALIZED_TEXT_LENGTH else content
    if not isinstance(content, list):
        return _normalize_chat_content(content)

    items = content[:MAX_CONTENT_LIST_SIZE] if len(content) > MAX_CONTENT_LIST_SIZE else content
    normalized_parts: List[Dict[str, Any]] = []
    text_accum_len = 0

    for part in items:
        if isinstance(part, str):
            if part:
                trimmed = part[:MAX_NORMALIZED_TEXT_LENGTH]
                normalized_parts.append({"type": "text", "text": trimmed})
                text_accum_len += len(trimmed)
            continue

        if not isinstance(part, dict):
            continue

        raw_type = part.get("type")
        part_type = str(raw_type or "").strip().lower()

        if part_type in _TEXT_PART_TYPES:
            text = part.get("text")
            if text is None:
                continue
            if not isinstance(text, str):
                text = str(text)
            if text:
                trimmed = text[:MAX_NORMALIZED_TEXT_LENGTH]
                normalized_parts.append({"type": "text", "text": trimmed})
                text_accum_len += len(trimmed)
            continue

        if part_type in _IMAGE_PART_TYPES:
            detail = part.get("detail")
            image_ref = part.get("image_url")
            if isinstance(image_ref, dict):
                url_value = image_ref.get("url")
                detail = image_ref.get("detail", detail)
            else:
                url_value = image_ref
            if not isinstance(url_value, str) or not url_value.strip():
                raise ValueError("invalid_image_url:Image parts must include a non-empty image URL.")
            url_value = url_value.strip()
            lowered = url_value.lower()
            if lowered.startswith("data:"):
                if not lowered.startswith("data:image/") or "," not in url_value:
                    raise ValueError(
                        "unsupported_content_type:Only image data URLs are supported."
                    )
            elif not (lowered.startswith("http://") or lowered.startswith("https://")):
                raise ValueError(
                    "invalid_image_url:Image inputs must use http(s) URLs or data:image/... URLs."
                )
            image_part: Dict[str, Any] = {"type": "image_url", "image_url": {"url": url_value}}
            if detail is not None:
                if not isinstance(detail, str) or not detail.strip():
                    raise ValueError("invalid_content_part:Image detail must be a non-empty string when provided.")
                image_part["image_url"]["detail"] = detail.strip()
            normalized_parts.append(image_part)
            continue

        if part_type in _FILE_PART_TYPES:
            raise ValueError(
                "unsupported_content_type:Inline image inputs are supported, "
                "but uploaded files and document inputs are not supported on this endpoint."
            )

        raise ValueError(
            f"unsupported_content_type:Unsupported content part type {raw_type!r}. "
            "Only text and image_url/input_image parts are supported."
        )

    if not normalized_parts:
        return ""

    if all(p.get("type") == "text" for p in normalized_parts):
        return "\n".join(p["text"] for p in normalized_parts if p.get("text"))

    return normalized_parts


def _content_has_visible_payload(content: Any) -> bool:
    """True when content has any text or image attachment."""
    if isinstance(content, str):
        return bool(content.strip())
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict):
                ptype = str(part.get("type") or "").strip().lower()
                if ptype in _TEXT_PART_TYPES and str(part.get("text") or "").strip():
                    return True
                if ptype in _IMAGE_PART_TYPES:
                    return True
    return False


def _multimodal_validation_error(exc: ValueError, *, param: str) -> "web.Response":
    """Translate a ValueError into a 400 response."""
    raw = str(exc)
    code, _, message = raw.partition(":")
    if not message:
        code, message = "invalid_content_part", raw
    return web.json_response(
        _openai_error(message, code=code, param=param),
        status=400,
    )


def check_api_server_requirements() -> bool:
    """Check if API server dependencies are available."""
    return AIOHTTP_AVAILABLE


class ResponseStore:
    """SQLite-backed LRU store for Responses API state."""

    def __init__(self, max_size: int = MAX_STORED_RESPONSES, db_path: str = None):
        self._max_size = max_size
        if db_path is None:
            db_path = ":memory:"
        self._db_path: Optional[str] = db_path if db_path != ":memory:" else None
        try:
            self._conn = sqlite3.connect(db_path, check_same_thread=False)
        except Exception:
            self._conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._db_path = None

        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS responses (
                response_id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                accessed_at REAL NOT NULL
            )"""
        )
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS conversations (
                name TEXT PRIMARY KEY,
                response_id TEXT NOT NULL
            )"""
        )
        self._conn.commit()

    def get(self, response_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a stored response by ID."""
        row = self._conn.execute(
            "SELECT data FROM responses WHERE response_id = ?", (response_id,)
        ).fetchone()
        if row is None:
            return None
        self._conn.execute(
            "UPDATE responses SET accessed_at = ? WHERE response_id = ?",
            (time.time(), response_id),
        )
        self._conn.commit()
        return json.loads(row[0])

    def put(self, response_id: str, data: Dict[str, Any]) -> None:
        """Store a response, evicting the oldest if at capacity."""
        self._conn.execute(
            "INSERT OR REPLACE INTO responses (response_id, data, accessed_at) VALUES (?, ?, ?)",
            (response_id, json.dumps(data, default=str), time.time()),
        )
        count = self._conn.execute("SELECT COUNT(*) FROM responses").fetchone()[0]
        if count > self._max_size:
            evict_ids = [
                row[0]
                for row in self._conn.execute(
                    "SELECT response_id FROM responses ORDER BY accessed_at ASC LIMIT ?",
                    (count - self._max_size,),
                ).fetchall()
            ]
            if evict_ids:
                placeholders = ",".join("?" for _ in evict_ids)
                self._conn.execute(
                    f"DELETE FROM conversations WHERE response_id IN ({placeholders})",
                    evict_ids,
                )
                self._conn.execute(
                    f"DELETE FROM responses WHERE response_id IN ({placeholders})",
                    evict_ids,
                )
        self._conn.commit()

    def delete(self, response_id: str) -> bool:
        """Remove a response from the store."""
        self._conn.execute(
            "DELETE FROM conversations WHERE response_id = ?", (response_id,)
        )
        cursor = self._conn.execute(
            "DELETE FROM responses WHERE response_id = ?", (response_id,)
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def get_conversation(self, name: str) -> Optional[str]:
        """Get the latest response_id for a conversation name."""
        row = self._conn.execute(
            "SELECT response_id FROM conversations WHERE name = ?", (name,)
        ).fetchone()
        return row[0] if row else None

    def set_conversation(self, name: str, response_id: str) -> None:
        """Map a conversation name to its latest response_id."""
        self._conn.execute(
            "INSERT OR REPLACE INTO conversations (name, response_id) VALUES (?, ?)",
            (name, response_id),
        )
        self._conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        try:
            self._conn.close()
        except Exception:
            pass

    def __len__(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM responses").fetchone()
        return row[0] if row else 0


# CORS middleware
_CORS_HEADERS = {
    "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Authorization, Content-Type, Idempotency-Key",
}


if AIOHTTP_AVAILABLE:

    @web.middleware
    async def cors_middleware(request, handler):
        """Add CORS headers for explicitly allowed origins; handle OPTIONS preflight."""
        adapter = request.app.get("openai_adapter")
        origin = request.headers.get("Origin", "")
        cors_headers = None
        if adapter is not None:
            if not adapter._origin_allowed(origin):
                return web.Response(status=403)
            cors_headers = adapter._cors_headers_for_origin(origin)

        if request.method == "OPTIONS":
            if cors_headers is None:
                return web.Response(status=403)
            return web.Response(status=200, headers=cors_headers)

        response = await handler(request)
        if cors_headers is not None:
            response.headers.update(cors_headers)
        return response


else:
    cors_middleware = None  # type: ignore[assignment]


def _openai_error(
    message: str, err_type: str = "invalid_request_error", param: str = None, code: str = None
) -> Dict[str, Any]:
    """OpenAI-style error envelope."""
    return {
        "error": {
            "message": message,
            "type": err_type,
            "param": param,
            "code": code,
        }
    }


if AIOHTTP_AVAILABLE:

    @web.middleware
    async def body_limit_middleware(request, handler):
        """Reject overly large request bodies early based on Content-Length."""
        if request.method in {"POST", "PUT", "PATCH"}:
            cl = request.headers.get("Content-Length")
            if cl is not None:
                try:
                    if int(cl) > MAX_REQUEST_BYTES:
                        return web.json_response(
                            _openai_error("Request body too large.", code="body_too_large"), status=413
                        )
                except ValueError:
                    return web.json_response(
                        _openai_error("Invalid Content-Length header.", code="invalid_content_length"),
                        status=400,
                    )
        return await handler(request)


else:
    body_limit_middleware = None  # type: ignore[assignment]


_SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "0",
    "Referrer-Policy": "no-referrer",
}


if AIOHTTP_AVAILABLE:

    @web.middleware
    async def security_headers_middleware(request, handler):
        """Add security headers to all responses."""
        response = await handler(request)
        for k, v in _SECURITY_HEADERS.items():
            response.headers.setdefault(k, v)
        return response


else:
    security_headers_middleware = None  # type: ignore[assignment]


class _IdempotencyCache:
    """In-memory idempotency cache with TTL and basic LRU semantics."""

    def __init__(self, max_items: int = 1000, ttl_seconds: int = 300):
        self._store = OrderedDict()
        self._inflight: Dict[tuple[str, str], "asyncio.Task[Any]"] = {}
        self._ttl = ttl_seconds
        self._max = max_items

    def _purge(self):
        now = time.time()
        expired = [k for k, v in self._store.items() if now - v["ts"] > self._ttl]
        for k in expired:
            self._store.pop(k, None)
        while len(self._store) > self._max:
            self._store.popitem(last=False)

    async def get_or_set(self, key: str, fingerprint: str, compute_coro):
        self._purge()
        item = self._store.get(key)
        if item and item["fp"] == fingerprint:
            return item["resp"]

        inflight_key = (key, fingerprint)
        task = self._inflight.get(inflight_key)
        if task is None:

            async def _compute_and_store():
                resp = await compute_coro()
                import time as _t

                self._store[key] = {"resp": resp, "fp": fingerprint, "ts": _t.time()}
                self._purge()
                return resp

            task = asyncio.create_task(_compute_and_store())
            self._inflight[inflight_key] = task

            def _clear_inflight(done_task: "asyncio.Task[Any]") -> None:
                if self._inflight.get(inflight_key) is done_task:
                    self._inflight.pop(inflight_key, None)

            task.add_done_callback(_clear_inflight)

        return await asyncio.shield(task)


_idem_cache = _IdempotencyCache()


def _make_request_fingerprint(body: Dict[str, Any], keys: List[str]) -> str:
    """Create a fingerprint for idempotency checking."""
    subset = {k: body.get(k) for k in keys}
    return hashlib.sha256(repr(subset).encode("utf-8")).hexdigest()


def _derive_chat_session_id(
    system_prompt: Optional[str],
    first_user_message: str,
) -> str:
    """Derive a stable session ID from the conversation's first user message."""
    seed = f"{system_prompt or ''}\n{first_user_message}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return f"api-{digest}"


class OpenAIAdapter:
    """OpenAI-compatible HTTP API adapter for Gateway."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        if config is None:
            config = {}
        extra = config.get("extra", {}) if isinstance(config, dict) else config
        if not isinstance(extra, dict):
            extra = {}

        self._host: str = extra.get("host", os.getenv("API_SERVER_HOST", DEFAULT_HOST))
        raw_port = extra.get("port")
        if raw_port is None:
            raw_port = os.getenv("API_SERVER_PORT", str(DEFAULT_PORT))
        self._port: int = _coerce_port(raw_port, DEFAULT_PORT)
        self._api_key: str = extra.get("key", os.getenv("API_SERVER_KEY", ""))
        self._cors_origins: tuple[str, ...] = self._parse_cors_origins(
            extra.get("cors_origins", os.getenv("API_SERVER_CORS_ORIGINS", "")),
        )
        self._model_name: str = extra.get("model_name", os.getenv("API_SERVER_MODEL_NAME", "Agent-Z"))
        self._app: Optional["web.Application"] = None
        self._runner: Optional["web.AppRunner"] = None
        self._site: Optional["web.TCPSite"] = None
        self._response_store = ResponseStore()
        self._run_streams: Dict[str, "asyncio.Queue[Optional[Dict]]"] = {}
        self._run_streams_created: Dict[str, float] = {}
        self._active_run_agents: Dict[str, Any] = {}
        self._active_run_tasks: Dict[str, "asyncio.Task"] = {}
        self._run_statuses: Dict[str, Dict[str, Any]] = {}
        self._run_approval_sessions: Dict[str, str] = {}
        self._agent = None
        self._llm_provider = None

    @staticmethod
    def _parse_cors_origins(value: Any) -> tuple[str, ...]:
        """Normalize configured CORS origins into a stable tuple."""
        if not value:
            return ()

        if isinstance(value, str):
            items = value.split(",")
        elif isinstance(value, (list, tuple, set)):
            items = value
        else:
            items = [str(value)]

        return tuple(str(item).strip() for item in items if str(item).strip())

    def _cors_headers_for_origin(self, origin: str) -> Optional[Dict[str, str]]:
        """Return CORS headers for an allowed browser origin."""
        if not origin or not self._cors_origins:
            return None

        if "*" in self._cors_origins:
            headers = dict(_CORS_HEADERS)
            headers["Access-Control-Allow-Origin"] = "*"
            headers["Access-Control-Max-Age"] = "600"
            return headers

        if origin not in self._cors_origins:
            return None

        headers = dict(_CORS_HEADERS)
        headers["Access-Control-Allow-Origin"] = origin
        headers["Vary"] = "Origin"
        headers["Access-Control-Max-Age"] = "600"
        return headers

    def _origin_allowed(self, origin: str) -> bool:
        """Allow non-browser clients and explicitly configured browser origins."""
        if not origin:
            return True

        if not self._cors_origins:
            return False

        return "*" in self._cors_origins or origin in self._cors_origins

    def _check_auth(self, request: "web.Request") -> Optional["web.Response"]:
        """Validate Bearer token from Authorization header."""
        if not self._api_key:
            return None

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            if hmac.compare_digest(token, self._api_key):
                return None

        return web.json_response(
            {"error": {"message": "Invalid API key", "type": "invalid_request_error", "code": "invalid_api_key"}},
            status=401,
        )

    _MAX_SESSION_HEADER_LEN = 256

    def _parse_session_key_header(
        self, request: "web.Request"
    ) -> tuple[Optional[str], Optional["web.Response"]]:
        """Extract and validate the X-Session-Key header."""
        raw = request.headers.get("X-Session-Key", "").strip()
        if not raw:
            return None, None

        if not self._api_key:
            logger.warning("X-Session-Key rejected: no API key configured.")
            return None, web.json_response(
                _openai_error("X-Session-Key requires API key authentication."),
                status=403,
            )

        if re.search(r"[\r\n\x00]", raw):
            return None, web.json_response(
                {"error": {"message": "Invalid session key", "type": "invalid_request_error"}},
                status=400,
            )

        if len(raw) > self._MAX_SESSION_HEADER_LEN:
            return None, web.json_response(
                {"error": {"message": "Session key too long", "type": "invalid_request_error"}},
                status=400,
            )

        return raw, None

    def init_agent(self, agent, llm_provider=None):
        """Initialize the agent and provider."""
        self._agent = agent
        self._llm_provider = llm_provider

    async def _handle_health(self, request: "web.Request") -> "web.Response":
        """GET /health — simple health check."""
        return web.json_response({"status": "ok", "platform": "Agent-Z"})

    async def _handle_health_detailed(self, request: "web.Request") -> "web.Response":
        """GET /health/detailed — rich status for cross-container dashboard probing."""
        import psutil

        mem = psutil.virtual_memory()
        return web.json_response({
            "status": "ok",
            "platform": "Agent-Z",
            "pid": os.getpid(),
            "uptime": time.time(),
            "memory_available_mb": mem.available // (1024 * 1024),
        })

    async def _handle_models(self, request: "web.Request") -> "web.Response":
        """GET /v1/models — return Agent-Z as an available model."""
        auth_err = self._check_auth(request)
        if auth_err:
            return auth_err

        return web.json_response({
            "object": "list",
            "data": [
                {
                    "id": self._model_name,
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "agentz",
                    "permission": [],
                    "root": self._model_name,
                    "parent": None,
                }
            ],
        })

    async def _handle_capabilities(self, request: "web.Request") -> "web.Response":
        """GET /v1/capabilities — advertise the stable API surface."""
        auth_err = self._check_auth(request)
        if auth_err:
            return auth_err

        return web.json_response({
            "object": "agentz.gateway.openai_adapter.capabilities",
            "platform": "Agent-Z",
            "model": self._model_name,
            "auth": {
                "type": "bearer",
                "required": bool(self._api_key),
            },
            "runtime": {
                "mode": "gateway_agent",
                "tool_execution": "gateway",
            },
            "features": {
                "chat_completions": True,
                "chat_completions_streaming": True,
                "responses_api": True,
                "responses_streaming": True,
                "run_submission": True,
                "run_status": True,
                "run_events_sse": True,
                "run_stop": True,
                "run_approval_response": True,
                "tool_progress_events": True,
                "approval_events": True,
                "session_continuity_header": "X-Session-Id",
                "session_key_header": "X-Session-Key",
                "cors": bool(self._cors_origins),
            },
            "endpoints": {
                "health": {"method": "GET", "path": "/health"},
                "health_detailed": {"method": "GET", "path": "/health/detailed"},
                "models": {"method": "GET", "path": "/v1/models"},
                "chat_completions": {"method": "POST", "path": "/v1/chat/completions"},
                "responses": {"method": "POST", "path": "/v1/responses"},
                "runs": {"method": "POST", "path": "/v1/runs"},
                "run_status": {"method": "GET", "path": "/v1/runs/{run_id}"},
                "run_events": {"method": "GET", "path": "/v1/runs/{run_id}/events"},
                "run_approval": {"method": "POST", "path": "/v1/runs/{run_id}/approval"},
                "run_stop": {"method": "POST", "path": "/v1/runs/{run_id}/stop"},
            },
        })

    async def _handle_chat_completions(self, request: "web.Request") -> "web.Response":
        """POST /v1/chat/completions — OpenAI Chat Completions format."""
        auth_err = self._check_auth(request)
        if auth_err:
            return auth_err

        try:
            body = await request.json()
        except (json.JSONDecodeError, Exception):
            return web.json_response(_openai_error("Invalid JSON in request body"), status=400)

        messages = body.get("messages")
        if not messages or not isinstance(messages, list):
            return web.json_response(
                {"error": {"message": "Missing or invalid 'messages' field", "type": "invalid_request_error"}},
                status=400,
            )

        stream = _coerce_request_bool(body.get("stream"), default=False)

        system_prompt = None
        conversation_messages: List[Dict[str, Any]] = []

        for idx, msg in enumerate(messages):
            role = msg.get("role", "")
            raw_content = msg.get("content", "")
            if role == "system":
                content = _normalize_chat_content(raw_content)
                if system_prompt is None:
                    system_prompt = content
                else:
                    system_prompt = system_prompt + "\n" + content
            elif role in {"user", "assistant"}:
                try:
                    content = _normalize_multimodal_content(raw_content)
                except ValueError as exc:
                    return _multimodal_validation_error(exc, param=f"messages[{idx}].content")
                conversation_messages.append({"role": role, "content": content})

        user_message: Any = ""
        history = []
        if conversation_messages:
            user_message = conversation_messages[-1].get("content", "")
            history = conversation_messages[:-1]

        if not _content_has_visible_payload(user_message):
            return web.json_response(
                {"error": {"message": "No user message found in messages", "type": "invalid_request_error"}},
                status=400,
            )

        gateway_session_key, key_err = self._parse_session_key_header(request)
        if key_err is not None:
            return key_err

        provided_session_id = request.headers.get("X-Session-Id", "").strip()
        if provided_session_id:
            if not self._api_key:
                return web.json_response(
                    _openai_error("Session continuation requires API key authentication."),
                    status=403,
                )
            if re.search(r"[\r\n\x00]", provided_session_id):
                return web.json_response(
                    {"error": {"message": "Invalid session ID", "type": "invalid_request_error"}},
                    status=400,
                )
            session_id = provided_session_id
        else:
            first_user = ""
            for cm in conversation_messages:
                if cm.get("role") == "user":
                    first_user = cm.get("content", "")
                    break
            session_id = _derive_chat_session_id(system_prompt, first_user)

        completion_id = f"chatcmpl-{uuid.uuid4().hex[:29]}"
        model_name = body.get("model", self._model_name)
        created = int(time.time())

        if stream:
            import queue as _q

            _stream_q: _q.Queue = _q.Queue()

            def _on_delta(delta):
                if delta is not None:
                    _stream_q.put(delta)

            agent_ref = [None]
            agent_task = asyncio.ensure_future(
                self._run_agent(
                    user_message=user_message,
                    conversation_history=history,
                    ephemeral_system_prompt=system_prompt,
                    session_id=session_id,
                    stream_delta_callback=_on_delta,
                    agent_ref=agent_ref,
                    gateway_session_key=gateway_session_key,
                )
            )
            agent_task.add_done_callback(lambda _fut: _stream_q.put(None))

            return await self._write_sse_chat_completion(
                request, completion_id, model_name, created, _stream_q, agent_task, agent_ref, session_id=session_id,
                gateway_session_key=gateway_session_key,
            )

        async def _compute_completion():
            return await self._run_agent(
                user_message=user_message,
                conversation_history=history,
                ephemeral_system_prompt=system_prompt,
                session_id=session_id,
                gateway_session_key=gateway_session_key,
            )

        idempotency_key = request.headers.get("Idempotency-Key")
        if idempotency_key:
            fp = _make_request_fingerprint(body, keys=["model", "messages", "tools", "tool_choice", "stream"])
            try:
                result, usage = await _idem_cache.get_or_set(idempotency_key, fp, _compute_completion)
            except Exception as e:
                logger.error("Error running agent for chat completions: %s", e, exc_info=True)
                return web.json_response(
                    _openai_error(f"Internal server error: {e}", err_type="server_error"),
                    status=500,
                )
        else:
            try:
                result, usage = await _compute_completion()
            except Exception as e:
                logger.error("Error running agent for chat completions: %s", e, exc_info=True)
                return web.json_response(
                    _openai_error(f"Internal server error: {e}", err_type="server_error"),
                    status=500,
                )

        final_response = result.get("final_response") or ""
        is_partial = bool(result.get("partial"))
        is_failed = bool(result.get("failed"))
        completed = bool(result.get("completed", True))
        err_msg = result.get("error")

        if is_partial and err_msg and "truncat" in err_msg.lower():
            finish_reason = "length"
        elif is_failed or (not completed and err_msg):
            finish_reason = "error"
        else:
            finish_reason = "stop"

        response_headers = {
            "X-Session-Id": result.get("session_id", session_id),
        }
        if gateway_session_key:
            response_headers["X-Session-Key"] = gateway_session_key

        if not final_response and (is_failed or is_partial):
            err_body = _openai_error(
                err_msg or "Agent run did not produce a response.",
                err_type="server_error",
                code="agent_incomplete",
            )
            err_body["error"]["agentz"] = {
                "completed": completed,
                "partial": is_partial,
                "failed": is_failed,
            }
            response_headers["X-Completed"] = "false"
            response_headers["X-Partial"] = "true" if is_partial else "false"
            return web.json_response(err_body, status=502, headers=response_headers)

        response_data = {
            "id": completion_id,
            "object": "chat.completion",
            "created": created,
            "model": model_name,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": final_response,
                    },
                    "finish_reason": finish_reason,
                }
            ],
            "usage": {
                "prompt_tokens": usage.get("input_tokens", 0),
                "completion_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
        }
        if is_partial or is_failed or not completed:
            response_data["agentz"] = {
                "completed": completed,
                "partial": is_partial,
                "failed": is_failed,
                "error": err_msg,
                "error_code": "output_truncated" if finish_reason == "length" else "agent_error",
            }
            response_headers["X-Completed"] = "false"
            response_headers["X-Partial"] = "true" if is_partial else "false"
            if err_msg:
                response_headers["X-Error"] = err_msg[:200]

        return web.json_response(response_data, headers=response_headers)

    async def _write_sse_chat_completion(
        self, request: "web.Request", completion_id: str, model: str,
        created: int, stream_q, agent_task, agent_ref=None, session_id: str = None,
        gateway_session_key: str = None,
    ) -> "web.StreamResponse":
        """Write streaming SSE from agent's stream_delta_callback queue."""
        import queue as _q

        sse_headers = {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
        origin = request.headers.get("Origin", "")
        cors = self._cors_headers_for_origin(origin) if origin else None
        if cors:
            sse_headers.update(cors)
        if session_id:
            sse_headers["X-Session-Id"] = session_id
        if gateway_session_key:
            sse_headers["X-Session-Key"] = gateway_session_key

        response = web.StreamResponse(status=200, reason="OK", headers=sse_headers)
        await response.prepare(request)

        last_chunk_id = 0
        try:
            while True:
                try:
                    delta = stream_q.get(timeout=CHAT_COMPLETIONS_SSE_KEEPALIVE_SECONDS)
                except _q.empty:
                    await response.write(b": keepalive\n\n")
                    if agent_task.done():
                        break
                    continue

                if delta is None:
                    break

                if delta == "__tool_progress__":
                    continue

                last_chunk_id += 1
                chunk_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"

                if isinstance(delta, str):
                    content = delta
                elif isinstance(delta, dict):
                    content = delta.get("content", delta.get("text", ""))
                else:
                    content = str(delta)

                chunk = {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"role": "assistant", "content": content},
                            "finish_reason": None,
                        }
                    ],
                }
                await response.write(f"data: {json.dumps(chunk)}\n\n".encode("utf-8"))

            final_chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop",
                    }
                ],
            }
            await response.write(f"data: {json.dumps(final_chunk)}\n\n".encode("utf-8"))
            await response.write(b"data: [DONE]\n\n")

        except asyncio.CancelledError:
            if agent_ref and agent_ref[0]:
                try:
                    agent_ref[0].interrupt()
                except Exception:
                    pass
            raise

        await response.write_eof()
        return response

    async def _run_agent(
        self,
        user_message: str,
        conversation_history: List[Dict[str, Any]] = None,
        ephemeral_system_prompt: Optional[str] = None,
        session_id: Optional[str] = None,
        stream_delta_callback=None,
        tool_start_callback=None,
        tool_complete_callback=None,
        agent_ref=None,
        gateway_session_key: Optional[str] = None,
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Run the agent and return result."""
        if conversation_history is None:
            conversation_history = []

        result = {"final_response": "", "completed": True, "session_id": session_id}
        usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

        if self._agent:
            try:
                if hasattr(self._agent, "respond"):
                    response = await self._agent.respond(user_message, {"session_id": session_id})
                    result["final_response"] = getattr(response, "content", str(response))
                    if hasattr(response, "confidence"):
                        result["confidence"] = response.confidence
                elif hasattr(self._agent, "run"):
                    response = await self._agent.run(user_message)
                    result["final_response"] = getattr(response, "content", str(response))
            except Exception as e:
                result["failed"] = True
                result["error"] = str(e)
        else:
            result["final_response"] = "Agent not initialized. Please configure the agent first."

        return result, usage

    async def _handle_responses(self, request: "web.Request") -> "web.Response":
        """POST /v1/responses — OpenAI Responses API format."""
        auth_err = self._check_auth(request)
        if auth_err:
            return auth_err

        try:
            body = await request.json()
        except (json.JSONDecodeError, Exception):
            return web.json_response(_openai_error("Invalid JSON in request body"), status=400)

        response_id = f"resp_{uuid.uuid4().hex[:24]}"
        previous_response_id = body.get("previous_response_id")

        if previous_response_id:
            stored = self._response_store.get(previous_response_id)
            if stored:
                conversation_history = stored.get("conversation_history", [])
            else:
                conversation_history = []
        else:
            conversation_history = []

        input_content = body.get("input", "")
        if isinstance(input_content, list):
            for item in input_content:
                if isinstance(item, dict):
                    content = item.get("content", [])
                    if isinstance(content, list):
                        for c in content:
                            if isinstance(c, dict) and c.get("type") in _TEXT_PART_TYPES:
                                conversation_history.append({
                                    "role": "user",
                                    "content": c.get("text", "")
                                })
                    elif isinstance(content, str):
                        conversation_history.append({"role": "user", "content": content})
        elif isinstance(input_content, str):
            conversation_history.append({"role": "user", "content": input_content})

        result, usage = await self._run_agent(
            user_message=str(input_content),
            conversation_history=conversation_history,
        )

        self._response_store.put(response_id, {
            "output": result.get("final_response", ""),
            "conversation_history": conversation_history,
        })

        return web.json_response({
            "id": response_id,
            "object": "response",
            "status": "completed",
            "output": [
                {
                    "id": f"msg_{uuid.uuid4().hex[:24]}",
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "output_text",
                            "text": result.get("final_response", ""),
                        }
                    ],
                }
            ],
            "usage": usage,
        })

    async def _handle_get_response(self, request: "web.Request") -> "web.Response":
        """GET /v1/responses/{response_id} — Retrieve a stored response."""
        auth_err = self._check_auth(request)
        if auth_err:
            return auth_err

        response_id = request.match_info.get("response_id")
        stored = self._response_store.get(response_id)

        if not stored:
            return web.json_response(
                {"error": {"message": "Response not found", "type": "invalid_request_error"}},
                status=404,
            )

        return web.json_response({
            "id": response_id,
            "object": "response",
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "output_text",
                            "text": stored.get("output", ""),
                        }
                    ],
                }
            ],
        })

    async def _handle_delete_response(self, request: "web.Request") -> "web.Response":
        """DELETE /v1/responses/{response_id} — Delete a stored response."""
        auth_err = self._check_auth(request)
        if auth_err:
            return auth_err

        response_id = request.match_info.get("response_id")
        deleted = self._response_store.delete(response_id)

        return web.json_response({"deleted": deleted})

    async def _handle_runs(self, request: "web.Request") -> "web.Response":
        """POST /v1/runs — Start a run."""
        auth_err = self._check_auth(request)
        if auth_err:
            return auth_err

        try:
            body = await request.json()
        except (json.JSONDecodeError, Exception):
            return web.json_response(_openai_error("Invalid JSON in request body"), status=400)

        run_id = f"run_{uuid.uuid4().hex[:24]}"
        self._run_statuses[run_id] = {"status": "pending", "run_id": run_id}

        return web.json_response({
            "id": run_id,
            "status": "pending",
        }, status=202)

    async def _handle_run_status(self, request: "web.Request") -> "web.Response":
        """GET /v1/runs/{run_id} — Get run status."""
        auth_err = self._check_auth(request)
        if auth_err:
            return auth_err

        run_id = request.match_info.get("run_id")
        status = self._run_statuses.get(run_id, {})

        if not status:
            return web.json_response(
                {"error": {"message": "Run not found", "type": "invalid_request_error"}},
                status=404,
            )

        return web.json_response(status)

    async def _handle_run_events(self, request: "web.Request") -> "web.Response":
        """GET /v1/runs/{run_id}/events — SSE stream of run events."""
        auth_err = self._check_auth(request)
        if auth_err:
            return auth_err

        run_id = request.match_info.get("run_id")
        status = self._run_statuses.get(run_id, {})
        if not status:
            return web.json_response(
                {"error": {"message": "Run not found", "type": "invalid_request_error"}},
                status=404,
            )

        sse_headers = {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
        }
        response = web.StreamResponse(status=200, reason="OK", headers=sse_headers)
        await response.prepare(request)

        event_data = {
            "event": "status",
            "data": {"status": status.get("status", "completed")},
        }
        await response.write(f"data: {json.dumps(event_data)}\n\n".encode("utf-8"))
        await response.write(b"data: [DONE]\n\n")
        await response.write_eof()

        return response

    async def _handle_run_approval(self, request: "web.Request") -> "web.Response":
        """POST /v1/runs/{run_id}/approval — Resolve run approval."""
        auth_err = self._check_auth(request)
        if auth_err:
            return auth_err

        try:
            body = await request.json()
        except (json.JSONDecodeError, Exception):
            return web.json_response(_openai_error("Invalid JSON in request body"), status=400)

        return web.json_response({"approved": body.get("approved", True)})

    async def _handle_run_stop(self, request: "web.Request") -> "web.Response":
        """POST /v1/runs/{run_id}/stop — Interrupt running agent."""
        auth_err = self._check_auth(request)
        if auth_err:
            return auth_err

        run_id = request.match_info.get("run_id")
        if run_id in self._active_run_agents:
            try:
                self._active_run_agents[run_id].interrupt()
            except Exception:
                pass

        return web.json_response({"stopped": True})

    async def _handle_cors_preflight(self, request: "web.Request") -> "web.Response":
        """Handle OPTIONS preflight request."""
        return web.Response(status=200)

    async def start(self):
        """Start the API server."""
        if not AIOHTTP_AVAILABLE:
            logger.error("aiohttp is not available. Cannot start API server.")
            return

        self._app = web.Application(middlewares=[])
        self._app["openai_adapter"] = self

        if cors_middleware:
            self._app.middlewares.append(cors_middleware)
        if body_limit_middleware:
            self._app.middlewares.append(body_limit_middleware)
        if security_headers_middleware:
            self._app.middlewares.append(security_headers_middleware)

        self._app.router.add_get("/health", self._handle_health)
        self._app.router.add_get("/health/detailed", self._handle_health_detailed)
        self._app.router.add_get("/v1/models", self._handle_models)
        self._app.router.add_get("/v1/capabilities", self._handle_capabilities)
        self._app.router.add_post("/v1/chat/completions", self._handle_chat_completions)
        self._app.router.add_post("/v1/responses", self._handle_responses)
        self._app.router.add_get(r"/v1/responses/{response_id}", self._handle_get_response)
        self._app.router.add_delete(r"/v1/responses/{response_id}", self._handle_delete_response)
        self._app.router.add_post("/v1/runs", self._handle_runs)
        self._app.router.add_get(r"/v1/runs/{run_id}", self._handle_run_status)
        self._app.router.add_get(r"/v1/runs/{run_id}/events", self._handle_run_events)
        self._app.router.add_post(r"/v1/runs/{run_id}/approval", self._handle_run_approval)
        self._app.router.add_post(r"/v1/runs/{run_id}/stop", self._handle_run_stop)
        self._app.router.add_options("/{path:.*}", self._handle_cors_preflight)

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, self._host, self._port)
        await self._site.start()

        logger.info(f"OpenAI-compatible API adapter started on {self._host}:{self._port}")

    async def stop(self):
        """Stop the API server."""
        if self._site:
            await self._site.stop()
        if self._runner:
            await self._runner.cleanup()
        self._response_store.close()
        logger.info("OpenAI-compatible API adapter stopped")


def create_openai_adapter(config: Optional[Dict[str, Any]] = None) -> OpenAIAdapter:
    """Create and return an OpenAI adapter instance."""
    return OpenAIAdapter(config)


# 向后兼容别名
APIServerAdapter = OpenAIAdapter


def create_api_server(config: Optional[Dict[str, Any]] = None) -> OpenAIAdapter:
    """Create and return an API server adapter instance. (向后兼容别名)"""
    return create_openai_adapter(config)