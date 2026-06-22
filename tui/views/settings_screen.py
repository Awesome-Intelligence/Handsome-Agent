#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Settings Screen - TUI 设置界面模态窗口

提供完整的设置界面功能:
- 左侧分类列表
- 右侧设置内容区
- 键盘导航
- 设置保存

🚪 Access - 💬 CLI - TUI Views - SettingsScreen
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

# Textual 框架导入
TEXTUAL_AVAILABLE = True
try:
    from textual.app import ComposeResult
    from textual.screen import ModalScreen
    from textual.widgets import Static, Button
    from textual.containers import Container, Horizontal, Vertical, VerticalScroll
    from textual.binding import Binding
    from textual.message import Message
except ImportError:
    TEXTUAL_AVAILABLE = False
    ModalScreen = object
    Static = object
    Button = object
    Container = object
    Horizontal = object
    Vertical = object
    VerticalScroll = object
    Binding = object
    Message = object

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
    from tui.views.settings.models import (
        Language, ExplanationDepth, IntentMode, SessionResetMode, TerminalBackend,
        ResponseFormat
    )
except ImportError:
    SettingsManager = None
    SettingsDocument = None
    CategoryMeta = None


# ============================================================================
# 主题颜色常量
# ============================================================================

AVOCADO_PRIMARY = "#B180D7"
AVOCADO_BRIGHT = "#C9A0E0"
AVOCADO_DIM = "#8B5CAC"
AVOCADO_DARK = "#6B4EA8"
WHITE = "white"
GRAY_DIM = "#888888"
GOLD = "#FFD700"
SUCCESS = "#50C878"


# ============================================================================
# CSS 样式
# ============================================================================

SETTINGS_SCREEN_CSS = """
SettingsScreen {
    align: center middle;
}

#settings-container {
    width: 90%;
    height: 85%;
    border: solid $primary;
    background: $surface;
}

#settings-header {
    height: 3;
    background: $primary;
    content-align: center middle;
}

#settings-header Static {
    color: $text;
    text-style: bold;
}

#settings-body {
    height: 1fr;
}

#sidebar {
    width: 25%;
    height: 100%;
    background: $panel;
    border-right: solid $border;
}

#sidebar VerticalScroll {
    height: 100%;
}

.category-item {
    height: 3;
    padding: 0 2;
    content-align: left middle;
}

.category-item:hover {
    background: $accent 15%;
}

.category-item.active {
    background: $accent 25%;
    color: $accent;
    text-style: bold;
}

#content {
    width: 75%;
    height: 100%;
}

#content-scroll {
    height: 100%;
    padding: 1 2;
}

.setting-item {
    height: 3;
    padding: 0 1;
    content-align: left middle;
    border-bottom: solid $border;
}

.setting-item:hover {
    background: $accent 10%;
}

.setting-item.focused {
    background: $accent 20%;
}

.setting-label {
    width: 40%;
    color: $text-muted;
}

.setting-value {
    width: 60%;
    color: $accent;
}

.setting-toggle {
    width: 5%;
    color: $success;
}

.setting-toggle.off {
    color: $text-muted;
}

.setting-separator {
    height: 1;
    background: $border;
}

#settings-footer {
    height: 3;
    background: $panel;
    content-align: center middle;
}

#settings-footer Static {
    color: $text-muted;
}

.about-section {
    padding: 2 1;
    height: auto;
}

.about-title {
    text-style: bold;
    color: $accent;
    padding-bottom: 1;
}

.about-content {
    color: $text;
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
    """TUI 设置界面模态窗口"""
    
    CSS = SETTINGS_SCREEN_CSS
    
    BINDINGS = [
        Binding("escape", "close", "关闭", show=False),
        Binding("q", "close", "关闭", show=False),
        Binding("tab", "next_category", "下一分类", show=False),
        Binding("shift+tab", "prev_category", "上一分类", show=False),
        Binding("s", "save", "保存", show=False),
        Binding("r", "reset_category", "重置", show=False),
        Binding("up", "move_up", "上移", show=False),
        Binding("down", "move_down", "下移", show=False),
        Binding("left", "focus_sidebar", "侧边栏", show=False),
        Binding("right", "focus_content", "内容区", show=False),
        Binding("j", "move_down", "下移", show=False),
        Binding("k", "move_up", "上移", show=False),
        Binding("h", "focus_sidebar", "侧边栏", show=False),
        Binding("l", "focus_content", "内容区", show=False),
        Binding("space", "toggle_current", "切换", show=False),
    ]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._settings_manager = get_settings_manager() if SettingsManager else None
        self._current_category: str = "language"
        self._current_item_index: int = 0
        self._focus_area: str = "content"  # sidebar | content
        self._logger = get_access_logger("SettingsScreen", sublayer="tui")
        self._pending_changes: dict = {}
    
    def compose(self) -> ComposeResult:
        """组合组件"""
        # 头部
        with Container(id="settings-header"):
            yield Static("⚙ 设置", id="settings-title")
        
        # 主体
        with Horizontal(id="settings-body"):
            # 侧边栏
            with Vertical(id="sidebar"):
                yield from self._compose_sidebar()
            
            # 内容区
            with VerticalScroll(id="content"):
                yield from self._compose_content()
        
        # 底部
        with Container(id="settings-footer"):
            yield Static(
                "↑↓ 移动  Tab 切换分类  Space 切换  s 保存  Esc 关闭",
                id="settings-hint"
            )
    
    def _compose_sidebar(self) -> ComposeResult:
        """生成侧边栏分类列表"""
        for cat_id, icon, name, _ in CategoryMeta.CATEGORIES:
            is_active = cat_id == self._current_category
            yield Static(
                f"{icon}  {name}",
                id=f"cat-{cat_id}",
                classes=f"category-item {'active' if is_active else ''}"
            )
    
    def _compose_content(self) -> ComposeResult:
        """生成设置内容区"""
        yield Static("", id="content-header", classes="setting-item")
        yield from self._get_category_items(self._current_category)
    
    def _get_category_items(self, category: str) -> list:
        """获取指定分类的设置项"""
        items = []
        settings = self._settings_manager.get_settings() if self._settings_manager else SettingsDocument()
        
        if category == "language":
            items = self._build_language_items(settings)
        elif category == "llm":
            items = self._build_llm_items(settings)
        elif category == "model":
            items = self._build_model_items(settings)
        elif category == "terminal":
            items = self._build_terminal_items(settings)
        elif category == "agent":
            items = self._build_agent_items(settings)
        elif category == "session":
            items = self._build_session_items(settings)
        elif category == "intent":
            items = self._build_intent_items(settings)
        elif category == "preferences":
            items = self._build_preferences_items(settings)
        elif category == "tools":
            items = self._build_tools_items(settings)
        elif category == "logging":
            items = self._build_logging_items(settings)
        elif category == "about":
            items = self._build_about_items(settings)
        
        return items
    
    def _build_language_items(self, settings: SettingsDocument) -> list:
        """构建语言设置项"""
        current = settings.display.language.value
        options = [
            ("zh", "中文"),
            ("en", "English"),
        ]
        options_text = "  ".join([f"{'●' if v == current else '○'} {l}" for v, l in options])
        return [
            Static(f"🌐 显示语言", classes="setting-item"),
            Static(options_text, classes="setting-item"),
        ]
    
    def _build_llm_items(self, settings: SettingsDocument) -> list:
        """构建 LLM 设置项"""
        return [
            Static("🤖 大模型", classes="setting-item setting-label"),
            Static(f"  Provider: {settings.llm.provider or '未配置'}", classes="setting-item"),
            Static(f"  模型: {settings.llm.model or '未配置'}", classes="setting-item"),
            Static(f"  Base URL: {settings.llm.base_url or '-'}", classes="setting-item"),
            Static("  ⚠ API Key 已配置" if settings.llm.provider else "  ⚠ 请先配置 Provider", classes="setting-item"),
        ]
    
    def _build_model_items(self, settings: SettingsDocument) -> list:
        """构建模型参数设置项"""
        model = settings.model
        return [
            Static("🔧 模型参数", classes="setting-item setting-label"),
            Static(f"  模型名称: {model.name or '未设置'}", classes="setting-item"),
            Static(f"  Temperature: {model.temperature}", classes="setting-item"),
            Static(f"  Max Tokens: {model.max_tokens}", classes="setting-item"),
            Static(f"  Context Window: {model.context_window}", classes="setting-item"),
        ]
    
    def _build_terminal_items(self, settings: SettingsDocument) -> list:
        """构建终端设置项"""
        current = settings.terminal.backend.value
        options = "  ".join([f"{'●' if v == current else '○'} {l}" for v, l in [("local", "本地执行"), ("docker", "Docker 容器")]])
        return [
            Static("💻 终端", classes="setting-item setting-label"),
            Static(options, classes="setting-item"),
        ]
    
    def _build_agent_items(self, settings: SettingsDocument) -> list:
        """构建 Agent 设置项"""
        agent = settings.agent
        return [
            Static("⚙️ Agent 设置", classes="setting-item setting-label"),
            Static(f"  最大迭代次数: {agent.max_iterations}", classes="setting-item"),
            Static(f"  超时时间: {agent.timeout_seconds}s", classes="setting-item"),
        ]
    
    def _build_session_items(self, settings: SettingsDocument) -> list:
        """构建会话设置项"""
        session = settings.session
        memory = settings.memory
        session_reset = settings.session_reset
        compression = settings.compression
        return [
            Static("🔄 会话", classes="setting-item setting-label"),
            Static(f"  启用: {'是' if session.enabled else '否'}", classes="setting-item"),
            Static(f"  存储方式: {session.storage}", classes="setting-item"),
            Static(f"  重置策略: {session_reset.mode.value}", classes="setting-item"),
            Static(f"  {'[×] 记忆系统' if memory.enabled else '[ ] 记忆系统'}", classes="setting-item"),
            Static(f"  {'[×] Context 压缩' if compression.enabled else '[ ] Context 压缩'}", classes="setting-item"),
        ]
    
    def _build_intent_items(self, settings: SettingsDocument) -> list:
        """构建意图识别设置项"""
        current = settings.intent_mode.value
        options = [
            ("llm", "大模型模式"),
            ("hybrid", "混合模式"),
            ("keyword", "关键词模式"),
        ]
        options_text = "  ".join([f"{'●' if v == current else '○'} {l}" for v, l in options])
        return [
            Static("🧠 意图识别", classes="setting-item setting-label"),
            Static(options_text, classes="setting-item"),
        ]
    
    def _build_preferences_items(self, settings: SettingsDocument) -> list:
        """构建响应偏好设置项"""
        prefs = settings.preferences
        return [
            Static("📝 响应偏好", classes="setting-item setting-label"),
            Static(f"  详细程度: {prefs.explanation_depth.value}", classes="setting-item"),
            Static(f"  响应格式: {prefs.response_format.value}", classes="setting-item"),
            Static(f"  日志级别: {prefs.log_level}", classes="setting-item"),
        ]
    
    def _build_tools_items(self, settings: SettingsDocument) -> list:
        """构建工具设置项"""
        tools = settings.tools
        return [
            Static("🛠️ 工具", classes="setting-item setting-label"),
            Static(f"  {'[×]' if tools.stt_enabled else '[ ]'} STT (语音转文字)", classes="setting-item"),
            Static(f"  {'[×]' if tools.tts_enabled else '[ ]'} TTS (文字转语音)", classes="setting-item"),
            Static(f"  {'[×]' if tools.browser_enabled else '[ ]'} Browser", classes="setting-item"),
            Static(f"  {'[×]' if tools.web_debug else '[ ]'} Web Debug", classes="setting-item"),
            Static(f"  {'[×]' if tools.vision_debug else '[ ]'} Vision Debug", classes="setting-item"),
        ]
    
    def _build_logging_items(self, settings: SettingsDocument) -> list:
        """构建日志设置项"""
        return [
            Static("📄 日志", classes="setting-item setting-label"),
            Static(f"  {'[×] 文件日志' if settings.logging.file_enabled else '[ ] 文件日志'}", classes="setting-item"),
        ]
    
    def _build_about_items(self, settings: SettingsDocument) -> list:
        """构建关于设置项"""
        about = settings.about
        return [
            Static("ℹ️ 关于", classes="about-title"),
            Static(f"  版本: {about.version}", classes="about-content"),
            Static(f"  许可证: {about.license}", classes="about-content"),
        ]
    
    # ========================================================================
    # 操作方法
    # ========================================================================
    
    def action_close(self) -> None:
        """关闭设置界面"""
        self._logger.debug("Settings screen closed")
        self.post_message(SettingsClosed())
        self.dismiss()
    
    def action_save(self) -> None:
        """保存设置"""
        if self._settings_manager:
            if self._settings_manager.save():
                self._logger.info("Settings saved")
                self.notify("✓ 设置已保存", timeout=2.0)
            else:
                self._logger.error("Failed to save settings")
                self.notify("✗ 保存失败", timeout=2.0)
        self.post_message(SettingsSaved(self))
        self.dismiss()
    
    def action_next_category(self) -> None:
        """切换到下一个分类"""
        next_cat = CategoryMeta.get_next_category(self._current_category)
        self._switch_category(next_cat)
    
    def action_prev_category(self) -> None:
        """切换到上一个分类"""
        prev_cat = CategoryMeta.get_prev_category(self._current_category)
        self._switch_category(prev_cat)
    
    def action_reset_category(self) -> None:
        """重置当前分类"""
        if self._settings_manager:
            self._settings_manager.reset_to_defaults(self._current_category)
            self._refresh_content()
            self.notify("✓ 已重置", timeout=2.0)
    
    def _switch_category(self, category: str) -> None:
        """切换到指定分类"""
        # 移除旧分类的高亮
        old_widget = self.query_one(f"#cat-{self._current_category}", Static)
        if old_widget:
            old_widget.remove_class("active")
        
        # 高亮新分类
        self._current_category = category
        new_widget = self.query_one(f"#cat-{category}", Static)
        if new_widget:
            new_widget.add_class("active")
        
        # 刷新内容区
        self._refresh_content()
        self._logger.debug(f"Switched to category: {category}")
    
    def _refresh_content(self) -> None:
        """刷新内容区"""
        content = self.query_one("#content", VerticalScroll)
        # 移除旧内容
        for widget in content.query("Static"):
            if widget.id not in ("content-header",):
                widget.remove()
        # 添加新内容
        for item in self._get_category_items(self._current_category):
            content.mount(item)
    
    def action_move_up(self) -> None:
        """上移"""
        pass
    
    def action_move_down(self) -> None:
        """下移"""
        pass
    
    def action_focus_sidebar(self) -> None:
        """聚焦侧边栏"""
        self._focus_area = "sidebar"
    
    def action_focus_content(self) -> None:
        """聚焦内容区"""
        self._focus_area = "content"
    
    def action_toggle_current(self) -> None:
        """切换当前选项"""
        pass
    
    def on_mount(self) -> None:
        """组件挂载"""
        self._logger.debug("Settings screen mounted")
    
    def on_key(self, event) -> None:
        """处理键盘事件"""
        # 分类切换快捷键
        if event.key == "tab":
            if event.shift:
                self.action_prev_category()
            else:
                self.action_next_category()
            event.prevent_default()
            event.stop()


# ============================================================================
# 模块导出
# ============================================================================

__all__ = [
    "SettingsScreen",
    "SettingsClosed",
    "SettingsSaved",
    "SETTINGS_SCREEN_CSS",
]
