# TUI 任务面板实时同步规范

## Why

当用户与 Agent 对话时，复杂任务会被 TaskPlanner 拆分成子任务执行。用户期望在 TUI 侧边栏实时看到：
- 任务拆分后的子任务列表
- 每个子任务的实时状态（待处理→执行中→完成/失败）
- 任务执行的进度

当前 TasksPane 仅是占位组件，需要实现真正的任务同步功能。

## What Changes

1. **扩展流式事件系统** - 在 `common/streaming/events.py` 新增任务相关事件类型
2. **新增 TUIConsumer** - 创建 `tui/consumers/tasks_consumer.py`，将流式事件转换为 TUI 消息
3. **改造 TasksPane** - 重写 `tui/sidebar.py` 中的 TasksPane，实现任务列表显示
4. **新增 TUI 消息** - 创建 `tui/messages.py`，定义 Textual 消息类型
5. **集成事件发射** - 在 `agent/task/task_planner.py` 的关键节点发射事件

### 架构图

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           Agent 执行层                                    │
│  ┌─────────────────┐      ┌──────────────────┐                          │
│  │   TaskPlanner   │─────▶│  StreamEmitter   │─────▶  Event Queue         │
│  │  (任务规划/执行) │      │   (事件发射器)    │                          │
│  └────────┬────────┘      └──────────────────┘                          │
└───────────┼──────────────────────────────────────────────────────────────┘
            │
            ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         事件消费者层                                      │
│  ┌─────────────────┐      ┌──────────────────┐                           │
│  │ ConsoleConsumer │      │   TUIConsumer   │  ◀── 新增                   │
│  │   (已有-控制台)  │      │   (新-广播)      │                           │
│  └─────────────────┘      └────────┬─────────┘                           │
│                                     │ (post_message)                     │
│                                     ▼                                     │
│                            ┌──────────────────┐                           │
│                            │  TasksPane       │                           │
│                            │  (Textual 组件)  │                           │
│                            └──────────────────┘                           │
└──────────────────────────────────────────────────────────────────────────┘
```

## Impact

- Affected specs: TUI 交互体验
- Affected code:
  - `common/streaming/events.py` - 扩展事件类型
  - `common/streaming/consumer.py` - 新增 TUIConsumer
  - `tui/messages.py` - 新增 TUI 消息定义
  - `tui/sidebar.py` - 重写 TasksPane
  - `tui/consumers/tasks_consumer.py` - 新增消费者
  - `agent/task/task_planner.py` - 集成事件发射

## ADDED Requirements

### Requirement: 任务事件类型

系统 SHALL 提供完整的任务生命周期事件。

#### Scenario: 任务创建
- **WHEN** Agent 开始拆分复杂任务
- **THEN** 发射 `PLAN_START` 事件

#### Scenario: 子任务创建
- **WHEN** Agent 规划出子任务列表
- **THEN** 发射 `PLAN_PROGRESS` 事件，包含所有子任务

#### Scenario: 子任务开始
- **WHEN** Agent 开始执行某个子任务
- **THEN** 发射 `SUBTASK_STARTED` 事件

#### Scenario: 子任务完成
- **WHEN** 子任务执行完成或失败
- **THEN** 发射 `SUBTASK_COMPLETED` 事件

### Requirement: TUIConsumer 事件转换

系统 SHALL 将流式事件转换为 TUI 可消费的消息。

#### Scenario: 事件订阅
- **WHEN** TUIConsumer 初始化
- **THEN** 注册到 ConsumerRegistry

#### Scenario: 事件转换
- **WHEN** 收到流式任务事件
- **THEN** 转换为 TasksPaneUpdated 或 CurrentTaskChanged 消息

#### Scenario: 安全发布
- **WHEN** App 未挂载时尝试发布消息
- **THEN** 静默忽略，不抛出异常

### Requirement: TasksPane 任务显示

系统 SHALL 在 TUI 侧边栏实时显示任务状态。

#### Scenario: 空状态
- **WHEN** 没有任务时
- **THEN** 显示 "[dim]暂无任务[/dim]"

#### Scenario: 任务列表
- **WHEN** 有任务时
- **THEN** 显示所有子任务及其状态

#### Scenario: 当前任务高亮
- **WHEN** 有任务正在执行
- **THEN** 在面板顶部高亮显示当前任务

#### Scenario: 状态图标
- **WHEN** 显示任务状态时
- **THEN** 使用对应图标：⏳pending, 🔄running, ✅completed, ❌failed

### Requirement: 任务进度显示

系统 SHALL 显示任务执行进度。

#### Scenario: 进度条
- **WHEN** 任务正在执行
- **THEN** 显示进度条 (e.g., ████████░░ 80%)

#### Scenario: 进度百分比
- **WHEN** 计算整体进度
- **THEN** 显示 completed/total 和百分比

## Technical Implementation

### 事件类型扩展

```python
# common/streaming/events.py 新增
class StreamEventType(Enum):
    # ... 现有事件 ...

    # 任务相关事件
    SUBTASK_STARTED = "stream.subtask_started"
    SUBTASK_PROGRESS = "stream.subtask_progress"
    SUBTASK_COMPLETED = "stream.subtask_completed"
    TASK_PROGRESS = "stream.task_progress"
    TASK_COMPLETED = "stream.task_completed"
```

### TUIConsumer 实现

```python
# tui/consumers/tasks_consumer.py
class TUIConsumer(StreamConsumer):
    def __init__(self, app):
        self._app = app
        self._tasks: Dict[str, TaskState] = {}

    async def on_event(self, event: StreamEvent) -> None:
        # 根据事件类型处理
        if event.type == StreamEventType.PLAN_START:
            await self._handle_plan_start(event)
        # ...
```

### TasksPane 实现

```python
# tui/sidebar.py
class TasksPane(SidebarPane):
    async def on_tasks_pane_updated(self, event: TasksPaneUpdated) -> None:
        """处理任务面板更新"""
        self._tasks = event.tasks
        self._update_display()
```

### 样式定义

```css
/* tui/theming/css/components.css */
#tasks-pane .task-item.running {
    color: $accent;
    text-style: bold;
}
```

## Success Criteria

- [ ] Agent 拆分任务时，侧边栏实时显示子任务
- [ ] 子任务状态变更时，侧边栏同步更新
- [ ] 当前执行任务高亮显示在面板顶部
- [ ] 任务进度以进度条形式显示
- [ ] 不同状态使用不同图标区分
