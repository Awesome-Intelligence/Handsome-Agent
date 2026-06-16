# Checklist - TUI 视觉美化增强

## Task 1: 消息 Markdown 渲染优化

- [x] Task 1.1: 修改 `_append_message` 方法 - 将消息渲染从 Panel 改为 Markdown 样式
- [x] Task 1.2: 移除 `from rich.panel import Panel` 导入（如果不再需要）

## Task 2: Tab 按钮底部高亮指示器

- [x] Task 2.1: 更新 CSS 样式 - 为 `.sidebar-tab.active` 添加底部 2px 蓝色线条
- [x] Task 2.2: 测试 Tab 切换时的视觉反馈

## Task 3: 流式输出动画效果

- [x] Task 3.1: 添加 CSS 动画定义
- [x] Task 3.2: 修改流式消息显示逻辑

## Task 4: Header 状态指示器

- [x] Task 4.1: 添加状态指示器颜色常量
- [x] Task 4.2: 修改 Header 组件
- [x] Task 4.3: 在 Agent 处理开始/结束时调用状态更新

## Task 5: Footer 快捷键分组显示

- [x] Task 5.1: 更新 CSS 样式 - 添加 `.footer-key` 样式定义
- [x] Task 5.2: 修改 Footer 内容渲染
- [x] Task 5.3: 更新相关方法

## 最终验证

- [x] 消息使用 Markdown 样式显示，不再使用厚重 Panel
- [x] Tab 按钮有底部高亮指示器
- [x] 流式输出有闪烁动画
- [x] Header 显示在线/忙碌状态指示
- [x] Footer 快捷键使用分组样式
- [x] 整体视觉风格与 CodeWhale 接近
- [x] 运行 `python -m cli.main --textual` 无错误