# 🧠 Decision - ✅ Task - Rails 模块

"""
Rails 模块 - 可插拔的拦截器机制

Rail 本质：
- 可插拔的 before/after 钩子
- 包装器（Wrapper）模式
- 在关键节点插入拦截逻辑

v2.0.0 变更：
- 统一为 RailRegistry 单例模式
- 移除 RailManager，简化架构

使用示例：
```python
from agent.rails import get_rail_registry

registry = get_rail_registry()

# 注册 Rail
registry.register(session_id, TaskEventRail(session_id))

# 获取 Rails
rails = registry.get_rails(session_id)

# 触发拦截
result = await registry.trigger_before_tool_call(session_id, "write_file", args)

# 清理会话
registry.clear_session(session_id)
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

from agent.rails.registry import (
    RailRegistry,  # 统一注册表
    get_rail_registry,  # 获取单例
    reset_rail_registry,  # 重置（主要用于测试）
)

from agent.rails.task_event_rail import TaskEventRail

# Tool Guardrails
from agent.rails.tool_guardrails import (
    ToolCallGuardrailConfig,
    ToolCallSignature,
    ToolGuardrailDecision,
    ToolCallGuardrailController,
    IDEMPOTENT_TOOL_NAMES,
    MUTATING_TOOL_NAMES,
    classify_tool_failure,
    toolguard_synthetic_result,
    append_toolguard_guidance,
)

__all__ = [
    # 核心类
    "Rail",
    "RailRegistry",
    # 枚举和类型
    "RailPriority",
    "RailContext",
    "RailResult",
    "InterruptType",
    # Rails
    "TaskEventRail",
    # Tool Guardrails
    "ToolCallGuardrailConfig",
    "ToolCallSignature",
    "ToolGuardrailDecision",
    "ToolCallGuardrailController",
    "IDEMPOTENT_TOOL_NAMES",
    "MUTATING_TOOL_NAMES",
    "classify_tool_failure",
    "toolguard_synthetic_result",
    "append_toolguard_guidance",
    # 全局函数
    "get_rail_registry",
    "reset_rail_registry",
]
