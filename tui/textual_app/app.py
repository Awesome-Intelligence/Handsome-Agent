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
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from .imports import (
    TEXTUAL_AVAILABLE,
    _TEXTUAL_IMPORT_ERROR,
    App,
    ComposeResult,
    Header,
    Footer,
    Static,
    RichLog,
    TextArea,
    Button,
    Markdown,
    LoadingIndicator,
    Select,
    Input,
    Binding,
    Container,
    Vertical,
    Horizontal,
    TextualScreen,
    Message,
    on,
    Key,
    Click,
    textual_events,
    NewLine,
    KeyEvent,
    RichText,
    Style,
    estimate_messages_tokens_rough,
    ChatContainer,
    SessionPickerScreen,
    SidebarContainer,
    TUIConsumer,
    ApprovalDialog,
    ApprovalMode,
    RiskLevel,
    ApprovalManager,
    ApprovalConfirmed,
    ApprovalRejected,
    create_approval_dialog,
    SessionStore,
    HelpScreen,
    FilePreviewScreen,
    SettingsScreen,
    LogScreen,
    get_stylesheets,
    get_i18n,
    t,
    get_access_logger,
    LogManager,
    _patch_textual_logger,
)

if TYPE_CHECKING:
    from textual.widget import Widget

from .actions import ActionsMixin
from .agent_runner import AgentRunnerMixin
from .approval import ApprovalMixin
from .banner import BannerMixin
from .greeting import GreetingMixin
from .wisdom import WisdomMixin
from .css import APP_CSS
from .helpers import CompatibleLog, LogDescriptor, _COMPATIBLE_LOG
from .loading import LoadingMixin
from .log_handler import TuiLogHandler
from .model_selector import ModelSelectorMixin
from .notifications import NotifyMixin, NotificationType
from .session import SessionMixin
from .sidebar_panels import SidebarPanelMixin
from .slash_completion_bind import SlashCompletionMixin
from .status_bar import StatusBarMixin
from .text_area import SubmitTextArea
from .screens import CustomModelInputScreen
from tui.widgets.slash_completion import SlashCompletionList

from .constants import (
    PURPLE_PRIMARY,
    PURPLE_BRIGHT,
    PURPLE_DIM,
    PURPLE_DARK,
    WHITE,
    GRAY_DIM,
    GOLD,
    STATUS_ONLINE,
    STATUS_BUSY,
    STATUS_ERROR,
)

_patch_textual_logger()

# ponytail: 直接用 Textual 内置主题列表（22 个），自定义主题已删。
THEME_CYCLE: list[str] = []
if TEXTUAL_AVAILABLE:
    try:
        from textual.theme import BUILTIN_THEMES
        THEME_CYCLE = list(BUILTIN_THEMES.keys())
    except ImportError:
        THEME_CYCLE = ["textual-dark"]


class AgentApp(
    StatusBarMixin,
    BannerMixin,
    GreetingMixin,
    WisdomMixin,
    ModelSelectorMixin,
    ApprovalMixin,
    NotifyMixin,
    SessionMixin,
    AgentRunnerMixin,
    SidebarPanelMixin,
    ActionsMixin,
    LoadingMixin,
    SlashCompletionMixin,
    App,
):
    """Agent Textual TUI Application.

    v8.x 重构：主类瘦身到只剩生命周期编排。所有职责已下放到
    ``tui/textual_app/*.py`` 下的 mixin 模块。

    Mixin 继承顺序（从左到右优先级递减）：
      StatusBar → Banner → Greeting → Wisdom →
      ModelSelector → Approval → Notify → Session → AgentRunner →
      SidebarPanel → Actions → Loading → SlashCompletion → App
    """
    log = LogDescriptor()
    BINDINGS = [Binding('ctrl+q', 'quit', 'Quit'), Binding('ctrl+c', 'copy', 'Copy'), Binding('ctrl+b', 'toggle_sidebar', 'Sidebar'), Binding('f1', 'open_help', 'Help'), Binding('f2', 'open_settings', 'Settings'), Binding('f3', 'open_log_screen', 'Logs'), Binding('ctrl+left', 'prev_panel', 'Prev Panel', show=False), Binding('ctrl+right', 'next_panel', 'Next Panel', show=False)]
    CSS = APP_CSS
    if TEXTUAL_AVAILABLE:
        # ponytail: Textual 内置主题自动注册；自定义主题已删除。
        # 不用类型注解（避免遮蔽父类 Reactive descriptor）。
        theme = "textual-dark"

    def __init__(self, model_name: str='Agent', provider: str | None=None, cwd: str | None=None, session_id: str | None=None, context_length: int | None=None, approval_mode: str | ApprovalMode='suggest', agent=None, **kwargs):
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
        if context_length is None:
            try:
                from common.config import get_model_config
                context_length = get_model_config().context_window
            except Exception:
                context_length = None
        self.context_length = context_length
        self._logger = get_access_logger('TextualUI', sublayer='tui')
        # LoadingMixin 中 _STATUS_ICONS 是 🟢/⏳，主类这里覆盖为表情脸版本（保持原有视觉）
        self._STATUS_ICONS = {'online': '😄', 'busy': ['🤔', '🤨', '😲', '🤯'], 'warning': '😕', 'error': '😐'}
        self._is_streaming: bool = False
        self._agent = agent
        # Session / Approval 动态初始化钩子
        self._init_session_store()
        self._init_approval_manager(approval_mode)
        # Banner cache 特定结构（不同于 BannerMixin 的空 {}，不能删）
        self._builtin_models: list[tuple[str, str]] = self._get_configured_models()
        self._banner_cache: dict = {
            'project_path': None, 'skills_path': None, 'tools_path': None,
            'skills_count': None, 'tools_count': None, 'version': None,
        }
        # 主类独有属性（mixin 中未定义）
        self._tui_consumer: Optional['TUIConsumer'] = None
        self._agent_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='agent-worker')

    def compose(self) -> ComposeResult:
        with Container(id='app-header'):
            with Horizontal():
                yield Static('', id='welcome-banner')
                with Vertical(id='header-info-right'):
                    yield Static('', id='version-info')
                    yield Static('', id='skills-info')
                    yield Static('', id='tools-info')
                yield Static('►', id='theme-toggle', classes='theme-toggle')
        with Horizontal(id='main-area'):
            if ChatContainer:
                yield ChatContainer(id='chat-area')
            if SidebarContainer:
                with Container(id='sidebar-container'):
                    goal_manager = getattr(self._agent, '_goal_manager', None) if self._agent else None
                    yield SidebarContainer(cwd=self.cwd, agent=self._agent, goal_manager=goal_manager)
        with Container(id='input-area'):
            with Container(id='status-bar'):
                with Horizontal(id='status-content'):
                    yield Static('●', id='status-icon', classes='status-icon')
                    yield Select(id='status-model', classes='status-model', options=self._builtin_models, allow_blank=False, compact=True)
                    yield Static('0/128K', id='status-tokens', classes='status-tokens')
                    yield Static('0:00', id='status-time', classes='status-time')
                    yield Static('🔧', id='status-tools', classes='status-tools')
                    yield Static('', id='status-queue', classes='status-queue')
                    with Horizontal(id='status-right'):
                        yield Static(t('tui.status_bar.mode_iter'), id='status-mode-toggle', classes='status-mode-toggle')
            yield SubmitTextArea(id='user-input', classes='input-field', placeholder=t('tui.input.placeholder', '输入消息...Enter 发送'))
            yield Footer()
            yield SlashCompletionList(id='slash-completion')

    def on_mount(self) -> None:
        self._logger.info('Textual UI mounted')
        self._cache_widgets()
        self._render_welcome_banner()
        self._update_status_bar()
        self._update_theme_toggle_label()
        self._update_theme_toggle_tooltip()
        self.call_later(self._generate_wisdom_async)
        self.call_later(self._send_welcome_message)
        self._register_event_listeners()
        self.call_later(self._load_stylesheets)
        self.call_later(self._init_model_select)
        if TUIConsumer and self._agent is not None:
            try:
                self._tui_consumer = TUIConsumer()
                if hasattr(self._agent, '_stream_emitter') and self._agent._stream_emitter is not None:
                    emitter = self._agent._stream_emitter
                    if hasattr(emitter, 'registry'):
                        emitter.registry.register(self._tui_consumer)
                        self._logger.info('TUIConsumer registered to agent registry')
            except Exception as e:
                self._logger.warning(f'Failed to initialize TUIConsumer: {e}')
        try:
            from tui.services.session_store import SessionStore
            session_store = SessionStore()
            persisted_history = session_store.load_input_history(limit=100)
            if persisted_history:
                self._input_history = persisted_history
                self._logger.info(f'Loaded {len(persisted_history)} persisted input history items')
        except Exception as e:
            self._logger.warning(f'Failed to load persisted input history: {e}')
        if SubmitTextArea is not None:
            try:
                text_area = self.query_one('#user-input', SubmitTextArea)
                text_area.history_navigate = self._navigate_input_history
            except Exception as e:
                self._logger.warning(f'Failed to wire up history navigation: {e}')
        self._bind_slash_completion()
        self.set_focus(self.query_one('#user-input', TextArea))
        self.call_later(self._update_token_count)

    async def _load_stylesheets(self) -> None:
        if get_stylesheets is None:
            self._logger.debug('CSS module not available, using inline CSS')
            return
        try:
            stylesheets = get_stylesheets()
            for css_file in stylesheets:
                css_path = Path(css_file)
                if css_path.exists():
                    await self.add_stylesheet(str(css_path))
                    self._logger.debug(f'Loaded stylesheet: {css_path.name}')
                else:
                    self._logger.debug(f'Stylesheet not found: {css_path}')
        except Exception as e:
            self._logger.debug(f'Failed to load stylesheets: {e}')

    def _on_theme_toggle_click(self) -> None:
        """点击 #theme-toggle 时切换 Textual 内置主题。"""
        if not THEME_CYCLE:
            self._logger.warning('No themes available to toggle')
            return
        try:
            current = self.theme if isinstance(self.theme, str) else 'textual-dark'
            i = THEME_CYCLE.index(current) if current in THEME_CYCLE else -1
            self.theme = THEME_CYCLE[(i + 1) % len(THEME_CYCLE)]
            self._logger.info(f'Theme switched to: {self.theme}')
            self._update_theme_toggle_label()
            # ponytail: Textual 不自动刷新已挂载 ModalScreen（如 LogScreen / SessionPicker）
            # 的 $primary/$accent 变量，主动 refresh_css 让所有 screen 同时切色。
            self.refresh_css(animate=False)
            self.notify_animated(
                t('tui.theme.switched', '主题已切换: {theme}', theme=self.theme),
                NotificationType.INFO,
            )
        except Exception as e:
            self._logger.warning(f'Theme toggle failed: {e}')

    def _update_theme_toggle_label(self) -> None:
        """确保 #theme-toggle 显示三角符号（固定图标，不随主题变化）。"""
        try:
            widget = self._widget_cache.get('theme_toggle')
            if widget is None:
                widget = self.query_one('#theme-toggle', Static)
                self._widget_cache['theme_toggle'] = widget
            widget.update('►')
        except Exception:
            pass

    def _update_theme_toggle_tooltip(self) -> None:
        """更新主题切换按钮的 tooltip."""
        theme_toggle = self._widget_cache.get('theme_toggle')
        if theme_toggle is None:
            try:
                theme_toggle = self.query_one('#theme-toggle', Static)
                self._widget_cache['theme_toggle'] = theme_toggle
            except Exception:
                return
        theme_toggle.tooltip = t('tui.command.toggle_theme')

    @on(Click, '#theme-toggle')
    def _handle_theme_toggle_click(self, _event: Click) -> None:
        """处理 #theme-toggle 点击事件."""
        self._on_theme_toggle_click()

    def _update_token_count(self) -> None:
        """更新 token 计数（方案B：消息完成后估算，不影响性能）."""
        if not estimate_messages_tokens_rough:
            self._logger.info('[token_count] estimate_messages_tokens_rough not available')
            return
        if not self._session_store:
            self._logger.info('[token_count] _session_store not available')
            return
        if not self.session_id:
            self._logger.info('[token_count] session_id not available')
            return
        try:
            messages = self._session_store.get_messages(self.session_id, limit=1000)
            self._logger.info(f'[token_count] got {len(messages)} messages')
            message_dicts = [{'role': msg.role, 'content': msg.content or ''} for msg in messages]
            self._current_token_count = estimate_messages_tokens_rough(message_dicts)
            self._logger.info(f'[token_count] estimated: {self._current_token_count}')
            tokens_widget = self._widget_cache.get('status_tokens')
            if tokens_widget and self.context_length:
                tokens_widget.update(f'│ {self._format_context(self._current_token_count)}/{self._format_context(self.context_length)} ')
        except Exception as e:
            self._logger.info(f'[token_count] Failed: {e}')

    @on(SubmitTextArea.InputSubmitted)
    def _on_input_submitted(self, event: SubmitTextArea.InputSubmitted) -> None:
        self._dismiss_slash_palette()
        text_area = self._widget_cache.get('user_input')
        if text_area is None:
            text_area = self.query_one('#user-input', SubmitTextArea)
        user_input = text_area.text.strip()
        if not user_input:
            return
        if self._agent_busy:
            self._pending_queue.append(user_input)
            queue_len = len(self._pending_queue)
            text_area.disabled = True
            self._update_queue_display()
            self.notify_animated(t('tui.queue.message_queued', '消息已加入队列 (排队中: {n}条)', n=queue_len), NotificationType.INFO)
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
                self._logger.warning(f'Failed to save input history: {e}')
        self._history_index = -1
        self._current_input = ''
        text_area.text = ''
        self._append_message('user', user_input)
        self._logger.debug(f'User input: {user_input[:50]}...')
        self._agent_busy = True
        self.call_later(lambda: self._call_agent_async(user_input))

    def _register_event_listeners(self) -> None:
        pass

    def _toggle_sidebar(self) -> None:
        sidebar = self.query_one('#sidebar-container', Container)
        if sidebar.styles.display == 'none':
            sidebar.styles.display = 'block'
            self.notify('侧边栏已显示')
        else:
            sidebar.styles.display = 'none'
            self.notify('侧边栏已隐藏')

    def start_streaming_message(self, widget_id: str) -> None:
        """兼容旧 API：把流开始转发给 ChatContainer。

        老版本向 RichLog widget 写入；新版不再维护独立 typewriter 路径，
        一律走 ChatContainer.start_streaming。
        """
        chat_area = self._widget_cache.get('chat_area')
        if chat_area is None and ChatContainer is not None:
            try:
                chat_area = self.query_one('#chat-area', ChatContainer)
            except Exception:
                chat_area = None
        if chat_area is not None:
            chat_area.start_streaming('assistant')
            self._is_streaming = True

    def append_streaming_text(self, text: str) -> None:
        """兼容旧 API：把 delta 转发给 ChatContainer。"""
        if not text:
            return
        chat_area = self._widget_cache.get('chat_area')
        if chat_area is None and ChatContainer is not None:
            try:
                chat_area = self.query_one('#chat-area', ChatContainer)
            except Exception:
                chat_area = None
        if chat_area is not None:
            if not getattr(self, '_is_streaming', False):
                chat_area.start_streaming('assistant')
                self._is_streaming = True
            chat_area.append_streaming_text(text)

    def is_streaming(self) -> bool:
        """当前是否在流式输出。委托给 ChatContainer。"""
        chat_area = self._widget_cache.get('chat_area')
        if chat_area is None and ChatContainer is not None:
            try:
                chat_area = self.query_one('#chat-area', ChatContainer)
            except Exception:
                chat_area = None
        if chat_area is None:
            return False
        return bool(chat_area.is_streaming())

    def cancel_streaming(self) -> None:
        """取消流；委托给 ChatContainer。"""
        chat_area = self._widget_cache.get('chat_area')
        if chat_area is None and ChatContainer is not None:
            try:
                chat_area = self.query_one('#chat-area', ChatContainer)
            except Exception:
                chat_area = None
        if chat_area is not None:
            chat_area.cancel_streaming()
        self._is_streaming = False

    def _cache_widgets(self) -> None:
        """缓存常用 Widget 引用（优化性能，避免频繁 query_one）"""
        try:
            self._widget_cache['status_icon'] = self.query_one('#status-icon', Static)
            self._widget_cache['status_model'] = self.query_one('#status-model', Select)
            self._widget_cache['status_tokens'] = self.query_one('#status-tokens', Static)
            self._widget_cache['status_time'] = self.query_one('#status-time', Static)
            self._widget_cache['status_tools'] = self.query_one('#status-tools', Static)
            self._widget_cache['status_queue'] = self.query_one('#status-queue', Static)
            self._widget_cache['status_mode_toggle'] = self.query_one('#status-mode-toggle', Static)
            self._widget_cache['status_bar'] = self.query_one('#status-bar')
            self._widget_cache['chat_area'] = self.query_one('#chat-area', ChatContainer)
            self._widget_cache['user_input'] = self.query_one('#user-input', TextArea)
            self._widget_cache['welcome_banner'] = self.query_one('#welcome-banner', Static)
            self._widget_cache['version_info'] = self.query_one('#version-info', Static)
            self._widget_cache['skills_info'] = self.query_one('#skills-info', Static)
            self._widget_cache['tools_info'] = self.query_one('#tools-info', Static)
            self._widget_cache['theme_toggle'] = self.query_one('#theme-toggle', Static)
            try:
                self._widget_cache['sidebar_container'] = self.query_one('#sidebar-container', Container)
            except Exception:
                pass
            self._logger.debug(f'Cached {len(self._widget_cache)} widgets')
        except Exception as e:
            self._logger.warning(f'Failed to cache widgets: {e}')

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
        try:
            widget = self.query_one(f'#{key}' if not key.startswith('#') else key, widget_class)
            self._widget_cache[key] = widget
            return widget
        except Exception:
            return None

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
            from agent.skills.skill_manager import skill_manager
            return len(skill_manager.skills)
        except ImportError:
            pass
        return 0

    def _get_project_path(self) -> str:
        """获取项目根目录（Agent-Z 所在目录）"""
        from pathlib import Path
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent
        return str(project_root)

    def _get_skills_path(self) -> str:
        """获取 skills 目录路径"""
        from pathlib import Path
        project_root = Path(__file__).resolve().parent.parent.parent
        skills_dir = project_root / 'skills'
        return str(skills_dir)

    def _get_tools_path(self) -> str:
        """获取 tools 目录路径"""
        from pathlib import Path
        project_root = Path(__file__).resolve().parent.parent.parent
        tools_dir = project_root / 'tools'
        return str(tools_dir)

    def _format_context(self, tokens: int | None) -> str:
        if not tokens:
            return '?'
        if tokens >= 1000000:
            val = tokens / 1000000
            rounded = round(val)
            if abs(val - rounded) < 0.05:
                return f'{rounded}M'
            return f'{val:.1f}M'
        elif tokens >= 1000:
            val = tokens / 1000
            rounded = round(val)
            if abs(val - rounded) < 0.05:
                return f'{rounded}K'
            return f'{val:.1f}K'
        return str(tokens)

    def _init_approval_manager(self, approval_mode: str | ApprovalMode) -> None:
        if ApprovalManager:
            try:
                if isinstance(approval_mode, str):
                    mode = ApprovalMode.from_string(approval_mode)
                else:
                    mode = approval_mode
                self._approval_manager = ApprovalManager(mode=mode)
                self._logger.info(f'ApprovalManager initialized with mode: {mode.value}')
            except Exception as e:
                self._logger.error(f'Failed to initialize ApprovalManager: {e}')
                self._approval_manager = None

    def on_unmount(self) -> None:
        if getattr(self, '_agent_executor', None) is not None:
            try:
                self._agent_executor.shutdown(wait=True, cancel_futures=True)
            except Exception as e:
                self._logger.debug(f'agent executor shutdown failed: {e}')
            self._agent_executor = None
        self._flush_messages()
        self._logger.debug('Application unmounted, data saved')
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

    def _on_session_selected(self, event: 'SessionPickerScreen.SessionSelected') -> None:
        old_session_id = self.session_id
        self.session_id = event.session_id
        self._logger.info(f'Session switched: {old_session_id} -> {event.session_id}')
        self._render_welcome_banner()
        chat_view = self.query_one('#chat-area', ChatContainer)
        chat_view.clear_messages()
        history = self._restore_session(event.session_id)
        for msg in history:
            chat_view.append_message(msg['role'], msg['content'], thinking=msg.get('thinking'))
        if not history:
            chat_view.show_greeting()
        self.notify(t('session.switched', '已切换到会话: {title}').format(title=event.session_title))

    def _on_session_deleted(self, event: 'SessionPickerScreen.SessionDeleted') -> None:
        if event.session_id == self.session_id:
            self._logger.info('Current session deleted, switching to new session')
            if self._session_store:
                new_id, _ = self._session_store.get_or_create_session(model=self.model_name or '', provider=self.provider or '')
                self.session_id = new_id
                self._render_welcome_banner()
                chat_view = self.query_one('#chat-area', ChatContainer)
                chat_view.clear_messages()
                chat_view.show_greeting()
        self._logger.info(f'Session deleted: {event.session_id}')

    def append_chat_message(self, role: str, content: str) -> None:
        chat_area = self.query_one('#chat-area', ChatContainer)
        if chat_area:
            label = 'You' if role == 'user' else 'Agent'
            if hasattr(chat_area, 'write'):
                chat_area.write(f'{label}: {content}\n')
            elif hasattr(chat_area, 'append_message'):
                chat_area.append_message(role, content)

    def clear_chat(self) -> None:
        chat_area = self.query_one('#chat-area', ChatContainer)
        if chat_area:
            if hasattr(chat_area, 'clear'):
                chat_area.clear()
            elif hasattr(chat_area, 'clear_messages'):
                chat_area.clear_messages()

    def on_settings_saved(self, event) -> None:
        """Settings 保存后同步 Agent 运行时模型（无需重启）。"""
        if not hasattr(self, '_agent') or not self._agent:
            return
        try:
            from common.config import load_config
            cfg = load_config()
            llm = cfg.get('llm', {})
            provider = llm.get('provider', '')
            if provider:
                self._agent.set_model(provider=provider, model=llm.get('model') or None, api_key=llm.get('api_key') or None, base_url=llm.get('base_url') or None)
                self._logger.info(f'Agent model synced to {provider}')
        except Exception as e:
            self._logger.warning(f'Failed to sync agent model: {e}')

def run_textual_app(model_name: str='Agent-Z', provider: str | None=None, cwd: str | None=None, session_id: str | None=None, context_length: int | None=None, approval_mode: str='suggest', agent=None) -> int:
    if not TEXTUAL_AVAILABLE:
        print(get_textual_install_hint())
        return 1
    compatible, reason = is_textual_compatible()
    if not compatible:
        print(f'\n⚠ Cannot start Textual TUI: {reason}')
        print('Falling back to legacy CLI mode...\n')
        return 1
    app = AgentApp(model_name=model_name, provider=provider, cwd=cwd, session_id=session_id, context_length=context_length, approval_mode=approval_mode, agent=agent)
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
        return f'Textual not installed or import failed: {_TEXTUAL_IMPORT_ERROR}'
    try:
        import textual
    except ImportError as e:
        return f'Textual not installed: {e}'
    except Exception as e:
        return f'Error importing Textual: {e}'
    return 'Unknown error'

def get_textual_install_hint() -> str:
    return '\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n⚠  Textual 不可用\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n原因：Textual 库未安装或导入失败\n\n解决方案：\n  1. 安装 Textual：pip install textual>=0.50.0\n  2. 或使用 --no-textual 参数强制使用传统 CLI 模式\n  3. 或在非 TTY 环境（如管道/重定向）中自动使用传统模式\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'

def is_textual_compatible() -> tuple[bool, str | None]:
    if not TEXTUAL_AVAILABLE:
        return (False, 'Textual not installed')
    if not sys.stdout.isatty():
        return (False, 'Non-TTY environment detected')
    try:
        import shutil
        terminal_size = shutil.get_terminal_size()
        if terminal_size.columns < 40:
            return (False, 'Terminal too narrow (minimum 40 columns)')
    except Exception:
        pass
    return (True, None)

def create_fallback_app(model_name: str='Agent-Z', provider: str | None=None, cwd: str | None=None, session_id: str | None=None, context_length: int | None=None, approval_mode: str='suggest') -> None:
    from common.terminal.banner import print_simple_banner
    from common.terminal.ui import print_info, print_warning
    print_simple_banner()
    print_info(f'Model: {model_name}')
    if provider:
        print_info(f'Provider: {provider}')
    print_info(f'CWD: {cwd or os.getcwd()}')
    if session_id:
        print_info(f'Session: {session_id}')
    print()
    print_warning('Using legacy CLI mode (Textual TUI not available)')
    print_info('For TUI mode, install: pip install textual>=0.50.0')
    print()
__all__ = [
    "AgentApp",
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
    "NotificationType",
]
if __name__ == '__main__':
    print('Testing AgentApp...')
    print()
    if not TEXTUAL_AVAILABLE:
        print('Textual is not available.')
        print('Error message:', get_textual_import_error())
        sys.exit(1)
    print(f'Textual available: {TEXTUAL_AVAILABLE}')
    print()
    print('Starting Textual app...')
    print()
    exit_code = run_textual_app(model_name='gpt-4o', provider='OpenAI', cwd='E:/Projects/Agent-Z', session_id='test-session-001', context_length=128000)
    sys.exit(exit_code)