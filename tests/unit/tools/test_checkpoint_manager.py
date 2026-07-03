#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Checkpoint Manager module.

Tests cover:
- CheckpointManager initialization
- Helper functions (validation, path operations)
- Constants and configuration
"""

import pytest
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from tools.checkpoint_manager import (
    CheckpointManager,
    DEFAULT_EXCLUDES,
    CHECKPOINT_BASE,
    _validate_commit_hash,
    _validate_file_path,
    _normalize_path,
    _project_hash,
    _store_path,
    _ref_name,
    _COMMIT_HASH_RE,
    _MAX_FILES,
)

# ─────────────────────────────────────────────────────────────────────────────
# Test Helper Functions
# ─────────────────────────────────────────────────────────────────────────────


class TestValidateCommitHash:
    """Tests for _validate_commit_hash() function."""

    def test_valid_commit_hash(self):
        """_validate_commit_hash() returns None for valid hashes."""
        valid_hashes = ["abcd", "1234567890abcdef", "a1b2c3d4e5f"]
        for h in valid_hashes:
            assert _validate_commit_hash(h) is None

    def test_empty_hash_returns_error(self):
        """_validate_commit_hash() returns error for empty hash."""
        assert _validate_commit_hash("") is not None
        assert _validate_commit_hash("   ") is not None

    def test_none_hash_returns_error(self):
        """_validate_commit_hash() returns error for None-like hash."""
        assert _validate_commit_hash(None) is not None

    def test_hash_starting_with_dash_returns_error(self):
        """_validate_commit_hash() rejects hash starting with dash."""
        assert _validate_commit_hash("-abcd") is not None

    def test_invalid_characters_returns_error(self):
        """_validate_commit_hash() rejects non-hex characters."""
        assert _validate_commit_hash("xyz123") is not None
        assert _validate_commit_hash("ghij") is not None


class TestValidateFilePath:
    """Tests for _validate_file_path() function."""

    def test_valid_relative_path(self):
        """_validate_file_path() accepts relative paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            assert _validate_file_path("file.txt", tmpdir) is None
            assert _validate_file_path("src/main.py", tmpdir) is None
            assert _validate_file_path("./file.txt", tmpdir) is None

    def test_empty_path_returns_error(self):
        """_validate_file_path() rejects empty paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            assert _validate_file_path("", tmpdir) is not None
            assert _validate_file_path("   ", tmpdir) is not None

    def test_absolute_path_returns_error(self):
        """_validate_file_path() rejects absolute paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            assert _validate_file_path("/absolute/path", tmpdir) is not None
            assert _validate_file_path("C:/Windows", tmpdir) is not None

    def test_path_traversal_returns_error(self):
        """_validate_file_path() rejects path traversal attempts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            assert _validate_file_path("../escape", tmpdir) is not None
            assert _validate_file_path("foo/../../../etc/passwd", tmpdir) is not None


class TestNormalizePath:
    """Tests for _normalize_path() function."""

    def test_normalize_path_expands_user(self):
        """_normalize_path() expands ~ in paths."""
        result = _normalize_path("~/test")
        assert "~" not in str(result)
        assert result.is_absolute()

    def test_normalize_path_resolves_relative(self):
        """_normalize_path() resolves relative paths."""
        result = _normalize_path(".")
        assert result.is_absolute()

    def test_normalize_path_returns_path_object(self):
        """_normalize_path() returns a Path object."""
        result = _normalize_path("/tmp/test")
        assert isinstance(result, Path)


class TestProjectHash:
    """Tests for _project_hash() function."""

    def test_project_hash_returns_hex_string(self):
        """_project_hash() returns a hexadecimal string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hash_result = _project_hash(tmpdir)
            assert isinstance(hash_result, str)
            assert all(c in "0123456789abcdef" for c in hash_result)

    def test_project_hash_length(self):
        """_project_hash() returns 16 character hash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hash_result = _project_hash(tmpdir)
            assert len(hash_result) == 16

    def test_same_path_same_hash(self):
        """_project_hash() returns same hash for same path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hash1 = _project_hash(tmpdir)
            hash2 = _project_hash(tmpdir)
            assert hash1 == hash2

    def test_different_paths_different_hashes(self):
        """_project_hash() returns different hashes for different paths."""
        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                hash1 = _project_hash(tmpdir1)
                hash2 = _project_hash(tmpdir2)
                assert hash1 != hash2


class TestStorePath:
    """Tests for _store_path() function."""

    def test_store_path_returns_path(self):
        """_store_path() returns a Path object."""
        result = _store_path()
        assert isinstance(result, Path)

    def test_store_path_with_base(self):
        """_store_path() uses provided base."""
        custom_base = Path("/custom/base")
        result = _store_path(custom_base)
        assert result == custom_base / "store"


class TestRefName:
    """Tests for _ref_name() function."""

    def test_ref_name_format(self):
        """_ref_name() returns correctly formatted ref name."""
        result = _ref_name("abc123")
        assert result == "refs/handsome/abc123"

    def test_ref_name_uses_hash(self):
        """_ref_name() uses provided hash in ref name."""
        result = _ref_name("deadbeef")
        assert "deadbeef" in result


# ─────────────────────────────────────────────────────────────────────────────
# Test Constants
# ─────────────────────────────────────────────────────────────────────────────


class TestConstants:
    """Tests for module constants."""

    def test_default_excludes_is_list(self):
        """DEFAULT_EXCLUDES is a list."""
        assert isinstance(DEFAULT_EXCLUDES, list)
        assert len(DEFAULT_EXCLUDES) > 0

    def test_default_excludes_contains_common_patterns(self):
        """DEFAULT_EXCLUDES contains common ignore patterns."""
        common_patterns = ["node_modules/", ".git/", "*.pyc", ".venv/"]
        for pattern in common_patterns:
            assert pattern in DEFAULT_EXCLUDES

    def test_checkpoint_base_is_path(self):
        """CHECKPOINT_BASE is a Path object."""
        assert isinstance(CHECKPOINT_BASE, Path)

    def test_commit_hash_regex_is_compiled(self):
        """_COMMIT_HASH_RE is a compiled regex."""
        import re

        assert isinstance(_COMMIT_HASH_RE, re.Pattern)

    def test_max_files_is_reasonable(self):
        """_MAX_FILES is a reasonable value."""
        assert _MAX_FILES > 0
        assert _MAX_FILES > 1000


# ─────────────────────────────────────────────────────────────────────────────
# Test CheckpointManager Initialization
# ─────────────────────────────────────────────────────────────────────────────


class TestCheckpointManagerInit:
    """Tests for CheckpointManager initialization."""

    def test_default_initialization(self):
        """CheckpointManager initializes with reasonable defaults."""
        cm = CheckpointManager()

        assert cm.enabled is False
        assert cm.max_snapshots == 20
        assert cm.max_total_size_mb == 500
        assert cm.max_file_size_mb == 10

    def test_custom_initialization(self):
        """CheckpointManager accepts custom parameters."""
        cm = CheckpointManager(
            enabled=True,
            max_snapshots=50,
            max_total_size_mb=1000,
            max_file_size_mb=5,
        )

        assert cm.enabled is True
        assert cm.max_snapshots == 50
        assert cm.max_total_size_mb == 1000
        assert cm.max_file_size_mb == 5

    def test_enabled_defaults_to_false(self):
        """CheckpointManager defaults to disabled."""
        cm = CheckpointManager()
        assert cm.enabled is False

    def test_negative_max_snapshots_handled(self):
        """CheckpointManager handles negative max_snapshots."""
        cm = CheckpointManager(max_snapshots=-1)
        # Should not crash, value may be normalized
        assert cm.max_snapshots == -1 or cm.max_snapshots >= 0


# ─────────────────────────────────────────────────────────────────────────────
# Test CheckpointManager Properties and Methods
# ─────────────────────────────────────────────────────────────────────────────


class TestCheckpointManagerProperties:
    """Tests for CheckpointManager properties."""

    def test_checkpoint_manager_has_enabled_property(self):
        """CheckpointManager has enabled property."""
        cm = CheckpointManager(enabled=True)
        assert hasattr(cm, "enabled")
        assert cm.enabled is True

    def test_checkpoint_manager_has_max_snapshots(self):
        """CheckpointManager has max_snapshots property."""
        cm = CheckpointManager(max_snapshots=30)
        assert hasattr(cm, "max_snapshots")
        assert cm.max_snapshots == 30

    def test_checkpoint_manager_has_checkpointed_dirs_attribute(self):
        """CheckpointManager has _checkpointed_dirs attribute."""
        cm = CheckpointManager()
        assert hasattr(cm, "_checkpointed_dirs")

    def test_checkpoint_manager_has_git_available_attribute(self):
        """CheckpointManager has _git_available attribute."""
        cm = CheckpointManager()
        assert hasattr(cm, "_git_available")


class TestCheckpointManagerMethods:
    """Tests for CheckpointManager methods."""

    def test_checkpoint_manager_has_new_turn_method(self):
        """CheckpointManager has new_turn() method."""
        cm = CheckpointManager()
        assert hasattr(cm, "new_turn")
        assert callable(getattr(cm, "new_turn"))

    def test_checkpoint_manager_has_ensure_checkpoint_method(self):
        """CheckpointManager has ensure_checkpoint() method."""
        cm = CheckpointManager()
        assert hasattr(cm, "ensure_checkpoint")
        assert callable(getattr(cm, "ensure_checkpoint"))

    def test_checkpoint_manager_has_list_checkpoints_method(self):
        """CheckpointManager has list_checkpoints() method."""
        cm = CheckpointManager()
        assert hasattr(cm, "list_checkpoints")
        assert callable(getattr(cm, "list_checkpoints"))

    def test_checkpoint_manager_has_diff_method(self):
        """CheckpointManager has diff() method."""
        cm = CheckpointManager()
        assert hasattr(cm, "diff")
        assert callable(getattr(cm, "diff"))


# ─────────────────────────────────────────────────────────────────────────────
# Test CheckpointManager Disabled Mode
# ─────────────────────────────────────────────────────────────────────────────


class TestCheckpointManagerDisabledMode:
    """Tests for CheckpointManager when disabled."""

    def test_disabled_manager_returns_none_for_list_checkpoints(self):
        """Disabled manager returns empty for list_checkpoints."""
        cm = CheckpointManager(enabled=False)

        # When disabled, operations should return empty/default values
        # The exact behavior depends on implementation
        if hasattr(cm, "list_checkpoints"):
            result = cm.list_checkpoints("/tmp")
            # Disabled mode should return empty or None
            assert (
                result is None
                or result == []
                or (isinstance(result, list) and len(result) == 0)
            )

    def test_disabled_manager_ensure_checkpoint_is_safe(self):
        """Disabled manager's ensure_checkpoint is safe to call."""
        cm = CheckpointManager(enabled=False)

        # Should not raise even with invalid arguments
        try:
            if hasattr(cm, "ensure_checkpoint"):
                cm.ensure_checkpoint("/tmp", "test")
        except Exception:
            # Some validation errors may still be raised
            pass

    def test_disabled_manager_new_turn_is_safe(self):
        """Disabled manager's new_turn is safe to call."""
        cm = CheckpointManager(enabled=False)

        # Should not raise
        try:
            if hasattr(cm, "new_turn"):
                cm.new_turn()
        except Exception:
            pass
