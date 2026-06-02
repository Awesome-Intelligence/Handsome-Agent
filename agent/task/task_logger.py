#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task Logger - 任务规划和执行的直观可视化日志

提供:
1. 树形任务列表显示
2. 实时进度条
3. 执行状态追踪
4. 汇总报告
"""

from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass
import time


class LogStyle(Enum):
    """日志样式"""
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"
    BG_GREEN = "\033[102m"
    BG_YELLOW = "\033[103m"
    RESET = "\033[0m"


@dataclass
class TaskNode:
    """任务节点"""
    id: int
    title: str
    status: str = "pending"  # pending, running, completed, failed
    depends_on: List[int] = None
    children: List['TaskNode'] = None
    result: Optional[str] = None
    
    def __post_init__(self):
        if self.depends_on is None:
            self.depends_on = []
        if self.children is None:
            self.children = []


class TaskTreeLogger:
    """
    任务树形日志可视化
    
    特性:
    - 树形结构显示任务依赖关系
    - 实时状态更新（彩色输出）
    - 进度条显示
    - 执行时间统计
    """
    
    PREFIX_EMPTY = "    "
    PREFIX_LAST = "└── "
    PREFIX_BRANCH = "├── "
    PREFIX_RUNNING = "🔄 "
    PREFIX_COMPLETED = "✅ "
    PREFIX_PENDING = "⏳ "
    PREFIX_FAILED = "❌ "
    
    def __init__(self, main_task: str = ""):
        self.main_task = main_task
        self.tasks: List[TaskNode] = []
        self.start_time = time.time()
        self._indent_width = 4
    
    def set_main_task(self, task: str):
        """设置主任务"""
        self.main_task = task
    
    def add_task(self, id: int, title: str, depends_on: List[int] = None):
        """添加任务"""
        self.tasks.append(TaskNode(
            id=id,
            title=title,
            depends_on=depends_on or []
        ))
    
    def add_tasks(self, tasks_data: List[Dict[str, Any]]):
        """批量添加任务"""
        for item in tasks_data:
            self.add_task(
                id=item.get('id', 0),
                title=item.get('title', ''),
                depends_on=item.get('depends_on', [])
            )
    
    def update_task_status(self, task_id: int, status: str, result: str = None):
        """更新任务状态"""
        for task in self.tasks:
            if task.id == task_id:
                task.status = status
                if result:
                    task.result = result
                break
    
    def build_tree(self) -> List[TaskNode]:
        """构建任务树（处理依赖关系）"""
        roots = []
        task_map = {t.id: t for t in self.tasks}
        
        for task in self.tasks:
            if not task.depends_on:
                roots.append(task)
        
        def get_children(parent_id: int) -> List[TaskNode]:
            return [t for t in self.tasks if parent_id in t.depends_on]
        
        def assign_children(node: TaskNode):
            node.children = get_children(node.id)
            for child in node.children:
                assign_children(child)
        
        for root in roots:
            assign_children(root)
        
        return roots
    
    def _get_status_icon(self, status: str) -> str:
        """获取状态图标"""
        icons = {
            'pending': '⏳',
            'running': '🔄',
            'completed': '✅',
            'failed': '❌',
            'cancelled': '➖'
        }
        return icons.get(status, '❓')
    
    def _get_status_color(self, status: str) -> str:
        """获取状态颜色"""
        colors = {
            'pending': LogStyle.GRAY.value,
            'running': LogStyle.CYAN.value,
            'completed': LogStyle.GREEN.value,
            'failed': LogStyle.RED.value,
            'cancelled': LogStyle.YELLOW.value
        }
        return colors.get(status, LogStyle.WHITE.value)
    
    def format_tree(self, nodes: List[TaskNode], prefix: str = "", is_last: bool = True, is_root: bool = True) -> str:
        """格式化树形结构"""
        lines = []
        
        for i, node in enumerate(nodes):
            is_last_node = (i == len(nodes) - 1)
            
            if is_root:
                connector = "└─" if is_last_node else "├─"
                status_icon = self._get_status_icon(node.status)
                status_color = self._get_status_color(node.status)
                lines.append(f"{status_color}{status_icon} {node.title}{LogStyle.RESET.value}")
            else:
                connector = "  " if is_last_node else "│ "
                status_icon = self._get_status_icon(node.status)
                status_color = self._get_status_color(node.status)
                lines.append(f"{prefix}{connector}{status_color}{status_icon} {node.title}{LogStyle.RESET.value}")
            
            if node.children:
                extension = "    " if is_last_node else "│   "
                child_prefix = prefix + extension
                child_lines = self.format_tree(node.children, child_prefix, is_last_node, is_root=False)
                lines.extend(child_lines)
        
        return lines
    
    def render(self) -> str:
        """渲染完整任务树"""
        lines = []
        
        if self.main_task:
            lines.append("")
            lines.append(f"{LogStyle.BOLD.value}{LogStyle.CYAN.value}📋 主任务: {self.main_task}{LogStyle.RESET.value}")
            lines.append("")
        
        stats = self.get_statistics()
        progress_bar = self._render_progress_bar(stats['completed'], stats['total'])
        
        lines.append(f"  {progress_bar}  {stats['completed']}/{stats['total']} ({stats['percentage']}%)")
        lines.append("")
        
        tree_nodes = self.build_tree()
        if tree_nodes:
            tree_lines = self.format_tree(tree_nodes)
            for line in tree_lines:
                lines.append(f"  {line}")
        else:
            for task in self.tasks:
                status_icon = self._get_status_icon(task.status)
                status_color = self._get_status_color(task.status)
                lines.append(f"  {status_icon} {status_color}{task.title}{LogStyle.RESET.value}")
        
        lines.append("")
        lines.append(self._render_time_stats())
        
        return "\n".join(lines)
    
    def _render_progress_bar(self, completed: int, total: int, width: int = 20) -> str:
        """渲染进度条"""
        if total == 0:
            return f"[{'░' * width}]"
        
        percentage = completed / total
        filled = int(width * percentage)
        empty = width - filled
        
        completed_color = LogStyle.GREEN.value
        pending_color = LogStyle.GRAY.value
        reset = LogStyle.RESET.value
        
        bar = f"{completed_color}{'█' * filled}{pending_color}{'░' * empty}{reset}"
        return f"[{bar}]"
    
    def _render_time_stats(self) -> str:
        """渲染时间统计"""
        elapsed = time.time() - self.start_time
        
        if elapsed < 60:
            time_str = f"{elapsed:.1f}秒"
        elif elapsed < 3600:
            time_str = f"{elapsed/60:.1f}分钟"
        else:
            time_str = f"{elapsed/3600:.1f}小时"
        
        stats = self.get_statistics()
        
        lines = [
            f"{LogStyle.GRAY.value}─" * 40 + LogStyle.RESET.value,
            f"  📊 统计: 完成 {stats['completed']} | 失败 {stats['failed']} | 待处理 {stats['pending']}",
            f"  ⏱️  耗时: {time_str}"
        ]
        
        return "\n".join(lines)
    
    def get_statistics(self) -> Dict[str, int]:
        """获取统计信息"""
        completed = sum(1 for t in self.tasks if t.status == 'completed')
        failed = sum(1 for t in self.tasks if t.status in ['failed', 'cancelled'])
        running = sum(1 for t in self.tasks if t.status == 'running')
        pending = sum(1 for t in self.tasks if t.status == 'pending')
        total = len(self.tasks)
        
        percentage = int(completed / total * 100) if total > 0 else 0
        
        return {
            'total': total,
            'completed': completed,
            'failed': failed,
            'running': running,
            'pending': pending,
            'percentage': percentage
        }
    
    def render_header(self) -> str:
        """渲染表头"""
        elapsed = time.time() - self.start_time
        
        lines = [
            "",
            f"{LogStyle.BOLD.value}{LogStyle.CYAN.value}╔{'═' * 60}╗{LogStyle.RESET.value}",
            f"{LogStyle.BOLD.value}{LogStyle.CYAN.value}║ 🎯 任务规划与执行追踪{' ' * 35}║{LogStyle.RESET.value}",
            f"{LogStyle.BOLD.value}{LogStyle.CYAN.value}╚{'═' * 60}╝{LogStyle.RESET.value}",
            ""
        ]
        
        if self.main_task:
            lines.append(f"{LogStyle.BOLD.value}📋 任务: {self.main_task}{LogStyle.RESET.value}")
        
        return "\n".join(lines)
    
    def render_step_start(self, step_num: int, total: int, task_title: str) -> str:
        """渲染步骤开始"""
        stats = self.get_statistics()
        progress_bar = self._render_progress_bar(stats['completed'], stats['total'])
        
        lines = [
            "",
            f"{LogStyle.CYAN.value}┌─ 第 {step_num}/{total} 步 ─{'─' * 40}┐{LogStyle.RESET.value}",
            f"{LogStyle.CYAN.value}│ {progress_bar} {stats['completed']}/{stats['total']}        │{LogStyle.RESET.value}",
            f"{LogStyle.CYAN.value}│ 🔄 {task_title:<42}│{LogStyle.RESET.value}",
            f"{LogStyle.CYAN.value}└{'─' * 56}┘{LogStyle.RESET.value}",
            ""
        ]
        
        return "\n".join(lines)
    
    def render_step_complete(self, task_title: str, result: str = "") -> str:
        """渲染步骤完成"""
        lines = [
            f"{LogStyle.GREEN.value}✅ 已完成: {task_title}{LogStyle.RESET.value}"
        ]
        
        if result:
            result_preview = result[:60] + "..." if len(result) > 60 else result
            lines.append(f"   └─ {LogStyle.GRAY.value}{result_preview}{LogStyle.RESET.value}")
        
        return "\n".join(lines)
    
    def render_step_failed(self, task_title: str, error: str) -> str:
        """渲染步骤失败"""
        error_preview = error[:60] + "..." if len(error) > 60 else error
        
        lines = [
            f"{LogStyle.RED.value}❌ 失败: {task_title}{LogStyle.RESET.value}",
            f"   └─ {LogStyle.YELLOW.value}错误: {error_preview}{LogStyle.RESET.value}"
        ]
        
        return "\n".join(lines)
    
    def render_summary(self) -> str:
        """渲染汇总报告"""
        stats = self.get_statistics()
        elapsed = time.time() - self.start_time
        
        if elapsed < 60:
            time_str = f"{elapsed:.1f}秒"
        elif elapsed < 3600:
            time_str = f"{elapsed/60:.1f}分钟"
        else:
            time_str = f"{elapsed/3600:.1f}小时"
        
        success = stats['completed'] == stats['total'] and stats['failed'] == 0
        
        if success:
            status_icon = "🎉"
            status_color = LogStyle.GREEN.value
            status_text = "全部完成!"
        elif stats['failed'] > 0:
            status_icon = "⚠️"
            status_color = LogStyle.YELLOW.value
            status_text = "部分失败"
        else:
            status_icon = "🔄"
            status_color = LogStyle.CYAN.value
            status_text = "进行中"
        
        lines = [
            "",
            f"{LogStyle.BOLD.value}{status_color}{'═' * 50}{LogStyle.RESET.value}",
            f"{status_color}║ {status_icon} {status_text:<44}║{LogStyle.RESET.value}",
            f"{status_color}║ {'─' * 46}║{LogStyle.RESET.value}",
            f"{status_color}║ 完成: {stats['completed']:<6} 失败: {stats['failed']:<6} 耗时: {time_str:<15}║{LogStyle.RESET.value}",
            f"{status_color}{'═' * 50}{LogStyle.RESET.value}",
            ""
        ]
        
        return "\n".join(lines)


class TaskLogger:
    """
    任务日志管理器
    
    统一的日志接口，支持多种输出格式
    """
    
    def __init__(self, name: str = "TaskLogger"):
        self.name = name
        self.tree_logger = None
    
    def plan_start(self, task: str) -> str:
        """任务规划开始"""
        self.tree_logger = TaskTreeLogger(task)
        lines = [
            f"{LogStyle.BOLD.value}{LogStyle.MAGENTA.value}🎯 开始分析任务复杂度...{LogStyle.RESET.value}",
            f"{LogStyle.GRAY.value}   任务: {task[:50]}{'...' if len(task) > 50 else ''}{LogStyle.RESET.value}"
        ]
        return "\n".join(lines)
    
    def plan_complete(self, complexity: str, subtasks: List[Dict], reasoning: str) -> str:
        """任务规划完成"""
        if not self.tree_logger:
            self.tree_logger = TaskTreeLogger()
        
        self.tree_logger.set_main_task(reasoning or "任务规划")
        
        for task in subtasks:
            self.tree_logger.add_task(
                id=task.get('id', 0),
                title=task.get('title', ''),
                depends_on=task.get('depends_on', [])
            )
        
        lines = [
            "",
            f"{LogStyle.BOLD.value}{LogStyle.GREEN.value}✨ 任务规划完成!{LogStyle.RESET.value}",
            f"{LogStyle.GRAY.value}   复杂度: {complexity} | 子任务数: {len(subtasks)}{LogStyle.RESET.value}",
            ""
        ]
        
        lines.append(self.tree_logger.render())
        
        return "\n".join(lines)
    
    def execute_start(self, task_id: int, total: int, title: str) -> str:
        """执行开始"""
        if self.tree_logger:
            self.tree_logger.update_task_status(task_id, 'running')
        
        if not self.tree_logger:
            self.tree_logger = TaskTreeLogger()
        
        return self.tree_logger.render_step_start(task_id, total, title)
    
    def execute_complete(self, task_id: int, title: str, result: str = "") -> str:
        """执行完成"""
        if self.tree_logger:
            self.tree_logger.update_task_status(task_id, 'completed', result)
            return self.tree_logger.render_step_complete(title, result)
        
        return f"{LogStyle.GREEN.value}✅ 完成: {title}{LogStyle.RESET.value}"
    
    def execute_failed(self, task_id: int, title: str, error: str) -> str:
        """执行失败"""
        if self.tree_logger:
            self.tree_logger.update_task_status(task_id, 'failed', error)
            return self.tree_logger.render_step_failed(title, error)
        
        return f"{LogStyle.RED.value}❌ 失败: {title} - {error[:50]}{LogStyle.RESET.value}"
    
    def progress_update(self) -> str:
        """进度更新"""
        if self.tree_logger:
            stats = self.tree_logger.get_statistics()
            progress_bar = self.tree_logger._render_progress_bar(
                stats['completed'], 
                stats['total']
            )
            return f"  {progress_bar}  {stats['completed']}/{stats['total']} ({stats['percentage']}%)"
        
        return ""
    
    def final_summary(self) -> str:
        """最终汇总"""
        if self.tree_logger:
            return self.tree_logger.render_summary()
        
        return f"{LogStyle.GREEN.value}任务执行完成!{LogStyle.RESET.value}"


def create_task_logger(name: str = "TaskLogger") -> TaskLogger:
    """创建任务日志器"""
    return TaskLogger(name)