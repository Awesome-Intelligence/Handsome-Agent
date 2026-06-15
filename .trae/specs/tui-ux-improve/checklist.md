# Checklist - TUI 用户体验优化

## 阶段一：布局重构

- [x] Task 1.1: 移除 Tabs 标签栏组件，暂时使用单一视图
- [x] Task 1.2: 调整 compose() 方法中的组件顺序
- [x] Task 1.3: 更新 CSS 样式以适应新布局

- [x] Task 2.1: 创建自定义 HeaderWidget 类
- [x] Task 2.2: 显示模型名称、工作目录、上下文占用百分比
- [x] Task 2.3: 实现动态更新机制

- [x] Task 3.1: 创建自定义 StatusBar 类
- [x] Task 3.2: 显示当前目录、Token 统计
- [x] Task 3.3: 显示快捷键提示

- [x] Task 4.1: 使用 InputArea 或 TextArea 组件
- [x] Task 4.2: 设置固定底部位置（dock: bottom）
- [x] Task 4.3: 添加发送按钮

## 阶段二：欢迎横幅优化

- [x] Task 5.1: 移除复杂的功能列表
- [x] Task 5.2: 显示简洁的欢迎语和基本提示
- [x] Task 5.3: 调整横幅样式和位置

## 阶段三：交互优化

- [x] Task 6.1: 配置 RichLog 的 auto_scroll 属性
- [x] Task 6.2: 处理用户手动滚动时的行为

- [x] Task 7.1: 测试 Enter 发送消息
- [x] Task 7.2: 测试 Ctrl+C 中断操作
- [x] Task 7.3: 测试 Ctrl+L 清屏

## 阶段四：样式优化

- [x] Task 8.1: 更新主背景色为 #0d1117
- [x] Task 8.2: 调整边框和分隔线颜色
- [x] Task 8.3: 优化输入框和按钮样式

- [x] Task 9.1: 调整文字大小和行高
- [x] Task 9.2: 优化组件间距
- [x] Task 9.3: 调整内边距

## 最终验证

- [x] 界面布局从上到下为：Header → Chat → Footer → Composer
- [x] Header 显示模型名称和上下文占用
- [x] Footer 显示快捷键提示
- [x] 输入框固定在底部
- [x] 欢迎信息简洁明了
- [x] 用户可以轻松上手使用
- [x] 运行 `python -m cli.main --textual` 无错误
- [x] 界面样式与 CodeWhale 接近