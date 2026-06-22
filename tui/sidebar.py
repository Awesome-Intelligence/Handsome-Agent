"""
TUI 侧边栏组件 - 提供文件树、任务、Agent、日志面板
使用 Textual TabbedContent + TabPane 组件实现
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Iterable
from typing_extensions import Self

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.events import Click
from textual.message import Message
from textual.widgets import Static, RichLog, TabbedContent, TabPane, DirectoryTree
from textual.widgets import Tabs
from textual import on


# 图标系统
try:
    from tui.theming import (
        FILE_TYPE_ICONS,
        get_file_icon,
        TASK_STATUS_ICONS,
        AGENT_STATUS_ICONS,
        LOG_LEVEL_ICONS,
        PANEL_ICONS,
    )
except ImportError:
    # 降级方案：使用内联默认值
    FILE_TYPE_ICONS = {".default": "📄"}
    TASK_STATUS_ICONS = {}
    AGENT_STATUS_ICONS = {"idle": "🟢", "busy": "🟠"}
    LOG_LEVEL_ICONS = {"INFO": "ℹ️", "DEBUG": "🐛", "WARNING": "⚠️", "ERROR": "❌"}
    PANEL_ICONS = {"file_tree": "📁", "tasks": "📋", "agent": "🤖", "logs": "📜"}

    def get_file_icon(filename: str) -> str:
        ext = Path(filename).suffix.lower()
        return FILE_TYPE_ICONS.get(ext, FILE_TYPE_ICONS[".default"])


# ============================================================================
# 过滤目录树
# ============================================================================


class FilteredDirectoryTree(DirectoryTree):
    """过滤后的目录树组件."""

    BLOCKLIST = {".venv", "node_modules", "__pycache__", ".git", ".idea", ".vscode"}

    def filter_paths(self, paths: Iterable[Path]) -> list[Path]:
        """过滤目录树，隐藏隐藏文件和黑名单目录."""
        result = []
        for path in paths:
            if not path.name.startswith(".") and path.name not in self.BLOCKLIST:
                result.append(path)
        return result


# ============================================================================
# 面板基类
# ============================================================================


class SidebarPane(TabPane):
    """侧边栏面板基类."""

    DEFAULT_CSS = """
    SidebarPane {
        width: 100%;
        height: 100%;
        padding: 1;
    }
    """

    def set_focus_within(self) -> None:
        """设置面板内部焦点（可被子类重写）."""

    def activate(self) -> Self:
        """激活面板并切换到该 Tab."""
        assert self.parent is not None
        if self.id is not None and isinstance(self.parent.parent, TabbedContent):
            self.parent.parent.active = self.id
        return self


# ============================================================================
# 任务面板
# ============================================================================


class TasksPane(SidebarPane):
    """
    任务面板 - 实时显示 Agent 拆分出的任务
    
    功能:
    1. 显示当前执行的任务（置顶，高亮）
    2. 显示所有子任务列表
    3. 显示任务状态和进度
    """
    
    # 内部数据结构
    _tasks: Dict[str, List] = {}  # task_id -> subtasks
    _current_task_id: Optional[str] = None
    _current_subtask_id: Optional[int] = None
    _progress_percent: int = 0
    _expanded_tasks: set = set()  # 展开的任务 ID
    
    # 状态图标
    STATUS_ICONS = {
        "pending": "⏳",
        "running": "🔄",
        "completed": "✅",
        "failed": "❌",
        "error": "❌",
        "cancelled": "➖",
    }
    
    # 默认 CSS
    DEFAULT_CSS = """
    TasksPane {
        width: 100%;
        height: 100%;
    }
    
    TasksPane #tasks-container {
        width: 100%;
        height: 100%;
        padding: 0;
    }
    
    TasksPane #current-task {
        width: 100%;
        padding: 0 1;
        background: $accent 15%;
        border: solid $accent;
        margin-bottom: 1;
    }
    
    TasksPane .task-item {
        padding: 0 1 0 2;
    }
    
    TasksPane .task-item.pending {
        color: $text-muted;
    }
    
    TasksPane .task-item.running {
        color: $accent;
        text-style: bold;
    }
    
    TasksPane .task-item.completed {
        color: $success;
    }
    
    TasksPane .task-item.failed,
    TasksPane .task-item.error {
        color: $error;
    }
    
    TasksPane .task-item.cancelled {
        color: $text-muted;
        text-style: italic;
    }
    
    TasksPane #empty-state {
        color: $text-muted;
        text-style: italic;
    }
    """
    
    def __init__(self) -> None:
        super().__init__(id="tasks", title="任务")
        # 尝试导入消息类型
        try:
            from tui.messages import TaskItem, TasksPaneUpdated, CurrentTaskChanged
            self._has_messages = True
        except ImportError:
            self._has_messages = False
    
    def compose(self) -> ComposeResult:
        """组合子组件."""
        with Vertical(id="tasks-container"):
            # 当前执行任务（动态显示）
            yield Static("", id="current-task")
            
            # 任务列表
            yield Static("[dim]暂无任务[/dim]", id="tasks-list")
    
    # ==================== 消息处理 ====================
    
    def on_mount(self) -> None:
        """组件挂载时初始化."""
        # 订阅消息
        if self._has_messages:
            from tui.messages import TasksPaneUpdated, CurrentTaskChanged
            self._tasks_pane_updated = TasksPaneUpdated
            self._current_task_changed = CurrentTaskChanged
    
    async def _on_tasks_pane_updated(self, event) -> None:
        """处理任务面板更新"""
        self._tasks = event.tasks if hasattr(event, 'tasks') else {}
        self._current_task_id = event.current_task_id if hasattr(event, 'current_task_id') else None
        self._current_subtask_id = event.current_subtask_id if hasattr(event, 'current_subtask_id') else None
        self._progress_percent = event.progress_percent if hasattr(event, 'progress_percent') else 0
        
        self._update_display()
    
    async def _on_current_task_changed(self, event) -> None:
        """处理当前任务变更"""
        self._current_task_id = event.task_id if hasattr(event, 'task_id') else None
        self._current_subtask_id = event.subtask_id if hasattr(event, 'subtask_id') else None
        
        if event.task_id and event.task_id in self._tasks:
            # 更新当前任务显示
            current_task_widget = self.query_one("#current-task", Static)
            if hasattr(event, 'status') and event.status == "running":
                current_task_widget.update(
                    self._format_current_task(event.subtask_title if hasattr(event, 'subtask_title') else "")
                )
    
    # ==================== 显示逻辑 ====================
    
    def _update_display(self) -> None:
        """更新任务列表显示"""
        tasks_list_widget = self.query_one("#tasks-list", Static)
        
        if not self._tasks:
            tasks_list_widget.update("[dim]暂无任务[/dim]")
            return
        
        lines = []
        for task_id, subtasks in self._tasks.items():
            if not subtasks:
                continue
            
            # 获取主任务信息
            main_task = subtasks[0].title if hasattr(subtasks[0], 'title') and subtasks[0].title else "未知任务"
            
            # 任务分组
            lines.append(f"[dim]┌─ {main_task[:30]}[/dim]")
            
            for subtask in subtasks:
                icon = self.STATUS_ICONS.get(
                    subtask.status if hasattr(subtask, 'status') else "pending", 
                    "❓"
                )
                
                # 构建显示行
                title = subtask.title if hasattr(subtask, 'title') else str(subtask)
                display_title = title[:35] if len(title) > 35 else title
                
                if hasattr(subtask, 'status') and subtask.status == "running" and hasattr(subtask, 'progress') and subtask.progress > 0:
                    # 显示进度
                    progress_bar = self._make_progress_bar(subtask.progress)
                    lines.append(f"  {icon} {display_title} {progress_bar}")
                else:
                    lines.append(f"  {icon} {display_title}")
            
            lines.append("[dim]└{'─' * 30}[/dim]")
        
        tasks_list_widget.update("\n".join(lines) if lines else "[dim]暂无任务[/dim]")
    
    def _format_current_task(self, title: str) -> str:
        """格式化当前执行任务"""
        progress_bar = self._make_progress_bar(self._progress_percent)
        icon = self.STATUS_ICONS.get("running", "🔄")
        
        return f"""[bold]{icon} 执行中[/bold]

[accent]{title or "未知任务"}[/accent]

{progress_bar} {self._progress_percent}%
"""
    
    def _make_progress_bar(self, percent: int, width: int = 10) -> str:
        """生成进度条"""
        filled = int(width * percent / 100)
        empty = width - filled
        return f"[success]{'█' * filled}[/success][dim]{'░' * empty}[/dim]"
    
    # ==================== 交互操作 ====================
    
    def toggle_task_expanded(self, task_id: str) -> None:
        """切换任务展开/折叠"""
        if task_id in self._expanded_tasks:
            self._expanded_tasks.discard(task_id)
        else:
            self._expanded_tasks.add(task_id)
        self._update_display()


# ============================================================================
# 文件树面板
# ============================================================================


class FileTreePane(SidebarPane):
    """可交互的文件树面板."""

    class FileSelected(Message):
        """文件选中消息."""

        def __init__(self, path: Path) -> None:
            self.path = path
            super().__init__()

    DEFAULT_CSS = """
    FileTreePane {
        width: 100%;
        height: 100%;
    }

    FileTreePane DirectoryTree {
        height: 100%;
        background: transparent;
    }

    FileTreePane DirectoryTree > .tree--cursor {
        background: $accent 25%;
        color: $text;
    }

    FileTreePane DirectoryTree .tree--node-toggle {
        color: $accent;
    }
    """

    def __init__(self, cwd: str = None) -> None:
        self._cwd = Path(cwd) if cwd else Path.cwd()
        super().__init__(id="file_tree", title="文件")

    def compose(self) -> ComposeResult:
        """组合子组件."""
        yield FilteredDirectoryTree(
            self._cwd,
            id="file-tree-widget",
        )

    @on(DirectoryTree.FileSelected)
    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """处理文件选中事件."""
        event.stop()
        self.post_message(self.FileSelected(Path(event.path)))

    def set_focus_within(self) -> None:
        """设置面板内部焦点."""
        tree = self.query_one(DirectoryTree, None)
        if tree:
            tree.focus(scroll_visible=False)


# ============================================================================
# Agent 面板
# ============================================================================


class AgentPane(SidebarPane):
    """Agent 面板."""

    def __init__(self, agent=None) -> None:
        self._agent = agent
        super().__init__(id="agent", title="Agent")

    def compose(self) -> ComposeResult:
        """组合子组件."""
        idle_icon = AGENT_STATUS_ICONS.get("idle", "🟢")
        yield Static(f"[green]{idle_icon} 空闲[/green]", id="agent-content")


# ============================================================================
# 日志面板
# ============================================================================


class LogsPane(SidebarPane):
    """日志面板."""

    def __init__(self) -> None:
        super().__init__(id="logs", title="日志")

    def compose(self) -> ComposeResult:
        """组合子组件."""
        yield RichLog(id="log-output", auto_scroll=True, max_lines=1000, wrap=True, min_width=1)


# ============================================================================
# 侧边栏容器
# ============================================================================


class SidebarContainer(Vertical, can_focus=False, can_focus_children=True):
    """侧边栏主容器."""

    DEFAULT_CSS = """
    SidebarContainer {
        width: 100%;
        height: 100%;
    }

    SidebarContainer > TabbedContent {
        height: 100%;
    }

    SidebarContainer Tabs {
        dock: top;
    }

    SidebarContainer Tabs Tab {
        color: $text-muted;
    }

    SidebarContainer Tabs Tab:hover {
        background: transparent;
        color: $text;
    }

    SidebarContainer Tabs Tab.active {
        background: transparent;
        color: $accent;
        text-style: bold;
        border-bottom: solid $accent;
    }

    SidebarContainer ContentSwitcher {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("ctrl+left", "previous_tab", "Previous tab", show=False),
        Binding("ctrl+right", "next_tab", "Next tab", show=False),
    ]

    def __init__(self, cwd: str = None, agent=None):
        super().__init__(id="sidebar-container-inner")
        self._cwd = cwd
        self._agent = agent

    def compose(self) -> ComposeResult:
        """组合子组件."""
        # 创建面板实例
        self._tasks_pane = TasksPane()
        self._file_tree_pane = FileTreePane(self._cwd)
        self._agent_pane = AgentPane(self._agent)
        self._logs_pane = LogsPane()

        with TabbedContent():
            yield self._tasks_pane
            yield self._file_tree_pane
            yield self._agent_pane
            yield self._logs_pane

    @property
    def tasks_pane(self) -> TasksPane:
        """任务面板."""
        return self._tasks_pane

    @property
    def file_tree_pane(self) -> FileTreePane:
        """文件树面板."""
        return self._file_tree_pane

    @property
    def agent_pane(self) -> AgentPane:
        """Agent 面板."""
        return self._agent_pane

    @property
    def logs_pane(self) -> LogsPane:
        """日志面板."""
        return self._logs_pane

    def switch_to_panel(self, panel_id: str) -> None:
        """切换到指定面板.

        Args:
            panel_id: 面板 ID (tasks, file_tree, agent, logs)
        """
        tabs = self.query_one(Tabs)
        if panel_id in ["tasks", "file_tree", "agent", "logs"]:
            tabs.active = panel_id

    @on(Tabs.TabActivated)
    def on_tab_activated(self, event: Tabs.TabActivated) -> None:
        """Tab 切换时更新颜色."""
        # 获取当前主题颜色（从父组件或默认值）
        active_color = getattr(self, '_active_tab_color', '#B180D7')
        self.update_tab_colors(active_color)

    def set_active_color(self, color: str) -> None:
        """设置激活 Tab 的颜色.

        Args:
            color: 颜色值（十六进制）
        """
        self._active_tab_color = color
        self.update_tab_colors(color)

    def action_previous_tab(self) -> None:
        """切换到上一个 Tab."""
        tabs = self.query_one(Tabs)
        tabs.action_previous_tab()
        self.focus_active_tab()

    def action_next_tab(self) -> None:
        """切换到下一个 Tab."""
        tabs = self.query_one(Tabs)
        tabs.action_next_tab()
        self.focus_active_tab()

    def focus_active_tab(self) -> None:
        """聚焦当前激活的 Tab 内容."""
        if active := self.query_one(Tabs).active:
            self.query_one(f"SidebarPane#{active}", SidebarPane).set_focus_within()

    def update_tab_colors(self, active_color: str) -> None:
        """更新侧边栏 Tab 颜色.

        Args:
            active_color: 激活状态的 Tab 颜色（十六进制）
        """
        tabs = self.query_one(Tabs)
        for tab in tabs.query("Tab"):
            if tab.id == tabs.active:
                tab.styles.color = active_color
                tab.styles.border_bottom = f"solid {active_color}"
            else:
                tab.styles.color = ""
                tab.styles.border_bottom = ""


# ============================================================================
# 保留的辅助类（用于向后兼容）
# ============================================================================


class SidebarTabBar(Static):
    """侧边栏标签栏（已弃用，保留用于兼容）."""

    def __init__(self, on_switch: callable = None):
        super().__init__()
        self._on_switch = on_switch

    def compose(self) -> ComposeResult:
        """组合子组件."""
        yield Static("[dim]请使用 TabbedContent 切换面板[/dim]", id="deprecated-tabbar")


# ============================================================================
# 日志格式化辅助函数
# ============================================================================


def get_log_level_icon(level: str) -> str:
    """根据日志级别获取图标.

    Args:
        level: 日志级别字符串

    Returns:
        对应的 Emoji 图标
    """
    return LOG_LEVEL_ICONS.get(level.upper(), "ℹ️")


def format_log_entry(level: str, message: str) -> str:
    """格式化带图标的日志条目.

    Args:
        level: 日志级别
        message: 日志消息

    Returns:
        格式化的日志字符串（带颜色）
    """
    icon = get_log_level_icon(level)
    # 根据级别选择颜色
    color_map = {
        "DEBUG": "#8b949e",  # 灰色
        "INFO": "#58a6ff",  # 蓝色
        "WARNING": "#f0883e",  # 橙色
        "WARN": "#f0883e",  # 橙色
        "ERROR": "#f85149",  # 红色
        "ERR": "#f85149",  # 红色
        "CRITICAL": "#f85149",  # 红色
        "FATAL": "#f85149",  # 红色
        "SUCCESS": "#3fb950",  # 绿色
    }
    color = color_map.get(level.upper(), "#c9d1d9")
    return f"{icon} [{color}]{level}[/]  {message}"


# ============================================================================
# 任务格式化辅助函数
# ============================================================================


def get_task_status_icon(status: str) -> str:
    """根据任务状态获取图标.

    Args:
        status: 任务状态字符串

    Returns:
        对应的 Emoji 图标
    """
    return TASK_STATUS_ICONS.get(status.lower(), "📋")


def format_task_item(title: str, status: str = "todo", priority: str = "normal") -> str:
    """格式化带图标的任务项.

    Args:
        title: 任务标题
        status: 任务状态
        priority: 任务优先级

    Returns:
        格式化的任务字符串（带图标）
    """
    status_icon = get_task_status_icon(status)
    return f"{status_icon} {title}"


# ============================================================================
# 模块导出
# ============================================================================

__all__ = [
    "SidebarContainer",
    "SidebarPane",
    "TasksPane",
    "FileTreePane",
    "FilteredDirectoryTree",
    "AgentPane",
    "LogsPane",
    "SidebarTabBar",
    "get_log_level_icon",
    "format_log_entry",
    "get_task_status_icon",
    "format_task_item",
]