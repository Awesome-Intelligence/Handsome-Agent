# -*- coding: utf-8 -*-
"""
Agent State 模块 - 统一状态管理

提供 Agent 生命周期的统一状态管理，包括：
- AgentStatus: 状态枚举
- AgentState: 统一状态管理器
- ExitDecision: 退出决策
- ExitReason: 退出原因枚举

使用示例：
```python
from agent.state import AgentState, AgentStatus, ExitDecision

state = AgentState(max_iterations=20)
state.start()

# 检查状态
if state.is_running:
    decision = state.should_exit(step_result)
    if not decision.should_exit:
        # 继续执行
        pass
```

状态转换：
- IDLE → RUNNING: start()
- RUNNING → PAUSED: pause()
- RUNNING → COMPLETED: complete() / should_exit()
- RUNNING → ABORTED: abort()
- PAUSED → RUNNING: resume()
- PAUSED → ABORTED: abort()
- COMPLETED/ABORTED → IDLE: reset()
"""

# 从 enums.py 导入所有状态枚举（统一位置）
from .enums import (
    AgentStatus,
    TaskStatus,
    TodoStatus,
    TaskEventType,
    BudgetMode,
    ExitReason,
)
from agent.state.agent_state import (
    AgentState,
    ExitDecision,
    StateTransition,
)
from agent.state.session_store import SessionStore

__all__ = [
    # 状态枚举
    "AgentStatus",
    "TaskStatus",
    "TodoStatus",
    "TaskEventType",
    "BudgetMode",
    "ExitReason",
    # 状态管理
    "AgentState",
    # 会话存储
    "SessionStore",
    # 数据类
    "ExitDecision",
    "StateTransition",
]