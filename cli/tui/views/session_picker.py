#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Session Picker View - Textual TUI Session Selector

🚪 Access - 💬 CLI - TUI Views - SessionPicker

提供会话选择功能，支持：
- 会话列表显示（标题、创建时间、消息数量）
- 实时搜索过滤
- 删除会话
- 键盘导航
- 选择后恢复会话上下文

Features:
- 实时搜索
- 键盘导航（↑/↓/j/k）
- 选择后恢复消息历史
- 删除确认
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

# Textual 框架导入（带降级机制）
TEXTUAL_AVAILABLE = True
try:
    from textual.app import ComposeResult
    from textual.screen import ModalScreen
    from textual.widgets import Static, Input, ListView, ListItem, Button
    from textual.containers import Container, Horizontal
    from textual.message import Message
    from textual.widget import Widget
except ImportError:
    TEXTUAL_AVAILABLE = False
    ModalScreen = object  # type: ignore
    Static = object  # type: ignore
    Input = object  # type: ignore
    ListView = object  # type: ignore
    ListItem = object  # type: ignore
    Container = object  # type: ignore
    Horizontal = object  # type: ignore
    Message = object  # type: ignore
    Widget = object  # type: ignore

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


# ============================================================================
# 主题颜色常量（高雅紫）
# ============================================================================

AVOCADO_PRIMARY = "#B180D7"       # rgb(177,128,215) - 主色
AVOCADO_BRIGHT = "#C9A0E0"        # rgb(201,160,224) - 亮色
AVOCADO_DIM = "#8B5CAC"           # rgb(139,92,172) - 暗色
AVOCADO_DARK = "#6B4EA8"          # rgb(107,78,168) - 深色
WHITE = "white"
GRAY_DIM = "#888888"
GOLD = "#FFD700"
RED = "#FF6B6B"


# ============================================================================
# Session Item 数据类
# ============================================================================

@dataclass
class SessionItem:
    """会话列表项
    
    Attributes:
        id: 会话 ID
        title: 会话标题
        created_at: 创建时间
        message_count: 消息数量
        model: 使用的模型
    """
    id: str
    title: str
    created_at: Optional[str] = None
    message_count: int = 0
    model: str = ""
    
    def matches(self, query: str) -> bool:
        """检查会话是否匹配查询
        
        Args:
            query: 搜索查询
            
        Returns:
            True 如果匹配，否则 False
        """
        query = query.lower().strip()
        if not query:
            return True
        
        # 匹配标题
        if query in self.title.lower():
            return True
        
        # 匹配模型
        if query in self.model.lower():
            return True
        
        return False


# ============================================================================
# Session Picker CSS
# ============================================================================

SESSION_PICKER_CSS = """
SessionPickerScreen {
    background: $avocado_dark;
}

#picker-container {
    width: 70;
    height: auto;
    max-height: 24;
    margin: 1 2;
    background: $surface;
    border: solid $avocado_primary;
    border-title-style: bold;
    padding: 0 1;
}

#search-input {
    width: 100%;
    margin: 1 0;
    border: solid $avocado_dim;
}

#search-input:focus {
    border: solid $avocado_bright;
}

#session-list {
    height: 14;
    width: 100%;
    padding: 0;
}

.session-item {
    width: 100%;
    height: auto;
    padding: 0 1;
}

.session-item:hover {
    background: $avocado_dim;
}

.session-item:focus {
    background: $avocado_primary;
}

.session-title {
    width: 100%;
    color: $avocado_bright;
    text-style: bold;
}

.session-meta {
    width: 100%;
    color: $gray_dim;
}

.session-delete {
    width: 100%;
    color: $red;
}

#action-bar {
    width: 100%;
    height: auto;
    padding: 1 0;
}

#action-bar Button {
    margin-right: 1;
}

#hint-bar {
    width: 100%;
    height: auto;
    padding: 1 0;
    color: $gray_dim;
}

#empty-hint {
    width: 100%;
    height: 5;
    content-align: center middle;
    color: $gray_dim;
}
"""


# ============================================================================
# SessionPickerScreen - 会话选择器模态窗口
# ============================================================================

class SessionPickerScreen(ModalScreen):
    """会话选择器模态窗口
    
    提供会话选择功能，支持：
    - 模糊搜索会话
    - 键盘导航
    - 删除会话
    - 选择后恢复上下文
    
    Messages:
        SessionSelected: 会话选择事件
        SessionDeleted: 会话删除事件
        PickerClosed: 面板关闭事件
    """
    
    CSS = SESSION_PICKER_CSS
    
    # 会话选择消息
    class SessionSelected(Message):
        """会话选择消息"""
        def __init__(self, sender: Widget, session_id: str, session_title: str) -> None:
            super().__init__()
            self.session_id = session_id
            self.session_title = session_title
    
    # 会话删除消息
    class SessionDeleted(Message):
        """会话删除消息"""
        def __init__(self, sender: Widget, session_id: str) -> None:
            super().__init__()
            self.session_id = session_id
    
    # 面板关闭消息
    class PickerClosed(Message):
        """面板关闭消息"""
        pass
    
    def __init__(
        self,
        current_session_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """初始化会话选择器
        
        Args:
            current_session_id: 当前会话 ID（用于高亮显示）
            **kwargs: 传递给父类的参数
        """
        super().__init__(**kwargs)
        self._current_session_id = current_session_id
        self._sessions: list[SessionItem] = []
        self._filtered_sessions: list[SessionItem] = []
        self._selected_index: int = 0
        self._logger = get_access_logger("SessionPicker", sublayer="tui")
        self._i18n = get_i18n()
        
        # 删除确认状态
        self._delete_confirm_index: Optional[int] = None
        
        # 加载会话数据
        self._load_sessions()
    
    def _load_sessions(self) -> None:
        """从数据库加载会话列表"""
        try:
            from ..services.session_store import SessionStore
            
            store = SessionStore()
            session_list = store.list_sessions(limit=50)
            
            self._sessions = [
                SessionItem(
                    id=s.id,
                    title=s.title or self._i18n.t("session.default_title", "新会话"),
                    created_at=s.created_at.strftime("%Y-%m-%d %H:%M") if s.created_at else "",
                    message_count=s.message_count,
                    model=s.model or "",
                )
                for s in session_list
            ]
            self._filtered_sessions = self._sessions.copy()
            
            self._logger.debug(f"Loaded {len(self._sessions)} sessions")
        except Exception as e:
            self._logger.error(f"Failed to load sessions: {e}")
            self._sessions = []
            self._filtered_sessions = []
    
    def _filter_sessions(self, query: str) -> None:
        """过滤会话列表
        
        Args:
            query: 搜索查询
        """
        self._filtered_sessions = [
            s for s in self._sessions
            if s.matches(query)
        ]
        self._selected_index = 0
        self._delete_confirm_index = None
    
    def _delete_session_at_index(self, index: int) -> None:
        """删除指定索引的会话
        
        Args:
            index: 列表索引
        """
        if 0 <= index < len(self._filtered_sessions):
            session = self._filtered_sessions[index]
            
            try:
                from ..services.session_store import SessionStore
                
                store = SessionStore()
                store.delete_session(session.id)
                
                # 从列表中移除
                self._sessions = [s for s in self._sessions if s.id != session.id]
                self._filter_sessions("")
                
                self._logger.info(f"Session deleted: {session.id}")
                self.post_message(self.SessionDeleted(self, session.id))
            except Exception as e:
                self._logger.error(f"Failed to delete session: {e}")
    
    def compose(self) -> ComposeResult:
        """组合组件
        
        Returns:
            组件生成器
        """
        # 标题
        title = self._i18n.t("tui.session_picker.title", "会话选择器")
        yield Static(
            f"[bold {AVOCADO_BRIGHT}]📋 {title}[/]",
            id="picker-title"
        )
        
        # 搜索输入
        placeholder = self._i18n.t("tui.session_picker.search_hint", "搜索会话...")
        yield Input(
            placeholder=placeholder,
            id="search-input"
        )
        
        # 会话列表
        yield ListView(id="session-list")
        
        # 空状态提示
        empty_text = self._i18n.t("tui.session_picker.empty", "暂无会话记录")
        yield Static(
            empty_text,
            id="empty-hint"
        )
        
        # 操作栏
        with Horizontal(id="action-bar"):
            new_text = self._i18n.t("tui.session_picker.new_session", "新建会话")
            yield Button(
                new_text,
                id="new-session-button",
                variant="primary"
            )
        
        # 提示栏
        hint_up = self._i18n.t("tui.session_picker.hint_up", "↑/k")
        hint_down = self._i18n.t("tui.session_picker.hint_down", "↓/j")
        hint_enter = self._i18n.t("tui.session_picker.hint_enter", "Enter")
        hint_esc = self._i18n.t("tui.session_picker.hint_esc", "Esc")
        hint_delete = self._i18n.t("tui.session_picker.hint_delete", "D")
        yield Static(
            f"[{GRAY_DIM}]{hint_up} {hint_down} 导航  |  {hint_enter} 选择  |  {hint_delete} 删除  |  {hint_esc} 关闭[/]",
            id="hint-bar"
        )
    
    def on_mount(self) -> None:
        """组件挂载时初始化"""
        self._logger.debug("Session picker mounted")
        
        # 设置焦点到搜索框
        input_widget = self.query_one("#search-input", Input)
        input_widget.focus()
        
        # 更新会话列表
        self._update_session_list()
        self._update_empty_hint()
    
    def _update_session_list(self) -> None:
        """更新会话列表"""
        list_view = self.query_one("#session-list", ListView)
        
        # 清空并重建列表
        list_view.clear()
        
        for i, session in enumerate(self._filtered_sessions):
            # 格式化显示
            current_marker = " ▶" if session.id == self._current_session_id else ""
            meta_parts = []
            if session.created_at:
                meta_parts.append(session.created_at)
            if session.message_count > 0:
                msg_text = self._i18n.t("session.message_count", "{count} 条消息")
                meta_parts.append(msg_text.format(count=session.message_count))
            if session.model:
                meta_parts.append(session.model)
            
            meta_text = " · ".join(meta_parts) if meta_parts else ""
            
            # 判断是否处于删除确认状态
            if self._delete_confirm_index == i:
                confirm_text = self._i18n.t("session.delete_confirm", "确认删除?")
                item_content = (
                    f"[{RED}]{confirm_text}[/{RED}]"
                    f"[{GRAY_DIM}] - {session.title}[/{GRAY_DIM}]"
                )
            else:
                item_content = (
                    f"[{AVOCADO_BRIGHT}]{session.title}{current_marker}[/{AVOCADO_BRIGHT}]"
                    f"[{GRAY_DIM}] - {meta_text}[/{GRAY_DIM}]"
                )
            
            item = ListItem(
                Static(item_content),
                id=f"session-{session.id}"
            )
            list_view.append(item)
        
        # 选择第一个或保持当前选择
        max_index = len(self._filtered_sessions) - 1
        if self._selected_index > max_index:
            self._selected_index = max(0, max_index)
        
        if self._filtered_sessions:
            list_view.index = self._selected_index
    
    def _update_empty_hint(self) -> None:
        """更新空状态提示"""
        empty_hint = self.query_one("#empty-hint", Static)
        if self._filtered_sessions:
            empty_hint.display = False
        else:
            empty_hint.display = True
    
    def _select_previous(self) -> None:
        """选择上一个会话"""
        list_view = self.query_one("#session-list", ListView)
        if list_view.index is not None and list_view.index > 0:
            list_view.index -= 1
            self._selected_index = list_view.index
            self._delete_confirm_index = None
    
    def _select_next(self) -> None:
        """选择下一个会话"""
        list_view = self.query_one("#session-list", ListView)
        max_index = len(self._filtered_sessions) - 1
        if list_view.index is not None and list_view.index < max_index:
            list_view.index += 1
            self._selected_index = list_view.index
            self._delete_confirm_index = None
    
    def _select_session(self) -> None:
        """选择当前会话"""
        if not self._filtered_sessions:
            return
        
        session = self._filtered_sessions[self._selected_index]
        self._logger.info(f"Session selected: {session.id}")
        
        # 发送选择消息
        self.post_message(self.SessionSelected(self, session.id, session.title))
        
        # 关闭面板
        self._close()
    
    def _confirm_delete(self) -> None:
        """确认删除当前会话"""
        if not self._filtered_sessions:
            return
        
        if self._delete_confirm_index == self._selected_index:
            # 再次按 D，确认删除
            self._delete_session_at_index(self._selected_index)
            self._delete_confirm_index = None
        else:
            # 进入删除确认状态
            self._delete_confirm_index = self._selected_index
        
        self._update_session_list()
    
    def _cancel_delete(self) -> None:
        """取消删除确认"""
        self._delete_confirm_index = None
        self._update_session_list()
    
    def _create_new_session(self) -> None:
        """创建新会话"""
        try:
            from ..services.session_store import SessionStore
            
            store = SessionStore()
            session_id = store.create_session()
            
            self._logger.info(f"New session created: {session_id}")
            
            # 发送选择消息
            title = self._i18n.t("session.default_title", "新会话")
            self.post_message(self.SessionSelected(self, session_id, title))
            
            # 关闭面板
            self._close()
        except Exception as e:
            self._logger.error(f"Failed to create session: {e}")
    
    def _close(self) -> None:
        """关闭面板"""
        self._logger.debug("Closing session picker")
        
        # 刷新待写入消息
        try:
            from ..services.session_store import SessionStore
            store = SessionStore()
            store.flush_pending_messages()
        except Exception:
            pass
        
        self.post_message(self.PickerClosed())
        self.app.pop_screen()
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """搜索框内容变化时更新列表"""
        if event.input.id == "search-input":
            self._filter_sessions(event.value)
            self._update_session_list()
            self._update_empty_hint()
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """搜索框提交时选择会话"""
        if event.input.id == "search-input":
            self._select_session()
    
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """列表项选中时选择会话"""
        self._select_session()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮按下事件"""
        if event.button.id == "new-session-button":
            self._create_new_session()
    
    def on_key(self, event: "Input.Key") -> None:
        """处理键盘事件"""
        key = event.key
        
        # 上方向键或 k
        if key in ("up", "k"):
            self._select_previous()
            self._update_session_list()
            event.prevent_default()
        
        # 下方向键或 j
        elif key in ("down", "j"):
            self._select_next()
            self._update_session_list()
            event.prevent_default()
        
        # 回车
        elif key == "enter":
            if self._delete_confirm_index is not None:
                self._delete_session_at_index(self._selected_index)
                self._delete_confirm_index = None
            else:
                self._select_session()
            self._update_session_list()
            event.prevent_default()
        
        # Esc
        elif key == "escape":
            if self._delete_confirm_index is not None:
                self._cancel_delete()
            else:
                self._close()
            event.prevent_default()
        
        # D - 删除
        elif key.lower() == "d":
            self._confirm_delete()
            event.prevent_default()


# ============================================================================
# 模块导出
# ============================================================================

__all__ = [
    "SessionPickerScreen",
    "SessionItem",
]