"""TUIConsumer - 任务事件日志消费者

订阅 StreamEmitter 的任务相关事件，仅用于日志记录。
GoalPane 通过轮询 SessionTodoStore 获取任务状态，无需此消费者推送。

用法::

    consumer = TUIConsumer()
    registry.register(consumer)
"""

from common.streaming.consumer import StreamConsumer
from common.streaming.events import StreamEvent, StreamEventType
from common.logging_manager import get_decision_logger

# 任务规划日志
task_logger = get_decision_logger("TaskEvent", sublayer="task")


class TUIConsumer(StreamConsumer):
    """TUI 任务事件日志消费者。

    处理 StreamEmitter 的任务相关事件，仅用于日志记录。
    GoalPane 通过定时轮询 SessionTodoStore 获取任务状态，两者完全解耦。
    """

    @property
    def name(self) -> str:
        return "tui_tasks"

    async def on_event(self, event: StreamEvent) -> None:
        """处理流式事件"""
        if event.type == StreamEventType.PLAN_START:
            task_logger.info(f"📋 任务规划开始: {event.data.get('main_task', '')[:50]}...")
        elif event.type == StreamEventType.PLAN_PROGRESS:
            subtasks = event.data.get("subtasks", [])
            task_logger.debug(f"任务规划进度: {len(subtasks)} 个子任务")
        elif event.type == StreamEventType.PLAN_COMPLETE:
            task_logger.info("✅ 任务规划完成")
        elif event.type == StreamEventType.SUBTASK_STARTED:
            task_logger.info(f"🔄 开始执行: {event.data.get('subtask_title', 'Unknown')}")
        elif event.type == StreamEventType.SUBTASK_COMPLETED:
            success = event.data.get("success", True)
            title = event.data.get("subtask_title", "Unknown")
            duration_ms = event.data.get("duration_ms", 0)
            if success:
                task_logger.info(f"✅ 完成: {title} ({(duration_ms/1000):.1f}s)")
            else:
                task_logger.warning(f"❌ 失败: {title} - {event.data.get('error', '')}")
