#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WelcomeScreen - 欢迎界面组件

🚪 Access - 💬 CLI - TUI Views - WelcomeScreen

提供新用户欢迎界面，包括：
- Agent 名称和版本信息
- 简短介绍
- 特色功能展示
- "开始使用"按钮
- API Key 配置入口
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Optional

# 降级机制：如果 textual 不可用，提供友好提示
try:
    from textual.app import ComposeResult
    from textual.widgets import Static, Button, Digits
    from textual.containers import Container, VerticalScroll, Grid
    from textual.message import Message
except ImportError:
    pass

# i18n 支持
try:
    from common.i18n import get_i18n, t
except ImportError:
    # 降级：简单的翻译函数
    def get_i18n():
        class SimpleI18n:
            def t(self, key, default=None, **kwargs):
                return default or key
        return SimpleI18n()
    
    def t(key, default=None, **kwargs):
        return default or key

# 日志支持
try:
    from common.logging_manager import get_access_logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    def get_access_logger(*args, **kwargs):
        return logging.getLogger("Agent")

# 主题颜色
try:
    from tui.textual_app import AVOCADO_PRIMARY, AVOCADO_BRIGHT, AVOCADO_DIM, AVOCADO_DARK, WHITE
except ImportError:
    AVOCADO_PRIMARY = "#8B9A46"
    AVOCADO_BRIGHT = "#A0B45A"
    AVOCADO_DIM = "#647030"
    AVOCADO_DARK = "#465020"
    WHITE = "white"


# ============================================================================
# WelcomeScreen CSS 样式
# ============================================================================

WELCOME_CSS = """
WelcomeScreen {
    align: center middle;
}

#welcome-container {
    width: 80;
    height: auto;
    max-height: 90%;
    background: """ + AVOCADO_DARK + """;
    border: solid """ + AVOCADO_PRIMARY + """;
    padding: 2 3;
}

#welcome-header {
    height: auto;
    width: 100%;
    margin-bottom: 1;
}

#welcome-title {
    height: 2;
    width: 100%;
    content-align: center middle;
    text-style: bold;
    color: """ + AVOCADO_BRIGHT + """;
}

#welcome-subtitle {
    height: 1;
    width: 100%;
    content-align: center middle;
    color: """ + AVOCADO_DIM + """;
}

#welcome-divider {
    height: 1;
    width: 100%;
    content-align: center middle;
    color: """ + AVOCADO_DIM + """;
}

#welcome-features {
    height: auto;
    width: 100%;
    margin: 1 0;
}

.feature-item {
    height: 1;
    width: 100%;
    color: """ + WHITE + """;
}

.feature-emoji {
    color: """ + AVOCADO_BRIGHT + """;
}

#welcome-status {
    height: auto;
    width: 100%;
    margin: 1 0;
}

.status-row {
    height: 1;
    width: 100%;
}

.status-label {
    color: """ + AVOCADO_DIM + """;
    width: 12;
}

.status-value {
    color: """ + AVOCADO_BRIGHT + """;
}

.status-warning {
    color: """ + AVOCADO_BRIGHT + """;
}

#welcome-actions {
    height: auto;
    width: 100%;
    margin-top: 1;
}

#action-buttons {
    height: auto;
    width: 100%;
    layout: horizontal;
    align: center middle;
    spacing: 2;
}

.button-primary {
    width: 18;
}

.button-secondary {
    width: 18;
}

#skip-hint {
    height: 1;
    width: 100%;
    content-align: center middle;
    color: #888888;
}
"""


# ============================================================================
# WelcomeScreen 消息类
# ============================================================================

class WelcomeScreenMessage(Message):
    """欢迎界面消息基类."""
    
    def __init__(self, screen: "WelcomeScreen") -> None:
        super().__init__()
        self.screen = screen


class StartOnboarding(WelcomeScreenMessage):
    """开始引导流程."""
    pass


class SkipOnboarding(WelcomeScreenMessage):
    """跳过引导流程."""
    pass


class OpenSettings(WelcomeScreenMessage):
    """打开设置."""
    pass


# ============================================================================
# WelcomeScreen 类
# ============================================================================

class WelcomeScreen(Static):
    """欢迎界面组件.
    
    显示 Agent 名称、版本、简介、特色功能，以及操作按钮。
    
    Attributes:
        show_api_key_status: 是否显示 API Key 状态
        has_api_key: 是否已配置 API Key
    """
    
    CSS = WELCOME_CSS
    
    def __init__(
        self,
        show_api_key_status: bool = True,
        has_api_key: bool = False,
        version: str = "0.0.1",
        **kwargs
    ):
        """初始化 WelcomeScreen.
        
        Args:
            show_api_key_status: 是否显示 API Key 配置状态
            has_api_key: 是否已配置 API Key
            version: Agent 版本号
            **kwargs: 传递给父类的其他参数
        """
        super().__init__(**kwargs)
        self.show_api_key_status = show_api_key_status
        self.has_api_key = has_api_key
        self.version = version
        self._logger = get_access_logger("WelcomeScreen", sublayer="tui")
    
    def compose(self) -> ComposeResult:
        """组合欢迎界面布局."""
        i18n = get_i18n()
        
        with Container(id="welcome-container"):
            # 标题区域
            yield Static(
                f"[bold {AVOCADO_BRIGHT}]╔══════════════════════════════════════════╗[/]",
                id="welcome-header"
            )
            
            # Agent 名称
            yield Static(
                f"[bold {AVOCADO_BRIGHT}]║[/]    [bold {AVOCADO_BRIGHT}]👤 Agent-Z[/]    [dim]v{self.version}[/]              [bold {AVOCADO_BRIGHT}]║[/]",
                id="welcome-title"
            )
            
            # 副标题
            yield Static(
                f"[bold {AVOCADO_BRIGHT}]╠══════════════════════════════════════════╣[/]"
            )
            yield Static(
                f"[bold {AVOCADO_BRIGHT}]║[/]  [dim]{i18n.t('onboarding.welcome.subtitle')}[/]          [bold {AVOCADO_BRIGHT}]║[/]"
            )
            
            # 分隔线
            yield Static(
                f"[bold {AVOCADO_BRIGHT}]╠══════════════════════════════════════════╣[/]",
                id="welcome-divider"
            )
            
            # 特色功能
            with VerticalScroll(id="welcome-features"):
                features = [
                    ("🤖", i18n.t('onboarding.welcome.feature.ai')),
                    ("💬", i18n.t('onboarding.welcome.feature.chat')),
                    ("🛠️", i18n.t('onboarding.welcome.feature.tools')),
                    ("🧠", i18n.t('onboarding.welcome.feature.memory')),
                ]
                
                for emoji, desc in features:
                    yield Static(
                        f"[bold {AVOCADO_BRIGHT}]║[/]  [bold]{emoji}[/] {desc}                              [bold {AVOCADO_BRIGHT}]║[/]",
                        classes="feature-item"
                    )
            
            # API Key 状态
            if self.show_api_key_status:
                yield Static(
                    f"[bold {AVOCADO_BRIGHT}]╠══════════════════════════════════════════╣[/]",
                    id="welcome-status"
                )
                
                if self.has_api_key:
                    status_text = f"[bold {AVOCADO_BRIGHT}]║[/]  [bold {AVOCADO_BRIGHT}]✓[/] {i18n.t('onboarding.welcome.api_key.configured')[:35]:<35}         [bold {AVOCADO_BRIGHT}]║[/]"
                else:
                    status_text = f"[bold {AVOCADO_BRIGHT}]║[/]  [bold]{i18n.t('onboarding.welcome.api_key.not_configured')[:35]:<35}         [bold {AVOCADO_BRIGHT}]║[/]"
                
                yield Static(status_text, classes="status-row")
            
            # 底部边框
            yield Static(
                f"[bold {AVOCADO_BRIGHT}]╚══════════════════════════════════════════╝[/]"
            )
            
            # 操作按钮
            with Grid(id="welcome-actions"):
                yield Button(
                    i18n.t('onboarding.welcome.button.start'),
                    id="btn-start",
                    variant="primary",
                    classes="button-primary"
                )
                yield Button(
                    i18n.t('onboarding.welcome.button.skip'),
                    id="btn-skip",
                    classes="button-secondary"
                )
            
            # 跳过提示
            yield Static(
                i18n.t('onboarding.welcome.skip_hint'),
                id="skip-hint"
            )
    
    def on_mount(self) -> None:
        """界面挂载时初始化."""
        self._logger.info("WelcomeScreen mounted")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮按下事件.
        
        Args:
            event: 按钮按下事件
        """
        button_id = event.button.id
        
        if button_id == "btn-start":
            self._logger.info("Start onboarding button pressed")
            self.post_message(StartOnboarding(self))
        elif button_id == "btn-skip":
            self._logger.info("Skip onboarding button pressed")
            self.post_message(SkipOnboarding(self))


# ============================================================================
# 模块导出
# ============================================================================

__all__ = [
    "WelcomeScreen",
    "WelcomeScreenMessage",
    "StartOnboarding",
    "SkipOnboarding",
    "OpenSettings",
    "WELCOME_CSS",
]