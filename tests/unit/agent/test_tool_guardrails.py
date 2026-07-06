#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Tool Guardrails.

Tests the tool-call loop detection mechanisms:
- Exact failure detection (same tool + same args)
- Same-tool failure detection (same tool, different args)
- Idempotent tool no-progress detection
"""

import pytest

from agent.rails.tool_guardrails import (
    ToolCallGuardrailConfig,
    ToolCallSignature,
    ToolGuardrailDecision,
    ToolCallGuardrailController,
    classify_tool_failure,
    canonical_tool_args,
    IDEMPOTENT_TOOL_NAMES,
    MUTATING_TOOL_NAMES,
)


class TestToolCallSignature:
    """Test tool call signature creation and hashing."""

    def test_signature_from_call(self):
        """Test creating signature from tool call."""
        sig = ToolCallSignature.from_call("read_file", {"path": "/tmp/test.txt"})
        assert sig.tool_name == "read_file"
        assert len(sig.args_hash) == 64  # SHA256 hex length

    def test_signature_stability(self):
        """Test that same inputs produce same signature."""
        args = {"path": "/tmp/test.txt", "offset": 0}
        sig1 = ToolCallSignature.from_call("read_file", args)
        sig2 = ToolCallSignature.from_call("read_file", args)
        assert sig1.args_hash == sig2.args_hash

    def test_signature_arg_order_independent(self):
        """Test that argument order doesn't affect hash."""
        args1 = {"a": 1, "b": 2, "c": 3}
        args2 = {"c": 3, "a": 1, "b": 2}
        sig1 = ToolCallSignature.from_call("read_file", args1)
        sig2 = ToolCallSignature.from_call("read_file", args2)
        assert sig1.args_hash == sig2.args_hash

    def test_signature_different_for_different_args(self):
        """Test that different args produce different hash."""
        sig1 = ToolCallSignature.from_call("read_file", {"path": "/tmp/a.txt"})
        sig2 = ToolCallSignature.from_call("read_file", {"path": "/tmp/b.txt"})
        assert sig1.args_hash != sig2.args_hash

    def test_signature_different_for_different_tools(self):
        """Test that different tools produce different signature object."""
        sig1 = ToolCallSignature.from_call("read_file", {"path": "/tmp/test.txt"})
        sig2 = ToolCallSignature.from_call("write_file", {"path": "/tmp/test.txt"})
        # Tool names are different
        assert sig1.tool_name == "read_file"
        assert sig2.tool_name == "write_file"
        # Note: args_hash is the same when args are identical
        # The signature combines tool_name and args_hash in ToolCallGuardrailController


class TestCanonicalToolArgs:
    """Test argument canonicalization."""

    def test_canonical_sorted_keys(self):
        """Test that keys are sorted in output."""
        args = {"z": 1, "a": 2, "m": 3}
        canonical = canonical_tool_args(args)
        # Should be sorted alphabetically
        assert canonical.index('"a"') < canonical.index('"m"')
        assert canonical.index('"m"') < canonical.index('"z"')

    def test_canonical_compact(self):
        """Test that output is compact (no extra whitespace)."""
        args = {"key": "value"}
        canonical = canonical_tool_args(args)
        assert " " not in canonical


class TestClassifyToolFailure:
    """Test tool failure classification."""

    def test_none_result_not_failed(self):
        """Test that None result is not classified as failure."""
        failed, suffix = classify_tool_failure("read_file", None)
        assert failed is False
        assert suffix == ""

    def test_error_in_json_response(self):
        """Test detection of error in JSON response."""
        result = '{"success": false, "error": "File not found"}'
        failed, suffix = classify_tool_failure("read_file", result)
        assert failed is True
        assert suffix == " [error]"

    def test_error_prefix(self):
        """Test detection of Error prefix."""
        result = "Error: Connection refused"
        failed, suffix = classify_tool_failure("execute_terminal", result)
        assert failed is True
        assert suffix == " [error]"

    def test_terminal_exit_code_nonzero(self):
        """Test detection of non-zero exit code."""
        result = '{"exit_code": 127, "stdout": "", "stderr": "Command not found"}'
        failed, suffix = classify_tool_failure("execute_terminal", result)
        assert failed is True
        assert suffix == " [exit 127]"

    def test_terminal_exit_code_zero_not_failed(self):
        """Test that zero exit code is not a failure."""
        result = '{"exit_code": 0, "stdout": "Success", "stderr": ""}'
        failed, suffix = classify_tool_failure("execute_terminal", result)
        assert failed is False

    def test_memory_limit_exceeded(self):
        """Test detection of memory limit exceeded."""
        result = '{"success": false, "error": "Memory exceeds the limit"}'
        failed, suffix = classify_tool_failure("memory", result)
        assert failed is True
        assert suffix == " [full]"


class TestExactFailureDetection:
    """Test exact failure detection (same tool + same args)."""

    def test_no_warning_for_first_failure(self):
        """Test that no warning for first failure."""
        controller = ToolCallGuardrailController(
            ToolCallGuardrailConfig(warnings_enabled=True)
        )
        decision = controller.after_call(
            "read_file", {"path": "/tmp/test.txt"}, '{"error": "not found"}', failed=True
        )
        assert decision.action == "allow"
        assert decision.count == 1

    def test_warning_after_threshold(self):
        """Test warning after exact failure threshold."""
        controller = ToolCallGuardrailController(
            ToolCallGuardrailConfig(
                warnings_enabled=True,
                exact_failure_warn_after=2,
            )
        )
        args = {"path": "/tmp/test.txt"}

        # First call - fail
        controller.after_call("read_file", args, '{"error": "not found"}', failed=True)
        # Second call - fail
        decision = controller.after_call("read_file", args, '{"error": "not found"}', failed=True)

        assert decision.action == "warn"
        assert decision.code == "repeated_exact_failure_warning"
        assert decision.count == 2

    def test_success_clears_exact_failure_count(self):
        """Test that success clears exact failure count."""
        controller = ToolCallGuardrailController(
            ToolCallGuardrailConfig(warnings_enabled=True, exact_failure_warn_after=2)
        )
        args = {"path": "/tmp/test.txt"}

        # Fail twice
        controller.after_call("read_file", args, '{"error": "not found"}', failed=True)
        controller.after_call("read_file", args, '{"error": "not found"}', failed=True)
        # Success
        controller.after_call("read_file", args, '{"success": true}', failed=False)
        # Fail again - should restart count
        decision = controller.after_call("read_file", args, '{"error": "not found"}', failed=True)

        assert decision.action == "allow"
        assert decision.count == 1

    def test_different_args_different_count(self):
        """Test that different args don't share exact failure count."""
        controller = ToolCallGuardrailController(
            ToolCallGuardrailConfig(
                warnings_enabled=True,
                exact_failure_warn_after=2,
                same_tool_failure_warn_after=10,  # High threshold to avoid same-tool warning
            )
        )

        # Fail on file A twice
        controller.after_call("read_file", {"path": "/tmp/a.txt"}, '{"error": "not found"}', failed=True)
        controller.after_call("read_file", {"path": "/tmp/a.txt"}, '{"error": "not found"}', failed=True)
        # Fail on file B - exact count is separate, but same-tool count is 3
        decision = controller.after_call("read_file", {"path": "/tmp/b.txt"}, '{"error": "not found"}', failed=True)

        # Exact failure count for b.txt is 1 (allow)
        assert decision.count == 1
        # Same-tool count triggers same_tool_failure_warn_after=10? No, it's 3
        # So action should be allow
        assert decision.action == "allow"


class TestSameToolFailureDetection:
    """Test same-tool failure detection (same tool, different args)."""

    def test_warning_after_threshold(self):
        """Test warning after same-tool failure threshold."""
        controller = ToolCallGuardrailController(
            ToolCallGuardrailConfig(
                warnings_enabled=True,
                same_tool_failure_warn_after=3,
            )
        )

        # Fail with different args each time
        controller.after_call("read_file", {"path": "/tmp/a.txt"}, '{"error": "not found"}', failed=True)
        controller.after_call("read_file", {"path": "/tmp/b.txt"}, '{"error": "not found"}', failed=True)
        decision = controller.after_call("read_file", {"path": "/tmp/c.txt"}, '{"error": "not found"}', failed=True)

        assert decision.action == "warn"
        assert decision.code == "same_tool_failure_warning"
        assert decision.count == 3

    def test_success_clears_same_tool_count(self):
        """Test that success clears same-tool failure count."""
        controller = ToolCallGuardrailController(
            ToolCallGuardrailConfig(warnings_enabled=True, same_tool_failure_warn_after=2)
        )

        # Fail twice
        controller.after_call("read_file", {"path": "/tmp/a.txt"}, '{"error": "not found"}', failed=True)
        controller.after_call("read_file", {"path": "/tmp/b.txt"}, '{"error": "not found"}', failed=True)
        # Success
        controller.after_call("read_file", {"path": "/tmp/c.txt"}, '{"success": true}', failed=False)
        # Fail again - should restart count
        decision = controller.after_call("read_file", {"path": "/tmp/d.txt"}, '{"error": "not found"}', failed=True)

        assert decision.action == "allow"
        assert decision.count == 1


class TestIdempotentNoProgressDetection:
    """Test idempotent tool no-progress detection."""

    def test_same_result_repeated(self):
        """Test detection of repeated same result from idempotent tool."""
        controller = ToolCallGuardrailController(
            ToolCallGuardrailConfig(
                warnings_enabled=True,
                no_progress_warn_after=2,
            )
        )
        args = {"path": "/tmp/test.txt"}
        result = '{"content": "Hello World", "lines": 1}'

        # First call
        controller.after_call("read_file", args, result, failed=False)
        # Second call - same result
        decision = controller.after_call("read_file", args, result, failed=False)

        assert decision.action == "warn"
        assert decision.code == "idempotent_no_progress_warning"
        assert decision.count == 2

    def test_different_result_resets_count(self):
        """Test that different result resets no-progress count."""
        controller = ToolCallGuardrailController(
            ToolCallGuardrailConfig(warnings_enabled=True, no_progress_warn_after=2)
        )
        args = {"path": "/tmp/test.txt"}

        controller.after_call("read_file", args, '{"content": "Hello"}', failed=False)
        controller.after_call("read_file", args, '{"content": "Hello"}', failed=False)
        controller.after_call("read_file", args, '{"content": "World"}', failed=False)
        decision = controller.after_call("read_file", args, '{"content": "World"}', failed=False)

        # Should restart count for new result
        assert decision.action == "warn"
        assert decision.count == 2

    def test_mutating_tool_not_tracked(self):
        """Test that mutating tools are not tracked for no-progress."""
        controller = ToolCallGuardrailController(
            ToolCallGuardrailConfig(warnings_enabled=True, no_progress_warn_after=2)
        )
        args = {"path": "/tmp/test.txt", "content": "Hello"}

        # Mutating tool - repeated calls should not trigger no-progress
        controller.after_call("write_file", args, '{"success": true}', failed=False)
        controller.after_call("write_file", args, '{"success": true}', failed=False)
        decision = controller.after_call("write_file", args, '{"success": true}', failed=False)

        assert decision.action == "allow"
        assert decision.count == 0


class TestHardStop:
    """Test hard stop functionality."""

    def test_exact_failure_halt(self):
        """Test that exact failure can trigger hard stop.

        Note: Hard stop is checked in before_call, so we need to call
        before_call after the failures to trigger the block.
        """
        controller = ToolCallGuardrailController(
            ToolCallGuardrailConfig(
                hard_stop_enabled=True,
                exact_failure_block_after=3,
            )
        )
        args = {"path": "/tmp/test.txt"}

        # Fail 3 times with same args (record via after_call)
        controller.after_call("read_file", args, '{"error": "not found"}', failed=True)
        controller.after_call("read_file", args, '{"error": "not found"}', failed=True)
        controller.after_call("read_file", args, '{"error": "not found"}', failed=True)

        # Now before_call should block (check happens in before_call)
        decision = controller.before_call("read_file", args)

        assert decision.action == "block"
        assert decision.code == "repeated_exact_failure_block"
        assert decision.should_halt is True

    def test_same_tool_failure_halt(self):
        """Test that same-tool failure can trigger hard stop."""
        controller = ToolCallGuardrailController(
            ToolCallGuardrailConfig(
                hard_stop_enabled=True,
                same_tool_failure_halt_after=5,
            )
        )

        # Fail with different args
        for i in range(5):
            controller.after_call("read_file", {"path": f"/tmp/{i}.txt"}, '{"error": "not found"}', failed=True)

        # After 5 failures, should halt
        decision = controller.after_call("read_file", {"path": "/tmp/new.txt"}, '{"error": "not found"}', failed=True)

        assert decision.action == "halt"
        assert decision.code == "same_tool_failure_halt"
        assert decision.should_halt is True

    def test_before_call_blocks_when_halt_set(self):
        """Test that before_call returns block when halt is set."""
        controller = ToolCallGuardrailController(
            ToolCallGuardrailConfig(
                hard_stop_enabled=True,
                exact_failure_block_after=2,
            )
        )
        args = {"path": "/tmp/test.txt"}

        # Fail twice to trigger halt
        controller.after_call("read_file", args, '{"error": "not found"}', failed=True)
        controller.after_call("read_file", args, '{"error": "not found"}', failed=True)

        # Next call should be blocked
        decision = controller.before_call("read_file", args)

        assert decision.action == "block"
        assert controller.halt_decision is not None

    def test_halt_decision_persists(self):
        """Test that halt decision persists after being set.

        Note: halt_decision is set in before_call when hard stop triggers.
        """
        controller = ToolCallGuardrailController(
            ToolCallGuardrailConfig(
                hard_stop_enabled=True,
                exact_failure_block_after=2,
            )
        )
        args = {"path": "/tmp/test.txt"}

        # Trigger halt via before_call
        controller.after_call("read_file", args, '{"error": "not found"}', failed=True)
        controller.after_call("read_file", args, '{"error": "not found"}', failed=True)
        # before_call sets halt_decision when blocking
        controller.before_call("read_file", args)

        # Check halt_decision property
        assert controller.halt_decision is not None
        assert controller.halt_decision.should_halt is True


class TestResetForTurn:
    """Test reset functionality."""

    def test_reset_clears_counts(self):
        """Test that reset_for_turn clears all counts."""
        controller = ToolCallGuardrailController(
            ToolCallGuardrailConfig(
                warnings_enabled=True,
                exact_failure_warn_after=2,
                same_tool_failure_warn_after=2,
                no_progress_warn_after=2,
            )
        )

        # Add some failures and no-progress
        controller.after_call("read_file", {"path": "/tmp/a.txt"}, '{"error": "not found"}', failed=True)
        controller.after_call("read_file", {"path": "/tmp/b.txt"}, '{"error": "not found"}', failed=True)
        controller.after_call("read_file", {"path": "/tmp/c.txt"}, '{"content": "same"}', failed=False)

        # Reset
        controller.reset_for_turn()

        # Next call should start fresh
        decision = controller.after_call("read_file", {"path": "/tmp/d.txt"}, '{"error": "not found"}', failed=True)
        assert decision.count == 1
        assert decision.action == "allow"


class TestToolGuardrailDecision:
    """Test ToolGuardrailDecision class."""

    def test_allows_execution_for_allow(self):
        """Test allows_execution for 'allow' action."""
        decision = ToolGuardrailDecision(action="allow")
        assert decision.allows_execution is True

    def test_allows_execution_for_warn(self):
        """Test allows_execution for 'warn' action."""
        decision = ToolGuardrailDecision(action="warn")
        assert decision.allows_execution is True

    def test_not_allows_execution_for_block(self):
        """Test allows_execution for 'block' action."""
        decision = ToolGuardrailDecision(action="block")
        assert decision.allows_execution is False

    def test_not_allows_execution_for_halt(self):
        """Test allows_execution for 'halt' action."""
        decision = ToolGuardrailDecision(action="halt")
        assert decision.allows_execution is False

    def test_to_metadata(self):
        """Test to_metadata conversion."""
        sig = ToolCallSignature.from_call("read_file", {"path": "/tmp/test.txt"})
        decision = ToolGuardrailDecision(
            action="warn",
            code="test_code",
            message="Test message",
            tool_name="read_file",
            count=3,
            signature=sig,
        )
        metadata = decision.to_metadata()

        assert metadata["action"] == "warn"
        assert metadata["code"] == "test_code"
        assert metadata["message"] == "Test message"
        assert metadata["tool_name"] == "read_file"
        assert metadata["count"] == 3
        assert "signature" in metadata


class TestConfigFromMapping:
    """Test configuration from mapping."""

    def test_defaults(self):
        """Test default configuration."""
        config = ToolCallGuardrailConfig.from_mapping(None)
        assert config.warnings_enabled is True
        assert config.hard_stop_enabled is False
        assert config.exact_failure_warn_after == 2

    def test_custom_values(self):
        """Test custom configuration values."""
        data = {
            "warnings_enabled": False,
            "hard_stop_enabled": True,
            "warn_after": {
                "exact_failure": 5,
            },
            "hard_stop_after": {
                "same_tool_failure": 10,
            },
        }
        config = ToolCallGuardrailConfig.from_mapping(data)

        assert config.warnings_enabled is False
        assert config.hard_stop_enabled is True
        assert config.exact_failure_warn_after == 5
        assert config.same_tool_failure_halt_after == 10


class TestPredefinedToolSets:
    """Test predefined idempotent and mutating tool sets."""

    def test_read_file_is_idempotent(self):
        """Test that read_file is in idempotent set."""
        assert "read_file" in IDEMPOTENT_TOOL_NAMES

    def test_write_file_is_mutating(self):
        """Test that write_file is in mutating set."""
        assert "write_file" in MUTATING_TOOL_NAMES

    def test_execute_terminal_is_mutating(self):
        """Test that execute_terminal is in mutating set."""
        assert "execute_terminal" in MUTATING_TOOL_NAMES

    def test_no_overlap(self):
        """Test that idempotent and mutating sets don't overlap."""
        overlap = IDEMPOTENT_TOOL_NAMES & MUTATING_TOOL_NAMES
        assert len(overlap) == 0
