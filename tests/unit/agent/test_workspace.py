#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Workspace module.

Tests cover:
- WorkspaceManager class
- DEFAULT_WORKSPACE_DIR constant
- get_workspace_manager function
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from agent.workspace import (
    WorkspaceManager,
    get_workspace_manager,
    DEFAULT_WORKSPACE_DIR,
    BOOTSTRAP_FILES,
    STATE_FILE,
)


class TestConstants:
    """Tests for module constants."""

    def test_default_workspace_dir(self):
        """DEFAULT_WORKSPACE_DIR is set."""
        assert DEFAULT_WORKSPACE_DIR is not None
        assert isinstance(DEFAULT_WORKSPACE_DIR, Path)

    def test_bootstrap_files_is_dict(self):
        """BOOTSTRAP_FILES is a dictionary."""
        assert isinstance(BOOTSTRAP_FILES, dict)

    def test_state_file_is_string(self):
        """STATE_FILE is a string."""
        assert isinstance(STATE_FILE, str)


class TestGetWorkspaceManager:
    """Tests for get_workspace_manager() function."""

    def test_returns_workspace_manager(self):
        """get_workspace_manager() returns a WorkspaceManager instance."""
        result = get_workspace_manager()
        assert isinstance(result, WorkspaceManager)


class TestWorkspaceManagerInit:
    """Tests for WorkspaceManager initialization."""

    def test_init_with_default_workspace(self):
        """WorkspaceManager initializes with default workspace_dir."""
        manager = WorkspaceManager()
        assert manager.workspace_dir == DEFAULT_WORKSPACE_DIR

    def test_init_with_custom_workspace(self, tmp_path):
        """WorkspaceManager accepts custom workspace_dir."""
        manager = WorkspaceManager(workspace_dir=tmp_path)
        assert manager.workspace_dir == tmp_path


class TestWorkspaceManagerPaths:
    """Tests for WorkspaceManager path properties."""

    def test_template_dir_property(self, tmp_path):
        """template_dir property returns path."""
        manager = WorkspaceManager(workspace_dir=tmp_path)
        assert hasattr(manager, 'template_dir')

    def test_state_path_property(self, tmp_path):
        """state_path returns path to state file."""
        manager = WorkspaceManager(workspace_dir=tmp_path)
        assert manager.state_path == tmp_path / STATE_FILE

    def test_logs_dir_property(self, tmp_path):
        """logs_dir property returns path."""
        manager = WorkspaceManager(workspace_dir=tmp_path)
        assert manager.logs_dir == tmp_path / "logs"

    def test_sessions_dir_property(self, tmp_path):
        """sessions_dir property returns path."""
        manager = WorkspaceManager(workspace_dir=tmp_path)
        assert manager.sessions_dir == tmp_path / "sessions"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
