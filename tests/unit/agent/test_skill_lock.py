#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Skill Lock module.

Tests cover:
- HubLockEntry dataclass
- HubLockFile class
- Lock file management
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime

from agent.skill_lock import HubLockEntry, HubLockFile, LOCK_VERSION

# ─────────────────────────────────────────────────────────────────────────────
# Test HubLockEntry
# ─────────────────────────────────────────────────────────────────────────────


class TestHubLockEntry:
    """Tests for HubLockEntry dataclass."""

    def test_hub_lock_entry_creation(self):
        """HubLockEntry creates with required fields."""
        entry = HubLockEntry(
            skill_name="test_skill",
            source="github",
            identifier="user/repo",
            installed_at="2024-01-01T00:00:00Z",
            origin_hash="abc123",
        )

        assert entry.skill_name == "test_skill"
        assert entry.source == "github"
        assert entry.identifier == "user/repo"
        assert entry.installed_at == "2024-01-01T00:00:00Z"
        assert entry.origin_hash == "abc123"

    def test_hub_lock_entry_with_all_fields(self):
        """HubLockEntry creates with all optional fields."""
        entry = HubLockEntry(
            skill_name="my_skill",
            source="url",
            identifier="https://example.com/skill.zip",
            installed_at="2024-06-15T10:30:00Z",
            origin_hash="def456",
            version="2.0.0",
            author="Test Author",
            description="A test skill",
            trust_level="trusted",
            install_path="skills/my_skill",
        )

        assert entry.version == "2.0.0"
        assert entry.author == "Test Author"
        assert entry.description == "A test skill"
        assert entry.trust_level == "trusted"
        assert entry.install_path == "skills/my_skill"

    def test_hub_lock_entry_defaults(self):
        """HubLockEntry has correct defaults."""
        entry = HubLockEntry(
            skill_name="default_skill",
            source="hermes-index",
            identifier="skill_id",
            installed_at="2024-01-01T00:00:00Z",
            origin_hash="hash123",
        )

        assert entry.version == "1.0.0"
        assert entry.author == ""
        assert entry.description == ""
        assert entry.trust_level == "community"
        assert entry.install_path == ""
        assert entry.extra == {}

    def test_hub_lock_entry_extra_field(self):
        """HubLockEntry accepts extra field."""
        entry = HubLockEntry(
            skill_name="skill_with_extra",
            source="github",
            identifier="repo",
            installed_at="2024-01-01T00:00:00Z",
            origin_hash="hash",
            extra={"key": "value"},
        )

        assert entry.extra == {"key": "value"}


# ─────────────────────────────────────────────────────────────────────────────
# Test HubLockFile
# ─────────────────────────────────────────────────────────────────────────────


class TestHubLockFile:
    """Tests for HubLockFile class."""

    def test_hub_lock_file_initialization(self):
        """HubLockFile initializes correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock = HubLockFile(skills_dir=tmpdir)

            assert lock._skills_dir == Path(tmpdir)
            assert ".hub" in str(lock._lock_dir)

    def test_lock_file_path(self):
        """HubLockFile constructs correct lock file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock = HubLockFile(skills_dir=tmpdir)

            assert lock._lock_file.name == "lock.json"
            assert ".hub" in str(lock._lock_file)

    def test_load_returns_empty_when_no_file(self):
        """_load() returns empty structure when lock file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock = HubLockFile(skills_dir=tmpdir)
            # Clear cache to force load
            lock._cache = None

            data = lock._load()

            assert data["version"] == LOCK_VERSION
            assert data["installed"] == {}

    def test_load_returns_cached_data(self):
        """_load() returns cached data when available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock = HubLockFile(skills_dir=tmpdir)
            lock._cache = {"version": 1, "installed": {"test": {}}}

            data = lock._load()

            assert data == {"version": 1, "installed": {"test": {}}}

    def test_load_returns_valid_structure_for_invalid_json(self):
        """_load() returns valid structure for corrupted file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_file = Path(tmpdir) / ".hub" / "lock.json"
            lock_file.parent.mkdir(parents=True, exist_ok=True)
            lock_file.write_text("not valid json{", encoding="utf-8")

            lock = HubLockFile(skills_dir=tmpdir)
            data = lock._load()

            # Should return valid structure
            assert data["version"] == LOCK_VERSION
            assert data["installed"] == {}

    def test_has_entry_returns_false_when_not_installed(self):
        """has() returns False when skill is not installed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock = HubLockFile(skills_dir=tmpdir)
            lock._load()

            assert lock.has("nonexistent_skill") is False

    def test_add_entry(self):
        """add_entry() adds a new entry to lock."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock = HubLockFile(skills_dir=tmpdir)
            entry = HubLockEntry(
                skill_name="new_skill",
                source="github",
                identifier="user/repo",
                installed_at="2024-01-01T00:00:00Z",
                origin_hash="abc123",
            )

            lock.add_entry(entry)

            assert lock.has_entry("new_skill") is True

    def test_get_entry(self):
        """get() returns entry if installed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock = HubLockFile(skills_dir=tmpdir)
            entry = HubLockEntry(
                skill_name="my_skill",
                source="github",
                identifier="user/repo",
                installed_at="2024-01-01T00:00:00Z",
                origin_hash="abc123",
            )
            lock.add(entry)

            retrieved = lock.get("my_skill")

            assert retrieved is not None
            assert retrieved.skill_name == "my_skill"
            assert retrieved.source == "github"

    def test_get_entry_returns_none_when_not_found(self):
        """get() returns None when skill not installed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock = HubLockFile(skills_dir=tmpdir)
            lock._load()

            result = lock.get("nonexistent")

            assert result is None

    def test_remove_entry(self):
        """remove() deletes an entry from lock."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock = HubLockFile(skills_dir=tmpdir)
            entry = HubLockEntry(
                skill_name="to_remove",
                source="github",
                identifier="user/repo",
                installed_at="2024-01-01T00:00:00Z",
                origin_hash="abc123",
            )
            lock.add(entry)
            assert lock.has("to_remove") is True

            lock.remove("to_remove")

            assert lock.has("to_remove") is False

    def test_list_entries(self):
        """list() returns all installed skill names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock = HubLockFile(skills_dir=tmpdir)

            entry1 = HubLockEntry(
                skill_name="skill_1",
                source="github",
                identifier="r1",
                installed_at="2024-01-01T00:00:00Z",
                origin_hash="h1",
            )
            entry2 = HubLockEntry(
                skill_name="skill_2",
                source="url",
                identifier="r2",
                installed_at="2024-01-01T00:00:00Z",
                origin_hash="h2",
            )
            lock.add(entry1)
            lock.add(entry2)

            names = lock.list()

            assert "skill_1" in names
            assert "skill_2" in names
            assert len(names) == 2

    def test_clear(self):
        """clear() removes all entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock = HubLockFile(skills_dir=tmpdir)

            entry = HubLockEntry(
                skill_name="to_clear",
                source="github",
                identifier="r",
                installed_at="2024-01-01T00:00:00Z",
                origin_hash="h",
            )
            lock.add(entry)
            assert lock.has("to_clear") is True

            lock.clear()

            assert lock.has("to_clear") is False
            assert len(lock.list()) == 0

    def test_save_and_load_persistence(self):
        """save() and load() maintain persistence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock1 = HubLockFile(skills_dir=tmpdir)
            entry = HubLockEntry(
                skill_name="persistent",
                source="github",
                identifier="r",
                installed_at="2024-01-01T00:00:00Z",
                origin_hash="h",
            )
            lock1.add(entry)
            lock1.save()

            # Create new instance to simulate restart
            lock2 = HubLockFile(skills_dir=tmpdir)
            lock2._load()

            assert lock2.has("persistent") is True
            assert lock2.get("persistent").source == "github"


class TestLockVersion:
    """Tests for LOCK_VERSION constant."""

    def test_lock_version_is_one(self):
        """LOCK_VERSION is 1."""
        assert LOCK_VERSION == 1
