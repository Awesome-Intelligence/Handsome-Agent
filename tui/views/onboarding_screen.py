#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OnboardingScreen - 首次使用引导流程

🚪 Access - 💬 CLI - TUI Views - OnboardingScreen

提供多步骤向导界面，帮助用户完成初始配置：
- 选择 LLM 提供商
- 配置 API Key
- 选择界面语言
- 信任工作目录
- 保存配置
"""

from __future__ import annotations

import json
import os
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Optional

# 降级机制：如果 textual 不可用，提供友好提示
try:
    from textual.app import ComposeResult
    from textual.widgets import (
        Static, Button, Input, RadioButton, RadioSet, ProgressBar,
        Rule, Sparkline
    )
    from textual.containers import Container, VerticalScroll, Grid, Horizontal
    from textual.message import Message
except ImportError:
    pass

# i18n 支持
try:
    from common.i18n import get_i18n, t, reset_language_cache
except ImportError:
    # 降级：简单的翻译函数
    def get_i18n():
        class SimpleI18n:
            def t(self, key, default=None, **kwargs):
                return default or key
        return SimpleI18n()
    
    def t(key, default=None, **kwargs):
        return default or key
    
    def reset_language_cache():
        pass

# 日志支持
try:
    from common.logging_manager import get_access_logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    def get_access_logger(*args, **kwargs):
        return logging.getLogger("Agent")

# 配置支持
try:
    from common.config import AGENT_Z_HOME, ensure_workspace_dirs
except ImportError:
    AGENT_Z_HOME = Path.home() / ".agent_z"
    def ensure_workspace_dirs():
        AGENT_Z_HOME.mkdir(parents=True, exist_ok=True)

# Provider 定义
try:
    from tui.providers import PROVIDERS
except ImportError:
    PROVIDERS = {}

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
# 引导步骤枚举
# ============================================================================

class OnboardingStep(Enum):
    """引导步骤枚举."""
    WELCOME = "welcome"           # 欢迎页
    SELECT_PROVIDER = "provider"  # 选择 LLM 提供商
    INPUT_API_KEY = "api_key"     # 输入 API Key
    SELECT_LANGUAGE = "language"  # 选择界面语言
    TRUST_DIRECTORY = "directory" # 信任工作目录
    COMPLETE = "complete"         # 完成


# ============================================================================
# OnboardingScreen CSS 样式
# ============================================================================

ONBOARDING_CSS = """
OnboardingScreen {
    align: center middle;
}

#onboarding-container {
    width: 80;
    height: auto;
    max-height: 90%;
    background: """ + AVOCADO_DARK + """;
    border: solid """ + AVOCADO_PRIMARY + """;
    padding: 2 3;
}

#progress-bar {
    height: 2;
    width: 100%;
    margin-bottom: 1;
}

#step-header {
    height: auto;
    width: 100%;
    margin-bottom: 1;
}

#step-title {
    height: 2;
    width: 100%;
    content-align: center middle;
    text-style: bold;
    color: """ + AVOCADO_BRIGHT + """;
}

#step-description {
    height: auto;
    width: 100%;
    content-align: center middle;
    color: """ + WHITE + """;
    margin-bottom: 1;
}

#step-content {
    height: auto;
    width: 100%;
    margin: 1 0;
}

.provider-list {
    height: auto;
    width: 100%;
    padding: 0 2;
}

.provider-item {
    height: 3;
    width: 100%;
    background: """ + AVOCADO_DIM + """;
    border: solid """ + AVOCADO_PRIMARY + """;
    margin: 0 0 1 0;
    padding: 0 1;
}

.provider-item:hover {
    background: """ + AVOCADO_PRIMARY + """;
}

.provider-item.selected {
    background: """ + AVOCADO_PRIMARY + """;
    border: solid """ + AVOCADO_BRIGHT + """;
}

.provider-name {
    color: """ + WHITE + """;
    text-style: bold;
}

.provider-models {
    color: """ + AVOCADO_DIM + """;
}

#api-key-input {
    width: 100%;
    border: solid """ + AVOCADO_PRIMARY + """;
    margin: 1 0;
}

#api-key-input:focus {
    border: solid """ + AVOCADO_BRIGHT + """;
}

.language-options {
    height: auto;
    width: 100%;
    padding: 0 2;
}

.language-item {
    height: 2;
    width: 100%;
    background: """ + AVOCADO_DIM + """;
    border: solid """ + AVOCADO_PRIMARY + """;
    margin: 0 0 1 0;
    padding: 0 1;
}

.language-item:hover {
    background: """ + AVOCADO_PRIMARY + """;
}

.language-item.selected {
    background: """ + AVOCADO_PRIMARY + """;
    border: solid """ + AVOCADO_BRIGHT + """;
}

.directory-info {
    height: auto;
    width: 100%;
    padding: 0 2;
}

.directory-path {
    color: """ + AVOCADO_BRIGHT + """;
}

#step-actions {
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
    width: 15;
}

.button-secondary {
    width: 15;
}

.button-back {
    width: 15;
}

#completion-icon {
    height: 4;
    width: 100%;
    content-align: center middle;
}

#completion-message {
    height: auto;
    width: 100%;
    content-align: center middle;
    color: """ + AVOCADO_BRIGHT + """;
}

RadioSet {
    height: auto;
    width: 100%;
}

RadioButton {
    margin: 0 0 1 0;
}
"""


# ============================================================================
# OnboardingScreen 消息类
# ============================================================================

class OnboardingMessage(Message):
    """引导流程消息基类."""
    
    def __init__(self, screen: "OnboardingScreen") -> None:
        super().__init__()
        self.screen = screen


class OnboardingComplete(OnboardingMessage):
    """引导流程完成."""
    pass


class OnboardingSkipped(OnboardingMessage):
    """引导流程被跳过."""
    pass


class ConfigurationSaved(OnboardingMessage):
    """配置已保存."""
    
    def __init__(self, screen: "OnboardingScreen", config: dict) -> None:
        super().__init__(screen)
        self.config = config


# ============================================================================
# OnboardingScreen 类
# ============================================================================

class OnboardingScreen(Container):
    """首次使用引导界面.
    
    提供多步骤向导，帮助用户完成初始配置。
    
    Attributes:
        current_step: 当前步骤
        selected_provider: 选中的提供商
        selected_language: 选中的语言
        trusted_directory: 信任的目录
    """
    
    CSS = ONBOARDING_CSS
    
    # 支持的语言列表
    LANGUAGES = [
        ("zh", "中文 (Chinese)"),
        ("en", "English"),
        ("ja", "日本語"),
        ("ko", "한국어"),
    ]
    
    def __init__(self, **kwargs):
        """初始化 OnboardingScreen."""
        super().__init__(**kwargs)
        self._logger = get_access_logger("OnboardingScreen", sublayer="tui")
        
        # 引导状态
        self.current_step = OnboardingStep.WELCOME
        self.selected_provider: Optional[str] = None
        self.selected_api_key: Optional[str] = None
        self.selected_language = "zh"
        self.trusted_directory = str(AGENT_Z_HOME)
        
        # 所有步骤
        self._all_steps = [
            OnboardingStep.WELCOME,
            OnboardingStep.SELECT_PROVIDER,
            OnboardingStep.INPUT_API_KEY,
            OnboardingStep.SELECT_LANGUAGE,
            OnboardingStep.TRUST_DIRECTORY,
            OnboardingStep.COMPLETE,
        ]
    
    def compose(self) -> ComposeResult:
        """组合引导界面布局."""
        yield Container(id="onboarding-container")
    
    def on_mount(self) -> None:
        """界面挂载时初始化."""
        self._logger.info("OnboardingScreen mounted")
        self._render_current_step()
    
    def _get_step_index(self, step: OnboardingStep) -> int:
        """获取步骤索引."""
        return self._all_steps.index(step)
    
    def _get_progress(self) -> float:
        """获取进度 (0.0 - 1.0)."""
        current_idx = self._get_step_index(self.current_step)
        return (current_idx + 1) / len(self._all_steps)
    
    def _render_current_step(self) -> None:
        """渲染当前步骤内容."""
        container = self.query_one("#onboarding-container")
        container.remove_children()
        
        i18n = get_i18n()
        
        # 进度条（除了欢迎页和完成页）
        if self.current_step not in (OnboardingStep.WELCOME, OnboardingStep.COMPLETE):
            progress = self._get_progress()
            progress_bar = ProgressBar(
                total=100,
                progress=int(progress * 100),
                show_eta=False,
                id="progress-bar"
            )
            container.mount(progress_bar)
        
        # 根据步骤渲染不同内容
        if self.current_step == OnboardingStep.WELCOME:
            self._render_welcome_step(container, i18n)
        elif self.current_step == OnboardingStep.SELECT_PROVIDER:
            self._render_provider_step(container, i18n)
        elif self.current_step == OnboardingStep.INPUT_API_KEY:
            self._render_api_key_step(container, i18n)
        elif self.current_step == OnboardingStep.SELECT_LANGUAGE:
            self._render_language_step(container, i18n)
        elif self.current_step == OnboardingStep.TRUST_DIRECTORY:
            self._render_directory_step(container, i18n)
        elif self.current_step == OnboardingStep.COMPLETE:
            self._render_complete_step(container, i18n)
    
    def _render_welcome_step(self, container: Container, i18n) -> None:
        """渲染欢迎步骤."""
        container.mount(Static(
            f"[bold {AVOCADO_BRIGHT}]╔══════════════════════════════════════════╗[/]",
        ))
        container.mount(Static(
            f"[bold {AVOCADO_BRIGHT}]║[/]  [bold {AVOCADO_BRIGHT}]👋 {i18n.t('onboarding.welcome.title')}[/]                [bold {AVOCADO_BRIGHT}]║[/]"
        ))
        container.mount(Static(
            f"[bold {AVOCADO_BRIGHT}]╠══════════════════════════════════════════╣[/]"
        ))
        container.mount(Static(
            f"[bold {AVOCADO_BRIGHT}]║[/]  [dim]{i18n.t('onboarding.welcome.description')}[/]    [bold {AVOCADO_BRIGHT}]║[/]"
        ))
        container.mount(Static(
            f"[bold {AVOCADO_BRIGHT}]╚══════════════════════════════════════════╝[/]"
        ))
        
        # 步骤说明
        container.mount(Static(
            i18n.t('onboarding.welcome.steps_preview'),
            id="step-description"
        ))
        
        # 操作按钮
        with Horizontal(id="step-actions"):
            container.mount(Horizontal(
                Button(
                    i18n.t('onboarding.button.start'),
                    id="btn-start",
                    variant="primary",
                    classes="button-primary"
                ),
                Button(
                    i18n.t('onboarding.button.skip'),
                    id="btn-skip",
                    classes="button-secondary"
                ),
                id="action-buttons"
            ))
    
    def _render_provider_step(self, container: Container, i18n) -> None:
        """渲染选择提供商步骤."""
        container.mount(Static(
            f"[bold {AVOCADO_BRIGHT}]╔══════════════════════════════════════════╗[/]",
            id="step-header"
        ))
        container.mount(Static(
            f"[bold {AVOCADO_BRIGHT}]║[/]  [bold]{i18n.t('onboarding.provider.title')}[/]                     [bold {AVOCADO_BRIGHT}]║[/]",
            id="step-title"
        ))
        container.mount(Static(
            f"[bold {AVOCADO_BRIGHT}]╠══════════════════════════════════════════╣[/]"
        ))
        container.mount(Static(
            f"[bold {AVOCADO_BRIGHT}]║[/]  [dim]{i18n.t('onboarding.provider.description')}[/]                [bold {AVOCADO_BRIGHT}]║[/]"
        ))
        container.mount(Static(
            f"[bold {AVOCADO_BRIGHT}]╚══════════════════════════════════════════╝[/]"
        ))
        
        # 提供商列表
        with VerticalScroll(id="step-content", classes="provider-list"):
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
                    classes="provider-item"
                )
                item._provider_id = provider_id
                yield item
        
        # 操作按钮
        with Horizontal(id="step-actions"):
            container.mount(Horizontal(
                Button(
                    i18n.t('onboarding.button.next'),
                    id="btn-next",
                    variant="primary",
                    classes="button-primary"
                ),
                Button(
                    i18n.t('onboarding.button.back'),
                    id="btn-back",
                    classes="button-back"
                ),
                Button(
                    i18n.t('onboarding.button.skip'),
                    id="btn-skip-step",
                    classes="button-secondary"
                ),
                id="action-buttons"
            ))
    
    def _render_api_key_step(self, container: Container, i18n) -> None:
        """渲染输入 API Key 步骤."""
        container.mount(Static(
            f"[bold {AVOCADO_BRIGHT}]╔══════════════════════════════════════════╗[/]",
            id="step-header"
        ))
        container.mount(Static(
            f"[bold {AVOCADO_BRIGHT}]║[/]  [bold]{i18n.t('onboarding.api_key.title')}[/]                  [bold {AVOCADO_BRIGHT}]║[/]"
        ))
        container.mount(Static(
            f"[bold {AVOCADO_BRIGHT}]╠══════════════════════════════════════════╣[/]"
        ))
        
        if self.selected_provider:
            provider_info = PROVIDERS.get(self.selected_provider, {})
            provider_name = provider_info.get("display_name", self.selected_provider)
            container.mount(Static(
                f"[bold {AVOCADO_BRIGHT}]║[/]  [dim]{i18n.t('onboarding.api_key.selected_provider')}: {provider_name}[/]          [bold {AVOCADO_BRIGHT}]║[/]"
            ))
            
            # API Key 获取链接
            website = provider_info.get("website", "")
            if website:
                container.mount(Static(
                    f"[bold {AVOCADO_BRIGHT}]║[/]  [dim]{i18n.t('onboarding.api_key.get_key')}: {website}[/]          [bold {AVOCADO_BRIGHT}]║[/]"
                ))
        
        container.mount(Static(
            f"[bold {AVOCADO_BRIGHT}]╚══════════════════════════════════════════╝[/]"
        ))
        
        # API Key 输入框
        with VerticalScroll(id="step-content"):
            container.mount(Static(
                i18n.t('onboarding.api_key.input_prompt'),
                id="api-key-label"
            ))
            container.mount(Input(
                placeholder=i18n.t('onboarding.api_key.placeholder'),
                id="api-key-input",
                password=True
            ))
        
        # 操作按钮
        with Horizontal(id="step-actions"):
            container.mount(Horizontal(
                Button(
                    i18n.t('onboarding.button.next'),
                    id="btn-next",
                    variant="primary",
                    classes="button-primary"
                ),
                Button(
                    i18n.t('onboarding.button.back'),
                    id="btn-back",
                    classes="button-back"
                ),
                Button(
                    i18n.t('onboarding.button.skip'),
                    id="btn-skip-step",
                    classes="button-secondary"
                ),
                id="action-buttons"
            ))
    
    def _render_language_step(self, container: Container, i18n) -> None:
        """渲染选择语言步骤."""
        container.mount(Static(
            f"[bold {AVOCADO_BRIGHT}]╔══════════════════════════════════════════╗[/]",
            id="step-header"
        ))
        container.mount(Static(
            f"[bold {AVOCADO_BRIGHT}]║[/]  [bold]{i18n.t('onboarding.language.title')}[/]                        [bold {AVOCADO_BRIGHT}]║[/]"
        ))
        container.mount(Static(
            f"[bold {AVOCADO_BRIGHT}]╠══════════════════════════════════════════╣[/]"
        ))
        container.mount(Static(
            f"[bold {AVOCADO_BRIGHT}]║[/]  [dim]{i18n.t('onboarding.language.description')}[/]   [bold {AVOCADO_BRIGHT}]║[/]"
        ))
        container.mount(Static(
            f"[bold {AVOCADO_BRIGHT}]╚══════════════════════════════════════════╝[/]"
        ))
        
        # 语言选项
        with VerticalScroll(id="step-content", classes="language-options"):
            for lang_code, lang_name in self.LANGUAGES:
                is_selected = lang_code == self.selected_language
                item = Static(
                    f"[bold]{'●' if is_selected else '○'}[/] {lang_name}",
                    classes=f"language-item{' selected' if is_selected else ''}"
                )
                item._lang_code = lang_code
                yield item
        
        # 操作按钮
        with Horizontal(id="step-actions"):
            container.mount(Horizontal(
                Button(
                    i18n.t('onboarding.button.next'),
                    id="btn-next",
                    variant="primary",
                    classes="button-primary"
                ),
                Button(
                    i18n.t('onboarding.button.back'),
                    id="btn-back",
                    classes="button-back"
                ),
                id="action-buttons"
            ))
    
    def _render_directory_step(self, container: Container, i18n) -> None:
        """渲染信任目录步骤."""
        container.mount(Static(
            f"[bold {AVOCADO_BRIGHT}]╔══════════════════════════════════════════╗[/]",
            id="step-header"
        ))
        container.mount(Static(
            f"[bold {AVOCADO_BRIGHT}]║[/]  [bold]{i18n.t('onboarding.directory.title')}[/]            [bold {AVOCADO_BRIGHT}]║[/]"
        ))
        container.mount(Static(
            f"[bold {AVOCADO_BRIGHT}]╠══════════════════════════════════════════╣[/]"
        ))
        container.mount(Static(
            f"[bold {AVOCADO_BRIGHT}]║[/]  [dim]{i18n.t('onboarding.directory.description')}[/] [bold {AVOCADO_BRIGHT}]║[/]"
        ))
        container.mount(Static(
            f"[bold {AVOCADO_BRIGHT}]╚══════════════════════════════════════════╝[/]"
        ))
        
        # 目录信息
        with VerticalScroll(id="step-content", classes="directory-info"):
            container.mount(Static(
                f"[dim]{i18n.t('onboarding.directory.current')}:[/]",
            ))
            container.mount(Static(
                f"[bold {AVOCADO_BRIGHT}]{self.trusted_directory}[/]",
                classes="directory-path"
            ))
            container.mount(Static(""))
            container.mount(Static(
                f"[dim]{i18n.t('onboarding.directory.info')}[/]"
            ))
        
        # 操作按钮
        with Horizontal(id="step-actions"):
            container.mount(Horizontal(
                Button(
                    i18n.t('onboarding.button.finish'),
                    id="btn-finish",
                    variant="primary",
                    classes="button-primary"
                ),
                Button(
                    i18n.t('onboarding.button.back'),
                    id="btn-back",
                    classes="button-back"
                ),
                id="action-buttons"
            ))
    
    def _render_complete_step(self, container: Container, i18n) -> None:
        """渲染完成步骤."""
        container.mount(Static(
            f"[bold {AVOCADO_BRIGHT}]╔══════════════════════════════════════════╗[/]",
        ))
        container.mount(Static(
            f"[bold {AVOCADO_BRIGHT}]║[/]  [bold {AVOCADO_BRIGHT}]✅ {i18n.t('onboarding.complete.title')}[/]                        [bold {AVOCADO_BRIGHT}]║[/]"
        ))
        container.mount(Static(
            f"[bold {AVOCADO_BRIGHT}]╠══════════════════════════════════════════╣[/]"
        ))
        container.mount(Static(
            f"[bold {AVOCADO_BRIGHT}]║[/]  [dim]{i18n.t('onboarding.complete.message')}[/]          [bold {AVOCADO_BRIGHT}]║[/]"
        ))
        container.mount(Static(
            f"[bold {AVOCADO_BRIGHT}]╚══════════════════════════════════════════╝[/]"
        ))
        
        # 完成图标
        container.mount(Static(
            f"[bold {AVOCADO_BRIGHT}]🎉[/]",
            id="completion-icon"
        ))
        
        # 摘要信息
        summary_items = []
        if self.selected_provider:
            summary_items.append(f"• {i18n.t('onboarding.complete.provider')}: {self.selected_provider}")
        summary_items.append(f"• {i18n.t('onboarding.complete.language')}: {self.selected_language}")
        summary_items.append(f"• {i18n.t('onboarding.complete.directory')}: {self.trusted_directory}")
        
        summary_text = "\n".join(summary_items)
        container.mount(Static(
            f"[dim]{summary_text}[/]",
            id="completion-message"
        ))
        
        # 操作按钮
        with Horizontal(id="step-actions"):
            container.mount(Horizontal(
                Button(
                    i18n.t('onboarding.button.start_using'),
                    id="btn-start-using",
                    variant="primary",
                    classes="button-primary"
                ),
                Button(
                    i18n.t('onboarding.button.configure_more'),
                    id="btn-configure",
                    classes="button-secondary"
                ),
                id="action-buttons"
            ))
    
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
            # 确保目录存在
            ensure_workspace_dirs()
            
            config_file = AGENT_Z_HOME / "config.json"
            
            # 读取现有配置
            existing_config = {}
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    existing_config = json.load(f)
            
            # 合并配置
            existing_config.update(config)
            
            # 写入配置
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(existing_config, f, indent=2, ensure_ascii=False)
            
            self._logger.info("Configuration saved successfully")
            
            # 重置语言缓存
            reset_language_cache()
            
            return config
        except Exception as e:
            self._logger.error(f"Failed to save configuration: {e}")
            return config
    
    def _next_step(self) -> None:
        """移动到下一步."""
        current_idx = self._get_step_index(self.current_step)
        if current_idx < len(self._all_steps) - 1:
            self.current_step = self._all_steps[current_idx + 1]
            self._render_current_step()
            self._logger.info(f"Step changed to: {self.current_step.value}")
    
    def _prev_step(self) -> None:
        """移动到上一步."""
        current_idx = self._get_step_index(self.current_step)
        if current_idx > 0:
            self.current_step = self._all_steps[current_idx - 1]
            self._render_current_step()
            self._logger.info(f"Step changed to: {self.current_step.value}")
    
    def _select_provider(self, provider_id: str) -> None:
        """选择提供商."""
        self.selected_provider = provider_id
        self._logger.info(f"Provider selected: {provider_id}")
    
    def _select_language(self, lang_code: str) -> None:
        """选择语言."""
        self.selected_language = lang_code
        self._logger.info(f"Language selected: {lang_code}")
    
    def on_click(self, event) -> None:
        """处理点击事件 (用于选择项)."""
        # 处理提供商选择
        for widget in self.query(".provider-item"):
            if widget.is_parent_of(event.target) or widget == event.target:
                if hasattr(widget, "_provider_id"):
                    # 取消所有选中状态
                    for w in self.query(".provider-item"):
                        w.remove_class("selected")
                    # 设置新选中状态
                    widget.add_class("selected")
                    self._select_provider(widget._provider_id)
                    return
        
        # 处理语言选择
        for widget in self.query(".language-item"):
            if widget.is_parent_of(event.target) or widget == event.target:
                if hasattr(widget, "_lang_code"):
                    # 取消所有选中状态
                    for w in self.query(".language-item"):
                        w.remove_class("selected")
                    # 设置新选中状态
                    widget.add_class("selected")
                    self._select_language(widget._lang_code)
                    return
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮按下事件."""
        button_id = event.button.id
        
        if button_id == "btn-start":
            self._next_step()
        elif button_id == "btn-skip" or button_id == "btn-skip-step":
            self._logger.info("Onboarding skipped by user")
            self.post_message(OnboardingSkipped(self))
        elif button_id == "btn-next":
            # 获取 API Key 输入
            if self.current_step == OnboardingStep.INPUT_API_KEY:
                api_key_input = self.query_one("#api-key-input", Input)
                self.selected_api_key = api_key_input.value
            self._next_step()
        elif button_id == "btn-back":
            self._prev_step()
        elif button_id == "btn-finish":
            # 保存配置
            self._save_config()
            self.current_step = OnboardingStep.COMPLETE
            self._render_current_step()
        elif button_id == "btn-start-using":
            self._logger.info("Onboarding completed, starting main app")
            self.post_message(OnboardingComplete(self))
        elif button_id == "btn-configure":
            self._logger.info("Onboarding completed, opening settings")
            config = self._save_config()
            self.post_message(ConfigurationSaved(self, config))


# ============================================================================
# 模块导出
# ============================================================================

__all__ = [
    "OnboardingStep",
    "OnboardingScreen",
    "OnboardingMessage",
    "OnboardingComplete",
    "OnboardingSkipped",
    "ConfigurationSaved",
    "ONBOARDING_CSS",
]