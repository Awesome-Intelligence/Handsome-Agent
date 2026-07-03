#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Path Security module.

Tests cover:
- has_traversal_component() function
- validate_within_dir() function
- Path traversal attack prevention
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from tools.path_security import has_traversal_component, validate_within_dir

# ─────────────────────────────────────────────────────────────────────────────
# Test has_traversal_component
# ─────────────────────────────────────────────────────────────────────────────


class TestHasTraversalComponent:
    """Tests for has_traversal_component() function."""

    def test_simple_relative_path_returns_false(self):
        """has_traversal_component() returns False for simple relative paths."""
        assert has_traversal_component("file.txt") is False
        assert has_traversal_component("src/main.py") is False
        assert has_traversal_component("docs/readme.md") is False

    def test_path_with_dot_returns_true(self):
        """has_traversal_component() returns True for paths with '..'."""
        assert has_traversal_component("../file.txt") is True
        assert has_traversal_component("foo/../bar") is True
        assert has_traversal_component("foo/../../etc/passwd") is True
        # Note: ".../file" contains ".." so it returns True (substring check)

    def test_absolute_path_returns_true(self):
        """has_traversal_component() returns True for absolute paths."""
        if os.name == "nt":
            # Windows absolute paths (drive letters)
            assert has_traversal_component("C:/Windows") is True
            assert has_traversal_component("D:/Program Files") is True
        else:
            # Unix absolute paths
            assert has_traversal_component("/etc/passwd") is True
            assert has_traversal_component("/home/user/file") is True

    def test_empty_string_returns_false(self):
        """has_traversal_component() returns False for empty string."""
        assert has_traversal_component("") is False

    def test_current_dir_reference_returns_false(self):
        """has_traversal_component() returns False for '.' references."""
        assert has_traversal_component("./file.txt") is False
        assert has_traversal_component("foo/./bar") is False

    def test_windows_drive_letter_detected(self):
        """has_traversal_component() detects Windows drive letters."""
        assert has_traversal_component("E:/file.txt") is True
        assert has_traversal_component("C:\\\\Windows\\\\System32") is True

    def test_paths_without_dots_or_absolute_return_false(self):
        """has_traversal_component() returns False for normal paths."""
        assert has_traversal_component("images/photo.jpg") is False
        assert has_traversal_component("data/config.json") is False
        assert has_traversal_component("readme.md") is False


# ─────────────────────────────────────────────────────────────────────────────
# Test validate_within_dir
# ─────────────────────────────────────────────────────────────────────────────


class TestValidateWithinDir:
    """Tests for validate_within_dir() function."""

    def test_file_in_base_directory_returns_none(self):
        """validate_within_dir() returns None when file is within base."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            target = base / "file.txt"

            result = validate_within_dir(target, base)

            assert result is None

    def test_file_in_subdirectory_returns_none(self):
        """validate_within_dir() returns None when file is in subdirectory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            target = base / "subdir" / "nested" / "file.txt"

            # Create the subdirectory
            target.parent.mkdir(parents=True, exist_ok=True)
            target.touch()

            result = validate_within_dir(target, base)

            assert result is None

    def test_file_outside_base_returns_error(self):
        """validate_within_dir() returns error when file is outside."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            # Target outside base using ..
            target = (base.parent / "outside").resolve()

            result = validate_within_dir(target, base)

            assert result is not None
            assert "traversal" in result.lower() or "outside" in result.lower()

    def test_parent_directory_traversal_returns_error(self):
        """validate_within_dir() detects parent directory traversal."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            target = (base / ".." / ".." / "etc" / "passwd").resolve()

            result = validate_within_dir(target, base)

            assert result is not None

    def test_symlink_to_outside_returns_error(self):
        """validate_within_dir() detects symlinks pointing outside."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            outside_dir = Path(tmpdir).parent / "outside_dir"
            outside_dir.mkdir(exist_ok=True)
            target_file = outside_dir / "secret.txt"
            target_file.touch()

            # Create symlink inside base pointing to outside
            symlink = base / "link_to_outside"
            try:
                symlink.symlink_to(target_file)
                result = validate_within_dir(symlink, base)
                # resolve() follows symlinks, so this should detect traversal
                assert result is not None
            except (OSError, NotImplementedError):
                # Symlinks may not work on all platforms (e.g., Windows without admin)
                pytest.skip("Symlinks not supported on this platform")

    def test_relative_path_resolved_correctly(self):
        """validate_within_dir() correctly resolves relative paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            # Create a resolved path that's within base
            target = (base / "subdir" / ".." / "file.txt").resolve()

            result = validate_within_dir(target, base)

            # After resolving, should be within base (since .. cancels subdir)
            assert result is None

    def test_nonexistent_target_returns_none(self):
        """validate_within_dir() returns None for nonexistent paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            target = base / "nonexistent" / "file.txt"

            # Target doesn't exist but resolve() still works
            result = validate_within_dir(target, base)

            # Should still validate path structure
            # (Nonexistent files can still be validated)
            assert result is None or "traversal" in result.lower()

    def test_case_sensitivity_on_windows(self):
        """validate_within_dir() handles case sensitivity correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            target = base / "FILE.TXT"

            # Create the file
            target.touch()

            result = validate_within_dir(target, base)

            # On Windows, this should pass (case insensitive)
            # On Unix, case matters
            if os.name == "nt":
                assert result is None
            else:
                # On Unix, uppercase path should still be within base
                assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# Test Integration
# ─────────────────────────────────────────────────────────────────────────────


class TestPathSecurityIntegration:
    """Integration tests for path security functions."""

    def test_combined_validation_detects_attack(self):
        """Combining both functions provides defense in depth."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)

            # Attack path: use parent traversal to escape
            attack_path = base.parent / "outside"

            # First check detects traversal
            assert has_traversal_component(str(attack_path)) is True

            # Second check would return error
            result = validate_within_dir(attack_path.resolve(), base)
            assert result is not None

    def test_relative_traversal_detected(self):
        """Relative path traversal is properly detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)

            traversal_path = "foo/../../etc/passwd"

            assert has_traversal_component(traversal_path) is True

            result = validate_within_dir(Path(traversal_path).resolve(), base)
            assert result is not None

    def test_safe_path_passes_both_checks(self):
        """Safe paths pass both validation functions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            safe_path = base / "projects" / "myproject" / "file.txt"
            safe_path.parent.mkdir(parents=True, exist_ok=True)
            safe_path.touch()

            # Safe path should be valid
            assert validate_within_dir(safe_path, base) is None
