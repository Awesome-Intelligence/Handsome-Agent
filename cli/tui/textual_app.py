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
    # Textual 8.x 中使用 Key 事件而不是 KeyEvent
    KeyEvent = Key
except ImportError as e:
    TEXTUAL_AVAILABLE = False
    _TEXTUAL_IMPORT_ERROR = str(e)

# 条件导入 typing 工具
if TYPE_CHECKING:
    from textual.widget import Widget

# 主题系统
try:
    from .themes import ThemeManager, get_theme_manager
except ImportError:
    ThemeManager = None
    get_theme_manager = None

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
    from common.logging_manager import get_access_logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    def get_access_logger(*args, **kwargs):
        return logging.getLogger("HandsomeAgent")

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

# Monkeypatch Textual 的 LayerLogger 以修复 Textual 8.x 兼容性问题
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
        ("ctrl+4", "switch_to_context", "Context"),
        ("f1", "open_help", "Help"),
        ("ctrl+/", "open_help", "Help"),
        ("ctrl+r", "open_session_selector", "Session Selector"),
        ("ctrl+l", "clear_screen", "Clear"),
        ("j", "scroll_down", "Scroll Down"),
        ("k", "scroll_up", "Scroll Up"),
        ("ctrl+shift+t", "change_theme", "Change Theme"),
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
}

#chat-log {
    height: 100%;
    width: 100%;
    background: #0d1117;
    padding: 1 2;
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

/* 输入区域 - 固定在底部 */
#input-area {
    height: 5;
    width: 100%;
    background: #161b22;
    dock: bottom;
    border-top: solid #30363d;
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
    width: 20%;
    height: 100%;
    background: #161b22;
    border-left: solid #30363d;
}

#sidebar-tabs {
    height: 3;
    background: #0d1117;
    border-bottom: solid #30363d;
}

#tab-bar {
    height: 100%;
    layout: horizontal;
}

.sidebar-tab {
    background: #21262d;
    color: #8b949e;
    border: none;
    padding: 0 1;
    margin: 1;
    min-width: 3;
}

.sidebar-tab.active {
    background: #30363d;
    color: #c9d1d9;
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
                yield Static(self.model_name or "Handsome Agent", classes="header-model")
                ctx_str = f"[{self._format_context(self.context_length)}]" if self.context_length else ""
                yield Static(ctx_str, classes="header-context")
                cwd_short = self.cwd[-30:] if self.cwd and len(self.cwd) > 30 else (self.cwd or "")
                yield Static(cwd_short, classes="header-cwd")
        
        # 主区域 - 左侧聊天 + 右侧侧边栏
        with Horizontal(id="main-area"):
            # 左侧聊天区域（弹性高度）
            with VerticalScroll(id="chat-area"):
                yield Static("", id="welcome-banner")
                yield RichLog(id="chat-log", auto_scroll=True)
            
            # 右侧侧边栏
            if SidebarContainer and SidebarTabBar:
                with Container(id="sidebar-container"):
                    yield SidebarTabBar(on_switch=self._on_sidebar_panel_switch)
                    yield SidebarContainer(cwd=self.cwd, agent=self._agent)
        
        # 自定义 Footer - 显示状态信息
        with Container(id="app-footer"):
            with Horizontal(id="footer-content"):
                yield Static("tokens: 0", classes="footer-token")
                yield Static("Ctrl+B: 侧边栏 | Ctrl+K: 命令 | Ctrl+L: 清屏", classes="footer-hint")
        
        # 输入区域（固定在底部）
        with Container(id="input-area"):
            yield TextArea(
                id="user-input",
                classes="input-field",
                placeholder="输入消息... (Ctrl+Enter 换行, Enter 发送)",
            )
    
    def on_key(self, event: KeyEvent) -> None:
        """处理全局键盘事件.
        
        - Ctrl+1/2/3/4: 侧边栏面板切换
        """
        # 检查 Ctrl 键是否按下
        if event.control and event.key in ['1', '2', '3', '4']:
            # 直接调用面板切换方法
            if event.key == '1':
                self.action_switch_to_file_tree()
            elif event.key == '2':
                self.action_switch_to_tasks()
            elif event.key == '3':
                self.action_switch_to_agent()
            elif event.key == '4':
                self.action_switch_to_context()
            event.prevent_default()
            event.stop()
            return
    
    def _on_text_area_key_down(self, event: Key) -> None:
        """处理 TextArea 按键事件.
        
        - Enter: 发送消息
        - ↑/↓: 历史导航
        """
        from textual.widgets import TextArea
        
        # 获取按下的键
        key = event.key
        
        # 检查 Ctrl 键是否按下
        is_ctrl = False
        if hasattr(event, 'control') and event.control:
            is_ctrl = True
        
        # Ctrl+数字键已经在全局事件中处理
        if is_ctrl and key in ['1', '2', '3', '4']:
            return
        
        # 处理 Enter 键 - 发送消息
        if str(key) == 'enter':
            # 检查是否有修饰键（简单检查 event 的属性）
            has_modifier = False
            if hasattr(event, 'control') and event.control:
                has_modifier = True
            if hasattr(event, 'shift') and event.shift:
                has_modifier = True
            if hasattr(event, 'alt') and event.alt:
                has_modifier = True
            
            if not has_modifier:
                # Enter: 发送消息
                self._submit_from_history()
                event.prevent_default()
                event.stop()
            # 如果有修饰键，则允许 TextArea 默认处理（插入换行）
            return
        
        # 处理方向键 - 历史导航
        if str(key) == 'up':
            self._history_prev()
            event.prevent_default()
            event.stop()
            return
        
        if str(key) == 'down':
            self._history_next()
            event.prevent_default()
            event.stop()
            return
    
    def on_mount(self) -> None:
        """应用挂载时初始化."""
        self._logger.info("Textual UI mounted")
        self._render_welcome_banner()
        
        # 注册事件监听器
        self._register_event_listeners()
        
        # 聚焦到输入框（TextArea）
        self.set_focus(self.query_one("#user-input", TextArea))
    
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
    
    def _render_welcome_banner(self) -> None:
        """渲染简洁的欢迎横幅."""
        i18n = get_i18n()
        
        # 简洁的欢迎横幅（参考 CodeWhale 风格）
        welcome_lines = [
            f"[bold #58a6ff]Welcome to Handsome Agent[/]",
            f"[dim]Ask questions or give instructions below...[/]",
        ]
        
        # 设置横幅内容
        welcome_widget = self.query_one("#welcome-banner")
        if welcome_widget:
            welcome_widget.update("\n".join(welcome_lines))
    
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
            panel_type: 面板类型 (file_tree, tasks, agent, context)
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
    
    def action_switch_to_context(self) -> None:
        """切换到上下文面板 (Ctrl+4)."""
        self._get_sidebar_and_switch("context")
    
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
    
    def _append_message(self, role: str, content: str) -> None:
        """追加消息到聊天区域.
        
        Args:
            role: 消息角色 ("user", "assistant", "system")
            content: 消息内容
        """
        log = self.query_one("#chat-log", RichLog)
        from rich.panel import Panel
        from rich.text import Text
        from datetime import datetime
        
        # 根据角色选择样式
        if role == "user":
            panel = Panel(
                content,
                title="[cyan]You[/]",
                style="cyan",
                border_style="cyan",
                padding=(0, 1)
            )
        elif role == "assistant":
            panel = Panel(
                content,
                title="[green]Agent[/]",
                style="green",
                border_style="green",
                padding=(0, 1)
            )
        else:  # system
            panel = Panel(
                content,
                title="[yellow]System[/]",
                style="yellow",
                border_style="yellow",
                padding=(0, 1)
            )
        
        log.write(panel)
    
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
        """异步调用 Agent 处理用户输入.
        
        Args:
            user_input: 用户输入的消息
        """
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        # 显示加载状态
        self._append_message("system", "🤔 正在思考...")
        
        # 在线程池中执行异步操作
        def run_agent():
            try:
                # 获取 Agent 实例
                agent = self._get_agent()
                if agent:
                    # 获取事件循环并运行协程
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        # agent.chat 可能返回协程，需要等待
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
        
        # 轮询结果（简单实现）
        import time
        max_wait = 60  # 最多等待 60 秒
        start_time = time.time()
        while not future.done():
            if time.time() - start_time > max_wait:
                self._append_message("system", "⏱️ 处理超时，请重试")
                return
            time.sleep(0.5)
        
        # 获取结果并显示
        try:
            response = future.result()
            if response:
                # 如果是 AgentResponse 对象，提取 content
                if hasattr(response, 'content'):
                    self._append_message("assistant", str(response.content))
                else:
                    self._append_message("assistant", str(response))
            else:
                self._append_message("assistant", "（无回复）")
        except Exception as e:
            self._append_message("system", f"❌ 处理失败: {str(e)}")
    
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
    
    return app.run()


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