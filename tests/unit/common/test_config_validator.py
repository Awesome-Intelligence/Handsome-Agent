#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the Pydantic config validator.

Tests type validation, field constraints, and nested model validation.
"""

import pytest
from pydantic import ValidationError

from common.config_validator import (
    LLMProviderConfig,
    ModelConfig,
    TerminalConfig,
    BrowserConfig,
    SkillsConfig,
    SessionResetPolicy,
    PlatformConfig,
    MemoryConfig,
    CompressionConfig,
    DebugConfig,
    LoggingConfig,
    Settings,
)


class TestLLMProviderConfig:
    """Test LLM Provider configuration."""

    def test_default_values(self):
        """Test default configuration values."""
        config = LLMProviderConfig()
        assert config.api_key is None
        assert config.base_url is None
        assert config.model is None
        assert config.enabled is False

    def test_valid_base_url(self):
        """Test valid base_url with https."""
        config = LLMProviderConfig(base_url="https://api.example.com/v1")
        assert config.base_url == "https://api.example.com/v1"

    def test_invalid_base_url(self):
        """Test invalid base_url without scheme."""
        with pytest.raises(ValidationError) as exc_info:
            LLMProviderConfig(base_url="api.example.com")
        assert "http" in str(exc_info.value).lower()

    def test_base_url_trailing_slash(self):
        """Test that trailing slash is removed."""
        config = LLMProviderConfig(base_url="https://api.example.com/")
        assert config.base_url == "https://api.example.com"


class TestModelConfig:
    """Test Model configuration."""

    def test_valid_model_format(self):
        """Test valid model format with provider/model."""
        config = ModelConfig(default="openai/gpt-4o-mini")
        assert config.default == "openai/gpt-4o-mini"

    def test_invalid_model_format(self):
        """Test invalid model format without provider."""
        with pytest.raises(ValidationError) as exc_info:
            ModelConfig(default="gpt-4o-mini")
        assert "provider/model" in str(exc_info.value).lower()

    def test_temperature_bounds(self):
        """Test temperature bounds validation."""
        # Valid range
        config = ModelConfig(temperature=1.5)
        assert config.temperature == 1.5

        # Out of range
        with pytest.raises(ValidationError):
            ModelConfig(temperature=3.0)

    def test_max_tokens_bounds(self):
        """Test max_tokens bounds validation."""
        config = ModelConfig(max_tokens=50000)
        assert config.max_tokens == 50000

        with pytest.raises(ValidationError):
            ModelConfig(max_tokens=0)


class TestTerminalConfig:
    """Test Terminal configuration."""

    def test_valid_backend(self):
        """Test valid backend types."""
        for backend in ["local", "docker", "ssh"]:
            config = TerminalConfig(backend=backend)
            assert config.backend == backend

    def test_invalid_backend(self):
        """Test invalid backend type."""
        with pytest.raises(ValidationError):
            TerminalConfig(backend="invalid")

    def test_ssh_config_validation(self):
        """Test SSH config validation requires user when host is set."""
        # SSH host without user should fail
        with pytest.raises(ValidationError) as exc_info:
            TerminalConfig(ssh_host="example.com")
        assert "ssh_user" in str(exc_info.value).lower()

        # SSH host with user should pass
        config = TerminalConfig(ssh_host="example.com", ssh_user="root")
        assert config.ssh_host == "example.com"

    def test_timeout_bounds(self):
        """Test timeout bounds validation."""
        config = TerminalConfig(timeout=300)
        assert config.timeout == 300

        with pytest.raises(ValidationError):
            TerminalConfig(timeout=0)

        with pytest.raises(ValidationError):
            TerminalConfig(timeout=4000)


class TestBrowserConfig:
    """Test Browser configuration."""

    def test_default_values(self):
        """Test default browser configuration."""
        config = BrowserConfig()
        assert config.enabled is False
        assert config.provider == "browserbase"
        assert config.session_timeout == 300

    def test_session_timeout_bounds(self):
        """Test session timeout bounds."""
        config = BrowserConfig(session_timeout=600)
        assert config.session_timeout == 600

        with pytest.raises(ValidationError):
            BrowserConfig(session_timeout=10)  # Too low


class TestSkillsConfig:
    """Test Skills configuration."""

    def test_default_values(self):
        """Test default skills configuration."""
        config = SkillsConfig()
        assert config.external_dirs == []
        assert config.disabled == []
        assert config.auto_sync is True

    def test_external_dirs_validation(self):
        """Test external_dirs must be absolute paths."""
        # Absolute path should pass
        config = SkillsConfig(external_dirs=["/path/to/skills"])
        assert config.external_dirs == ["/path/to/skills"]

        # Relative path should fail
        with pytest.raises(ValidationError):
            SkillsConfig(external_dirs=["relative/path"])


class TestSessionResetPolicy:
    """Test Session Reset Policy configuration."""

    def test_valid_modes(self):
        """Test valid reset modes."""
        for mode in ["time", "idle", "both", "never"]:
            config = SessionResetPolicy(mode=mode)
            assert config.mode == mode

    def test_invalid_mode(self):
        """Test invalid reset mode."""
        with pytest.raises(ValidationError):
            SessionResetPolicy(mode="invalid")

    def test_at_hour_bounds(self):
        """Test at_hour bounds."""
        config = SessionResetPolicy(at_hour=12)
        assert config.at_hour == 12

        with pytest.raises(ValidationError):
            SessionResetPolicy(at_hour=24)


class TestMemoryConfig:
    """Test Memory configuration."""

    def test_default_values(self):
        """Test default memory configuration."""
        config = MemoryConfig()
        assert config.enabled is True
        assert config.max_entries == 1000
        assert config.curator_enabled is True

    def test_retrieval_weights_validation(self):
        """Test retrieval weights must sum to 1.0."""
        # Valid weights
        config = MemoryConfig(
            retrieval_fts_weight=0.3,
            retrieval_jaccard_weight=0.3,
            retrieval_hrr_weight=0.4,
        )
        assert config.retrieval_fts_weight == 0.3

        # Invalid weights
        with pytest.raises(ValidationError) as exc_info:
            MemoryConfig(
                retrieval_fts_weight=0.5,
                retrieval_jaccard_weight=0.5,
                retrieval_hrr_weight=0.5,
            )
        assert "sum to 1.0" in str(exc_info.value).lower()

    def test_semantic_retrieval_bounds(self):
        """Test semantic retrieval bounds."""
        config = MemoryConfig(
            semantic_max_results=10,
            semantic_min_score=0.5,
        )
        assert config.semantic_max_results == 10
        assert config.semantic_min_score == 0.5

        with pytest.raises(ValidationError):
            MemoryConfig(semantic_min_score=1.5)


class TestCompressionConfig:
    """Test Compression configuration."""

    def test_threshold_bounds(self):
        """Test compression threshold bounds."""
        config = CompressionConfig(threshold=0.8)
        assert config.threshold == 0.8

        with pytest.raises(ValidationError):
            CompressionConfig(threshold=0.05)

        with pytest.raises(ValidationError):
            CompressionConfig(threshold=1.1)


class TestLoggingConfig:
    """Test Logging configuration."""

    def test_valid_rotation(self):
        """Test valid rotation strategies."""
        for rotation in ["daily", "hourly", "midnight", "size"]:
            config = LoggingConfig(rotation=rotation)
            assert config.rotation == rotation

    def test_invalid_rotation(self):
        """Test invalid rotation strategy."""
        with pytest.raises(ValidationError):
            LoggingConfig(rotation="weekly")

    def test_backup_count_bounds(self):
        """Test backup count bounds."""
        config = LoggingConfig(backup_count=10)
        assert config.backup_count == 10

        with pytest.raises(ValidationError):
            LoggingConfig(backup_count=0)


class TestSettings:
    """Test Settings configuration."""

    def test_default_values(self):
        """Test default settings values."""
        settings = Settings()
        assert settings.app_name == "HandsomeAgent"
        assert settings.max_iterations == 10
        assert settings.timeout_seconds == 60.0

    def test_iterations_bounds(self):
        """Test max_iterations bounds."""
        settings = Settings(max_iterations=100)
        assert settings.max_iterations == 100

        with pytest.raises(ValidationError):
            Settings(max_iterations=0)

        with pytest.raises(ValidationError):
            Settings(max_iterations=2000)

    def test_timeout_bounds(self):
        """Test timeout_seconds bounds."""
        settings = Settings(timeout_seconds=300.0)
        assert settings.timeout_seconds == 300.0

        with pytest.raises(ValidationError):
            Settings(timeout_seconds=0.0)

    def test_computed_paths(self):
        """Test computed path properties."""
        settings = Settings()
        assert settings.sessions_dir == settings.handsome_home / "sessions"
        assert settings.memories_dir == settings.handsome_home / "memories"
        assert settings.logs_dir == settings.handsome_home / "logs"

    def test_get_nested_configs(self):
        """Test getting nested configuration models."""
        settings = Settings()

        model_config = settings.get_model_config()
        assert isinstance(model_config, ModelConfig)
        assert model_config.default == "openai/gpt-4o-mini"

        terminal_config = settings.get_terminal_config()
        assert isinstance(terminal_config, TerminalConfig)
        assert terminal_config.backend == "local"

        browser_config = settings.get_browser_config()
        assert isinstance(browser_config, BrowserConfig)
        assert browser_config.enabled is False

    def test_port_bounds(self):
        """Test port number bounds."""
        settings = Settings(gateway_port=9000)
        assert settings.gateway_port == 9000

        with pytest.raises(ValidationError):
            Settings(gateway_port=0)

        with pytest.raises(ValidationError):
            Settings(gateway_port=70000)


class TestConfigValidationExamples:
    """Test configuration validation with real-world examples."""

    def test_llm_provider_with_full_config(self):
        """Test complete LLM provider configuration."""
        config = LLMProviderConfig(
            api_key="sk-test123",
            base_url="https://api.openai.com/v1",
            model="gpt-4",
            enabled=True,
        )
        assert config.api_key == "sk-test123"
        assert config.enabled is True

    def test_memory_config_with_custom_retrieval(self):
        """Test memory configuration with custom retrieval strategy."""
        config = MemoryConfig(
            enabled=True,
            semantic_retrieval_enabled=True,
            retrieval_fts_weight=0.2,
            retrieval_jaccard_weight=0.2,
            retrieval_hrr_weight=0.6,
            retrieval_total_limit=10,
        )
        assert config.semantic_retrieval_enabled is True
        assert config.retrieval_hrr_weight == 0.6

    def test_terminal_ssh_config(self):
        """Test terminal SSH configuration."""
        config = TerminalConfig(
            backend="ssh",
            ssh_host="prod-server.example.com",
            ssh_user="deploy",
            ssh_port=2222,
            ssh_key="/home/user/.ssh/id_rsa",
            timeout=120,
        )
        assert config.backend == "ssh"
        assert config.ssh_port == 2222
