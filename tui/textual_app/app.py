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
from pathlib import Path
from typing import TYPE_CHECKING, Optional

# 降级机制：如果 textual 不可用，提供友好提示
TEXTUAL_AVAILABLE = True
_TEXTUAL_IMPORT_ERROR: str | None = None

try:
    from textual.app import App, ComposeResult
    from textual.widgets import Header, Footer, Static, RichLog, Tabs, Tab, TextArea, Button
    from textual.widgets import Markdown, ProgressBar, LoadingIndicator
    from textual.binding import Binding
    from textual.containers import Container, Vertical, VerticalScroll, Horizontal
    from textual.message import Message
    from textual import on
    from textual.events import Key
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

# 跨模块导入 - Textual 组件 (使用绝对导入，因为这些模块仍在 cli/tui/ 下)
try:
    from tui.theming import ThemeManager, get_theme_manager
except ImportError:
    ThemeManager = None
    get_theme_manager = None

try:
    from tui.views.chat_view import ChatView
except ImportError:
    ChatView = None

try:
    from tui.widgets.command_palette import CommandPaletteScreen, Command
except ImportError:
    CommandPaletteScreen = None
    Command = None

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
        ApprovalDialog, ApprovalMode, RiskLevel, ApprovalManager,
        ApprovalConfirmed, ApprovalRejected, create_approval_dialog,
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
    from tui.core.keybindings import (
        KeyBinding, KeyBindingManager, KeyBindingCategory, create_default_keybindings,
    )
except ImportError:
    KeyBinding = None
    KeyBindingManager = None
    KeyBindingCategory = None
    create_default_keybindings = None

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
    # Default 主题 - 高雅紫
    THEME_DEFAULT = Theme(
        name="default",
        primary="#B180D7",
        secondary="#C9A0E0",
        accent="#B180D7",
        foreground="#FFFFFF",
        background="#1a1a1a",
        surface="#2a2a2a",
        panel="#1a1a1a",
        success="#4CAF50",
        warning="#FF9800",
        error="#F44336",
        dark=True,
    )

    # Awesome 主题 - 活力绿
    THEME_AWESOME = Theme(
        name="awesome",
        primary="#A9FC6E",
        secondary="#C5FF9E",
        accent="#A9FC6E",
        foreground="#FFFFFF",
        background="#1A2E0A",
        surface="#2a2a2a",
        panel="#1a1a1a",
        success="#4CAF50",
        warning="#FF9800",
        error="#F44336",
        dark=True,
    )

    # 主题列表
    THEMES = [THEME_DEFAULT, THEME_AWESOME]


class HandsomeAgentApp(App):
    """Handsome Agent Textual TUI Application."""

    log = LogDescriptor()

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("ctrl+k", "open_command_palette", "Command"),
        Binding("ctrl+b", "toggle_sidebar", "Sidebar"),
        Binding("f1", "open_help", "Help"),
        Binding("ctrl+1", "switch_to_file_tree", "", show=False),
        Binding("ctrl+2", "switch_to_tasks", "", show=False),
        Binding("ctrl+3", "switch_to_agent", "", show=False),
        Binding("ctrl+4", "switch_to_logs", "", show=False),
        Binding("ctrl+shift+a", "change_theme", "", show=False),
        Binding("ctrl+shift+b", "toggle_transparency", "", show=False),
        Binding("ctrl+shift+m", "toggle_markdown", "", show=False),
        Binding("f10", "toggle_dark_mode", "", show=False),
        Binding("ctrl+/", "open_help", "", show=False),
        Binding("ctrl+r", "open_session_selector", "", show=False),
        Binding("ctrl+l", "clear_screen", "", show=False),
        Binding("j", "scroll_down", "", show=False),
        Binding("k", "scroll_up", "", show=False),
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
        **kwargs
    ):
        _patch_textual_logger()

        self._tui_log_handler: TuiLogHandler | None = None
        self._saved_console_handler: logging.Handler | None = None
        if LogManager is not None:
            try:
                lm = LogManager.get_instance()
                if lm._console_handler is not None:
                    self._tui_log_handler = TuiLogHandler(self)
                    if hasattr(lm._console_handler, 'formatter'):
                        self._tui_log_handler.setFormatter(lm._console_handler.formatter)
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
        self.context_length = context_length
        self._logger = get_access_logger("TextualUI", sublayer="tui")

        self._is_loading: bool = False
        self._loading_timer: Optional[callable] = None
        # 使用 Textual 原生 LoadingIndicator（覆盖模式）
        self._use_native_loading: bool = False
        self._loading_indicator: Optional[LoadingIndicator] = None
        # 保留原有的状态栏加载动画实现（可定制）
        self._LOADING_FRAMES = {
            "dots": ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"],
            "circle": ["◐", "◓", "◑", "◒"],
            "braille": ["⠓", "⠒", "⠐", "⠔", "⠠", "⠡", "⠢", "⠣"],
            "pulse": ["●", "○", "◌"],
        }
        self._loading_frames: list = self._LOADING_FRAMES["dots"]
        self._loading_frame_index: int = 0
        self._loading_style: str = "dots"

        self._is_streaming: bool = False
        self._streaming_text: str = ""
        self._streaming_widget_id: str | None = None
        self._streaming_timer: Optional[callable] = None
        self._streaming_chars_per_tick: int = 3
        self._streaming_delay_ms: int = 30

        self._agent = agent
        self._theme_manager: ThemeManager | None = None
        if get_theme_manager:
            self._theme_manager = get_theme_manager()
            if initial_theme:
                self._theme_manager.set_theme(initial_theme)
            # 注册主题变更回调
            self._theme_manager.register_theme_change_callback(self._on_theme_changed)

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
        self._key_binding_manager: Optional[KeyBindingManager] = None
        if KeyBindingManager:
            self._init_keybinding_manager()
        self._init_session_store()
        self._init_approval_manager(approval_mode)
        self._agent_status = "online"
        # 使用 Textual 原生 Markdown 组件，无需初始化
        self._markdown_enabled = True
        # TUIConsumer（任务面板消费者）
        self._tui_consumer: Optional["TUIConsumer"] = None

    def compose(self) -> ComposeResult:
        with Container(id="app-header"):
            with Horizontal(id="header-content"):
                # 左侧：ASCII Banner
                with Vertical(id="banner-left"):
                    yield Static("", id="welcome-banner")
                # 右侧：版本、skills、工具信息
                with Vertical(id="header-info-right"):
                    yield Static("", id="version-info", classes="header-info-text")
                    yield Static("", id="skills-info", classes="header-info-text")
                    yield Static("", id="tools-info", classes="header-info-text")

        with Horizontal(id="main-area"):
            yield ChatView(id="chat-area")
            if SidebarContainer:
                with Container(id="sidebar-container"):
                    yield SidebarContainer(cwd=self.cwd, agent=self._agent)

        with Container(id="input-area"):
            with Container(id="status-bar"):
                with Horizontal(id="status-content"):
                    yield Static("●", id="status-icon", classes="status-icon")
                    yield Static(self.model_name or "Handsome Agent", id="status-model", classes="status-model")
                    yield Static("0/128K", id="status-tokens", classes="status-tokens")
                    yield ProgressBar(id="status-progress", show_percentage=False)
                    yield Static("0:00", id="status-time", classes="status-time")
                    yield Static("🔧", id="status-tools", classes="status-tools")
            yield SubmitTextArea(
                id="user-input",
                classes="input-field",
                placeholder="输入消息...Enter 发送",
            )
            yield Footer()

    def on_key(self, event: KeyEvent) -> None:
        if event.key == "b" and event.control:
            self._toggle_sidebar()
            event.prevent_default()
            event.stop()
            return

        if event.control and event.key in ['1', '2', '3', '4']:
            if event.key == '1':
                self.action_switch_to_file_tree()
            elif event.key == '2':
                self.action_switch_to_tasks()
            elif event.key == '3':
                self.action_switch_to_agent()
            elif event.key == '4':
                self.action_switch_to_logs()
            event.prevent_default()
            event.stop()

    def on_mount(self) -> None:
        self._logger.info("Textual UI mounted")
        
        # 注册自定义主题（Textual 8.x 需要手动注册）
        if TEXTUAL_AVAILABLE:
            for theme in THEMES:
                self.register_theme(theme)
            self._logger.info(f"Registered {len(THEMES)} themes: {[t.name for t in THEMES]}")
            
            # 设置默认主题为 "default"（紫色）
            self.theme = "default"
            self._logger.info(f"Set default theme to: {self.theme}")
        
        self._render_welcome_banner()
        self._update_status_bar()
        self._register_event_listeners()
        self.call_later(self._load_stylesheets)

        if self._tui_log_handler is not None:
            try:
                from textual.widgets import Log
                log_widget = self.query_one("#log-output", Log)
                self._tui_log_handler.set_widget(log_widget)
            except Exception:
                pass

        if self._theme_manager and self._theme_manager.is_transparency_enabled():
            self._logger.info("Applying saved transparency settings")
            self._update_transparency_styles(True)

        # 初始化 TUIConsumer 并注册到 Agent 的事件系统
        if TUIConsumer and self._agent is not None:
            try:
                self._tui_consumer = TUIConsumer(self)
                
                # 尝试获取 Agent 的 registry 并注册消费者
                if hasattr(self._agent, '_stream_emitter') and self._agent._stream_emitter is not None:
                    emitter = self._agent._stream_emitter
                    if hasattr(emitter, 'registry'):
                        emitter.registry.register(self._tui_consumer)
                        self._logger.info("TUIConsumer registered to agent registry")
                
                # 同时设置 TaskPlanner 的 emitter
                if hasattr(self._agent, '_task_planning_middleware') and self._agent._task_planning_middleware is not None:
                    planner = getattr(self._agent._task_planning_middleware, 'planner', None)
                    if planner and hasattr(planner, 'set_emitter'):
                        if hasattr(self._agent, '_stream_emitter'):
                            planner.set_emitter(self._agent._stream_emitter)
                            self._logger.info("TaskPlanner emitter set")
                            
            except Exception as e:
                self._logger.warning(f"Failed to initialize TUIConsumer: {e}")

        self.set_focus(self.query_one("#user-input", TextArea))

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
        self._logger.debug(f"[_apply_theme_class] Called, _theme_css_loaded={self._theme_css_loaded}, theme_id={self.theme_id}")

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
        self._logger.info(f"[SYNC] Theme CSS already preloaded, switching to: {theme_id}")

    def _on_theme_changed(self, theme_id: str) -> None:
        """主题变更回调（CSS 已预加载，只需更新 class）."""
        # CSS 在初始化时已全部预加载，这里只需更新 class
        self.theme_id = theme_id
        self._apply_theme_class()

    def update_theme_css(self) -> None:
        self._apply_theme_class()

    def action_toggle_dark_mode(self) -> None:
        if self.theme == "textual-dark":
            self.theme = "textual-light"
            self.notify("切换到浅色模式")
        else:
            self.theme = "textual-dark"
            self.notify("切换到深色模式")

    def _update_status_bar(self) -> None:
        try:
            icon_widget = self.query_one("#status-icon", Static)
            icon_widget.update("●")
            model_widget = self.query_one("#status-model", Static)
            model_widget.update(f" {self.model_name or 'Handsome Agent'} ")
            tokens_widget = self.query_one("#status-tokens", Static)
            if self.context_length:
                tokens_widget.update(f"│ 0/{self._format_context(self.context_length)} ")
            else:
                tokens_widget.update("│ n/a ")
            # 使用 Textual 原生 ProgressBar 组件
            progress_widget = self.query_one("#status-progress", ProgressBar)
            progress_widget.update(progress=0.0)
            time_widget = self.query_one("#status-time", Static)
            time_widget.update("│ 0m 0s ")
            tools_widget = self.query_one("#status-tools", Static)
            tools_widget.update("🔧")
        except Exception as e:
            self._logger.debug(f"Failed to update status bar: {e}")

    @on(SubmitTextArea.InputSubmitted)
    def _on_input_submitted(self, event: SubmitTextArea.InputSubmitted) -> None:
        text_area = self.query_one("#user-input", SubmitTextArea)
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
        self.call_later(lambda: self._call_agent_async(user_input))

    def _register_event_listeners(self) -> None:
        self._logger.debug("Event listeners registered (using @on decorators)")

    def _start_loading_animation(self) -> None:
        if self._is_loading:
            return
        self._is_loading = True
        
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
            # 使用原有的状态栏加载动画
            self._loading_frame_index = 0
            self._update_loading_frame()

    def _stop_loading_animation(self) -> None:
        self._is_loading = False
        
        if self._use_native_loading and self._loading_indicator is not None:
            # 移除 Textual 原生 LoadingIndicator
            try:
                self._loading_indicator.remove()
                self._loading_indicator = None
            except Exception:
                pass
        else:
            # 使用原有的状态栏加载动画
            try:
                status_icon = self.query_one("#status-icon", Static)
                status_icon.update("●")
            except Exception:
                pass

    def _toggle_sidebar(self) -> None:
        sidebar = self.query_one("#sidebar-container", Container)

        if sidebar.styles.display == "none":
            sidebar.styles.display = "block"
            self.notify("侧边栏已显示")
        else:
            sidebar.styles.display = "none"
            self.notify("侧边栏已隐藏")

    def _update_loading_frame(self) -> None:
        if not self._is_loading:
            return
        status_icon = self.query_one("#status-icon", Static)
        status_icon.update(self._loading_frames[self._loading_frame_index])
        self._loading_frame_index = (self._loading_frame_index + 1) % len(self._loading_frames)
        self.set_timer(0.2, self._update_loading_frame)

    def set_loading_style(self, style: str) -> bool:
        if style in self._LOADING_FRAMES:
            self._loading_style = style
            self._loading_frames = self._LOADING_FRAMES[style]
            self._loading_frame_index = 0
            self._logger.debug(f"Loading style changed to: {style}")
            return True
        return False

    def cycle_loading_style(self) -> str:
        styles = list(self._LOADING_FRAMES.keys())
        current_index = styles.index(self._loading_style) if self._loading_style in styles else 0
        next_index = (current_index + 1) % len(styles)
        next_style = styles[next_index]
        self.set_loading_style(next_style)
        return next_style

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

        chat_area = self.query_one("#chat-area", ChatView)
        chat_area.mount(streaming_widget)

        self._streaming_timer = self.set_interval(
            self._streaming_delay_ms / 1000.0,
            self._update_typewriter_frame
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

        current_displayed = getattr(self, '_streaming_displayed', 0)
        chars_to_add = self._streaming_chars_per_tick
        end_index = min(current_displayed + chars_to_add, len(self._streaming_text))
        new_chars = self._streaming_text[current_displayed:end_index]

        if new_chars:
            self._streaming_current_content += new_chars
            streaming_widget.update(self._streaming_current_content)
            self._streaming_displayed = end_index

        try:
            chat_area = self.query_one("#chat-area", ChatView)
            if hasattr(chat_area, 'scroll_home'):
                chat_area.scroll_home(animate=False)
            elif hasattr(chat_area, 'scroll_to'):
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

        full_content = getattr(self, '_streaming_current_content', "") or ""
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

    def _render_welcome_banner(self) -> None:
        # 根据主题 ID 确定 Banner 颜色
        # default: 紫色, awesome: 绿色
        banner_color = "#C9A0E0" if self.theme_id == "default" else "#C5FF9E"
        secondary_color = "#8b949e"

        # 渲染左侧 ASCII Banner
        welcome_lines = [
            f"[bold {banner_color}]░█░█░█▀█░█▀█░█▀▄░█▀▀░█▀█░█▄█░█▀▀[/]",
            f"[bold {banner_color}]░█▀█░█▀█░█░█░█░█░▀▀█░█░█░█░█░█▀▀[/]",
            f"[bold {banner_color}]░▀░▀░▀░▀░▀░▀░▀▀░░▀▀▀░▀▀▀░▀░▀░▀▀▀[/]",
        ]

        welcome_widget = self.query_one("#welcome-banner")
        if welcome_widget:
            from rich.text import Text as RichText
            welcome_text = RichText.from_markup("\n".join(welcome_lines))
            welcome_widget.update(welcome_text)

        # 渲染右侧信息栏
        from rich.text import Text as RichText

        # 版本信息 + 项目路径
        version_widget = self.query_one("#version-info")
        if version_widget:
            from cli import __version__ as app_version
            project_path = self._get_project_path()
            version_text = RichText.from_markup(f"[dim]{app_version}[/] [bright_black]@[/] [bright_black]{project_path}[/]")
            version_widget.update(version_text)

        # Skill 数量 + 路径
        skills_widget = self.query_one("#skills-info")
        if skills_widget:
            skills_count = self._get_skills_count()
            skills_path = self._get_skills_path()
            skills_text = RichText.from_markup(f"[bold #f0c040]⭐[/] [dim]{skills_count}[/] [bright_black]@[/] [bright_black]{skills_path}[/]")
            skills_widget.update(skills_text)

        # 工具数量 + 路径
        tools_widget = self.query_one("#tools-info")
        if tools_widget:
            tools_count = self._get_tools_count()
            tools_path = self._get_tools_path()
            tools_text = RichText.from_markup(f"[bold #58a6ff]🔧[/] [dim]{tools_count}[/] [bright_black]@[/] [bright_black]{tools_path}[/]")
            tools_widget.update(tools_text)

    def _get_tools_count(self) -> int:
        """获取已注册的工具数量"""
        try:
            from tools.tool_registry import get_tool_registry
            registry = get_tool_registry()
            if registry:
                return len(registry._tools) if hasattr(registry, '_tools') else 0
        except ImportError:
            pass
        return 0

    def _get_skills_count(self) -> int:
        """获取已加载的 Skill 数量"""
        try:
            from skills.skill_loader import get_skill_loader
            loader = get_skill_loader()
            if loader:
                return len(loader._skills) if hasattr(loader, '_skills') else 0
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

    def _init_keybinding_manager(self) -> None:
        self._key_binding_manager = KeyBindingManager()

        if create_default_keybindings:
            bindings = create_default_keybindings(
                on_new_tab=self.action_new_tab,
                on_close_tab=self.action_close_tab,
                on_next_tab=self.action_next_tab,
                on_prev_tab=self.action_prev_tab,
                on_open_command_palette=self.action_open_command_palette,
                on_scroll_up=self.action_scroll_up,
                on_scroll_down=self.action_scroll_down,
                on_open_help=self.action_open_help,
                on_open_session_selector=self.action_open_session_selector,
                on_clear_screen=self.action_clear_screen,
                on_quit=self.action_quit,
            )
            self._key_binding_manager.register_batch(bindings)

        self._logger.debug("KeyBindingManager initialized")

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
                self._logger.info(f"ApprovalManager initialized with mode: {mode.value}")
            except Exception as e:
                self._logger.error(f"Failed to initialize ApprovalManager: {e}")
                self._approval_manager = None

    def set_theme(self, theme_id: str) -> bool:
        if not self._theme_manager:
            self._logger.warning("Theme manager not available")
            return False

        success = self._theme_manager.set_theme(theme_id)
        if success:
            display_name = self._theme_manager.get_current_display_name()
            self.notify(f"Theme changed to: {display_name}")
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

    def action_change_theme(self) -> None:
        """使用 Textual 主题系统切换主题."""
        if not TEXTUAL_AVAILABLE:
            self.notify("Theme system not available")
            return

        # 获取我们支持的主题列表
        theme_ids = [t.name for t in THEMES]
        if not theme_ids:
            self.notify("No themes available")
            return

        # 获取当前主题（可能是 textual-dark 或我们自定义的主题）
        current_theme = self.theme
        
        # 如果当前主题不在我们的列表中，尝试在 available_themes 中查找
        if current_theme not in theme_ids:
            self._logger.info(f"[action_change_theme] current '{current_theme}' not in {theme_ids}")
            # 尝试在可用主题中查找我们的主题
            if current_theme in self.available_themes:
                # 当前是 Textual 内置主题，切换到我们的第一个主题
                current_index = -1  # 这样下一个会是 index 0
            else:
                current_index = -1
        else:
            current_index = theme_ids.index(current_theme)
        
        next_index = (current_index + 1) % len(theme_ids)
        next_theme_id = theme_ids[next_index]
        
        self._logger.info(f"[action_change_theme] switching from '{current_theme}' to '{next_theme_id}'")
        
        # 使用 Textual 主题系统切换主题
        self.theme = next_theme_id
        
        self._logger.info(f"[action_change_theme] after switch: {self.theme}")
        
        # 保存主题偏好
        if self._theme_manager:
            self._theme_manager.set_theme(next_theme_id)
        
        # 显示通知
        self.notify_success(f"Theme: {next_theme_id}", duration=2.0)

    def action_toggle_transparency(self) -> None:
        if not self._theme_manager:
            self.notify("Theme manager not available")
            return

        enabled = self._theme_manager.toggle_transparency()
        self._update_transparency_styles(enabled)

        if enabled:
            self.notify("✓ 半透明背景已启用 (毛玻璃效果)")
        else:
            self.notify("✗ 半透明背景已禁用")

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

    def action_toggle_markdown(self) -> None:
        self._markdown_enabled = not self._markdown_enabled

        if self._markdown_enabled:
            if TEXTUAL_AVAILABLE and Markdown is not None:
                self.notify_info("✓ Markdown 渲染已启用")
            else:
                self.notify_warning("Textual Markdown 组件不可用")
        else:
            self.notify_info("✗ Markdown 渲染已禁用")

        self._logger.debug(f"Markdown rendering: {self._markdown_enabled}")

    def is_markdown_enabled(self) -> bool:
        return self._markdown_enabled

    def is_markdown_available(self) -> bool:
        """检查 Textual 原生 Markdown 组件是否可用."""
        return TEXTUAL_AVAILABLE and Markdown is not None

    def get_markdown_features(self) -> dict:
        """获取 Markdown 功能特性."""
        return {
            "textual_markdown": TEXTUAL_AVAILABLE and Markdown is not None,
        }

    def action_toggle_loading_style(self) -> None:
        """切换加载动画样式（原生 LoadingIndicator / 状态栏动画）."""
        self._use_native_loading = not self._use_native_loading
        
        if self._use_native_loading:
            self.notify_info("✓ 使用原生 LoadingIndicator")
        else:
            self.notify_info("✓ 使用状态栏加载动画")

    def set_use_native_loading(self, use_native: bool) -> None:
        """设置是否使用原生 LoadingIndicator.
        
        Args:
            use_native: True 使用原生 LoadingIndicator，False 使用状态栏动画
        """
        self._use_native_loading = use_native

    def render_markdown(self, text: str) -> str:
        """使用 Textual 原生 Markdown 组件渲染文本.
        
        Args:
            text: Markdown 格式的文本
            
        Returns:
            渲染后的 Rich 格式文本
        """
        if not self._markdown_enabled:
            return text

        try:
            return self._render_markdown_content(text)
        except Exception as e:
            self._logger.debug(f"Markdown render failed: {e}")
            return text

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
            title=notification_type.upper() if notification_type != NotificationType.INFO else "通知",
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

        risk_level = self._approval_manager.get_risk_level(tool_name) if self._approval_manager else RiskLevel.MEDIUM
        preview = self._generate_tool_preview(tool_name, tool_args)

        dialog = create_approval_dialog(
            operation=tool_name,
            preview=preview,
            risk_level=risk_level,
        )

        self._logger.info(f"Showing approval dialog for: {tool_name} (risk: {risk_level.value})")
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
            operation = self._pending_tool_call["name"] if self._pending_tool_call else "unknown"
            self._logger.info(f"Approval result for '{operation}': {'approved' if approved else 'rejected'}")

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
            return [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]
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
                **kwargs
            )
            self._auto_save_check()
        except Exception as e:
            self._logger.error(f"Failed to save message: {e}")

    def on_unmount(self) -> None:
        self._flush_messages()
        self._logger.debug("Application unmounted, data saved")
        self._restore_console_handler()

    def _restore_console_handler(self) -> None:
        if self._tui_log_handler is not None and self._saved_console_handler is not None:
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
                self._logger.debug(f"Sidebar toggled, display: {sidebar.styles.display}")
        except Exception as e:
            self._logger.debug(f"Sidebar toggle failed: {e}")

    def _get_sidebar_and_switch(self, panel_type: str) -> None:
        try:
            sidebar = self.query_one("#sidebar-container")
            if sidebar.styles.display == "none":
                sidebar.styles.display = "block"
        except:
            pass

        self._on_sidebar_panel_switch(panel_type)

    def action_switch_to_file_tree(self) -> None:
        self._get_sidebar_and_switch("file_tree")

    def action_switch_to_tasks(self) -> None:
        self._get_sidebar_and_switch("tasks")

    def action_switch_to_agent(self) -> None:
        self._get_sidebar_and_switch("agent")

    def action_switch_to_logs(self) -> None:
        self._get_sidebar_and_switch("logs")

    def set_agent_status(self, status: str) -> None:
        self._agent_status = status
        self._logger.debug(f"Agent status changed to: {status}")

    def action_toggle_help(self) -> None:
        self.action_open_help()

    def action_open_help(self) -> None:
        if HelpScreen:
            self.push_screen(HelpScreen(
                key_binding_manager=self._key_binding_manager
            ))
            self._logger.debug("Help screen opened")
        else:
            self.notify("Help: q=quit, Ctrl+B=sidebar, Ctrl+T=new tab")

    def action_open_command_palette(self) -> None:
        if CommandPaletteScreen:
            self.push_screen(CommandPaletteScreen())
            self._logger.debug("Command palette opened")
        else:
            self.notify("Command palette not available")

    def action_open_session_selector(self) -> None:
        if SessionPickerScreen:
            self.push_screen(SessionPickerScreen(
                current_session_id=self.session_id
            ))
            self._logger.debug("Session picker opened")
        else:
            self.notify(t("tui.session_selector.hint", "Session selector not available"))

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
    
    def _append_message(self, role: str, content: str, render_markdown: bool = True) -> None:
        chat_area = self.query_one("#chat-area", ChatView)

        # ChatView 使用 append_message 正确传递 role
        if hasattr(chat_area, 'append_message'):
            chat_area.append_message(role, content)
        elif hasattr(chat_area, 'write'):
            chat_area.write(f"{content}\n")

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
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        self.set_agent_status("busy")
        self._start_loading_animation()

        def run_agent():
            try:
                agent = self._get_agent()
                if agent:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        response = agent.chat(user_input)
                        if asyncio.iscoroutine(response):
                            response = loop.run_until_complete(response)
                        return response
                    finally:
                        loop.close()
                else:
                    return "Agent 未初始化，请检查配置"
            except Exception as e:
                return f"错误: {str(e)}"

        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(run_agent)
        executor.shutdown(wait=False)

        self._agent_future = future
        self._agent_start_time = __import__("time").time()

        if hasattr(self, '_poll_timer') and self._poll_timer is not None:
            self._poll_timer.stop()

        self._poll_timer = self.set_interval(0.3, self._poll_agent_result)

    def _poll_agent_result(self) -> None:
        import time
        future = getattr(self, '_agent_future', None)
        if future is None:
            return

        if future.done():
            self._poll_timer.stop()
            self._poll_timer = None

            self._stop_loading_animation()
            self.set_agent_status("online")

            elapsed = time.time() - getattr(self, '_agent_start_time', time.time())
            elapsed_minutes = int(elapsed // 60)
            elapsed_seconds = int(elapsed % 60)

            try:
                response = future.result()
                if response:
                    if hasattr(response, 'content'):
                        content = str(response.content)
                    else:
                        content = str(response)
                else:
                    content = "（无回复）"

                self._show_typewriter_message(content)

                try:
                    time_widget = self.query_one("#status-time", Static)
                    time_widget.update(f"│ {elapsed_minutes}m {elapsed_seconds}s ")
                except Exception:
                    pass
            except Exception as e:
                self._stop_loading_animation()
                self.set_agent_status("error")
                self._append_message("system", f"❌ 处理失败: {str(e)}")

            self._agent_future = None
            return

        if time.time() - getattr(self, '_agent_start_time', time.time()) > 60:
            self._poll_timer.stop()
            self._poll_timer = None
            self._append_message("system", "⏱️ 处理超时，请重试")
            self._agent_future = None

    def _get_agent(self):
        if hasattr(self, '_agent') and self._agent:
            return self._agent
        return getattr(self, '_agent', None)

    def _show_typewriter_message(self, content: str) -> None:
        # 流式输出暂不支持 ChatView，直接写入
        chat_area = self.query_one("#chat-area", ChatView)
        if chat_area:
            if hasattr(chat_area, 'write'):
                chat_area.write(f"\nAgent: {content}\n")

    def action_clear_screen(self) -> None:
        chat_area = self.query_one("#chat-area", ChatView)
        if chat_area:
            if hasattr(chat_area, 'clear'):
                chat_area.clear()
            elif hasattr(chat_area, 'clear_messages'):
                chat_area.clear_messages()
        self._logger.debug("Screen cleared")

    def action_cancel_current(self) -> None:
        self._logger.info("User requested cancel current operation")
        try:
            input_field = self.query_one("#user-input", TextArea)
            input_field.text = ""
            self.set_focus(input_field)
        except:
            pass
        self.notify("已取消当前操作")

    def action_quit(self) -> None:
        self._logger.info("User requested quit")
        self.app.exit()

    def _on_session_selected(self, event: "SessionPickerScreen.SessionSelected") -> None:
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

        self.notify(t("session.switched", "已切换到会话: {title}").format(title=event.session_title))

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

        self._logger.info(f"Session deleted: {event.session_id}")

    def action_scroll_up(self) -> None:
        try:
            content_area = self.query_one("#content-area", VerticalScroll)
            content_area.scroll_up(animate=True)
        except Exception:
            pass

    def action_scroll_down(self) -> None:
        try:
            content_area = self.query_one("#content-area", VerticalScroll)
            content_area.scroll_down(animate=True)
        except Exception:
            pass

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
            if hasattr(chat_area, 'write'):
                chat_area.write(f"{label}: {content}\n")
            elif hasattr(chat_area, 'append_message'):
                chat_area.append_message(role, content)

    def clear_chat(self) -> None:
        chat_area = self.query_one("#chat-area", ChatView)
        if chat_area:
            if hasattr(chat_area, 'clear'):
                chat_area.clear()
            elif hasattr(chat_area, 'clear_messages'):
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
]


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
