# Checklist - TUI 任务面板实时同步

## 阶段一：基础框架

- [ ] Task 1.1: 在 `common/streaming/events.py` 新增任务相关事件类型
- [ ] Task 1.2: 在 `common/streaming/emitter.py` 新增事件发射方法
- [ ] Task 1.3: 更新 `__all__` 导出列表

- [ ] Task 2.1: 创建 `tui/messages.py`
- [ ] Task 2.2: 定义 TaskItem 数据类
- [ ] Task 2.3: 定义 TasksPaneUpdated 消息
- [ ] Task 2.4: 定义 CurrentTaskChanged 消息

- [ ] Task 3.1: 创建 `tui/consumers/` 目录
- [ ] Task 3.2: 创建 `tui/consumers/__init__.py`
- [ ] Task 3.3: 实现 TUIConsumer 类
- [ ] Task 3.4: 实现事件处理方法
- [ ] Task 3.5: 在 `common/streaming/consumer.py` 添加导出

## 阶段二：TasksPane 重写

- [ ] Task 4.1: 修改 `tui/sidebar.py` 中的 TasksPane
- [ ] Task 4.2: 实现 compose 方法
- [ ] Task 4.3: 实现消息处理方法
- [ ] Task 4.4: 实现 _update_display 方法
- [ ] Task 4.5: 实现进度条生成方法

- [ ] Task 5.1: 在 `tui/theming/css/components.css` 添加样式
- [ ] Task 5.2: 添加任务状态样式
- [ ] Task 5.3: 添加当前任务高亮样式

## 阶段三：Agent 层集成

- [ ] Task 6.1: 在 TaskPlanner 添加 emitter 引用
- [ ] Task 6.2: 在 decompose_task 发射事件
- [ ] Task 6.3: 在 update_subtask_status 发射子任务事件

- [ ] Task 7.1: 在 HandsomeAgentApp 初始化 TUIConsumer
- [ ] Task 7.2: 注册到 ConsumerRegistry
- [ ] Task 7.3: 处理 App 未挂载的情况

## 最终验证

- [ ] Agent 拆分任务时，侧边栏实时显示子任务
- [ ] 子任务状态变更时，侧边栏同步更新
- [ ] 当前执行任务高亮显示在面板顶部
- [ ] 任务进度以进度条形式显示
- [ ] 不同状态使用不同图标区分
