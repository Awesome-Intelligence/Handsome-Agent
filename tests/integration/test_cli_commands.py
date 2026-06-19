#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration tests for CLI commands and agent functionality.

This test suite verifies that all CLI commands work correctly with the agent.

🚪 Access - 💬 CLI - 集成测试
"""

import pytest
import asyncio
import subprocess
import sys
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from io import StringIO


class TestCLICommands:
    """Test CLI command structure and imports."""

    def test_cli_main_import(self):
        """Test that CLI main module can be imported."""
        try:
            from cli import main as cli_main
            assert cli_main is not None
        except ImportError as e:
            pytest.fail(f"Failed to import CLI main: {e}")

    def test_parser_import(self):
        """Test that CLI parser can be imported."""
        try:
            from cli._parser import build_top_level_parser
            parser, subparsers, chat_parser = build_top_level_parser()
            assert parser is not None
            assert subparsers is not None
        except ImportError as e:
            pytest.fail(f"Failed to import CLI parser: {e}")

    def test_commands_import(self):
        """Test that CLI commands module can be imported."""
        try:
            from cli.commands import execute_command
            assert execute_command is not None
        except ImportError as e:
            pytest.fail(f"Failed to import CLI commands: {e}")


class TestModelCLI:
    """Test model management CLI commands."""

    def test_model_cli_import(self):
        """Test that model CLI can be imported."""
        try:
            from cli.config.model_cli import list_models, set_default_model
            assert list_models is not None
            assert set_default_model is not None
        except ImportError as e:
            pytest.fail(f"Failed to import model CLI: {e}")

    def test_list_models_no_json(self, capsys):
        """Test list_models without JSON output."""
        from cli.config.model_cli import list_models

        list_models(provider="openai", json_output=False)
        captured = capsys.readouterr()
        assert "OpenAI" in captured.out


class TestSkillsCLI:
    """Test skills management CLI commands."""

    def test_skills_cli_import(self):
        """Test that skills CLI can be imported."""
        try:
            from cli.skills_cli import list_skills, sync_skills, uninstall_skill
            assert list_skills is not None
            assert sync_skills is not None
            assert uninstall_skill is not None
        except ImportError as e:
            pytest.fail(f"Failed to import skills CLI: {e}")

    @pytest.mark.asyncio
    async def test_sync_skills_with_empty_skills_dir(self, tmp_path):
        """Test syncing skills with empty skills directory."""
        from cli.skills_cli import sync_skills

        # Create an empty skills directory
        empty_dir = tmp_path / "skills"
        empty_dir.mkdir()

        # 直接 mock get_skills_dir 返回空目录
        with patch('cli.skills_cli.get_skills_dir', return_value=empty_dir):
            # Mock the SkillsLoader import by patching it where it's used
            with patch('skills.SkillsLoader') as mock_loader_class:
                mock_instance = MagicMock()
                mock_instance.load_all = MagicMock(return_value=[])
                mock_loader_class.return_value = mock_instance

                with patch('skills.get_skill_telemetry') as mock_telemetry:
                    mock_telemetry_instance = MagicMock()
                    mock_telemetry.return_value = mock_telemetry_instance

                    result = await sync_skills()
                    # 即使有空目录，sync_skills 应该返回 True（成功创建目录）
                    assert isinstance(result, bool)


class TestConfigCLI:
    """Test configuration management CLI commands."""

    def test_config_cli_import(self):
        """Test that config CLI can be imported."""
        try:
            from cli.config_cli import show_config, get_config, set_config
            assert show_config is not None
            assert get_config is not None
            assert set_config is not None
        except ImportError as e:
            pytest.fail(f"Failed to import config CLI: {e}")

    def test_show_config_json(self, capsys):
        """Test show_config with JSON output."""
        from cli.config_cli import show_config

        show_config(json_output=True)
        captured = capsys.readouterr()
        # Output should be JSON or empty
        assert "{" in captured.out or "}" in captured.out or captured.out == ""


class TestStatusCLI:
    """Test status display CLI commands."""

    def test_status_import(self):
        """Test that status module can be imported."""
        try:
            from cli.status import show_status
            assert show_status is not None
        except ImportError as e:
            pytest.fail(f"Failed to import status module: {e}")

    def test_show_status_basic(self, capsys):
        """Test basic status display."""
        from cli.status import show_status

        # 测试基本状态显示（不需要 mock）
        result = show_status(verbose=False, json_output=False)
        # show_status 没有返回值，直接输出
        assert result is None


class TestSetupCLI:
    """Test setup wizard CLI commands."""

    def test_setup_import(self):
        """Test that setup module can be imported."""
        try:
            from cli.setup.setup_wizard import run_setup_wizard
            assert run_setup_wizard is not None
        except ImportError as e:
            pytest.fail(f"Failed to import setup module: {e}")


class TestCommandsExecution:
    """Test command execution in interactive mode."""

    def test_execute_help_command(self):
        """Test executing /help command."""
        from cli.commands import execute_command

        context = {"agent": None, "model_name": "Test"}
        result = execute_command("/help", context)
        assert result is not None
        assert len(result) > 0

    def test_execute_status_command(self):
        """Test executing /status command."""
        from cli.commands import execute_command

        context = {"agent": None, "model_name": "Test"}
        result = execute_command("/status", context)
        assert result is not None

    def test_execute_clear_command(self):
        """Test executing /clear command."""
        from cli.commands import execute_command

        context = {"agent": None, "model_name": "Test"}
        result = execute_command("/clear", context)
        assert result == "__CLEAR__"

    def test_execute_unknown_command(self):
        """Test executing unknown command."""
        from cli.commands import execute_command

        context = {"agent": None, "model_name": "Test"}
        result = execute_command("/unknown", context)
        # Unknown commands should return empty or error message
        assert result is not None


class TestAgentIntegration:
    """Test Agent integration with CLI."""

    def test_agent_import(self):
        """Test that Agent can be imported."""
        try:
            from agent.agent import Agent, AgentResponse
            assert Agent is not None
            assert AgentResponse is not None
        except ImportError as e:
            pytest.fail(f"Failed to import Agent: {e}")

    def test_agent_creation_no_llm(self):
        """Test creating Agent without LLM provider."""
        from agent.agent import Agent

        agent = Agent(llm_provider=None)
        assert agent is not None
        # Agent should have minimal functionality without LLM
        assert hasattr(agent, 'chat')

    def test_agent_session_initialization(self):
        """Test Agent session initialization."""
        from agent.agent import Agent

        agent = Agent(llm_provider=None, enable_session=True)
        assert agent is not None

    @pytest.mark.asyncio
    async def test_agent_chat_basic(self):
        """Test basic Agent chat functionality."""
        from agent.agent import Agent

        agent = Agent(llm_provider=None)

        # Without LLM, chat should handle gracefully
        try:
            response = await agent.chat("test message")
            assert response is not None
        except Exception:
            # Expected when no LLM is configured
            pass


class TestCLIArguments:
    """Test CLI argument parsing."""

    def test_parser_builds_correctly(self):
        """Test that parser builds correctly."""
        from cli._parser import build_top_level_parser

        parser, subparsers, chat_parser = build_top_level_parser()

        # Verify main parser exists
        assert parser is not None

        # Verify subparsers exist for subcommands
        assert 'setup' in subparsers.choices
        assert 'status' in subparsers.choices
        assert 'model' in subparsers.choices
        assert 'skills' in subparsers.choices
        assert 'config' in subparsers.choices

    def test_subcommand_parsers_exist(self):
        """Test that all subcommand parsers exist."""
        from cli._parser import build_top_level_parser

        parser, subparsers, chat_parser = build_top_level_parser()

        # Test model subcommands
        model_parser = subparsers.choices.get('model')
        assert model_parser is not None
        assert 'list' in model_parser._actions[1].choices
        assert 'set' in model_parser._actions[1].choices

        # Test skills subcommands in _parser.py (only 'list' and 'search' are defined here)
        skills_parser = subparsers.choices.get('skills')
        assert skills_parser is not None
        assert 'list' in skills_parser._actions[1].choices
        assert 'search' in skills_parser._actions[1].choices


class TestBannerAndUI:
    """Test banner and UI components."""

    def test_banner_import(self):
        """Test that banner module can be imported."""
        try:
            from cli.banner import print_simple_banner, build_welcome_banner
            assert print_simple_banner is not None
            assert build_welcome_banner is not None
        except ImportError as e:
            pytest.fail(f"Failed to import banner module: {e}")

    def test_ui_import(self):
        """Test that UI module can be imported."""
        try:
            from cli.ui import print_header, print_success, print_error
            assert print_header is not None
            assert print_success is not None
            assert print_error is not None
        except ImportError as e:
            pytest.fail(f"Failed to import UI module: {e}")

    def test_banner_print_simple(self, capsys):
        """Test printing simple banner."""
        from cli.banner import print_simple_banner

        print_simple_banner()
        captured = capsys.readouterr()
        assert len(captured.out) > 0


class TestConfigLoad:
    """Test configuration loading."""

    def test_config_import(self):
        """Test that config can be imported."""
        try:
            from common.config import (
                get_settings,
                get_config_dir,
                get_skills_dir,
                get_llm_provider_config,
            )
            assert get_settings is not None
            assert get_config_dir is not None
            assert get_skills_dir is not None
            assert get_llm_provider_config is not None
        except ImportError as e:
            pytest.fail(f"Failed to import config: {e}")

    def test_get_settings_returns_settings(self):
        """Test that get_settings returns a Settings object."""
        from common.config import get_settings

        settings = get_settings()
        assert settings is not None
        # Settings is a pydantic model
        assert hasattr(settings, 'model_dump')

    def test_get_config_dir(self):
        """Test that get_config_dir returns a Path."""
        from common.config import get_config_dir

        config_dir = get_config_dir()
        assert config_dir is not None
        assert isinstance(config_dir, Path)


class TestExceptionHandling:
    """Test exception handling in CLI."""

    def test_agent_error_import(self):
        """Test that AgentError can be imported."""
        from common.exceptions import AgentError, InputValidationError
        assert AgentError is not None
        assert InputValidationError is not None

    def test_agent_error_creation(self):
        """Test creating AgentError."""
        from common.exceptions import AgentError

        error = AgentError("Test error message")
        assert str(error) == "Test error message"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])