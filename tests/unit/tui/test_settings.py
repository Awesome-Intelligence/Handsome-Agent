"""Settings 单元测试 - 验证配置保存/加载的完整性"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


class TestSettingsDocumentRoundTrip:
    """测试 SettingsDocument 与 CLI 配置格式的往返转换"""

    def test_llm_config_all_fields_preserved(self):
        """验证 LLMConfig 所有字段往返后不丢失"""
        from tui.views.settings.models import SettingsDocument, ProviderItemConfig

        doc = SettingsDocument()
        doc.llm.provider = "openai"
        doc.llm.model = "gpt-4o-mini"
        # credentials 现在在 providers.<name> 下
        doc.providers.items["openai"] = ProviderItemConfig(
            api_key="sk-test123",
            base_url="https://api.openai.com/v1",
        )

        cli_config = doc.to_dict()
        restored = SettingsDocument.from_dict(cli_config)

        assert restored.llm.provider == "openai"
        assert restored.llm.model == "gpt-4o-mini"
        assert restored.providers.items["openai"].api_key == "sk-test123"
        assert restored.providers.items["openai"].base_url == "https://api.openai.com/v1"

    def test_model_settings_config_all_fields_preserved(self):
        """验证 ModelSettingsConfig 所有字段往返后不丢失"""
        from tui.views.settings.models import SettingsDocument

        doc = SettingsDocument()
        doc.model_settings.name = "gpt-4o"
        doc.model_settings.context_window = 128000
        doc.model_settings.temperature = 0.9
        doc.model_settings.max_tokens = 8192

        cli_config = doc.to_dict()
        restored = SettingsDocument.from_dict(cli_config)

        assert restored.model_settings.name == "gpt-4o"
        assert restored.model_settings.context_window == 128000
        assert restored.model_settings.temperature == 0.9
        assert restored.model_settings.max_tokens == 8192

    def test_display_config_preserved(self):
        """验证 DisplayConfig 往返"""
        from tui.views.settings.models import SettingsDocument, Language

        doc = SettingsDocument()
        doc.display.language = Language.EN
        doc.display.verbose = True
        doc.display.show_reasoning = True

        cli_config = doc.to_dict()
        restored = SettingsDocument.from_dict(cli_config)

        assert restored.display.language == Language.EN
        assert restored.display.verbose is True
        assert restored.display.show_reasoning is True

    def test_preferences_config_preserved(self):
        """验证 PreferencesConfig 往返"""
        from tui.views.settings.models import SettingsDocument, ExplanationDepth, ResponseFormat

        doc = SettingsDocument()
        doc.preferences.explanation_depth = ExplanationDepth.BRIEF
        doc.preferences.response_format = ResponseFormat.PLAIN
        doc.preferences.log_level = "debug"

        cli_config = doc.to_dict()
        restored = SettingsDocument.from_dict(cli_config)

        assert restored.preferences.explanation_depth == ExplanationDepth.BRIEF
        assert restored.preferences.response_format == ResponseFormat.PLAIN
        assert restored.preferences.log_level == "debug"

    def test_tui_defaults_not_lost_on_round_trip(self):
        """验证 TUI 专用配置字段在往返后仍然存在"""
        from tui.views.settings.models import SettingsDocument, TUI_DEFAULTS

        doc = SettingsDocument.from_dict({})

        # tools 是 TUI 专用配置，有默认值
        assert doc.tools.stt_enabled is False
        assert doc.tools.tts_enabled is False
        assert doc.tools.browser_enabled is False
        # agent 字段有默认值
        assert doc.agent.max_turns == 90
        assert doc.agent.gateway_timeout == 1800
        # compression 字段有默认值
        assert doc.compression.enabled is True
        assert doc.compression.threshold == 0.50
        # intent_mode 来自 TUI_DEFAULTS
        assert doc.intent_mode.value == TUI_DEFAULTS["intent_mode"]

    def test_new_config_fields_preserved(self):
        """验证新增配置字段往返后不丢失"""
        from tui.views.settings.models import SettingsDocument

        doc = SettingsDocument()
        # agent 新字段
        doc.agent.gateway_auto_continue_freshness = 7200
        # terminal 新字段
        doc.terminal.home_mode = "real"
        doc.terminal.container_cpu = 4
        doc.terminal.docker_env = {"FOO": "bar"}
        # compression 新字段
        doc.compression.threshold = 0.6
        doc.compression.target_ratio = 0.25
        # browser 新字段
        doc.browser.command_timeout = 60
        doc.browser.camofox.managed_persistence = True

        cli_config = doc.to_dict()
        restored = SettingsDocument.from_dict(cli_config)

        assert restored.agent.gateway_auto_continue_freshness == 7200
        assert restored.terminal.home_mode == "real"
        assert restored.terminal.container_cpu == 4
        assert restored.terminal.docker_env == {"FOO": "bar"}
        assert restored.compression.threshold == 0.6
        assert restored.compression.target_ratio == 0.25
        assert restored.browser.command_timeout == 60
        assert restored.browser.camofox.managed_persistence is True


class TestCollectSettings:
    """测试 _collect_settings 收集所有字段"""

    def test_collect_settings_reads_model_and_base_url(self):
        """验证 _collect_settings 读取 model 和 base_url"""
        from tui.views.settings.models import SettingsDocument, ProviderItemConfig

        doc = SettingsDocument()
        doc.llm.provider = "openai"
        doc.llm.model = "gpt-4o"
        doc.providers.items["openai"] = ProviderItemConfig(
            base_url="https://custom.vip.com/v1"
        )

        assert doc.llm.model == "gpt-4o"
        assert doc.providers.items["openai"].base_url == "https://custom.vip.com/v1"


class TestSettingsManagerSaveLoad:
    """测试 SettingsManager 的保存和加载"""

    @patch("tui.views.settings.manager.get_settings_manager")
    def test_save_load_preserves_llm_fields(self, mock_get_manager):
        """验证 SettingsManager 保存/加载后 LLM 字段不丢失"""
        from tui.views.settings.manager import SettingsManager
        from tui.views.settings.models import SettingsDocument, ProviderItemConfig

        manager = SettingsManager.__new__(SettingsManager)
        manager._settings = None
        manager._listeners = []
        manager._dirty = False
        manager._logger = MagicMock()
        manager._cli_config_module = None

        manager._settings = SettingsDocument()
        manager._settings.llm.provider = "anthropic"
        manager._settings.llm.model = "claude-sonnet-4"
        manager._settings.providers.items["anthropic"] = ProviderItemConfig(
            api_key="sk-ant-test",
            base_url="https://api.anthropic.com",
        )

        cli_config = manager._settings.to_dict()
        assert cli_config["llm"]["provider"] == "anthropic"
        assert cli_config["llm"]["model"] == "claude-sonnet-4"
        assert cli_config["providers"]["anthropic"]["api_key"] == "sk-ant-test"
        assert cli_config["providers"]["anthropic"]["base_url"] == "https://api.anthropic.com"

        restored = SettingsDocument.from_dict(cli_config)
        assert restored.llm.provider == "anthropic"
        assert restored.llm.model == "claude-sonnet-4"
        assert restored.providers.items["anthropic"].api_key == "sk-ant-test"
        assert restored.providers.items["anthropic"].base_url == "https://api.anthropic.com"
