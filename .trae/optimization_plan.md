# Agent-Z 任务处理流程优化方案

> 文档版本: v1.0.0
> 创建日期: 2026-06-27
> 状态: 待评审

---

## 一、优化背景与目标

### 1.1 优化背景

经过深入分析 Agent-Z 的任务处理流程，发现存在 8 处重复/冗余设计，这些问题虽然不影响功能正确性，但增加了代码复杂度和维护成本。

### 1.2 优化目标

| 维度 | 当前状态 | 优化目标 |
|------|----------|----------|
| **代码复杂度** | 多层抽象、职责重叠 | 清晰的单层抽象、职责明确 |
| **存储冗余** | 消息记录 2-3 份 | 单一数据源 |
| **预算控制** | 2 套独立系统 | 统一 Budget 接口 |
| **中断机制** | 3 处检查点 | 统一中断处理 |
| **维护成本** | 高（多处同步） | 低（单向数据流） |

### 1.3 优化原则

1. **渐进式重构**：分阶段实施，每次只修改一个模块
2. **向后兼容**：保持 API 兼容性，避免破坏性变更
3. **数据流优先**：先理清数据流，再优化代码结构
4. **可回滚**：每个阶段都可独立回滚

---

## 二、问题根因分析

### 2.1 架构层问题 vs 实现层问题

| 类别 | 问题编号 | 问题描述 | 根因类型 |
|------|----------|----------|----------|
| **架构层** | 问题 1, 5, 8 | 预算控制、轨迹存储、Goal 存储重复 | 设计时未统一规划 |
| **实现层** | 问题 2, 3, 4, 6, 7 | 格式转换、重复注册、中断检查 | 代码复制/历史遗留 |

### 2.2 依赖关系图

```
┌─────────────────────────────────────────────────────────────────┐
│                        依赖关系图                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Session ──────────────────────┬──────────────────► Curator     │
│      │                         │                                  │
│      ├─► ReActContext ─────────┼──────────────────► Trajectory   │
│      │                         │                                  │
│      └─► GoalStateRecord ──────┴──────────────────► GoalManager  │
│                                                                  │
│  IterationBudget ─────────────────────────────────► Agent       │
│      │                                                          │
│      └─► GoalManager (共享 session_id)                          │
│                                                                  │
│  ContextManager ───────────────────────────────► AgentLoop      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 优先级矩阵

| 问题 | 严重程度 | 优化价值 | 实施难度 | 优先级 |
|------|----------|----------|----------|--------|
| 问题 5: 轨迹双重存储 | 中 | 高 | 中 | **P0** |
| 问题 1: 预算控制重叠 | 中 | 高 | 低 | **P0** |
| 问题 6: 上下文压缩重复 | 中 | 中 | 中 | **P1** |
| 问题 2: 消息格式转换 | 低 | 中 | 高 | **P1** |
| 问题 7: Curator/Trajectory 职责 | 中 | 中 | 低 | **P1** |
| 问题 4: 中断检查重复 | 中 | 中 | 低 | **P2** |
| 问题 3: Rails 双重注册 | 低 | 低 | 低 | **P2** |
| 问题 8: Goal 双重存储 | 低 | 低 | 低 | **P3** |

---

## 三、详细优化方案

### 3.1 问题 5: 轨迹双重存储 (P0)

#### 3.1.1 问题描述

**位置**：`agent/session.py` + `agent/curator/trajectory_recorder.py`

**当前状态**：
```python
# agent/agent.py 第 303-306 行
if self._session:
    self._session.add_message("user", user_input)
self._trajectory_recorder.add_human_message(user_input)  # 重复记录

# agent/agent.py 第 317-320 行
if self._session:
    self._session.add_message("assistant", str(final_result))
self._trajectory_recorder.add_gpt_message(str(final_result))  # 重复记录
```

**根因**：TrajectoryRecorder 和 Session 都记录消息，但用途不同：
- Session：会话历史管理
- TrajectoryRecorder：训练数据收集

#### 3.1.2 优化方案：统一消息数据源

**方案设计**：
```
┌─────────────────────────────────────────────────────────────────┐
│                     优化后的数据流                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Agent.chat()                                                    │
│      │                                                           │
│      ├──► Session.add_message() ──────► 单一消息源              │
│      │                                                           │
│      └──► TrajectoryRecorder ──────────► 仅从 Session 读取      │
│              │                                                   │
│              └──► 导出训练数据格式                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**具体修改**：

1. **修改 `agent/curator/trajectory_recorder.py`**：
```python
class TrajectoryRecorder:
    """轨迹记录器 - 训练数据收集"""
    
    def __init__(self, session: Optional[Session] = None):
        self._session = session  # 持有 Session 引用
        self._metadata: Dict[str, Any] = {}
    
    def get_trajectory(self) -> Dict[str, Any]:
        """
        获取轨迹数据（从 Session 读取，不再自己维护消息）
        
        Returns:
            包含消息历史的轨迹数据
        """
        if self._session is None:
            return {"messages": [], "metadata": self._metadata}
        
        # 从 Session 获取消息，不再自己维护
        messages = self._session.get_history()
        return {
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp,
                    "tool_call_id": msg.tool_call_id,
                    "tool_result": msg.tool_result,
                }
                for msg in messages
            ],
            "metadata": self._metadata,
        }
    
    # 移除以下方法，不再自己添加消息
    # def add_human_message(self, content: str) -> None
    # def add_gpt_message(self, content: str) -> None
    # def add_tool_call(self, ...) -> None
```

2. **修改 `agent/agent.py`**：
```python
async def chat(self, user_input: str, ...) -> AgentResponse:
    # 添加消息到 Session（唯一数据源）
    if self._session:
        self._session.add_message("user", user_input)
    
    # TrajectoryRecorder 不再单独添加消息
    # 改为从 Session 读取（见 TrajectoryRecorder.get_trajectory）
    
    # ... 后续逻辑保持不变 ...
```

**风险评估**：
| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 训练数据格式变化 | 中 | 保持导出格式兼容 |
| Session 加载延迟 | 低 | TrajectoryRecorder 缓存最近轨迹 |

#### 3.1.3 验证方案

```bash
# 测试脚本
python -c "
from agent.session import Session
from agent.curator.trajectory_recorder import TrajectoryRecorder

# 1. 创建 Session
session = Session('test_session')

# 2. 添加消息
session.add_message('user', 'Hello')
session.add_message('assistant', 'Hi there')

# 3. 创建 TrajectoryRecorder（关联 Session）
recorder = TrajectoryRecorder(session=session)

# 4. 验证轨迹数据一致性
trajectory = recorder.get_trajectory()
assert len(trajectory['messages']) == 2
assert trajectory['messages'][0]['content'] == 'Hello'

print('✓ 轨迹数据一致性验证通过')
"
```

---

### 3.2 问题 1: 预算控制职责重叠 (P0)

#### 3.2.1 问题描述

**位置**：
- `agent/iteration_budget.py` - IterationBudget
- `agent/goal/manager.py` - GoalManager._current_goal.current_turn
- `agent/agent.py` 第 475-491 行

**当前状态**：
```python
# agent/agent.py 第 475-491 行
if goal_active:
    # Goal 模式：使用 GoalManager 的轮次限制
    if goal_state and goal_state.current_turn >= goal_state.max_turns:
        loop.abort()
        break
else:
    # 非 Goal 模式：使用 IterationBudget 的迭代限制
    if not self._shared_budget.can_iterate():
        loop.abort()
        break
```

**问题**：
- 两套独立的预算系统
- 退出条件分散在多处
- 概念混淆：iteration vs turn

#### 3.2.2 优化方案：统一 Budget 接口

**方案设计**：

```
┌─────────────────────────────────────────────────────────────────┐
│                     优化后的预算控制                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    Budget Protocol                          │ │
│  │  ├── can_iterate() -> bool                                  │ │
│  │  ├── consume() -> int                                       │ │
│  │  ├── remaining() -> int                                     │ │
│  │  └── reset()                                                │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              ▲                                   │
│          ┌──────────────────┴──────────────────┐                │
│          │                                     │                │
│  ┌───────┴───────┐                   ┌────────┴────────┐       │
│  │IterationBudget│                   │   TurnBudget    │       │
│  │ (非Goal模式)   │                   │   (Goal模式)     │       │
│  └───────────────┘                   └─────────────────┘       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**具体修改**：

1. **创建统一的 Budget 接口** (`agent/budget.py`)：

```python
from abc import ABC, abstractmethod
from typing import Protocol


class Budget(Protocol):
    """预算控制协议"""
    
    def can_iterate(self) -> bool:
        """是否可以继续迭代"""
        ...
    
    def consume(self) -> int:
        """消耗预算，返回当前已消耗数"""
        ...
    
    def remaining(self) -> int:
        """剩余预算"""
        ...
    
    def reset(self) -> None:
        """重置预算"""
        ...
    
    def to_dict(self) -> dict:
        """序列化为字典"""
        ...
```

2. **重构 IterationBudget**：

```python
from dataclasses import dataclass, field
from typing import Dict, Any
import time


@dataclass
class IterationBudget:
    """
    迭代预算控制（非 Goal 模式）
    
    设计说明：
    - 仅用于非 Goal 模式的迭代控制
    - Goal 模式使用 TurnBudget
    """
    
    max_iterations: int = 20
    iterations_used: int = 0
    created_at: float = field(default_factory=time.time)
    
    def can_iterate(self) -> bool:
        return self.iterations_used < self.max_iterations
    
    def consume(self) -> int:
        self.iterations_used += 1
        return self.iterations_used
    
    def remaining(self) -> int:
        return max(0, self.max_iterations - self.iterations_used)
    
    def reset(self) -> None:
        self.iterations_used = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "iteration",
            "max": self.max_iterations,
            "used": self.iterations_used,
            "created_at": self.created_at,
        }
```

3. **新增 TurnBudget**：

```python
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime


@dataclass
class TurnBudget:
    """
    轮次预算控制（Goal 模式）
    
    设计说明：
    - 用于 Goal 模式的 Judge 判断轮次控制
    - 内部委托给 GoalManager 的状态管理
    """
    
    max_turns: int = 20
    current_turn: int = 0
    
    def can_iterate(self) -> bool:
        return self.current_turn < self.max_turns
    
    def consume(self) -> int:
        self.current_turn += 1
        return self.current_turn
    
    def remaining(self) -> int:
        return max(0, self.max_turns - self.current_turn)
    
    def reset(self) -> None:
        self.current_turn = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "turn",
            "max": self.max_turns,
            "used": self.current_turn,
        }
```

4. **修改 Agent._run_loop()**：

```python
# agent/agent.py 第 475-491 行（优化后）
async def _run_loop(self, ...):
    # 统一预算接口
    budget: Budget
    
    if goal_active and goal_manager:
        # Goal 模式：使用 TurnBudget
        budget = TurnBudget(
            max_turns=goal_state.max_turns,
            current_turn=goal_state.current_turn
        )
    else:
        # 非 Goal 模式：使用 IterationBudget
        budget = self._shared_budget
    
    while True:
        # ... 执行逻辑 ...
        
        # 统一的预算检查
        if not budget.can_iterate():
            loop.abort()
            break
        
        budget.consume()
```

**风险评估**：

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| GoalManager 状态同步 | 中 | TurnBudget 每次从 GoalState 读取 |
| 预算消耗时机 | 中 | 统一在 loop.abort() 之前消耗 |

#### 3.2.3 验证方案

```python
# 测试脚本
def test_budget_unification():
    # 测试 IterationBudget
    iter_budget = IterationBudget(max_iterations=5)
    assert iter_budget.can_iterate() == True
    iter_budget.consume()
    assert iter_budget.remaining() == 4
    
    # 测试 TurnBudget
    turn_budget = TurnBudget(max_turns=10)
    assert turn_budget.can_iterate() == True
    turn_budget.consume()
    assert turn_budget.remaining() == 9
    
    print("✓ Budget 接口统一验证通过")
```

---

### 3.3 问题 6: 上下文压缩重复 (P1)

#### 3.3.1 问题描述

**位置**：
- `agent/context/context_manager.py` 第 470-486 行 (build_parts)
- `agent/context/context_manager.py` 第 570-587 行 (build_messages)

**当前状态**：
```python
# build_parts() 和 build_messages() 都有相同的压缩逻辑
if self._context_compressor.should_compress(estimated_tokens):
    processed_history = self.compress(conversation_history, estimated_tokens)
```

#### 3.3.2 优化方案：单一压缩入口

**方案设计**：

```
┌─────────────────────────────────────────────────────────────────┐
│                     优化后的压缩流程                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ContextManager.build_messages()                                │
│      │                                                           │
│      ├──► _prepare_history()  ◄── 唯一压缩入口                  │
│      │       │                                               │
│      │       └──► should_compress()                           │
│      │               │                                           │
│      │               └──► compress()                           │
│      │                                                           │
│      └──► ContextBuilder.build_messages()                       │
│                                                                  │
│  ContextManager.build_parts()                                   │
│      │                                                           │
│      └──► _prepare_history()  ◄── 复用相同逻辑                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**具体修改**：

```python
class ContextManager:
    """上下文管理器"""
    
    async def build_messages(self, ...):
        # 准备历史（统一压缩入口）
        processed_history = await self._prepare_history(conversation_history, estimated_tokens)
        
        # 构建消息
        return await self._context_builder.build_messages(...)
    
    async def build_parts(self, ...):
        # 准备历史（复用相同逻辑）
        processed_history = await self._prepare_history(conversation_history, estimated_tokens)
        
        # 构建 parts
        return await self._context_builder.build_parts(...)
    
    async def _prepare_history(
        self,
        conversation_history: List[Message],
        estimated_tokens: int
    ) -> List[Message]:
        """
        统一的上下文准备逻辑（包含压缩）
        
        这是 build_messages() 和 build_parts() 的共享入口
        """
        if self._context_compressor.should_compress(estimated_tokens):
            return self._context_compressor.compress(
                conversation_history, 
                estimated_tokens
            )
        return conversation_history
```

**风险评估**：

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 性能影响 | 低 | 压缩逻辑仅在超过阈值时触发 |
| 向后兼容 | 低 | 保持相同输出格式 |

#### 3.3.3 验证方案

```python
def test_compression_unification():
    # 验证 build_messages 和 build_parts 使用相同的压缩逻辑
    manager = ContextManager(...)
    
    # 模拟大量历史消息
    history = [Message(role="user", content=f"Message {i}") for i in range(50)]
    
    # 调用两个方法
    result1 = manager.build_messages(history, ...)
    result2 = manager.build_parts(history, ...)
    
    # 验证压缩行为一致
    assert result1.messages[0].role == result2.messages[0].role
    print("✓ 压缩逻辑一致性验证通过")
```

---

### 3.4 问题 2: 消息格式多重转换 (P1)

#### 3.4.1 问题描述

**位置**：
- `agent/session.py` - Message 类
- `agent/react/context.py` - ReActMessage 类
- `agent/context/context_builder.py` - Dict 格式

**转换链路**：
```
Session.Message 
    → ReActContext._messages (ReActMessage)
    → ReActContext.to_messages_dict() (Dict)
    → LLM API 格式
```

#### 3.4.2 优化方案：统一消息格式

**方案设计**：

```python
# 统一的标准化消息格式
@dataclass
class StandardMessage:
    """标准消息格式 - 所有模块使用"""
    role: str  # 'user', 'assistant', 'system', 'tool'
    content: str
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None
    tool_result: Optional[Any] = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为 API 格式"""
        result = {"role": self.role, "content": self.content}
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        if self.tool_result:
            result["tool_result"] = self.tool_result
        return result
    
    @classmethod
    def from_session_message(cls, msg: Message) -> "StandardMessage":
        """从 Session.Message 转换"""
        return cls(
            role=msg.role,
            content=msg.content,
            tool_call_id=msg.tool_call_id,
            tool_result=msg.tool_result,
            timestamp=msg.timestamp,
            metadata=msg.metadata,
        )
```

**适配层设计**：

```python
class MessageAdapter:
    """消息格式适配器"""
    
    @staticmethod
    def to_standard(messages: List[Message]) -> List[StandardMessage]:
        """Session.Message -> StandardMessage"""
        return [StandardMessage.from_session_message(m) for m in messages]
    
    @staticmethod
    def to_react_messages(messages: List[StandardMessage]) -> List[ReActMessage]:
        """StandardMessage -> ReActMessage"""
        return [
            ReActMessage(
                role=m.role,
                content=m.content,
                tool_calls=m.tool_calls,
                tool_call_id=m.tool_call_id,
            )
            for m in messages
        ]
```

**风险评估**：

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 大规模重构 | 高 | 分阶段实施，每个阶段可回滚 |
| 性能影响 | 低 | 转换是轻量级操作 |

#### 3.4.3 实施步骤

**阶段 1**: 定义 StandardMessage 和适配器
**阶段 2**: 修改 Session 使用 StandardMessage
**阶段 3**: 修改 ReActContext 使用 StandardMessage
**阶段 4**: 移除适配器，直接使用 StandardMessage

---

### 3.5 问题 7: Curator/Trajectory 职责重叠 (P1)

#### 3.5.1 问题描述

**位置**：
- `agent/curator/curator.py`
- `agent/curator/trajectory_recorder.py`

**当前状态**：
```python
# agent.py 第 229-263 行
if self._curator and self.enable_curator:
    trajectory = self._trajectory_recorder.get_trajectory()
    result = await self._curator.process_trajectory({...})

self._trajectory_recorder.save_trajectory(metadata=trajectory_metadata)  # 又保存一次
```

#### 3.5.2 优化方案：明确职责边界

**职责重新划分**：

| 组件 | 职责 | 移除 |
|------|------|------|
| **TrajectoryRecorder** | 存储 + 导出训练数据 | 处理逻辑 |
| **Curator** | 处理逻辑（评估、合成） | 存储逻辑 |

**具体修改**：

```python
class TrajectoryRecorder:
    """轨迹记录器 - 仅负责存储和导出"""
    
    def get_trajectory(self) -> Dict[str, Any]:
        """获取轨迹数据（只读）"""
        ...
    
    def save_trajectory(self, metadata: Dict[str, Any]) -> None:
        """保存轨迹到文件"""
        ...
    
    def export_training_data(self) -> TrainingData:
        """导出为训练数据格式"""
        ...


class Curator:
    """Curator - 仅负责处理逻辑"""
    
    async def process_trajectory(self, trajectory: Dict[str, Any]) -> Dict[str, Any]:
        """处理轨迹（不涉及存储）"""
        # 评估轨迹
        evaluation = self._evaluate(trajectory)
        
        # 合成技能（如果有）
        if evaluation.get("should_synthesize"):
            skills = self._synthesize_skills(trajectory)
        
        return {"evaluation": evaluation, "skills": skills}
    
    # 移除 save_trajectory 方法
```

**修改 Agent.chat()**：

```python
async def chat(self, user_input: str, ...) -> AgentResponse:
    # ... 执行逻辑 ...
    
    # Curator 处理轨迹（不保存）
    if self._curator and self.enable_curator:
        trajectory = self._trajectory_recorder.get_trajectory()
        result = await self._curator.process_trajectory(trajectory)
    
    # TrajectoryRecorder 保存轨迹（不处理）
    self._trajectory_recorder.save_trajectory(metadata=trajectory_metadata)
```

---

### 3.6 问题 4: 中断检查重复 (P2)

#### 3.6.1 问题描述

**位置**：
- `agent/agent.py` 第 471-473 行
- `agent/react/loop.py` 第 206-214 行和 222-232 行

**当前状态**：
```python
# agent.py 第 471-473 行
if self._interrupt_requested:
    loop.abort()
    break

# AgentLoop._execute_step() 中两次检查
async def _execute_step(self, context, step_num: int):
    if self._check_interrupt():  # 第一次
        self._state = LoopState.ABORTED
        ...
    
    step_result = await self._execute_step(...)
    
    if self._check_interrupt():  # 第二次
        self._state = LoopState.ABORTED
        ...
```

#### 3.6.2 优化方案：统一中断处理

**方案设计**：

```python
class InterruptController:
    """
    统一中断控制器
    
    设计说明：
    - 单一中断标志源
    - 统一的检查和设置接口
    - 支持多种触发方式
    """
    
    def __init__(self):
        self._interrupt_event = asyncio.Event()
        self._interrupt_reason: Optional[str] = None
    
    def request_interrupt(self, reason: str = "user_requested") -> None:
        """请求中断"""
        self._interrupt_reason = reason
        self._interrupt_event.set()
    
    def check(self) -> bool:
        """检查是否请求中断"""
        return self._interrupt_event.is_set()
    
    def clear(self) -> None:
        """清除中断请求"""
        self._interrupt_event.clear()
        self._interrupt_reason = None
    
    def get_reason(self) -> Optional[str]:
        """获取中断原因"""
        return self._interrupt_reason
```

**修改 AgentLoop**：

```python
class AgentLoop:
    """执行循环"""
    
    def __init__(self, interrupt_controller: InterruptController, ...):
        self._interrupt = interrupt_controller
        # 移除 _check_interrupt() 方法
    
    async def step(self, context) -> StepResult:
        # 统一的检查点
        if self._interrupt.check():
            self._state = LoopState.ABORTED
            return StepResult(status=LoopState.ABORTED, ...)
        
        # 执行步骤
        return await self._execute_step(context, ...)
```

**修改 Agent**：

```python
class Agent:
    """主 Agent 类"""
    
    def __init__(self, ...):
        self._interrupt = InterruptController()
        # 移除 self._interrupt_requested
    
    async def _run_loop(self, ...):
        while True:
            # 统一的检查点
            if self._interrupt.check():
                loop.abort()
                break
            
            # ... 执行逻辑 ...
```

---

### 3.7 问题 3: Rails 双重注册 (P2)

#### 3.7.1 问题描述

**位置**：`agent/agent.py` 第 420-427 行

**当前状态**：
```python
rail_manager = get_rail_manager(session_id)
rail_manager.register_rail(TaskEventRail(session_id))  # 注册到 RailManager
rails = [TaskEventRail(session_id)]  # 又注册到 AgentLoop
```

#### 3.7.2 优化方案：统一注册入口

```python
class RailRegistry:
    """Rails 注册表（单例）"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._rails = {}
        return cls._instance
    
    def register(self, session_id: str, rail: BaseRail) -> None:
        """注册 Rail"""
        if session_id not in self._rails:
            self._rails[session_id] = []
        self._rails[session_id].append(rail)
    
    def get_rails(self, session_id: str) -> List[BaseRail]:
        """获取 Rails 列表"""
        return self._rails.get(session_id, [])
    
    def unregister(self, session_id: str, rail: BaseRail) -> None:
        """取消注册"""
        if session_id in self._rails:
            self._rails[session_id].remove(rail)


# 修改 Agent
class Agent:
    def __init__(self, ...):
        self._rail_registry = RailRegistry()
    
    async def _setup_rails(self, session_id: str) -> List[BaseRail]:
        """设置 Rails 并返回列表"""
        rail = TaskEventRail(session_id)
        
        # 单一注册入口
        self._rail_registry.register(session_id, rail)
        
        return [rail]  # 返回列表供 AgentLoop 使用
```

---

### 3.8 问题 8: Goal 双重存储 (P3)

#### 3.8.1 问题描述

**位置**：
- `agent/goal/manager.py` - GoalManager._current_goal
- `agent/session.py` - Session._goal_state (GoalStateRecord)

#### 3.8.2 优化方案：统一到 GoalManager

```python
class Session:
    """会话管理（移除 GoalStateRecord）"""
    
    def __init__(self, session_id: str, ...):
        # 移除 _goal_state
        # self._goal_state: Optional[GoalStateRecord] = None
        pass
    
    # 移除以下方法：
    # def get_goal_state(self) -> Optional[GoalStateRecord]
    # def set_goal_state(...)
    # def update_goal_status(...)
    # def update_goal_turns(...)
    # def clear_goal_state()


# 统一由 GoalManager 管理
class GoalManager:
    """Goal 管理器（唯一的 Goal 状态源）"""
    
    def get_goal_state(self) -> Optional[GoalState]:
        """获取 Goal 状态"""
        return self._current_goal
    
    def save_state(self) -> None:
        """保存到 Session"""
        if self._current_goal and self._session_id:
            # 使用 Session 的通用接口保存
            self._session.save_goal_state(
                self._session_id,
                self._current_goal.to_json()
            )
```

---

## 四、实施路线图

### 4.1 分阶段实施计划

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           实施时间线                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Week 1-2: P0 问题修复                                                   │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ • 问题 5: 轨迹双重存储统一                                       │    │
│  │ • 问题 1: 预算控制接口统一                                       │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                              ↓                                          │
│  Week 3-4: P1 问题修复                                                   │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ • 问题 6: 上下文压缩重复消除                                     │    │
│  │ • 问题 7: Curator/Trajectory 职责分离                           │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                              ↓                                          │
│  Week 5: P2 问题修复                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ • 问题 4: 中断机制统一                                           │    │
│  │ • 问题 3: Rails 注册统一                                         │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                              ↓                                          │
│  Week 6: P3 问题修复 + 测试                                              │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ • 问题 8: Goal 存储统一                                         │    │
│  │ • 问题 2: 消息格式统一（视情况）                                 │    │
│  │ • 集成测试 + 回归测试                                            │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 每个阶段的交付物

| 阶段 | 交付物 | 验收标准 |
|------|--------|----------|
| **Week 1-2** | Budget 接口代码、轨迹存储重构代码 | 单元测试通过 |
| **Week 3-4** | 压缩逻辑重构、Curator 重构代码 | 功能测试通过 |
| **Week 5** | 中断控制器、Rail 注册重构代码 | 集成测试通过 |
| **Week 6** | 所有重构代码、测试报告 | 回归测试通过 |

---

## 五、风险评估与缓解

### 5.1 风险矩阵

| 风险 | 概率 | 影响 | 风险值 | 缓解措施 |
|------|------|------|--------|----------|
| 大规模重构导致回归问题 | 中 | 高 | **高** | 分阶段实施，每个阶段独立测试 |
| Session 加载延迟 | 低 | 低 | 低 | 缓存机制 |
| Budget 状态不同步 | 中 | 中 | 中 | TurnBudget 每次从 GoalState 读取 |
| 训练数据格式变化 | 低 | 低 | 低 | 保持导出格式兼容 |
| 中断机制失效 | 低 | 高 | **高** | 统一测试覆盖 |

### 5.2 回滚计划

每个阶段实施后，如果发现问题：

1. **立即回滚**：使用 Git revert 恢复到上一个稳定版本
2. **增量修复**：修复问题后重新提交
3. **用户通知**：如果影响用户功能，提前通知

---

## 六、验证与测试

### 6.1 单元测试要求

```python
# test_budget.py
def test_iteration_budget():
    budget = IterationBudget(max_iterations=5)
    assert budget.can_iterate() == True
    budget.consume()
    assert budget.remaining() == 4

def test_turn_budget():
    budget = TurnBudget(max_turns=10)
    assert budget.can_iterate() == True
    budget.consume()
    assert budget.remaining() == 9

# test_trajectory.py
def test_trajectory_unification():
    session = Session('test')
    session.add_message('user', 'Hello')
    
    recorder = TrajectoryRecorder(session=session)
    trajectory = recorder.get_trajectory()
    
    assert len(trajectory['messages']) == 1
    assert trajectory['messages'][0]['content'] == 'Hello'
```

### 6.2 集成测试要求

```bash
# 端到端测试
pytest tests/integration/test_agent_chat.py -v

# 验证数据流
python tests/verify_data_flow.py
```

---

## 七、预期收益

### 7.1 量化收益

| 指标 | 当前 | 优化后 | 改善 |
|------|------|--------|------|
| **消息存储份数** | 2-3 份 | 1 份 | 50-70% 减少 |
| **预算检查点** | 2 处 | 1 处 | 50% 减少 |
| **压缩逻辑重复** | 2 处 | 1 处 | 50% 减少 |
| **中断检查点** | 3 处 | 1 处 | 67% 减少 |

### 7.2 非量化收益

- **代码可维护性提升**：清晰的职责边界
- **调试成本降低**：单一数据源，更易追踪
- **扩展性增强**：模块化设计便于添加新功能

---

## 八、总结

本优化方案针对 Agent-Z 任务处理流程中的 8 处重复/冗余问题，制定了详细的解决方案：

| 优先级 | 问题 | 方案 | 实施难度 |
|--------|------|------|----------|
| **P0** | 轨迹双重存储 | 统一消息数据源 | 中 |
| **P0** | 预算控制重叠 | 统一 Budget 接口 | 低 |
| **P1** | 上下文压缩重复 | 单一压缩入口 | 中 |
| **P1** | Curator/Trajectory 职责 | 明确职责边界 | 低 |
| **P2** | 中断检查重复 | 统一中断控制器 | 低 |
| **P2** | Rails 双重注册 | 统一注册入口 | 低 |
| **P3** | Goal 双重存储 | 统一到 GoalManager | 低 |
| **P1** | 消息格式转换 | 统一标准格式 | 高 |

**建议实施顺序**：P0 → P1 → P2 → P3，确保核心问题优先解决。

---

*文档结束*