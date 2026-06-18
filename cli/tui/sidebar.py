"""
TUI 侧边栏组件 - 提供文件树、任务、Agent、日志面板
使用 Textual TabbedContent + TabPane 组件实现
"""

from pathlib import Path
from typing_extensions import Self

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Static, RichLog, TabbedContent, TabPane
from textual.widgets import Tabs

# 图标系统
try:
    from cli.tui.themes import (
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
        _, ext = Path(filename).suffix.lower()
        return FILE_TYPE_ICONS.get(ext, FILE_TYPE_ICONS[".default"])


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
    """任务面板."""

    def __init__(self) -> None:
        super().__init__(id="tasks", title="任务")

    def compose(self) -> ComposeResult:
        """组合子组件."""
        yield Static("[dim]暂无任务[/dim]", id="tasks-content")


# ============================================================================
# 文件树面板
# ============================================================================


class FileTreePane(SidebarPane):
    """文件树面板."""

    def __init__(self, cwd: str = None) -> None:
        self._cwd = cwd
        super().__init__(id="file_tree", title="文件")

    def compose(self) -> ComposeResult:
        """组合子组件."""
        yield Static(self._build_file_tree(), id="file-tree-content")

    def _build_file_tree(self) -> str:
        """构建文件树."""
        lines = []
        cwd = Path(self._cwd) if self._cwd else Path.cwd()
        try:
            items = sorted(cwd.iterdir(), key=lambda p: (not p.is_dir(), p.name))
            for item in items[:15]:
                if item.is_dir():
                    lines.append(f"[cyan]📁 {item.name}/[/cyan]")
                else:
                    # 使用 get_file_icon 获取文件图标
                    icon = get_file_icon(item.name)
                    ext = item.suffix.lower()
                    # 根据文件类型选择颜色
                    code_exts = {'.py', '.rs', '.js', '.ts', '.go', '.java', '.c', '.cpp', '.cs', '.rb'}
                    doc_exts = {'.md', '.txt', '.pdf', '.doc', '.docx'}
                    if ext in code_exts:
                        lines.append(f"[green]{icon} {item.name}[/green]")
                    elif ext in doc_exts:
                        lines.append(f"[yellow]{icon} {item.name}[/yellow]")
                    else:
                        lines.append(f"{icon} {item.name}")
            if len(items) > 15:
                lines.append(f"[dim]... 还有 {len(items) - 15} 个项目[/dim]")
        except Exception as e:
            lines.append(f"[red]错误: {e}[/red]")
        return '\n'.join(lines)


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
    "AgentPane",
    "LogsPane",
    "SidebarTabBar",  # 保留用于向后兼容
    # 辅助函数
    "get_log_level_icon",
    "format_log_entry",
    "get_task_status_icon",
    "format_task_item",
]
