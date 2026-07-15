#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for common.llm_providers.catalog

🚪 Access - 💬 Tests - Common - LLM Providers

覆盖：
- PROVIDERS 字典结构与必需字段
- get_provider_ids() / get_provider_info() 行为
- CLI 兼容层（cli.cli_commands.providers）仍能正常导出 PROVIDERS
- tui/views/settings_screen.py 不再反向 import cli
"""

from __future__ import annotations

import importlib


class TestCatalogData:
    """Provider 元数据完整性测试。"""

    def test_providers_dict_non_empty(self):
        from common.llm_providers import PROVIDERS

        assert isinstance(PROVIDERS, dict)
        assert len(PROVIDERS) >= 5

    def test_each_provider_has_required_fields(self):
        from common.llm_providers import PROVIDERS

        required = {"name", "display_name", "models", "default_model"}
        for pid, meta in PROVIDERS.items():
            assert isinstance(pid, str)
            assert isinstance(meta, dict)
            missing = required - set(meta.keys())
            assert not missing, f"Provider '{pid}' missing fields: {missing}"

    def test_each_provider_models_non_empty(self):
        from common.llm_providers import PROVIDERS

        for pid, meta in PROVIDERS.items():
            models = meta.get("models", [])
            assert models, f"Provider '{pid}' has empty models list"
            assert meta["default_model"] in models, (
                f"Provider '{pid}': default_model "
                f"'{meta['default_model']}' not in models {models}"
            )

    def test_each_provider_env_vars_is_list(self):
        from common.llm_providers import PROVIDERS

        for pid, meta in PROVIDERS.items():
            env_vars = meta.get("env_vars", [])
            assert isinstance(env_vars, list)
            for v in env_vars:
                assert isinstance(v, str)
                assert v.isupper() or "_" in v, (
                    f"Provider '{pid}' env_var '{v}' not uppercase"
                )


class TestQueryFunctions:
    """纯查询函数行为测试。"""

    def test_get_provider_ids_sorted(self):
        from common.llm_providers import PROVIDERS, get_provider_ids

        ids = get_provider_ids()
        assert ids == sorted(ids)
        assert set(ids) == set(PROVIDERS.keys())

    def test_get_provider_info_returns_dict(self):
        from common.llm_providers import get_provider_info

        info = get_provider_info("openai")
        assert info is not None
        assert info["name"] == "OpenAI"
        assert "gpt-4o" in info["models"]

    def test_get_provider_info_returns_none_for_unknown(self):
        from common.llm_providers import get_provider_info

        assert get_provider_info("nonexistent_provider") is None


class TestBackwardsCompat:
    """向后兼容：旧导入路径仍可用。"""

    def test_cli_compat_layer_exports_providers(self):
        """cli.cli_commands.providers.PROVIDERS 必须指向同一字典对象。"""
        cli_providers = importlib.import_module("cli.cli_commands.providers")
        common_providers = importlib.import_module("common.llm_providers")

        assert cli_providers.PROVIDERS is common_providers.PROVIDERS

    def test_cli_compat_layer_exposes_functions(self):
        cli_providers = importlib.import_module("cli.cli_commands.providers")

        for name in ("list_providers", "get_provider_info",
                     "check_provider_status", "search_provider"):
            assert hasattr(cli_providers, name), f"Missing: {name}"


class TestReverseDependencyCleared:
    """tui/ 下不再反向 import cli/。"""

    def test_tui_views_no_longer_import_cli(self):
        """settings_screen.py 应该从 common.llm_providers 导入，而非 cli.cli_commands.providers。"""
        settings_path = "tui/views/settings_screen.py"
        import pathlib

        src = pathlib.Path(settings_path).read_text(encoding="utf-8")
        assert "from cli.cli_commands.providers" not in src, (
            f"{settings_path} still imports cli.cli_commands.providers"
        )
        assert "from common.llm_providers" in src, (
            f"{settings_path} should import from common.llm_providers"
        )

    def test_app_py_no_longer_imports_cli_config(self):
        import pathlib

        src = pathlib.Path("tui/textual_app/app.py").read_text(encoding="utf-8")
        assert "from cli.config.config import load_config" not in src

    def test_settings_manager_no_longer_imports_cli_config(self):
        import pathlib

        src = pathlib.Path(
            "tui/views/settings/manager.py"
        ).read_text(encoding="utf-8")
        assert "from cli.config.config import load_config" not in src