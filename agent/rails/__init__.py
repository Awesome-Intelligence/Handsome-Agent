# 🧠 Decision - ✅ Task - Rails 模块

"""
Rails 模块 - 可插拔的拦截器机制

注意：Rail 不是子层，是拦截器模式。

Rail 本质：
- 可插拔的 before/after 钩子
- 包装器（Wrapper）模式
- 在关键节点插入拦截逻辑

使用示例：
```python
from agent.rails import RailManager, TaskEventRail

# Rail 作为拦截器
manager = RailManager(session_id)
manager.register_rail(TaskEventRail(session_id))

# 在工具调用前后触发
result = await manager.trigger_before_tool_call("todo_create", args)
# ... 执行工具 ...
await manager.trigger_after_tool_call("todo_create", args, result)
```

子层标识：✅ Task（Rail 执行任务相关逻辑时使用）
主层：🧠 Decision
"""

from agent.rails.rail import (
    Rail,  # 核心 Rail 基类，支持可插拔安全检查
    RailPriority,
    RailContext,
    RailResult,
    InterruptType,
)

from agent.rails.manager import (
    RailManager,
    get_rail_manager,
    reset_rail_manager,
)

from agent.rails.task_event_rail import TaskEventRail

__all__ = [
    "Rail",
    "RailPriority",
    "RailContext",
    "RailResult",
    "InterruptType",
    "RailManager",
    "get_rail_manager",
    "reset_rail_manager",
    "TaskEventRail",
]