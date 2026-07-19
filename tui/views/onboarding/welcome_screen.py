#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WelcomeScreen - 欢迎界面

🚪 Access - 💬 TUI - Views - Onboarding - WelcomeScreen

使用 Textual ModalScreen 实现欢迎界面。
"""

from __future__ import annotations

from textual.screen import ModalScreen
from textual.widgets import Button, Static
from textual.containers import Container
from textual.message import Message
from textual.css.query import NoMatches

try:
    from common.i18n import get_i18n
except ImportError:

    def get_i18n():
        class SimpleI18n:
            def t(self, key, default=None, **kwargs):
                return default or key

        return SimpleI18n()


try:
    from common.logging_manager import get_access_logger
except ImportError:
    import logging

    logging.basicConfig(level=logging.INFO)

    def get_access_logger(*args, **kwargs):
        return logging.getLogger("WelcomeScreen")


WELCOME_CSS = """
WelcomeScreen {
    align: center middle;
    background: $primary 20%;
}

#welcome-container {
    width: 70;
    height: auto;
    background: $surface;
    border: solid $accent;
    padding: 1 2;
}

.welcome-title {
    color: $accent;
    text-style: bold;
}

.welcome-subtitle {
    color: $text-muted;
}

.welcome-version {
    color: $text-disabled;
}

.welcome-features {
    height: auto;
    layout: vertical;
}

.feature-item {
    height: auto;
    layout: horizontal;
}

.feature-icon {
    width: 4;
    color: $accent;
}

.feature-text {
    width: 1fr;
    color: $text;
}

.welcome-actions {
    height: auto;
    layout: horizontal;
}

.welcome-actions Button {
    width: 1fr;
}

#skip-hint {
    color: $text-disabled;
    text-style: italic;
}
"""


class WelcomeScreen(ModalScreen):
    """欢迎界面 ModalScreen."""

    CSS = WELCOME_CSS

    class StartOnboarding(Message):
        """开始引导流程消息"""

        pass

    class SkipOnboarding(Message):
        """跳过引导流程消息"""

        pass

    def __init__(
        self,
        version: str = "0.0.1",
        has_api_key: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._version = version
        self._has_api_key = has_api_key
        self._logger = get_access_logger("WelcomeScreen", sublayer="tui")

    def compose(self):
        i18n = get_i18n()
        api_key_status = (
            i18n.t("onboarding.welcome.api_key.configured")
            if self._has_api_key
            else i18n.t("onboarding.welcome.api_key.not_configured")
        )

        with Container(id="welcome-container"):
            yield Static(
                f"[bold $accent]╔══════════════════════════════════════════╗[/]",
                id="welcome-header",
            )
            yield Static(
                f"[bold $accent]║[/]    [bold $accent]👤 Agent-Z[/]    [dim]v{self._version}[/]              [bold $accent]║[/]"
            )
            yield Static(
                f"[bold $accent]║[/]  [dim]{i18n.t('onboarding.welcome.subtitle')}[/]        [bold $accent]║[/]"
            )
            yield Static(f"[bold $accent]║[/]  [dim]{'-' * 40}[/]        [bold $accent]║[/]")

            with Container(classes="welcome-features"):
                features = [
                    ("🤖", i18n.t("onboarding.welcome.feature.ai")),
                    ("💬", i18n.t("onboarding.welcome.feature.chat")),
                    ("🛠️", i18n.t("onboarding.welcome.feature.tools")),
                    ("🧠", i18n.t("onboarding.welcome.feature.memory")),
                ]
                for icon, text in features:
                    with Container(classes="feature-item"):
                        yield Static(f"[bold $accent]│[/] [dim]{icon}[/]", classes="feature-icon")
                        yield Static(f"[dim]{text}[/]", classes="feature-text")

            yield Static(f"[bold $accent]╠══════════════════════════════════════════╣[/]")
            status_text = f"[bold $accent]✓[/] {api_key_status}"
            yield Static(f"[bold $accent]║[/]  {status_text:<40}  [bold $accent]║[/]")
            yield Static(f"[bold $accent]╚══════════════════════════════════════════╝[/]")

            with Container(classes="welcome-actions"):
                yield Button(
                    i18n.t("onboarding.welcome.button.start"),
                    id="btn-start",
                    variant="primary",
                )
                yield Button(
                    i18n.t("onboarding.welcome.button.skip"),
                    id="btn-skip",
                    variant="default",
                )

            yield Static(
                i18n.t("onboarding.welcome.skip_hint"),
                id="skip-hint",
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        self._logger.info(f"WelcomeScreen button pressed: {button_id}")

        if button_id == "btn-start":
            self.post_message(self.StartOnboarding())
            self.dismiss()
        elif button_id == "btn-skip":
            self.post_message(self.SkipOnboarding())
            self.dismiss()


__all__ = ["WelcomeScreen"]
