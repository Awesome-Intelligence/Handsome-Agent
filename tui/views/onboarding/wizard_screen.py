#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WizardScreen - 配置向导

🚪 Access - 💬 TUI - Views - Onboarding - WizardScreen

使用 Textual ModalScreen 和内置表单组件实现多步骤配置向导。
"""

from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Optional

from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Static,
    Input,
    Select,
)
from textual.containers import Container, VerticalScroll
from textual.message import Message
from textual.css.query import NoMatches

try:
    from common.i18n import get_i18n, reset_language_cache
except ImportError:

    def get_i18n():
        class SimpleI18n:
            def t(self, key, default=None, **kwargs):
                return default or key

        def reset_language_cache():
            pass

    reset_language_cache = reset_language_cache


from common.logging_manager import get_access_logger


try:
    from common.config import AGENT_Z_HOME, ensure_workspace_dirs
except ImportError:
    AGENT_Z_HOME = Path.home() / ".agent_z"

    def ensure_workspace_dirs():
        AGENT_Z_HOME.mkdir(parents=True, exist_ok=True)


# 支持的 AI 提供商
PROVIDERS = {
    "anthropic": {
        "display_name": "Anthropic Claude",
        "default_model": "claude-sonnet-4-20250514",
        "env_vars": ["ANTHROPIC_API_KEY"],
        "website": "https://console.anthropic.com/settings/keys",
    },
    "openai": {
        "display_name": "OpenAI GPT",
        "default_model": "gpt-4o",
        "env_vars": ["OPENAI_API_KEY"],
        "website": "https://platform.openai.com/api-keys",
    },
}

# 支持的语言
LANGUAGES = [
    ("zh", "中文 (Chinese)"),
    ("en", "English"),
    ("ja", "日本語"),
    ("ko", "한국어"),
]


WIZARD_CSS = """
WizardScreen {
    align: center middle;
    background: $primary 20%;
}

#wizard-container {
    width: 80;
    height: auto;
    max-height: 80%;
    background: $surface;
    border: solid $accent;
    padding: 1 2;
}

.step-header {
    color: $accent;
    text-style: bold;
}

.step-description {
    color: $text-muted;
    margin-top: 1;
}

.step-content {
    height: auto;
    max-height: 15;
    margin: 1 0;
    padding: 0;
}

.step-actions {
    height: auto;
    layout: horizontal;
    spacing: 1;
}

.step-actions Button {
    width: 1fr;
}

.provider-item {
    height: auto;
    padding: 0 1;
    margin: 0 0 1 0;
}

.provider-item:hover {
    background: $primary 20%;
}

.provider-item.selected {
    background: $accent 30%;
}

.provider-item .provider-name {
    text-style: bold;
    color: $text;
}

.provider-item .provider-model {
    color: $text-muted;
}

.provider-item .provider-status {
    color: $success;
}

#api-key-input {
    width: 100%;
    margin-top: 1;
}

#progress-info {
    color: $text-muted;
    margin-bottom: 1;
}

.wizard-actions {
    height: auto;
    layout: horizontal;
    spacing: 1;
    margin-top: 1;
}

.wizard-actions Button {
    width: 1fr;
}
"""


class WizardScreen(ModalScreen):
    """配置向导 ModalScreen - 4步骤引导用户完成初始配置."""

    CSS = WIZARD_CSS

    class Complete(Message):
        """配置完成消息"""

        def __init__(self, sender, config: dict):
            super().__init__()
            self.sender = sender
            self.config = config

    class Skip(Message):
        """跳过消息"""

        pass

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._logger = get_access_logger("WizardScreen", sublayer="tui")

        # 引导状态
        self._current_step = 1
        self._total_steps = 4
        self.selected_provider: Optional[str] = None
        self.selected_api_key: Optional[str] = None
        self.selected_language = "zh"
        self.trusted_directory = str(AGENT_Z_HOME)

        # 选中的提供商元素（用于高亮）
        self._selected_provider_widget: Optional[Static] = None

    def compose(self):
        yield Container(id="wizard-container")

    def on_mount(self) -> None:
        self._logger.info("WizardScreen mounted")
        self._render_step()

    def _render_step(self) -> None:
        """根据当前步骤渲染内容."""
        container = self.query_one("#wizard-container")
        container.remove_children()

        i18n = get_i18n()

        # 进度信息
        container.mount(
            Static(
                f"[dim]{i18n.t('onboarding.wizard.progress', step=self._current_step, total=self._total_steps)}[/]",
                id="progress-info",
            )
        )

        if self._current_step == 1:
            self._render_provider_step(container, i18n)
        elif self._current_step == 2:
            self._render_api_key_step(container, i18n)
        elif self._current_step == 3:
            self._render_language_step(container, i18n)
        elif self._current_step == 4:
            self._render_directory_step(container, i18n)

    def _render_provider_step(self, container: Container, i18n) -> None:
        """渲染选择提供商步骤."""
        container.mount(
            Static(
                f"[bold $accent]╔══════════════════════════════════════════╗[/]",
            )
        )
        container.mount(
            Static(
                f"[bold $accent]║[/]  [bold]{i18n.t('onboarding.provider.title')}[/]                     [bold $accent]║[/]"
            )
        )
        container.mount(
            Static(
                f"[bold $accent]╠══════════════════════════════════════════╣[/]"
            )
        )
        container.mount(
            Static(
                f"[bold $accent]║[/]  [dim]{i18n.t('onboarding.provider.description')}[/]                [bold $accent]║[/]"
            )
        )
        container.mount(
            Static(
                f"[bold $accent]╚══════════════════════════════════════════╝[/]"
            )
        )

        # 提供商列表
        with VerticalScroll(id="step-content", classes="step-content"):
            for provider_id, provider_info in PROVIDERS.items():
                display_name = provider_info.get("display_name", provider_id)
                default_model = provider_info.get("default_model", "")

                # 检查是否已配置 API Key
                env_vars = provider_info.get("env_vars", [])
                has_key = any(os.environ.get(v) for v in env_vars)
                status = "[bold green]✓[/]" if has_key else "[dim]○[/]"

                item = Static(
                    f"{status} [bold]{provider_id}[/] - {display_name}\n"
                    f"      [dim]{default_model}[/]",
                    classes="provider-item",
                )
                item._provider_id = provider_id
                container.mount(item)

        # 操作按钮
        with Container(classes="step-actions"):
            container.mount(
                Button(
                    i18n.t("onboarding.button.next"),
                    id="btn-next",
                    variant="primary",
                )
            )
            container.mount(
                Button(
                    i18n.t("onboarding.button.skip"),
                    id="btn-skip-step",
                    variant="default",
                )
            )

    def _render_api_key_step(self, container: Container, i18n) -> None:
        """渲染输入 API Key 步骤."""
        container.mount(
            Static(
                f"[bold $accent]╔══════════════════════════════════════════╗[/]",
            )
        )
        container.mount(
            Static(
                f"[bold $accent]║[/]  [bold]{i18n.t('onboarding.api_key.title')}[/]                  [bold $accent]║[/]"
            )
        )
        container.mount(
            Static(
                f"[bold $accent]╠══════════════════════════════════════════╣[/]"
            )
        )

        if self.selected_provider:
            provider_info = PROVIDERS.get(self.selected_provider, {})
            provider_name = provider_info.get("display_name", self.selected_provider)
            container.mount(
                Static(
                    f"[bold $accent]║[/]  [dim]{i18n.t('onboarding.api_key.selected_provider')}: {provider_name}[/]          [bold $accent]║[/]"
                )
            )

            website = provider_info.get("website", "")
            if website:
                container.mount(
                    Static(
                        f"[bold $accent]║[/]  [dim]{i18n.t('onboarding.api_key.get_key')}: {website}[/]          [bold $accent]║[/]"
                    )
                )

        container.mount(
            Static(
                f"[bold $accent]╚══════════════════════════════════════════╝[/]"
            )
        )

        # API Key 输入框
        with VerticalScroll(id="step-content", classes="step-content"):
            container.mount(
                Static(
                    i18n.t("onboarding.api_key.input_prompt"),
                )
            )
            container.mount(
                Input(
                    placeholder=i18n.t("onboarding.api_key.placeholder"),
                    id="api-key-input",
                    password=True,
                )
            )

        # 操作按钮
        with Container(classes="step-actions"):
            container.mount(
                Button(
                    i18n.t("onboarding.button.next"),
                    id="btn-next",
                    variant="primary",
                )
            )
            container.mount(
                Button(
                    i18n.t("onboarding.button.back"),
                    id="btn-back",
                    variant="default",
                )
            )
            container.mount(
                Button(
                    i18n.t("onboarding.button.skip"),
                    id="btn-skip-step",
                    variant="default",
                )
            )

    def _render_language_step(self, container: Container, i18n) -> None:
        """渲染选择语言步骤."""
        container.mount(
            Static(
                f"[bold $accent]╔══════════════════════════════════════════╗[/]",
            )
        )
        container.mount(
            Static(
                f"[bold $accent]║[/]  [bold]{i18n.t('onboarding.language.title')}[/]                        [bold $accent]║[/]"
            )
        )
        container.mount(
            Static(
                f"[bold $accent]╠══════════════════════════════════════════╣[/]"
            )
        )
        container.mount(
            Static(
                f"[bold $accent]║[/]  [dim]{i18n.t('onboarding.language.description')}[/]   [bold $accent]║[/]"
            )
        )
        container.mount(
            Static(
                f"[bold $accent]╚══════════════════════════════════════════╝[/]"
            )
        )

        # 语言选择
        language_options = [(label, value) for value, label in LANGUAGES]
        with VerticalScroll(id="step-content", classes="step-content"):
            container.mount(
                Select(
                    language_options,
                    id="language-select",
                    value=self.selected_language,
                )
            )

        # 操作按钮
        with Container(classes="step-actions"):
            container.mount(
                Button(
                    i18n.t("onboarding.button.next"),
                    id="btn-next",
                    variant="primary",
                )
            )
            container.mount(
                Button(
                    i18n.t("onboarding.button.back"),
                    id="btn-back",
                    variant="default",
                )
            )
            container.mount(
                Button(
                    i18n.t("onboarding.button.skip"),
                    id="btn-skip-step",
                    variant="default",
                )
            )

    def _render_directory_step(self, container: Container, i18n) -> None:
        """渲染选择工作目录步骤."""
        container.mount(
            Static(
                f"[bold $accent]╔══════════════════════════════════════════╗[/]",
            )
        )
        container.mount(
            Static(
                f"[bold $accent]║[/]  [bold]{i18n.t('onboarding.directory.title')}[/]            [bold $accent]║[/]"
            )
        )
        container.mount(
            Static(
                f"[bold $accent]╠══════════════════════════════════════════╣[/]"
            )
        )
        container.mount(
            Static(
                f"[bold $accent]║[/]  [dim]{i18n.t('onboarding.directory.description')}[/] [bold $accent]║[/]"
            )
        )
        container.mount(
            Static(
                f"[bold $accent]╚══════════════════════════════════════════╝[/]"
            )
        )

        # 目录输入
        with VerticalScroll(id="step-content", classes="step-content"):
            container.mount(
                Static(
                    f"[dim]{i18n.t('onboarding.directory.current')}:[/]"
                )
            )
            container.mount(
                Input(
                    value=self.trusted_directory,
                    id="directory-input",
                )
            )
            container.mount(
                Static(
                    f"[dim]{i18n.t('onboarding.directory.info')}[/]",
                    id="directory-info",
                )
            )

        # 操作按钮
        with Container(classes="step-actions"):
            container.mount(
                Button(
                    i18n.t("onboarding.button.finish"),
                    id="btn-finish",
                    variant="primary",
                )
            )
            container.mount(
                Button(
                    i18n.t("onboarding.button.back"),
                    id="btn-back",
                    variant="default",
                )
            )

    def _save_config(self) -> dict:
        """保存配置到文件."""
        config = {
            "provider": self.selected_provider,
            "api_key": self.selected_api_key,
            "language": self.selected_language,
            "workspace": self.trusted_directory,
            "onboarding_completed": True,
        }

        try:
            ensure_workspace_dirs()

            config_file = AGENT_Z_HOME / "config.json"

            existing_config = {}
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    existing_config = json.load(f)

            existing_config.update(config)

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(existing_config, f, indent=2, ensure_ascii=False)

            self._logger.info("Configuration saved successfully")

            reset_language_cache()

            return config
        except Exception as e:
            self._logger.error(f"Failed to save configuration: {e}")
            return config

    def _next_step(self) -> None:
        """移动到下一步."""
        if self._current_step < self._total_steps:
            self._current_step += 1
            self._render_step()

    def _prev_step(self) -> None:
        """移动到上一步."""
        if self._current_step > 1:
            self._current_step -= 1
            self._render_step()

    def _handle_provider_selection(self) -> None:
        """处理提供商选择."""
        try:
            container = self.query_one("#step-content")
            items = container.query("Static.provider-item")

            for item in items:
                item.set_class(False, "selected")

            if self._selected_provider_widget:
                self._selected_provider_widget.set_class(True, "selected")
        except NoMatches:
            pass

    def on_click(self, event) -> None:
        """处理点击事件 - 选择提供商."""
        from textual.widgets import Static

        # 检查是否点击了提供商项
        try:
            if isinstance(event.widget, Static) and hasattr(
                event.widget, "_provider_id"
            ):
                # 移除之前的选中状态
                if self._selected_provider_widget:
                    self._selected_provider_widget.set_class(False, "selected")

                self._selected_provider_widget = event.widget
                self.selected_provider = event.widget._provider_id
                self._handle_provider_selection()
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        self._logger.info(f"WizardScreen button pressed: {button_id}")

        if button_id == "btn-next":
            if self._current_step == 1:
                if not self.selected_provider:
                    # 默认选择第一个
                    self.selected_provider = "anthropic"
            elif self._current_step == 2:
                try:
                    input_widget = self.query_one("#api-key-input", Input)
                    self.selected_api_key = input_widget.value
                except NoMatches:
                    pass
            elif self._current_step == 3:
                try:
                    select_widget = self.query_one("#language-select", Select)
                    self.selected_language = select_widget.value
                except NoMatches:
                    pass
            self._next_step()

        elif button_id == "btn-back":
            self._prev_step()

        elif button_id == "btn-skip-step":
            if self._current_step == self._total_steps:
                self.post_message(self.Skip())
                self.dismiss()
            else:
                self._next_step()

        elif button_id == "btn-finish":
            try:
                input_widget = self.query_one("#directory-input", Input)
                self.trusted_directory = input_widget.value
            except NoMatches:
                pass

            config = self._save_config()
            self.post_message(self.Complete(self, config))
            self.dismiss()


__all__ = ["WizardScreen"]
