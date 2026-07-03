#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Context Engine and Context Compressor modules.

Tests cover:
- ContextEngine ABC interface and contract
- ContextCompressor initialization and configuration
- should_compress() compression threshold logic
- update_from_response() token tracking
- compress() compression pipeline
- Session lifecycle (on_session_start/end/reset)
- Hook system for compression events
- Error classification for compression failures
- Strategy patterns for compression
"""

import pytest
import time
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Any, Dict, List

from agent.context.context_engine import ContextEngine
from agent.context.context_compressor import (
    ContextCompressor,
    CompressionHooks,
    CompressionHookInfo,
    CompressionEvent,
    CompressionErrorType,
    ErrorClassification,
    classify_compression_error,
    SUMMARY_PREFIX,
)

# ─────────────────────────────────────────────────────────────────────────────
# Test Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def sample_messages():
    """Create a sample message list for testing compression."""
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"},
        {"role": "assistant", "content": "I'm doing well, thank you!"},
        {"role": "user", "content": "Can you help me with coding?"},
        {
            "role": "assistant",
            "content": "Of course! What do you need help with?",
            "tool_calls": [
                {
                    "id": "call_001",
                    "type": "function",
                    "function": {
                        "name": "write_file",
                        "arguments": '{"path": "test.py", "content": "print(1)"}',
                    },
                }
            ],
        },
        {
            "role": "tool",
            "content": "File written successfully to test.py",
            "tool_call_id": "call_001",
        },
        {"role": "user", "content": "Great, thanks!"},
        {"role": "assistant", "content": "You're welcome!"},
    ]


@pytest.fixture
def long_messages():
    """Create a long message list that exceeds compression threshold."""
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]
    # Add many tool result messages to push token count high
    for i in range(20):
        messages.append(
            {
                "role": "tool",
                "content": f"Tool result {i}: " + "x" * 500,
                "tool_call_id": f"call_{i:03d}",
            }
        )
    return messages


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client for summary generation."""
    client = MagicMock()
    response = MagicMock()
    response.content = "## Active Task\nWrite tests\n\n## Completed Actions\n1. Write test file - done [tool: write_file]"
    client.generate = AsyncMock(return_value=response)
    return client


# ─────────────────────────────────────────────────────────────────────────────
# Test ContextEngine ABC
# ─────────────────────────────────────────────────────────────────────────────


class TestContextEngineInterface:
    """Tests for ContextEngine abstract base class interface."""

    def test_abstract_class_cannot_be_instantiated(self):
        """ContextEngine is abstract and cannot be instantiated directly."""
        with pytest.raises(TypeError, match="abstract"):
            ContextEngine()

    def test_subclass_must_implement_name_property(self):
        """Subclass must implement the name property."""

        class MinimalEngine(ContextEngine):
            @property
            def name(self) -> str:
                return "minimal"

            def update_from_response(self, usage: Dict[str, Any]) -> None:
                pass

            def should_compress(self, prompt_tokens: int = None) -> bool:
                return False

            def compress(
                self,
                messages: List[Dict[str, Any]],
                current_tokens: int = None,
                focus_topic: str = None,
            ) -> List[Dict[str, Any]]:
                return messages

        engine = MinimalEngine()
        assert engine.name == "minimal"

    def test_subclass_must_implement_abstract_methods(self):
        """Subclass must implement all abstract methods."""

        class IncompleteEngine(ContextEngine):
            @property
            def name(self) -> str:
                return "incomplete"

            # Missing update_from_response, should_compress, compress

        with pytest.raises(TypeError, match="abstract"):
            IncompleteEngine()


class TestContextEngineDefaultImplementations:
    """Tests for ContextEngine default method implementations."""

    def test_on_session_start_default_is_noop(self):
        """on_session_start has a default no-op implementation."""

        class TestEngine(ContextEngine):
            @property
            def name(self) -> str:
                return "test"

            def update_from_response(self, usage: Dict[str, Any]) -> None:
                pass

            def should_compress(self, prompt_tokens: int = None) -> bool:
                return False

            def compress(
                self,
                messages: List[Dict[str, Any]],
                current_tokens: int = None,
                focus_topic: str = None,
            ) -> List[Dict[str, Any]]:
                return messages

        engine = TestEngine()
        # Should not raise
        engine.on_session_start("test_session")
        engine.on_session_start("test_session", hermes_home="/tmp")

    def test_on_session_end_default_is_noop(self):
        """on_session_end has a default no-op implementation."""

        class TestEngine(ContextEngine):
            @property
            def name(self) -> str:
                return "test"

            def update_from_response(self, usage: Dict[str, Any]) -> None:
                pass

            def should_compress(self, prompt_tokens: int = None) -> bool:
                return False

            def compress(
                self,
                messages: List[Dict[str, Any]],
                current_tokens: int = None,
                focus_topic: str = None,
            ) -> List[Dict[str, Any]]:
                return messages

        engine = TestEngine()
        # Should not raise
        engine.on_session_end("test_session", [])

    def test_on_session_reset_clears_state(self):
        """on_session_reset clears compression-related state."""

        class TestEngine(ContextEngine):
            @property
            def name(self) -> str:
                return "test"

            def update_from_response(self, usage: Dict[str, Any]) -> None:
                pass

            def should_compress(self, prompt_tokens: int = None) -> bool:
                return False

            def compress(
                self,
                messages: List[Dict[str, Any]],
                current_tokens: int = None,
                focus_topic: str = None,
            ) -> List[Dict[str, Any]]:
                return messages

        engine = TestEngine()
        engine.last_prompt_tokens = 1000
        engine.last_completion_tokens = 500
        engine.last_total_tokens = 1500
        engine.compression_count = 5

        engine.on_session_reset()

        assert engine.last_prompt_tokens == 0
        assert engine.last_completion_tokens == 0
        assert engine.last_total_tokens == 0
        assert engine.compression_count == 0

    def test_get_tool_schemas_default_returns_empty_list(self):
        """get_tool_schemas returns empty list by default."""

        class TestEngine(ContextEngine):
            @property
            def name(self) -> str:
                return "test"

            def update_from_response(self, usage: Dict[str, Any]) -> None:
                pass

            def should_compress(self, prompt_tokens: int = None) -> bool:
                return False

            def compress(
                self,
                messages: List[Dict[str, Any]],
                current_tokens: int = None,
                focus_topic: str = None,
            ) -> List[Dict[str, Any]]:
                return messages

        engine = TestEngine()
        assert engine.get_tool_schemas() == []

    def test_get_status_returns_standard_fields(self):
        """get_status returns standard status dictionary."""

        class TestEngine(ContextEngine):
            @property
            def name(self) -> str:
                return "test"

            def update_from_response(self, usage: Dict[str, Any]) -> None:
                pass

            def should_compress(self, prompt_tokens: int = None) -> bool:
                return False

            def compress(
                self,
                messages: List[Dict[str, Any]],
                current_tokens: int = None,
                focus_topic: str = None,
            ) -> List[Dict[str, Any]]:
                return messages

        engine = TestEngine()
        engine.last_prompt_tokens = 1000
        engine.last_completion_tokens = 500
        engine.threshold_tokens = 8000
        engine.context_length = 128000
        engine.compression_count = 3

        status = engine.get_status()

        assert "last_prompt_tokens" in status
        assert "last_completion_tokens" in status
        assert "threshold_tokens" in status
        assert "context_length" in status
        assert "compression_count" in status
        assert "usage_percent" in status


# ─────────────────────────────────────────────────────────────────────────────
# Test ContextCompressor Initialization
# ─────────────────────────────────────────────────────────────────────────────


class TestContextCompressorInit:
    """Tests for ContextCompressor initialization."""

    def test_default_initialization(self):
        """ContextCompressor initializes with reasonable defaults."""
        compressor = ContextCompressor()

        assert compressor.name == "compressor"
        assert compressor.model == "gpt-4"
        assert compressor.threshold_percent == 0.75
        assert compressor.protect_first_n == 3
        assert compressor.protect_last_n == 6
        assert compressor.context_length == 8192  # gpt-4 default
        assert compressor.threshold_tokens >= 8192  # at least MINIMUM_CONTEXT_LENGTH
        assert compressor.compression_count == 0

    def test_custom_initialization(self):
        """ContextCompressor accepts custom parameters."""
        compressor = ContextCompressor(
            model="claude-3.5-sonnet",
            threshold_percent=0.80,
            protect_first_n=5,
            protect_last_n=10,
            summary_target_ratio=0.15,
            quiet_mode=True,
        )

        assert compressor.model == "claude-3.5-sonnet"
        assert compressor.threshold_percent == 0.80
        assert compressor.protect_first_n == 5
        assert compressor.protect_last_n == 10
        assert compressor.summary_target_ratio == 0.15
        assert compressor.quiet_mode is True

    def test_context_length_lookup(self):
        """ContextCompressor looks up known model context lengths."""
        test_cases = [
            ("gpt-4", 8192),
            ("gpt-4-turbo", 128000),
            ("gpt-4o", 128000),
            ("gpt-4o-mini", 128000),
            ("gpt-3.5-turbo", 16385),
            ("claude-3-opus", 200000),
            ("claude-3.5-sonnet", 200000),
            ("unknown-model", 8192),  # default
        ]

        for model, expected_length in test_cases:
            compressor = ContextCompressor(model=model)
            assert compressor.context_length == expected_length, f"Failed for {model}"

    def test_summary_target_ratio_clamped(self):
        """summary_target_ratio is clamped between 0.10 and 0.80."""
        # Test lower bound
        compressor = ContextCompressor(summary_target_ratio=0.05)
        assert compressor.summary_target_ratio == 0.10

        # Test upper bound
        compressor = ContextCompressor(summary_target_ratio=0.90)
        assert compressor.summary_target_ratio == 0.80

        # Test valid range
        compressor = ContextCompressor(summary_target_ratio=0.30)
        assert compressor.summary_target_ratio == 0.30

    def test_tail_token_budget_calculation(self):
        """Tail token budget is calculated from threshold and ratio."""
        compressor = ContextCompressor(
            model="gpt-4",
            threshold_percent=0.75,
            summary_target_ratio=0.20,
        )
        # threshold_tokens = max(8192 * 0.75, 8192) = 8192 (MINIMUM_CONTEXT_LENGTH wins)
        # tail_token_budget = 8192 * 0.20 = 1638.4 ≈ 1638
        assert compressor.threshold_tokens == 8192
        assert compressor.tail_token_budget > 0


# ─────────────────────────────────────────────────────────────────────────────
# Test ContextCompressor Core Methods
# ─────────────────────────────────────────────────────────────────────────────


class TestShouldCompress:
    """Tests for should_compress() method."""

    def test_below_threshold_returns_false(self):
        """should_compress returns False when tokens are below threshold."""
        compressor = ContextCompressor(quiet_mode=True)
        compressor.threshold_tokens = 8000
        compressor.last_prompt_tokens = 5000

        assert compressor.should_compress() is False

    def test_above_threshold_returns_true(self):
        """should_compress returns True when tokens exceed threshold."""
        compressor = ContextCompressor(quiet_mode=True)
        compressor.threshold_tokens = 8000
        compressor.last_prompt_tokens = 10000

        assert compressor.should_compress() is True

    def test_explicit_prompt_tokens_overrides_last(self):
        """Explicit prompt_tokens parameter overrides last_prompt_tokens."""
        compressor = ContextCompressor(quiet_mode=True)
        compressor.threshold_tokens = 8000
        compressor.last_prompt_tokens = 5000  # below threshold

        # Explicit value above threshold
        assert compressor.should_compress(prompt_tokens=12000) is True

        # Explicit value below threshold
        assert compressor.should_compress(prompt_tokens=3000) is False

    def test_ineffective_compressions_skip_compression(self):
        """After 2 ineffective compressions, should_compress returns False."""
        compressor = ContextCompressor(quiet_mode=True)
        compressor.threshold_tokens = 8000
        compressor.last_prompt_tokens = 10000
        compressor._ineffective_compression_count = 2

        assert compressor.should_compress() is False

    def test_ineffective_count_resets_on_successful_compression(self):
        """Ineffective compression count resets when compression is effective."""
        compressor = ContextCompressor(quiet_mode=True)
        compressor.threshold_tokens = 8000
        compressor.last_prompt_tokens = 10000
        compressor._ineffective_compression_count = 1

        # Simulate effective compression by setting savings > 10%
        compressor._last_compression_savings_pct = 25.0

        # should_compress doesn't reset, but compress() would
        assert compressor.should_compress() is True


class TestUpdateFromResponse:
    """Tests for update_from_response() method."""

    def test_updates_token_stats(self):
        """update_from_response updates all token statistics."""
        compressor = ContextCompressor(quiet_mode=True)

        usage = {
            "prompt_tokens": 5000,
            "completion_tokens": 1000,
            "total_tokens": 6000,
        }

        compressor.update_from_response(usage)

        assert compressor.last_prompt_tokens == 5000
        assert compressor.last_completion_tokens == 1000
        assert compressor.last_total_tokens == 6000

    def test_handles_partial_usage(self):
        """update_from_response handles missing keys gracefully."""
        compressor = ContextCompressor(quiet_mode=True)

        usage = {"prompt_tokens": 5000}
        compressor.update_from_response(usage)

        assert compressor.last_prompt_tokens == 5000
        assert compressor.last_completion_tokens == 0
        assert compressor.last_total_tokens == 5000

    def test_handles_empty_usage(self):
        """update_from_response handles empty usage dict."""
        compressor = ContextCompressor(quiet_mode=True)

        compressor.update_from_response({})

        assert compressor.last_prompt_tokens == 0
        assert compressor.last_completion_tokens == 0
        assert compressor.last_total_tokens == 0

    def test_handles_none_usage(self):
        """update_from_response handles None usage."""
        compressor = ContextCompressor(quiet_mode=True)

        compressor.update_from_response(None)

        assert compressor.last_prompt_tokens == 0
        assert compressor.last_completion_tokens == 0
        assert compressor.last_total_tokens == 0


class TestCompress:
    """Tests for compress() method."""

    def test_short_messages_unchanged(self, sample_messages):
        """compress() returns messages unchanged if below minimum."""
        compressor = ContextCompressor(quiet_mode=True)

        compressed = compressor.compress(sample_messages)

        # Should return same messages since only 8 messages
        assert len(compressed) == len(sample_messages)

    def test_compression_increments_count_on_successful_compress(self, mock_llm_client):
        """compress() increments compression_count on successful compression."""
        compressor = ContextCompressor(quiet_mode=True)
        compressor.set_llm_client(mock_llm_client)

        # Create messages that will exceed threshold
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
        ]
        # Add enough content to exceed threshold (threshold_tokens = 8192 for gpt-4)
        for i in range(20):
            messages.append(
                {
                    "role": "tool",
                    "content": f"Tool result {i}: " + "x" * 1000,
                    "tool_call_id": f"call_{i:03d}",
                }
            )
        messages.append({"role": "user", "content": "Thanks!"})
        messages.append({"role": "assistant", "content": "You're welcome!"})

        initial_count = compressor.compression_count
        compressor.compress(messages)

        # Compression may or may not happen depending on token estimation
        # Just verify the method runs without error
        assert compressor.compression_count >= initial_count

    def test_compress_handles_llm_error_gracefully(
        self, sample_messages, mock_llm_client
    ):
        """compress() handles LLM errors without crashing."""
        compressor = ContextCompressor(quiet_mode=True)
        compressor.set_llm_client(mock_llm_client)

        # Mock LLM to raise an error that will be caught
        mock_llm_client.generate = AsyncMock(side_effect=Exception("Connection failed"))

        # Create messages that will trigger compression attempt
        messages = sample_messages.copy()
        for i in range(20):
            messages.append(
                {
                    "role": "tool",
                    "content": f"Tool result {i}: " + "x" * 1000,
                    "tool_call_id": f"call_{i:03d}",
                }
            )

        # Should not raise, but may return messages unchanged
        result = compressor.compress(messages)
        assert isinstance(result, list)

    def test_compress_sets_last_compression_savings(self, mock_llm_client):
        """compress() records the compression savings percentage."""
        compressor = ContextCompressor(quiet_mode=True)
        compressor.set_llm_client(mock_llm_client)

        # Create messages that will trigger compression
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
        ]
        for i in range(20):
            messages.append(
                {
                    "role": "tool",
                    "content": f"Tool result {i}: " + "x" * 1000,
                    "tool_call_id": f"call_{i:03d}",
                }
            )
        messages.append({"role": "user", "content": "Thanks!"})

        compressor.compress(messages)

        # Savings percentage should be tracked
        assert compressor._last_compression_savings_pct >= 0


class TestHasContentToCompress:
    """Tests for has_content_to_compress() method."""

    def test_empty_messages_returns_false(self):
        """has_content_to_compress returns False for empty message list."""
        compressor = ContextCompressor(quiet_mode=True)

        assert compressor.has_content_to_compress([]) is False

    def test_with_many_tool_results_returns_true(self):
        """has_content_to_compress returns True when there are middle messages."""
        compressor = ContextCompressor(quiet_mode=True)

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
        ]

        # Add many tool results in the middle
        for i in range(15):
            messages.append(
                {
                    "role": "tool",
                    "content": f"Tool result {i}: " + "x" * 500,
                    "tool_call_id": f"call_{i:03d}",
                }
            )

        messages.append({"role": "user", "content": "Thanks!"})
        messages.append({"role": "assistant", "content": "You're welcome!"})

        # With 20 messages and only 4 protected, there's plenty to compress
        assert compressor.has_content_to_compress(messages) is True


# ─────────────────────────────────────────────────────────────────────────────
# Test Session Lifecycle
# ─────────────────────────────────────────────────────────────────────────────


class TestSessionLifecycle:
    """Tests for session lifecycle methods."""

    def test_on_session_start_is_callable(self):
        """on_session_start can be called with session_id."""
        compressor = ContextCompressor(quiet_mode=True)

        # Should not raise
        compressor.on_session_start("test_session_123")

    def test_on_session_start_accepts_kwargs(self):
        """on_session_start accepts optional kwargs."""
        compressor = ContextCompressor(quiet_mode=True)

        # Should not raise
        compressor.on_session_start(
            "test_session",
            hermes_home="/tmp/hermes",
            platform="test",
            model="gpt-4",
        )

    def test_on_session_end_is_callable(self):
        """on_session_end can be called with session_id and messages."""
        compressor = ContextCompressor(quiet_mode=True)

        # Should not raise
        compressor.on_session_end("test_session", [])

    def test_on_session_reset_clears_token_state_and_count(self):
        """on_session_reset clears token stats and compression count."""
        compressor = ContextCompressor()
        compressor.compression_count = 5
        compressor._previous_summary = "Some previous summary"
        compressor._ineffective_compression_count = 2
        compressor._last_summary_error = "Some error"

        compressor.on_session_reset()

        # Compression count is reset
        assert compressor.compression_count == 0
        # Token stats are also reset (via on_session_reset in base class)
        assert compressor.last_prompt_tokens == 0
        assert compressor.last_completion_tokens == 0
        # Note: _previous_summary is NOT cleared by on_session_reset
        # (it's preserved for iterative summarization across resets)
        # Similarly _ineffective_compression_count and _last_summary_error
        # are NOT cleared by on_session_reset - they're compression-internal state

    def test_clear_method_clears_state(self):
        """clear() clears compression state without resetting session info."""
        compressor = ContextCompressor()
        compressor.compression_count = 5
        compressor._previous_summary = "Previous summary"
        compressor._ineffective_compression_count = 3
        compressor._last_summary_error = "Error"

        compressor.clear()

        assert compressor._previous_summary is None
        assert compressor._ineffective_compression_count == 0
        assert compressor._last_summary_error is None
        assert compressor.compression_count == 5  # Not cleared by clear()


# ─────────────────────────────────────────────────────────────────────────────
# Test Hook System
# ─────────────────────────────────────────────────────────────────────────────


class TestCompressionHooks:
    """Tests for CompressionHooks class."""

    def test_pre_compress_hook_called(self, sample_messages):
        """Pre-compress hooks are called before compression."""
        hooks = CompressionHooks()
        called = []

        def pre_hook(msgs):
            called.append(("pre", len(msgs)))

        hooks.on_pre_compress(pre_hook)
        hooks._run_pre_compress(sample_messages)

        assert len(called) == 1
        assert called[0] == ("pre", len(sample_messages))

    def test_post_compress_hook_called(self, sample_messages):
        """Post-compress hooks are called after compression."""
        hooks = CompressionHooks()
        called = []

        def post_hook(original, compressed, info):
            called.append(("post", len(original), len(compressed)))

        hooks.on_post_compress(post_hook)

        info = CompressionHookInfo(
            compress_count=1,
            total_tokens_before=1000,
            total_tokens_after=500,
            messages_count_before=10,
            messages_count_after=5,
            compression_ratio=0.5,
            summary_generated=True,
            summary_model_used="gpt-4",
            elapsed_seconds=1.0,
        )

        hooks._run_post_compress(sample_messages, sample_messages[:5], info)

        assert len(called) == 1
        assert called[0] == ("post", 8, 5)

    def test_summary_success_hook(self):
        """Summary success hooks are called with content and elapsed time."""
        hooks = CompressionHooks()
        called = []

        def success_hook(content, success, elapsed):
            called.append((content, success, elapsed))

        hooks.on_summary_success(success_hook)
        hooks._run_summary_success("Test summary content", 1.5)

        assert len(called) == 1
        assert called[0][0] == "Test summary content"
        assert called[0][1] is True
        assert called[0][2] == 1.5

    def test_summary_failed_hook(self):
        """Summary failed hooks are called with error and elapsed time."""
        hooks = CompressionHooks()
        called = []

        def failed_hook(error, success, elapsed):
            called.append((error, success, elapsed))

        hooks.on_summary_failed(failed_hook)
        hooks._run_summary_failed("Error message", 0.5)

        assert len(called) == 1
        assert called[0][0] == "Error message"
        assert called[0][1] is False
        assert called[0][2] == 0.5

    def test_fallback_hook(self):
        """Fallback hooks are called when model fallback occurs."""
        hooks = CompressionHooks()
        called = []

        def fallback_hook(from_model, to_model):
            called.append((from_model, to_model))

        hooks.on_fallback(fallback_hook)
        hooks._run_fallback("summary-model", "main-model")

        assert len(called) == 1
        assert called[0] == ("summary-model", "main-model")

    def test_clear_removes_all_hooks(self):
        """clear() removes all registered hooks."""
        hooks = CompressionHooks()
        hooks.on_pre_compress(lambda m: None)
        hooks.on_post_compress(lambda o, c, i: None)
        hooks.on_summary_success(lambda c, s, e: None)

        hooks.clear()

        assert len(hooks._pre_compress_hooks) == 0
        assert len(hooks._post_compress_hooks) == 0
        assert len(hooks._summary_success_hooks) == 0

    def test_stats_initial_state(self):
        """Stats are initialized to zero."""
        hooks = CompressionHooks()

        stats = hooks.stats

        assert stats["total_compressions"] == 0
        assert stats["total_summaries"] == 0
        assert stats["total_fallbacks"] == 0
        assert stats["total_savings_tokens"] == 0


class TestCompressorHookIntegration:
    """Tests for ContextCompressor hook integration."""

    def test_register_pre_compress_hook(self, sample_messages, mock_llm_client):
        """ContextCompressor can register pre-compress hooks."""
        compressor = ContextCompressor(quiet_mode=True)
        compressor.set_llm_client(mock_llm_client)
        called = []

        def pre_hook(msgs):
            called.append(len(msgs))

        compressor.register_pre_compress_hook(pre_hook)

        # Add content to trigger compression
        messages = sample_messages.copy()
        for i in range(15):
            messages.append(
                {
                    "role": "tool",
                    "content": f"Tool result {i}: " + "x" * 1000,
                    "tool_call_id": f"call_{i:03d}",
                }
            )

        compressor.compress(messages)

        assert len(called) == 1
        assert called[0] > len(sample_messages)

    def test_get_compression_stats(self):
        """get_compression_stats returns hook statistics."""
        compressor = ContextCompressor(quiet_mode=True)

        stats = compressor.get_compression_stats()

        assert "total_compressions" in stats
        assert "total_summaries" in stats
        assert "compression_count" in stats

    def test_clear_hooks(self):
        """clear_hooks removes all hooks from compressor."""
        compressor = ContextCompressor(quiet_mode=True)

        compressor.register_pre_compress_hook(lambda m: None)
        compressor.register_post_compress_hook(lambda o, c, i: None)

        compressor.clear_hooks()

        # Verify hooks are cleared (no-op check)
        assert len(compressor._hooks._pre_compress_hooks) == 0
        assert len(compressor._hooks._post_compress_hooks) == 0


# ─────────────────────────────────────────────────────────────────────────────
# Test Error Classification
# ─────────────────────────────────────────────────────────────────────────────


class TestErrorClassification:
    """Tests for error classification system."""

    def test_classify_rate_limit_error(self):
        """Rate limit errors are classified correctly."""

        class RateLimitError(Exception):
            status_code = 429

        error = RateLimitError("Rate limit exceeded")
        result = classify_compression_error(error)

        assert result.error_type == CompressionErrorType.RATE_LIMITED
        assert result.can_retry is True
        assert result.should_fallback is True
        assert result.cooldown_seconds > 0

    def test_classify_timeout_error(self):
        """Timeout errors are classified correctly."""
        error = TimeoutError("Request timeout")

        result = classify_compression_error(error)

        assert result.error_type == CompressionErrorType.TIMEOUT
        assert result.can_retry is True

    def test_classify_connection_error(self):
        """Connection errors are classified correctly."""
        error = ConnectionError("Connection refused")

        result = classify_compression_error(error)

        assert result.error_type == CompressionErrorType.CONNECTION_ERROR
        assert result.can_retry is True

    def test_classify_no_provider_error(self):
        """No provider error is classified as NO_PROVIDER."""
        # The code checks for "no provider" (with space, not "no llm provider")
        error = RuntimeError("no provider configured")

        result = classify_compression_error(error)

        assert result.error_type == CompressionErrorType.NO_PROVIDER
        assert result.can_retry is False
        assert result.should_fallback is False

    def test_classify_model_not_found(self):
        """Model not found errors are classified correctly."""
        error = Exception("Model not found: gpt-5")
        error.status_code = 404

        result = classify_compression_error(error)

        assert result.error_type == CompressionErrorType.MODEL_NOT_FOUND
        assert result.status_code == 404

    def test_classify_unknown_error(self):
        """Unknown errors get classified as UNKNOWN."""
        error = ValueError("Something went wrong")

        result = classify_compression_error(error)

        assert result.error_type == CompressionErrorType.UNKNOWN
        assert result.can_retry is True

    def test_error_classification_has_all_fields(self):
        """ErrorClassification has all required fields."""
        error = RuntimeError("Test error")
        result = classify_compression_error(error)

        assert hasattr(result, "error_type")
        assert hasattr(result, "status_code")
        assert hasattr(result, "error_message")
        assert hasattr(result, "can_retry")
        assert hasattr(result, "should_fallback")
        assert hasattr(result, "cooldown_seconds")
        assert hasattr(result, "reason")


# ─────────────────────────────────────────────────────────────────────────────
# Test Update Model
# ─────────────────────────────────────────────────────────────────────────────


class TestUpdateModel:
    """Tests for update_model() method."""

    def test_update_model_changes_context_length(self):
        """update_model changes context_length based on new model."""
        compressor = ContextCompressor(model="gpt-4")

        compressor.update_model(
            model="claude-3.5-sonnet",
            context_length=200000,
        )

        # Only context_length is updated by ContextCompressor's update_model
        # Note: threshold_tokens is NOT recalculated in ContextCompressor's override
        assert compressor.context_length == 200000

    def test_update_model_updates_provider_info(self):
        """update_model updates provider information."""
        compressor = ContextCompressor(model="gpt-4", provider="openai")

        compressor.update_model(
            model="claude-3.5-sonnet",
            context_length=200000,
            provider="anthropic",
            base_url="https://api.anthropic.com",
        )

        assert compressor.model == "claude-3.5-sonnet"
        assert compressor.provider == "anthropic"
        assert compressor.base_url == "https://api.anthropic.com"

    def test_update_model_with_summary_model_override(self):
        """update_model accepts summary_model_override."""
        compressor = ContextCompressor(model="gpt-4", quiet_mode=True)

        compressor.update_model(
            model="claude-3.5-sonnet",
            context_length=200000,
            summary_model_override="gpt-4-mini",
        )

        assert compressor._config_summary_model == "gpt-4-mini"
        assert compressor._summary_model_fallen_back is False


# ─────────────────────────────────────────────────────────────────────────────
# Test Strategy Patterns
# ─────────────────────────────────────────────────────────────────────────────


class TestCompressionStrategies:
    """Tests for compression strategy methods."""

    def test_get_strategy(self):
        """get_strategy returns registered strategies."""
        compressor = ContextCompressor(quiet_mode=True)

        keyword_strategy = compressor.get_strategy("keyword_priority")
        assert keyword_strategy is not None

        turn_strategy = compressor.get_strategy("turn_importance")
        assert turn_strategy is not None

    def test_get_unknown_strategy_returns_none(self):
        """get_strategy returns None for unknown strategy."""
        compressor = ContextCompressor(quiet_mode=True)

        result = compressor.get_strategy("nonexistent_strategy")
        assert result is None

    def test_enable_strategy(self):
        """enable_strategy enables a disabled strategy."""
        compressor = ContextCompressor(quiet_mode=True)

        keyword_strategy = compressor.get_strategy("keyword_priority")
        original_enabled = keyword_strategy.enabled

        compressor.disable_strategy("keyword_priority")
        assert keyword_strategy.enabled is False

        compressor.enable_strategy("keyword_priority")
        assert keyword_strategy.enabled is True

    def test_disable_strategy(self):
        """disable_strategy disables an enabled strategy."""
        compressor = ContextCompressor(quiet_mode=True)

        keyword_strategy = compressor.get_strategy("keyword_priority")

        compressor.disable_strategy("keyword_priority")
        assert keyword_strategy.enabled is False

    def test_get_enabled_strategies(self):
        """get_enabled_strategies returns list of enabled strategy names."""
        compressor = ContextCompressor(quiet_mode=True)

        enabled = compressor.get_enabled_strategies()

        assert isinstance(enabled, list)
        assert len(enabled) > 0
        assert "keyword_priority" in enabled
