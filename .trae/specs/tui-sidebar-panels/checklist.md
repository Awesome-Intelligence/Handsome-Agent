# Checklist - TUI 侧边栏面板

## 阶段一：基础框架

- [x] Task 1.1: 创建 SidebarContainer 组件
- [x] Task 1.2: 创建 TabBar 标签栏（4个标签）
- [x] Task 1.3: 创建 ContentArea 内容区域

- [x] Task 2.1: 定义侧边栏容器样式
- [x] Task 2.2: 定义标签栏样式
- [x] Task 2.3: 定义面板内容样式

## 阶段二：文件树面板

- [x] Task 3.1: 创建 FileTreePanel 组件
- [x] Task 3.2: 实现目录遍历逻辑
- [x] Task 3.3: 实现展开/折叠功能
- [x] Task 3.4: 添加文件/目录图标

## 阶段三：任务面板

- [x] Task 4.1: 创建 TasksPanel 组件
- [x] Task 4.2: 从 Agent 获取任务列表
- [x] Task 4.3: 显示任务名称和状态

## 阶段四：Agent 面板

- [x] Task 5.1: 创建 AgentPanel 组件
- [x] Task 5.2: 显示 Agent 名称和状态
- [x] Task 5.3: 显示当前操作

## 阶段五：上下文面板

- [x] Task 6.1: 创建 ContextPanel 组件
- [x] Task 6.2: 显示 Token 计数
- [x] Task 6.3: 显示消息数量和上下文占用

## 阶段六：快捷键和交互

- [x] Task 7.1: Ctrl+B 显示/隐藏侧边栏
- [x] Task 7.2: Ctrl+1-4 切换面板
- [x] Task 7.3: ↑/↓ 导航
- [x] Task 7.4: Esc 返回聊天区域

- [x] Task 8.1: 修改主布局支持侧边栏
- [x] Task 8.2: 连接面板数据源
- [x] Task 8.3: 测试整体功能

## 最终验证

- [x] 侧边栏可以正常显示和隐藏
- [x] 四个面板都可以切换
- [x] 文件树正确显示项目结构
- [x] 任务面板显示任务列表
- [x] Agent 面板显示状态信息
- [x] 上下文面板显示统计数据
- [x] 所有快捷键正常工作
- [x] 运行 `python -m cli.main --textual` 测试完整功能