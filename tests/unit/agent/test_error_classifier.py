#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the enhanced Error Classifier.

Tests provider-specific patterns, SSL/TLS, disconnect detection,
usage-limit disambiguation, and metadata.raw parsing.
"""

import json
from dataclasses import dataclass
from typing import Optional

import pytest

from agent.error.error_classifier import (
    ClassifiedError,
    FailoverReason,
    classify_api_error,
)


@dataclass
class MockAPIError(Exception):
    """Mock API error for testing."""
    status_code: Optional[int] = None
    body: Optional[dict] = None
    message: str = ""

    def __str__(self):
        return self.message


class TestProviderSpecificPatterns:
    """Test provider-specific error patterns."""

    def test_anthropic_thinking_signature_error(self):
        """Test Anthropic thinking block signature invalid (400)."""
        error = MockAPIError(
            status_code=400,
            message="Invalid signature for thinking block",
        )
        result = classify_api_error(error)

        assert result.reason == FailoverReason.thinking_signature
        assert result.retryable is True
        assert result.should_compress is False

    def test_anthropic_long_context_tier_gate(self):
        """Test Anthropic long-context tier gate (429)."""
        error = MockAPIError(
            status_code=429,
            message="Extra usage requires long context tier subscription",
        )
        result = classify_api_error(error)

        assert result.reason == FailoverReason.long_context_tier
        assert result.retryable is True
        assert result.should_compress is True

    def test_llama_cpp_grammar_pattern_error(self):
        """Test llama.cpp grammar pattern rejection (400)."""
        error = MockAPIError(
            status_code=400,
            message="Error parsing grammar: json-schema-to-grammar rejected pattern",
        )
        result = classify_api_error(error)

        assert result.reason == FailoverReason.llama_cpp_grammar_pattern
        assert result.retryable is True
        assert result.should_compress is False

    def test_xai_grok_subscription_error(self):
        """Test xAI Grok subscription entitlement error."""
        error = MockAPIError(
            message="You do not have an active Grok subscription",
        )
        result = classify_api_error(error)

        assert result.reason == FailoverReason.auth
        assert result.retryable is False
        assert result.should_fallback is True

    def test_xai_grok_out_of_resources(self):
        """Test xAI Grok out of available resources."""
        error = MockAPIError(
            message="You have either run out of available resources or do not have an active Grok subscription",
        )
        result = classify_api_error(error)

        assert result.reason == FailoverReason.auth
        assert result.retryable is False


class TestOpenRouterPatterns:
    """Test OpenRouter-specific patterns."""

    def test_openrouter_policy_blocked_404(self):
        """Test OpenRouter policy blocked (404)."""
        error = MockAPIError(
            status_code=404,
            message="No endpoints available matching your guardrail restrictions and data policy",
        )
        result = classify_api_error(error)

        assert result.reason == FailoverReason.provider_policy_blocked
        assert result.retryable is False
        assert result.should_fallback is False

    def test_openrouter_metadata_raw_parsing(self):
        """Test OpenRouter metadata.raw parsing for upstream errors."""
        # Simulate OpenRouter wrapping upstream error
        upstream_error = json.dumps({
            "error": {
                "message": "context length exceeded",
                "type": "invalid_request_error"
            }
        })

        error = MockAPIError(
            status_code=400,
            body={
                "error": {
                    "message": "Provider returned error",
                    "code": "upstream_error",
                    "metadata": {
                        "raw": upstream_error
                    }
                }
            },
            message="Provider returned error",
        )
        result = classify_api_error(error)

        # Should detect context overflow from nested error
        assert result.reason == FailoverReason.context_overflow
        assert result.should_compress is True


class TestSSLandDisconnectPatterns:
    """Test SSL/TLS and server disconnect patterns."""

    def test_ssl_transient_error(self):
        """Test SSL/TLS transient errors are classified as timeout."""
        error = MockAPIError(
            message="[SSL: BAD_RECORD_MAC] ssl alert",
        )
        result = classify_api_error(error)

        assert result.reason == FailoverReason.timeout
        assert result.retryable is True
        # Should NOT trigger compression for SSL hiccups
        assert result.should_compress is False

    def test_server_disconnect_with_large_context(self):
        """Test server disconnect on large session triggers context overflow."""
        error = MockAPIError(
            message="Server disconnected unexpectedly",
        )
        result = classify_api_error(
            error,
            approx_tokens=150000,
            context_length=200000,
            num_messages=150,
        )

        assert result.reason == FailoverReason.context_overflow
        assert result.should_compress is True

    def test_server_disconnect_with_small_context(self):
        """Test server disconnect on small session triggers timeout."""
        error = MockAPIError(
            message="Connection reset by peer",
        )
        result = classify_api_error(
            error,
            approx_tokens=1000,
            context_length=200000,
        )

        assert result.reason == FailoverReason.timeout
        assert result.retryable is True


class TestUsageLimitDisambiguation:
    """Test usage-limit disambiguation (billing vs rate_limit)."""

    def test_usage_limit_with_retry_signal(self):
        """Test usage-limit with retry signal is classified as rate_limit."""
        error = MockAPIError(
            status_code=402,
            message="Usage limit exceeded. Please try again in 5 minutes.",
        )
        result = classify_api_error(error)

        assert result.reason == FailoverReason.rate_limit
        assert result.retryable is True
        assert result.should_rotate_credential is True

    def test_usage_limit_with_billing_signal(self):
        """Test usage-limit without retry signal is classified as billing."""
        error = MockAPIError(
            status_code=402,
            message="Insufficient credits for this operation",
        )
        result = classify_api_error(error)

        assert result.reason == FailoverReason.billing
        assert result.retryable is False
        assert result.should_rotate_credential is True

    def test_usage_limit_transient_signals(self):
        """Test various transient signals for usage limit."""
        transient_messages = [
            "quota exceeded, resets at midnight",
            "limit exceeded, retry after 1 hour",
            "usage limit, please wait a moment",
            "key limit exceeded, requests remaining: 0",
        ]

        for msg in transient_messages:
            error = MockAPIError(message=msg)
            result = classify_api_error(error)
            # All should be classified as rate_limit if they have transient signals
            if any(signal in msg for signal in ["retry", "resets", "wait", "remaining"]):
                assert result.reason == FailoverReason.rate_limit, f"Failed for: {msg}"
            else:
                assert result.reason == FailoverReason.billing, f"Failed for: {msg}"


class TestMultimodalToolContent:
    """Test multimodal tool content unsupported patterns."""

    def test_multimodal_tool_content_error(self):
        """Test multimodal tool content unsupported error."""
        error = MockAPIError(
            status_code=400,
            message="Tool message content must be a string, got list",
        )
        result = classify_api_error(error)

        assert result.reason == FailoverReason.multimodal_tool_content_unsupported
        assert result.retryable is True

    def test_multimodal_tool_content_variants(self):
        """Test various multimodal tool content error messages."""
        variants = [
            "text is not set",
            "tool content must be a string",
            "tool message must be a string",
            "expected string, got array",
        ]

        for msg in variants:
            error = MockAPIError(status_code=400, message=msg)
            result = classify_api_error(error)
            assert result.reason == FailoverReason.multimodal_tool_content_unsupported


class TestRequestValidation:
    """Test request validation patterns."""

    def test_request_validation_error_502(self):
        """Test request validation error returned as 502."""
        error = MockAPIError(
            status_code=502,
            body={"error": {"code": "unknown_parameter"}},
            message="Bad gateway",
        )
        result = classify_api_error(error)

        # Should be classified as format_error, not server_error
        assert result.reason == FailoverReason.format_error
        assert result.retryable is False
        assert result.should_fallback is True

    def test_request_validation_patterns(self):
        """Test various request validation patterns."""
        patterns = [
            "unknown parameter 'temperature'",
            "unsupported parameter",
            "invalid_request_error",
        ]

        for msg in patterns:
            error = MockAPIError(status_code=500, message=msg)
            result = classify_api_error(error)
            # These should be detected as format errors
            assert result.reason == FailoverReason.format_error or result.should_fallback is True


class TestContextOverflowDetection:
    """Test context overflow detection improvements."""

    def test_generic_400_with_large_context(self):
        """Test generic 400 error with large context is context overflow."""
        error = MockAPIError(
            status_code=400,
            body={"error": {"message": "Error"}},
            message="Bad Request",
        )
        result = classify_api_error(
            error,
            approx_tokens=90000,
            context_length=200000,
            num_messages=100,
        )

        assert result.reason == FailoverReason.context_overflow
        assert result.should_compress is True

    def test_generic_400_with_small_context(self):
        """Test generic 400 error with small context is format error."""
        error = MockAPIError(
            status_code=400,
            body={"error": {"message": "Error"}},
            message="Bad Request",
        )
        result = classify_api_error(
            error,
            approx_tokens=1000,
            context_length=200000,
        )

        assert result.reason == FailoverReason.format_error
        assert result.retryable is False


class TestErrorCodeClassification:
    """Test error code classification."""

    def test_resource_exhausted_code(self):
        """Test resource_exhausted error code."""
        error = MockAPIError(
            body={"error": {"code": "resource_exhausted"}},
            message="Resource exhausted",
        )
        result = classify_api_error(error)

        assert result.reason == FailoverReason.rate_limit
        assert result.retryable is True

    def test_context_length_exceeded_code(self):
        """Test context_length_exceeded error code."""
        error = MockAPIError(
            body={"error": {"code": "context_length_exceeded"}},
            message="Context length exceeded",
        )
        result = classify_api_error(error)

        assert result.reason == FailoverReason.context_overflow
        assert result.should_compress is True

    def test_insufficient_quota_code(self):
        """Test insufficient_quota error code."""
        error = MockAPIError(
            body={"error": {"code": "insufficient_quota"}},
            message="Insufficient quota",
        )
        result = classify_api_error(error)

        assert result.reason == FailoverReason.billing
        assert result.retryable is False


class TestTransportErrorClassification:
    """Test transport error classification."""

    def test_connection_error_type(self):
        """Test ConnectionError type classification."""
        error = ConnectionError("Connection refused")

        result = classify_api_error(error)

        assert result.reason == FailoverReason.timeout
        assert result.retryable is True

    def test_timeout_error_type(self):
        """Test TimeoutError type classification."""
        error = TimeoutError("Request timed out")

        result = classify_api_error(error)

        assert result.reason == FailoverReason.timeout
        assert result.retryable is True

    def test_oserror_types(self):
        """Test OSError types classification."""
        os_error = OSError("Network is unreachable")

        result = classify_api_error(os_error)

        assert result.reason == FailoverReason.timeout
        assert result.retryable is True


class TestPayloadTooLarge:
    """Test payload too large patterns."""

    def test_payload_too_large_with_413(self):
        """Test 413 status code."""
        error = MockAPIError(
            status_code=413,
            message="Request Entity Too Large",
        )
        result = classify_api_error(error)

        assert result.reason == FailoverReason.payload_too_large
        assert result.should_compress is True

    def test_payload_too_large_without_status(self):
        """Test payload too large without status code."""
        error = MockAPIError(
            message="Request entity too large for the server",
        )
        result = classify_api_error(error)

        assert result.reason == FailoverReason.payload_too_large
        assert result.should_compress is True


class TestImageTooLarge:
    """Test image too large patterns."""

    def test_image_exceeds_5mb(self):
        """Test Anthropic image exceeds 5MB error."""
        error = MockAPIError(
            status_code=400,
            message="messages.0.content.1.image.source.base64: image exceeds 5 MB maximum",
        )
        result = classify_api_error(error)

        assert result.reason == FailoverReason.image_too_large
        assert result.retryable is True


class TestChinesePatterns:
    """Test Chinese error message patterns."""

    def test_chinese_billing_patterns(self):
        """Test Chinese billing patterns."""
        patterns = [
            "额度不足，请充值",
            "配额不足",
            "余额不足",
            "账户已停用",
        ]

        for msg in patterns:
            error = MockAPIError(message=msg)
            result = classify_api_error(error)
            assert result.reason == FailoverReason.billing

    def test_chinese_rate_limit_patterns(self):
        """Test Chinese rate limit patterns."""
        patterns = [
            "请求过于频繁，请稍后重试",
            "限流中",
            "请稍后再试",
        ]

        for msg in patterns:
            error = MockAPIError(message=msg)
            result = classify_api_error(error)
            assert result.reason == FailoverReason.rate_limit

    def test_chinese_context_overflow_patterns(self):
        """Test Chinese context overflow patterns."""
        patterns = [
            "上下文长度超出限制",
            "超过最大长度",
            "上下文过长",
        ]

        for msg in patterns:
            error = MockAPIError(message=msg)
            result = classify_api_error(error)
            assert result.reason == FailoverReason.context_overflow


class TestRecoveryHints:
    """Test recovery hint properties."""

    def test_auth_error_not_retryable(self):
        """Test auth errors are not directly retryable."""
        error = MockAPIError(
            status_code=401,
            message="Invalid API key",
        )
        result = classify_api_error(error)

        assert result.retryable is False
        assert result.should_rotate_credential is True
        assert result.should_fallback is True
        assert result.is_auth is True

    def test_rate_limit_should_fallback(self):
        """Test rate limit errors should fallback."""
        error = MockAPIError(
            status_code=429,
            message="Rate limit exceeded",
        )
        result = classify_api_error(error)

        assert result.should_rotate_credential is True
        assert result.should_fallback is True
        assert result.retryable is True

    def test_billing_not_retryable(self):
        """Test billing errors are not retryable."""
        error = MockAPIError(
            status_code=402,
            message="Insufficient credits",
        )
        result = classify_api_error(error)

        assert result.retryable is False
        assert result.should_rotate_credential is True
        assert result.should_fallback is True

    def test_context_overflow_should_compress(self):
        """Test context overflow should trigger compression."""
        error = MockAPIError(
            status_code=400,
            message="Context length exceeded",
        )
        result = classify_api_error(error)

        assert result.should_compress is True
        assert result.retryable is True


class TestErrorCauseChain:
    """Test error cause chain traversal."""

    def test_nested_error_with_status_code(self):
        """Test extracting status code from nested error."""
        @dataclass
        class InnerError(Exception):
            status_code: int = 500
            message: str = "Internal Server Error"

            def __str__(self):
                return self.message

        inner = InnerError()
        outer = Exception("Outer error")
        outer.__cause__ = inner

        result = classify_api_error(outer)

        assert result.status_code == 500
        assert result.reason == FailoverReason.server_error


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_error_message(self):
        """Test empty error message."""
        error = MockAPIError(message="")

        result = classify_api_error(error)

        assert result.reason == FailoverReason.unknown
        assert result.retryable is True

    def test_generic_error_short_message(self):
        """Test generic error with short message."""
        error = MockAPIError(message="Error")

        result = classify_api_error(error)

        # Should fall through to unknown
        assert result.reason in (FailoverReason.format_error, FailoverReason.unknown)

    def test_large_context_threshold_for_small_windows(self):
        """Test large context threshold for smaller context windows."""
        error = MockAPIError(
            status_code=400,
            body={"error": {"message": "Error"}},
            message="Bad Request",
        )

        # 256K context window: threshold is 120K tokens or 200 messages
        result = classify_api_error(
            error,
            approx_tokens=130000,
            context_length=256000,
            num_messages=50,
        )

        # Should trigger context overflow due to high token count
        assert result.reason == FailoverReason.context_overflow
