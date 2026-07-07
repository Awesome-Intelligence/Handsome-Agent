#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Textual TUI Application Main Class

🚪 Access - 💬 CLI - Textual UI - 主应用类

基于 Textual 框架的现代化终端界面，提供丰富的交互体验。
"""

from __future__ import annotations

import logging
import os
import sys
from collections import deque
from pathlib import Path
from typing import TYPE_CHECKING, Optional

# 降级机制：如果 textual 不可用，提供友好提示
TEXTUAL_AVAILABLE = True
_TEXTUAL_IMPORT_ERROR: str | None = None

try:
    from textual.app import App, ComposeResult
    from textual.widgets import (
        Header,
        Footer,
        Static,
        RichLog,
        Tabs,
        Tab,
        TextArea,
        Button,
    )
    from textual.widgets import Markdown, LoadingIndicator, Select, Input
    from textual.binding import Binding
    from textual.containers import Container, Vertical, VerticalScroll, Horizontal
    from textual.screen import Screen as TextualScreen
    from textual.message import Message
    from textual import on
    from textual.events import Key, Click
    from textual import events as textual_events
    from textual.theme import Theme

    # NewLine 在 Textual 0.x 中已被移除，使用 Rich.Text 替代
    try:
        from textual.widgets._text_area import NewLine
    except ImportError:
        # Textual 1.x 不再有 NewLine，创建一个简单的替代类
        class NewLine:
            def __init__(self, count: int = 1):
                self.count = count

    KeyEvent = Key
except ImportError as e:
    TEXTUAL_AVAILABLE = False
    _TEXTUAL_IMPORT_ERROR = str(e)

# TextualScreen 后备定义（当 Textual 不可用时）
if not TEXTUAL_AVAILABLE:

    class TextualScreen:
        """Textual Screen 的后备类."""

        pass


# Rich 库导入
try:
    from rich.text import Text as RichText
    from rich.style import Style
except ImportError:
    RichText = None
    Style = None

if TYPE_CHECKING:
    from textual.widget import Widget

# 本地导入 - 从子模块导入
from .css import APP_CSS
from .helpers import CompatibleLog, LogDescriptor, _COMPATIBLE_LOG
from .log_handler import TuiLogHandler
from .notifications import NotificationType
from .text_area import SubmitTextArea
from tui.widgets.slash_completion import SlashCompletionList

# 跨模块导入 - Textual 组件 (使用绝对导入，因为这些模块仍在 cli/tui/ 下)
try:
    from tui.theming import ThemeManager, get_theme_manager
except ImportError:
    ThemeManager = None
    get_theme_manager = None

# Token 估算（Hermes 风格，不影响性能）
try:
    from agent.context.token_estimator import estimate_messages_tokens_rough
except ImportError:
    estimate_messages_tokens_rough = None

try:
    from tui.views.chat_view import ChatView
except ImportError:
    ChatView = None

try:
    from tui.views.session_picker import SessionPickerScreen
except ImportError:
    SessionPickerScreen = None

try:
    from tui.sidebar import SidebarContainer
except ImportError:
    SidebarContainer = None

try:
    from tui.consumers import TUIConsumer
except ImportError:
    TUIConsumer = None

try:
    from tui.widgets.approval_dialog import (
        ApprovalDialog,
        ApprovalMode,
        RiskLevel,
        ApprovalManager,
        ApprovalConfirmed,
        ApprovalRejected,
        create_approval_dialog,
    )
except ImportError:
    ApprovalDialog = None
    ApprovalMode = None
    RiskLevel = None
    ApprovalManager = None
    ApprovalConfirmed = None
    ApprovalRejected = None
    create_approval_dialog = None

try:
    from tui.services.session_store import SessionStore
except ImportError:
    SessionStore = None

try:
    from tui.views.help_view import HelpScreen
except ImportError:
    HelpScreen = None

try:
    from tui.views.file_preview import FilePreviewScreen
except ImportError:
    FilePreviewScreen = None

try:
    from tui.views.settings_screen import SettingsScreen
except ImportError:
    SettingsScreen = None

try:
    from tui.views.log_screen import LogScreen
except ImportError:
    LogScreen = None

try:
    from tui.theming.css import get_stylesheets
except ImportError:
    get_stylesheets = None

# i18n 支持
try:
    from common.i18n import get_i18n, t
except ImportError:

    def get_i18n():
        class SimpleI18n:
            def t(self, key, default=None, **kwargs):
                return default or key

        return SimpleI18n()

    def t(key, default=None, **kwargs):
        return default or key


# 日志支持
try:
    from common.logging_manager import get_access_logger, LogManager
except ImportError:
    import logging

    logging.basicConfig(level=logging.INFO)

    def get_access_logger(*args, **kwargs):
        return logging.getLogger("HandsomeAgent")

    LogManager = None

# 颜色常量（用于横幅等 Rich 标记）- 高雅紫
PURPLE_PRIMARY = "#B180D7"
PURPLE_BRIGHT = "#C9A0E0"
PURPLE_DIM = "#9A6BC2"
PURPLE_DARK = "#7A4DA8"
WHITE = "white"
GRAY_DIM = "#888888"
GOLD = "#FFD700"

STATUS_ONLINE = "#3fb950"
STATUS_BUSY = "#f0883e"
STATUS_ERROR = "#f85149"


def _patch_textual_logger():
    """Patch Textual's LayerLogger to be compatible."""
    try:
        from textual._log import LayerLogger

        LayerLogger.system = lambda *args, **kwargs: None
        LayerLogger.info = lambda *args, **kwargs: None
        LayerLogger.debug = lambda *args, **kwargs: None
        LayerLogger.warning = lambda *args, **kwargs: None
        LayerLogger.error = lambda *args, **kwargs: None
        LayerLogger.critical = lambda *args, **kwargs: None
    except ImportError:
        pass


_patch_textual_logger()


# ============================================================================
# Textual 主题定义
# ============================================================================

if TEXTUAL_AVAILABLE:
    from tui.theming.preset_themes import _PRESET_THEMES

    THEMES = [
        Theme(
            name=t.theme_id,
            primary=t.primary,
            secondary=t.secondary,
            accent=t.accent,
            foreground=t.foreground,
            background=t.background,
            surface=t.surface,
            panel=t.panel,
            success=t.success,
            warning=t.warning,
            error=t.error,
            dark=True,
        )
        for t in _PRESET_THEMES.values()
    ]


class HandsomeAgentApp(App):
    """Handsome Agent Textual TUI Application."""

    log = LogDescriptor()

    BINDINGS = [
        # --- 核心快捷键 ---
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+b", "toggle_sidebar", "Sidebar"),
        Binding("f1", "open_help", "Help"),
        Binding("f2", "open_settings", "Settings"),
        Binding("f3", "open_log_screen", "Logs"),
        # --- 标签管理快捷键 ---
        Binding("ctrl+t", "new_tab", "New Tab", show=False),
        Binding("ctrl+w", "close_tab", "Close Tab", show=False),
        Binding("ctrl+tab", "next_tab", "Next Tab", show=False),
        Binding("ctrl+shift+tab", "prev_tab", "Prev Tab", show=False),
        # --- 面板切换快捷键 (ctrl+方向键) ---
        Binding("ctrl+left", "prev_panel", "Prev Panel", show=False),
        Binding("ctrl+right", "next_panel", "Next Panel", show=False),
    ]

    # Textual 主题系统 - 定义为类属性
    if TEXTUAL_AVAILABLE:
        themes: list[Theme] = THEMES

    # 从 css.py 导入 CSS
    CSS = APP_CSS

    def __init__(
        self,
        model_name: str = "Handsome Agent",
        provider: str | None = None,
        cwd: str | None = None,
        session_id: str | None = None,
        context_length: int | None = None,
        approval_mode: str | ApprovalMode = "suggest",
        initial_theme: str | None = None,
        agent=None,
        **kwargs,
    ):
        _patch_textual_logger()

        self._tui_log_handler: TuiLogHandler | None = None
        self._saved_console_handler: logging.Handler | None = None
        if LogManager is not None:
            try:
                lm = LogManager.get_instance()
                if lm._console_handler is not None:
                    self._tui_log_handler = TuiLogHandler(self)
                    if hasattr(lm._console_handler, "formatter"):
                        self._tui_log_handler.setFormatter(
                            lm._console_handler.formatter
                        )
                    self._tui_log_handler.setLevel(lm._console_handler.level)
                    if lm._console_handler in logging.root.handlers:
                        logging.root.removeHandler(lm._console_handler)
                        self._saved_console_handler = lm._console_handler
                    logging.root.addHandler(self._tui_log_handler)
                    for logger_name in logging.Logger.manager.loggerDict:
                        logger = logging.getLogger(logger_name)
                        if lm._console_handler in logger.handlers:
                            logger.removeHandler(lm._console_handler)
                            logger.addHandler(self._tui_log_handler)
            except Exception:
                pass

        super().__init__(**kwargs)
        self._logger = _COMPATIBLE_LOG

        self.model_name = model_name
        self.provider = provider
        self.cwd = cwd or os.getcwd()
        self.session_id = session_id
        # 如果没有传入 context_length，从配置读取
        if context_length is None:
            try:
                from common.config import get_model_config

                context_length = get_model_config().context_window
            except Exception:
                context_length = None
        self.context_length = context_length
        self._logger = get_access_logger("TextualUI", sublayer="tui")

        self._is_loading: bool = False
        self._loading_timer: Optional[callable] = None
        # 使用 Textual 原生 LoadingIndicator（覆盖模式）
        self._use_native_loading: bool = False
        self._loading_indicator: Optional[LoadingIndicator] = None
        # 状态图标配置
        self._STATUS_ICONS = {
            "online": "😄",  # 在线
            "busy": ["🤔", "🤨", "😲", "🤯"],  # 思考中/忙碌（循环动画）
            "warning": "😕",  # 警告
            "error": "😐",  # 错误/离线
        }
        self._current_status: str = "online"
        self._busy_frame_index: int = 0  # busy 状态动画帧索引

        self._is_streaming: bool = False
        self._streaming_text: str = ""
        self._streaming_widget_id: str | None = None
        self._streaming_timer: Optional[callable] = None
        self._streaming_chars_per_tick: int = 10  # 优化：从 3 改为 10，减少更新频率
        self._streaming_delay_ms: int = 50  # 优化：从 30 改为 50ms
        self._streaming_scroll_threshold: int = 15  # 每累积 15 个字符才滚动一次

        self._agent = agent
        self._theme_manager: ThemeManager | None = None
        if get_theme_manager:
            self._theme_manager = get_theme_manager()
            if initial_theme:
                self._theme_manager.set_theme(initial_theme)
            # 注册主题变更回调（必须在 set_theme 之后，这样初始主题切换也会触发回调）
            self._theme_manager.register_theme_change_callback(self._on_theme_changed)
            # 同步 theme_id 到 _theme_manager 的当前主题
            self.theme_id = self._theme_manager.get_current_theme_id()
        else:
            self.theme_id: str = "default"
        self._theme_css_loaded: bool = False
        self._theme_css_paths: list[str] = []  # 已加载的主题 CSS 文件路径
        self._session_store: Optional[SessionStore] = None
        self._pending_message_count: int = 0
        self._auto_save_interval: int = 5
        self._tab_counter = 0
        self._tab_states: dict[str, dict] = {}
        self._active_tab_id: str | None = None
        self._approval_manager: Optional[ApprovalManager] = None
        self._pending_tool_call: dict | None = None
        self._approval_callback: Optional[callable] = None
        self._input_history: list[str] = []
        self._history_index: int = -1
        self._current_input: str = ""
        self._init_session_store()
        self._init_approval_manager(approval_mode)
        self._agent_status = "online"
        # 使用 Textual 原生 Markdown 组件，无需初始化
        self._markdown_enabled = True
        # Token 计数（方案B：消息完成后估算）
        self._current_token_count: int = 0
        # 跟踪本次会话使用的工具
        self._used_tools: set = set()
        # TUIConsumer（日志消费者）
        self._tui_consumer: Optional["TUIConsumer"] = None
        # 消息队列（防止并发 agent 调用）
        self._pending_queue: "deque[str]" = deque()
        self._agent_busy: bool = False
        # 模型列表（动态从配置读取）
        self._builtin_models: list[tuple[str, str]] = self._get_configured_models()

        # Welcome Banner 缓存
        self._banner_cache: dict = {
            "project_path": None,
            "skills_path": None,
            "tools_path": None,
            "skills_count": None,
            "tools_count": None,
            "version": None,
        }
        self._banner_cache_initialized: bool = False

        # ========== Widget 缓存（优化性能）==========
        self._widget_cache: dict = {}  # 缓存常用 widget 引用

    def compose(self) -> ComposeResult:
        with Container(id="app-header"):
            with Horizontal():
                # 左侧：ASCII Banner
                yield Static("", id="welcome-banner")
                # 右侧：版本、skills、工具信息
                with Vertical(id="header-info-right"):
                    yield Static("", id="version-info")
                    yield Static("", id="skills-info")
                    yield Static("", id="tools-info")
                # 最右下角：主题切换按钮
                yield Static("►", id="theme-toggle", classes="theme-toggle")

        with Horizontal(id="main-area"):
            yield ChatView(id="chat-area")
            if SidebarContainer:
                with Container(id="sidebar-container"):
                    # 获取 Agent 的 GoalManager（如果存在）
                    goal_manager = (
                        getattr(self._agent, "_goal_manager", None)
                        if self._agent
                        else None
                    )
                    yield SidebarContainer(
                        cwd=self.cwd, agent=self._agent, goal_manager=goal_manager
                    )

        with Container(id="input-area"):
            with Container(id="status-bar"):
                with Horizontal(id="status-content"):
                    yield Static("●", id="status-icon", classes="status-icon")
                    yield Select(
                        id="status-model",
                        classes="status-model",
                        options=self._builtin_models,
                        allow_blank=False,
                        compact=True,
                    )
                    yield Static("0/128K", id="status-tokens", classes="status-tokens")
                    yield Static("0:00", id="status-time", classes="status-time")
                    yield Static("🔧", id="status-tools", classes="status-tools")
                    yield Static("", id="status-queue", classes="status-queue")
                    with Horizontal(id="status-right"):
                        yield Static(
                            t("tui.status_bar.mode_iter"),
                            id="status-mode-toggle",
                            classes="status-mode-toggle",
                        )
            yield SubmitTextArea(
                id="user-input",
                classes="input-field",
                placeholder=t("tui.input.placeholder", "输入消息...Enter 发送"),
            )
            yield Footer()
            yield SlashCompletionList(id="slash-completion")

    def on_mount(self) -> None:
        self._logger.info("Textual UI mounted")

        # 注册自定义主题（Textual 8.x 需要手动注册）
        if TEXTUAL_AVAILABLE:
            for theme in THEMES:
                self.register_theme(theme)
            self._logger.info(
                f"Registered {len(THEMES)} themes: {[t.name for t in THEMES]}"
            )

            # 从保存的偏好恢复主题
            saved_theme = self._theme_manager.get_current_theme_id()
            self.theme = saved_theme
            self._logger.info(f"Restored theme: {self.theme}")

        # 缓存常用 Widget 引用（优化性能）
        self._cache_widgets()

        self._render_welcome_banner()
        self._update_status_bar()
        self._update_theme_toggle_tooltip()
        # 异步生成哲学语录（不阻塞 UI）
        self.call_later(self._generate_wisdom_async)
        self._register_event_listeners()
        self.call_later(self._load_stylesheets)
        # 延迟初始化模型选择下拉菜单，确保 Select widget 已完全 mount
        self.call_later(self._init_model_select)

        if self._theme_manager and self._theme_manager.is_transparency_enabled():
            self._logger.info("Applying saved transparency settings")
            self._update_transparency_styles(True)

        # 初始化 TUIConsumer 并注册到 Agent 的事件系统（仅用于日志）
        if TUIConsumer and self._agent is not None:
            try:
                self._tui_consumer = TUIConsumer()

                # 尝试获取 Agent 的 registry 并注册消费者
                if (
                    hasattr(self._agent, "_stream_emitter")
                    and self._agent._stream_emitter is not None
                ):
                    emitter = self._agent._stream_emitter
                    if hasattr(emitter, "registry"):
                        emitter.registry.register(self._tui_consumer)
                        self._logger.info("TUIConsumer registered to agent registry")
            except Exception as e:
                self._logger.warning(f"Failed to initialize TUIConsumer: {e}")

        # 加载持久化的输入历史（跨会话）
        try:
            from tui.services.session_store import SessionStore

            session_store = SessionStore()
            persisted_history = session_store.load_input_history(limit=100)
            if persisted_history:
                self._input_history = persisted_history
                self._logger.info(
                    f"Loaded {len(persisted_history)} persisted input history items"
                )
        except Exception as e:
            self._logger.warning(f"Failed to load persisted input history: {e}")

        # 绑定输入框历史导航回调（上下键切换历史消息）
        if SubmitTextArea is not None:
            try:
                text_area = self.query_one("#user-input", SubmitTextArea)
                text_area.history_navigate = self._navigate_input_history
            except Exception as e:
                self._logger.warning(f"Failed to wire up history navigation: {e}")

        # 绑定斜杠命令补全回调
        self._bind_slash_completion()

        self.set_focus(self.query_one("#user-input", TextArea))

        # 初始化 token 计数（加载历史会话的 token）
        self.call_later(self._update_token_count)

    async def _load_stylesheets(self) -> None:
        if get_stylesheets is None:
            self._logger.debug("CSS module not available, using inline CSS")
            return

        try:
            # 加载基础 CSS
            stylesheets = get_stylesheets()
            for css_file in stylesheets:
                css_path = Path(css_file)
                if css_path.exists():
                    await self.add_stylesheet(str(css_path))
                    self._logger.debug(f"Loaded stylesheet: {css_path.name}")
                else:
                    self._logger.debug(f"Stylesheet not found: {css_path}")

            self._theme_css_loaded = True

            # 预加载所有主题的 CSS（避免切换时闪烁）
            if self._theme_manager:
                for tid in self._theme_manager.list_theme_ids():
                    css_path = self._theme_manager.get_theme_css_path(tid)
                    if css_path and css_path.exists():
                        await self.add_stylesheet(str(css_path))
                        self._logger.debug(f"Preloaded theme CSS: {css_path.name}")

            # 应用初始主题 class
            self._apply_theme_class()
        except Exception as e:
            self._logger.debug(f"Failed to load stylesheets: {e}")

    def _apply_theme_class(self) -> None:
        self._logger.debug(
            f"[_apply_theme_class] Called, _theme_css_loaded={self._theme_css_loaded}, theme_id={self.theme_id}"
        )

        if not self._theme_css_loaded:
            self.set_timer(0.5, self._apply_theme_class)
            return

        try:
            # 获取 Screen 组件
            screen = self.screen
            if not screen:
                self._logger.warning("[_apply_theme_class] No screen found")
                return

            # 获取所有主题 ID 并移除旧主题 class
            if self._theme_manager:
                theme_ids = self._theme_manager.list_theme_ids()
                for tid in theme_ids:
                    screen.remove_class(f"theme-{tid}")

            # 添加新主题 class 到 Screen
            screen.add_class(f"theme-{self.theme_id}")
            self._logger.info(f"Applied theme class: theme-{self.theme_id}")
        except Exception as e:
            self._logger.error(f"[_apply_theme_class] Error: {e}")

    async def _load_theme_css(self, theme_id: str) -> None:
        """加载主题 CSS 文件（异步）."""
        if not self._theme_manager:
            return

        try:
            # 卸载之前的主题 CSS
            for css_path in self._theme_css_paths:
                try:
                    await self.remove_stylesheet(css_path)
                except Exception:
                    pass
            self._theme_css_paths.clear()

            # 加载新的主题 CSS
            theme_css_path = self._theme_manager.get_theme_css_path(theme_id)
            if theme_css_path and theme_css_path.exists():
                await self.add_stylesheet(str(theme_css_path))
                self._theme_css_paths.append(str(theme_css_path))
                self._logger.debug(f"Loaded theme CSS: {theme_css_path.name}")
        except Exception as e:
            self._logger.debug(f"Failed to load theme CSS: {e}")

    def _load_theme_css_sync(self, theme_id: str) -> None:
        """切换主题 CSS（CSS 已预加载，只需记录当前主题）."""
        # CSS 在初始化时已全部预加载，这里只需记录即可
        self._logger.info(
            f"[SYNC] Theme CSS already preloaded, switching to: {theme_id}"
        )

    def _on_theme_changed(self, theme_id: str) -> None:
        """主题变更回调（CSS 已预加载，只需更新 class）."""
        # CSS 在初始化时已全部预加载，这里只需更新 class
        self.theme_id = theme_id
        self.theme = theme_id  # 切换 Textual 原生主题（驱动 $primary 等核心变量）
        self._apply_theme_class()
        self._update_theme_toggle_tooltip()

        # 清除 banner 颜色缓存并重新渲染（切换 Banner 颜色）
        cache_key = f"_banner_color_{theme_id}"
        if hasattr(self, cache_key):
            delattr(self, cache_key)
        self._render_welcome_banner()

    def update_theme_css(self) -> None:
        self._apply_theme_class()

    def _update_status_bar(self) -> None:
        try:
            # 使用缓存的 widgets（避免频繁 query_one）
            icon_widget = self._widget_cache.get("status_icon")
            if icon_widget:
                icon_widget.update(self._STATUS_ICONS.get(self._current_status, "😐"))

            tokens_widget = self._widget_cache.get("status_tokens")
            if tokens_widget:
                if self.context_length:
                    tokens_widget.update(
                        f"│ {self._format_context(self._current_token_count)}"
                        f"/{self._format_context(self.context_length)} "
                    )
                else:
                    tokens_widget.update("│ n/a ")

            time_widget = self._widget_cache.get("status_time")
            if time_widget:
                time_widget.update("│ 0m 0s ")

            tools_widget = self._widget_cache.get("status_tools")
            if tools_widget:
                tools_widget.update("🔧")
        except Exception as e:
            self._logger.debug(f"Failed to update status bar: {e}")

    def _update_used_tools(self) -> None:
        """更新已使用工具的显示."""
        try:
            tools_widget = self._widget_cache.get("status_tools")
            if tools_widget:
                count = len(self._used_tools)
                if count > 0:
                    # 显示工具名称（限制总长度）
                    tools_str = ",".join(sorted(self._used_tools))
                    if len(tools_str) > 15:
                        # 如果太长，缩写
                        sorted_tools = sorted(self._used_tools)
                        tools_str = ",".join(sorted_tools[:3])
                        if count > 3:
                            tools_str += f",+{count-3}"
                    tools_widget.update(f"🔧{tools_str}")
                else:
                    tools_widget.update("🔧")
        except Exception as e:
            self._logger.debug(f"Failed to update tools display: {e}")

    def _update_queue_display(self, queue_len_override: int | None = None) -> None:
        """更新队列状态显示（状态栏 + 输入框内容）。

        Args:
            queue_len_override: 可选，强制使用指定队列长度（用于 pop 后准确反映剩余数量）
        """
        queue_len = (
            queue_len_override
            if queue_len_override is not None
            else len(self._pending_queue)
        )
        try:
            queue_widget = self._widget_cache.get("status_queue")
            text_area = self._widget_cache.get("user_input")
            if queue_len > 0:
                # 状态栏显示排队数量
                if queue_widget:
                    queue_widget.update(f"⏳ {queue_len}")
                    queue_widget.set_class(True, "has-queue")
                # 输入框直接显示队首排队消息，禁用编辑
                if text_area:
                    text_area.text = self._pending_queue[0]
                    text_area.disabled = True
            else:
                # 队列空：恢复空闲状态
                if queue_widget:
                    queue_widget.update("")
                    queue_widget.set_class(False, "has-queue")
                if text_area:
                    text_area.text = ""
                    text_area.disabled = False
                    text_area.placeholder = t(
                        "tui.input.placeholder", "输入消息...Enter 发送"
                    )
        except Exception as e:
            self._logger.debug(f"Failed to update queue display: {e}")

    def _toggle_budget_mode(self) -> None:
        """切换 Goal 模式和迭代模式."""
        try:
            if (
                hasattr(self, "_agent")
                and self._agent
                and hasattr(self._agent, "state")
            ):
                state = self._agent.state
                from agent.state import BudgetMode

                if state.budget_mode == BudgetMode.TURN:
                    state._enable_iteration_mode()
                    mode_icon = t("tui.status_bar.mode_iter")
                    mode_text = t("tui.status_bar.mode_iter").replace("⚡ ", "")
                else:
                    state._enable_goal_mode()
                    mode_icon = t("tui.status_bar.mode_goal", "🎯 Goal")
                    mode_text = "Goal"

                # 更新按钮显示
                toggle_widget = self._widget_cache.get("status_mode_toggle")
                if toggle_widget:
                    toggle_widget.update(mode_icon)

                self._logger.info(f"Budget mode switched to: {mode_text}")
        except Exception as e:
            self._logger.debug(f"Failed to toggle budget mode: {e}")

    @on(Click, "#status-mode-toggle")
    def _on_click_mode_toggle(self, event: Click) -> None:
        """处理模式切换按钮点击事件."""
        self._logger.info("Mode toggle clicked!")
        self._toggle_budget_mode()

    @on(Click, "#theme-toggle")
    def _on_theme_toggle_click(self, event: Click | None = None) -> None:
        """处理主题切换按钮点击事件."""
        self._logger.info("Theme toggle clicked!")
        if not self._theme_manager:
            self._logger.warning("Theme manager not available")
            return

        current_theme = self._theme_manager.get_current_theme_id()
        available_themes = self._theme_manager.list_theme_ids()
        if len(available_themes) < 2:
            self._logger.warning("Not enough themes available to toggle")
            return

        current_index = available_themes.index(current_theme)
        next_index = (current_index + 1) % len(available_themes)
        next_theme = available_themes[next_index]

        self.set_theme(next_theme)

    def action_toggle_theme(self) -> None:
        """切换主题（快捷键 Ctrl+Shift+T）."""
        self._on_theme_toggle_click(None)

    def _update_theme_toggle_tooltip(self) -> None:
        """更新主题切换按钮的 tooltip，显示当前主题名称."""
        if not self._theme_manager:
            return

        theme_toggle = self._widget_cache.get("theme_toggle")
        if not theme_toggle:
            try:
                theme_toggle = self.query_one("#theme-toggle", Static)
                self._widget_cache["theme_toggle"] = theme_toggle
            except Exception:
                return

        theme_name = t("tui.command.toggle_theme")
        theme_toggle.tooltip = theme_name

    def _update_token_count(self) -> None:
        """更新 token 计数（方案B：消息完成后估算，不影响性能）."""
        if not estimate_messages_tokens_rough:
            self._logger.info(
                "[token_count] estimate_messages_tokens_rough not available"
            )
            return

        if not self._session_store:
            self._logger.info("[token_count] _session_store not available")
            return

        if not self.session_id:
            self._logger.info("[token_count] session_id not available")
            return

        try:
            messages = self._session_store.get_messages(self.session_id, limit=1000)
            self._logger.info(f"[token_count] got {len(messages)} messages")

            # 使用 Hermes 风格的 rough 估算
            message_dicts = [
                {"role": msg.role, "content": msg.content or ""} for msg in messages
            ]
            self._current_token_count = estimate_messages_tokens_rough(message_dicts)
            self._logger.info(f"[token_count] estimated: {self._current_token_count}")

            tokens_widget = self._widget_cache.get("status_tokens")
            if tokens_widget and self.context_length:
                tokens_widget.update(
                    f"│ {self._format_context(self._current_token_count)}"
                    f"/{self._format_context(self.context_length)} "
                )
        except Exception as e:
            self._logger.info(f"[token_count] Failed: {e}")

    def _get_configured_models(self) -> list[tuple[str, str]]:
        """从用户配置中获取已配置的模型列表."""
        models: list[tuple[str, str]] = []

        # 1. 从 cli.config 读取
        try:
            from cli.config.config import load_config

            config = load_config()
            llm = config.get("llm", {})
            provider = llm.get("provider", "")
            model = llm.get("model", "")
            if provider and provider != "none" and model:
                models.append((f"{provider}/{model}", f"{provider}/{model}"))
        except (ImportError, Exception):
            pass

        # 2. 从 common.config.llm_providers 读取
        if not models:
            try:
                from common.config import get_settings

                providers = get_settings().llm_providers
                for p_name, p_cfg in providers.items():
                    if isinstance(p_cfg, dict) and p_cfg.get("enabled"):
                        model = p_cfg.get("model")
                        if model:
                            models.append((f"{p_name}/{model}", f"{p_name}/{model}"))
            except Exception:
                pass

        # 3. 如果还是没有配置，使用"未配置"提示
        if not models:
            models.append(("not_configured", "⚠️ 未配置，请先在设置中配置模型"))

        models.append(("custom", "其他..."))
        return models

    def _init_model_select(self) -> None:
        """初始化模型选择下拉菜单."""
        try:
            select_widget = self.query_one("#status-model", Select)

            if not self._builtin_models:
                self._logger.warning("No models configured, cannot init select")
                return

            # 找到第一个非 not_configured 的模型（使用 label，因为 allow_blank=False 时 label 就是 value）
            current_label = None
            for value, label in self._builtin_models:
                if value != "not_configured":
                    current_label = (
                        label  # 使用 label，因为 allow_blank=False 时 label 即 value
                    )
                    break

            # 如果没有配置任何有效模型，使用 not_configured
            if not current_label:
                current_label = self._builtin_models[0][1]  # 第一个的 label

            select_widget.value = current_label
            self._logger.debug(f"Model select initialized with: {current_label}")
        except Exception as e:
            self._logger.error(f"Failed to init model select: {e}", exc_info=True)

    @on(Select.Changed)
    def _on_model_selected(self, event: Select.Changed) -> None:
        """处理模型选择变化（仅预览，不真实切换）."""
        if event.control.id == "status-model":
            selected = event.value
            if selected == "custom":
                self._show_custom_model_input()
            elif selected == "not_configured":
                self.notify("⚠️ 请先在设置中配置 LLM 模型")
            elif selected:
                self._logger.info(f"Model preview: {selected}")
                self.notify(f"预览模型: {selected}")

    def _show_custom_model_input(self) -> None:
        """显示自定义模型输入对话框."""
        self.push_screen(
            CustomModelInputScreen(on_submit=self._handle_custom_model_input),
        )

    def _handle_custom_model_input(self, value: str) -> None:
        """处理自定义模型输入（仅预览，不真实切换）."""
        if value and value.strip():
            # 仅显示预览，不真实切换模型
            try:
                select_widget = self.query_one("#status-model", Select)
                custom_model = value.strip()
                # 检查自定义模型是否已在列表中，不在则添加
                model_values = [opt[0] for opt in self._builtin_models]
                if custom_model not in model_values:
                    # 在 "其他..." 选项前插入自定义模型
                    custom_index = (
                        model_values.index("custom")
                        if "custom" in model_values
                        else len(self._builtin_models)
                    )
                    self._builtin_models.insert(
                        custom_index, (custom_model, custom_model)
                    )
                    select_widget.set_options(self._builtin_models)
                select_widget.value = custom_model
            except Exception:
                pass
            self._logger.info(f"Custom model preview: {value.strip()}")
            self.notify(f"预览自定义模型: {value.strip()}")

    @on(SubmitTextArea.InputSubmitted)
    def _on_input_submitted(self, event: SubmitTextArea.InputSubmitted) -> None:
        # 关闭斜杠补全浮层
        self._dismiss_slash_palette()
        # 使用缓存的 widget（优化性能）
        text_area = self._widget_cache.get("user_input")
        if text_area is None:
            text_area = self.query_one("#user-input", SubmitTextArea)
        user_input = text_area.text.strip()

        if not user_input:
            return

        # Agent 正忙时：消息入队、禁用输入框、直接返回
        if self._agent_busy:
            self._pending_queue.append(user_input)
            queue_len = len(self._pending_queue)
            text_area.disabled = True
            self._update_queue_display()
            self.notify_animated(
                t(
                    "tui.queue.message_queued",
                    "消息已加入队列 (排队中: {n}条)",
                    n=queue_len,
                ),
                NotificationType.INFO,
            )
            return

        if not user_input:
            return

        if user_input not in self._input_history:
            self._input_history.insert(0, user_input)
            if len(self._input_history) > 100:
                self._input_history = self._input_history[:100]

            try:
                from tui.services.session_store import SessionStore

                session_store = SessionStore()
                session_store.save_input_history(user_input)
            except Exception as e:
                self._logger.warning(f"Failed to save input history: {e}")

        self._history_index = -1
        self._current_input = ""
        text_area.text = ""
        self._append_message("user", user_input)
        self._logger.debug(f"User input: {user_input[:50]}...")
        # 同步加锁，确保后续消息立即进入队列
        self._agent_busy = True
        self.call_later(lambda: self._call_agent_async(user_input))

    def _dismiss_slash_palette(self) -> None:
        """关闭斜杠补全浮层。"""
        try:
            completion = self.query_one("#slash-completion", SlashCompletionList)
            text_area = self.query_one("#user-input", SubmitTextArea)
            completion.set_class(False, "visible")
            completion.clear()
            text_area._slash_snapshot = None
        except Exception:
            pass

    def _bind_slash_completion(self) -> None:
        """绑定斜杠命令补全浮层的回调。"""
        try:
            text_area = self.query_one("#user-input", SubmitTextArea)
            completion = self.query_one("#slash-completion", SlashCompletionList)
        except Exception as e:
            self._logger.warning(f"Failed to bind slash completion: {e}")
            return

        def show_palette():
            completion.dismiss()  # 先清空再显示
            completion.set_class(True, "visible")

        def update_filter(query: str):
            completion.filter_commands(query)

        def confirm_and_insert() -> str | None:
            cmd = completion.insert_selected()
            if cmd:
                snapshot = text_area._slash_snapshot
                if snapshot:
                    snapshot_text, _ = snapshot
                    # 用快照长度定位 / 位置，截断 / 之后的内容并替换为完整命令
                    slash_text_len = len(snapshot_text)
                    text_area.text = text_area.text[:slash_text_len] + cmd
                    text_area.cursor_location = slash_text_len + len(cmd)
                completion.dismiss()
                text_area._slash_snapshot = None
            return cmd

        def dismiss_palette():
            completion.dismiss()
            text_area._slash_snapshot = None

        text_area.slash_show = show_palette
        text_area.slash_update = update_filter
        text_area.slash_complete = confirm_and_insert
        text_area.slash_dismiss = dismiss_palette

        completion.on_dismiss = dismiss_palette

    def _register_event_listeners(self) -> None:
        pass

    @on(Click, "#input-area")
    def _on_input_area_click(self, event: Click) -> None:
        """点击输入区域时，若点击的不是补全列表则关闭浮层。"""
        try:
            completion = self.query_one("#slash-completion", SlashCompletionList)
            if not completion.has_class("visible"):
                return
            # query_one 会抛出如果点击目标在 completion 内
            self.query_one("#slash-completion", SlashCompletionList)
        except Exception:
            # 点击不在 completion 内，关闭浮层
            self._dismiss_slash_palette()

    def _start_loading_animation(self) -> None:
        if self._is_loading:
            return
        self._is_loading = True

        # 更新状态为忙碌
        self._current_status = "busy"
        self._busy_frame_index = 0

        # 开启呼吸效果
        status_bar = self.query_one("#status-bar")
        status_bar.set_class(True, "breathing")

        if self._use_native_loading and LoadingIndicator is not None:
            # 使用 Textual 原生 LoadingIndicator
            try:
                if self._loading_indicator is None:
                    # 动态创建 LoadingIndicator 并覆盖到输入区域
                    status_bar = self.query_one("#status-bar")
                    self._loading_indicator = LoadingIndicator()
                    status_bar.mount(self._loading_indicator)
            except Exception:
                pass
        else:
            # 使用状态图标动画
            self._update_status_icon()
            self._update_busy_animation()

    def _update_busy_animation(self) -> None:
        """更新 busy 状态的动画图标"""
        if not self._is_loading or self._current_status != "busy":
            return
        self._busy_frame_index = (self._busy_frame_index + 1) % 4
        self._update_status_icon()
        self.set_timer(0.5, self._update_busy_animation)

    def _stop_loading_animation(self) -> None:
        self._is_loading = False

        # 更新状态为在线
        self._current_status = "online"
        self._busy_frame_index = 0

        # 停止呼吸效果
        status_bar = self.query_one("#status-bar")
        status_bar.set_class(False, "breathing")

        if self._use_native_loading and self._loading_indicator is not None:
            # 移除 Textual 原生 LoadingIndicator
            try:
                self._loading_indicator.remove()
                self._loading_indicator = None
            except Exception:
                pass
        else:
            # 更新状态图标
            self._update_status_icon()

    def _toggle_sidebar(self) -> None:
        sidebar = self.query_one("#sidebar-container", Container)

        if sidebar.styles.display == "none":
            sidebar.styles.display = "block"
            self.notify("侧边栏已显示")
        else:
            sidebar.styles.display = "none"
            self.notify("侧边栏已隐藏")

    def _update_status_icon(self) -> None:
        """更新状态图标"""
        icon_widget = self._widget_cache.get("status_icon")
        if icon_widget:
            status_icon = self._STATUS_ICONS.get(self._current_status, "😐")
            # busy 状态使用动画帧
            if self._current_status == "busy" and isinstance(status_icon, list):
                icon = status_icon[self._busy_frame_index % len(status_icon)]
            else:
                icon = status_icon
            icon_widget.update(icon)

    def set_agent_status(self, status: str) -> None:
        """设置 Agent 状态"""
        if status in self._STATUS_ICONS:
            self._current_status = status
        self._logger.debug(f"Agent status changed to: {status}")

    def start_streaming_message(self, widget_id: str) -> None:
        self._is_streaming = True
        self._streaming_text = ""
        self._streaming_widget_id = widget_id

        log = self.query_one(f"#{widget_id}", RichLog)
        if log:
            from rich.text import Text as RichText

            header = RichText.from_markup("[bold #3fb950]**Assistant**[/]\n\n")
            log.write(header)

    def append_streaming_text(self, text: str) -> None:
        if not self._is_streaming:
            return
        self._streaming_text += text

    def start_typewriter_effect(self, full_text: str, widget_id: str) -> None:
        self._is_streaming = True
        self._streaming_text = full_text
        self._streaming_widget_id = widget_id
        self._streaming_displayed = 0
        self._streaming_current_content = ""

        self._remove_streaming_widget()

        from textual.widgets import Static

        streaming_widget = Static(
            id="streaming-output",
            classes="typewriter-output",
            markup=True,
        )

        # 使用缓存的 chat_area（优化性能）
        chat_area = self._widget_cache.get("chat_area")
        if chat_area:
            chat_area.mount(streaming_widget)

        # 初始化滚动计数器
        self._streaming_chars_since_scroll = 0

        self._streaming_timer = self.set_interval(
            self._streaming_delay_ms / 1000.0, self._update_typewriter_frame
        )

    def _remove_streaming_widget(self) -> None:
        try:
            widget = self.query_one("#streaming-output")
            widget.remove()
        except Exception:
            pass

    def _update_typewriter_frame(self) -> None:
        if not self._is_streaming:
            return

        try:
            streaming_widget = self.query_one("#streaming-output")
        except Exception:
            return

        current_displayed = getattr(self, "_streaming_displayed", 0)
        chars_to_add = self._streaming_chars_per_tick
        end_index = min(current_displayed + chars_to_add, len(self._streaming_text))
        new_chars = self._streaming_text[current_displayed:end_index]

        if new_chars:
            self._streaming_current_content += new_chars
            streaming_widget.update(self._streaming_current_content)
            self._streaming_displayed = end_index
            # 更新滚动计数器
            self._streaming_chars_since_scroll = getattr(
                self, "_streaming_chars_since_scroll", 0
            ) + len(new_chars)

        # 滚动节流：每累积一定字符数才滚动一次（优化性能）
        should_scroll = (
            self._streaming_chars_since_scroll >= self._streaming_scroll_threshold
        )
        if should_scroll:
            self._streaming_chars_since_scroll = 0
            try:
                chat_area = self._widget_cache.get("chat_area")
                if chat_area:
                    if hasattr(chat_area, "scroll_home"):
                        chat_area.scroll_home(animate=False)
                    elif hasattr(chat_area, "scroll_to"):
                        chat_area.scroll_to(0, animate=False)
            except Exception:
                pass

        if self._streaming_displayed >= len(self._streaming_text):
            self._finish_typewriter_effect()
        else:
            streaming_widget.update(self._streaming_current_content + "[blink]▋[/]")

    def _finish_typewriter_effect(self) -> None:
        if self._streaming_timer:
            self._streaming_timer.stop()
            self._streaming_timer = None

        full_content = getattr(self, "_streaming_current_content", "") or ""
        full_content = full_content.replace("[blink]▋[/]", "")

        if full_content and self._streaming_widget_id:
            try:
                log = self.query_one(f"#{self._streaming_widget_id}", RichLog)
                log.write(full_content)
                log.write("\n")
            except Exception:
                pass

        self._remove_streaming_widget()
        self._is_streaming = False
        self._streaming_displayed = 0

    def is_streaming(self) -> bool:
        return self._is_streaming

    def cancel_streaming(self) -> None:
        if self._streaming_timer:
            self._streaming_timer.stop()
            self._streaming_timer = None

        self._remove_streaming_widget()
        self._is_streaming = False
        self._streaming_text = ""
        self._streaming_widget_id = None
        self._streaming_displayed = 0
        self._streaming_current_content = ""

    def _init_banner_cache(self) -> None:
        """初始化 Banner 缓存（在后台线程中调用）"""
        if self._banner_cache_initialized:
            return

        try:
            # 缓存项目路径
            self._banner_cache["project_path"] = self._get_project_path()
            self._banner_cache["skills_path"] = self._get_skills_path()
            self._banner_cache["tools_path"] = self._get_tools_path()
            # 缓存数量
            self._banner_cache["skills_count"] = self._get_skills_count()
            self._banner_cache["tools_count"] = self._get_tools_count()
            # 缓存版本
            try:
                from cli import __version__ as app_version

                self._banner_cache["version"] = app_version
            except ImportError:
                self._banner_cache["version"] = "unknown"
            self._banner_cache_initialized = True
            self._logger.debug("Banner cache initialized")
        except Exception as e:
            self._logger.error(f"Failed to initialize banner cache: {e}")

    def _cache_widgets(self) -> None:
        """缓存常用 Widget 引用（优化性能，避免频繁 query_one）"""
        try:
            # 状态栏 widgets
            self._widget_cache["status_icon"] = self.query_one("#status-icon", Static)
            self._widget_cache["status_model"] = self.query_one("#status-model", Select)
            self._widget_cache["status_tokens"] = self.query_one(
                "#status-tokens", Static
            )
            self._widget_cache["status_time"] = self.query_one("#status-time", Static)
            self._widget_cache["status_tools"] = self.query_one("#status-tools", Static)
            self._widget_cache["status_queue"] = self.query_one("#status-queue", Static)
            self._widget_cache["status_mode_toggle"] = self.query_one(
                "#status-mode-toggle", Static
            )
            self._widget_cache["status_bar"] = self.query_one("#status-bar")

            # 聊天区域
            self._widget_cache["chat_area"] = self.query_one("#chat-area", ChatView)

            # 输入框
            self._widget_cache["user_input"] = self.query_one("#user-input", TextArea)

            # Banner widgets
            self._widget_cache["welcome_banner"] = self.query_one(
                "#welcome-banner", Static
            )
            self._widget_cache["version_info"] = self.query_one("#version-info", Static)
            self._widget_cache["skills_info"] = self.query_one("#skills-info", Static)
            self._widget_cache["tools_info"] = self.query_one("#tools-info", Static)
            self._widget_cache["theme_toggle"] = self.query_one("#theme-toggle", Static)

            # 侧边栏
            try:
                self._widget_cache["sidebar_container"] = self.query_one(
                    "#sidebar-container", Container
                )
            except Exception:
                pass

            self._logger.debug(f"Cached {len(self._widget_cache)} widgets")
        except Exception as e:
            self._logger.warning(f"Failed to cache widgets: {e}")

    def _get_cached_widget(self, key: str, widget_class=None):
        """获取缓存的 Widget 引用

        Args:
            key: Widget 缓存键
            widget_class: 可选的 widget 类型，用于回退到 query_one

        Returns:
            Widget 引用或 None
        """
        if key in self._widget_cache:
            return self._widget_cache[key]

        # 回退到 query_one（如果 widget 未被缓存）
        try:
            widget = self.query_one(
                f"#{key}" if not key.startswith("#") else key, widget_class
            )
            self._widget_cache[key] = widget
            return widget
        except Exception:
            return None

    def _get_theme_banner_color(self) -> str:
        """从当前 Theme 对象获取 banner 颜色."""
        if self._theme_manager:
            theme = self._theme_manager.get_current_theme()
            return theme.banner_color
        return "#C9A0E0"  # 默认紫色

    def _render_welcome_banner(self) -> None:
        """渲染欢迎 Banner 和右侧信息。

        布局：
        ┌─────────────────────────────────────────────────────────────────┐
        │ ░█░█░█▀█░█▀█░█▀▄░█▀▀░█▀█░█▄█░█▀▀    │  v1.0.0                   │
        │ ░█▀█░█▀█░█░█░█░█░▀▀█░█░█░█░█░█▀▀    │  Agent · my-project       │
        │ ░▀░▀░▀░▀░▀░▀░▀▀░░▀▀▀░▀▀▀░▀░▀░▀▀▀    │  代码写得好，bug 少...    │
        └─────────────────────────────────────────────────────────────────┘
        """
        # 初始化缓存（首次调用时）
        if not self._banner_cache_initialized:
            self._init_banner_cache()

        # 从 CSS 主题文件读取 Banner 颜色
        banner_color = self._get_theme_banner_color()

        # 渲染左侧 ASCII Banner
        welcome_lines = [
            f"[bold {banner_color}]░█░█░█▀█░█▀█░█▀▄░█▀▀░█▀█░█▄█░█▀▀[/]",
            f"[bold {banner_color}]░█▀█░█▀█░█░█░█░█░▀▀█░█░█░█░█░█▀▀[/]",
            f"[bold {banner_color}]░▀░▀░▀░▀░▀░▀░▀▀░░▀▀▀░▀▀▀░▀░▀░▀▀▀[/]",
        ]

        # 使用缓存的 widgets
        welcome_widget = self._widget_cache.get("welcome_banner")
        if welcome_widget:
            from rich.text import Text as RichText

            welcome_text = RichText.from_markup("\n".join(welcome_lines))
            welcome_widget.update(welcome_text)

        # 获取随机问候语（先显示 fallback，LLM 生成后再更新）
        try:
            from common.i18n import get_random_greeting

            greeting = get_random_greeting()
        except Exception:
            greeting = "存在先于本质。"

        # 渲染右侧信息栏
        from rich.text import Text as RichText

        # 尝试获取当前模式
        current_mode = "Agent"  # 默认模式
        try:
            if (
                hasattr(self, "_agent")
                and self._agent
                and hasattr(self._agent, "get_mode")
            ):
                current_mode = self._agent.get_mode()
        except Exception:
            pass

        # 获取工作目录（绝对路径）
        cwd_path = self.cwd or "unknown"

        # 路径太长时截断显示（单行）
        max_chars = 40
        if len(cwd_path) > max_chars:
            half = max_chars - 3  # 留3位给 "..."
            cwd_path = cwd_path[:half] + "..."

        # 第1行：版本号 + 俏皮话（不要引号）
        version_widget = self._widget_cache.get("version_info")
        if version_widget and self._banner_cache.get("version"):
            version_text = RichText.from_markup(
                f"[dim]{self._banner_cache['version']}[/] [dim]·[/] [italic dim]{greeting}[/]"
            )
            version_widget.update(version_text)

        # 第2行：工作目录（单行显示）
        mode_widget = self._widget_cache.get("skills_info")
        if mode_widget:
            mode_text = RichText.from_markup(f"[bright_black]{cwd_path}[/]")
            mode_widget.update(mode_text)

        # 第3行：留空（不再使用）
        greeting_widget = self._widget_cache.get("tools_info")
        if greeting_widget:
            greeting_widget.update("")

    def _generate_wisdom_async(self) -> None:
        """后台异步生成哲学语录并更新 Banner 显示。"""
        try:
            agent = self._get_agent()
            if not agent or not agent.llm_provider:
                return

            from common.i18n import get_language

            lang = get_language()
            lang_prompt = {"zh": "中文", "en": "English"}.get(lang, "English")

            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # ponytail: 一次简单 LLM 调用，timeout 15s
                response = loop.run_until_complete(
                    agent.llm_provider.generate(
                        prompt=f"Give me one short philosophical quote (max 25 characters) in {lang_prompt} about life, existence, or wisdom. Only return the quote, nothing else.",
                        max_tokens=60,
                        temperature=1.0,
                    )
                )
                wisdom = (
                    response.content.strip() if response and response.content else None
                )
            finally:
                loop.close()

            if wisdom:
                version_widget = self._widget_cache.get("version_info")
                if version_widget and self._banner_cache.get("version"):
                    from rich.text import Text as RichText

                    version_text = RichText.from_markup(
                        f"[dim]{self._banner_cache['version']}[/] [dim]·[/] [italic dim]{wisdom}[/]"
                    )
                    version_widget.update(version_text)
        except Exception:
            pass  # 静默失败，用户看到的是 fallback

    def _get_tools_count(self) -> int:
        """获取已注册的工具数量"""
        try:
            from tools.tool_registry import get_tool_registry

            registry = get_tool_registry()
            if registry:
                return len(registry._tools) if hasattr(registry, "_tools") else 0
        except ImportError:
            pass
        return 0

    def _get_skills_count(self) -> int:
        """获取已加载的 Skill 数量"""
        try:
            from agent.skills.skill_manager import skill_manager

            return len(skill_manager.skills)
        except ImportError:
            pass
        return 0

    def _get_project_path(self) -> str:
        """获取项目根目录（Handsome Agent 所在目录）"""
        from pathlib import Path

        # 获取当前文件所在目录，然后取上级目录
        current_file = Path(__file__).resolve()
        # tui/textual_app/app.py -> tui/textual_app -> tui -> 项目根目录
        project_root = current_file.parent.parent.parent
        return str(project_root)

    def _get_skills_path(self) -> str:
        """获取 skills 目录路径"""
        from pathlib import Path

        project_root = Path(__file__).resolve().parent.parent.parent
        skills_dir = project_root / "skills"
        return str(skills_dir)

    def _get_tools_path(self) -> str:
        """获取 tools 目录路径"""
        from pathlib import Path

        project_root = Path(__file__).resolve().parent.parent.parent
        tools_dir = project_root / "tools"
        return str(tools_dir)

    def _format_context(self, tokens: int | None) -> str:
        if not tokens:
            return "?"

        if tokens >= 1_000_000:
            val = tokens / 1_000_000
            rounded = round(val)
            if abs(val - rounded) < 0.05:
                return f"{rounded}M"
            return f"{val:.1f}M"
        elif tokens >= 1_000:
            val = tokens / 1_000
            rounded = round(val)
            if abs(val - rounded) < 0.05:
                return f"{rounded}K"
            return f"{val:.1f}K"
        return str(tokens)

    def _init_session_store(self) -> None:
        if SessionStore:
            try:
                self._session_store = SessionStore()
                self._logger.debug("SessionStore initialized")

                if not self.session_id:
                    self.session_id, is_new = self._session_store.get_or_create_session(
                        model=self.model_name or "",
                        provider=self.provider or "",
                    )
                    if is_new:
                        self._logger.info(f"Created new session: {self.session_id}")
                    else:
                        self._logger.debug(f"Using existing session: {self.session_id}")
                else:
                    self._session_store.get_or_create_session(
                        model=self.model_name or "",
                        provider=self.provider or "",
                        session_id=self.session_id,
                    )
            except Exception as e:
                self._logger.error(f"Failed to initialize SessionStore: {e}")
                self._session_store = None

    def _init_approval_manager(self, approval_mode: str | ApprovalMode) -> None:
        if ApprovalManager:
            try:
                if isinstance(approval_mode, str):
                    mode = ApprovalMode.from_string(approval_mode)
                else:
                    mode = approval_mode

                self._approval_manager = ApprovalManager(mode=mode)
                self._logger.info(
                    f"ApprovalManager initialized with mode: {mode.value}"
                )
            except Exception as e:
                self._logger.error(f"Failed to initialize ApprovalManager: {e}")
                self._approval_manager = None

    def set_theme(self, theme_id: str) -> bool:
        if not self._theme_manager:
            self._logger.warning("Theme manager not available")
            return False

        success = self._theme_manager.set_theme(theme_id)
        if success:
            self._logger.info(f"Theme changed to: {theme_id}")
        else:
            self.notify(f"Theme '{theme_id}' not found")
            self._logger.warning(f"Theme not found: {theme_id}")

        return success

    def get_current_theme_id(self) -> str:
        if self._theme_manager:
            return self._theme_manager.get_current_theme_id()
        return "default"

    def list_available_themes(self) -> list[str]:
        if self._theme_manager:
            return self._theme_manager.list_theme_ids()
        return ["default"]

    def _update_transparency_styles(self, enabled: bool) -> None:
        transparent_mappings = {
            "#app-header": "transparent-header",
            "#status-bar": "transparent-status-bar",
            "#app-footer": "transparent-footer",
            "#sidebar-container": "transparent-sidebar",
            "#chat-area": "transparent-chat",
            "#user-input": "transparent-input",
            "#welcome-banner": "transparent-welcome",
        }

        try:
            for widget_id, transparent_class in transparent_mappings.items():
                try:
                    widget = self.query_one(widget_id)

                    if enabled:
                        widget.add_class(transparent_class)
                    else:
                        widget.remove_class(transparent_class)

                except Exception:
                    pass
        except Exception as e:
            self._logger.debug(f"Failed to update transparency styles: {e}")

    def is_transparency_enabled(self) -> bool:
        if self._theme_manager:
            return self._theme_manager.is_transparency_enabled()
        return False

    def notify_animated(
        self,
        message: str,
        notification_type: str = NotificationType.INFO,
        duration: float = 3.0,
    ) -> None:
        icon = NotificationType.get_icon(notification_type)

        if notification_type == NotificationType.SUCCESS:
            animated_msg = f"✅ {message}"
        elif notification_type == NotificationType.WARNING:
            animated_msg = f"⚠️ {message}"
        elif notification_type == NotificationType.ERROR:
            animated_msg = f"❌ {message}"
        else:
            animated_msg = f"ℹ️ {message}"

        self.notify(
            animated_msg,
            timeout=duration,
            title=(
                notification_type.upper()
                if notification_type != NotificationType.INFO
                else "通知"
            ),
        )

        self._logger.debug(f"Animated notification: [{notification_type}] {message}")

    def notify_success(self, message: str, duration: float = 3.0) -> None:
        self.notify_animated(message, NotificationType.SUCCESS, duration)

    def notify_warning(self, message: str, duration: float = 4.0) -> None:
        self.notify_animated(message, NotificationType.WARNING, duration)

    def notify_error(self, message: str, duration: float = 5.0) -> None:
        self.notify_animated(message, NotificationType.ERROR, duration)

    def notify_info(self, message: str, duration: float = 3.0) -> None:
        self.notify_animated(message, NotificationType.INFO, duration)

    def show_loading_animation(self, message: str = "加载中...") -> None:
        loading_msg = f"⏳ {message}"
        self.notify(loading_msg, timeout=None, title="LOADING")

    def show_progress_notification(
        self,
        progress: float,
        message: str = "",
        total: int = 100,
    ) -> None:
        percent = int(progress * 100)
        current = int(progress * total)

        bar_length = 20
        filled = int(bar_length * progress)
        bar = "█" * filled + "░" * (bar_length - filled)

        progress_msg = f"{bar} {percent}%"
        if message:
            progress_msg = f"{message}\n{progress_msg}"

        self.notify(progress_msg, timeout=2.0, title=f"进度 ({current}/{total})")

    def apply_skin_from_engine(self) -> bool:
        if not self._theme_manager:
            self._logger.warning("Theme manager not available")
            return False

        success = self._theme_manager.load_skin_from_engine()
        if success:
            display_name = self._theme_manager.get_current_display_name()
            self.notify(f"Applied skin: {display_name}")
            self._logger.info("Skin applied from engine")
        else:
            self._logger.debug("No skin to apply from engine")

        return success

    def request_tool_approval(
        self,
        tool_name: str,
        tool_args: dict,
        callback: callable,
    ) -> bool:
        if not self._approval_manager:
            callback(True)
            return False

        if not self._approval_manager.should_approve(tool_name):
            self._logger.debug(f"Tool '{tool_name}' does not require approval")
            callback(True)
            return False

        self._pending_tool_call = {
            "name": tool_name,
            "args": tool_args,
        }
        self._approval_callback = callback
        self._show_approval_dialog(tool_name, tool_args)
        return True

    def _show_approval_dialog(self, tool_name: str, tool_args: dict) -> None:
        if not ApprovalDialog:
            self._logger.warning("ApprovalDialog not available, rejecting operation")
            self._handle_approval_result(False)
            return

        risk_level = (
            self._approval_manager.get_risk_level(tool_name)
            if self._approval_manager
            else RiskLevel.MEDIUM
        )
        preview = self._generate_tool_preview(tool_name, tool_args)

        dialog = create_approval_dialog(
            operation=tool_name,
            preview=preview,
            risk_level=risk_level,
        )

        self._logger.info(
            f"Showing approval dialog for: {tool_name} (risk: {risk_level.value})"
        )
        self.screen.mount(dialog)

    def _generate_tool_preview(self, tool_name: str, tool_args: dict) -> str:
        preview_parts = []

        for key, value in tool_args.items():
            value_str = str(value)
            if len(value_str) > 50:
                value_str = value_str[:47] + "..."

            if key.lower() in ("password", "token", "secret", "key", "api_key"):
                value_str = "***"

            preview_parts.append(f"{key}={value_str}")

        preview = "; ".join(preview_parts)

        if len(preview) > 100:
            preview = preview[:97] + "..."

        return preview

    def _handle_approval_result(self, approved: bool) -> None:
        if self._approval_callback:
            operation = (
                self._pending_tool_call["name"]
                if self._pending_tool_call
                else "unknown"
            )
            self._logger.info(
                f"Approval result for '{operation}': {'approved' if approved else 'rejected'}"
            )

            try:
                self._approval_callback(approved)
            except Exception as e:
                self._logger.error(f"Error in approval callback: {e}")

        self._pending_tool_call = None
        self._approval_callback = None

    def on_approval_confirmed(self, event: ApprovalConfirmed) -> None:
        self._handle_approval_result(True)

    def on_approval_rejected(self, event: ApprovalRejected) -> None:
        self._handle_approval_result(False)

    def set_approval_mode(self, mode: str | ApprovalMode) -> None:
        if self._approval_manager:
            self._approval_manager.set_mode(mode)
            self._logger.info(f"Approval mode changed to: {mode}")

    def get_approval_mode(self) -> ApprovalMode:
        if self._approval_manager:
            return self._approval_manager.mode
        return ApprovalMode.AUTO

    def is_sensitive_operation(self, operation: str) -> bool:
        if self._approval_manager:
            return self._approval_manager.is_sensitive_operation(operation)
        return False

    def _restore_session(self, session_id: str) -> list[dict[str, str]]:
        if not self._session_store:
            return []

        try:
            messages = self._session_store.get_messages(session_id, limit=100)
            return [{"role": msg.role, "content": msg.content} for msg in messages]
        except Exception as e:
            self._logger.error(f"Failed to restore session: {e}")
            return []

    def _auto_save_check(self) -> None:
        self._pending_message_count += 1
        if self._pending_message_count >= self._auto_save_interval:
            self._flush_messages()

    def _flush_messages(self) -> None:
        if self._session_store:
            try:
                count = self._session_store.flush_pending_messages()
                if count > 0:
                    self._logger.debug(f"Flushed {count} pending messages")
                self._pending_message_count = 0
            except Exception as e:
                self._logger.error(f"Failed to flush messages: {e}")

    def save_message(self, role: str, content: str, **kwargs) -> None:
        if not self._session_store or not self.session_id:
            return

        try:
            self._session_store.save_message(
                session_id=self.session_id,
                role=role,
                content=content,
                flush=False,
                **kwargs,
            )
            self._auto_save_check()
        except Exception as e:
            self._logger.error(f"Failed to save message: {e}")

    def on_unmount(self) -> None:
        self._flush_messages()
        self._logger.debug("Application unmounted, data saved")
        self._restore_console_handler()

    def _restore_console_handler(self) -> None:
        if (
            self._tui_log_handler is not None
            and self._saved_console_handler is not None
        ):
            try:
                if self._tui_log_handler in logging.root.handlers:
                    logging.root.removeHandler(self._tui_log_handler)
                for logger_name in logging.Logger.manager.loggerDict:
                    logger = logging.getLogger(logger_name)
                    if self._tui_log_handler in logger.handlers:
                        logger.removeHandler(self._tui_log_handler)

                if self._saved_console_handler not in logging.root.handlers:
                    logging.root.addHandler(self._saved_console_handler)
            except Exception:
                pass

    def _on_sidebar_panel_switch(self, panel_type: str) -> None:
        try:
            sidebar = self.query_one("#sidebar-container-inner")
            if sidebar:
                sidebar.switch_to_panel(panel_type)
        except Exception as e:
            self._logger.debug(f"Failed to switch sidebar panel: {e}")

    def action_toggle_sidebar(self) -> None:
        try:
            sidebar = self.query_one("#sidebar-container")
            if sidebar:
                if sidebar.styles.display == "none":
                    sidebar.styles.display = "block"
                    self.notify("侧边栏已显示")
                else:
                    sidebar.styles.display = "none"
                    self.notify("侧边栏已隐藏")
                self._logger.debug(
                    f"Sidebar toggled, display: {sidebar.styles.display}"
                )
        except Exception as e:
            self._logger.debug(f"Sidebar toggle failed: {e}")

    def _get_sidebar_and_switch(self, panel_type: str) -> None:
        """显示侧边栏并切换到指定面板."""
        self._logger.info(f"[_get_sidebar_and_switch] panel_type={panel_type}")
        try:
            # 先显示外层容器（如果隐藏的话）
            outer = self.query_one("#sidebar-container", Container)
            self._logger.debug(
                f"[_get_sidebar_and_switch] outer display={outer.styles.display}"
            )
            if outer.styles.display == "none":
                outer.styles.display = "block"
            # 再切换内部 SidebarContainer 的面板
            inner = self.query_one("#sidebar-container-inner", SidebarContainer)
            self._logger.debug(
                f"[_get_sidebar_and_switch] inner={type(inner).__name__}"
            )
            inner.switch_to_panel(panel_type)
        except Exception as e:
            self._logger.error(f"[_get_sidebar_and_switch] Failed: {e}", exc_info=True)

    def action_next_panel(self) -> None:
        """切换到下一个面板."""
        panel_order = ["goal", "file_tree", "skills"]
        try:
            inner = self.query_one("#sidebar-container-inner", SidebarContainer)
            # 获取 TabbedContent 的当前活动面板
            tabbed = inner.query_one("TabbedContent")
            current_tab = tabbed.active
            if current_tab in panel_order:
                idx = panel_order.index(current_tab)
                next_panel = panel_order[(idx + 1) % len(panel_order)]
                self._get_sidebar_and_switch(next_panel)
        except Exception as e:
            self._logger.debug(f"action_next_panel: {e}")

    def action_prev_panel(self) -> None:
        """切换到上一个面板."""
        panel_order = ["goal", "file_tree", "skills"]
        try:
            inner = self.query_one("#sidebar-container-inner", SidebarContainer)
            # 获取 TabbedContent 的当前活动面板
            tabbed = inner.query_one("TabbedContent")
            current_tab = tabbed.active
            if current_tab in panel_order:
                idx = panel_order.index(current_tab)
                prev_panel = panel_order[(idx - 1) % len(panel_order)]
                self._get_sidebar_and_switch(prev_panel)
        except Exception as e:
            self._logger.debug(f"action_prev_panel: {e}")

    def action_open_log_screen(self) -> None:
        """打开全局日志窗口 (Alt+L)."""
        if LogScreen:
            # 检查是否已经打开（直接判断当前屏幕）
            if isinstance(self.screen, LogScreen):
                self.pop_screen()
                return
            self.push_screen(LogScreen())
            self._logger.debug("Log screen opened")
        else:
            self.notify("日志窗口不可用")

    def action_open_help(self) -> None:
        if HelpScreen:
            self.push_screen(HelpScreen())
            self._logger.debug("Help screen opened")
        else:
            self.notify("Help: q=quit, Ctrl+B=sidebar, Ctrl+T=new tab")

    def action_open_settings(self) -> None:
        """打开设置界面."""
        if SettingsScreen:
            self.push_screen(SettingsScreen())
            self._logger.debug("Settings screen opened")
        else:
            self.notify("Settings not available")

    def _on_send_button_pressed(self) -> None:
        self._submit_user_input()

    def _on_text_area_submitted(self) -> None:
        self._submit_user_input()

    def _render_markdown_content(self, content: str) -> str:
        """使用 Textual 原生 Markdown 组件渲染内容.

        Args:
            content: Markdown 格式的文本

        Returns:
            渲染后的 Rich 格式文本
        """
        if not content:
            return content

        try:
            # 使用 Textual 原生 Markdown 组件渲染
            markdown_widget = Markdown(content)
            # 获取渲染结果（返回 Rich Text 对象）
            from rich.console import RenderableType

            return markdown_widget._content  # Markdown widget 的内部内容已经是渲染好的
        except Exception:
            return content

    def _append_message(
        self, role: str, content: str, render_markdown: bool = True
    ) -> None:
        # 使用缓存的 widget（优化性能）
        chat_area = self._widget_cache.get("chat_area")
        if chat_area is None:
            chat_area = self.query_one("#chat-area", ChatView)

        # 提取 tool_name 并跟踪工具
        tool_name = None
        if role == "tool" and content:
            # 尝试从 content 中提取工具名
            # 常见格式: "ToolName: result" 或 "Using tool: ToolName"
            lines = content.split("\n")
            first_line = lines[0] if lines else ""
            if ": " in first_line:
                tool_name = first_line.split(":")[0].strip()
            elif "using tool" in first_line.lower():
                # 格式: "Using tool: ToolName"
                parts = first_line.lower().split("using tool")
                if len(parts) > 1:
                    tool_name = (
                        parts[1].strip().split()[0] if parts[1].strip() else None
                    )
            if tool_name:
                self._used_tools.add(tool_name)

        # ChatView 使用 append_message 正确传递 role
        if hasattr(chat_area, "append_message"):
            chat_area.append_message(role, content, tool_name=tool_name)
        elif hasattr(chat_area, "write"):
            chat_area.write(f"{content}\n")

        # 同时保存到 session_store（用于 token 计数）
        self.save_message(role, content)

        # 更新工具显示
        self._update_used_tools()

    def _navigate_input_history(self, direction: int) -> None:
        """输入框上下键触发的历史导航回调。

        Args:
            direction: -1 表示向上（更早的历史），
                1 表示向下（更新的历史或还原当前输入）
        """
        if direction < 0:
            self._history_prev()
        else:
            self._history_next()

    def _history_prev(self) -> None:
        text_area = self.query_one("#user-input", TextArea)

        if not self._input_history:
            return

        if self._history_index == -1:
            self._current_input = text_area.text

        if self._history_index < len(self._input_history) - 1:
            self._history_index += 1
            text_area.text = self._input_history[self._history_index]

    def _history_next(self) -> None:
        text_area = self.query_one("#user-input", TextArea)

        if self._history_index == -1:
            return

        if self._history_index > 0:
            self._history_index -= 1
            text_area.text = self._input_history[self._history_index]
        else:
            self._history_index = -1
            text_area.text = self._current_input

    def _submit_from_history(self) -> None:
        text_area = self.query_one("#user-input", TextArea)
        user_input = text_area.text.strip()

        if not user_input:
            return

        if user_input not in self._input_history:
            self._input_history.insert(0, user_input)
            if len(self._input_history) > 100:
                self._input_history = self._input_history[:100]

        self._history_index = -1
        self._current_input = ""
        text_area.text = ""
        self._append_message("user", user_input)
        self._logger.debug(f"User input: {user_input[:50]}...")
        self.app.call_later(lambda: self._call_agent_async(user_input))

    def _submit_user_input(self) -> None:
        text_area = self.query_one("#user-input", TextArea)
        user_input = text_area.text.strip()

        if not user_input:
            return

        if user_input not in self._input_history:
            self._input_history.insert(0, user_input)
            if len(self._input_history) > 100:
                self._input_history = self._input_history[:100]

        self._history_index = -1
        self._current_input = ""
        text_area.text = ""
        self._append_message("user", user_input)
        self._logger.debug(f"User input: {user_input[:50]}...")
        self.app.call_later(lambda: self._call_agent_async(user_input))

    def _call_agent_async(self, user_input: str) -> None:
        """使用持久事件循环在子线程中运行异步 agent"""
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        self.set_agent_status("busy")
        self._start_loading_animation()

        def on_stream_delta(text: str):
            self.app.call_later(self._on_agent_stream_delta, text)

        def on_thinking(text: str):
            self.app.call_later(self._on_agent_thinking, text)

        def run_agent():
            """在子线程中运行异步 agent"""
            try:
                agent = self._get_agent()
                if agent:
                    agent.set_stream_callback(on_stream_delta)
                    agent.set_thinking_callback(on_thinking)

                    # 获取或创建线程局部的事件循环
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_closed():
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                    try:
                        response = agent.chat(user_input, enable_stream=True)
                        if asyncio.iscoroutine(response):
                            response = loop.run_until_complete(response)
                        return response
                    finally:
                        # 不关闭循环，让它被垃圾回收
                        pass
                else:
                    return "Agent 未初始化，请检查配置"
            except Exception as e:
                return f"错误: {str(e)}"

        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(run_agent)
        executor.shutdown(wait=False)

        self._agent_future = future
        self._agent_start_time = __import__("time").time()
        self._current_thinking = ""

        # ponytail: done_callback instead of fixed-interval polling — no CPU waste
        def _on_done(f):
            self.app.call_later(self._agent_result_callback)

        future.add_done_callback(_on_done)

    def _agent_result_callback(self) -> None:
        """Called on main thread when agent future completes."""
        import time

        future = getattr(self, "_agent_future", None)
        if future is None:
            return

        self._stop_loading_animation()
        self.set_agent_status("online")

        elapsed = time.time() - getattr(self, "_agent_start_time", time.time())
        elapsed_minutes = int(elapsed // 60)
        elapsed_seconds = int(elapsed % 60)

        try:
            response = future.result()
            if response:
                if hasattr(response, "content"):
                    content = str(response.content)
                else:
                    content = str(response)
            else:
                content = "（无回复）"

            self._complete_agent_stream()

            if not getattr(self, "_current_streaming_id", None):
                self._show_typewriter_message(content)

            time_widget = self._widget_cache.get("status_time")
            if time_widget:
                if elapsed_minutes > 0:
                    time_widget.update(f"│ {elapsed_minutes}m {elapsed_seconds}s ")
                else:
                    time_widget.update(f"│ {elapsed_seconds}s ")

            if self._session_store:
                self._session_store.flush_pending_messages()
            self.call_later(self._update_token_count)
        except Exception as e:
            self._stop_loading_animation()
            self.set_agent_status("error")
            self._append_message("system", f"❌ 处理失败: {str(e)}")
            self._current_streaming_id = None

        self._agent_future = None
        self._agent_busy = False

        # 处理队列中的下一条消息
        if self._pending_queue:
            next_input = self._pending_queue.popleft()
            self._append_message("user", next_input)
            # 更新队列显示（pop 后传入新的队列长度以正确反映剩余排队消息）
            self._update_queue_display(queue_len_override=len(self._pending_queue))
            self._call_agent_async(next_input)
        else:
            # 队列已空，恢复输入框
            self._update_queue_display()

    def _get_agent(self):
        if hasattr(self, "_agent") and self._agent:
            return self._agent
        if getattr(self, "_agent", None) is not None:
            return self._agent
        try:
            from agent.agent import create_agent_from_config

            self._agent = create_agent_from_config()
            if self._agent:
                self._logger.info("Agent lazily created from config")
        except Exception as e:
            self._logger.warning(f"Failed to lazy-create agent: {e}")
        return getattr(self, "_agent", None)

    def _on_agent_stream_delta(self, text: str) -> None:
        """处理 Agent 流式输出增量"""
        chat_area = self._widget_cache.get("chat_area")
        if chat_area is None:
            chat_area = self.query_one("#chat-area", ChatView)

        if chat_area and hasattr(chat_area, "start_streaming"):
            if (
                not hasattr(self, "_current_streaming_id")
                or not self._current_streaming_id
            ):
                self._current_streaming_id = chat_area.start_streaming("assistant")

            if hasattr(chat_area, "append_streaming_text"):
                chat_area.append_streaming_text(text)

    def _on_agent_thinking(self, text: str) -> None:
        """处理 Agent 思考内容"""
        self._current_thinking = getattr(self, "_current_thinking", "") + text

        chat_area = self._widget_cache.get("chat_area")
        if chat_area is None:
            chat_area = self.query_one("#chat-area", ChatView)

        if chat_area and hasattr(chat_area, "append_streaming_thinking"):
            chat_area.append_streaming_thinking(text)

    def _complete_agent_stream(self) -> None:
        """完成 Agent 流式输出"""
        chat_area = self._widget_cache.get("chat_area")
        if chat_area is None:
            chat_area = self.query_one("#chat-area", ChatView)

        if (
            chat_area
            and hasattr(chat_area, "complete_streaming")
            and hasattr(self, "_current_streaming_id")
        ):
            chat_area.complete_streaming()

        self._current_streaming_id = None

    def _show_typewriter_message(self, content: str) -> None:
        """显示 Agent 回复消息"""
        chat_area = self._widget_cache.get("chat_area")
        if chat_area is None:
            chat_area = self.query_one("#chat-area", ChatView)

        if chat_area:
            if hasattr(chat_area, "add_assistant_message"):
                chat_area.add_assistant_message(content)
            elif hasattr(chat_area, "write"):
                chat_area.write(f"\nAgent: {content}\n")

    def action_quit(self) -> None:
        self._logger.info("User requested quit")
        self.app.exit()

    def _on_session_selected(
        self, event: "SessionPickerScreen.SessionSelected"
    ) -> None:
        old_session_id = self.session_id
        self.session_id = event.session_id
        self._logger.info(f"Session switched: {old_session_id} -> {event.session_id}")
        self._render_welcome_banner()

        if self._active_tab_id and self._active_tab_id in self._tab_states:
            chat_view = self._tab_states[self._active_tab_id]["chat_view"]
            chat_view.clear_messages()
            history = self._restore_session(event.session_id)
            for msg in history:
                chat_view.append_message(msg["role"], msg["content"])
            if not history:
                chat_view.show_greeting()

        self.notify(
            t("session.switched", "已切换到会话: {title}").format(
                title=event.session_title
            )
        )

    def _on_session_deleted(self, event: "SessionPickerScreen.SessionDeleted") -> None:
        if event.session_id == self.session_id:
            self._logger.info("Current session deleted, switching to new session")
            if self._session_store:
                new_id, _ = self._session_store.get_or_create_session(
                    model=self.model_name or "",
                    provider=self.provider or "",
                )
                self.session_id = new_id
                self._render_welcome_banner()
                if self._active_tab_id and self._active_tab_id in self._tab_states:
                    self._tab_states[self._active_tab_id]["chat_view"].clear_messages()
                    self._tab_states[self._active_tab_id]["chat_view"].show_greeting()

        self._logger.info(f"Session deleted: {event.session_id}")

    def action_next_tab(self) -> None:
        tabs = self.query_one("Tabs", Tabs)
        all_tabs = list(tabs.query("Tab"))
        if not all_tabs:
            return

        current_index = -1
        for i, tab in enumerate(all_tabs):
            if tab.id == tabs.active:
                current_index = i
                break

        next_index = (current_index + 1) % len(all_tabs)
        next_tab = all_tabs[next_index]

        if next_tab.id:
            tabs.active = next_tab.id
            self._logger.debug(f"Switched to next tab: {next_tab.id}")

    def action_prev_tab(self) -> None:
        tabs = self.query_one("Tabs", Tabs)
        all_tabs = list(tabs.query("Tab"))
        if not all_tabs:
            return

        current_index = -1
        for i, tab in enumerate(all_tabs):
            if tab.id == tabs.active:
                current_index = i
                break

        prev_index = (current_index - 1) % len(all_tabs)
        prev_tab = all_tabs[prev_index]

        if prev_tab.id:
            tabs.active = prev_tab.id
            self._logger.debug(f"Switched to previous tab: {prev_tab.id}")

    def append_chat_message(self, role: str, content: str) -> None:
        chat_area = self.query_one("#chat-area", ChatView)
        if chat_area:
            label = "You" if role == "user" else "Agent"
            if hasattr(chat_area, "write"):
                chat_area.write(f"{label}: {content}\n")
            elif hasattr(chat_area, "append_message"):
                chat_area.append_message(role, content)

    def clear_chat(self) -> None:
        chat_area = self.query_one("#chat-area", ChatView)
        if chat_area:
            if hasattr(chat_area, "clear"):
                chat_area.clear()
            elif hasattr(chat_area, "clear_messages"):
                chat_area.clear_messages()

    def add_tab(self) -> str | None:
        if not ChatView:
            self._logger.warning("ChatView not available")
            return None

        self._tab_counter += 1
        tab_id = f"chat-tab-{self._tab_counter}"
        tab_title = t("chat.tab.title", "Chat") + f" {self._tab_counter}"

        tabs = self.query_one("Tabs", Tabs)
        content_area = self.query_one("#content-area", VerticalScroll)

        tabs.add_tab(Tab(tab_title, id=tab_id))
        chat_view = ChatView(tab_id, tab_title)
        content_area.mount(chat_view)

        self._tab_states[tab_id] = {
            "title": tab_title,
            "chat_view": chat_view,
        }

        tabs.active = tab_id
        self._active_tab_id = tab_id
        self._show_tab_content(tab_id)

        self._logger.info(f"Tab created: {tab_id}")
        return tab_id

    def close_tab(self, tab_id: str) -> bool:
        tabs = self.query_one("Tabs", Tabs)
        content_area = self.query_one("#content-area", VerticalScroll)

        all_tabs = list(tabs.query("Tab"))

        if len(all_tabs) <= 1:
            self.notify(t("chat.tab.cannot_close_last", "Cannot close the last tab"))
            return False

        tab_to_close = tabs.query_one(f"#{tab_id}", Tab)
        if not tab_to_close:
            self._logger.warning(f"Tab not found: {tab_id}")
            return False

        was_active = tabs.active == tab_id
        tab_to_close.remove()

        if tab_id in self._tab_states:
            chat_view = self._tab_states[tab_id]["chat_view"]
            chat_view.remove()
            del self._tab_states[tab_id]

        if was_active:
            remaining_tabs = list(tabs.query("Tab"))
            if remaining_tabs:
                new_active = remaining_tabs[0].id
                tabs.active = new_active
                self._active_tab_id = new_active
                self._show_tab_content(new_active)

        self._logger.info(f"Tab closed: {tab_id}")
        return True

    def _show_tab_content(self, tab_id: str) -> None:
        content_area = self.query_one("#content-area", VerticalScroll)

        for state in self._tab_states.values():
            chat_view = state["chat_view"]
            if chat_view.parent:
                chat_view.display = False

        if tab_id in self._tab_states:
            chat_view = self._tab_states[tab_id]["chat_view"]
            chat_view.display = True

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        if event.tab:
            tab_id = event.tab.id
            if tab_id:
                self._active_tab_id = tab_id
                self._show_tab_content(tab_id)
                self._logger.debug(f"Tab activated: {tab_id}")

    def action_new_tab(self) -> None:
        self.add_tab()

    def action_close_tab(self) -> None:
        if self._active_tab_id:
            self.close_tab(self._active_tab_id)


def run_textual_app(
    model_name: str = "Handsome Agent",
    provider: str | None = None,
    cwd: str | None = None,
    session_id: str | None = None,
    context_length: int | None = None,
    approval_mode: str = "suggest",
    initial_theme: str | None = None,
    agent=None,
) -> int:
    if not TEXTUAL_AVAILABLE:
        print(get_textual_install_hint())
        return 1

    compatible, reason = is_textual_compatible()
    if not compatible:
        print(f"\n⚠ Cannot start Textual TUI: {reason}")
        print("Falling back to legacy CLI mode...\n")
        return 1

    app = HandsomeAgentApp(
        model_name=model_name,
        provider=provider,
        cwd=cwd,
        session_id=session_id,
        context_length=context_length,
        approval_mode=approval_mode,
        initial_theme=initial_theme,
        agent=agent,
    )

    try:
        return app.run()
    finally:
        app._restore_console_handler()


def check_textual_available() -> bool:
    return TEXTUAL_AVAILABLE


def get_textual_import_error() -> str | None:
    if TEXTUAL_AVAILABLE:
        return None

    if _TEXTUAL_IMPORT_ERROR:
        return f"Textual not installed or import failed: {_TEXTUAL_IMPORT_ERROR}"

    try:
        import textual
    except ImportError as e:
        return f"Textual not installed: {e}"
    except Exception as e:
        return f"Error importing Textual: {e}"

    return "Unknown error"


def get_textual_install_hint() -> str:
    return (
        "\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚠  Textual 不可用\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "原因：Textual 库未安装或导入失败\n"
        "\n"
        "解决方案：\n"
        "  1. 安装 Textual：pip install textual>=0.50.0\n"
        "  2. 或使用 --no-textual 参数强制使用传统 CLI 模式\n"
        "  3. 或在非 TTY 环境（如管道/重定向）中自动使用传统模式\n"
        "\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    )


def is_textual_compatible() -> tuple[bool, str | None]:
    if not TEXTUAL_AVAILABLE:
        return False, "Textual not installed"

    if not sys.stdout.isatty():
        return False, "Non-TTY environment detected"

    try:
        import shutil

        terminal_size = shutil.get_terminal_size()
        if terminal_size.columns < 40:
            return False, "Terminal too narrow (minimum 40 columns)"
    except Exception:
        pass

    return True, None


def create_fallback_app(
    model_name: str = "Handsome Agent",
    provider: str | None = None,
    cwd: str | None = None,
    session_id: str | None = None,
    context_length: int | None = None,
    approval_mode: str = "suggest",
) -> None:
    from common.terminal.banner import print_simple_banner
    from common.terminal.ui import print_info, print_warning

    print_simple_banner()
    print_info(f"Model: {model_name}")
    if provider:
        print_info(f"Provider: {provider}")
    print_info(f"CWD: {cwd or os.getcwd()}")
    if session_id:
        print_info(f"Session: {session_id}")

    print()
    print_warning("Using legacy CLI mode (Textual TUI not available)")
    print_info("For TUI mode, install: pip install textual>=0.50.0")
    print()


__all__ = [
    "HandsomeAgentApp",
    "run_textual_app",
    "check_textual_available",
    "get_textual_import_error",
    "get_textual_install_hint",
    "is_textual_compatible",
    "create_fallback_app",
    "TEXTUAL_AVAILABLE",
    "PURPLE_PRIMARY",
    "PURPLE_BRIGHT",
    "PURPLE_DIM",
    "PURPLE_DARK",
    "ThemeManager",
    "get_theme_manager",
    "NotificationType",
    "NotificationAnimationManager",
    "is_markdown_available",
    "CustomModelInputScreen",
]


class CustomModelInputScreen(TextualScreen if TEXTUAL_AVAILABLE else object):
    """自定义模型输入对话框."""

    CSS = """
    CustomModelInputScreen {
        align: center middle;
    }

    #dialog {
        width: 50;
        height: auto;
        border: solid $primary;
        background: $surface;
        padding: 1 2;
    }

    #title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    #input-container {
        margin: 1 0;
    }

    #buttons {
        height: auto;
        align: center;
    }
    """

    def __init__(self, on_submit: callable = None, **kwargs):
        super().__init__(**kwargs)
        self._on_submit = on_submit

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Static("输入自定义模型名称", id="title")
            with Container(id="input-container"):
                yield Input(placeholder="例如: custom-model-v1", id="model-input")
            with Container(id="buttons"):
                yield Button("确认", id="btn-submit", variant="primary")
                yield Button("取消", id="btn-cancel", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-submit":
            input_widget = self.query_one("#model-input", Input)
            value = input_widget.value.strip()
            if value and self._on_submit:
                self.dismiss(value)
        elif event.button.id == "btn-cancel":
            self.dismiss(None)


if __name__ == "__main__":
    print("Testing HandsomeAgentApp...")
    print()

    if not TEXTUAL_AVAILABLE:
        print("Textual is not available.")
        print("Error message:", get_textual_import_error())
        sys.exit(1)

    print(f"Textual available: {TEXTUAL_AVAILABLE}")
    print()
    print("Starting Textual app...")
    print()

    exit_code = run_textual_app(
        model_name="gpt-4o",
        provider="OpenAI",
        cwd="E:/Projects/Handsome-Agent",
        session_id="test-session-001",
        context_length=128000,
    )

    sys.exit(exit_code)
