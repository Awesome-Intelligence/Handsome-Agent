"""TUIConsumer - 任务事件日志消费者

订阅 StreamEmitter 的任务相关事件，用于：
1. 日志记录
2. 向 GoalPane 发布消息以实时更新任务状态
"""

from typing import Dict, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime

from common.streaming.consumer import StreamConsumer
from common.streaming.events import StreamEvent, StreamEventType
from common.logging_manager import get_decision_logger

if TYPE_CHECKING:
    from textual.app import TextualApp

# 任务规划日志
task_logger = get_decision_logger("TaskEvent", sublayer="task")


@dataclass
class TaskState:
    """任务状态追踪（用于本地日志）"""
    task_id: str
    main_task: str
    complexity: str = "unknown"
    subtasks: Dict[int, any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    @property
    def total(self) -> int:
        return len(self.subtasks)
    
    @property
    def completed(self) -> int:
        return sum(1 for s in self.subtasks.values() if getattr(s, 'status', '') == "completed")
    
    @property
    def progress_percent(self) -> int:
        if self.total == 0:
            return 0
        return int(self.completed / self.total * 100)


class TUIConsumer(StreamConsumer):
    """
    TUI 任务事件日志消费者
    
    处理 StreamEmitter 的任务相关事件，用于日志记录。
    
    用法::
    
        consumer = TUIConsumer()
        registry.register(consumer)
    """
    
    def __init__(self) -> None:
        """初始化消费者."""
        self._tasks: Dict[str, TaskState] = {}  # task_id -> TaskState
        self._current_task_id: Optional[str] = None
        self._current_subtask_id: Optional[int] = None
    
    @property
    def name(self) -> str:
        return "tui_tasks"
    
    async def on_event(self, event: StreamEvent) -> None:
        """处理流式事件"""
        # 任务规划相关
        if event.type == StreamEventType.PLAN_START:
            await self._handle_plan_start(event)
        elif event.type == StreamEventType.PLAN_PROGRESS:
            await self._handle_plan_progress(event)
        elif event.type == StreamEventType.PLAN_COMPLETE:
            await self._handle_plan_complete(event)
        
        # 子任务相关
        elif event.type == StreamEventType.SUBTASK_STARTED:
            await self._handle_subtask_started(event)
        elif event.type == StreamEventType.SUBTASK_PROGRESS:
            await self._handle_subtask_progress(event)
        elif event.type == StreamEventType.SUBTASK_COMPLETED:
            await self._handle_subtask_completed(event)
        
        # 工具调用（可作为隐性子任务追踪）
        elif event.type == StreamEventType.TOOL_START:
            await self._handle_tool_start(event)
        elif event.type == StreamEventType.TOOL_END:
            await self._handle_tool_end(event)
    
    async def _handle_plan_start(self, event: StreamEvent) -> None:
        """处理任务规划开始"""
        data = event.data
        task_id = f"task_{data.get('main_task', '')[:20]}_{int(datetime.now().timestamp())}"
        
        self._tasks[task_id] = TaskState(
            task_id=task_id,
            main_task=data.get("main_task", ""),
            complexity=data.get("complexity", "unknown"),
        )
        
        task_logger.info(f"📋 任务规划开始: {data.get('main_task', '')[:50]}...")
    
    async def _handle_plan_progress(self, event: StreamEvent) -> None:
        """处理任务规划进度（创建子任务）"""
        data = event.data
        subtasks_data = data.get("subtasks", [])
        
        if not self._tasks:
            return
        
        task_state = list(self._tasks.values())[-1]
        
        # 更新子任务列表
        for i, st in enumerate(subtasks_data):
            subtask_id = st.get("id", i + 1)
            if subtask_id not in task_state.subtasks:
                # 创建简化的任务项
                task_item = type('TaskItem', (), {
                    'task_id': task_state.task_id,
                    'subtask_id': subtask_id,
                    'title': st.get("title", st.get("name", "Unknown")),
                    'description': st.get("description", ""),
                    'status': "pending",
                    'started_at': None,
                    'completed_at': None,
                    'result': '',
                    'error': '',
                    'progress': 0,
                })()
                task_state.subtasks[subtask_id] = task_item
        
        task_logger.debug(f"任务规划进度: {len(task_state.subtasks)} 个子任务")
    
    async def _handle_plan_complete(self, event: StreamEvent) -> None:
        """处理任务规划完成"""
        if self._tasks:
            task_state = list(self._tasks.values())[-1]
            task_state.completed_at = datetime.now()
            task_logger.info(f"✅ 任务规划完成: {len(task_state.subtasks)} 个子任务")
    
    async def _handle_subtask_started(self, event: StreamEvent) -> None:
        """处理子任务开始"""
        data = event.data
        task_id = data.get("task_id", "")
        subtask_id = data.get("subtask_id", 0)
        subtask_title = data.get("subtask_title", "Unknown")
        
        if task_id in self._tasks:
            task_state = self._tasks[task_id]
            if subtask_id in task_state.subtasks:
                task_state.subtasks[subtask_id].status = "running"
                task_state.subtasks[subtask_id].started_at = datetime.now()
                
                self._current_task_id = task_id
                self._current_subtask_id = subtask_id
        
        task_logger.info(f"🔄 开始执行: {subtask_title}")
    
    async def _handle_subtask_progress(self, event: StreamEvent) -> None:
        """处理子任务进度"""
        data = event.data
        task_id = data.get("task_id", "")
        subtask_id = data.get("subtask_id", 0)
        progress = data.get("progress", 0)
        
        if task_id in self._tasks:
            task_state = self._tasks[task_id]
            if subtask_id in task_state.subtasks:
                task_state.subtasks[subtask_id].progress = progress
    
    async def _handle_subtask_completed(self, event: StreamEvent) -> None:
        """处理子任务完成"""
        data = event.data
        task_id = data.get("task_id", "")
        subtask_id = data.get("subtask_id", 0)
        success = data.get("success", True)
        result = data.get("result", "")
        error = data.get("error", "")
        subtask_title = data.get("subtask_title", "Unknown")
        
        if task_id in self._tasks:
            task_state = self._tasks[task_id]
            if subtask_id in task_state.subtasks:
                task_state.subtasks[subtask_id].status = "completed" if success else "failed"
                task_state.subtasks[subtask_id].completed_at = datetime.now()
                task_state.subtasks[subtask_id].result = result
                task_state.subtasks[subtask_id].error = error
                
                # 计算持续时间
                started = task_state.subtasks[subtask_id].started_at
                if started:
                    duration = (datetime.now() - started).total_seconds() * 1000
                    task_state.subtasks[subtask_id].duration_ms = int(duration)
                
                # 清除当前任务
                if self._current_subtask_id == subtask_id:
                    self._current_task_id = None
                    self._current_subtask_id = None
        
        status_icon = "✅" if success else "❌"
        duration_ms = 0
        if task_id in self._tasks and subtask_id in self._tasks[task_id].subtasks:
            duration_ms = getattr(self._tasks[task_id].subtasks[subtask_id], 'duration_ms', 0)
        
        if success:
            task_logger.info(f"{status_icon} 完成: {subtask_title} ({(duration_ms/1000):.1f}s)")
        else:
            task_logger.warning(f"{status_icon} 失败: {subtask_title} - {error}")
    
    async def _handle_tool_start(self, event: StreamEvent) -> None:
        """处理工具开始"""
        # 可选：记录工具调用
        pass
    
    async def _handle_tool_end(self, event: StreamEvent) -> None:
        """处理工具结束"""
        pass
    
    def get_tasks(self) -> Dict[str, TaskState]:
        """获取所有任务状态（供外部查询）"""
        return self._tasks
    
    def clear_tasks(self) -> None:
        """清空所有任务"""
        self._tasks.clear()
        self._current_task_id = None
        self._current_subtask_id = None
