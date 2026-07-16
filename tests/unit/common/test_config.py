#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the unified YAML configuration system.

Tests cover: load/save, cache, env override, dotenv, migration,
workspace directories, and config helpers.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


class TestLoadSaveConfig:
    """Test config loading and saving."""

    def test_load_config_returns_dict(self):
        """Test load_config returns a dict with expected top-level keys."""
        from common.config import load_config

        cfg = load_config()
        assert isinstance(cfg, dict)
        assert "model" in cfg
        assert "agent" in cfg
        assert "terminal" in cfg

    def test_load_config_includes_defaults(self):
        """Test default values are present."""
        from common.config import load_config

        cfg = load_config()
        assert cfg["agent"]["max_turns"] == 90
        assert cfg["agent"]["gateway_timeout"] == 1800
        assert cfg["terminal"]["backend"] == "local"

    def test_save_and_reload(self):
        """Test saving and reloading preserves values."""
        from common.config import load_config, save_config

        cfg = load_config()
        cfg["agent"]["max_turns"] = 42
        save_config(cfg)

        cfg2 = load_config(use_cache=False)
        assert cfg2["agent"]["max_turns"] == 42

        # restore default
        cfg["agent"]["max_turns"] = 90
        save_config(cfg)


class TestEnvOverride:
    """Test environment variable override."""

    def test_agentz_home_from_env(self):
        """Test AGENT_Z_HOME env var is respected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_home = Path(tmpdir) / "custom_agent"
            with patch.dict(os.environ, {"AGENT_Z_HOME": str(custom_home)}):
                # Reload module to pick up new env
                import importlib
                from common import config as cfg_module

                importlib.reload(cfg_module)

                from common.config import AGENT_Z_HOME, get_config_path

                assert str(AGENT_Z_HOME) == str(custom_home)
                assert get_config_path().parent == custom_home


class TestWorkspaceDirs:
    """Test workspace directory helpers."""

    def test_get_sessions_dir(self):
        """Test sessions directory path."""
        from common.config import get_sessions_dir, AGENT_Z_HOME

        assert get_sessions_dir() == AGENT_Z_HOME / "sessions"

    def test_get_memories_dir(self):
        """Test memories directory path."""
        from common.config import get_memories_dir, AGENT_Z_HOME

        assert get_memories_dir() == AGENT_Z_HOME / "memories"

    def test_get_logs_dir(self):
        """Test logs directory path."""
        from common.config import get_logs_dir, AGENT_Z_HOME

        assert get_logs_dir() == AGENT_Z_HOME / "logs"

    def test_ensure_workspace_dirs_creates_them(self):
        """Test ensure_workspace_dirs creates all required directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_home = Path(tmpdir) / "test_agent"

            with patch.dict(os.environ, {"AGENT_Z_HOME": str(custom_home)}):
                import importlib
                from common import config as cfg_module

                importlib.reload(cfg_module)

                from common.config import (
                    ensure_workspace_dirs,
                    get_sessions_dir,
                    get_memories_dir,
                )

                ensure_workspace_dirs()

                assert custom_home.exists()
                assert get_sessions_dir().exists()
                assert get_memories_dir().exists()


class TestConfigHelpers:
    """Test typed config getters."""

    def test_get_model_config(self):
        """Test get_model_config returns a dict."""
        from common.config import get_model_config

        cfg = get_model_config()
        assert isinstance(cfg, dict)
        assert "name" in cfg

    def test_get_terminal_config(self):
        """Test get_terminal_config returns a dict."""
        from common.config import get_terminal_config

        cfg = get_terminal_config()
        assert isinstance(cfg, dict)
        assert cfg["backend"] == "local"

    def test_get_memory_config(self):
        """Test get_memory_config returns a dict."""
        from common.config import get_memory_config

        cfg = get_memory_config()
        assert isinstance(cfg, dict)
        assert cfg["enabled"] is True

    def test_get_compression_config(self):
        """Test get_compression_config returns a dict."""
        from common.config import get_compression_config

        cfg = get_compression_config()
        assert isinstance(cfg, dict)
        assert cfg["enabled"] is True

    def test_get_disabled_skills(self):
        """Test get_disabled_skills returns a list."""
        from common.config import get_disabled_skills

        disabled = get_disabled_skills()
        assert isinstance(disabled, list)


class TestDefaultConfig:
    """Test DEFAULT_CONFIG schema."""

    def test_agent_section_complete(self):
        """Test agent section has all expected keys."""
        from common.config import DEFAULT_CONFIG

        agent = DEFAULT_CONFIG["agent"]
        assert "max_turns" in agent
        assert "gateway_timeout" in agent
        assert "verify_on_stop" in agent
        assert "coding_context" in agent

    def test_tool_loop_guardrails_top_level(self):
        """Test tool_loop_guardrails is a top-level key."""
        from common.config import DEFAULT_CONFIG

        tlr = DEFAULT_CONFIG["tool_loop_guardrails"]
        assert "warn_after" in tlr
        assert "hard_stop_after" in tlr

    def test_tool_loop_guardrails_structure(self):
        """Test tool_loop_guardrails has warn and hard_stop thresholds."""
        from common.config import DEFAULT_CONFIG

        tlr = DEFAULT_CONFIG["tool_loop_guardrails"]
        assert "warn_after" in tlr
        assert "hard_stop_after" in tlr
        assert tlr["warn_after"]["exact_failure"] == 2
        assert tlr["hard_stop_after"]["exact_failure"] == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
