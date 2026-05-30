#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the shared module configuration.

Tests cover Settings management, workspace directory configuration,
and environment variable handling.
"""

import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile


class TestSettings:
    """Test Settings configuration management."""
    
    def test_default_settings(self):
        """Test default settings values."""
        from shared.config import Settings
        
        settings = Settings()
        
        assert settings.app_name == "HandsomeAgent"
        assert settings.app_version == "1.0.0"
        assert settings.debug is False
        assert settings.brain_service_host == "0.0.0.0"
        assert settings.brain_service_port == 8001
        assert settings.gateway_host == "0.0.0.0"
        assert settings.gateway_port == 8000
        assert settings.executor_port == 8002
    
    def test_settings_with_env_variables(self):
        """Test settings override with environment variables."""
        with patch.dict(os.environ, {
            'APP_NAME': 'TestAgent',
            'DEBUG': 'true',
            'BRAIN_SERVICE_PORT': '9000'
        }):
            # Clear cached settings
            from shared import config
            config.get_settings.cache_clear()
            
            settings = config.get_settings()
            
            assert settings.app_name == 'TestAgent'
            assert settings.debug is True
            assert settings.brain_service_port == 9000
    
    def test_get_settings_singleton(self):
        """Test that get_settings returns cached singleton."""
        from shared.config import get_settings
        
        settings1 = get_settings()
        settings2 = get_settings()
        
        assert settings1 is settings2
    
    def test_allowed_commands_default(self):
        """Test default allowed commands list."""
        from shared.config import Settings
        
        settings = Settings()
        
        assert "git" in settings.allowed_commands
        assert "npm" in settings.allowed_commands
        assert "pip" in settings.allowed_commands
        assert "python" in settings.allowed_commands
    
    def test_blocked_patterns_default(self):
        """Test default blocked patterns list."""
        from shared.config import Settings
        
        settings = Settings()
        
        assert "rm -rf /" in settings.blocked_patterns
        assert "curl | sh" in settings.blocked_patterns


class TestWorkspaceConfiguration:
    """Test workspace directory configuration."""
    
    def test_get_default_handsome_home(self):
        """Test default handsome home directory."""
        from shared.config import get_default_handsome_home, HANDSOME_HOME
        
        default_home = get_default_handsome_home()
        
        assert isinstance(default_home, Path)
        assert default_home.name == ".handsome_agent"
        assert str(HANDSOME_HOME) == str(default_home)
    
    def test_custom_handsome_home_via_env(self):
        """Test custom handsome home via environment variable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_home = Path(tmpdir) / "custom_agent"
            
            with patch.dict(os.environ, {'HANDSOME_HOME': str(custom_home)}):
                # Reload module to pick up new environment
                import importlib
                from shared import config
                importlib.reload(config)
                
                from shared.config import HANDSOME_HOME
                
                assert str(HANDSOME_HOME) == str(custom_home)
    
    def test_get_sessions_dir(self):
        """Test sessions directory path."""
        from shared.config import get_sessions_dir, HANDSOME_HOME
        
        sessions_dir = get_sessions_dir()
        
        assert sessions_dir == HANDSOME_HOME / "sessions"
    
    def test_get_memories_dir(self):
        """Test memories directory path."""
        from shared.config import get_memories_dir, HANDSOME_HOME
        
        memories_dir = get_memories_dir()
        
        assert memories_dir == HANDSOME_HOME / "memories"
    
    def test_get_logs_dir(self):
        """Test logs directory path."""
        from shared.config import get_logs_dir, HANDSOME_HOME
        
        logs_dir = get_logs_dir()
        
        assert logs_dir == HANDSOME_HOME / "logs"
    
    def test_get_config_dir(self):
        """Test config directory path."""
        from shared.config import get_config_dir, HANDSOME_HOME
        
        config_dir = get_config_dir()
        
        assert config_dir == HANDSOME_HOME / "config"


class TestEnsureWorkspaceDirs:
    """Test workspace directory creation."""
    
    def test_ensure_workspace_dirs_creates_directories(self):
        """Test that ensure_workspace_dirs creates all required directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_home = Path(tmpdir) / "test_agent"
            
            with patch.dict(os.environ, {'HANDSOME_HOME': str(custom_home)}):
                # Reload module
                import importlib
                from shared import config
                importlib.reload(config)
                
                from shared.config import ensure_workspace_dirs, get_sessions_dir, get_memories_dir
                
                ensure_workspace_dirs()
                
                assert custom_home.exists()
                assert get_sessions_dir().exists()
                assert get_memories_dir().exists()
    
    def test_ensure_workspace_dirs_idempotent(self):
        """Test that ensure_workspace_dirs is idempotent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_home = Path(tmpdir) / "test_agent"
            
            with patch.dict(os.environ, {'HANDSOME_HOME': str(custom_home)}):
                import importlib
                from shared import config
                importlib.reload(config)
                
                from shared.config import ensure_workspace_dirs
                
                # First call
                ensure_workspace_dirs()
                
                # Second call should not raise
                ensure_workspace_dirs()
                
                assert custom_home.exists()


class TestDatabasePath:
    """Test database path configuration."""
    
    def test_default_db_path(self):
        """Test default database path."""
        from shared.config import Settings, HANDSOME_HOME
        
        settings = Settings()
        
        expected_path = HANDSOME_HOME / "handsome_agent.db"
        assert settings.db_path == str(expected_path)
    
    def test_custom_db_path(self):
        """Test custom database path."""
        # This test verifies db_path is constructed from HANDSOME_HOME
        from shared.config import Settings, HANDSOME_HOME
        
        settings = Settings()
        
        # db_path should contain handsome_agent.db
        assert "handsome_agent.db" in settings.db_path
        assert settings.db_path == str(HANDSOME_HOME / "handsome_agent.db")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
