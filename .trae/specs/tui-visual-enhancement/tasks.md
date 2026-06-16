# Tasks - TUI 视觉美化增强

## Task 1: 消息 Markdown 渲染优化

- [x] Task 1.1: 修改 `_append_message` 方法 - 将消息渲染从 Panel 改为 Markdown 样式
  - 1.1.1: 用户消息使用 `**You**` 粗体蓝色标题
  - 1.1.2: 助手消息使用 `**Assistant**` 粗体绿色标题
  - 1.1.3: 工具消息使用缩进 + 图标样式

- [x] Task 1.2: 移除 `from rich.panel import Panel` 导入（如果不再需要）

## Task 2: Tab 按钮底部高亮指示器

- [x] Task 2.1: 更新 CSS 样式 - 为 `.sidebar-tab.active` 添加底部 2px 蓝色线条
  - 2.1.1: 修改 `textual_app.py` 中的 CSS 定义
  - 2.1.2: 或者在 `sidebar.py` 中的 SidebarTabBar 组件添加内联样式

- [x] Task 2.2: 测试 Tab 切换时的视觉反馈

## Task 3: 流式输出动画效果

- [x] Task 3.1: 添加 CSS 动画定义
  - 3.1.1: 添加 `.streaming-indicator` 闪烁动画
  - 3.1.2: 添加 `.thinking-indicator` 思考内容动画

- [x] Task 3.2: 修改流式消息显示逻辑
  - 3.2.1: 在流式输出时显示闪烁光标 `▌`
  - 3.2.2: 在思考内容中显示动画指示器

## Task 4: Header 状态指示器

- [x] Task 4.1: 添加状态指示器颜色常量
  - 4.1.1: STATUS_ONLINE = "#3fb950"
  - 4.1.2: STATUS_BUSY = "#f0883e"
  - 4.1.3: STATUS_ERROR = "#f85149"

- [x] Task 4.2: 修改 Header 组件
  - 4.2.1: 添加状态指示器显示区域
  - 4.2.2: 实现状态更新方法 `set_status(status: str)`

- [x] Task 4.3: 在 Agent 处理开始/结束时调用状态更新

## Task 5: Footer 快捷键分组显示

- [x] Task 5.1: 更新 CSS 样式 - 添加 `.footer-key` 样式定义

- [x] Task 5.2: 修改 Footer 内容渲染
  - 5.2.1: 将快捷键格式化为 `[Ctrl+K]` 样式
  - 5.2.2: 使用 `|` 分隔不同分组

- [x] Task 5.3: 更新 `_render_footer` 或相关方法

## Task Dependencies

- Task 1: 独立进行
- Task 2: 独立进行
- Task 3: 独立进行
- Task 4: 独立进行
- Task 5: 独立进行

（所有任务可并行进行，彼此无依赖）

## 验证方式

- [x] 运行 `python -m cli.main --textual` 查看界面
- [x] 发送消息验证 Markdown 渲染效果
- [x] 点击 Tab 按钮验证底部高亮
- [x] 发送长消息验证流式输出动画
- [x] 观察 Header 状态指示器变化
- [x] 查看 Footer 快捷键分组样式