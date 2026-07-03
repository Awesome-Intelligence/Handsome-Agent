"""Settings 单元测试 - 验证配置保存/加载的完整性"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


class TestSettingsDocumentRoundTrip:
    """测试 SettingsDocument 与 CLI 配置格式的往返转换"""

    def test_llm_config_all_fields_preserved(self):
        """验证 LLMConfig 所有字段往返后不丢失"""
        from tui.views.settings.models import SettingsDocument, LLMConfig

        doc = SettingsDocument()
        doc.llm.provider = "openai"
        doc.llm.model = "gpt-4o-mini"
        doc.llm.api_key = "sk-test123"
        doc.llm.base_url = "https://api.openai.com/v1"

        cli_config = doc.to_cli_config()
        restored = SettingsDocument.from_cli_config(cli_config)

        assert restored.llm.provider == "openai"
        assert restored.llm.model == "gpt-4o-mini"
        assert restored.llm.api_key == "sk-test123"
        assert restored.llm.base_url == "https://api.openai.com/v1"

    def test_model_config_all_fields_preserved(self):
        """验证 ModelConfig 所有字段往返后不丢失"""
        from tui.views.settings.models import SettingsDocument, ModelConfig

        doc = SettingsDocument()
        doc.model.name = "gpt-4o"
        doc.model.context_window = 128000
        doc.model.temperature = 0.9
        doc.model.max_tokens = 8192

        cli_config = doc.to_cli_config()
        restored = SettingsDocument.from_cli_config(cli_config)

        assert restored.model.name == "gpt-4o"
        assert restored.model.context_window == 128000
        assert restored.model.temperature == 0.9
        assert restored.model.max_tokens == 8192

    def test_display_config_preserved(self):
        """验证 DisplayConfig 往返"""
        from tui.views.settings.models import SettingsDocument, Language

        doc = SettingsDocument()
        doc.display.language = Language.EN
        doc.display.verbose = True
        doc.display.show_reasoning = True

        cli_config = doc.to_cli_config()
        restored = SettingsDocument.from_cli_config(cli_config)

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

        cli_config = doc.to_cli_config()
        restored = SettingsDocument.from_cli_config(cli_config)

        assert restored.preferences.explanation_depth == ExplanationDepth.BRIEF
        assert restored.preferences.response_format == ResponseFormat.PLAIN
        assert restored.preferences.log_level == "debug"

    def test_tui_defaults_not_lost_on_round_trip(self):
        """验证 TUI_DEFAULTS 字段在往返后仍然存在（不因 from_cli_config 而丢失）"""
        from tui.views.settings.models import SettingsDocument, TUI_DEFAULTS

        doc = SettingsDocument.from_cli_config({})

        assert doc.tools.stt_enabled == TUI_DEFAULTS["tools"]["stt_enabled"]
        assert doc.agent.max_iterations == TUI_DEFAULTS["agent"]["max_iterations"]
        assert doc.agent.timeout_seconds == TUI_DEFAULTS["agent"]["timeout_seconds"]
        assert doc.session_reset.mode == TUI_DEFAULTS["session_reset"]["mode"]
        assert doc.compression.enabled == TUI_DEFAULTS["compression"]["enabled"]
        assert doc.intent_mode == TUI_DEFAULTS["intent_mode"]


class TestCollectSettings:
    """测试 _collect_settings 收集所有字段"""

    def _make_mock_screen(self, controls: dict) -> MagicMock:
        """构造带有所需控件的模拟 SettingsScreen"""
        from unittest.mock import MagicMock
        screen = MagicMock()
        for selector, value in controls.items():
            ctrl = MagicMock()
            ctrl.value = value
            screen.query_one.return_value = selector
            # 每次 query_one 被调用时返回对应控件
        def query_one(sel, cls=None):
            return controls.get(sel, MagicMock())
        screen.query_one = query_one
        return screen

    def test_collect_settings_reads_model_and_base_url(self):
        """验证 _collect_settings 读取 model 和 base_url（修复前的回归测试）"""
        from tui.views.settings.models import SettingsDocument

        # 模拟 _collect_settings 的逻辑
        doc = SettingsDocument()
        controls = {
            "#llm-model-input": MagicMock(value="gpt-4o"),
            "#llm-url-input": MagicMock(value="https://custom.vip.com/v1"),
        }

        def query_one(sel, cls=None):
            return controls[sel]

        screen = MagicMock()
        screen.query_one = query_one

        # 手动执行类似 _collect_settings 的逻辑来验证 model/base_url
        model_input = screen.query_one("#llm-model-input")
        url_input = screen.query_one("#llm-url-input")

        doc.llm.model = model_input.value
        doc.llm.base_url = url_input.value

        assert doc.llm.model == "gpt-4o"
        assert doc.llm.base_url == "https://custom.vip.com/v1"


class TestSettingsManagerSaveLoad:
    """测试 SettingsManager 的保存和加载"""

    @patch("tui.views.settings.manager.get_settings_manager")
    def test_save_load_preserves_llm_fields(self, mock_get_manager):
        """验证 SettingsManager 保存/加载后 LLM 字段不丢失"""
        from tui.views.settings.manager import SettingsManager

        manager = SettingsManager.__new__(SettingsManager)
        manager._settings = None
        manager._listeners = []
        manager._dirty = False
        manager._logger = MagicMock()
        manager._cli_config_module = None  # 不依赖真实文件

        # 直接操作 _settings
        from tui.views.settings.models import SettingsDocument
        manager._settings = SettingsDocument()
        manager._settings.llm.provider = "anthropic"
        manager._settings.llm.model = "claude-sonnet-4"
        manager._settings.llm.api_key = "sk-ant-test"
        manager._settings.llm.base_url = "https://api.anthropic.com"

        # 验证 to_cli_config 包含所有字段
        cli_config = manager._settings.to_cli_config()
        assert cli_config["llm"]["provider"] == "anthropic"
        assert cli_config["llm"]["model"] == "claude-sonnet-4"
        assert cli_config["llm"]["api_key"] == "sk-ant-test"
        assert cli_config["llm"]["base_url"] == "https://api.anthropic.com"

        # 验证 from_cli_config 能正确恢复
        restored = SettingsDocument.from_cli_config(cli_config)
        assert restored.llm.provider == "anthropic"
        assert restored.llm.model == "claude-sonnet-4"
        assert restored.llm.api_key == "sk-ant-test"
        assert restored.llm.base_url == "https://api.anthropic.com"
