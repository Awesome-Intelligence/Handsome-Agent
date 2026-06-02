# 🧠 Decision - ✅ Task - ReAct 模块

"""
ReAct 模块 - LLM 驱动的 ReAct 循环执行引擎

ReAct = Reasoning + Acting

注意：ReAct 不是子层，是执行模式。

核心概念：
1. LLM 在每次循环中决策下一步行动
2. 可选的 Rails 拦截机制
3. 支持复杂任务的多步骤执行

使用方式：
```python
from agent.react import ReActLoop, ReActContext

# 创建上下文
context = ReActContext(
    task_description="帮我做一个博客系统",
    tools=tools_schema,
    tool_handlers=tool_handlers
)

# 创建 ReAct 循环
loop = ReActLoop(
    llm_provider=llm,
    session_id=session_id,
    rails=[TaskEventRail(session_id)]
)

# 执行
result = await loop.run(context)
```

子层标识：✅ Task（ReAct 执行任务相关逻辑时使用）
主层：🧠 Decision
"""

from agent.react.context import ReActContext
from agent.react.loop import ReActLoop, LoopState, StepResult

__all__ = [
    "ReActContext",
    "ReActLoop",
    "LoopState",
    "StepResult",
]