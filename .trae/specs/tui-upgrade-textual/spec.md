# Handsome-Agent TUI 框架升级规范

## Why

当前 Handsome-Agent 的 TUI 框架基于 curses + Rich + inquirer 混合方案，存在以下问题：
- 功能相对简单，缺少多标签页、快捷键系统等高级交互
- curses 库 API 底层，开发效率低
- 与 CodeWhale 相比，UI 体验有明显差距

通过引入 Textual 框架，可以实现接近 CodeWhale 的 TUI 体验，同时保持 Python 开发效率。

## What Changes

### 阶段一：框架迁移

- 引入 Textual 框架作为新的 TUI 核心
- 保持与现有 Rich 代码的兼容性
- 实现基础的 Textual App 结构
- 迁移现有的 curses 交互组件到 Textual widgets

### 阶段二：核心功能实现

- 实现多标签页系统（Chat/Delegation）
- 实现快捷键绑定系统
- 增强流式输出显示
- 实现会话持久化

### 阶段三：高级功能

- 实现权限审批系统
- 实现新用户引导流程
- 增强主题/皮肤系统
- 优化性能和用户体验

## Impact

- Affected specs: TUI交互体验、命令系统配置
- Affected code: cli/ 目录下的所有 UI 相关代码

## ADDED Requirements

### Requirement: Textual 框架基础架构

系统 SHALL 提供基于 Textual 框架的 TUI 核心架构，兼容现有业务逻辑。

#### Scenario: Textual App 启动
- **WHEN** 用户启动 TUI 应用
- **THEN** 初始化 Textual App，显示欢迎横幅和状态栏

#### Scenario: 基础布局
- **WHEN** TUI 应用渲染
- **THEN** 显示 Header、Content 区域、Footer

### Requirement: 多标签页系统

系统 SHALL 提供多标签页支持，允许用户在不同会话间切换。

#### Scenario: 创建新标签页
- **WHEN** 用户按下 Ctrl+T 或点击新建按钮
- **THEN** 创建新的 Chat 标签页并切换到该标签

#### Scenario: 切换标签页
- **WHEN** 用户按下 Ctrl+Tab 或点击标签
- **THEN** 切换到目标标签页

#### Scenario: 关闭标签页
- **WHEN** 用户按下 Ctrl+W 或点击关闭按钮
- **THEN** 关闭当前标签页，切换到相邻标签

### Requirement: 快捷键绑定系统

系统 SHALL 提供完整的快捷键绑定，支持常用操作。

#### Scenario: 全局快捷键
- **WHEN** 用户按下 Ctrl+K
- **THEN** 打开命令面板

#### Scenario: 导航快捷键
- **WHEN** 用户按下 ↑/↓ 或 j/k
- **THEN** 上下滚动消息列表

#### Scenario: 快捷键帮助
- **WHEN** 用户按下 F1 或 Ctrl+/
- **THEN** 显示快捷键帮助面板

### Requirement: 流式输出增强

系统 SHALL 支持流式输出，并可选显示模型思考过程。

#### Scenario: 流式文本输出
- **WHEN** LLM 返回流式数据
- **THEN** 实时显示在消息区域

#### Scenario: 思考过程显示（可选）
- **WHEN** 用户启用思考显示
- **THEN** 区分显示思考过程和最终输出

### Requirement: 会话持久化

系统 SHALL 支持会话历史持久化，支持会话恢复。

#### Scenario: 会话自动保存
- **WHEN** 用户结束对话或应用退出
- **THEN** 自动保存会话历史到本地存储

#### Scenario: 会话恢复
- **WHEN** 用户启动应用并选择历史会话
- **THEN** 恢复完整的会话上下文

### Requirement: 权限审批系统

系统 SHALL 提供工具执行前的权限确认机制。

#### Scenario: 工具执行确认
- **WHEN** 用户执行敏感工具（如删除文件）
- **THEN** 显示确认对话框，等待用户确认

#### Scenario: 审批模式配置
- **WHEN** 用户配置审批模式为 Auto/Suggest/Manual
- **THEN** 根据模式自动处理或提示确认

## MODIFIED Requirements

### Requirement: 颜色和主题系统

保持现有的牛油果绿主题，同时适配 Textual 的主题系统。

#### Scenario: 主题加载
- **WHEN** TUI 应用启动
- **THEN** 加载用户配置的主题（默认牛油果绿）

### Requirement: 状态栏组件

将现有的 StatusBar 组件迁移到 Textual，实现实时信息显示。

#### Scenario: 状态栏更新
- **WHEN** 模型响应时
- **THEN** 更新 Token 计数、上下文占用等信息

## REMOVED Requirements

### Requirement: 旧的 curses 交互组件

**Reason**: 被 Textual 原生组件替代，不再需要 curses_radiolist 和 curses_checklist

**Migration**: 
- 使用 Textual 的 SelectionList、Checkbox 等替代
- 保留降级机制，在 Textual 不可用时回退到简单文本输入

## Technical Architecture

### 技术选型

| 组件 | 技术选型 | 版本要求 |
|------|----------|----------|
| TUI框架 | Textual | ≥0.50.0 |
| 增强输出 | Rich | ≥13.0.0 (保持兼容) |
| 会话存储 | SQLite3 + SQLAlchemy | 最新稳定版 |
| 异步支持 | asyncio | 标准库 |

### 架构层次

```
┌─────────────────────────────────────────┐
│         cli/tui/textual_app.py          │
│        (Textual App 主类)               │
├─────────────────────────────────────────┤
│         cli/tui/widgets/                │
│    (自定义 Widget 组件)                 │
├─────────────────────────────────────────┤
│         cli/tui/views/                  │
│      (视图层：Chat, Help, etc)          │
├─────────────────────────────────────────┤
│         cli/components/                 │
│   (业务组件：颜色、输出、状态栏)         │
├─────────────────────────────────────────┤
│         cli/core/                       │
│     (核心逻辑：Agent、工具执行)          │
└─────────────────────────────────────────┘
```

### 迁移策略

1. **渐进式迁移**：保持现有功能可用，逐步替换
2. **接口兼容**：保持与现有业务逻辑的接口一致
3. **降级支持**：Textual 不可用时回退到简单模式
4. **主题兼容**：复用现有的牛油果绿主题配置