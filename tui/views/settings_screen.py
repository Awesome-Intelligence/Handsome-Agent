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
try:
    from common.logging_manager import get_access_logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    def get_access_logger(*args, **kwargs):
        return logging.getLogger("HandsomeAgent")

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
    background: $boost 40%;
}

#settings-container {
    width: 90%;
    height: 80%;
    border: solid $accent;
    background: $surface;
}

#settings-header {
    height: 3;
    background: $primary;
    content-align: center middle;
    border-bottom: solid $border;
}

#settings-header Static {
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
    content-align: center middle;
    color: $text-muted;
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

    def compose(self) -> ComposeResult:
        """组合组件"""
        with Container(id="settings-container"):
            # 头部
            with Container(id="settings-header"):
                yield Static("⚙ 设置", id="settings-title")

            # 主体：左侧分类树 + 右侧内容
            with Horizontal(id="settings-body"):
                # 侧边栏分类导航
                with Container(id="sidebar"):
                    yield from self._compose_sidebar_tree()

                # 内容区
                with VerticalScroll(id="content-area"):
                    yield from self._compose_content()

            yield Static("Tab 切换分类  |  ↑↓ 移动  |  Enter/Space 确认  |  Ctrl+S 保存  |  Ctrl+R 重置  |  Esc 关闭", id="settings-footer")

    def _compose_sidebar_tree(self) -> ComposeResult:
        """生成侧边栏分类树"""
        tree = Tree("Categories", id="category-tree")
        tree.show_root = False  # Textual 8.x 用属性设置
        tree.show_guides = False
        # 添加分类节点
        if CategoryMeta:
            for cat_id, icon, name, _ in CategoryMeta.CATEGORIES:
                label = f"{icon}  {name}"
                node = tree.root.add(label, data=cat_id)
                if cat_id == self._current_category:
                    tree.select_node(node)
        yield tree

    def _compose_content(self) -> ComposeResult:
        """生成设置内容区"""
        yield from self._build_category_content(self._current_category)

    def _build_category_content(self, category: str) -> ComposeResult:
        """根据分类构建内容"""
        settings = self._settings_manager.get_settings() if self._settings_manager else SettingsDocument()

        # 根据分类生成不同的设置项
        if category == "language":
            yield from self._build_language_content(settings)
        elif category == "llm":
            yield from self._build_llm_content(settings)
        elif category == "model":
            yield from self._build_model_content(settings)
        elif category == "terminal":
            yield from self._build_terminal_content(settings)
        elif category == "agent":
            yield from self._build_agent_content(settings)
        elif category == "session":
            yield from self._build_session_content(settings)
        elif category == "preferences":
            yield from self._build_preferences_content(settings)
        elif category == "tools":
            yield from self._build_tools_content(settings)
        elif category == "logging":
            yield from self._build_logging_content(settings)
        elif category == "about":
            yield from self._build_about_content(settings)
        else:
            yield Static("暂无设置项", id="no-settings")

    def _build_language_content(self, settings: SettingsDocument) -> ComposeResult:
        """构建语言设置内容"""
        yield Static("🌐 显示语言", classes="setting-group-title")
        language_options = [
            ("中文", "中文"),
            ("English", "English"),
        ]
        current = settings.display.language.value if hasattr(settings.display, 'language') else "zh"
        current_label = "中文" if current == "zh" else "English"
        yield Select(
            options=language_options,
            value=current_label,
            id="language-select",
            allow_blank=False,
            classes="setting-row"
        )

    def _build_llm_content(self, settings: SettingsDocument) -> ComposeResult:
        """构建 LLM 设置内容"""
        yield Static("🤖 大模型配置", classes="setting-group-title")

        # Provider 选择
        yield Static("Provider", classes="setting-row")
        try:
            from cli.cli_commands.providers import PROVIDERS
            provider_options = [(p["name"], p["name"]) for p in PROVIDERS.values()]
            # 通过 provider id 查找显示名称
            provider_id = settings.llm.provider if hasattr(settings.llm, 'provider') else "openai"
            current_provider = "OpenAI"
            for p in PROVIDERS.values():
                if p.get("name", "").lower() == provider_id.lower():
                    current_provider = p["name"]
                    break
            else:
                # 没找到对应 name，可能是 id 本身
                current_provider = PROVIDERS.get(provider_id, {}).get("name", provider_id.title())
        except ImportError:
            provider_options = [("OpenAI", "OpenAI")]
            current_provider = "OpenAI"
        # 空值保护
        if not current_provider:
            current_provider = provider_options[0][1]
        yield Select(
            options=provider_options,
            value=current_provider,
            id="llm-provider-select",
            allow_blank=False,
            classes="setting-row"
        )

        # Model 输入
        yield Static("模型名称", classes="setting-row")
        current_model = settings.llm.model if hasattr(settings.llm, 'model') else ""
        placeholder_model = current_model if current_model else "gpt-4o-mini"
        yield Input(current_model, id="llm-model-input", placeholder=f"当前: {placeholder_model}", classes="setting-row")

        # Base URL 输入
        yield Static("Base URL (可选)", classes="setting-row")
        current_url = settings.llm.base_url if hasattr(settings.llm, 'base_url') else ""
        placeholder_url = current_url if current_url else "https://api.example.com/v1"
        yield Input(current_url, id="llm-url-input", placeholder=f"当前: {placeholder_url}", classes="setting-row")

        # API Key 输入（密码模式）
        yield Static("API Key (可选)", classes="setting-row")
        current_api_key = settings.llm.api_key if hasattr(settings.llm, 'api_key') else ""
        display_api_key = "********" if current_api_key else ""
        yield Input(
            display_api_key,
            id="llm-apikey-input",
            placeholder="输入新 API Key（不填则保留原值）",
            password=True,
            classes="setting-row"
        )

    def _build_model_content(self, settings: SettingsDocument) -> ComposeResult:
        """构建模型参数设置内容"""
        yield Static("🔧 模型参数", classes="setting-group-title")

        model = settings.model

        yield Static("Temperature (0.0-1.0)", classes="setting-row")
        yield Input(
            str(model.temperature),
            id="model-temperature-input",
            placeholder=f"当前: {model.temperature} (范围: 0.0-1.0)",
            classes="setting-row"
        )

        yield Static("Max Tokens", classes="setting-row")
        yield Input(
            str(model.max_tokens),
            id="model-maxtokens-input",
            placeholder=f"当前: {model.max_tokens}",
            classes="setting-row"
        )

        yield Static("Context Window", classes="setting-row")
        yield Input(
            str(model.context_window),
            id="model-contextwindow-input",
            placeholder=f"当前: {model.context_window}",
            classes="setting-row"
        )

    def _build_terminal_content(self, settings: SettingsDocument) -> ComposeResult:
        """构建终端设置内容"""
        yield Static("💻 终端设置", classes="setting-group-title")

        backend_options = [
            ("本地执行", "本地执行"),
            ("Docker 容器", "Docker 容器"),
        ]
        current_backend = "本地执行" if hasattr(settings.terminal, 'backend') and settings.terminal.backend == 'local' else "Docker 容器"
        yield Select(
            options=backend_options,
            value=current_backend,
            id="terminal-backend-select",
            allow_blank=False,
            classes="setting-row"
        )

    def _build_agent_content(self, settings: SettingsDocument) -> ComposeResult:
        """构建 Agent 设置内容"""
        yield Static("⚙️ Agent 设置", classes="setting-group-title")

        agent = settings.agent

        yield Static("最大迭代次数", classes="setting-row")
        yield Input(
            str(agent.max_iterations),
            id="agent-maxiterations-input",
            placeholder=f"当前: {agent.max_iterations}",
            classes="setting-row"
        )

        yield Static("超时时间 (秒)", classes="setting-row")
        yield Input(
            str(agent.timeout_seconds),
            id="agent-timeout-input",
            placeholder=f"当前: {agent.timeout_seconds}s",
            classes="setting-row"
        )

    def _build_session_content(self, settings: SettingsDocument) -> ComposeResult:
        """构建会话设置内容"""
        yield Static("🔄 会话与记忆", classes="setting-group-title")

        session = settings.session
        memory = settings.memory
        compression = settings.compression

        # 会话开关
        yield Static("启用会话", classes="setting-row")
        yield Switch(session.enabled, id="session-enabled-switch", classes="setting-row")

        # 记忆系统开关
        yield Static("启用记忆系统", classes="setting-row")
        yield Switch(memory.enabled, id="memory-enabled-switch", classes="setting-row")

        # 语义检索开关
        yield Static("启用语义检索", classes="setting-row")
        yield Switch(memory.semantic_retrieval_enabled, id="semantic-switch", classes="setting-row")

        # Context 压缩开关
        yield Static("启用 Context 压缩", classes="setting-row")
        yield Switch(compression.enabled, id="compression-switch", classes="setting-row")

    def _build_preferences_content(self, settings: SettingsDocument) -> ComposeResult:
        """构建响应偏好设置内容"""
        yield Static("📝 响应偏好", classes="setting-group-title")

        prefs = settings.preferences

        # 详细程度
        depth_options = [
            ("简洁", "简洁"),
            ("普通", "普通"),
            ("详细", "详细"),
        ]
        current_depth = prefs.explanation_depth.value if hasattr(prefs, 'explanation_depth') else "普通"
        depth_label_map = {"brief": "简洁", "normal": "普通", "detailed": "详细"}
        depth_label = depth_label_map.get(current_depth, "普通")
        yield Static("详细程度", classes="setting-row")
        yield Select(
            options=depth_options,
            value=depth_label,
            id="depth-select",
            allow_blank=False,
            classes="setting-row"
        )

        # 响应格式
        format_options = [
            ("自动", "自动"),
            ("Markdown", "Markdown"),
            ("纯文本", "纯文本"),
        ]
        current_format = prefs.response_format.value if hasattr(prefs, 'response_format') else "markdown"
        format_label_map = {"auto": "自动", "markdown": "Markdown", "plain": "纯文本"}
        format_label = format_label_map.get(current_format, "Markdown")
        yield Static("响应格式", classes="setting-row")
        yield Select(
            options=format_options,
            value=format_label,
            id="format-select",
            allow_blank=False,
            classes="setting-row"
        )

    def _build_tools_content(self, settings: SettingsDocument) -> ComposeResult:
        """构建工具设置内容"""
        yield Static("🛠️ 工具设置", classes="setting-group-title")

        tools = settings.tools

        yield Static("STT (语音转文字)", classes="setting-row")
        yield Switch(tools.stt_enabled, id="stt-switch", classes="setting-row")

        yield Static("TTS (文字转语音)", classes="setting-row")
        yield Switch(tools.tts_enabled, id="tts-switch", classes="setting-row")

        yield Static("Browser 工具", classes="setting-row")
        yield Switch(tools.browser_enabled, id="browser-switch", classes="setting-row")

    def _build_logging_content(self, settings: SettingsDocument) -> ComposeResult:
        """构建日志设置内容"""
        yield Static("📄 日志设置", classes="setting-group-title")

        yield Static("启用文件日志", classes="setting-row")
        yield Switch(settings.logging.file_enabled, id="file-log-switch", classes="setting-row")

    def _build_about_content(self, settings: SettingsDocument) -> ComposeResult:
        """构建关于内容"""
        about = settings.about
        yield Static("ℹ️ 关于 Handsome Agent", classes="about-title")
        yield Static(f"版本: {about.version}", classes="about-content")
        yield Static(f"许可证: {about.license}", classes="about-content")
        yield Static("一个基于 LLM 的智能助手", classes="about-content")

    # ========================================================================
    # 事件处理
    # ========================================================================

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """处理分类树节点选择"""
        if event.node.data and isinstance(event.node.data, str):
            cat_id = event.node.data
            if cat_id != self._current_category:
                self._switch_category(cat_id)

    def _switch_category(self, category: str) -> None:
        """切换到指定分类"""
        self._current_category = category

        # 更新树的选择
        tree = self.query_one("#category-tree", Tree)
        for node in tree.root.children:
            if node.data == category:
                tree.select_node(node)
                break

        # 刷新内容区
        content_area = self.query_one("#content-area", VerticalScroll)
        # 清除旧内容
        for widget in content_area.query("*"):
            widget.remove()
        # 重新构建内容
        for widget in self._build_category_content(category):
            content_area.mount(widget)

        self._logger.debug(f"Switched to category: {category}")

    def action_close(self) -> None:
        """关闭设置界面"""
        self._logger.debug("Settings screen closed")
        self.post_message(SettingsClosed())
        self.dismiss()

    def action_save(self) -> None:
        """保存设置"""
        # 从控件收集设置值（验证数值范围）
        validation_errors, changed_settings = self._collect_settings()

        # 如果有验证错误，不保存并提示
        if validation_errors:
            error_msg = "✗ " + "\n✗ ".join(validation_errors[:3])
            if len(validation_errors) > 3:
                error_msg += f"\n... 还有 {len(validation_errors) - 3} 个错误"
            self.notify(error_msg, timeout=4.0)
            return

        if self._settings_manager:
            if self._settings_manager.save():
                # 显示变更列表
                if changed_settings:
                    changes_msg = "✓ 已保存: " + ", ".join(changed_settings[:5])
                    if len(changed_settings) > 5:
                        changes_msg += f"\n... 还有 {len(changed_settings) - 5} 项"
                    self.notify(changes_msg, timeout=3.0)
                else:
                    self.notify("✓ 设置已保存（无变更）", timeout=2.0)
            else:
                self._logger.error("Failed to save settings")
                self.notify("✗ 保存失败", timeout=2.0)
        self.post_message(SettingsSaved(self))
        self.dismiss()

    def _collect_settings(self) -> tuple[list, list]:
        """从控件收集设置值并保存到 manager，返回 (验证错误列表, 变更列表)"""
        validation_errors = []
        changed_settings = []

        if not self._settings_manager:
            return validation_errors, changed_settings

        settings = self._settings_manager.get_settings()

        # 语言设置（Select）：label → value
        try:
            lang_select = self.query_one("#language-select", Select)
            lang_map = {"中文": "zh", "English": "en"}
            old_lang = settings.display.language.value
            new_lang = lang_map.get(lang_select.value, "zh")
            if old_lang != new_lang:
                settings.display.language.value = new_lang
                changed_settings.append(f"语言: {old_lang} → {new_lang}")
        except Exception:
            pass

        # LLM Provider：label → provider id
        try:
            from cli.cli_commands.providers import PROVIDERS
            provider_select = self.query_one("#llm-provider-select", Select)
            provider_id = next(
                (k for k, p in PROVIDERS.items() if p["name"] == provider_select.value),
                provider_select.value.lower()
            )
            if settings.llm.provider != provider_id:
                settings.llm.provider = provider_id
                changed_settings.append(f"Provider: {provider_id}")
        except Exception:
            pass

        # API Key（如果用户修改了才保存）
        try:
            apikey_input = self.query_one("#llm-apikey-input", Input)
            new_api_key = apikey_input.value.strip()
            if new_api_key and new_api_key != "********":
                settings.llm.api_key = new_api_key
                changed_settings.append("API Key: 已修改")
            elif new_api_key == "":
                settings.llm.api_key = ""
        except Exception:
            pass

        # Model 名称
        try:
            model_input = self.query_one("#llm-model-input", Input)
            new_model = model_input.value.strip()
            if settings.llm.model != new_model:
                settings.llm.model = new_model
                changed_settings.append(f"Model: {new_model}")
        except Exception:
            pass

        # Base URL
        try:
            url_input = self.query_one("#llm-url-input", Input)
            new_url = url_input.value.strip()
            if settings.llm.base_url != new_url:
                settings.llm.base_url = new_url
                changed_settings.append(f"Base URL: {new_url}")
        except Exception:
            pass

        # 模型参数（带范围验证）
        try:
            temp_input = self.query_one("#model-temperature-input", Input)
            temp_val = float(temp_input.value) if temp_input.value else 0.7
            if 0.0 <= temp_val <= 1.0:
                if settings.model.temperature != temp_val:
                    settings.model.temperature = temp_val
                    changed_settings.append(f"Temperature: {temp_val}")
            else:
                validation_errors.append(f"Temperature 必须在 0.0-1.0 范围内（当前: {temp_val}）")
        except ValueError:
            validation_errors.append("Temperature 必须是数字")
        except Exception:
            pass
        try:
            maxtokens_input = self.query_one("#model-maxtokens-input", Input)
            maxtokens_val = int(maxtokens_input.value) if maxtokens_input.value else 4096
            if maxtokens_val > 0:
                if settings.model.max_tokens != maxtokens_val:
                    settings.model.max_tokens = maxtokens_val
                    changed_settings.append(f"Max Tokens: {maxtokens_val}")
            else:
                validation_errors.append(f"Max Tokens 必须是正整数（当前: {maxtokens_val}）")
        except ValueError:
            validation_errors.append("Max Tokens 必须是整数")
        except Exception:
            pass
        try:
            context_input = self.query_one("#model-contextwindow-input", Input)
            context_val = int(context_input.value) if context_input.value else 128000
            if context_val > 0:
                if settings.model.context_window != context_val:
                    settings.model.context_window = context_val
                    changed_settings.append(f"Context Window: {context_val}")
            else:
                validation_errors.append(f"Context Window 必须是正整数（当前: {context_val}）")
        except ValueError:
            validation_errors.append("Context Window 必须是整数")
        except Exception:
            pass

        # Agent 参数（带范围验证）
        try:
            maxiter_input = self.query_one("#agent-maxiterations-input", Input)
            maxiter_val = int(maxiter_input.value) if maxiter_input.value else 10
            if maxiter_val > 0:
                if settings.agent.max_iterations != maxiter_val:
                    settings.agent.max_iterations = maxiter_val
                    changed_settings.append(f"最大迭代次数: {maxiter_val}")
            else:
                validation_errors.append(f"最大迭代次数 必须是正整数（当前: {maxiter_val}）")
        except ValueError:
            validation_errors.append("最大迭代次数 必须是整数")
        except Exception:
            pass
        try:
            timeout_input = self.query_one("#agent-timeout-input", Input)
            timeout_val = float(timeout_input.value) if timeout_input.value else 60.0
            if timeout_val > 0:
                if settings.agent.timeout_seconds != timeout_val:
                    settings.agent.timeout_seconds = timeout_val
                    changed_settings.append(f"超时时间: {timeout_val}s")
            else:
                validation_errors.append(f"超时时间 必须是正数（当前: {timeout_val}）")
        except ValueError:
            validation_errors.append("超时时间必须是数字")
        except Exception:
            pass

        # 终端后端：label → value
        try:
            backend_select = self.query_one("#terminal-backend-select", Select)
            backend_map = {"本地执行": "local", "Docker 容器": "docker"}
            new_backend = backend_map.get(backend_select.value, "local")
            if settings.terminal.backend != new_backend:
                settings.terminal.backend = new_backend
                changed_settings.append(f"终端: {new_backend}")
        except Exception:
            pass

        # 偏好设置
        try:
            depth_select = self.query_one("#depth-select", Select)
            depth_map = {"简洁": "brief", "普通": "normal", "详细": "detailed"}
            prefs = self._settings_manager.get_settings().preferences
            if hasattr(prefs, 'explanation_depth'):
                new_depth = depth_map.get(depth_select.value, "normal")
                if prefs.explanation_depth.value != new_depth:
                    prefs.explanation_depth.value = new_depth
                    changed_settings.append(f"详细程度: {new_depth}")
        except Exception:
            pass
        try:
            format_select = self.query_one("#format-select", Select)
            format_map = {"自动": "auto", "Markdown": "markdown", "纯文本": "plain"}
            prefs = self._settings_manager.get_settings().preferences
            if hasattr(prefs, 'response_format'):
                new_format = format_map.get(format_select.value, "markdown")
                if prefs.response_format.value != new_format:
                    prefs.response_format.value = new_format
                    changed_settings.append(f"响应格式: {new_format}")
        except Exception:
            pass

        # 会话开关
        try:
            new_enabled = self.query_one("#session-enabled-switch", Switch).value
            if settings.session.enabled != new_enabled:
                settings.session.enabled = new_enabled
                changed_settings.append(f"会话: {'启用' if new_enabled else '禁用'}")
        except Exception:
            pass

        # 记忆开关
        try:
            new_mem = self.query_one("#memory-enabled-switch", Switch).value
            if settings.memory.enabled != new_mem:
                settings.memory.enabled = new_mem
                changed_settings.append(f"记忆系统: {'启用' if new_mem else '禁用'}")
        except Exception:
            pass

        # 语义检索开关
        try:
            new_sem = self.query_one("#semantic-switch", Switch).value
            if settings.memory.semantic_retrieval_enabled != new_sem:
                settings.memory.semantic_retrieval_enabled = new_sem
                changed_settings.append(f"语义检索: {'启用' if new_sem else '禁用'}")
        except Exception:
            pass

        # 压缩开关
        try:
            new_comp = self.query_one("#compression-switch", Switch).value
            if settings.compression.enabled != new_comp:
                settings.compression.enabled = new_comp
                changed_settings.append(f"Context压缩: {'启用' if new_comp else '禁用'}")
        except Exception:
            pass

        # STT/TTS 开关
        try:
            new_stt = self.query_one("#stt-switch", Switch).value
            if settings.tools.stt_enabled != new_stt:
                settings.tools.stt_enabled = new_stt
                changed_settings.append(f"STT: {'启用' if new_stt else '禁用'}")
        except Exception:
            pass
        try:
            new_tts = self.query_one("#tts-switch", Switch).value
            if settings.tools.tts_enabled != new_tts:
                settings.tools.tts_enabled = new_tts
                changed_settings.append(f"TTS: {'启用' if new_tts else '禁用'}")
        except Exception:
            pass
        try:
            new_browser = self.query_one("#browser-switch", Switch).value
            if settings.tools.browser_enabled != new_browser:
                settings.tools.browser_enabled = new_browser
                changed_settings.append(f"Browser: {'启用' if new_browser else '禁用'}")
        except Exception:
            pass

        # 文件日志开关
        try:
            new_log = self.query_one("#file-log-switch", Switch).value
            if settings.logging.file_enabled != new_log:
                settings.logging.file_enabled = new_log
                changed_settings.append(f"文件日志: {'启用' if new_log else '禁用'}")
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
            self.notify("✓ 已重置", timeout=2.0)

    def on_mount(self) -> None:
        """挂载时初始化"""
        # 设置默认选中分类
        tree = self.query_one("#category-tree", Tree)
        if tree.root.children:
            tree.select_node(tree.root.children[0])