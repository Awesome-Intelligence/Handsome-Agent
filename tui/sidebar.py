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
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual.events import Click
from textual.message import Message
from textual.widgets import Static, Log, TabbedContent, TabPane, DirectoryTree, Input, Button, ListView, ListItem, Tree
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
        '_goal_progress', '_goal_empty', '_tasks_list',
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
            # 进度条
            yield Static("", id="goal-progress")
            # 任务列表区域
            with Vertical(id="tasks-section"):
                yield Static("📋 任务列表", id="tasks-header")
                yield Static("[dim]暂无任务[/dim]", id="tasks-list")
            # 空状态提示（置底）
            yield Static("[dim]暂无活跃的目标[/dim]\n\n使用 /goal <目标> 创建新目标", id="goal-empty")
    
    def on_mount(self) -> None:
        """组件挂载时初始化."""
        try:
            from common.logging_manager import get_tui_logger
            self._logger = get_tui_logger("GoalPane")
        except ImportError:
            self._logger = None

        # 缓存 DOM 组件引用
        try:
            self._goal_progress = self.query_one("#goal-progress", Static)
            self._goal_empty = self.query_one("#goal-empty", Static)
            self._tasks_list = self.query_one("#tasks-list", Static)
            self._logger.info(
                f"on_mount: widgets cached - progress={id(self._goal_progress)}, "
                f"empty={id(self._goal_empty)}, tasks={id(self._tasks_list)}"
            )
        except Exception as e:
            self._logger.error(f"on_mount: failed to cache widgets: {e}")

        # 初始化 SessionTodoStore
        self._init_todo_store()

        # 启动定时刷新（_refresh_all 会在首次调用时立即刷新）
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
        if self._refresh_timer is None or not self._refresh_timer.is_active:
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
            # 动态获取最新的 goal_manager（从 app 层面获取，支持运行时更新）
            old_goal_manager = self._goal_manager
            self._update_goal_manager_from_app()
            gm_changed = old_goal_manager is not self._goal_manager

            # 计算当前状态的哈希
            current_goal_hash = self._get_goal_state_hash()
            current_tasks_hash = self._get_tasks_hash()

            # gm_changed 时强制刷新（goal_manager 发生变化）
            goal_changed = gm_changed or (current_goal_hash != self._last_goal_state)
            tasks_changed = current_tasks_hash != self._last_tasks_hash

            if self._logger:
                self._logger.debug(
                    f"_refresh_all: gm_changed={gm_changed}, goal_changed={goal_changed}, "
                    f"current_hash={current_goal_hash}, last_hash={self._last_goal_state}, "
                    f"tasks_changed={tasks_changed}, "
                    f"_goal_manager={id(self._goal_manager) if self._goal_manager else None}"
                )

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

    def _update_goal_manager_from_app(self) -> None:
        """从 app 动态获取最新的 goal_manager"""
        try:
            app = getattr(self, 'app', None)
            if app is None:
                self._logger.warning("_update_goal_manager_from_app: app is None")
                return

            agent = getattr(app, '_agent', None)
            if agent is None:
                self._logger.warning("_update_goal_manager_from_app: agent is None")
                return

            # 从 agent 获取 goal_manager（GoalManager 始终存在，即使没有 goal）
            new_goal_manager = getattr(agent, '_goal_manager', None)
            if new_goal_manager is None:
                self._logger.warning("_update_goal_manager_from_app: agent._goal_manager is None")
                return

            # 只有当 goal_manager 引用变化时才更新
            if new_goal_manager is not self._goal_manager:
                old_id = id(self._goal_manager) if self._goal_manager else None
                self._goal_manager = new_goal_manager
                self._logger.info(
                    f"GoalManager updated: {old_id} -> {id(new_goal_manager)}, "
                    f"goal={new_goal_manager.state.goal[:30] if new_goal_manager.state else 'None'}"
                )
        except Exception as e:
            self._logger.error(f"_update_goal_manager_from_app error: {e}")
    
    def _refresh_goal(self) -> None:
        """从 GoalManager 刷新 Goal 状态"""
        if not self._goal_manager:
            self._logger.warning("_refresh_goal: _goal_manager is None, showing empty state")
            self._show_goal_empty_state()
            return

        try:
            goal_state = self._goal_manager.state
            self._logger.info(
                f"_refresh_goal: goal_state={goal_state is not None}, "
                f"status={goal_state.status if goal_state else 'N/A'}, "
                f"goal={getattr(goal_state, 'goal', 'N/A')[:30] if goal_state else 'N/A'}"
            )

            if not goal_state:
                self._show_goal_empty_state()
                return

            self._update_goal_display(goal_state)
        except Exception as e:
            if self._logger:
                self._logger.error(f"_refresh_goal failed: {e}")
            self._show_goal_empty_state()
    
    def _show_goal_empty_state(self) -> None:
        """显示 Goal 空状态"""
        try:
            # 确保 DOM 组件已缓存
            if not self._goal_progress or not self._goal_empty:
                try:
                    self._goal_progress = self.query_one("#goal-progress", Static)
                    self._goal_empty = self.query_one("#goal-empty", Static)
                except Exception:
                    return

            self._goal_progress.update("")
            self._goal_empty.display = True
        except Exception as e:
            self._logger.error(f"_show_goal_empty_state error: {e}")
    
    def _update_goal_display(self, goal_state) -> None:
        """更新 Goal 状态显示"""
        try:
            # 确保 DOM 组件已缓存（可能在 on_mount 之前被调用）
            if not self._goal_progress or not self._goal_empty or not self._tasks_list:
                try:
                    self._goal_progress = self.query_one("#goal-progress", Static)
                    self._goal_empty = self.query_one("#goal-empty", Static)
                    self._tasks_list = self.query_one("#tasks-list", Static)
                    self._logger.debug(
                        f"Lazy cache: progress={id(self._goal_progress)}, "
                        f"empty={id(self._goal_empty)}, tasks={id(self._tasks_list)}"
                    )
                except Exception as e:
                    self._logger.warning(f"Failed to cache widgets: {e}")
                    return

            self._goal_empty.display = False

            # 获取目标内容（优先使用 get_display_info）
            goal_text = ""
            current_turn = 0
            max_turns = 0
            goal_status_icon = "🎯"

            try:
                display_info = self._goal_manager.get_display_info()
                if display_info:
                    goal_text = display_info.goal_truncated or display_info.goal or ""
                    current_turn = display_info.current_turn
                    max_turns = display_info.max_turns
                    goal_status_icon = display_info.status_icon or "🎯"
                else:
                    goal_text = goal_state.goal or ""
                    current_turn = goal_state.current_turn
                    max_turns = goal_state.max_turns
            except AttributeError:
                # 兼容旧版 GoalManager
                goal_text = getattr(goal_state, 'goal', '') or ""
                current_turn = getattr(goal_state, 'current_turn', 0)
                max_turns = getattr(goal_state, 'max_turns', 0)

            # 截断过长的目标文本
            max_goal_len = self._config.MAX_GOAL_DISPLAY_LENGTH
            if len(goal_text) > max_goal_len:
                goal_text = goal_text[:max_goal_len] + "..."

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

            # 更新进度条（基于任务完成情况）+ 轮次信息
            progress_bar = self._make_progress_bar(task_progress)
            if total_tasks > 0:
                progress_line = f"[dim]任务:[/dim] {completed_tasks}/{total_tasks} {progress_bar} | [dim]轮次:[/dim] {current_turn}/{max_turns}"
            else:
                progress_line = f"[dim]任务:[/dim] 0/0 {progress_bar} | [dim]轮次:[/dim] {current_turn}/{max_turns}"

            # 组装完整显示内容（目标内容在第一行，进度在第二行）
            self._goal_progress.update(f"{goal_status_icon} {goal_text}\n{progress_line}")

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
    """技能面板 - 使用 Tree 组件显示技能和 Bundle 列表"""

    # 状态图标
    SKILL_ICONS = {
        "active": "😎",
        "stale": "🟡",
        "archived": "⚪",
        "pinned": "📌",
    }

    DEFAULT_CSS = """
    SkillsPane {
        width: 100%;
        height: 100%;
    }

    SkillsPane #skills-container {
        width: 100%;
        height: 100%;
        padding: 0 1 1 1;
    }

    SkillsPane #skills-search {
        width: 100%;
        margin-bottom: 1;
    }

    SkillsPane #skills-search Input {
        height: 3;
    }

    SkillsPane Tree {
        height: 100%;
        background: transparent;
    }

    SkillsPane Tree .tree--node {
        padding: 0;
    }

    SkillsPane Tree .tree--node-toggle {
        display: none;
    }

    SkillsPane Tree > .tree--cursor {
        background: $accent 25%;
        color: $text;
    }
    """

    def __init__(self, on_skill_activate: callable = None, on_bundle_activate: callable = None) -> None:
        self._on_skill_activate = on_skill_activate
        self._on_bundle_activate = on_bundle_activate
        self._logger = None
        self._skills = []
        self._bundles = []
        self._search_query = ""
        # DOM 缓存
        self._tree = None
        self._search_input = None
        # Tree 根节点引用
        self._skills_root = None
        self._bundle_root = None
        # 展开状态保存
        self._skills_expanded = True
        self._bundle_expanded = True
        super().__init__(id="skills", title="技能")

    def compose(self) -> ComposeResult:
        """组合子组件"""
        with Vertical(id="skills-container"):
            # 搜索框
            yield Input(placeholder="搜索技能/Bundle...", id="skills-search")
            # 树形列表
            yield Tree("技能树", id="skills-tree")

    def on_mount(self) -> None:
        """组件挂载时初始化"""
        try:
            from common.logging_manager import get_tui_logger
            self._logger = get_tui_logger("SkillsPane")
        except ImportError:
            self._logger = None

        # 缓存 DOM 组件引用
        self._tree = self.query_one("#skills-tree", Tree)
        self._search_input = self.query_one("#skills-search", Input)

        # 设置 Tree 样式
        self._tree.show_root = False
        self._tree.show_collapse = False
        self._tree.enable_expand = True

        # 加载数据并构建树
        self._load_skills()
        self._load_bundles()
        self._build_tree()

        # ponytail: 停掉 5s 定时刷新 — _build_tree 无 hash gating，每 5s 无条件
        # tree.clear() + 全量 add 节点，在用户切回聊天面板时仍会触发 layout/render，
        # 是掉帧来源之一。需要手动重启 TUI 才能看到新装的 skill/bundle。

    @on(Input.Changed, "#skills-search")
    def _on_search_changed(self, event: Input.Changed) -> None:
        """搜索输入变化"""
        self._search_query = event.value.lower()
        self._build_tree()

    @on(Tree.NodeSelected, "#skills-tree")
    def _on_node_selected(self, event: Tree.NodeSelected) -> None:
        """节点选中时显示详情"""
        node = event.node
        if hasattr(node, '_skill_data') and node._skill_data:
            item_data = node._skill_data
            # 延迟打开弹窗，让选中状态先显示
            self.set_timer(0.1, lambda: self._show_skill_detail(item_data))

    @on(Tree.NodeExpanded, "#skills-tree")
    def _on_node_expanded(self, event: Tree.NodeExpanded) -> None:
        """节点展开时保存状态"""
        node = event.node
        if node == self._skills_root:
            self._skills_expanded = True
        elif node == self._bundle_root:
            self._bundle_expanded = True

    @on(Tree.NodeCollapsed, "#skills-tree")
    def _on_node_collapsed(self, event: Tree.NodeCollapsed) -> None:
        """节点折叠时保存状态"""
        node = event.node
        if node == self._skills_root:
            self._skills_expanded = False
        elif node == self._bundle_root:
            self._bundle_expanded = False

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

            # 尝试获取 telemetry
            telemetry = None
            try:
                from agent.skill_usage_tracker import get_skill_telemetry
                telemetry = get_skill_telemetry()
            except ImportError as e:
                if self._logger:
                    self._logger.debug(f"Telemetry not available: {e}")

            self._skills = []

            # 遍历技能目录（递归查找 SKILL.md）
            for skill_path in skills_dir.rglob("SKILL.md"):
                skill_dir = skill_path.parent
                if any(p.startswith(".") for p in skill_dir.relative_to(skills_dir).parts):
                    continue

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
                name = skill_id
                try:
                    content = skill_path.read_text(encoding="utf-8")
                    from agent.skill_utils import parse_frontmatter
                    fm, _ = parse_frontmatter(content)
                    description = fm.get("description", "")
                    name = fm.get("name", skill_id)
                except Exception:
                    pass

                self._skills.append({
                    "type": "skill",
                    "name": name,
                    "path": skill_id,
                    "description": description,
                    "category": "general",
                    "state": state,
                    "pinned": pinned,
                    "use_count": use_count,
                })

            if self._logger:
                self._logger.debug(f"Loaded {len(self._skills)} skills")

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
                    "type": "bundle",
                    "name": b.name,
                    "slug": b.slug,
                    "description": b.description,
                    "skills": b.skills,
                    "author": b.author,
                    "skills_count": len(b.skills),
                }
                for b in bundles
            ]
        except ImportError as e:
            if self._logger:
                self._logger.warning(f"Failed to load bundles: {e}")
            self._bundles = []

    def _filter_items(self) -> tuple:
        """根据搜索过滤技能和 Bundle"""
        skills = self._skills[:]
        bundles = self._bundles[:]

        if self._search_query:
            skills = [
                s for s in skills
                if (self._search_query in s["name"].lower() or
                    self._search_query in s.get("description", "").lower())
            ]
            bundles = [
                b for b in bundles
                if (self._search_query in b["name"].lower() or
                    self._search_query in b.get("description", "").lower())
            ]

        return skills, bundles

    def _build_tree(self) -> None:
        """构建技能和 Bundle 树"""
        if not self._tree:
            return

        # 清空现有树
        self._tree.clear()

        # 获取过滤后的数据
        skills, bundles = self._filter_items()

        # 创建根节点
        root = self._tree.root

        # 添加技能目录
        if skills or bundles:
            self._skills_root = root.add("📦 技能", expand=self._skills_expanded)
            for skill in skills:
                label = self._get_skill_label(skill)
                node = self._skills_root.add_leaf(label)
                node._skill_data = skill

            # 添加 Bundle 目录
            self._bundle_root = root.add("📦 Bundle", expand=self._bundle_expanded)
            for bundle in bundles:
                label = self._get_bundle_label(bundle)
                node = self._bundle_root.add_leaf(label)
                node._skill_data = bundle
        else:
            # 无数据时显示提示
            root.add("[dim]暂无技能[/dim]")

    def _get_skill_label(self, skill: dict) -> str:
        """获取技能节点标签"""
        pinned_mark = "📌 " if skill.get("pinned") else ""
        state_icon = self.SKILL_ICONS.get(skill.get("state", "active"), "🟢")
        return f"{pinned_mark}{state_icon} {skill['name']}"

    def _get_bundle_label(self, bundle: dict) -> str:
        """获取 Bundle 节点标签"""
        count = bundle.get("skills_count", 0)
        count_str = f" ({count})" if count else ""
        return f"📦 {bundle['name']}{count_str}"

    def _refresh_data(self) -> None:
        """定时刷新数据"""
        self._load_skills()
        self._load_bundles()
        self._build_tree()

    def _show_skill_detail(self, item_data: dict) -> None:
        """显示技能/Bundle 详情弹窗"""
        from tui.views.skill_detail import SkillDetailScreen
        self.app.push_screen(SkillDetailScreen(item_data))

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


class WrappedLog(Log):
    """日志显示组件，内部使用 Textual Log 控件。

    使用 Textual 内置 Log 实现，特性：
    - 懒渲染，只渲染可见行，不全文 rebuild
    - 内置 max_lines 自动截断
    - 内置 scroll_end() 支持打开时滚动到底部
    """

    DEFAULT_CSS = """
    WrappedLog {
        overflow-x: hidden;
    }
    """

    def __init__(self, max_lines: int = 1000, **kwargs):
        # auto_scroll=False: 禁用 Log 内部 worker，避免 NoActiveAppError；
        # 滚动到底部由外部 call_after_refresh + scroll_end 控制
        super().__init__(max_lines=max_lines, auto_scroll=False, **kwargs)

    def write_line(self, text: str) -> None:
        """追加一行日志，跳过 Log 内部 @work 线程 worker（避免 NoActiveAppError）。"""
        from textual.geometry import Size

        new_lines = text.splitlines()
        start_line = len(self._lines)
        self._lines.extend(new_lines)
        if self.max_lines is not None and len(self._lines) > self.max_lines:
            self._prune_max_lines()
        self.virtual_size = Size(self._width, len(self._lines))
        self.refresh_lines(start_line, len(new_lines))
        self.refresh()


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
        yield WrappedLog(id="log-output")


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