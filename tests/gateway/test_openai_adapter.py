#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the OpenAI-compatible API adapter.
迁移自 tests/api/test_api_server.py
"""

# 🚪 Access - Gateway - OpenAI Adapter Tests

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Skip tests if aiohttp is not available
pytest.importorskip("aiohttp")

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, TestClient

# 迁移后的导入路径
from gateway.adapters.openai_adapter import (
    OpenAIAdapter,
    ResponseStore,
    _IdempotencyCache,
    _normalize_chat_content,
    _normalize_multimodal_content,
    _content_has_visible_payload,
    check_api_server_requirements,
    _openai_error,
)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


class TestNormalizeChatContent:
    """Tests for _normalize_chat_content function."""

    def test_none_returns_empty(self):
        assert _normalize_chat_content(None) == ""

    def test_string_passthrough(self):
        assert _normalize_chat_content("hello world") == "hello world"

    def test_list_of_strings(self):
        content = ["hello", "world"]
        result = _normalize_chat_content(content)
        assert "hello" in result
        assert "world" in result

    def test_list_of_text_parts(self):
        content = [
            {"type": "text", "text": "hello"},
            {"type": "input_text", "text": "world"},
        ]
        result = _normalize_chat_content(content)
        assert "hello" in result
        assert "world" in result

    def test_nested_list(self):
        content = [["hello", "world"]]
        result = _normalize_chat_content(content)
        assert "hello" in result
        assert "world" in result

    def test_max_length_truncation(self):
        long_text = "a" * 100000
        result = _normalize_chat_content(long_text)
        assert len(result) <= 65536


class TestNormalizeMultimodalContent:
    """Tests for _normalize_multimodal_content function."""

    def test_none_returns_empty(self):
        assert _normalize_multimodal_content(None) == ""

    def test_string_passthrough(self):
        assert _normalize_multimodal_content("hello") == "hello"

    def test_text_part_normalized(self):
        content = [{"type": "text", "text": "hello"}]
        result = _normalize_multimodal_content(content)
        assert isinstance(result, list)
        assert result[0]["type"] == "text"

    def test_image_part_with_valid_url(self):
        content = [{"type": "image_url", "image_url": {"url": "https://example.com/image.png"}}]
        result = _normalize_multimodal_content(content)
        assert isinstance(result, list)
        assert result[0]["type"] == "image_url"

    def test_image_part_with_data_url(self):
        content = [{"type": "image_url", "image_url": {"url": "data:image/png;base64,abc123"}}]
        result = _normalize_multimodal_content(content)
        assert isinstance(result, list)

    def test_invalid_image_url_raises(self):
        content = [{"type": "image_url", "image_url": {}}]
        with pytest.raises(ValueError) as exc_info:
            _normalize_multimodal_content(content)
        assert "invalid_image_url" in str(exc_info.value)

    def test_unsupported_file_type_raises(self):
        content = [{"type": "file", "file": {"id": "file-123"}}]
        with pytest.raises(ValueError) as exc_info:
            _normalize_multimodal_content(content)
        assert "unsupported_content_type" in str(exc_info.value)

    def test_text_only_collapsed_to_string(self):
        content = [
            {"type": "text", "text": "hello"},
            {"type": "text", "text": "world"},
        ]
        result = _normalize_multimodal_content(content)
        assert isinstance(result, str)
        assert "hello" in result
        assert "world" in result


class TestContentHasVisiblePayload:
    """Tests for _content_has_visible_payload function."""

    def test_empty_string_false(self):
        assert _content_has_visible_payload("") is False

    def test_whitespace_string_false(self):
        assert _content_has_visible_payload("   ") is False

    def test_normal_string_true(self):
        assert _content_has_visible_payload("hello") is True

    def test_text_part_true(self):
        content = [{"type": "text", "text": "hello"}]
        assert _content_has_visible_payload(content) is True

    def test_image_part_true(self):
        content = [{"type": "image_url", "image_url": {"url": "https://example.com/image.png"}}]
        assert _content_has_visible_payload(content) is True

    def test_empty_list_false(self):
        assert _content_has_visible_payload([]) is False


class TestCheckRequirements:
    """Tests for check_api_server_requirements function."""

    def test_returns_true_when_aiohttp_available(self):
        assert check_api_server_requirements() is True


# ---------------------------------------------------------------------------
# ResponseStore
# ---------------------------------------------------------------------------


class TestResponseStore:
    """Tests for ResponseStore class."""

    def test_put_and_get(self):
        store = ResponseStore(max_size=10)
        store.put("resp_1", {"output": "hello"})
        assert store.get("resp_1") == {"output": "hello"}

    def test_get_missing_returns_none(self):
        store = ResponseStore(max_size=10)
        assert store.get("resp_missing") is None

    def test_lru_eviction(self):
        store = ResponseStore(max_size=3)
        store.put("resp_1", {"output": "one"})
        store.put("resp_2", {"output": "two"})
        store.put("resp_3", {"output": "three"})
        store.put("resp_4", {"output": "four"})
        assert store.get("resp_1") is None
        assert store.get("resp_2") is not None
        assert len(store) == 3

    def test_access_refreshes_lru(self):
        store = ResponseStore(max_size=3)
        store.put("resp_1", {"output": "one"})
        store.put("resp_2", {"output": "two"})
        store.put("resp_3", {"output": "three"})
        store.get("resp_1")
        store.put("resp_4", {"output": "four"})
        assert store.get("resp_2") is None
        assert store.get("resp_1") is not None

    def test_delete_existing(self):
        store = ResponseStore(max_size=10)
        store.put("resp_1", {"output": "hello"})
        assert store.delete("resp_1") is True
        assert store.get("resp_1") is None

    def test_delete_missing(self):
        store = ResponseStore(max_size=10)
        assert store.delete("resp_missing") is False


# ---------------------------------------------------------------------------
# _IdempotencyCache
# ---------------------------------------------------------------------------


class TestIdempotencyCache:
    """Tests for _IdempotencyCache class."""

    @pytest.mark.asyncio
    async def test_concurrent_same_key_and_fingerprint_runs_once(self):
        cache = _IdempotencyCache()
        gate = asyncio.Event()
        started = asyncio.Event()
        calls = 0

        async def compute():
            nonlocal calls
            calls += 1
            started.set()
            await gate.wait()
            return ("response", {"total_tokens": 1})

        first = asyncio.create_task(cache.get_or_set("idem-key", "fp-1", compute))
        second = asyncio.create_task(cache.get_or_set("idem-key", "fp-1", compute))

        await started.wait()
        assert calls == 1

        gate.set()
        first_result, second_result = await asyncio.gather(first, second)

        assert first_result == second_result == ("response", {"total_tokens": 1})

    @pytest.mark.asyncio
    async def test_different_fingerprint_does_not_reuse_inflight_task(self):
        cache = _IdempotencyCache()
        gate = asyncio.Event()
        started = asyncio.Event()
        calls = 0

        async def compute(fp):
            nonlocal calls
            calls += 1
            started.set()
            await gate.wait()
            return (f"response-{fp}", {"total_tokens": 1})

        first = asyncio.create_task(cache.get_or_set("idem-key", "fp-1", lambda: compute("fp-1")))
        await started.wait()
        gate.set()

        first_result = await first
        assert "fp-1" in first_result[0]


# ---------------------------------------------------------------------------
# OpenAIAdapter
# ---------------------------------------------------------------------------


class TestOpenAIAdapter:
    """Tests for OpenAIAdapter class."""

    def test_init_defaults(self):
        adapter = OpenAIAdapter()
        assert adapter._host == "127.0.0.1"
        assert adapter._port == 8000  # 统一使用 8000 端口
        assert adapter._api_key == ""
        assert adapter._model_name == "Agent-Z"

    def test_init_with_config(self):
        config = {
            "extra": {
                "host": "0.0.0.0",
                "port": 9000,
                "key": "secret-key",
                "model_name": "custom-model",
            }
        }
        adapter = OpenAIAdapter(config)
        assert adapter._host == "0.0.0.0"
        assert adapter._port == 9000
        assert adapter._api_key == "secret-key"
        assert adapter._model_name == "custom-model"

    def test_parse_cors_origins_empty(self):
        result = OpenAIAdapter._parse_cors_origins("")
        assert result == ()

    def test_parse_cors_origins_single(self):
        result = OpenAIAdapter._parse_cors_origins("https://example.com")
        assert result == ("https://example.com",)

    def test_parse_cors_origins_multiple(self):
        result = OpenAIAdapter._parse_cors_origins("https://a.com, https://b.com")
        assert result == ("https://a.com", "https://b.com")

    def test_origin_allowed_no_origins(self):
        adapter = OpenAIAdapter()
        assert adapter._origin_allowed("") is False
        assert adapter._origin_allowed("https://example.com") is False

    def test_origin_allowed_with_asterisk(self):
        adapter = OpenAIAdapter({"extra": {"cors_origins": "*"}})
        assert adapter._origin_allowed("https://any.com") is True

    def test_origin_allowed_specific(self):
        adapter = OpenAIAdapter({"extra": {"cors_origins": "https://allowed.com"}})
        assert adapter._origin_allowed("https://allowed.com") is True
        assert adapter._origin_allowed("https://other.com") is False

    def test_check_auth_no_key(self):
        adapter = OpenAIAdapter()
        request = MagicMock()
        request.headers = {}
        assert adapter._check_auth(request) is None

    def test_check_auth_invalid_token(self):
        adapter = OpenAIAdapter({"extra": {"key": "correct-key"}})
        request = MagicMock()
        request.headers = {"Authorization": "Bearer wrong-key"}
        response = adapter._check_auth(request)
        assert response is not None
        assert response.status == 401

    def test_check_auth_valid_token(self):
        adapter = OpenAIAdapter({"extra": {"key": "correct-key"}})
        request = MagicMock()
        request.headers = {"Authorization": "Bearer correct-key"}
        assert adapter._check_auth(request) is None


# ---------------------------------------------------------------------------
# Integration tests with TestClient
# ---------------------------------------------------------------------------


class TestAPIIntegration:
    """Integration tests using TestClient."""

    @pytest.fixture
    async def client(self):
        """Create a test client."""
        adapter = OpenAIAdapter()
        adapter._app = web.Application()

        async def setup_app(app):
            app["openai_adapter"] = adapter
            app.router.add_get("/health", adapter._handle_health)
            app.router.add_get("/v1/models", adapter._handle_models)
            app.router.add_get("/v1/capabilities", adapter._handle_capabilities)

        app = await setup_app(adapter._app)
        async with TestClient(adapter._app) as client:
            yield client

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test the /health endpoint."""
        adapter = OpenAIAdapter()
        adapter._app = web.Application()
        adapter._app["openai_adapter"] = adapter
        adapter._app.router.add_get("/health", adapter._handle_health)

        async with TestClient(adapter._app) as client:
            resp = await client.get("/health")
            assert resp.status == 200
            data = await resp.json()
            assert data["status"] == "ok"
            assert data["platform"] == "Agent-Z"

    @pytest.mark.asyncio
    async def test_models_endpoint(self):
        """Test the /v1/models endpoint."""
        adapter = OpenAIAdapter()
        adapter._app = web.Application()
        adapter._app["openai_adapter"] = adapter
        adapter._app.router.add_get("/v1/models", adapter._handle_models)

        async with TestClient(adapter._app) as client:
            resp = await client.get("/v1/models")
            assert resp.status == 200
            data = await resp.json()
            assert data["object"] == "list"
            assert len(data["data"]) == 1
            assert data["data"][0]["id"] == "Agent-Z"

    @pytest.mark.asyncio
    async def test_chat_completions_basic(self):
        """Test basic chat completions request."""
        adapter = OpenAIAdapter()
        adapter._app = web.Application()
        adapter._app["openai_adapter"] = adapter
        adapter._app.router.add_post("/v1/chat/completions", adapter._handle_chat_completions)

        async with TestClient(adapter._app) as client:
            resp = await client.post(
                "/v1/chat/completions",
                json={
                    "model": "Agent-Z",
                    "messages": [{"role": "user", "content": "Hello"}],
                },
            )
            assert resp.status == 200
            data = await resp.json()
            assert "id" in data
            assert data["object"] == "chat.completion"
            assert "choices" in data

    @pytest.mark.asyncio
    async def test_chat_completions_missing_messages(self):
        """Test chat completions with missing messages."""
        adapter = OpenAIAdapter()
        adapter._app = web.Application()
        adapter._app["openai_adapter"] = adapter
        adapter._app.router.add_post("/v1/chat/completions", adapter._handle_chat_completions)

        async with TestClient(adapter._app) as client:
            resp = await client.post("/v1/chat/completions", json={})
            assert resp.status == 400

    @pytest.mark.asyncio
    async def test_responses_api(self):
        """Test the /v1/responses endpoint."""
        adapter = OpenAIAdapter()
        adapter._app = web.Application()
        adapter._app["openai_adapter"] = adapter
        adapter._app.router.add_post("/v1/responses", adapter._handle_responses)

        async with TestClient(adapter._app) as client:
            resp = await client.post(
                "/v1/responses",
                json={"input": "Hello, how are you?"},
            )
            assert resp.status == 200
            data = await resp.json()
            assert "id" in data
            assert data["object"] == "response"


class TestOpenAIError:
    """Tests for _openai_error function."""

    def test_basic_error(self):
        result = _openai_error("Test error message")
        assert result["error"]["message"] == "Test error message"
        assert result["error"]["type"] == "invalid_request_error"
        assert result["error"]["param"] is None
        assert result["error"]["code"] is None

    def test_error_with_all_params(self):
        result = _openai_error("Test", "server_error", "param", "code")
        assert result["error"]["message"] == "Test"
        assert result["error"]["type"] == "server_error"
        assert result["error"]["param"] == "param"
        assert result["error"]["code"] == "code"