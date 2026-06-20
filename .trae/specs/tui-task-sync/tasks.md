# Tasks - TUI 任务面板实时同步

## 阶段一：基础框架

- [ ] Task 1: 扩展流式事件类型
  - [ ] 1.1: 在 `common/streaming/events.py` 新增任务相关事件类型
  - [ ] 1.2: 在 `common/streaming/emitter.py` 新增事件发射方法
  - [ ] 1.3: 更新 `__all__` 导出列表

- [ ] Task 2: 创建 TUI 消息定义
  - [ ] 2.1: 创建 `tui/messages.py`
  - [ ] 2.2: 定义 TaskItem 数据类
  - [ ] 2.3: 定义 TasksPaneUpdated 消息
  - [ ] 2.4: 定义 CurrentTaskChanged 消息

- [ ] Task 3: 创建 TUIConsumer
  - [ ] 3.1: 创建 `tui/consumers/` 目录
  - [ ] 3.2: 创建 `tui/consumers/__init__.py`
  - [ ] 3.3: 实现 TUIConsumer 类
  - [ ] 3.4: 实现事件处理方法
  - [ ] 3.5: 在 `common/streaming/consumer.py` 添加导出

## 阶段二：TasksPane 重写

- [ ] Task 4: 重写 TasksPane 组件
  - [ ] 4.1: 修改 `tui/sidebar.py` 中的 TasksPane
  - [ ] 4.2: 实现 compose 方法
  - [ ] 4.3: 实现消息处理方法
  - [ ] 4.4: 实现 _update_display 方法
  - [ ] 4.5: 实现进度条生成方法

- [ ] Task 5: 添加任务面板样式
  - [ ] 5.1: 在 `tui/theming/css/components.css` 添加样式
  - [ ] 5.2: 添加任务状态样式（pending/running/completed/failed）
  - [ ] 5.3: 添加当前任务高亮样式

## 阶段三：Agent 层集成

- [ ] Task 6: 集成事件发射到 TaskPlanner
  - [ ] 6.1: 在 TaskPlanner 添加 emitter 引用
  - [ ] 6.2: 在 decompose_task 发射 PLAN_START/PROGRESS/COMPLETE
  - [ ] 6.3: 在 update_subtask_status 发射子任务事件

- [ ] Task 7: 集成 TUIConsumer 到 TUI App
  - [ ] 7.1: 在 HandsomeAgentApp 初始化 TUIConsumer
  - [ ] 7.2: 注册到 ConsumerRegistry
  - [ ] 7.3: 处理 App 未挂载的情况

## Task Dependencies

- Task 2 依赖 Task 1
- Task 3 依赖 Task 1、Task 2
- Task 4 依赖 Task 2、Task 3
- Task 5 可与 Task 4 并行
- Task 7 依赖 Task 3、Task 4
