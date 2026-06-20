"""TUIConsumer - 将流式事件转换为 TUI 消息

订阅 StreamEmitter 的事件，转换为 Textual 消息发布到 TasksPane。
"""

from typing import Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime

from common.streaming.consumer import StreamConsumer
from common.streaming.events import StreamEvent, StreamEventType

# 尝试导入 TUI 消息，使用降级方案
try:
    from tui.messages import TaskItem, TasksPaneUpdated, CurrentTaskChanged
except ImportError:
    # 降级方案：如果 tui.messages 不存在，先定义占位类型
    TaskItem = None
    TasksPaneUpdated = None
    CurrentTaskChanged = None


@dataclass
class TaskState:
    """任务状态追踪"""
    task_id: str
    main_task: str
    complexity: str = "unknown"
    subtasks: Dict[int, "TaskItem"] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    @property
    def total(self) -> int:
        return len(self.subtasks)
    
    @property
    def completed(self) -> int:
        return sum(1 for s in self.subtasks.values() if s.status == "completed")
    
    @property
    def progress_percent(self) -> int:
        if self.total == 0:
            return 0
        return int(self.completed / self.total * 100)


class TUIConsumer(StreamConsumer):
    """
    TUI 任务消费者
    
    将 StreamEmitter 的任务相关事件转换为 Textual 消息。
    
    用法::
    
        # 在 TUI App 中
        consumer = TUIConsumer(app)
        registry.register(consumer)
    """
    
    def __init__(self, app):
        """
        Args:
            app: Textual App 或组件实例，用于 post_message
        """
        self._app = app
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
        
        await self._emit_update("task_created")
    
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
                # 创建 TaskItem
                task_item = TaskItem(
                    task_id=task_state.task_id,
                    subtask_id=subtask_id,
                    title=st.get("title", st.get("name", "Unknown")),
                    description=st.get("description", ""),
                    status="pending",
                    depends_on=st.get("depends_on", []),
                )
                task_state.subtasks[subtask_id] = task_item
        
        await self._emit_update("subtasks_updated")
    
    async def _handle_plan_complete(self, event: StreamEvent) -> None:
        """处理任务规划完成"""
        data = event.data
        
        if self._tasks:
            task_state = list(self._tasks.values())[-1]
            task_state.completed_at = datetime.now()
        
        await self._emit_update("task_completed")
    
    async def _handle_subtask_started(self, event: StreamEvent) -> None:
        """处理子任务开始"""
        data = event.data
        task_id = data.get("task_id", "")
        subtask_id = data.get("subtask_id", 0)
        
        if task_id in self._tasks:
            task_state = self._tasks[task_id]
            if subtask_id in task_state.subtasks:
                task_state.subtasks[subtask_id].status = "running"
                task_state.subtasks[subtask_id].started_at = datetime.now()
                
                self._current_task_id = task_id
                self._current_subtask_id = subtask_id
                
                # 发布当前任务变更消息
                if CurrentTaskChanged:
                    await self._post_message(CurrentTaskChanged(
                        self._app,
                        task_id=task_id,
                        subtask_id=subtask_id,
                        subtask_title=task_state.subtasks[subtask_id].title,
                        status="running",
                    ))
        
        await self._emit_update("subtask_started")
    
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
        
        await self._emit_update("subtask_progress")
    
    async def _handle_subtask_completed(self, event: StreamEvent) -> None:
        """处理子任务完成"""
        data = event.data
        task_id = data.get("task_id", "")
        subtask_id = data.get("subtask_id", 0)
        success = data.get("success", True)
        result = data.get("result", "")
        error = data.get("error", "")
        
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
        
        await self._emit_update("subtask_completed")
    
    async def _handle_tool_start(self, event: StreamEvent) -> None:
        """处理工具开始"""
        # 工具调用可以作为隐性子任务追踪
        # 这里可以扩展实现
        pass
    
    async def _handle_tool_end(self, event: StreamEvent) -> None:
        """处理工具结束"""
        pass
    
    async def _emit_update(self, reason: str) -> None:
        """发送面板更新消息"""
        if not TasksPaneUpdated:
            return
        
        tasks_dict = {
            task_id: list(task_state.subtasks.values())
            for task_id, task_state in self._tasks.items()
        }
        
        current_progress = 0
        if self._current_task_id and self._current_task_id in self._tasks:
            current_progress = self._tasks[self._current_task_id].progress_percent
        
        await self._post_message(TasksPaneUpdated(
            self._app,
            reason=reason,
            tasks=tasks_dict,
            current_task_id=self._current_task_id,
            current_subtask_id=self._current_subtask_id,
            progress_percent=current_progress,
        ))
    
    async def _post_message(self, message) -> None:
        """安全地 post_message 到 App"""
        try:
            self._app.post_message(message)
        except Exception:
            # App 可能还未挂载，静默忽略
            pass
    
    def get_tasks(self) -> Dict[str, TaskState]:
        """获取所有任务状态（供外部查询）"""
        return self._tasks
    
    def clear_tasks(self) -> None:
        """清空所有任务"""
        self._tasks.clear()
        self._current_task_id = None
        self._current_subtask_id = None
