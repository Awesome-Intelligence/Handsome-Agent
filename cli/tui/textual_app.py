#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Textual TUI Application for Handsome Agent

🚪 Access - 💬 CLI - Textual UI 组件

基于 Textual 框架的现代化终端用户界面，提供丰富的交互体验。

模块包含：
- HandsomeAgentApp: 主应用类
- 动态主题系统
- 欢迎横幅渲染
- 快捷键绑定系统

降级和兼容性机制：
- Textual 不可用时提供友好错误提示
- Rich 功能作为可选增强
- 非 TTY 环境自动回退
- 与皮肤引擎（skin_engine.py）保持兼容
"""

from __future__ import annotations

import logging
import os
import sys
from typing import TYPE_CHECKING, Optional

# 降级机制：如果 textual 不可用，提供友好提示
TEXTUAL_AVAILABLE = True
_TEXTUAL_IMPORT_ERROR: str | None = None

try:
    from textual.app import App, ComposeResult
    from textual.widgets import Header, Footer, Static, RichLog, Tabs, Tab, TextArea, Button
    from textual.containers import Container, VerticalScroll, Horizontal
    from textual.message import Message
    from textual import on
    from textual.events import Key
    from textual import events as textual_events
    # Textual 8.x 中使用 Key 事件而不是 KeyEvent
    KeyEvent = Key
except ImportError as e:
    TEXTUAL_AVAILABLE = False
    _TEXTUAL_IMPORT_ERROR = str(e)

# Rich 库导入（用于消息渲染）
try:
    from rich.text import Text as RichText
    from rich.console import NewLine
    from rich.style import Style
except ImportError:
    RichText = None
    NewLine = None
    Style = None

# 条件导入 typing 工具
if TYPE_CHECKING:
    from textual.widget import Widget

# 主题系统
try:
    from .themes import ThemeManager, get_theme_manager
except ImportError:
    ThemeManager = None
    get_theme_manager = None

# Markdown 渲染器
try:
    from .markdown_renderer import MarkdownRenderer, markdown_to_rich, is_markdown_available
except ImportError:
    MarkdownRenderer = None
    markdown_to_rich = None
    is_markdown_available = None

# ChatView 组件
try:
    from .views.chat_view import ChatView, ChatMessageSubmitted
except ImportError:
    ChatView = None
    ChatMessageSubmitted = None

# 命令面板组件
try:
    from .widgets.command_palette import CommandPaletteScreen, Command
except ImportError:
    CommandPaletteScreen = None
    Command = None

# 会话选择器组件
try:
    from .widgets.session_picker import SessionPickerScreen
except ImportError:
    SessionPickerScreen = None

# 侧边栏组件
try:
    from .sidebar import SidebarContainer, SidebarTabBar
except ImportError:
    SidebarContainer = None
    SidebarTabBar = None

# 审批对话框组件
try:
    from .widgets.approval_dialog import (
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

# 会话存储服务
try:
    from .services.session_store import SessionStore
except ImportError:
    SessionStore = None

# 帮助面板组件
try:
    from .views.help_view import HelpScreen
except ImportError:
    HelpScreen = None

# 快捷键管理
try:
    from .keybindings import (
        KeyBinding,
        KeyBindingManager,
        KeyBindingCategory,
        create_default_keybindings,
    )
except ImportError:
    KeyBinding = None
    KeyBindingManager = None
    KeyBindingCategory = None
    create_default_keybindings = None

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
    from common.logging_manager import get_access_logger, LogManager
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    def get_access_logger(*args, **kwargs):
        return logging.getLogger("HandsomeAgent")
    LogManager = None

# 降级的颜色常量（用于横幅等使用硬编码颜色的场景）
# 这些颜色现在通过主题系统管理，但横幅使用硬编码是因为它们在 CSS 中引用
# Textual 不支持动态 CSS 变量替换，这里用于 Rich 标记
AVOCADO_PRIMARY = "#8B9A46"
AVOCADO_BRIGHT = "#A0B45A"
AVOCADO_DIM = "#647030"
AVOCADO_DARK = "#465A1E"
WHITE = "white"
GRAY_DIM = "#888888"
GOLD = "#FFD700"

# 状态指示器颜色
STATUS_ONLINE = "#3fb950"    # 绿色 - 空闲
STATUS_BUSY = "#f0883e"      # 橙色 - 处理中
STATUS_ERROR = "#f85149"     # 红色 - 错误

# ============================================================================
# TuiLogHandler - 后端日志路由到 TUI 日志面板
# ============================================================================

class TuiLogHandler(logging.Handler):
    """将后端日志输出重定向到 Textual RichLog 组件的日志处理器。

    线程安全：通过 App.call_from_thread() 将日志从任意线程路由到 UI 线程。
    组件就绪前自动缓冲日志，就绪后一次性刷新。
    过滤规则：排除 TextualUI 相关的 DEBUG 日志（窗口切换、面板切换等）。
    """

    # 要过滤的 logger 名称前缀（这些日志太频繁，不显示在面板）
    _FILTER_PREFIXES = ("TextualUI", "cli.tui", "tui.", "keybinding", "key_binding", "KeyBinding")
    # 要过滤的日志消息关键词（UI 交互类日志）
    _FILTER_KEYWORDS = (
        "tab", "panel", "sidebar", "log", "command palette", "screen",
        "session", "window", "theme", "focus", "mount", "unmount",
        "key", "binding", "shortcut",
    )

    def __init__(self, app, buffer_size: int = 500):
        super().__init__()
        self._app = app
        self._widget = None  # type: RichLog | None
        self._buffer: list[logging.LogRecord] = []
        self._buffer_size = buffer_size

    def set_widget(self, widget) -> None:
        """设置目标 RichLog 组件并刷新缓冲区。"""
        self._widget = widget
        if self._buffer:
            for record in self._buffer:
                self._write_log(record)
            self._buffer.clear()

    def emit(self, record: logging.LogRecord) -> None:
        """接收日志记录（任意线程），路由到 UI 线程写入。"""
        # 过滤：排除 TextualUI 相关的 DEBUG 日志
        if record.levelno == logging.DEBUG and self._is_ui_debug_log(record):
            return
        
        if self._widget is None:
            if len(self._buffer) < self._buffer_size:
                self._buffer.append(record)
            return
        try:
            self._app.call_from_thread(self._write_log, record)
        except Exception:
            pass

    def _is_ui_debug_log(self, record: logging.LogRecord) -> bool:
        """判断是否为 UI 相关的 DEBUG 日志（需要过滤）。"""
        name = record.name
        if any(name.startswith(prefix) for prefix in self._FILTER_PREFIXES):
            return True
        # 也过滤 UI 交互类消息
        msg_lower = record.getMessage().lower()
        return any(kw in msg_lower for kw in self._FILTER_KEYWORDS)

    def _write_log(self, record: logging.LogRecord) -> None:
        """在 UI 线程中写入 RichLog 组件，直接追加到 lines 列表。
        
        绕过 RichLog 的 deferred render 机制，确保日志立即可见。
        """
        if self._widget is None:
            return
        
        msg = self.format(record)
        # 直接写入原始字符串，不预先换行
        # RichLog 会自动处理换行逻辑
        self._widget.write(msg)


# ============================================================================
# NotificationAnimationManager - 通知动画管理器
# ============================================================================

class NotificationType:
    """通知类型枚举."""
    
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    
    # 动画类型
    ANIM_SLIDE = "slide"
    ANIM_FADE = "fade"
    ANIM_BOUNCE = "bounce"
    ANIM_SHAKE = "shake"
    ANIM_PULSE = "pulse"
    
    @classmethod
    def get_animation_for_type(cls, notification_type: str) -> str:
        """根据通知类型获取对应的动画类名.
        
        Args:
            notification_type: 通知类型 (info/success/warning/error)
            
        Returns:
            动画类名
        """
        animations = {
            cls.INFO: cls.ANIM_SLIDE,
            cls.SUCCESS: cls.ANIM_BOUNCE,
            cls.WARNING: cls.ANIM_PULSE,
            cls.ERROR: cls.ANIM_SHAKE,
        }
        return animations.get(notification_type, cls.ANIM_FADE)
    
    @classmethod
    def get_icon(cls, notification_type: str) -> str:
        """获取通知类型的图标.
        
        Args:
            notification_type: 通知类型
            
        Returns:
            Emoji 图标
        """
        icons = {
            cls.INFO: "ℹ️",
            cls.SUCCESS: "✅",
            cls.WARNING: "⚠️",
            cls.ERROR: "❌",
        }
        return icons.get(notification_type, "ℹ️")


class NotificationAnimationManager:
    """通知动画管理器.
    
    负责：
    - 管理通知动画效果
    - 提供多种动画类型
    - 控制动画时长和缓动函数
    """
    
    # 动画时长配置 (秒)
    ANIMATION_DURATIONS = {
        "fast": 0.2,
        "normal": 0.3,
        "slow": 0.5,
    }
    
    # 动画缓动函数
    EASING_FUNCTIONS = {
        "ease": "ease",
        "ease-in": "ease-in",
        "ease-out": "ease-out",
        "ease-in-out": "ease-in-out",
        "bounce": "cubic-bezier(0.68, -0.55, 0.265, 1.55)",
        "elastic": "cubic-bezier(0.5, 1.5, 0.5, 1)",
    }
    
    @classmethod
    def get_css_animation(cls, animation_type: str, duration: str = "normal") -> str:
        """获取 CSS 动画字符串.
        
        Args:
            animation_type: 动画类型
            duration: 动画时长 (fast/normal/slow)
            
        Returns:
            CSS animation 属性值
        """
        duration_value = cls.ANIMATION_DURATIONS.get(duration, 0.3)
        easing = cls.EASING_FUNCTIONS.get("ease-out", "ease-out")
        
        animation_map = {
            NotificationType.ANIM_SLIDE: f"slide-in-right {duration_value}s {easing}",
            NotificationType.ANIM_FADE: f"fade-in {duration_value}s {easing}",
            NotificationType.ANIM_BOUNCE: f"bounce-in {duration_value}s {cls.EASING_FUNCTIONS['bounce']}",
            NotificationType.ANIM_SHAKE: f"shake {duration_value}s {easing}",
            NotificationType.ANIM_PULSE: f"pulse {duration_value * 2}s ease-in-out infinite",
        }
        
        return animation_map.get(animation_type, f"fade-in {duration_value}s {easing}")
    
    @classmethod
    def create_animated_notification(
        cls,
        message: str,
        notification_type: str = NotificationType.INFO,
        duration: float = 3.0,
    ) -> tuple[str, str]:
        """创建带动画的通知内容.
        
        Args:
            message: 通知消息
            notification_type: 通知类型
            duration: 显示时长（秒）
            
        Returns:
            (toast CSS类, 格式化消息)
        """
        # 获取动画类型
        anim_type = cls.get_animation_for_type(notification_type)
        icon = cls.get_icon(notification_type)
        
        # 构建 CSS 类
        css_classes = [
            "notification-toast",
            notification_type,
            f"anim-{anim_type}",
        ]
        css_class_str = " ".join(css_classes)
        
        # 格式化消息（带图标）
        formatted_message = f"[bold]{icon}[/] {message}"
        
        return css_class_str, formatted_message
    
    @classmethod
    def get_progress_bar_html(cls, progress: float, animated: bool = True) -> str:
        """生成分带动画的进度条 HTML.
        
        Args:
            progress: 进度 (0.0 - 1.0)
            animated: 是否启用动画
            
        Returns:
            进度条 CSS 类
        """
        base_class = "progress-bar"
        fill_class = "progress-bar-fill"
        if animated:
            fill_class += " progress-bar-animated"
        
        return f"{base_class} {fill_class}"


# ============================================================================
# HandsomeAgentApp 主类
# ============================================================================

# 创建一个兼容的 log 对象来替代 Textual 的 log
# Textual 8.x 的 log 是一个 callable
class CompatibleLog:
    """兼容 Textual 8.x 的 Log 对象."""
    
    def __call__(self, *args, **kwargs):
        """Textual 8.x log 是 callable."""
        pass
    
    def system(self, *args, **kwargs): pass
    def info(self, *args, **kwargs): pass
    def debug(self, *args, **kwargs): pass
    def warning(self, *args, **kwargs): pass
    def error(self, *args, **kwargs): pass
    def critical(self, *args, **kwargs): pass

# 全局单例实例
_COMPATIBLE_LOG = CompatibleLog()


# ============================================================================
# SubmitTextArea - 支持按 Enter 发送消息的 TextArea 子类
# ============================================================================

class SubmitTextArea(TextArea):
    """支持按 Enter 发送消息的 TextArea。
    
    - Enter（无修饰键）：触发 Submitted 事件（不插入换行）
    - Ctrl+Enter：插入换行（默认行为）
    
    内部使用自定义的 InputSubmitted 消息事件。
    """
    
    class InputSubmitted(Message):
        """输入提交事件（按 Enter 触发）。"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    async def _on_key(self, event: "textual_events.Key") -> None:
        """拦截 Enter 键：无修饰键时触发提交，否则保持默认行为。"""
        key = event.key
        
        # Enter without modifiers -> submit message
        # Textual 中修饰键编码在 key 字符串中：plain="enter", ctrl+enter="ctrl+enter"
        if key == "enter":
            event.stop()
            event.prevent_default()
            self.post_message(self.InputSubmitted())
            return
        
        # Ctrl+Enter / Shift+Enter / Alt+Enter -> insert newline (default behavior)
        # 这些 key 字符串包含 '+' 修饰符前缀
        if key.startswith("ctrl+") or key.startswith("shift+") or key.startswith("alt+"):
            await super()._on_key(event)
            return
        
        # 其他键保持默认行为
        await super()._on_key(event)


# ============================================================================
# ClickableStatic - 可点击的 Static 组件（用于替代 Button 避免样式问题）
# ============================================================================

class ClickableStatic(Static):
    """可点击的 Static 组件。
    
    用于替代 Button 以避免 Textual 默认样式中的边框问题。
    支持 on_click 事件处理。
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.can_focus = True
    
    def on_click(self) -> None:
        """处理点击事件。"""
        # 通知父组件（通过冒泡到 App）
        self.app._toggle_sidebar()


# ============================================================================
# HandsomeAgentApp 主类
# ============================================================================
def _patch_textual_logger():
    """Patch Textual's LayerLogger to be compatible."""
    try:
        from textual._log import LayerLogger
        # 将所有日志方法替换为接受任意参数
        LayerLogger.system = lambda *args, **kwargs: None
        LayerLogger.info = lambda *args, **kwargs: None
        LayerLogger.debug = lambda *args, **kwargs: None
        LayerLogger.warning = lambda *args, **kwargs: None
        LayerLogger.error = lambda *args, **kwargs: None
        LayerLogger.critical = lambda *args, **kwargs: None
    except ImportError:
        pass

# 立即执行 patch（模块导入时就打补丁）
_patch_textual_logger()

# Descriptor 来覆盖 App.log property
class LogDescriptor:
    """覆盖 App.log 属性的 descriptor."""
    def __get__(self, obj, objtype=None):
        return _COMPATIBLE_LOG
    
    def __set__(self, obj, value):
        pass  # 忽略设置，只用于读取

class HandsomeAgentApp(App):
    """Handsome Agent Textual TUI Application.
    
    基于 Textual 框架的现代化终端界面，提供丰富的交互体验。
    
    Attributes:
        CSS: 内联 CSS 样式定义（从主题系统生成）
        BINDINGS: 快捷键绑定列表
        model_name: 当前模型名称
        provider: 模型提供商
        session_id: 会话 ID
        theme_manager: 主题管理器实例
    """
    
    # 使用 descriptor 覆盖父类的 log property
    log = LogDescriptor()
    
    # 快捷键绑定
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+c", "cancel_current", "Cancel"),
        ("ctrl+b", "toggle_sidebar", "Sidebar"),
        ("ctrl+h", "toggle_help", "Help"),
        ("ctrl+t", "new_tab", "New Tab"),
        ("ctrl+w", "close_tab", "Close Tab"),
        ("ctrl+tab", "next_tab", "Next Tab"),
        ("ctrl+shift+tab", "prev_tab", "Previous Tab"),
        ("ctrl+k", "open_command_palette", "Command Palette"),
        ("ctrl+1", "switch_to_file_tree", "File Tree"),
        ("ctrl+2", "switch_to_tasks", "Tasks"),
        ("ctrl+3", "switch_to_agent", "Agent"),
        ("ctrl+4", "switch_to_logs", "Logs"),
        ("f1", "open_help", "Help"),
        ("ctrl+/", "open_help", "Help"),
        ("ctrl+r", "open_session_selector", "Session Selector"),
        ("ctrl+l", "clear_screen", "Clear"),
        ("j", "scroll_down", "Scroll Down"),
        ("k", "scroll_up", "Scroll Up"),
        ("ctrl+shift+t", "change_theme", "Change Theme"),
        ("ctrl+shift+b", "toggle_transparency", "Transparency"),  # 透明度切换
        ("ctrl+shift+m", "toggle_markdown", "Markdown"),  # Markdown 渲染切换
    ]
    
    def __init__(
        self,
        model_name: str = "Handsome Agent",
        provider: str | None = None,
        cwd: str | None = None,
        session_id: str | None = None,
        context_length: int | None = None,
        approval_mode: str | ApprovalMode = "suggest",
        initial_theme: str | None = None,
        agent=None,  # Agent 实例
        **kwargs
    ):
        """初始化 HandsomeAgentApp.
        
        Args:
            model_name: 模型名称
            provider: 模型提供商
            cwd: 当前工作目录
            session_id: 会话 ID
            context_length: 上下文窗口大小
            approval_mode: 审批模式（auto/suggest/manual）
            initial_theme: 初始主题 ID，None 则使用保存的偏好或默认主题
            agent: Agent 实例，用于处理用户消息
            **kwargs: 传递给父类的其他参数
        """
        # 先 patch Textual logger 以修复兼容性问题
        _patch_textual_logger()
        
        # 将后端控制台日志路由到 TUI 日志面板
        self._tui_log_handler: TuiLogHandler | None = None
        self._saved_console_handler: logging.Handler | None = None
        if LogManager is not None:
            try:
                lm = LogManager.get_instance()
                if lm._console_handler is not None:
                    # 创建 TUI 日志处理器并设置与控制台相同的格式
                    self._tui_log_handler = TuiLogHandler(self)
                    if hasattr(lm._console_handler, 'formatter'):
                        self._tui_log_handler.setFormatter(lm._console_handler.formatter)
                    self._tui_log_handler.setLevel(lm._console_handler.level)
                    
                    # 从 root logger 移除控制台 handler，添加 TUI handler
                    if lm._console_handler in logging.root.handlers:
                        logging.root.removeHandler(lm._console_handler)
                        self._saved_console_handler = lm._console_handler
                    logging.root.addHandler(self._tui_log_handler)
                    
                    # 从所有子 logger 移除控制台 handler
                    for logger_name in logging.Logger.manager.loggerDict:
                        logger = logging.getLogger(logger_name)
                        if lm._console_handler in logger.handlers:
                            logger.removeHandler(lm._console_handler)
                            logger.addHandler(self._tui_log_handler)
            except Exception:
                pass
        
        super().__init__(**kwargs)
        
        # 覆盖 _logger 为我们的兼容 Logger（修复 Textual 8.x 兼容性问题）
        # _logger 是 Widget.log 使用的实际对象
        self._logger = _COMPATIBLE_LOG
        
        self.model_name = model_name
        self.provider = provider
        self.cwd = cwd or os.getcwd()
        self.session_id = session_id
        self.context_length = context_length
        self._logger = get_access_logger("TextualUI", sublayer="tui")
        
        # 加载动画相关
        self._is_loading: bool = False
        self._loading_timer: Optional[callable] = None
        # 多套加载动画帧（支持切换）
        self._LOADING_FRAMES = {
            "dots": ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"],  # 点状旋转
            "circle": ["◐", "◓", "◑", "◒"],  # 圆形旋转
            "braille": ["⠓", "⠒", "⠐", "⠔", "⠠", "⠡", "⠢", "⠣"],  # 盲文旋转
            "pulse": ["●", "○", "◌"],  # 脉冲
        }
        self._loading_frames: list = self._LOADING_FRAMES["dots"]  # 默认使用点状
        self._loading_frame_index: int = 0
        self._loading_style: str = "dots"  # 当前动画风格
        
        # 流式输出打字机效果相关
        self._is_streaming: bool = False
        self._streaming_text: str = ""
        self._streaming_widget_id: str | None = None
        self._streaming_timer: Optional[callable] = None
        self._streaming_chars_per_tick: int = 3  # 每帧显示的字符数
        self._streaming_delay_ms: int = 30  # 每帧延迟（毫秒）
        
        # 保存 Agent 实例
        self._agent = agent
        
        # 主题管理器初始化
        self._theme_manager: ThemeManager | None = None
        if get_theme_manager:
            self._theme_manager = get_theme_manager()
            if initial_theme:
                self._theme_manager.set_theme(initial_theme)
        
        # 会话持久化相关
        self._session_store: Optional[SessionStore] = None
        self._pending_message_count: int = 0
        self._auto_save_interval: int = 5  # 每 N 条消息自动保存
        
        # 标签页相关状态
        self._tab_counter = 0
        self._tab_states: dict[str, dict] = {}
        self._active_tab_id: str | None = None
        
        # 审批流程相关
        self._approval_manager: Optional[ApprovalManager] = None
        self._pending_tool_call: dict | None = None  # 待审批的工具调用
        self._approval_callback: Optional[callable] = None  # 审批结果回调
        
        # Composer 历史记录相关
        self._input_history: list[str] = []  # 输入历史列表
        self._history_index: int = -1  # -1 表示当前输入
        self._current_input: str = ""  # 临时保存当前输入
        
        # 初始化快捷键管理器
        self._key_binding_manager: Optional[KeyBindingManager] = None
        if KeyBindingManager:
            self._init_keybinding_manager()
        
        # 初始化会话存储
        self._init_session_store()
        
        # 初始化审批管理器
        self._init_approval_manager(approval_mode)
        
        # Agent 状态指示器
        self._agent_status = "online"  # online/busy/error
        
        # Markdown 渲染器初始化
        self._markdown_renderer: MarkdownRenderer | None = None
        if MarkdownRenderer:
            try:
                self._markdown_renderer = MarkdownRenderer(enable_code_highlight=True)
                if self._markdown_renderer.is_available():
                    self._logger.debug("Markdown renderer initialized")
                else:
                    self._logger.debug("Markdown renderer not available: " + self._markdown_renderer.get_install_hint())
            except Exception as e:
                self._logger.debug(f"Failed to initialize Markdown renderer: {e}")
        
        # Markdown 渲染开关
        self._markdown_enabled = True  # 默认启用 Markdown 渲染
    
    # 类级别 CSS 属性（默认主题 - 参考 CodeWhale 深色主题）
    CSS = """
/* Handsome Agent - CodeWhale Style Theme */

Screen {
    background: #0d1117;
}

/* 聊天区域：深色背景 */
#chat-area {
    height: 1fr;
    width: 100%;
    background: #0d1117;
    overflow-y: auto;
}

#chat-log {
    height: 100%;
    width: 100%;
    background: #0d1117;
    padding: 1 2;
    overflow-x: hidden;
}

/* 欢迎横幅：简洁设计 */
#welcome-banner {
    height: auto;
    width: 100%;
    padding: 1 2;
    background: #161b22;
    border-bottom: solid #30363d;
}

#welcome-title {
    text-style: bold;
    color: #58a6ff;
    height: auto;
    padding: 0 0 1 0;
}

#welcome-content {
    color: #8b949e;
    height: auto;
    padding: 0 0 1 0;
}

/* 自定义 Header - 模型信息显示 */
#app-header {
    height: 1;
    width: 100%;
    background: #161b22;
    dock: top;
}

.header-content {
    height: 100%;
    layout: horizontal;
    padding: 0 2;
    align: left middle;
}

.header-model {
    color: #58a6ff;
    text-style: bold;
}

.header-context {
    color: #8b949e;
    margin-left: 4;
}

.header-cwd {
    color: #6e7681;
}

.header-status {
    color: #3fb950;
    margin-right: 1;
}

/* 流式输出指示器 - Textual CSS 不支持动画，使用静态样式 */
.streaming-indicator {
    color: #8b949e;
}

/* 自定义 Footer - 状态信息 */
#app-footer {
    height: 1;
    width: 100%;
    background: #21262d;
    dock: top;
}

.footer-content {
    height: 100%;
    layout: horizontal;
    padding: 0 2;
    align: left middle;
}

.footer-token {
    color: #8b949e;
}

.footer-hint {
    color: #6e7681;
}

/* === 状态栏样式 === */
#status-bar {
    height: 1;
    width: 100%;
    background: #21262d;
}

#status-content {
    height: 100%;
    layout: horizontal;
    padding: 0 2;
}

.status-icon {
    width: 1;
    color: #3fb950;  /* 绿色在线状态 */
}

.status-model {
    color: #58a6ff;
}

.status-sep {
    width: 1;
    color: #30363d;
}

.status-tokens {
    color: #8b949e;
}

.status-progress {
    color: #8b949e;
}

.status-time {
    color: #8b949e;
    width: 8;
}

.status-tools {
    color: #8b949e;
}

/* 聊天日志样式 */
#chat-log {
    padding: 1 2;
}

/* 消息样式 - 用户消息浅蓝气泡 */
#chat-log .user-message {
    background: #1f2937;
    color: #e5e7eb;
    padding: 0 1;
    margin: 0;
}

/* 消息样式 - 助手消息透明 */
#chat-log .assistant-message {
    color: #c9d1d9;
    padding: 0 1;
    margin: 0;
}

/* 消息样式 - 系统消息灰色 */
#chat-log .system-message {
    color: #8b949e;
    padding: 0 1;
    margin: 0;
}

/* 滚动条样式 - 美化为细线 */
#chat-area {
    overflow-y: auto;
}

/* 输入区域样式 */
#input-area {
    height: 5;
    width: 100%;
    background: #161b22;
    dock: bottom;
}

#input-field {
    border: solid #30363d;
    background: #0d1117;
    padding: 1 2;
}

#input-field:focus {
    border: solid #58a6ff;
}

/* 发送按钮样式 */
#send-button {
    width: 5;
    background: #238636;
    color: #ffffff;
}

#send-button:hover {
    background: #2ea043;
}

#input-row {
    height: 100%;
    width: 100%;
    layout: horizontal;
}

.input-field {
    border: solid #30363d;
    background: #161b22;
    color: #e6edf3;
    padding: 1 2;
    height: 100%;
    width: 1fr;
}

.input-field:focus {
    border: solid #58a6ff;
}

/* TextArea (Composer) specific styles */
#user-input {
    background: #0d1117;
    color: #ffffff;
    border: solid #30363d;
    padding: 1;
    height: 5;
}

#user-input:focus {
    border: solid #58a6ff;
}

/* 按钮通用样式 */
Button {
    background: #21262d;
    color: #c9d1d9;
    border: solid #30363d;
}

Button:hover {
    background: #30363d;
}

/* === 侧边栏样式 === */
#sidebar-container {
    width: 15%;
    min-width: 20;
    max-width: 25;
    height: 100%;
    background: #161b22;
    border-left: solid #30363d;
}

/* 侧边栏折叠状态 - 完全隐藏 */
#sidebar-container.collapsed {
    display: none;
}

/* 折叠按钮样式 - 固定在边缘 (使用 ClickableStatic 避免 Button 默认样式) */
ClickableStatic#sidebar-toggle {
    width: 2;
    height: 100%;
    min-width: 2;
    max-width: 2;
    background: #21262d;
    color: #8b949e;
    content-align: center middle;
    padding: 0;
    margin: 0;
}

ClickableStatic#sidebar-toggle:hover {
    background: #30363d;
    color: #c9d1d9;
}

#sidebar-tabs {
    height: 3;
    background: #161b22;
    border-bottom: solid #30363d;
    content-align: left bottom;
}

#tab-bar {
    height: 100%;
    layout: horizontal;
}

.sidebar-tab {
    background: #161b22;
    color: #8b949e;
    border: none;
    padding: 0 1;
    margin: 0;
    min-width: 3;
}

.sidebar-tab.active {
    background: #1f3a5f;
    color: #58a6ff;
    text-style: bold;
}

.sidebar-tab:hover {
    background: #30363d;
    color: #c9d1d9;
}

#sidebar-content-inner {
    height: 1fr;
    padding: 1;
}

.sidebar-panel {
    height: 100%;
    display: block;
}

.sidebar-panel.hidden {
    display: none;
}

.panel-title {
    color: #c9d1d9;
    text-style: bold;
    margin-bottom: 1;
}

#log-output {
    height: 100%;
    background: #0d1117;
    color: #8b949e;
}

/* === 主区域布局 === */
#main-area {
    height: 1fr;
    width: 100%;
}

#chat-area {
    width: 1fr;
    height: 100%;
}

#file-tree-title,
#tasks-title,
#agent-title,
#context-title {
    color: #c9d1d9;
    text-style: bold;
    margin-bottom: 1;
}

/* ============================================================================
   半透明背景样式 (Frosted Glass Effect)
   支持 Ctrl+Shift+B 快捷键切换
   ============================================================================ */

/* 透明度容器 - 基础样式 */
.transparent-container {
    /* 使用纯色背景作为降级方案 */
}

/* 半透明面板 - 毛玻璃效果 */
.transparent-panel {
    background: rgba(13, 17, 23, 0.75);
    border: solid rgba(48, 54, 61, 0.5);
}

/* 半透明标题栏 */
.transparent-header {
    background: rgba(22, 27, 34, 0.80);
}

/* 半透明状态栏 */
.transparent-status-bar {
    background: rgba(33, 38, 45, 0.80);
}

/* 半透明页脚 */
.transparent-footer {
    background: rgba(33, 38, 45, 0.85);
}

/* 半透明侧边栏 */
.transparent-sidebar {
    background: rgba(22, 27, 34, 0.75);
    border-left: solid rgba(48, 54, 61, 0.5);
}

/* 半透明聊天区域 */
.transparent-chat {
    background: rgba(13, 17, 23, 0.70);
}

/* 半透明输入框 */
.transparent-input {
    background: rgba(13, 17, 23, 0.60);
    border: solid rgba(88, 166, 255, 0.3);
}

.transparent-input:focus {
    border: solid rgba(88, 166, 255, 0.6);
}

/* 半透明欢迎横幅 */
.transparent-welcome {
    background: rgba(22, 27, 34, 0.65);
    border-bottom: solid rgba(48, 54, 61, 0.4);
}

/* 透明度切换指示器 */
.transparency-indicator {
    color: #58a6ff;
    text-style: bold;
}

/* ============================================================================
   通知样式 (Notification Styles)
   注意: Textual CSS 不支持 @keyframes 动画和细粒度边框属性
   ============================================================================ */

/* 通知样式 - 基础 */
.notification-toast {
    background: #21262d;
    border: solid #58a6ff;
    padding: 1 2;
}

/* 通知图标样式 */
.notification-icon {
    color: #58a6ff;
}

.notification-icon.success {
    color: #3fb950;
}

.notification-icon.warning {
    color: #f0883e;
}

.notification-icon.error {
    color: #f85149;
}

.notification-icon.info {
    color: #58a6ff;
}

/* 进度条样式 */
.progress-bar {
    height: 1;
    background: #21262d;
}

.progress-bar-fill {
    height: 100%;
    background: #58a6ff;
}

/* ============================================================================
   打字机效果光标样式
   ============================================================================ */

/* 闪烁光标样式 - 用于流式输出 */
.typewriter-cursor {
    color: #58a6ff;
    text-style: bold;
}

/* 加载动画文字样式 */
.loading-text {
    color: #8b949e;
}

/* 打字机完成后的淡入效果 (使用纯色，不支持 @keyframes 动画) */
.typewriter-complete {
    color: #c9d1d9;
}

/* 加载动画增强样式 */
.loading-indicator {
    color: #3fb950;
}

/* 加载动画帧样式 */
.loading-frame {
    text-style: bold;
}

/* 打字机输出组件样式 */
.typewriter-output {
    width: 1fr;
    height: auto;
    max-width: 100%;
    padding: 0 2;
    background: #0d1117;
}

/* 打字机速度控制 (通过 Python 代码控制，此处仅作标记) */
.typewriter-fast {
    color: #58a6ff;
}

.typewriter-normal {
    color: #58a6ff;
}

.typewriter-slow {
    color: #58a6ff;
}

"""
    
    def compose(self) -> ComposeResult:
        """组合应用布局组件.
        
        布局结构：
        - 自定义 Header（模型信息、上下文占用）
        - 主区域
          - 左侧：聊天区域（欢迎横幅 + 聊天历史）
          - 右侧：侧边栏（文件树、任务、Agent、上下文）
        - 自定义 Footer（状态信息、快捷键提示）
        - 输入区域（固定在底部）
        
        Returns:
            ComposeResult: 组件生成器
        """
        # 自定义 Header - 显示模型信息
        with Container(id="app-header"):
            with Horizontal(id="header-content"):
                yield Static("🟢", id="status-indicator", classes="header-status")
                yield Static(self.model_name or "Handsome Agent", classes="header-model")
                ctx_str = f"[{self._format_context(self.context_length)}]" if self.context_length else ""
                yield Static(ctx_str, classes="header-context")
                cwd_short = self.cwd[-30:] if self.cwd and len(self.cwd) > 30 else (self.cwd or "")
                yield Static(cwd_short, classes="header-cwd")
        
        # 主区域 - 左侧聊天 + 折叠按钮 + 右侧侧边栏
        with Horizontal(id="main-area"):
            # 左侧聊天区域（弹性高度）
            with VerticalScroll(id="chat-area"):
                yield Static("", id="welcome-banner")
                yield RichLog(id="chat-log", auto_scroll=True)
            
            # 折叠按钮 - 使用 ClickableStatic 避免 Button 默认样式问题
            if SidebarContainer and SidebarTabBar:
                yield ClickableStatic("◀", id="sidebar-toggle", markup=False)
            
            # 右侧侧边栏
            if SidebarContainer and SidebarTabBar:
                with Container(id="sidebar-container"):
                    yield SidebarTabBar(on_switch=self._on_sidebar_panel_switch)
                    yield SidebarContainer(cwd=self.cwd, agent=self._agent)
        
        # 状态栏 - 显示模型、Token、工具等信息
        with Container(id="status-bar"):
            with Horizontal(id="status-content"):
                yield Static("●", id="status-icon", classes="status-icon")
                yield Static(self.model_name or "Handsome Agent", id="status-model", classes="status-model")
                yield Static("│", id="status-sep1", classes="status-sep")
                tokens_init = f"0/{self._format_context(self.context_length)}" if self.context_length else "n/a"
                yield Static(tokens_init, id="status-tokens", classes="status-tokens")
                yield Static("│", id="status-sep2", classes="status-sep")
                yield Static("░░░░░░░░░░░░", id="status-progress", classes="status-progress")
                yield Static("│", id="status-sep3", classes="status-sep")
                yield Static("0m 0s", id="status-time", classes="status-time")
                yield Static("│", id="status-sep4", classes="status-sep")
                yield Static("🔧", id="status-tools", classes="status-tools")
        
        # 自定义 Footer - 显示快捷键提示
        with Container(id="app-footer"):
            with Horizontal(id="footer-content"):
                yield Static(
                    "[#c9d1d9][[/][#30363d]Ctrl+B[/][#c9d1d9]][/] 侧边栏 [#6e7681]|[/] "
                    "[#c9d1d9][[/][#30363d]Ctrl+K[/][#c9d1d9]][/] 命令 [#6e7681]|[/] "
                    "[#c9d1d9][[/][#30363d]Ctrl+Shift+B[/][#c9d1d9]][/] 透明 [#6e7681]|[/] "
                    "[#c9d1d9][[/][#30363d]Ctrl+Shift+M[/][#c9d1d9]][/] MD [#6e7681]|[/] "
                    "[#c9d1d9][[/][#30363d]Ctrl+L[/][#c9d1d9]][/] 清屏",
                    classes="footer-hint"
                )
        
        # 输入区域（固定在底部）
        with Container(id="input-area"):
            yield SubmitTextArea(
                id="user-input",
                classes="input-field",
                placeholder="输入消息... (Ctrl+Enter 换行, Enter 发送)",
            )
    
    def on_key(self, event: KeyEvent) -> None:
        """处理全局键盘事件.
        
        - Ctrl+B: 折叠/展开侧边栏
        - Ctrl+1/2/3/4: 侧边栏面板切换
        """
        # Ctrl+B 折叠/展开侧边栏
        if event.key == "b" and event.control:
            self._toggle_sidebar()
            event.prevent_default()
            event.stop()
            return
        
        # 检查 Ctrl 键是否按下 - 面板切换
        if event.control and event.key in ['1', '2', '3', '4']:
            # 直接调用面板切换方法
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
        """应用挂载时初始化."""
        self._logger.info("Textual UI mounted")
        self._render_welcome_banner()
        
        # 初始化状态栏
        self._update_status_bar()
        
        # 注册事件监听器
        self._register_event_listeners()
        
        # 将 TUI 日志处理器绑定到日志面板的 RichLog 组件
        if self._tui_log_handler is not None:
            try:
                log_widget = self.query_one("#log-output", RichLog)
                self._tui_log_handler.set_widget(log_widget)
            except Exception:
                pass
        
        # 应用已保存的透明度设置
        if self._theme_manager and self._theme_manager.is_transparency_enabled():
            self._logger.info("Applying saved transparency settings")
            self._update_transparency_styles(True)
        
        # 聚焦到输入框（TextArea）
        self.set_focus(self.query_one("#user-input", TextArea))
    
    def _update_status_bar(self) -> None:
        """更新状态栏显示."""
        try:
            # 状态指示器图标
            icon_widget = self.query_one("#status-indicator-icon", Static)
            icon_widget.update("●")
            
            # 模型名称
            model_widget = self.query_one("#status-model", Static)
            model_widget.update(f" {self.model_name or 'Handsome Agent'} ")
            
            # Token 使用情况
            tokens_widget = self.query_one("#status-tokens", Static)
            if self.context_length:
                tokens_widget.update(f"│ 0/{self._format_context(self.context_length)} ")
            else:
                tokens_widget.update("│ n/a ")
            
            # 进度条
            progress_widget = self.query_one("#status-progress", Static)
            progress_widget.update("░░░░░░░░░░░░")
            
            # 时间
            time_widget = self.query_one("#status-time", Static)
            time_widget.update("│ 0m 0s ")
            
            # 工具数量
            tools_widget = self.query_one("#status-tools", Static)
            tools_widget.update("🔧")
        except Exception as e:
            self._logger.debug(f"Failed to update status bar: {e}")
    
    @on(SubmitTextArea.InputSubmitted)
    def _on_input_submitted(self, event: SubmitTextArea.InputSubmitted) -> None:
        """处理 TextArea 回车提交事件：发送消息。"""
        text_area = self.query_one("#user-input", SubmitTextArea)
        user_input = text_area.text.strip()
        
        if not user_input:
            return
        
        # 添加到历史记录
        if user_input not in self._input_history:
            self._input_history.insert(0, user_input)
            if len(self._input_history) > 100:
                self._input_history = self._input_history[:100]
        
        # 重置历史索引
        self._history_index = -1
        self._current_input = ""
        
        # 清空输入框
        text_area.text = ""
        
        # 显示用户消息
        self._append_message("user", user_input)
        self._logger.debug(f"User input: {user_input[:50]}...")
        
        # 异步调用 Agent 处理
        self.call_later(lambda: self._call_agent_async(user_input))
    
    def _register_event_listeners(self) -> None:
        """注册事件监听器.
        
        注意：Textual 8.x 使用 @on 装饰器注册消息处理器，
        这些装饰器需要在类定义时使用，而不是在运行时调用。
        如果需要动态注册，可以使用 subscribe() 方法。
        """
        # Textual 8.x 消息处理器通过 @on 装饰器注册
        # 以下是占位注释，实际消息处理器应该在类方法上用 @on 装饰
        self._logger.debug("Event listeners registered (using @on decorators)")
        
        # 监听会话选择器事件（需要使用 @on 装饰器）
        # 示例（已在类方法上定义）：
        # @on(SessionPickerScreen.SessionSelected)
        # def _on_session_selected(self, event):
        #     pass
        
        # 监听审批对话框事件
        # @on(ApprovalConfirmed)
        # def on_approval_confirmed(self, event):
        #     pass
    
    def _start_loading_animation(self) -> None:
        """启动加载动画."""
        if self._is_loading:
            return
        self._is_loading = True
        self._loading_frame_index = 0
        self._update_loading_frame()
    
    def _stop_loading_animation(self) -> None:
        """停止加载动画."""
        self._is_loading = False
        # 恢复状态图标
        status_icon = self.query_one("#status-icon", Static)
        status_icon.update("●")
    
    def _toggle_sidebar(self) -> None:
        """切换侧边栏折叠状态."""
        sidebar = self.query_one("#sidebar-container", Container)
        toggle_btn = self.query_one("#sidebar-toggle", ClickableStatic)
        
        if sidebar.has_class("collapsed"):
            # 展开侧边栏
            sidebar.remove_class("collapsed")
            toggle_btn.remove_class("collapsed")
            toggle_btn.update("▶")  # 向左箭头 - 侧边栏已展开，点击收起
        else:
            # 折叠侧边栏
            sidebar.add_class("collapsed")
            toggle_btn.add_class("collapsed")
            toggle_btn.update("◀")  # 向右箭头 - 侧边栏已收起，点击展开
    
    def _update_loading_frame(self) -> None:
        """更新加载动画帧."""
        if not self._is_loading:
            return
        # 更新状态图标为当前帧
        status_icon = self.query_one("#status-icon", Static)
        status_icon.update(self._loading_frames[self._loading_frame_index])
        # 更新帧索引
        self._loading_frame_index = (self._loading_frame_index + 1) % len(self._loading_frames)
        # 设置下一个定时器（约 200ms 一帧）
        self.set_timer(0.2, self._update_loading_frame)
    
    # ========================================================================
    # 加载动画控制方法
    # ========================================================================
    
    def set_loading_style(self, style: str) -> bool:
        """设置加载动画风格.
        
        Args:
            style: 动画风格 (dots/circle/braille/pulse)
            
        Returns:
            True 如果设置成功
        """
        if style in self._LOADING_FRAMES:
            self._loading_style = style
            self._loading_frames = self._LOADING_FRAMES[style]
            self._loading_frame_index = 0
            self._logger.debug(f"Loading style changed to: {style}")
            return True
        return False
    
    def cycle_loading_style(self) -> str:
        """循环切换加载动画风格.
        
        Returns:
            切换后的动画风格名称
        """
        styles = list(self._LOADING_FRAMES.keys())
        current_index = styles.index(self._loading_style) if self._loading_style in styles else 0
        next_index = (current_index + 1) % len(styles)
        next_style = styles[next_index]
        self.set_loading_style(next_style)
        return next_style
    
    # ========================================================================
    # 流式输出打字机效果方法
    # ========================================================================
    
    def start_streaming_message(self, widget_id: str) -> None:
        """开始流式输出消息.
        
        Args:
            widget_id: 要更新的 RichLog 组件 ID
        """
        self._is_streaming = True
        self._streaming_text = ""
        self._streaming_widget_id = widget_id
        
        # 显示流式输出开始提示
        log = self.query_one(f"#{widget_id}", RichLog)
        if log:
            from rich.text import Text as RichText
            header = RichText.from_markup("[bold #3fb950]**Assistant**[/]\n\n")
            log.write(header)
    
    def append_streaming_text(self, text: str) -> None:
        """追加流式文本内容（由外部调用，如 agent 实时推送）.
        
        Args:
            text: 要追加的文本
        """
        if not self._is_streaming:
            return
        self._streaming_text += text
    
    def start_typewriter_effect(self, full_text: str, widget_id: str) -> None:
        """启动打字机效果（完整文本逐字显示）.
        
        Args:
            full_text: 完整的文本内容
            widget_id: 要更新的 RichLog 组件 ID
        """
        self._is_streaming = True
        self._streaming_text = full_text
        self._streaming_widget_id = widget_id
        self._streaming_displayed = 0
        self._streaming_current_content = ""  # 使用实例变量跟踪内容
        
        # 如果已经有流式组件，先移除
        self._remove_streaming_widget()
        
        # 创建一个临时的 Static 组件用于显示打字中的内容
        from textual.widgets import Static
        streaming_widget = Static(
            id="streaming-output",
            classes="typewriter-output",
            markup=True,
        )
        
        # 获取 chat-area 容器，在末尾添加流式组件（显示在底部）
        chat_area = self.query_one("#chat-area", VerticalScroll)
        chat_area.mount(streaming_widget)
        
        self._streaming_timer = self.set_interval(
            self._streaming_delay_ms / 1000.0,
            self._update_typewriter_frame
        )
    
    def _remove_streaming_widget(self) -> None:
        """移除流式输出组件."""
        try:
            widget = self.query_one("#streaming-output")
            widget.remove()
        except Exception:
            pass
    
    def _update_typewriter_frame(self) -> None:
        """更新打字机动画帧（定时器回调）."""
        if not self._is_streaming:
            return
        
        try:
            streaming_widget = self.query_one("#streaming-output")
        except Exception:
            return
        
        # 计算已显示的字符数
        current_displayed = getattr(self, '_streaming_displayed', 0)
        chars_to_add = self._streaming_chars_per_tick
        
        # 计算本帧要添加的字符范围
        end_index = min(current_displayed + chars_to_add, len(self._streaming_text))
        new_chars = self._streaming_text[current_displayed:end_index]
        
        if new_chars:
            # 追加新字符到当前内容
            self._streaming_current_content += new_chars
            streaming_widget.update(self._streaming_current_content)
            self._streaming_displayed = end_index
        
        # 滚动到底部
        try:
            chat_area = self.query_one("#chat-area")
            chat_area.scroll_end(animate=False)
        except Exception:
            pass
        
        # 检查是否完成
        if self._streaming_displayed >= len(self._streaming_text):
            self._finish_typewriter_effect()
        else:
            # 添加闪烁光标
            streaming_widget.update(self._streaming_current_content + "[blink]▋[/]")
    
    def _finish_typewriter_effect(self) -> None:
        """完成打字机效果."""
        if self._streaming_timer:
            self._streaming_timer.stop()
            self._streaming_timer = None
        
        # 使用实例变量获取内容
        full_content = getattr(self, '_streaming_current_content', "") or ""
        # 移除光标
        full_content = full_content.replace("[blink]▋[/]", "")
        
        # 将完整内容写入 RichLog
        if full_content and self._streaming_widget_id:
            try:
                log = self.query_one(f"#{self._streaming_widget_id}", RichLog)
                log.write(full_content)
                log.write("\n")
            except Exception:
                pass
        
        # 移除流式组件
        self._remove_streaming_widget()
        
        self._is_streaming = False
        self._streaming_displayed = 0
    
    def is_streaming(self) -> bool:
        """检查是否正在流式输出.
        
        Returns:
            True 如果正在流式输出
        """
        return self._is_streaming
    
    def cancel_streaming(self) -> None:
        """取消当前的流式输出."""
        if self._streaming_timer:
            self._streaming_timer.stop()
            self._streaming_timer = None
        
        self._remove_streaming_widget()
        
        self._is_streaming = False
        self._streaming_text = ""
        self._streaming_widget_id = None
        self._streaming_displayed = 0
        self._streaming_current_content = ""
    
    # ========================================================================
    # 欢迎横幅渲染
    # ========================================================================
    
    def _render_welcome_banner(self) -> None:
        """渲染简洁的欢迎横幅."""
        # ASCII 艺术横幅（来自 CLI 模式）
        welcome_lines = [
            "[bold #8B9A46]░█░█░█▀█░█▀█░█▀▄░█▀▀░█▀█░█▄█░█▀▀[/]",
            "[bold #8B9A46]░█▀█░█▀█░█░█░█░█░▀▀█░█░█░█░█░█▀▀[/]",
            "[bold #8B9A46]░▀░▀░▀░▀░▀░▀░▀▀░░▀▀▀░▀▀▀░▀░▀░▀▀▀[/]",
        ]
        
        # 设置横幅内容
        welcome_widget = self.query_one("#welcome-banner")
        if welcome_widget:
            from rich.text import Text as RichText
            welcome_text = RichText.from_markup("\n".join(welcome_lines))
            welcome_widget.update(welcome_text)
    
    def _format_context(self, tokens: int | None) -> str:
        """格式化 token 数量.
        
        Args:
            tokens: token 数量
            
        Returns:
            格式化后的字符串
        """
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
        """初始化快捷键管理器."""
        self._key_binding_manager = KeyBindingManager()
        
        # 注册默认快捷键
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
        """初始化会话存储服务."""
        if SessionStore:
            try:
                self._session_store = SessionStore()
                self._logger.debug("SessionStore initialized")
                
                # 如果没有指定 session_id，尝试获取或创建默认会话
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
                    # 确保 session_id 对应的会话存在
                    self._session_store.get_or_create_session(
                        model=self.model_name or "",
                        provider=self.provider or "",
                        session_id=self.session_id,
                    )
            except Exception as e:
                self._logger.error(f"Failed to initialize SessionStore: {e}")
                self._session_store = None
    
    def _init_approval_manager(self, approval_mode: str | ApprovalMode) -> None:
        """初始化审批管理器
        
        Args:
            approval_mode: 审批模式
        """
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
    
    # ========================================================================
    # 主题系统方法
    # ========================================================================
    
    def set_theme(self, theme_id: str) -> bool:
        """设置应用主题.
        
        Args:
            theme_id: 主题 ID (default/ares/mono/slate)
            
        Returns:
            True 如果设置成功，False 如果主题不存在
        """
        if not self._theme_manager:
            self._logger.warning("Theme manager not available")
            return False
        
        success = self._theme_manager.set_theme(theme_id)
        if success:
            # 通知用户主题已更改
            display_name = self._theme_manager.get_current_display_name()
            self.notify(f"Theme changed to: {display_name}")
            self._logger.info(f"Theme changed to: {theme_id}")
        else:
            self.notify(f"Theme '{theme_id}' not found")
            self._logger.warning(f"Theme not found: {theme_id}")
        
        return success
    
    def get_current_theme_id(self) -> str:
        """获取当前主题 ID.
        
        Returns:
            当前主题 ID
        """
        if self._theme_manager:
            return self._theme_manager.get_current_theme_id()
        return "default"
    
    def list_available_themes(self) -> list[str]:
        """列出所有可用的主题 ID.
        
        Returns:
            主题 ID 列表
        """
        if self._theme_manager:
            return self._theme_manager.list_theme_ids()
        return ["default"]
    
    def action_change_theme(self) -> None:
        """切换到下一个主题 (Ctrl+Shift+T)."""
        if not self._theme_manager:
            self.notify("Theme manager not available")
            return
        
        # 获取所有主题 ID
        theme_ids = self._theme_manager.list_theme_ids()
        if not theme_ids:
            return
        
        # 获取当前主题的索引
        current_id = self._theme_manager.get_current_theme_id()
        try:
            current_index = theme_ids.index(current_id)
        except ValueError:
            current_index = -1
        
        # 切换到下一个主题（循环）
        next_index = (current_index + 1) % len(theme_ids)
        next_theme_id = theme_ids[next_index]
        
        self.set_theme(next_theme_id)
    
    def action_toggle_transparency(self) -> None:
        """切换半透明背景 (Ctrl+Shift+B).
        
        启用毛玻璃效果，让 TUI 背景半透明显示终端背景。
        """
        if not self._theme_manager:
            self.notify("Theme manager not available")
            return
        
        # 切换透明度状态
        enabled = self._theme_manager.toggle_transparency()
        
        # 更新 UI 样式
        self._update_transparency_styles(enabled)
        
        # 显示通知
        if enabled:
            self.notify("✓ 半透明背景已启用 (毛玻璃效果)")
        else:
            self.notify("✗ 半透明背景已禁用")
    
    def _update_transparency_styles(self, enabled: bool) -> None:
        """更新透明度相关样式.
        
        Args:
            enabled: 是否启用透明度
        """
        # 需要更新的组件及其对应的透明样式类
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
                        # 添加透明样式类
                        widget.add_class(transparent_class)
                    else:
                        # 移除透明样式类
                        widget.remove_class(transparent_class)
                        
                except Exception:
                    # 组件可能不存在，跳过
                    pass
            
            # 更新页脚快捷键提示
            self._update_footer_hint()
            
        except Exception as e:
            self._logger.debug(f"Failed to update transparency styles: {e}")
    
    def _update_footer_hint(self) -> None:
        """更新页脚快捷键提示，添加透明度切换提示。"""
        try:
            footer = self.query_one("#app-footer")
            if footer:
                # 检测透明度状态
                is_transparent = (
                    self._theme_manager.is_transparency_enabled() 
                    if self._theme_manager else False
                )
                
                # 添加透明度指示符
                trans_indicator = "◐" if is_transparent else "○"
                trans_text = f" {trans_indicator} 透明度" if is_transparent else ""
                
                # 更新页脚内容
                footer.query_one("#footer-content", Horizontal).mount(
                    Static(
                        f"[#6e7681]|[/] [#c9d1d9][[/][#30363d]Ctrl+Shift+B[/][#c9d1d9]][/] 透明度",
                        classes="footer-hint"
                    ),
                    after=footer.query_one("#footer-content").last_child
                )
        except Exception:
            pass
    
    def is_transparency_enabled(self) -> bool:
        """检查透明度是否启用.
        
        Returns:
            True 如果透明度已启用
        """
        if self._theme_manager:
            return self._theme_manager.is_transparency_enabled()
        return False
    
    # ========================================================================
    # Markdown 渲染方法
    # ========================================================================
    
    def action_toggle_markdown(self) -> None:
        """切换 Markdown 渲染 (Ctrl+Shift+M)."""
        self._markdown_enabled = not self._markdown_enabled
        
        if self._markdown_enabled:
            if self._markdown_renderer and self._markdown_renderer.is_available():
                self.notify_info("✓ Markdown 渲染已启用")
            else:
                self.notify_warning("Markdown 渲染未安装（pip install mistune）")
        else:
            self.notify_info("✗ Markdown 渲染已禁用")
        
        self._logger.debug(f"Markdown rendering: {self._markdown_enabled}")
    
    def is_markdown_enabled(self) -> bool:
        """检查 Markdown 渲染是否启用.
        
        Returns:
            True 如果 Markdown 渲染已启用
        """
        return self._markdown_enabled
    
    def is_markdown_available(self) -> bool:
        """检查 Markdown 渲染是否可用（已安装依赖）。
        
        Returns:
            True 如果 Markdown 渲染库已安装
        """
        return self._markdown_renderer is not None and self._markdown_renderer.is_available()
    
    def get_markdown_features(self) -> dict:
        """获取 Markdown 功能特性.
        
        Returns:
            功能特性字典
        """
        if is_markdown_available:
            return is_markdown_available()
        return {"mistune": False, "pygments": False, "code_highlight": False}
    
    def render_markdown(self, text: str) -> str:
        """渲染 Markdown 文本.
        
        Args:
            text: Markdown 格式的文本
            
        Returns:
            渲染后的文本
        """
        if not self._markdown_enabled or not self._markdown_renderer:
            return text
        
        try:
            return self._markdown_renderer.render(text)
        except Exception as e:
            self._logger.debug(f"Markdown render failed: {e}")
            return text
    
    # ========================================================================
    # 动画通知方法
    # ========================================================================
    
    def notify_animated(
        self,
        message: str,
        notification_type: str = NotificationType.INFO,
        duration: float = 3.0,
    ) -> None:
        """显示带动画的通知.
        
        Args:
            message: 通知消息
            notification_type: 通知类型 (info/success/warning/error)
            duration: 显示时长（秒）
        """
        # 获取动画图标
        icon = NotificationType.get_icon(notification_type)
        
        # 根据类型添加不同的前缀和动画效果
        if notification_type == NotificationType.SUCCESS:
            # 成功通知：弹跳动画
            animated_msg = f"✅ {message}"
        elif notification_type == NotificationType.WARNING:
            # 警告通知：脉冲动画
            animated_msg = f"⚠️ {message}"
        elif notification_type == NotificationType.ERROR:
            # 错误通知：抖动动画
            animated_msg = f"❌ {message}"
        else:
            # 信息通知：滑入动画
            animated_msg = f"ℹ️ {message}"
        
        # 使用 Textual 内置的通知系统
        self.notify(
            animated_msg,
            timeout=duration,
            title=notification_type.upper() if notification_type != NotificationType.INFO else "通知",
        )
        
        self._logger.debug(f"Animated notification: [{notification_type}] {message}")
    
    def notify_success(self, message: str, duration: float = 3.0) -> None:
        """显示成功通知（带弹跳动画）.
        
        Args:
            message: 通知消息
            duration: 显示时长（秒）
        """
        self.notify_animated(message, NotificationType.SUCCESS, duration)
    
    def notify_warning(self, message: str, duration: float = 4.0) -> None:
        """显示警告通知（带脉冲动画）.
        
        Args:
            message: 通知消息
            duration: 显示时长（秒）
        """
        self.notify_animated(message, NotificationType.WARNING, duration)
    
    def notify_error(self, message: str, duration: float = 5.0) -> None:
        """显示错误通知（带抖动动画）.
        
        Args:
            message: 通知消息
            duration: 显示时长（秒）
        """
        self.notify_animated(message, NotificationType.ERROR, duration)
    
    def notify_info(self, message: str, duration: float = 3.0) -> None:
        """显示信息通知（带滑入动画）.
        
        Args:
            message: 通知消息
            duration: 显示时长（秒）
        """
        self.notify_animated(message, NotificationType.INFO, duration)
    
    def show_loading_animation(self, message: str = "加载中...") -> None:
        """显示加载动画通知.
        
        Args:
            message: 加载提示消息
        """
        loading_msg = f"⏳ {message}"
        self.notify(loading_msg, timeout=None, title="LOADING")
    
    def show_progress_notification(
        self,
        progress: float,
        message: str = "",
        total: int = 100,
    ) -> None:
        """显示进度通知.
        
        Args:
            progress: 当前进度 (0.0 - 1.0)
            message: 进度描述
            total: 总量
        """
        # 计算百分比
        percent = int(progress * 100)
        current = int(progress * total)
        
        # 生成进度条
        bar_length = 20
        filled = int(bar_length * progress)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        # 构建消息
        progress_msg = f"{bar} {percent}%"
        if message:
            progress_msg = f"{message}\n{progress_msg}"
        
        # 显示进度
        self.notify(progress_msg, timeout=2.0, title=f"进度 ({current}/{total})")
    
    def apply_skin_from_engine(self) -> bool:
        """从皮肤引擎应用皮肤到当前主题.
        
        Returns:
            True 如果应用成功
        """
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
    
    # ========================================================================
    # 审批流程方法
    # ========================================================================
    
    def request_tool_approval(
        self,
        tool_name: str,
        tool_args: dict,
        callback: callable,
    ) -> bool:
        """请求工具执行的审批
        
        Args:
            tool_name: 工具名称
            tool_args: 工具参数
            callback: 审批结果回调函数，签名为 callback(approved: bool)
            
        Returns:
            True 如果显示审批对话框，否则 False（自动模式或审批已跳过）
        """
        if not self._approval_manager:
            # 没有审批管理器，直接执行
            callback(True)
            return False
        
        if not self._approval_manager.should_approve(tool_name):
            # 不需要审批，直接执行
            self._logger.debug(f"Tool '{tool_name}' does not require approval")
            callback(True)
            return False
        
        # 保存待审批的工具调用
        self._pending_tool_call = {
            "name": tool_name,
            "args": tool_args,
        }
        self._approval_callback = callback
        
        # 显示审批对话框
        self._show_approval_dialog(tool_name, tool_args)
        return True
    
    def _show_approval_dialog(self, tool_name: str, tool_args: dict) -> None:
        """显示审批对话框
        
        Args:
            tool_name: 工具名称
            tool_args: 工具参数
        """
        if not ApprovalDialog:
            # 没有 ApprovalDialog 组件，直接拒绝
            self._logger.warning("ApprovalDialog not available, rejecting operation")
            self._handle_approval_result(False)
            return
        
        # 获取风险等级
        risk_level = self._approval_manager.get_risk_level(tool_name) if self._approval_manager else RiskLevel.MEDIUM
        
        # 生成操作预览
        preview = self._generate_tool_preview(tool_name, tool_args)
        
        # 创建并挂载审批对话框
        dialog = create_approval_dialog(
            operation=tool_name,
            preview=preview,
            risk_level=risk_level,
        )
        
        self._logger.info(f"Showing approval dialog for: {tool_name} (risk: {risk_level.value})")
        
        # 挂载到屏幕
        self.screen.mount(dialog)
    
    def _generate_tool_preview(self, tool_name: str, tool_args: dict) -> str:
        """生成工具预览文本
        
        Args:
            tool_name: 工具名称
            tool_args: 工具参数
            
        Returns:
            预览文本
        """
        preview_parts = []
        
        for key, value in tool_args.items():
            # 截断过长的值
            value_str = str(value)
            if len(value_str) > 50:
                value_str = value_str[:47] + "..."
            
            # 隐藏敏感字段
            if key.lower() in ("password", "token", "secret", "key", "api_key"):
                value_str = "***"
            
            preview_parts.append(f"{key}={value_str}")
        
        preview = "; ".join(preview_parts)
        
        # 截断过长的预览
        if len(preview) > 100:
            preview = preview[:97] + "..."
        
        return preview
    
    def _handle_approval_result(self, approved: bool) -> None:
        """处理审批结果
        
        Args:
            approved: 是否批准
        """
        if self._approval_callback:
            operation = self._pending_tool_call["name"] if self._pending_tool_call else "unknown"
            self._logger.info(f"Approval result for '{operation}': {'approved' if approved else 'rejected'}")
            
            # 调用回调函数
            try:
                self._approval_callback(approved)
            except Exception as e:
                self._logger.error(f"Error in approval callback: {e}")
        
        # 清理状态
        self._pending_tool_call = None
        self._approval_callback = None
    
    def on_approval_confirmed(self, event: ApprovalConfirmed) -> None:
        """处理审批确认事件
        
        Args:
            event: 审批确认事件
        """
        self._handle_approval_result(True)
    
    def on_approval_rejected(self, event: ApprovalRejected) -> None:
        """处理审批拒绝事件
        
        Args:
            event: 审批拒绝事件
        """
        self._handle_approval_result(False)
    
    def set_approval_mode(self, mode: str | ApprovalMode) -> None:
        """设置审批模式
        
        Args:
            mode: 审批模式（auto/suggest/manual）
        """
        if self._approval_manager:
            self._approval_manager.set_mode(mode)
            self._logger.info(f"Approval mode changed to: {mode}")
    
    def get_approval_mode(self) -> ApprovalMode:
        """获取当前审批模式
        
        Returns:
            当前审批模式
        """
        if self._approval_manager:
            return self._approval_manager.mode
        return ApprovalMode.AUTO
    
    def is_sensitive_operation(self, operation: str) -> bool:
        """判断操作是否为敏感操作
        
        Args:
            operation: 操作名称
            
        Returns:
            True 如果是敏感操作
        """
        if self._approval_manager:
            return self._approval_manager.is_sensitive_operation(operation)
        return False
    
    def _restore_session(self, session_id: str) -> list[dict[str, str]]:
        """恢复会话消息历史
        
        Args:
            session_id: 会话 ID
            
        Returns:
            消息历史列表
        """
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
        """检查是否需要自动保存."""
        self._pending_message_count += 1
        if self._pending_message_count >= self._auto_save_interval:
            self._flush_messages()
    
    def _flush_messages(self) -> None:
        """刷新待保存消息到数据库."""
        if self._session_store:
            try:
                count = self._session_store.flush_pending_messages()
                if count > 0:
                    self._logger.debug(f"Flushed {count} pending messages")
                self._pending_message_count = 0
            except Exception as e:
                self._logger.error(f"Failed to flush messages: {e}")
    
    def save_message(self, role: str, content: str, **kwargs) -> None:
        """保存消息到会话
        
        Args:
            role: 消息角色 (user/assistant/system/tool)
            content: 消息内容
            **kwargs: 其他参数（tokens, thinking_content, metadata）
        """
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
        """应用卸载时保存数据."""
        self._flush_messages()
        # 注意：这里不调用 super().on_unmount()，因为 Textual App 可能没有这个方法
        self._logger.debug("Application unmounted, data saved")
        
        # 恢复原始控制台日志处理器
        self._restore_console_handler()
    
    def _restore_console_handler(self) -> None:
        """恢复原始控制台日志处理器（TUI 退出时调用）。"""
        if self._tui_log_handler is not None and self._saved_console_handler is not None:
            try:
                # 移除 TUI handler
                if self._tui_log_handler in logging.root.handlers:
                    logging.root.removeHandler(self._tui_log_handler)
                for logger_name in logging.Logger.manager.loggerDict:
                    logger = logging.getLogger(logger_name)
                    if self._tui_log_handler in logger.handlers:
                        logger.removeHandler(self._tui_log_handler)
                
                # 恢复原始控制台 handler
                if self._saved_console_handler not in logging.root.handlers:
                    logging.root.addHandler(self._saved_console_handler)
            except Exception:
                pass
    
    def _on_sidebar_panel_switch(self, panel_type: str) -> None:
        """处理侧边栏面板切换回调."""
        try:
            sidebar = self.query_one("#sidebar-container-inner")
            if sidebar:
                sidebar.switch_panel(panel_type)
        except Exception as e:
            self._logger.debug(f"Failed to switch sidebar panel: {e}")
    
    def action_toggle_sidebar(self) -> None:
        """切换侧边栏显示."""
        try:
            sidebar = self.query_one("#sidebar-container")
            if sidebar:
                # Textual 只支持 block 或 none
                if sidebar.styles.display == "none":
                    sidebar.styles.display = "block"
                else:
                    sidebar.styles.display = "none"
                self._logger.debug(f"Sidebar toggled, display: {sidebar.styles.display}")
        except Exception as e:
            self._logger.debug(f"Sidebar toggle failed: {e}")
    
    def _get_sidebar_and_switch(self, panel_type: str) -> None:
        """获取侧边栏并切换面板.
        
        Args:
            panel_type: 面板类型 (file_tree, tasks, agent, logs)
        """
        # 确保侧边栏显示
        try:
            sidebar = self.query_one("#sidebar-container")
            if sidebar.styles.display == "none":
                sidebar.styles.display = "block"
        except:
            pass
        
        # 调用面板切换
        self._on_sidebar_panel_switch(panel_type)
    
    def action_switch_to_file_tree(self) -> None:
        """切换到文件树面板 (Ctrl+1)."""
        self._get_sidebar_and_switch("file_tree")
    
    def action_switch_to_tasks(self) -> None:
        """切换到任务面板 (Ctrl+2)."""
        self._get_sidebar_and_switch("tasks")
    
    def action_switch_to_agent(self) -> None:
        """切换到 Agent 面板 (Ctrl+3)."""
        self._get_sidebar_and_switch("agent")
    
    def action_switch_to_logs(self) -> None:
        """切换到日志面板 (Ctrl+4)."""
        self._get_sidebar_and_switch("logs")
    
    def set_agent_status(self, status: str) -> None:
        """设置 Agent 状态指示器
        
        Args:
            status: 状态类型 (online/busy/error)
        """
        self._agent_status = status
        indicator = self.query_one("#status-indicator", Static)
        
        if status == "busy":
            indicator.update("🟡")
            indicator.styles.color = STATUS_BUSY
        elif status == "error":
            indicator.update("🔴")
            indicator.styles.color = STATUS_ERROR
        else:
            indicator.update("🟢")
            indicator.styles.color = STATUS_ONLINE
    
    def action_toggle_help(self) -> None:
        """切换帮助面板显示."""
        self.action_open_help()
    
    def action_open_help(self) -> None:
        """打开帮助面板."""
        if HelpScreen:
            self.push_screen(HelpScreen(
                key_binding_manager=self._key_binding_manager
            ))
            self._logger.debug("Help screen opened")
        else:
            self.notify("Help: q=quit, Ctrl+B=sidebar, Ctrl+T=new tab")
    
    def action_open_command_palette(self) -> None:
        """打开命令面板 (Ctrl+K)."""
        if CommandPaletteScreen:
            self.push_screen(CommandPaletteScreen())
            self._logger.debug("Command palette opened")
        else:
            self.notify("Command palette not available")
    
    def action_open_session_selector(self) -> None:
        """打开会话选择器 (Ctrl+R)."""
        if SessionPickerScreen:
            self.push_screen(SessionPickerScreen(
                current_session_id=self.session_id
            ))
            self._logger.debug("Session picker opened")
        else:
            self.notify(t("tui.session_selector.hint", "Session selector not available"))
    
    def _on_send_button_pressed(self) -> None:
        """处理发送按钮点击."""
        self._submit_user_input()
    
    def _on_text_area_submitted(self) -> None:
        """处理 TextArea 提交（Enter 键）."""
        self._submit_user_input()
    
    def _append_message(self, role: str, content: str, render_markdown: bool = True) -> None:
        """追加消息到聊天区域.

        Args:
            role: 消息角色 ("user", "assistant", "system")
            content: 消息内容
            render_markdown: 是否渲染 Markdown（仅对 assistant 消息生效）
        """
        log = self.query_one("#chat-log", RichLog)
        
        # 检查是否需要渲染 Markdown
        should_render_markdown = (
            render_markdown 
            and self._markdown_enabled 
            and self._markdown_renderer 
            and role == "assistant"
        )
        
        # 如果需要渲染 Markdown，先转换内容
        if should_render_markdown:
            try:
                content = self._markdown_renderer.render(content)
            except Exception as e:
                self._logger.debug(f"Markdown render failed: {e}")
                # 降级：使用原始内容
        
        # 使用 RichText.from_markup() 正确解析 Rich 标记
        if RichText:
            if role == "user":
                # 用户消息：深灰蓝背景 + 蓝色文字
                title = RichText.from_markup("[bold #58a6ff]**You**[/]")
                body = RichText.from_markup(content)
                # 使用 Style 设置背景色，使用 stylize() 应用样式
                if Style:
                    bg_style = Style(bgcolor="#21262d")
                    body.stylize(bg_style, 0, len(body))
                formatted = title + RichText("\n\n") + body
            elif role == "assistant":
                # 助手消息：无背景
                formatted = RichText.from_markup(f"[bold #3fb950]**Assistant**[/]\n\n{content}")
            elif role == "tool":
                formatted = RichText.from_markup(f"[dim]🛠️ **Tool**[/]\n{content}")
            else:
                formatted = RichText.from_markup(f"[dim]**System**[/]\n\n{content}")
            # 消息之间添加空行分隔
            log.write(NewLine(1))
            log.write(formatted)
        else:
            # 降级：直接写入文本
            if role == "user":
                label = "You"
            elif role == "assistant":
                label = "Assistant"
            elif role == "tool":
                label = "Tool"
            else:
                label = "System"
            log.write(NewLine(1))
            log.write(f"{label}: {content}")
    
    def _history_prev(self) -> None:
        """显示上一条历史记录."""
        text_area = self.query_one("#user-input", TextArea)
        
        if not self._input_history:
            return
        
        # 保存当前输入（如果还没有保存）
        if self._history_index == -1:
            self._current_input = text_area.text
        
        # 移动到上一条
        if self._history_index < len(self._input_history) - 1:
            self._history_index += 1
            text_area.text = self._input_history[self._history_index]
    
    def _history_next(self) -> None:
        """显示下一条历史记录."""
        text_area = self.query_one("#user-input", TextArea)
        
        if self._history_index == -1:
            return
        
        # 移动到下一条
        if self._history_index > 0:
            self._history_index -= 1
            text_area.text = self._input_history[self._history_index]
        else:
            # 恢复到原始输入
            self._history_index = -1
            text_area.text = self._current_input
    
    def _submit_from_history(self) -> None:
        """从历史模式提交消息（带历史管理）."""
        text_area = self.query_one("#user-input", TextArea)
        user_input = text_area.text.strip()
        
        if not user_input:
            return
        
        # 添加到历史记录
        if user_input not in self._input_history:
            self._input_history.insert(0, user_input)
            # 限制历史长度
            if len(self._input_history) > 100:
                self._input_history = self._input_history[:100]
        
        # 重置历史索引
        self._history_index = -1
        self._current_input = ""
        
        # 清空输入框
        text_area.text = ""
        
        # 显示用户消息
        self._append_message("user", user_input)
        
        self._logger.debug(f"User input: {user_input[:50]}...")
        
        # 异步调用 Agent 处理
        self.app.call_later(lambda: self._call_agent_async(user_input))
    
    def _submit_user_input(self) -> None:
        """提交用户输入并触发 Agent 处理 (兼容方法)."""
        text_area = self.query_one("#user-input", TextArea)
        user_input = text_area.text.strip()
        
        if not user_input:
            return
        
        # 添加到历史记录
        if user_input not in self._input_history:
            self._input_history.insert(0, user_input)
            if len(self._input_history) > 100:
                self._input_history = self._input_history[:100]
        
        # 重置历史索引
        self._history_index = -1
        self._current_input = ""
        
        # 清空输入框
        text_area.text = ""
        
        # 显示用户消息
        self._append_message("user", user_input)
        
        self._logger.debug(f"User input: {user_input[:50]}...")
        
        # 异步调用 Agent 处理
        self.app.call_later(lambda: self._call_agent_async(user_input))
    
    def _call_agent_async(self, user_input: str) -> None:
        """异步调用 Agent 处理用户输入（非阻塞主线程）。
        
        Args:
            user_input: 用户输入的消息
        """
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        from textual.timer import Timer
        
        # 更新状态为忙碌
        self.set_agent_status("busy")
        
        # 启动加载动画
        self._start_loading_animation()
        
        # 显示加载状态
        self._append_message("system", "🤔 正在思考...")
        
        # 在线程池中执行异步操作
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
        
        # 使用线程池执行（避免阻塞 UI）
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(run_agent)
        executor.shutdown(wait=False)
        
        # 启动定时器轮询结果（非阻塞）
        self._agent_future = future
        self._agent_start_time = __import__("time").time()
        
        # 取消之前的轮询定时器（如果存在）
        if hasattr(self, '_poll_timer') and self._poll_timer is not None:
            self._poll_timer.stop()
        
        # 每 0.3 秒检查一次结果（非阻塞主线程）
        self._poll_timer = self.set_interval(0.3, self._poll_agent_result)
    
    def _poll_agent_result(self) -> None:
        """轮询 Agent 结果（非阻塞主线程）。由 set_interval 调用。"""
        import time
        future = getattr(self, '_agent_future', None)
        if future is None:
            return
        
        if future.done():
            self._poll_timer.stop()
            self._poll_timer = None
            
            # 停止加载动画
            self._stop_loading_animation()
            
            # 恢复状态为空闲
            self.set_agent_status("online")
            
            try:
                response = future.result()
                if response:
                    if hasattr(response, 'content'):
                        content = str(response.content)
                    else:
                        content = str(response)
                else:
                    content = "（无回复）"
                
                # 使用打字机效果显示内容
                self._show_typewriter_message(content)
            except Exception as e:
                # 停止加载动画
                self._stop_loading_animation()
                self.set_agent_status("error")
                self._append_message("system", f"❌ 处理失败: {str(e)}")
            
            self._agent_future = None
            return
        
        # 超时检查
        if time.time() - getattr(self, '_agent_start_time', time.time()) > 60:
            self._poll_timer.stop()
            self._poll_timer = None
            self._append_message("system", "⏱️ 处理超时，请重试")
            self._agent_future = None
    
    def _get_agent(self):
        """获取 Agent 实例.
        
        Returns:
            Agent 实例或 None
        """
        # 如果已经有 agent，直接返回
        if hasattr(self, '_agent') and self._agent:
            return self._agent
        
        # 尝试从外部获取 agent 实例
        # 这需要在 run_textual_mode 中设置
        return getattr(self, '_agent', None)
    
    def _show_typewriter_message(self, content: str) -> None:
        """使用打字机效果显示消息.
        
        Args:
            content: 消息内容
        """
        # 消息之间添加空行分隔
        log = self.query_one("#chat-log", RichLog)
        log.write(NewLine(1))
        
        # 渲染 Markdown（如果启用）- 使用行内渲染避免 HTML 标签问题
        if self._markdown_enabled and self._markdown_renderer and self._markdown_renderer.is_available():
            try:
                content = self._markdown_renderer.render_inline(content)
            except Exception as e:
                self._logger.debug(f"Markdown render failed: {e}")
        
        # 启动打字机效果
        self.start_typewriter_effect(content, "chat-log")
    
    def action_clear_screen(self) -> None:
        """清屏 (Ctrl+L)."""
        log = self.query_one("#chat-log", RichLog)
        if log:
            log.clear()
        self._logger.debug("Screen cleared")
    
    def action_cancel_current(self) -> None:
        """取消当前操作 (Ctrl+C)."""
        self._logger.info("User requested cancel current operation")
        # 清空输入框
        try:
            input_field = self.query_one("#user-input", TextArea)
            input_field.text = ""
            self.set_focus(input_field)
        except:
            pass
        self.notify("已取消当前操作")
    
    def action_quit(self) -> None:
        """退出应用 (Ctrl+Q / q)."""
        self._logger.info("User requested quit")
        # Textual 8.x 使用 exit 方法退出应用
        self.app.exit()
    
    def _on_session_selected(self, event: "SessionPickerScreen.SessionSelected") -> None:
        """处理会话选择事件
        
        Args:
            event: 会话选择事件
        """
        old_session_id = self.session_id
        self.session_id = event.session_id
        
        self._logger.info(f"Session switched: {old_session_id} -> {event.session_id}")
        
        # 刷新欢迎横幅显示新会话
        self._render_welcome_banner()
        
        # 清空当前聊天视图并加载历史消息
        if self._active_tab_id and self._active_tab_id in self._tab_states:
            chat_view = self._tab_states[self._active_tab_id]["chat_view"]
            chat_view.clear_messages()
            
            # 恢复消息历史
            history = self._restore_session(event.session_id)
            for msg in history:
                chat_view.append_message(msg["role"], msg["content"])
        
        self.notify(t("session.switched", "已切换到会话: {title}").format(title=event.session_title))
    
    def _on_session_deleted(self, event: "SessionPickerScreen.SessionDeleted") -> None:
        """处理会话删除事件
        
        Args:
            event: 会话删除事件
        """
        # 如果删除的是当前会话，切换到新会话
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
        """向上滚动 (k)."""
        try:
            content_area = self.query_one("#content-area", VerticalScroll)
            content_area.scroll_up(animate=True)
        except Exception:
            pass
    
    def action_scroll_down(self) -> None:
        """向下滚动 (j)."""
        try:
            content_area = self.query_one("#content-area", VerticalScroll)
            content_area.scroll_down(animate=True)
        except Exception:
            pass
    
    def action_next_tab(self) -> None:
        """切换到下一个标签页 (Ctrl+Tab)."""
        tabs = self.query_one("Tabs", Tabs)
        all_tabs = list(tabs.query("Tab"))
        if not all_tabs:
            return
        
        # 获取当前激活标签的索引
        current_index = -1
        for i, tab in enumerate(all_tabs):
            if tab.id == tabs.active:
                current_index = i
                break
        
        # 计算下一个标签索引（循环）
        next_index = (current_index + 1) % len(all_tabs)
        next_tab = all_tabs[next_index]
        
        if next_tab.id:
            tabs.active = next_tab.id
            self._logger.debug(f"Switched to next tab: {next_tab.id}")
    
    def action_prev_tab(self) -> None:
        """切换到上一个标签页 (Ctrl+Shift+Tab)."""
        tabs = self.query_one("Tabs", Tabs)
        all_tabs = list(tabs.query("Tab"))
        if not all_tabs:
            return
        
        # 获取当前激活标签的索引
        current_index = -1
        for i, tab in enumerate(all_tabs):
            if tab.id == tabs.active:
                current_index = i
                break
        
        # 计算上一个标签索引（循环）
        prev_index = (current_index - 1) % len(all_tabs)
        prev_tab = all_tabs[prev_index]
        
        if prev_tab.id:
            tabs.active = prev_tab.id
            self._logger.debug(f"Switched to previous tab: {prev_tab.id}")
    
    def append_chat_message(self, role: str, content: str) -> None:
        """向聊天日志追加消息.
        
        Args:
            role: 消息角色 (user/assistant)
            content: 消息内容
        """
        log = self.query_one("#chat-log", RichLog)
        if log:
            if role == "user":
                log.write(f"[bold {AVOCADO_BRIGHT}]You:[/] {content}")
            else:
                log.write(f"[bold {AVOCADO_PRIMARY}]Agent:[/] {content}")
    
    def clear_chat(self) -> None:
        """清空聊天日志."""
        log = self.query_one("#chat-log", RichLog)
        if log:
            log.clear()
    
    # ========================================================================
    # 标签页管理方法
    # ========================================================================
    
    def add_tab(self) -> str | None:
        """创建新的标签页.
        
        Returns:
            新标签页的 ID，如果失败则返回 None
        """
        if not ChatView:
            self._logger.warning("ChatView not available")
            return None
        
        self._tab_counter += 1
        tab_id = f"chat-tab-{self._tab_counter}"
        tab_title = t("chat.tab.title", "Chat") + f" {self._tab_counter}"
        
        # 获取 Tabs 组件
        tabs = self.query_one("Tabs", Tabs)
        content_area = self.query_one("#content-area", VerticalScroll)
        
        # 添加标签
        tabs.add_tab(Tab(tab_title, id=tab_id))
        
        # 创建 ChatView
        chat_view = ChatView(tab_id, tab_title)
        content_area.mount(chat_view)
        
        # 保存标签页状态
        self._tab_states[tab_id] = {
            "title": tab_title,
            "chat_view": chat_view,
        }
        
        # 激活新标签页
        tabs.active = tab_id
        self._active_tab_id = tab_id
        self._show_tab_content(tab_id)
        
        self._logger.info(f"Tab created: {tab_id}")
        return tab_id
    
    def close_tab(self, tab_id: str) -> bool:
        """关闭指定的标签页.
        
        Args:
            tab_id: 要关闭的标签页 ID
            
        Returns:
            True 如果关闭成功，False 如果失败（如只剩最后一个标签）
        """
        tabs = self.query_one("Tabs", Tabs)
        content_area = self.query_one("#content-area", VerticalScroll)
        
        # 获取所有标签
        all_tabs = list(tabs.query("Tab"))
        
        # 至少保留一个标签页
        if len(all_tabs) <= 1:
            self.notify(t("chat.tab.cannot_close_last", "Cannot close the last tab"))
            return False
        
        # 获取要关闭的标签
        tab_to_close = tabs.query_one(f"#{tab_id}", Tab)
        if not tab_to_close:
            self._logger.warning(f"Tab not found: {tab_id}")
            return False
        
        # 记录当前激活的标签
        was_active = tabs.active == tab_id
        
        # 移除标签
        tab_to_close.remove()
        
        # 移除对应的 ChatView
        if tab_id in self._tab_states:
            chat_view = self._tab_states[tab_id]["chat_view"]
            chat_view.remove()
            del self._tab_states[tab_id]
        
        # 如果关闭的是激活的标签，切换到其他标签
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
        """显示指定标签页的内容.
        
        Args:
            tab_id: 标签页 ID
        """
        content_area = self.query_one("#content-area", VerticalScroll)
        
        # 隐藏所有 ChatView
        for state in self._tab_states.values():
            chat_view = state["chat_view"]
            if chat_view.parent:
                chat_view.display = False
        
        # 显示当前标签页的 ChatView
        if tab_id in self._tab_states:
            chat_view = self._tab_states[tab_id]["chat_view"]
            chat_view.display = True
    
    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        """处理标签页激活事件.
        
        Args:
            event: 标签页激活事件
        """
        if event.tab:
            tab_id = event.tab.id
            if tab_id:
                self._active_tab_id = tab_id
                self._show_tab_content(tab_id)
                self._logger.debug(f"Tab activated: {tab_id}")
    
    def action_new_tab(self) -> None:
        """Ctrl+T: 新建标签页."""
        self.add_tab()
    
    def action_close_tab(self) -> None:
        """Ctrl+W: 关闭当前标签页."""
        if self._active_tab_id:
            self.close_tab(self._active_tab_id)


# ============================================================================
# 应用启动函数
# ============================================================================

def run_textual_app(
    model_name: str = "Handsome Agent",
    provider: str | None = None,
    cwd: str | None = None,
    session_id: str | None = None,
    context_length: int | None = None,
    approval_mode: str = "suggest",
    initial_theme: str | None = None,
    agent=None,  # Agent 实例
) -> int:
    """启动 Textual TUI 应用.
    
    Args:
        model_name: 模型名称
        provider: 模型提供商
        cwd: 当前工作目录
        session_id: 会话 ID
        context_length: 上下文窗口大小
        approval_mode: 审批模式（auto/suggest/manual）
        initial_theme: 初始主题 ID
        agent: Agent 实例（用于处理用户消息）
        
    Returns:
        退出码
    """
    if not TEXTUAL_AVAILABLE:
        # 使用友好的错误提示
        print(get_textual_install_hint())
        return 1
    
    # 检查环境兼容性
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
        agent=agent,  # 传递 Agent 实例
    )
    
    try:
        return app.run()
    finally:
        # 确保控制台日志在退出时恢复（兜底机制）
        app._restore_console_handler()


# ============================================================================
# 降级辅助函数
# ============================================================================

def check_textual_available() -> bool:
    """检查 Textual 是否可用.
    
    Returns:
        True 如果可用，否则 False
    """
    return TEXTUAL_AVAILABLE


def get_textual_import_error() -> str | None:
    """获取 Textual 导入错误信息.
    
    Returns:
        错误信息字符串，如果可用则返回 None
    """
    if TEXTUAL_AVAILABLE:
        return None
    
    # 返回已捕获的错误信息
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
    """获取 Textual 安装提示.
    
    Returns:
        安装提示字符串
    """
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
    """检查 Textual 是否兼容当前环境.
    
    Returns:
        (是否兼容, 原因描述)
    """
    # 检查 Textual 是否可用
    if not TEXTUAL_AVAILABLE:
        return False, "Textual not installed"
    
    # 检查是否在 TTY 环境
    if not sys.stdout.isatty():
        return False, "Non-TTY environment detected"
    
    # 检查终端是否支持颜色
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
    """创建回退应用（用于非 TTY 或 Textual 不可用时）.
    
    Args:
        model_name: 模型名称
        provider: 模型提供商
        cwd: 当前工作目录
        session_id: 会话 ID
        context_length: 上下文窗口大小
        approval_mode: 审批模式（auto/suggest/manual）
    """
    from cli.components.banner import print_simple_banner
    from cli.components.ui import print_info, print_warning
    
    # 打印欢迎横幅
    print_simple_banner()
    
    # 打印提示信息
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


# ============================================================================
# 模块导出
# ============================================================================

__all__ = [
    "HandsomeAgentApp",
    "run_textual_app",
    "check_textual_available",
    "get_textual_import_error",
    "get_textual_install_hint",
    "is_textual_compatible",
    "create_fallback_app",
    "TEXTUAL_AVAILABLE",
    # 主题颜色（用于横幅等 Rich 标记）
    "AVOCADO_PRIMARY",
    "AVOCADO_BRIGHT",
    "AVOCADO_DIM",
    "AVOCADO_DARK",
    "WHITE",
    "GRAY_DIM",
    "GOLD",
    # 主题系统
    "ThemeManager",
    "get_theme_manager",
    # 通知动画系统
    "NotificationType",
    "NotificationAnimationManager",
    # Markdown 渲染系统
    "MarkdownRenderer",
    "markdown_to_rich",
    "is_markdown_available",
    # 流式输出打字机效果
    "TypewriterEffect",
]


# ============================================================================
# 测试入口
# ============================================================================

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