#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Settings Screen - TUI 设置界面模态窗口

🚪 Access - 💬 CLI - TUI Views - SettingsScreen

使用 Textual 原生组件构建美观的设置界面:
- Tree: 侧边栏分类导航
- Switch: 开关设置
- Select: 下拉选择
- Input: 文本输入
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

# Textual 框架导入
TEXTUAL_AVAILABLE = True
try:
    from textual.app import ComposeResult
    from textual.screen import ModalScreen
    from textual.widgets import Static, Button, Tree, Switch, Select, Input
    from textual.containers import Container, Horizontal, Vertical, VerticalScroll, Grid
    from textual.binding import Binding
    from textual.message import Message
    from textual.events import Click
    from textual import on
except ImportError:
    TEXTUAL_AVAILABLE = False
    ModalScreen = object
    Static = object
    Button = object
    Tree = object
    Switch = object
    Select = object
    Input = object
    Container = object
    Horizontal = object
    Vertical = object
    VerticalScroll = object
    Grid = object
    Binding = lambda *a, **k: None  # 降级：空的 Binding
    Message = object
    Click = object

# i18n 支持
try:
    from common.i18n import get_i18n
except ImportError:

    def get_i18n():
        class SimpleI18n:
            def t(self, key, default=None, **kwargs):
                return default or key

        return SimpleI18n()


# 日志支持
from common.logging_manager import get_access_logger


# 设置模块导入
try:
    from tui.views.settings.manager import SettingsManager, get_settings_manager
    from tui.views.settings.models import SettingsDocument, CategoryMeta
except ImportError:
    SettingsManager = None
    SettingsDocument = None
    CategoryMeta = None


# ============================================================================
# CSS 样式 - 使用 Textual 主题变量和 grid 布局
# ============================================================================

SETTINGS_SCREEN_CSS = """
SettingsScreen {
    align: center middle;
    background: $primary 30%;
}

#settings-container {
    width: 90%;
    height: 80%;
    background: $surface;
}

#settings-header {
    width: 100%;
    height: 3;
    background: $accent;
    content-align: center middle;
    color: $text;
    text-style: bold;
}

#settings-body {
    height: 1fr;
}

#sidebar {
    width: 28%;
    border-right: solid $border;
    background: $panel;
}

#content-area {
    width: 72%;
    background: $surface;
}

#settings-footer {
    height: 1;
    layout: horizontal;
    content-align: center middle;
}

.settings-footer-item {
    width: auto;
    color: $text-muted;
    padding: 0 1;
}

.settings-footer-item:hover {
    color: $accent;
    background: $surface;
}

.settings-footer-separator {
    width: auto;
    color: $text-disabled;
}

#content-scroll {
    padding: 1 2;
    height: 100%;
}

/* 分类项样式 */
.category-header {
    color: $accent;
    text-style: bold;
    padding: 1 2;
    background: $accent 10%;
}

/* 设置项样式 */
.setting-row {
    height: auto;
    padding: 1 2;
    border-bottom: solid $border 30%;
}

.setting-label {
    width: 40%;
    color: $text;
}

.setting-control {
    width: 60%;
}

.setting-description {
    color: $text-muted;
    padding: 0 2;
    display: none;
}

/* Switch 样式 */
Switch {
    margin: 0 1;
}

/* Select 样式 */
Select {
    width: 100%;
    max-width: 200;
}

/* Input 样式 */
Input {
    width: 100%;
    max-width: 300;
}

/* 关于区域 */
.about-section {
    padding: 2;
    height: auto;
}

.about-title {
    text-style: bold;
    color: $accent;
    padding-bottom: 1;
}

.about-content {
    color: $text-muted;
}

/* 分组标题 */
.setting-group-title {
    color: $accent;
    text-style: bold;
    padding: 1 2;
    background: $accent 5%;
    border-bottom: solid $border;
}

/* 侧边栏分类项样式（使用 Static 避免焦点底色） */
.sidebar-item {
    width: 100%;
    height: 3;
    padding: 0 2;
    margin: 0;
    background: $panel;
    content-align: left middle;
    color: $text-muted;
}

.sidebar-item:hover {
    background: $accent 20%;
    color: $text;
}

.sidebar-item.selected {
    background: $primary 40%;
    color: $text;
}

/* Provider 配置列表 */
.llm-providers-list {
    height: 8;
    width: 100%;
    border: solid $border;
    padding: 0 1;
}

.provider-config-item {
    height: 2;
    width: 100%;
    padding: 0 1;
    color: $text-muted;
}

.provider-config-item.active {
    color: $text;
    text-style: bold;
}

.provider-config-item:hover {
    background: $accent 20%;
}

#llm-provider-details {
    height: auto;
    width: 100%;
    border: solid $border;
    padding: 1 2;
}

/* Fallback 列表 */
.fallback-list {
    height: 10;
    width: 100%;
    border: solid $border;
    padding: 0 1;
}

.fallback-item {
    height: 2;
    width: 100%;
    padding: 0 1;
    color: $text-muted;
}

.fallback-item:hover {
    background: $accent 20%;
}
"""


# ============================================================================
# 消息类型
# ============================================================================


class SettingsClosed(Message):
    """设置界面关闭消息"""

    pass


class SettingsSaved(Message):
    """设置已保存消息"""

    def __init__(self, sender) -> None:
        super().__init__()


# ============================================================================
# SettingsScreen 主类
# ============================================================================


class SettingsScreen(ModalScreen if TEXTUAL_AVAILABLE else object):
    """TUI 设置界面模态窗口 - 使用 Textual 原生组件"""

    CSS = SETTINGS_SCREEN_CSS

    BINDINGS = [
        Binding("escape", "close", "关闭", show=False),
        Binding("tab", "next_category", "下一分类", show=False),
        Binding("shift+tab", "prev_category", "上一分类", show=False),
        Binding("ctrl+s", "save", "保存", show=False),
        Binding("ctrl+r", "reset_category", "重置", show=False),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._settings_manager = get_settings_manager() if SettingsManager else None
        self._current_category: str = "language"
        self._setting_controls: dict[str, tuple] = {}  # 保存设置控件引用
        self._logger = get_access_logger("SettingsScreen", sublayer="tui")
        self._content_built: bool = False  # guard: only build content once on mount
        self._i18n = get_i18n()

    def _t(self, key: str, **kwargs) -> str:
        """Shortcut for i18n translation."""
        return self._i18n.t(f"tui.settings.{key}", **kwargs)

    def compose(self) -> ComposeResult:
        """组合组件"""
        with Container(id="settings-container"):
            yield Static(self._t("header"), id="settings-header")

            # 主体：左侧分类按钮列表 + 右侧内容
            with Horizontal(id="settings-body"):
                # 侧边栏分类导航
                with VerticalScroll(id="sidebar"):
                    yield from self._compose_sidebar_buttons()

                # 内容区
                with VerticalScroll(id="content-area"):
                    yield from self._compose_content()

            with Horizontal(id="settings-footer"):
                yield Static("Tab 切换", classes="settings-footer-item")
                yield Static("|", classes="settings-footer-separator")
                yield Static("↑↓ 移动", classes="settings-footer-item")
                yield Static("|", classes="settings-footer-separator")
                yield Static("确认", classes="settings-footer-item")
                yield Static("|", classes="settings-footer-separator")
                yield Static("Ctrl+S 保存", id="settings-footer-save", classes="settings-footer-item")
                yield Static("|", classes="settings-footer-separator")
                yield Static("Ctrl+R 重置", id="settings-footer-reset", classes="settings-footer-item")
                yield Static("|", classes="settings-footer-separator")
                yield Static("Esc 关闭", id="settings-footer-close", classes="settings-footer-item")

    def _compose_sidebar_buttons(self) -> ComposeResult:
        """生成侧边栏分类按钮列表（使用 Static 避免焦点底色）"""
        if CategoryMeta:
            for cat_id, icon, name_key, _ in CategoryMeta.CATEGORIES:
                label = f"{icon}  {self._t(name_key)}"
                item = Static(
                    label,
                    id=f"sidebar-item-{cat_id}",
                    classes=(
                        "sidebar-item selected"
                        if cat_id == self._current_category
                        else "sidebar-item"
                    ),
                )
                item._category_id = cat_id
                yield item

    def _compose_content(self) -> ComposeResult:
        """生成设置内容区"""
        yield from self._build_category_content(self._current_category)
        self._content_built = True

    def _build_category_content(self, category: str) -> ComposeResult:
        """根据分类构建内容"""
        settings = (
            self._settings_manager.get_settings()
            if self._settings_manager
            else SettingsDocument()
        )

        # 根据分类生成不同的设置项
        if category == "llm":
            # 合并 llm + providers + fallback + model
            yield from self._build_llm_content(settings)
            yield from self._build_model_content(settings)
            yield from self._build_fallback_content(settings)
        elif category == "terminal":
            yield from self._build_terminal_content(settings)
        elif category == "behavior":
            # 合并 agent + preferences
            yield from self._build_agent_content(settings)
            yield from self._build_preferences_content(settings)
        elif category == "session":
            # 合并 session + memory + compression + session_reset
            yield from self._build_session_content(settings)
        elif category == "tools":
            yield from self._build_tools_content(settings)
        elif category == "logging":
            yield from self._build_logging_content(settings)
        elif category == "about":
            yield from self._build_about_content(settings)
        else:
            yield Static(self._t("no_items"))

    def _build_llm_content(self, settings: SettingsDocument) -> ComposeResult:
        """构建 LLM 设置内容 - 已配置 Provider 列表置顶，选中后下方编辑"""
        yield Static(self._t("llm"), classes="setting-group-title")

        active_provider = (
            settings.llm.provider if hasattr(settings.llm, "provider") else ""
        )

        providers_items = (
            settings.providers.items if hasattr(settings, "providers") else {}
        )

        try:
            from common.llm_providers import PROVIDERS as CATALOG
        except ImportError:
            CATALOG = {}

        available = []
        for pid in CATALOG:
            available.append((CATALOG[pid]["name"], pid))
        for pid in providers_items:
            if pid not in CATALOG:
                available.append((pid.title(), pid))
        available.sort(key=lambda x: x[0])

        # ── 已配置 Provider 列表（可点击选中）────────────────────
        yield Static(self._t("configured_providers"), classes="setting-row")
        if providers_items:
            yield VerticalScroll(
                *(
                    self._iter_provider_items(
                        providers_items, CATALOG, active_provider
                    )
                ),
                id="llm-providers-list",
                classes="llm-providers-list",
            )
        else:
            yield Static(
                self._t("no_provider"),
                classes="provider-config-item",
            )

        # 预填当前选中 provider 的已有配置
        cur_pconf = (
            providers_items.get(active_provider)
            if active_provider in providers_items
            else None
        )
        cur_key = getattr(cur_pconf, "api_key", "") or ""
        cur_model = getattr(cur_pconf, "model", "") or ""
        cur_url = getattr(cur_pconf, "base_url", "") or ""
        cur_pid = active_provider if active_provider in dict(available) else None

        # ── 编辑 / 添加表单（始终可见）────────────────────────
        yield Static(self._t("edit_add_provider"), classes="setting-group-title")

        yield Static(self._t("provider"), classes="setting-row")
        select_kwargs = {"id": "llm-provider-select", "allow_blank": True, "classes": "setting-row"}
        if cur_pid:
            select_kwargs["value"] = cur_pid
        yield Select(options=[(name, pid) for name, pid in available], **select_kwargs)

        yield Static(self._t("api_key"), classes="setting-row")
        yield Input(
            value=cur_key,
            placeholder=self._t("provider_apikey_placeholder"),
            id="llm-apikey-input",
            password=True,
            classes="setting-row",
        )

        yield Static(self._t("model_name"), classes="setting-row")
        yield Input(
            value=cur_model,
            placeholder=self._t("provider_model_placeholder"),
            id="llm-model-input",
            classes="setting-row",
        )

        yield Static(self._t("base_url"), classes="setting-row")
        yield Input(
            value=cur_url,
            placeholder=self._t("provider_baseurl_placeholder"),
            id="llm-baseurl-input",
            classes="setting-row",
        )

    def _iter_provider_items(self, providers_items, CATALOG, active_provider):
        """生成 provider 列表项（供 VerticalScroll compose 使用）。"""
        has_any = False
        for pid, pconf in providers_items.items():
            has_any = True
            cat_info = CATALOG.get(pid, {})
            display_name = cat_info.get("display_name", pid.title())
            model = pconf.model if hasattr(pconf, "model") and pconf.model else ""
            has_key = bool(pconf.api_key if hasattr(pconf, "api_key") else False)
            status = "✓" if has_key else "○"
            is_active = "●" if pid == active_provider else "○"
            label = f"{is_active} {status} {display_name}"
            if model:
                label += f"  [dim]{model}[/]"
            item = Static(
                label,
                classes=f"provider-config-item{' active' if pid == active_provider else ''}",
            )
            item._provider_id = pid
            yield item

        if not has_any:
            yield Static(
                self._t("no_provider"),
                classes="provider-config-item",
            )

    async def _on_provider_item_click(self, provider_id: str) -> None:
        """点击 provider 条目 → 挂载编辑表单到 details 区"""
        settings = self._settings_manager.get_settings()
        providers_items = (
            settings.providers.items if hasattr(settings, "providers") else {}
        )
        pconf = providers_items.get(provider_id, {})
        api_key = getattr(pconf, "api_key", "") or ""
        model = getattr(pconf, "model", "") or ""
        base_url = getattr(pconf, "base_url", "") or ""

        details_container = self.query_one("#llm-provider-details", Container)
        await details_container.remove_children()

        from tui.views.settings.models import ProviderItemConfig

        self._editing_provider_id = provider_id

        await details_container.mount(
            Static(self._t("provider_edit_title", provider=provider_id), id="provider-edit-title"),
            Static(self._t("api_key"), classes="setting-row"),
            Input(
                api_key,
                id="provider-apikey-input",
                placeholder=self._t("provider_apikey_placeholder"),
                password=True,
                classes="setting-row",
            ),
            Static(self._t("model_name"), classes="setting-row"),
            Input(
                model,
                id="provider-model-input",
                placeholder=self._t("provider_model_placeholder"),
                classes="setting-row",
            ),
            Static(f"{self._t('base_url')}（可选）", classes="setting-row"),
            Input(
                base_url,
                id="provider-baseurl-input",
                placeholder=self._t("provider_baseurl_placeholder"),
                classes="setting-row",
            ),
        )

        try:
            add_sel = self.query_one("#llm-add-provider-select", Select)
            add_sel.value = None
        except Exception:
            pass

    def _build_model_content(self, settings: SettingsDocument) -> ComposeResult:
        """构建模型参数设置内容"""
        yield Static(self._t("model"), classes="setting-group-title")

        model = settings.model_settings

        yield Static(self._t("temperature"), classes="setting-row")
        yield Input(
            str(model.temperature),
            id="model-temperature-input",
            placeholder=f"{self._t('temperature')}: {model.temperature} (0.0-1.0)",
            classes="setting-row",
        )

        yield Static(self._t("max_tokens"), classes="setting-row")
        yield Input(
            str(model.max_tokens),
            id="model-maxtokens-input",
            placeholder=f"{self._t('max_tokens')}: {model.max_tokens}",
            classes="setting-row",
        )

        yield Static(self._t("context_window"), classes="setting-row")
        yield Input(
            str(model.context_window),
            id="model-contextwindow-input",
            placeholder=f"{self._t('context_window')}: {model.context_window}",
            classes="setting-row",
        )

        # 辅助任务专用模型
        yield Static(self._t("auxiliary_models"), classes="setting-row")
        yield Static(self._t("auxiliary_hint"), classes="setting-row")

        aux_fields = [
            ("compression_model", "compression_model", model.compression_model),
            ("title_model", "title_model", model.title_model),
            ("synthesis_model", "synthesis_model", model.synthesis_model),
            ("memory_model", "memory_model", model.memory_model),
            ("auxiliary_model", "auxiliary_model", model.auxiliary_model),
        ]
        for fid, label_key, current in aux_fields:
            yield Static(self._t(label_key), classes="setting-row")
            yield Input(
                current or "",
                id=f"model-{fid}-input",
                placeholder=f"{self._t(label_key)}: {current or self._t('depth_normal')}",
                classes="setting-row",
            )

    def _build_fallback_content(self, settings: SettingsDocument) -> ComposeResult:
        """构建 Fallback 配置内容"""
        yield Static(self._t("fallback"), classes="setting-group-title")
        yield Static(
            self._t("fallback_hint"),
            classes="setting-row",
        )

        # 已有 fallback 条目
        fb_items = (
            settings.fallback_providers.items
            if hasattr(settings, "fallback_providers")
            else []
        )
        fb_widgets = []
        if fb_items:
            for i, fb in enumerate(fb_items):
                provider = getattr(fb, "provider", "") or ""
                model = getattr(fb, "model", "") or ""
                base_url = getattr(fb, "base_url", "") or ""
                label = f"○ {provider}"
                if model:
                    label += f"  [dim]{model}[/]"
                if base_url:
                    label += f"  [dim]({base_url})[/]"
                item = Static(label, classes="fallback-item")
                item._fb_index = i
                fb_widgets.append(item)
        else:
            fb_widgets.append(
                Static(
                    self._t("no_fallback"),
                    classes="fallback-item",
                )
            )
        yield VerticalScroll(*fb_widgets, id="fallback-list", classes="fallback-list")

        # 添加 Fallback 选择
        yield Static(self._t("add_fallback"), classes="setting-row")
        try:
            from common.llm_providers import PROVIDERS as CATALOG
        except ImportError:
            CATALOG = {}
        fb_options = [
            (CATALOG[p]["name"], p) for p in CATALOG if p != settings.llm.provider
        ]
        fb_options.append(("+ 添加...", "__add__"))
        yield Select(
            options=fb_options,
            id="fallback-add-select",
            allow_blank=True,
            classes="setting-row",
        )

    def _build_terminal_content(self, settings: SettingsDocument) -> ComposeResult:
        """构建终端设置内容"""
        yield Static(self._t("terminal"), classes="setting-group-title")

        backend_options = [
            (self._t("backend_local"), "local"),
            (self._t("backend_docker"), "docker"),
        ]
        current_backend = (
            "local"
            if hasattr(settings.terminal, "backend")
            and settings.terminal.backend == "local"
            else "docker"
        )
        yield Select(
            options=backend_options,
            value=current_backend,
            id="terminal-backend-select",
            allow_blank=False,
            classes="setting-row",
        )

    def _build_agent_content(self, settings: SettingsDocument) -> ComposeResult:
        """构建 Agent 设置内容"""
        yield Static(self._t("agent"), classes="setting-group-title")

        agent = settings.agent

        yield Static(self._t("max_iterations"), classes="setting-row")
        yield Input(
            str(agent.max_turns),
            id="agent-maxiterations-input",
            placeholder=f"{self._t('max_iterations')}: {agent.max_turns}",
            classes="setting-row",
        )

        yield Static(self._t("timeout"), classes="setting-row")
        yield Input(
            str(agent.gateway_timeout),
            id="agent-timeout-input",
            placeholder=f"{self._t('timeout')}: {agent.gateway_timeout}s",
            classes="setting-row",
        )

    def _build_session_content(self, settings: SettingsDocument) -> ComposeResult:
        """构建会话设置内容"""
        yield Static(self._t("session"), classes="setting-group-title")

        session = settings.session
        memory = settings.memory
        compression = settings.compression
        session_reset = settings.session_reset

        # 会话开关
        yield Static(self._t("enable_session"), classes="setting-row")
        yield Switch(
            session.enabled, id="session-enabled-switch", classes="setting-row"
        )

        # 记忆系统开关
        yield Static(self._t("enable_memory"), classes="setting-row")
        yield Switch(memory.enabled, id="memory-enabled-switch", classes="setting-row")

        # 语义检索开关
        yield Static(self._t("enable_semantic"), classes="setting-row")
        yield Switch(
            memory.semantic_retrieval_enabled,
            id="semantic-switch",
            classes="setting-row",
        )

        # Context 压缩开关
        yield Static(self._t("enable_compression"), classes="setting-row")
        yield Switch(
            compression.enabled, id="compression-switch", classes="setting-row"
        )

        # 会话重置模式
        reset_options = [
            (self._t("reset_both"), "both"),
            (self._t("reset_daily"), "daily"),
            (self._t("reset_idle"), "idle"),
            (self._t("reset_never"), "never"),
        ]
        yield Static(self._t("reset_mode"), classes="setting-row")
        yield Select(
            options=reset_options,
            value=session_reset.mode.value,
            id="reset-mode-select",
            allow_blank=False,
            classes="setting-row",
        )

    def _build_preferences_content(self, settings: SettingsDocument) -> ComposeResult:
        """构建响应偏好设置内容"""
        yield Static(self._t("preferences"), classes="setting-group-title")

        # 显示语言
        language_options = [
            (self._t("lang_zh"), "zh"),
            (self._t("lang_en"), "en"),
        ]
        current = (
            settings.display.language.value
            if hasattr(settings.display, "language")
            else "zh"
        )
        yield Static(self._t("language"), classes="setting-row")
        yield Select(
            options=language_options,
            value=current,
            id="language-select",
            allow_blank=False,
            classes="setting-row",
        )

        prefs = settings.preferences

        # 详细程度
        depth_options = [
            (self._t("depth_brief"), "brief"),
            (self._t("depth_moderate"), "moderate"),
            (self._t("depth_detailed"), "detailed"),
        ]
        current_depth = (
            prefs.explanation_depth.value
            if hasattr(prefs, "explanation_depth")
            else "normal"
        )
        yield Static(self._t("explanation_depth"), classes="setting-row")
        yield Select(
            options=depth_options,
            value=current_depth,
            id="depth-select",
            allow_blank=False,
            classes="setting-row",
        )

        # 响应格式
        format_options = [
            (self._t("format_auto"), "auto"),
            (self._t("format_markdown"), "markdown"),
            (self._t("format_plain"), "plain"),
        ]
        current_format = (
            prefs.response_format.value
            if hasattr(prefs, "response_format")
            else "markdown"
        )
        yield Static(self._t("response_format"), classes="setting-row")
        yield Select(
            options=format_options,
            value=current_format,
            id="format-select",
            allow_blank=False,
            classes="setting-row",
        )

    def _build_tools_content(self, settings: SettingsDocument) -> ComposeResult:
        """构建工具设置内容"""
        yield Static(self._t("tools"), classes="setting-group-title")

        tools = settings.tools

        yield Static(self._t("stt"), classes="setting-row")
        yield Switch(tools.stt_enabled, id="stt-switch", classes="setting-row")

        yield Static(self._t("tts"), classes="setting-row")
        yield Switch(tools.tts_enabled, id="tts-switch", classes="setting-row")

        yield Static(self._t("browser"), classes="setting-row")
        yield Switch(tools.browser_enabled, id="browser-switch", classes="setting-row")

    def _build_logging_content(self, settings: SettingsDocument) -> ComposeResult:
        """构建日志设置内容"""
        yield Static(self._t("logging"), classes="setting-group-title")

        yield Static(self._t("enable_file_log"), classes="setting-row")
        yield Switch(
            settings.logging.file_enabled, id="file-log-switch", classes="setting-row"
        )

    def _build_about_content(self, settings: SettingsDocument) -> ComposeResult:
        """构建关于内容"""
        about = settings.about
        yield Static(self._t("about"), classes="about-title")
        yield Static(self._t("version", version=about.version), classes="about-content")
        yield Static(self._t("license", license=about.license), classes="about-content")
        yield Static(self._t("about_desc"), classes="about-content")

    # ========================================================================
    # 事件处理
    # ========================================================================

    async def on_click(self, event: Click) -> None:
        """统一处理点击事件：背景关闭 + 侧边栏分类切换 + provider 配置项点击"""
        if event.widget is self:
            self.action_close()
            return

        target = getattr(event, "widget", None) or getattr(event, "target", None)
        if target is None:
            return

        if hasattr(target, "_category_id"):
            cat_id = target._category_id
            if cat_id != self._current_category:
                self.call_later(lambda: self._switch_category(cat_id))
            return

        if self._current_category != "llm":
            return
        for widget in self.query(".provider-config-item"):
            if widget == target and hasattr(widget, "_provider_id"):
                pid = widget._provider_id
                await self._on_provider_item_click(pid)
                self.call_later(lambda: self._switch_category("llm"))
                return

    def _update_sidebar_selection(self, cat_id: str) -> None:
        """更新侧边栏分类项选中状态"""
        for item in self.query(".sidebar-item"):
            if getattr(item, "_category_id", None) == cat_id:
                item.add_class("selected")
            else:
                item.remove_class("selected")

    def _switch_category(self, category: str) -> None:
        """切换到指定分类"""
        if category == self._current_category:
            return
        self._current_category = category
        self._update_sidebar_selection(category)

        # Guard: if content hasn't been built yet (during compose),
        # let compose() handle it to avoid generator exhaustion
        if not getattr(self, "_content_built", False):
            return

        content_area = self.query_one("#content-area", VerticalScroll)
        content_area.remove_children()
        new_widgets = list(self._build_category_content(category))
        for widget in new_widgets:
            content_area.mount(widget)

        self._logger.debug(f"Switched to category: {category}")

    def action_close(self) -> None:
        """关闭设置界面"""
        self._logger.debug("Settings screen closed")
        self.post_message(SettingsClosed())
        self.dismiss()

    @on(Click, "#settings-footer-close")
    def _handle_footer_close_click(self, event: Static.Click) -> None:
        """点击 footer 关闭按钮"""
        event.stop()
        self.action_close()

    @on(Click, "#settings-footer-save")
    def _handle_footer_save_click(self, event: Static.Click) -> None:
        """点击 footer 保存按钮"""
        event.stop()
        self.action_save()

    @on(Click, "#settings-footer-reset")
    def _handle_footer_reset_click(self, event: Static.Click) -> None:
        """点击 footer 重置按钮"""
        event.stop()
        self.action_reset_category()

    def action_save(self) -> None:
        """保存设置"""
        # 从控件收集设置值（验证数值范围）
        validation_errors, changed_settings = self._collect_settings()

        # 如果有验证错误，不保存并提示
        if validation_errors:
            error_msg = self._t("validation_error") + ("\n" + self._t("validation_error")).join(validation_errors[:3])
            if len(validation_errors) > 3:
                error_msg += "\n" + self._t("more_errors", n=len(validation_errors) - 3)
            self.notify(error_msg, timeout=4.0)
            return

        if self._settings_manager:
            if self._settings_manager.save():
                # 显示变更列表
                if changed_settings:
                    changes_msg = self._t("saved_changes") + ", ".join(changed_settings[:5])
                    if len(changed_settings) > 5:
                        changes_msg += "\n" + self._t("more_changes", n=len(changed_settings) - 5)
                    self.notify(changes_msg, timeout=3.0)
                else:
                    self.notify(self._t("save_no_change"), timeout=2.0)
            else:
                self._logger.error("Failed to save settings")
                self.notify(self._t("save_error"), timeout=2.0)
        self.post_message(SettingsSaved(self))
        self.dismiss()

    def _collect_settings(self) -> tuple[list, list]:
        """从控件收集设置值并保存到 manager，返回 (验证错误列表, 变更列表)"""
        validation_errors = []
        changed_settings = []

        if not self._settings_manager:
            return validation_errors, changed_settings

        settings = self._settings_manager.get_settings()

        # 语言设置（Select）：value 直接就是代码
        try:
            lang_select = self.query_one("#language-select", Select)
            old_lang = settings.display.language.value
            new_lang = lang_select.value
            if old_lang != new_lang:
                settings.display.language.value = new_lang
                old_label = self._t(f"lang_{old_lang}")
                new_label = self._t(f"lang_{new_lang}")
                changed_settings.append(self._t("category_changed", old=old_label, new=new_label))
        except Exception:
            pass

        # LLM Provider: handle quick-add from dropdown
        # LLM Provider 表单：provider 下拉 + api key / model / base url
        try:
            from tui.views.settings.models import ProviderItemConfig

            provider_sel = self.query_one("#llm-provider-select", Select)
            key_inp = self.query_one("#llm-apikey-input", Input)
            model_inp = self.query_one("#llm-model-input", Input)
            url_inp = self.query_one("#llm-baseurl-input", Input)

            pid = provider_sel.value
            new_key = key_inp.value.strip()
            new_model = model_inp.value.strip()
            new_url = url_inp.value.strip()

            if pid:
                if not hasattr(settings.providers, "items"):
                    settings.providers.items = {}
                if pid not in settings.providers.items:
                    settings.providers.items[pid] = ProviderItemConfig(enabled=True)
                    changed_settings.append(f"添加 Provider: {pid}")
                if settings.llm.provider != pid:
                    settings.llm.provider = pid
                    changed_settings.append(f"激活 Provider: {pid}")
                # 同步 llm.model：若 providers 里存了 model 则用它
                pconf = settings.providers.items.get(pid)
                stored_model = getattr(pconf, "model", "") or ""
                if stored_model and settings.llm.model != stored_model:
                    settings.llm.model = stored_model

            # 始终尝试保存凭证（无论是否从下拉选）
            if new_key or new_model or new_url:
                target_pid = pid if pid else settings.llm.provider
                if target_pid and hasattr(settings.providers, "items"):
                    pconf = settings.providers.items.get(target_pid)
                    if pconf is None and target_pid:
                        settings.providers.items[target_pid] = ProviderItemConfig()
                        changed_settings.append(f"添加 Provider: {target_pid}")
                        pconf = settings.providers.items[target_pid]
                    if pconf:
                        if new_key and new_key != "********":
                            pconf.api_key = new_key
                            changed_settings.append(f"API Key 已更新")
                        if new_model:
                            pconf.model = new_model
                            # 同步写 llm.model 让 is_configured() 生效
                            settings.llm.model = new_model
                            changed_settings.append(f"Model: {new_model}")
                        if new_url:
                            pconf.base_url = new_url
                            changed_settings.append(f"Base URL: {new_url}")
        except Exception:
            pass

        # 点击已配置的 provider 条目 → 设为激活
        try:
            for widget in self.query(".provider-config-item"):
                if hasattr(widget, "_provider_id"):
                    pid = widget._provider_id
                    if settings.llm.provider != pid:
                        settings.llm.provider = pid
                        # 同步 model
                        pconf = (
                            settings.providers.items.get(pid)
                            if hasattr(settings, "providers")
                            else None
                        )
                        stored = getattr(pconf, "model", "") or ""
                        if stored:
                            settings.llm.model = stored
                        elif not settings.llm.model:
                            settings.llm.model = ""
                        changed_settings.append(f"激活 Provider: {pid}")
        except Exception:
            pass

        # Provider 编辑表单保存
        editing_pid = getattr(self, "_editing_provider_id", None)
        if editing_pid:
            from tui.views.settings.models import ProviderItemConfig

            pconf = settings.providers.items.get(editing_pid)
            if pconf is None:
                pconf = ProviderItemConfig(enabled=True)
                settings.providers.items[editing_pid] = pconf

            changed = False
            try:
                key_inp = self.query_one("#provider-apikey-input", Input)
                new_key = key_inp.value.strip()
                if new_key and new_key != "********":
                    pconf.api_key = new_key
                    changed = True
            except Exception:
                pass
            try:
                model_inp = self.query_one("#provider-model-input", Input)
                new_model = model_inp.value.strip()
                if new_model != (pconf.model or ""):
                    pconf.model = new_model
                    changed = True
            except Exception:
                pass
            try:
                url_inp = self.query_one("#provider-baseurl-input", Input)
                new_url = url_inp.value.strip()
                if new_url != (pconf.base_url or ""):
                    pconf.base_url = new_url
                    changed = True
            except Exception:
                pass
            if changed:
                changed_settings.append(f"更新 Provider: {editing_pid}")

        # 模型参数（带范围验证）
        try:
            temp_input = self.query_one("#model-temperature-input", Input)
            temp_val = float(temp_input.value) if temp_input.value else 0.7
            if 0.0 <= temp_val <= 1.0:
                if settings.model_settings.temperature != temp_val:
                    settings.model_settings.temperature = temp_val
                    changed_settings.append(f"Temperature: {temp_val}")
            else:
                validation_errors.append(
                    f"Temperature 必须在 0.0-1.0 范围内（当前: {temp_val}）"
                )
        except ValueError:
            validation_errors.append("Temperature 必须是数字")
        except Exception:
            pass
        try:
            maxtokens_input = self.query_one("#model-maxtokens-input", Input)
            maxtokens_val = (
                int(maxtokens_input.value) if maxtokens_input.value else 4096
            )
            if maxtokens_val > 0:
                if settings.model_settings.max_tokens != maxtokens_val:
                    settings.model_settings.max_tokens = maxtokens_val
                    changed_settings.append(f"Max Tokens: {maxtokens_val}")
            else:
                validation_errors.append(
                    f"Max Tokens 必须是正整数（当前: {maxtokens_val}）"
                )
        except ValueError:
            validation_errors.append("Max Tokens 必须是整数")
        except Exception:
            pass
        try:
            context_input = self.query_one("#model-contextwindow-input", Input)
            context_val = int(context_input.value) if context_input.value else 128000
            if context_val > 0:
                if settings.model_settings.context_window != context_val:
                    settings.model_settings.context_window = context_val
                    changed_settings.append(f"Context Window: {context_val}")
            else:
                validation_errors.append(
                    f"Context Window 必须是正整数（当前: {context_val}）"
                )
        except ValueError:
            validation_errors.append("Context Window 必须是整数")
        except Exception:
            pass

        # 辅助任务专用模型
        aux_fields = [
            ("compression_model", "compression_model"),
            ("title_model", "title_model"),
            ("synthesis_model", "synthesis_model"),
            ("memory_model", "memory_model"),
            ("auxiliary_model", "auxiliary_model"),
        ]
        for fid, label_key in aux_fields:
            try:
                inp = self.query_one(f"#model-{fid}-input", Input)
                new_val = inp.value.strip()
                old_val = getattr(settings.model_settings, fid, "") or ""
                if new_val != old_val:
                    setattr(settings.model_settings, fid, new_val)
                    changed_settings.append(f"{self._t(label_key)}: {new_val or self._t('depth_normal')}")
            except Exception:
                pass

        # Fallback chain: add from dropdown
        try:
            add_sel = self.query_one("#fallback-add-select", Select)
            selected = add_sel.value
            if selected and selected != "__add__":
                from tui.views.settings.models import FallbackProviderItem

                fb_items = (
                    settings.fallback_providers.items
                    if hasattr(settings, "fallback_providers")
                    else []
                )
                # Avoid duplicates
                existing = [getattr(fb, "provider", "") or "" for fb in fb_items]
                if selected not in existing:
                    fb_items.append(FallbackProviderItem(provider=selected))
                    settings.fallback_providers.items = fb_items
                    changed_settings.append(f"添加 Fallback: {selected}")
        except Exception:
            pass

        # Agent 参数（带范围验证）
        try:
            maxiter_input = self.query_one("#agent-maxiterations-input", Input)
            maxiter_val = int(maxiter_input.value) if maxiter_input.value else 10
            if maxiter_val > 0:
                if settings.agent.max_turns != maxiter_val:
                    settings.agent.max_turns = maxiter_val
                    changed_settings.append(f"最大迭代次数: {maxiter_val}")
            else:
                validation_errors.append(
                    f"最大迭代次数 必须是正整数（当前: {maxiter_val}）"
                )
        except ValueError:
            validation_errors.append("最大迭代次数 必须是整数")
        except Exception:
            pass
        try:
            timeout_input = self.query_one("#agent-timeout-input", Input)
            timeout_val = float(timeout_input.value) if timeout_input.value else 60.0
            if timeout_val > 0:
                if settings.agent.gateway_timeout != timeout_val:
                    settings.agent.gateway_timeout = timeout_val
                    changed_settings.append(f"超时时间: {timeout_val}s")
            else:
                validation_errors.append(f"超时时间 必须是正数（当前: {timeout_val}）")
        except ValueError:
            validation_errors.append(f"timeout: {self._t('timeout')} must be a number")
        except Exception:
            pass

        # 终端后端：value 直接就是代码
        try:
            backend_select = self.query_one("#terminal-backend-select", Select)
            new_backend = backend_select.value
            if settings.terminal.backend != new_backend:
                settings.terminal.backend = new_backend
                changed_settings.append(f"Terminal: {new_backend}")
        except Exception:
            pass

        # 偏好设置
        try:
            depth_select = self.query_one("#depth-select", Select)
            prefs = self._settings_manager.get_settings().preferences
            if hasattr(prefs, "explanation_depth"):
                new_depth = depth_select.value
                if prefs.explanation_depth.value != new_depth:
                    prefs.explanation_depth.value = new_depth
                    changed_settings.append(f"explanation_depth: {new_depth}")
        except Exception:
            pass
        try:
            format_select = self.query_one("#format-select", Select)
            prefs = self._settings_manager.get_settings().preferences
            if hasattr(prefs, "response_format"):
                new_format = format_select.value
                if prefs.response_format.value != new_format:
                    prefs.response_format.value = new_format
                    changed_settings.append(f"response_format: {new_format}")
        except Exception:
            pass

        # 会话开关
        try:
            new_enabled = self.query_one("#session-enabled-switch", Switch).value
            if settings.session.enabled != new_enabled:
                settings.session.enabled = new_enabled
                changed_settings.append(f"session: {new_enabled}")
        except Exception:
            pass

        # 记忆开关
        try:
            new_mem = self.query_one("#memory-enabled-switch", Switch).value
            if settings.memory.enabled != new_mem:
                settings.memory.enabled = new_mem
                changed_settings.append(f"memory: {new_mem}")
        except Exception:
            pass

        # 语义检索开关
        try:
            new_sem = self.query_one("#semantic-switch", Switch).value
            if settings.memory.semantic_retrieval_enabled != new_sem:
                settings.memory.semantic_retrieval_enabled = new_sem
                changed_settings.append(f"semantic: {new_sem}")
        except Exception:
            pass

        # 压缩开关
        try:
            new_comp = self.query_one("#compression-switch", Switch).value
            if settings.compression.enabled != new_comp:
                settings.compression.enabled = new_comp
                changed_settings.append(f"compression: {new_comp}")
        except Exception:
            pass

        # 会话重置模式
        try:
            reset_select = self.query_one("#reset-mode-select", Select)
            new_reset = reset_select.value
            if settings.session_reset.mode.value != new_reset:
                settings.session_reset.mode.value = new_reset
                changed_settings.append(f"reset_mode: {new_reset}")
        except Exception:
            pass

        # STT/TTS 开关
        try:
            new_stt = self.query_one("#stt-switch", Switch).value
            if settings.tools.stt_enabled != new_stt:
                settings.tools.stt_enabled = new_stt
                changed_settings.append(f"stt: {new_stt}")
        except Exception:
            pass
        try:
            new_tts = self.query_one("#tts-switch", Switch).value
            if settings.tools.tts_enabled != new_tts:
                settings.tools.tts_enabled = new_tts
                changed_settings.append(f"tts: {new_tts}")
        except Exception:
            pass
        try:
            new_browser = self.query_one("#browser-switch", Switch).value
            if settings.tools.browser_enabled != new_browser:
                settings.tools.browser_enabled = new_browser
                changed_settings.append(f"browser: {new_browser}")
        except Exception:
            pass

        # 文件日志开关
        try:
            new_log = self.query_one("#file-log-switch", Switch).value
            if settings.logging.file_enabled != new_log:
                settings.logging.file_enabled = new_log
                changed_settings.append(f"file_log: {new_log}")
        except Exception:
            pass

        return validation_errors, changed_settings

    def action_next_category(self) -> None:
        """切换到下一个分类"""
        if CategoryMeta:
            next_cat = CategoryMeta.get_next_category(self._current_category)
            self._switch_category(next_cat)

    def action_prev_category(self) -> None:
        """切换到上一个分类"""
        if CategoryMeta:
            prev_cat = CategoryMeta.get_prev_category(self._current_category)
            self._switch_category(prev_cat)

    def action_reset_category(self) -> None:
        """重置当前分类"""
        if self._settings_manager:
            self._settings_manager.reset_to_defaults(self._current_category)
            self._switch_category(self._current_category)  # 刷新内容
            self.notify(self._t("reset_done"), timeout=2.0)

    def on_mount(self) -> None:
        """挂载时初始化"""
        # 默认选中按钮已在 compose 时通过 classes 设置
