"""
TUI 侧边栏组件 - 提供文件树、目标、Agent、日志面板
使用 Textual TabbedContent + TabPane 组件实现
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Iterable
from typing_extensions import Self

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal
from textual.events import Click
from textual.message import Message
from textual.widgets import Static, Log, TabbedContent, TabPane, DirectoryTree, Input, Button
from textual.widgets import Tabs
from textual import on

# 文件预览支持
try:
    from tui.views.file_preview import FilePreviewScreen
except ImportError:
    FilePreviewScreen = None


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
    PANEL_ICONS = {"file_tree": "📁", "tasks": "📋", "goal": "🎯", "agent": "🤖", "logs": "📜"}

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
# 目标面板配置常量
# ============================================================================


@dataclass(frozen=True)
class GoalPaneConfig:
    """GoalPane 配置常量"""
    # 显示限制
    MAX_GOAL_DISPLAY_LENGTH: int = 50
    MAX_TASK_TITLE_LENGTH: int = 38
    MAX_VISIBLE_TASKS: int = 15
    PROGRESS_BAR_WIDTH: int = 10
    
    # 刷新配置
    REFRESH_INTERVAL: float = 1.0
    
    # 旋转动画
    SPINNER_FRAMES: tuple = ("⚪", "🟡", "🟠")
    
    # Goal 状态图标和文本
    GOAL_STATUS_ICONS: tuple = ("🎯", "⏸️", "✅", "🗑️", "⏰")
    GOAL_STATUS_TEXT: tuple = ("执行中", "已暂停", "已完成", "已清除", "已过期")
    
    # 任务状态图标
    TASK_STATUS_ICONS: tuple = ("⚪", "🔄", "✅", "➖")
    TASK_STATUS_TEXT: tuple = ("待处理", "进行中", "已完成", "已取消")


# 全局配置实例
GOAL_PANE_CONFIG = GoalPaneConfig()


# ============================================================================
# 目标面板（合并 Goal + 任务）
# ============================================================================


class GoalPane(SidebarPane):
    """
    目标面板 - 合并显示 Goal 状态和 Todo 任务列表
    
    功能:
    1. 头部显示 Goal 状态、目标描述、轮次进度
    2. 下方显示 Todo 任务列表（按状态分组）
    3. 支持通过 GoalManager 和 SessionTodoStore 动态更新
    """
    
    # 实例属性优化
    __slots__ = (
        '_goal_manager', '_logger', '_todo_store', '_config',
        '_refresh_interval', '_spinner_index', '_spinner_frames',
        '_refresh_timer', '_has_active_goal', '_tasks',
        '_goal_header', '_goal_progress', '_goal_empty', '_tasks_list',
        '_last_goal_state', '_last_tasks_hash'
    )
    
    # Goal 状态图标
    GOAL_STATUS_ICONS = {
        "active": "🎯",
        "paused": "⏸️",
        "done": "✅",
        "cleared": "🗑️",
        "expired": "⏰",
    }
    
    # 任务状态图标
    TASK_STATUS_ICONS = {
        "pending": "⚪",
        "in_progress": "🔄",
        "completed": "✅",
        "cancelled": "➖",
    }
    
    # 默认 CSS
    DEFAULT_CSS = """
    GoalPane {
        width: 100%;
        height: 100%;
    }
    
    GoalPane #goal-container {
        width: 100%;
        height: 100%;
        padding: 1;
    }
    
    GoalPane #goal-header {
        width: 100%;
        padding: 1;
        background: $accent 15%;
        border: solid $accent;
        margin-bottom: 1;
    }
    
    GoalPane #goal-progress {
        width: 100%;
        padding: 1;
    }
    
    GoalPane #tasks-section {
        width: 100%;
        height: 1fr;
        padding: 1;
    }
    
    GoalPane #tasks-header {
        width: 100%;
        padding-bottom: 1;
        color: $text-muted;
    }
    
    GoalPane #tasks-list {
        width: 100%;
        height: 1fr;
        color: $text;
    }
    
    GoalPane #goal-empty {
        color: $text-muted;
        text-style: italic;
        padding: 1;
    }
    
    GoalPane .status-badge.active {
        color: $success;
        text-style: bold;
    }
    
    GoalPane .status-badge.paused {
        color: $warning;
        text-style: bold;
    }
    
    GoalPane .status-badge.done {
        color: $success;
    }
    
    GoalPane .status-badge.expired {
        color: $error;
    }
    
    GoalPane .status-badge.cleared {
        color: $text-muted;
    }
    
    GoalPane .task-item {
        padding: 0 1 0 2;
    }
    
    GoalPane .task-item.in_progress {
        color: $accent;
        text-style: bold;
    }
    
    GoalPane .task-item.pending {
        color: $text-muted;
    }
    
    GoalPane .task-item.completed {
        color: $success;
    }
    
    GoalPane .task-item.cancelled {
        color: $text-muted;
        text-style: italic;
    }
    """
    
    def __init__(self, goal_manager=None) -> None:
        self._goal_manager = goal_manager
        self._logger = None
        self._todo_store = None
        self._config = GOAL_PANE_CONFIG  # 使用配置实例
        self._refresh_interval = self._config.REFRESH_INTERVAL
        self._spinner_index = 0
        self._spinner_frames = self._config.SPINNER_FRAMES
        self._refresh_timer = None
        self._has_active_goal = False
        self._tasks = {}
        self._last_goal_state = None
        self._last_tasks_hash = None
        # DOM 缓存初始化
        self._goal_header = None
        self._goal_progress = None
        self._goal_empty = None
        self._tasks_list = None
        
        # 检查是否有活跃的 goal
        if goal_manager is not None and goal_manager.is_active():
            self._has_active_goal = True
        super().__init__(id="goal", title="目标")
    
    def set_goal_manager(self, goal_manager) -> None:
        """设置 GoalManager 实例"""
        self._goal_manager = goal_manager
        # 检查是否有活跃的 goal，并相应地启动或停止定时器
        if goal_manager is not None and goal_manager.is_active():
            self._has_active_goal = True
            self._ensure_timer_running()
        else:
            self._has_active_goal = False
            self._ensure_timer_stopped()
    
    def compose(self) -> ComposeResult:
        """组合子组件."""
        with Vertical(id="goal-container"):
            # Goal 头部（状态+目标描述）
            yield Static("", id="goal-header")
            # 进度条
            yield Static("", id="goal-progress")
            # 空状态提示
            yield Static("[dim]暂无活跃的目标[/dim]\n\n使用 /goal <目标> 创建新目标", id="goal-empty")
            # 任务列表区域
            with Vertical(id="tasks-section"):
                yield Static("📋 任务列表", id="tasks-header")
                yield Static("[dim]暂无任务[/dim]", id="tasks-list")
    
    def on_mount(self) -> None:
        """组件挂载时初始化."""
        try:
            from common.logging_manager import get_tui_logger
            self._logger = get_tui_logger("GoalPane")
        except ImportError:
            self._logger = None
        
        # 缓存 DOM 组件引用
        self._goal_header = self.query_one("#goal-header", Static)
        self._goal_progress = self.query_one("#goal-progress", Static)
        self._goal_empty = self.query_one("#goal-empty", Static)
        self._tasks_list = self.query_one("#tasks-list", Static)
        
        # 初始化 SessionTodoStore
        self._init_todo_store()
        
        # 启动定时刷新
        self._start_refresh_timer()
    
    def _init_todo_store(self) -> None:
        """初始化 SessionTodoStore"""
        try:
            from tools.todo_tool import get_session_todo_store
            self._todo_store = get_session_todo_store()
            if self._logger:
                self._logger.debug("SessionTodoStore initialized")
        except ImportError as e:
            if self._logger:
                self._logger.warning(f"Failed to init SessionTodoStore: {e}")
            self._todo_store = None
    
    def _start_refresh_timer(self) -> None:
        """启动定时刷新定时器"""
        self._refresh_all()  # 立即刷新一次
        # 始终启动定时器以保持任务列表刷新
        # （无论是否有 goal，任务列表都需要显示）
        self._ensure_timer_running()
    
    def _ensure_timer_running(self) -> None:
        """确保定时器正在运行"""
        if self._refresh_timer is None:
            self._refresh_timer = self.set_interval(self._refresh_interval, self._refresh_all)
            if self._logger:
                self._logger.debug("Refresh timer started")
    
    def _ensure_timer_stopped(self) -> None:
        """确保定时器已停止"""
        if self._refresh_timer is not None:
            self._refresh_timer.stop()
            self._refresh_timer = None
            if self._logger:
                self._logger.debug("Refresh timer stopped")
    
    def _log_warning(self, msg: str) -> None:
        """统一日志警告（带空值检查）"""
        if self._logger:
            self._logger.warning(msg)
    
    def _get_goal_state_hash(self) -> Optional[str]:
        """计算目标状态的哈希值，用于变化检测"""
        if not self._goal_manager:
            return None
        try:
            state = self._goal_manager.state
            if not state:
                return None
            # 组合关键状态字段生成哈希
            hash_input = f"{state.status}:{state.goal}:{state.current_turn}:{state.max_turns}"
            return hashlib.md5(hash_input.encode()).hexdigest()[:8]
        except Exception:
            return None
    
    def _get_tasks_hash(self) -> Optional[str]:
        """计算任务列表的哈希值，用于变化检测"""
        if not self._todo_store:
            return None
        try:
            todos = self._todo_store.read()
            # 使用任务 ID 和状态生成哈希
            task_str = "|".join(f"{t.get('id', '')}:{t.get('status', '')}" for t in todos)
            if not task_str:
                return "empty"
            return hashlib.md5(task_str.encode()).hexdigest()[:8]
        except Exception:
            return None
    
    def _refresh_all(self) -> None:
        """刷新 Goal 和任务状态（智能刷新）"""
        try:
            # 计算当前状态的哈希
            current_goal_hash = self._get_goal_state_hash()
            current_tasks_hash = self._get_tasks_hash()
            
            # 只有哈希变化时才更新 DOM
            goal_changed = current_goal_hash != self._last_goal_state
            tasks_changed = current_tasks_hash != self._last_tasks_hash
            
            if goal_changed:
                self._refresh_goal()
                self._last_goal_state = current_goal_hash
            
            if tasks_changed:
                self._refresh_tasks()
                self._last_tasks_hash = current_tasks_hash
            
            # 检查是否有 active goal（使用公共方法）
            has_active_goal = (
                self._goal_manager is not None 
                and self._goal_manager.is_active()
            )
            
            # 根据 goal 状态控制定时器
            if has_active_goal and not self._has_active_goal:
                # 从无 goal 变为有 goal，启动定时器
                self._has_active_goal = True
                self._ensure_timer_running()
            elif not has_active_goal and self._has_active_goal:
                # 从有 goal 变为无 goal，停止定时器
                self._has_active_goal = False
                self._ensure_timer_stopped()
        except Exception as e:
            self._log_warning(f"Refresh failed: {e}")
        
        # 更新旋转图标帧（始终执行，UX 需要）
        self._spinner_index = (self._spinner_index + 1) % len(self._spinner_frames)
    
    def _refresh_goal(self) -> None:
        """从 GoalManager 刷新 Goal 状态"""
        if not self._goal_manager:
            self._show_goal_empty_state()
            return
        
        try:
            goal_state = self._goal_manager.state
            
            if not goal_state:
                self._show_goal_empty_state()
                return
            
            self._update_goal_display(goal_state)
        except Exception as e:
            if self._logger:
                self._logger.warning(f"Failed to refresh Goal state: {e}")
            self._show_goal_empty_state()
    
    def _show_goal_empty_state(self) -> None:
        """显示 Goal 空状态"""
        try:
            if self._goal_header:
                self._goal_header.update("")
            if self._goal_progress:
                self._goal_progress.update("")
            if self._goal_empty:
                self._goal_empty.display = True
        except Exception:
            pass
    
    def _update_goal_display(self, goal_state) -> None:
        """更新 Goal 状态显示"""
        try:
            if not self._goal_header or not self._goal_progress or not self._goal_empty:
                return
            
            self._goal_empty.display = False
            
            # 获取状态信息
            status = goal_state.status
            status_icon = self.GOAL_STATUS_ICONS.get(status, "❓")
            status_text = self._get_goal_status_text(status)
            
            # 获取目标描述（截断过长文本）
            goal_text = goal_state.goal
            max_len = self._config.MAX_GOAL_DISPLAY_LENGTH
            display_goal = goal_text[:max_len] + "..." if len(goal_text) > max_len else goal_text
            
            # 获取轮次信息（优先使用 get_display_info）
            try:
                display_info = self._goal_manager.get_display_info()
                if display_info:
                    current_turn = display_info.current_turn
                    max_turns = display_info.max_turns
                else:
                    current_turn = goal_state.current_turn
                    max_turns = goal_state.max_turns
            except AttributeError:
                # 兼容旧版 GoalManager
                current_turn = getattr(goal_state, 'current_turn', 0)
                max_turns = getattr(goal_state, 'max_turns', 0)
            
            # 获取任务进度信息
            total_tasks = 0
            completed_tasks = 0
            for board_id, subtasks in self._tasks.items():
                for subtask in subtasks:
                    total_tasks += 1
                    if getattr(subtask, 'status', '') == 'completed':
                        completed_tasks += 1
            
            # 计算任务完成进度
            if total_tasks > 0:
                task_progress = int((completed_tasks / total_tasks) * 100)
            else:
                task_progress = 0
            
            # 更新头部
            self._goal_header.update(f"""[bold]{status_icon} {status_text}[/bold]  [accent]{display_goal}[/accent]""")
            
            # 更新进度条（基于任务完成情况）+ 轮次信息
            progress_bar = self._make_progress_bar(task_progress)
            if total_tasks > 0:
                self._goal_progress.update(f"""[dim]任务:[/dim] {completed_tasks}/{total_tasks} {progress_bar} | [dim]轮次:[/dim] {current_turn}/{max_turns}""")
            else:
                self._goal_progress.update(f"""[dim]任务:[/dim] 0/0 {progress_bar} | [dim]轮次:[/dim] {current_turn}/{max_turns}""")
            
        except Exception as e:
            self._log_warning(f"Failed to update Goal display: {e}")
    
    def _get_goal_status_text(self, status: str) -> str:
        """获取 Goal 状态的中文文本"""
        status_map = {
            "active": "执行中",
            "paused": "已暂停",
            "done": "已完成",
            "cleared": "已清除",
            "expired": "已过期",
        }
        return status_map.get(status, status)
    
    def _refresh_tasks(self) -> None:
        """从 SessionTodoStore 刷新任务列表"""
        try:
            if self._todo_store is None:
                self._init_todo_store()
            
            if self._todo_store is None:
                return
            
            todos = self._todo_store.read()
            
            # 调试日志
            if self._logger:
                self._logger.debug(f"Todo refresh: {len(todos)} items, _todo_store id={id(self._todo_store)}")
            
            if not todos:
                self._tasks = {}
                self._update_tasks_display()
                return
            
            # 转换为内部格式
            self._tasks = {"session": self._convert_todos(todos)}
            self._update_tasks_display()
        except Exception as e:
            if self._logger:
                self._logger.warning(f"Failed to refresh tasks: {e}")
    
    def _convert_todos(self, todos: List[Dict]) -> List:
        """将 Todo 项转换为内部格式"""
        converted = []
        for todo in todos:
            task_item = type('TodoItem', (), {
                'task_id': todo.get("id", ""),
                'title': todo.get("content", ""),
                'status': todo.get("status", "pending"),
                'progress': self._get_todo_progress(todo.get("status", "pending")),
            })()
            converted.append(task_item)
        return converted
    
    def _get_todo_progress(self, todo_status: str) -> int:
        """获取 Todo 任务进度"""
        progress_map = {
            "pending": 0,
            "in_progress": 50,
            "completed": 100,
            "cancelled": 100,
        }
        return progress_map.get(todo_status, 0)
    
    def _update_tasks_display(self) -> None:
        """更新任务列表显示（按原始顺序，不分组）"""
        if not self._tasks_list:
            return
        
        if not self._tasks:
            self._tasks_list.update("[dim]暂无任务[/dim]")
            return
        
        lines = []
        total_count = 0
        max_visible = self._config.MAX_VISIBLE_TASKS
        max_title_len = self._config.MAX_TASK_TITLE_LENGTH
        
        # 按原始顺序遍历所有任务
        for board_id, subtasks in self._tasks.items():
            for subtask in subtasks:
                total_count += 1
                if total_count > max_visible:
                    break
                
                status = getattr(subtask, 'status', 'unknown')
                # 进行中任务使用旋转图标
                if status == "in_progress":
                    icon = self._spinner_frames[self._spinner_index]
                else:
                    icon = self.TASK_STATUS_ICONS.get(status, "❓")
                
                title = getattr(subtask, 'title', '未知任务')
                display_title = title[:max_title_len] if len(title) > max_title_len else title
                lines.append(f"{icon} {display_title}")
            
            if total_count > max_visible:
                break
        
        if not lines:
            lines.append("[dim]暂无任务[/dim]")
        elif total_count > max_visible:
            lines.append(f"[dim]... 还有 {total_count - max_visible} 个任务[/dim]")
        
        self._tasks_list.update("\n".join(lines).strip())
    
    def _make_progress_bar(self, percent: int, width: int = None) -> str:
        """生成进度条"""
        if width is None:
            width = self._config.PROGRESS_BAR_WIDTH
        filled = int(width * percent / 100)
        empty = width - filled
        return f"[success]{'█' * filled}[/success][dim]{'░' * empty}[/dim]"


# ============================================================================
# 保留旧 TasksPane 作为别名（向后兼容）
# ============================================================================


class TasksPane(GoalPane):
    """
    任务面板（已废弃，请使用 GoalPane）
    
    为向后兼容保留，内部逻辑完全复用 GoalPane
    """
    
    def __init__(self) -> None:
        super().__init__(goal_manager=None)
        self.id = "tasks"
        # 注意：不再设置 title，让 TabbedContent 使用默认标题


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
        file_path = Path(event.path)
        
        # 如果是目录，展开/折叠
        if file_path.is_dir():
            return
        
        # 如果是文件，打开预览
        if FilePreviewScreen:
            self.app.push_screen(FilePreviewScreen(file_path))

    def set_focus_within(self) -> None:
        """设置面板内部焦点."""
        tree = self.query_one(DirectoryTree, None)
        if tree:
            tree.focus(scroll_visible=False)


# ============================================================================
# 技能面板
# ============================================================================


class SkillsPane(SidebarPane):
    """技能面板 - 显示已安装的技能和 Bundle 列表"""

    # 状态图标
    SKILL_ICONS = {
        "active": "🟢",
        "stale": "🟡",
        "archived": "⚪",
        "pinned": "📌",
    }

    # 类别图标
    CATEGORY_ICONS = {
        "general": "📦",
        "developer": "🔧",
        "data": "📊",
        "ai": "🤖",
        "tools": "🛠️",
    }

    DEFAULT_CSS = """
    SkillsPane {
        width: 100%;
        height: 100%;
    }

    SkillsPane #skills-container {
        width: 100%;
        height: 100%;
        padding: 1;
    }

    SkillsPane #skills-search {
        width: 100%;
        margin-bottom: 1;
    }

    SkillsPane #skills-tabs {
        width: 100%;
        height: auto;
        margin-bottom: 1;
        layout: horizontal;
    }

    SkillsPane .skill-tab {
        width: 1fr;
        padding: 0 1;
        color: $text-muted;
        background: transparent;
        border: none;
    }

    SkillsPane .skill-tab:hover {
        background: $accent 15%;
    }

    SkillsPane .skill-tab.active {
        color: $accent;
        text-style: bold;
        border-bottom: solid $accent;
    }

    SkillsPane #skills-tabs {
        height: auto;
        margin-bottom: 1;
    }

    SkillsPane #skills-list {
        width: 100%;
        height: 1fr;
        padding: 1;
    }

    SkillsPane #bundles-list {
        width: 100%;
        height: 1fr;
        padding: 1;
    }

    SkillsPane .skill-item {
        padding: 0 1 0 2;
    }

    SkillsPane .skill-item:hover {
        background: $accent 15%;
    }

    SkillsPane .skill-item.pinned {
        color: $accent;
    }

    SkillsPane #skills-empty, #bundles-empty {
        color: $text-muted;
        text-style: italic;
        padding: 1;
    }

    SkillsPane #skills-hint {
        width: 100%;
        padding: 1;
        color: $text-muted;
        text-style: italic;
    }
    """

    def __init__(self, on_skill_activate: callable = None, on_bundle_activate: callable = None) -> None:
        self._on_skill_activate = on_skill_activate
        self._on_bundle_activate = on_bundle_activate
        self._logger = None
        self._refresh_timer = None
        self._skills = []
        self._bundles = []
        self._filtered_skills = []
        self._filtered_bundles = []
        self._search_query = ""
        self._current_tab = "skills"  # "skills" or "bundles"
        # DOM 缓存
        self._skills_list = None
        self._bundles_list = None
        self._search_input = None
        self._tab_skills = None
        self._tab_bundles = None
        self._bundles_empty = None
        super().__init__(id="skills", title="技能")

    def compose(self) -> ComposeResult:
        """组合子组件"""
        with Vertical(id="skills-container"):
            # 搜索框
            yield Input(placeholder="搜索技能...", id="skills-search")
            # Tab 选择器（真正的 Tab 切换）
            with Horizontal(id="skills-tabs"):
                Button("[b]技能[/b]", id="tab-skills", classes="skill-tab active", variant="default")
                Button("Bundle", id="tab-bundles", classes="skill-tab", variant="default")
            # 技能列表
            yield Static("[dim]暂无技能[/dim]", id="skills-list")
            # Bundle 列表
            yield Static("", id="bundles-list")
            # 底部提示
            yield Static("[dim]使用 /skill-name 激活技能[/dim]", id="skills-hint")

    def on_mount(self) -> None:
        """组件挂载时初始化"""
        try:
            from common.logging_manager import get_tui_logger
            self._logger = get_tui_logger("SkillsPane")
        except ImportError:
            self._logger = None

        # 缓存 DOM 组件引用
        self._skills_list = self.query_one("#skills-list", Static)
        self._bundles_list = self.query_one("#bundles-list", Static)
        self._search_input = self.query_one("#skills-search", Input)

        # 初始化 Tab 显示状态（技能 Tab 激活）
        self._current_tab = "skills"
        self._update_tab_appearance()

        # 加载数据
        self._load_skills()
        self._load_bundles()
        self._refresh_display()

        # 启动定时刷新
        self._start_refresh_timer()

    @on(Input.Changed)
    def _on_search_changed(self, event: Input.Changed) -> None:
        """搜索输入变化"""
        if hasattr(self, '_search_input') and event.input == self._search_input:
            self._search_query = event.value.lower()
            self._filter_data()
            self._refresh_display()

    @on(Button.Pressed, "#tab-skills")
    def _show_skills_tab(self) -> None:
        """切换到技能 Tab"""
        if self._current_tab == "skills":
            return
        self._current_tab = "skills"
        self._refresh_skills_list()
        self._update_tab_appearance()

    @on(Button.Pressed, "#tab-bundles")
    def _show_bundles_tab(self) -> None:
        """切换到 Bundle Tab"""
        if self._current_tab == "bundles":
            return
        self._current_tab = "bundles"
        self._refresh_bundles_list()
        self._update_tab_appearance()

    def _update_tab_appearance(self) -> None:
        """更新 Tab 样式和列表显示"""
        tabs_container = self.query_one("#skills-tabs", Horizontal)
        buttons = tabs_container.query(Button)
        tab_skills = buttons.nodes[0] if len(buttons.nodes) > 0 else None
        tab_bundles = buttons.nodes[1] if len(buttons.nodes) > 1 else None

        if self._current_tab == "skills":
            if tab_skills:
                tab_skills.label = "[b]技能[/b]"
            if tab_bundles:
                tab_bundles.label = "Bundle"
            self._skills_list.display = True
            self._bundles_list.display = False
        else:
            if tab_skills:
                tab_skills.label = "技能"
            if tab_bundles:
                tab_bundles.label = "[b]Bundle[/b]"
            self._skills_list.display = False
            self._bundles_list.display = True

    def _start_refresh_timer(self) -> None:
        """启动定时刷新"""
        self._refresh_timer = self.set_interval(5.0, self._refresh_data)

    def _load_skills(self) -> None:
        """加载技能列表"""
        try:
            from common.config import get_skills_dir

            skills_dir = get_skills_dir()
            if self._logger:
                self._logger.debug(f"Loading skills from: {skills_dir}")

            if not skills_dir.exists():
                self._skills = []
                if self._logger:
                    self._logger.debug("Skills dir does not exist")
                return

            # 尝试获取 telemetry，失败则使用默认值
            telemetry = None
            try:
                from agent.skill_usage_tracker import get_skill_telemetry
                telemetry = get_skill_telemetry()
            except ImportError as e:
                if self._logger:
                    self._logger.debug(f"Telemetry not available: {e}")

            self._skills = []

            # 遍历技能目录（递归查找 SKILL.md）
            skill_count = 0
            for skill_path in skills_dir.rglob("SKILL.md"):
                # 获取技能目录
                skill_dir = skill_path.parent
                # 跳过以 . 开头的目录
                if any(p.startswith(".") for p in skill_dir.relative_to(skills_dir).parts):
                    continue

                # 获取技能标识（使用相对路径）
                rel_path = skill_dir.relative_to(skills_dir)
                skill_id = str(rel_path).replace("\\", "/")

                # 获取追踪数据
                state = "active"
                pinned = False
                use_count = 0
                if telemetry:
                    try:
                        record = telemetry.get_record(skill_id)
                        if record:
                            state = record.state
                            pinned = record.pinned
                            use_count = record.use_count
                    except Exception:
                        pass

                # 读取技能描述
                description = ""
                category = "general"
                name = skill_id
                try:
                    content = skill_path.read_text(encoding="utf-8")
                    from agent.skill_utils import parse_frontmatter
                    fm, _ = parse_frontmatter(content)
                    description = fm.get("description", "")
                    category = fm.get("category", "general")
                    name = fm.get("name", skill_id)
                except Exception:
                    pass

                self._skills.append({
                    "name": name,
                    "path": skill_id,
                    "description": description,
                    "category": category,
                    "state": state,
                    "pinned": pinned,
                    "use_count": use_count,
                })
                skill_count += 1

            if self._logger:
                self._logger.debug(f"Loaded {skill_count} skills")

        except ImportError as e:
            if self._logger:
                self._logger.warning(f"Failed to load skills (ImportError): {e}")
            self._skills = []
        except Exception as e:
            if self._logger:
                self._logger.warning(f"Failed to load skills: {e}")
            self._skills = []

        except ImportError as e:
            if self._logger:
                self._logger.warning(f"Failed to load skills (ImportError): {e}")
            self._skills = []
        except Exception as e:
            if self._logger:
                self._logger.warning(f"Failed to load skills: {e}")
            self._skills = []

    def _load_bundles(self) -> None:
        """加载 Bundle 列表"""
        try:
            from agent.skill_workflows import list_bundles

            bundles = list_bundles()
            self._bundles = [
                {
                    "name": b.name,
                    "slug": b.slug,
                    "description": b.description,
                    "skills": b.skills,
                    "author": b.author,
                }
                for b in bundles
            ]
        except ImportError as e:
            if self._logger:
                self._logger.warning(f"Failed to load bundles: {e}")
            self._bundles = []

    def _filter_data(self) -> None:
        """根据搜索过滤数据"""
        if not self._search_query:
            self._filtered_skills = self._skills.copy()
            self._filtered_bundles = self._bundles.copy()
            return

        # 过滤技能
        self._filtered_skills = [
            s for s in self._skills
            if (self._search_query in s["name"].lower() or
                self._search_query in s.get("description", "").lower())
        ]

        # 过滤 Bundle
        self._filtered_bundles = [
            b for b in self._bundles
            if (self._search_query in b["name"].lower() or
                self._search_query in b.get("description", "").lower())
        ]

    def _refresh_data(self) -> None:
        """定时刷新数据"""
        self._load_skills()
        self._load_bundles()
        self._filter_data()
        self._refresh_display()

    def _refresh_display(self) -> None:
        """刷新显示"""
        if not self._skills_list or not self._bundles_list:
            return

        self._filter_data()

        # 刷新技能列表
        self._refresh_skills_list()
        # 刷新 Bundle 列表
        self._refresh_bundles_list()

    def _refresh_skills_list(self) -> None:
        """刷新技能列表显示"""
        if not self._filtered_skills:
            msg = "[dim]暂无技能[/dim]"
            if self._search_query:
                msg = f"[dim]搜索 '{self._search_query}' 无结果[/dim]"
            self._skills_list.update(msg)
            return

        lines = []
        categories = {}
        for skill in self._filtered_skills:
            cat = skill.get("category", "general")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(skill)

        for cat, skills in sorted(categories.items()):
            cat_icon = self.CATEGORY_ICONS.get(cat, "📦")
            lines.append(f"[bold]{cat_icon} {cat.upper()}[/bold]")

            for skill in skills[:10]:
                pinned_mark = "📌 " if skill.get("pinned") else "   "
                state_icon = self.SKILL_ICONS.get(skill.get("state", "active"), "🟢")
                lines.append(f"  {pinned_mark}{state_icon} {skill['name']}")
                if skill.get("description"):
                    desc = skill["description"]
                    if len(desc) > 35:
                        desc = desc[:35] + "..."
                    lines.append(f"       [dim]{desc}[/dim]")

            if len(skills) > 10:
                lines.append(f"       [dim]... 还有 {len(skills) - 10} 个[/dim]")

        self._skills_list.update("\n".join(lines).strip())

    def _refresh_bundles_list(self) -> None:
        """刷新 Bundle 列表显示"""
        if not self._filtered_bundles:
            msg = "[dim]暂无 Bundle[/dim]"
            if self._search_query:
                msg = f"[dim]搜索 '{self._search_query}' 无结果[/dim]"
            self._bundles_list.update(msg)
            return

        lines = []
        for bundle in self._filtered_bundles[:10]:
            lines.append(f"[accent]📦 {bundle['name']}[/accent]")
            if bundle.get("description"):
                desc = bundle["description"]
                if len(desc) > 40:
                    desc = desc[:40] + "..."
                lines.append(f"   [dim]{desc}[/dim]")
            skills_count = len(bundle.get("skills", []))
            lines.append(f"   [dim]{skills_count} 个技能[/dim]")

        if len(self._filtered_bundles) > 10:
            lines.append(f"[dim]... 还有 {len(self._filtered_bundles) - 10} 个[/dim]")

        self._bundles_list.update("\n".join(lines).strip())

    def set_focus_within(self) -> None:
        """设置面板内部焦点"""
        if self._search_input:
            self._search_input.focus()


# ============================================================================
# Agent 面板
# ============================================================================


# ============================================================================
# 日志面板
# ============================================================================


class WrappedLog(Static):
    """支持自动换行的日志显示组件。

    使用 Static 的 text_wrap 实现换行，支持：
    - 自动换行
    - 鼠标可选中文本
    - 自动追加日志行
    """

    def __init__(self, max_lines: int = 1000, **kwargs):
        super().__init__(**kwargs)
        self._lines: list[str] = []
        self._max_lines = max_lines

    def write_line(self, text: str) -> None:
        """追加一行日志文本，自动换行."""
        self._lines.append(text)

        # 限制最大行数，超出则截断前面部分
        if len(self._lines) > self._max_lines:
            self._lines = self._lines[-(self._max_lines // 2):]

        self.update("\n".join(self._lines))

    def clear(self) -> None:
        """清空日志."""
        self._lines.clear()
        self.update("")


# ============================================================================
# 日志面板
# ============================================================================


class LogsPane(SidebarPane):
    """日志面板（使用 WrappedLog 支持自动换行）."""

    DEFAULT_CSS = """
    LogsPane {
        width: 100%;
        height: 100%;
    }

    LogsPane #log-output {
        width: 100%;
        height: 100%;
        overflow-y: auto;
    }
    """

    def __init__(self) -> None:
        super().__init__(id="logs", title="日志")

    def compose(self) -> ComposeResult:
        """组合子组件."""
        yield WrappedLog(id="log-output", markup=False)


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

    def __init__(self, cwd: str = None, agent=None, goal_manager=None):
        super().__init__(id="sidebar-container-inner")
        self._cwd = cwd
        self._agent = agent
        self._goal_manager = goal_manager

    def compose(self) -> ComposeResult:
        """组合子组件."""
        # 创建面板实例（合并 Goal + Tasks 为 GoalPane）
        self._goal_pane = GoalPane(self._goal_manager)
        self._file_tree_pane = FileTreePane(self._cwd)
        self._skills_pane = SkillsPane()

        with TabbedContent():
            yield self._goal_pane
            yield self._file_tree_pane
            yield self._skills_pane

    @property
    def goal_pane(self) -> GoalPane:
        """目标面板."""
        return self._goal_pane

    @property
    def file_tree_pane(self) -> FileTreePane:
        """文件树面板."""
        return self._file_tree_pane

    @property
    def skills_pane(self) -> SkillsPane:
        """技能面板."""
        return self._skills_pane

    def switch_to_panel(self, panel_id: str) -> None:
        """切换到指定面板.

        Args:
            panel_id: 面板 ID (goal, file_tree, skills)
        """
        pane_map = {
            "goal": self._goal_pane,
            "file_tree": self._file_tree_pane,
            "skills": self._skills_pane,
        }
        pane = pane_map.get(panel_id)
        if pane:
            pane.activate()

    def set_goal_manager(self, goal_manager) -> None:
        """设置 GoalManager 实例并更新 Goal 面板"""
        self._goal_manager = goal_manager
        if self._goal_pane:
            self._goal_pane.set_goal_manager(goal_manager)

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
        格式化的日志字符串
    """
    icon = get_log_level_icon(level)
    return f"{icon} [{level}]  {message}"


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
    "TasksPane",  # 向后兼容，别名
    "GoalPane",
    "FileTreePane",
    "FilteredDirectoryTree",
    "SkillsPane",
    "WrappedLog",
    "SidebarTabBar",
    "get_log_level_icon",
    "format_log_entry",
    "get_task_status_icon",
    "format_task_item",
]