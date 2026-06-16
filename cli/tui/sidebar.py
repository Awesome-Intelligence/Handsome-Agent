"""
TUI 侧边栏组件 - 提供文件树、任务、Agent、日志面板
"""

from pathlib import Path
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static, Button, RichLog
from textual.containers import Container, Vertical, Horizontal
from textual import on


# === 侧边栏组件 ===
class SidebarContainer(Container):
    """侧边栏主容器."""
    
    def __init__(self, cwd: str = None, agent=None):
        super().__init__(id="sidebar-container-inner")
        self._cwd = cwd
        self._agent = agent
        self._active_panel = "file_tree"
    
    def compose(self) -> ComposeResult:
        with Vertical(id="sidebar-content-inner"):
            # 任务面板 - 第一个
            with Vertical(id="panel-tasks", classes="sidebar-panel"):
                yield Static("📋 任务", classes="panel-title")
                yield Static("[dim]暂无任务[/dim]", id="tasks-content")
            
            # 文件树面板 - 第二个
            with Vertical(id="panel-file_tree", classes="sidebar-panel hidden"):
                yield Static("📁 文件", classes="panel-title")
                yield Static(self._build_file_tree(), id="file-tree-content")
            
            # Agent 面板
            with Vertical(id="panel-agent", classes="sidebar-panel hidden"):
                yield Static("🤖 Agent", classes="panel-title")
                yield Static("[green]🟢 空闲[/green]", id="agent-content")
            
            # 日志面板 - 第三个
            with Vertical(id="panel-logs", classes="sidebar-panel hidden"):
                yield Static("📜 日志", classes="panel-title")
                yield RichLog(id="log-output", auto_scroll=True, max_lines=1000, wrap=True, min_width=1)
    
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
                    ext = item.suffix.lower()
                    if ext in ['.py', '.rs', '.js', '.ts', '.go']:
                        lines.append(f"[green]📄 {item.name}[/green]")
                    elif ext in ['.md', '.txt']:
                        lines.append(f"[yellow]📄 {item.name}[/yellow]")
                    else:
                        lines.append(f"📄 {item.name}")
            if len(items) > 15:
                lines.append(f"[dim]... 还有 {len(items) - 15} 个项目[/dim]")
        except Exception as e:
            lines.append(f"[red]错误: {e}[/red]")
        return '\n'.join(lines)
    
    def switch_panel(self, panel_type: str) -> None:
        """切换面板."""
        self._active_panel = panel_type
        
        # 切换面板显示
        for panel_id in ["panel-file_tree", "panel-tasks", "panel-agent", "panel-logs"]:
            panel = self.query_one(f"#{panel_id}")
            if panel_id == f"panel-{panel_type}":
                panel.remove_class("hidden")
            else:
                panel.add_class("hidden")
        
        # 切换标签样式
        for tab_id in ["btn-file_tree", "btn-tasks", "btn-agent", "btn-logs"]:
            btn = self.query_one(f"#{tab_id}")
            if tab_id == f"btn-{panel_type}":
                btn.add_class("active")
            else:
                btn.remove_class("active")


# === TabBar 组件 ===
class SidebarTabBar(Container):
    """侧边栏标签栏."""
    
    def __init__(self, on_switch: callable = None):
        super().__init__(id="sidebar-tabs")
        self._on_switch = on_switch
    
    def compose(self) -> ComposeResult:
        with Horizontal(id="tab-bar"):
            yield Button("📁", id="btn-file_tree", classes="sidebar-tab active", variant="primary")
            yield Button("📋", id="btn-tasks", classes="sidebar-tab")
            yield Button("🤖", id="btn-agent", classes="sidebar-tab")
            yield Button("📜", id="btn-logs", classes="sidebar-tab")
    
    @on(Button.Pressed, "#btn-file_tree")
    def _on_file_tree(self) -> None:
        self._switch("file_tree")
    
    @on(Button.Pressed, "#btn-tasks")
    def _on_tasks(self) -> None:
        self._switch("tasks")
    
    @on(Button.Pressed, "#btn-agent")
    def _on_agent(self) -> None:
        self._switch("agent")
    
    @on(Button.Pressed, "#btn-logs")
    def _on_logs(self) -> None:
        self._switch("logs")
    
    def _switch(self, panel_type: str) -> None:
        """切换面板."""
        # 更新按钮样式
        for btn_id in ["btn-file_tree", "btn-tasks", "btn-agent", "btn-logs"]:
            btn = self.query_one(f"#{btn_id}")
            if btn_id == f"btn-{panel_type}":
                btn.add_class("active")
            else:
                btn.remove_class("active")
        
        # 通知父组件
        if self._on_switch:
            self._on_switch(panel_type)
