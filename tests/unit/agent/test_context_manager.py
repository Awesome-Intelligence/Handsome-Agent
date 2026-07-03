#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Context Manager module.

Tests cover:
- ContextPurpose enum
- BuildPartsResult and BuildMessagesResult dataclasses
- ContextManager initialization
- Delegation to ContextCompressor and ContextBuilder
- Memory management methods
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Dict, List, Any

from agent.context.context_manager import (
    ContextManager,
    ContextPurpose,
    BuildPartsResult,
    BuildMessagesResult,
)

# ─────────────────────────────────────────────────────────────────────────────
# Test ContextPurpose Enum
# ─────────────────────────────────────────────────────────────────────────────


class TestContextPurpose:
    """Tests for ContextPurpose enum."""

    def test_context_purpose_values(self):
        """ContextPurpose has all expected values."""
        assert ContextPurpose.MODE_DECISION.value == "mode_decision"
        assert ContextPurpose.TOOL_SELECTION.value == "tool_selection"
        assert ContextPurpose.DIRECT_RESPONSE.value == "direct_response"
        assert ContextPurpose.CLARIFICATION.value == "clarification"
        assert ContextPurpose.TOOL_RESULT_SUMMARY.value == "tool_result_summary"
        assert ContextPurpose.AGENT_LOOP.value == "agent_loop"
        assert ContextPurpose.MESSAGES_BUILD.value == "messages_build"

    def test_context_purpose_is_string_enum(self):
        """ContextPurpose values are strings."""
        for purpose in ContextPurpose:
            assert isinstance(purpose.value, str)


# ─────────────────────────────────────────────────────────────────────────────
# Test BuildPartsResult
# ─────────────────────────────────────────────────────────────────────────────


class TestBuildPartsResult:
    """Tests for BuildPartsResult dataclass."""

    def test_build_parts_result_creation(self):
        """BuildPartsResult creates with required fields."""
        result = BuildPartsResult(
            parts={"stable": "system", "context": "", "volatile": ""},
            user_message="Hello",
            compressed=False,
            original_count=1,
            compressed_count=1,
            purpose=ContextPurpose.DIRECT_RESPONSE,
        )

        assert result.parts["stable"] == "system"
        assert result.user_message == "Hello"
        assert result.compressed is False
        assert result.original_count == 1
        assert result.compressed_count == 1
        assert result.purpose == ContextPurpose.DIRECT_RESPONSE

    def test_build_parts_result_with_compression(self):
        """BuildPartsResult tracks compression."""
        result = BuildPartsResult(
            parts={"stable": "system", "context": "", "volatile": ""},
            user_message="Hello",
            compressed=True,
            original_count=10,
            compressed_count=5,
            purpose=ContextPurpose.AGENT_LOOP,
        )

        assert result.compressed is True
        assert result.original_count == 10
        assert result.compressed_count == 5


# ─────────────────────────────────────────────────────────────────────────────
# Test BuildMessagesResult
# ─────────────────────────────────────────────────────────────────────────────


class TestBuildMessagesResult:
    """Tests for BuildMessagesResult dataclass."""

    def test_build_messages_result_creation(self):
        """BuildMessagesResult creates with required fields."""
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
        ]
        result = BuildMessagesResult(
            messages=messages,
            compressed=False,
            original_count=2,
            compressed_count=2,
            purpose=ContextPurpose.DIRECT_RESPONSE,
        )

        assert len(result.messages) == 2
        assert result.compressed is False
        assert result.original_count == 2
        assert result.compressed_count == 2
        assert result.purpose == ContextPurpose.DIRECT_RESPONSE

    def test_build_messages_result_with_compression(self):
        """BuildMessagesResult tracks compression."""
        messages = [{"role": "system", "content": "System"}]
        result = BuildMessagesResult(
            messages=messages,
            compressed=True,
            original_count=20,
            compressed_count=5,
            purpose=ContextPurpose.AGENT_LOOP,
        )

        assert result.compressed is True
        assert result.original_count == 20
        assert result.compressed_count == 5


# ─────────────────────────────────────────────────────────────────────────────
# Test ContextManager Initialization
# ─────────────────────────────────────────────────────────────────────────────


class TestContextManagerInit:
    """Tests for ContextManager initialization."""

    def test_default_initialization(self):
        """ContextManager initializes with None dependencies."""
        manager = ContextManager()

        assert manager._context_compressor is None
        assert manager._context_builder is None
        assert manager._memory_manager is None

    def test_initialization_with_compressor(self):
        """ContextManager accepts context_compressor."""
        mock_compressor = MagicMock()
        manager = ContextManager(context_compressor=mock_compressor)

        assert manager._context_compressor is mock_compressor

    def test_initialization_with_builder(self):
        """ContextManager accepts context_builder."""
        mock_builder = MagicMock()
        manager = ContextManager(context_builder=mock_builder)

        assert manager._context_builder is mock_builder

    def test_initialization_with_memory_manager(self):
        """ContextManager accepts memory_manager."""
        mock_memory = MagicMock()
        manager = ContextManager(memory_manager=mock_memory)

        assert manager._memory_manager is mock_memory

    def test_initialization_with_all_dependencies(self):
        """ContextManager accepts all dependencies."""
        mock_compressor = MagicMock()
        mock_builder = MagicMock()
        mock_memory = MagicMock()

        manager = ContextManager(
            context_compressor=mock_compressor,
            context_builder=mock_builder,
            memory_manager=mock_memory,
        )

        assert manager._context_compressor is mock_compressor
        assert manager._context_builder is mock_builder
        assert manager._memory_manager is mock_memory


# ─────────────────────────────────────────────────────────────────────────────
# Test ContextManager Properties
# ─────────────────────────────────────────────────────────────────────────────


class TestContextManagerProperties:
    """Tests for ContextManager properties."""

    def test_compressor_property(self):
        """compressor property returns the compressor."""
        mock_compressor = MagicMock()
        manager = ContextManager(context_compressor=mock_compressor)

        assert manager.compressor is mock_compressor

    def test_compressor_property_returns_none_when_not_set(self):
        """compressor property returns None when not set."""
        manager = ContextManager()

        assert manager.compressor is None

    def test_builder_property(self):
        """builder property returns the builder."""
        mock_builder = MagicMock()
        manager = ContextManager(context_builder=mock_builder)

        assert manager.builder is mock_builder

    def test_builder_property_returns_none_when_not_set(self):
        """builder property returns None when not set."""
        manager = ContextManager()

        assert manager.builder is None


# ─────────────────────────────────────────────────────────────────────────────
# Test ContextManager Setters
# ─────────────────────────────────────────────────────────────────────────────


class TestContextManagerSetters:
    """Tests for ContextManager setter methods."""

    def test_set_context_compressor(self):
        """set_context_compressor() updates the compressor."""
        manager = ContextManager()
        mock_compressor = MagicMock()

        manager.set_context_compressor(mock_compressor)

        assert manager._context_compressor is mock_compressor

    def test_set_context_builder(self):
        """set_context_builder() updates the builder."""
        manager = ContextManager()
        mock_builder = MagicMock()

        manager.set_context_builder(mock_builder)

        assert manager._context_builder is mock_builder

    def test_set_memory_manager(self):
        """set_memory_manager() updates the memory manager."""
        manager = ContextManager()
        mock_memory = MagicMock()

        manager.set_memory_manager(mock_memory)

        assert manager._memory_manager is mock_memory


# ─────────────────────────────────────────────────────────────────────────────
# Test Compression Delegation
# ─────────────────────────────────────────────────────────────────────────────


class TestCompressionDelegation:
    """Tests for compression delegation to ContextCompressor."""

    def test_should_compress_delegates_to_compressor(self):
        """should_compress() returns compressor's decision."""
        mock_compressor = MagicMock()
        mock_compressor.should_compress = MagicMock(return_value=True)
        manager = ContextManager(context_compressor=mock_compressor)

        result = manager.should_compress(estimated_tokens=10000)

        mock_compressor.should_compress.assert_called_once_with(10000)
        assert result is True

    def test_should_compress_returns_false_when_no_compressor(self):
        """should_compress() returns False when no compressor is set."""
        manager = ContextManager()

        result = manager.should_compress(estimated_tokens=10000)

        assert result is False

    def test_get_compression_stats_delegates(self):
        """get_compression_stats() returns compressor stats."""
        mock_compressor = MagicMock()
        mock_compressor.get_compression_stats = MagicMock(
            return_value={"total_compressions": 5}
        )
        manager = ContextManager(context_compressor=mock_compressor)

        result = manager.get_compression_stats()

        mock_compressor.get_compression_stats.assert_called_once()
        assert result == {"total_compressions": 5}

    def test_get_compression_stats_returns_empty_when_no_compressor(self):
        """get_compression_stats() returns empty dict when no compressor."""
        manager = ContextManager()

        result = manager.get_compression_stats()

        assert result == {}


# ─────────────────────────────────────────────────────────────────────────────
# Test Memory Methods
# ─────────────────────────────────────────────────────────────────────────────


class TestMemoryMethods:
    """Tests for memory-related methods."""

    def test_get_memory_snapshot_returns_empty_when_no_memory_manager(self):
        """_get_memory_snapshot() returns empty string when no memory manager."""
        manager = ContextManager()

        result = manager._get_memory_snapshot()

        assert result == ""

    def test_get_memory_snapshot_returns_memory_content(self):
        """_get_memory_snapshot() returns memory content when manager is set."""
        mock_memory = MagicMock()
        mock_memory.build_system_prompt = MagicMock(
            return_value="User profile and memories"
        )
        manager = ContextManager(memory_manager=mock_memory)

        result = manager._get_memory_snapshot()

        assert "<memory-context>" in result
        assert "User profile and memories" in result

    def test_get_memory_snapshot_handles_exception(self):
        """_get_memory_snapshot() handles memory manager exceptions."""
        mock_memory = MagicMock()
        mock_memory.build_system_prompt = MagicMock(
            side_effect=Exception("Memory error")
        )
        manager = ContextManager(memory_manager=mock_memory)

        result = manager._get_memory_snapshot()

        # Should return empty string on exception
        assert result == ""

    def test_get_memory_prefetch_context_returns_empty_when_no_memory_manager(self):
        """_get_memory_prefetch_context() returns empty when no memory manager."""
        manager = ContextManager()

        result = manager._get_memory_prefetch_context([])

        assert result == ""

    def test_memory_prefetch_context_calls_on_pre_compress(self):
        """_get_memory_prefetch_context() calls memory manager's on_pre_compress."""
        mock_memory = MagicMock()
        mock_memory.on_pre_compress = MagicMock(return_value="prefetch context")
        manager = ContextManager(memory_manager=mock_memory)

        messages = [{"role": "user", "content": "Hello"}]
        result = manager._get_memory_prefetch_context(messages)

        mock_memory.on_pre_compress.assert_called_once_with(messages)
        assert result == "prefetch context"

    def test_memory_prefetch_context_handles_exception(self):
        """_get_memory_prefetch_context() handles exceptions gracefully."""
        mock_memory = MagicMock()
        mock_memory.on_pre_compress = MagicMock(side_effect=Exception("Error"))
        manager = ContextManager(memory_manager=mock_memory)

        result = manager._get_memory_prefetch_context([])

        # Should return empty string on exception
        assert result == ""


# ─────────────────────────────────────────────────────────────────────────────
# Test Context Files Loading
# ─────────────────────────────────────────────────────────────────────────────


class TestContextFilesLoading:
    """Tests for context files loading."""

    def test_get_context_files_returns_content(self):
        """_get_context_files() returns content when files exist."""
        manager = ContextManager()

        # The method returns content (either from files or default template)
        result = manager._get_context_files()
        # Should return some content
        assert isinstance(result, (str, tuple, list))

    def test_context_files_loaded_list_is_accessible(self):
        """_context_files_loaded is a class variable accessible via instance."""
        manager = ContextManager()

        # Initially empty list
        assert hasattr(manager, "_context_files_loaded")
        assert isinstance(manager._context_files_loaded, list)
