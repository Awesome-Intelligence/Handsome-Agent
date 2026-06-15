# TUI 侧边栏面板规范

## Why

当前 TUI 界面缺少侧边栏，用户无法快速查看文件结构、任务状态、Agent 状态和上下文信息。需要添加类似 CodeWhale 的侧边栏功能，提升用户体验和工作效率。

## What Changes

### 新增功能

1. **文件树面板** - 显示项目文件结构，支持展开/折叠
2. **任务面板** - 显示当前任务列表和状态
3. **Agent 面板** - 显示 Agent 状态和活动
4. **上下文面板** - 显示当前上下文信息和统计

### 布局设计

```
┌────────────────────────────────────────────────────────────────────────┐
│ Header                                                                │
├──────────────────────────────────────────────────────┬─────────────────┤
│                                                      │ 文件树 │ 任务 │ │
│                                                      │ Agent  │ 上下文│ │
│              主聊天区域                                ├─────────────────┤
│                                                      │                 │
│                                                      │   面板内容       │
│                                                      │                 │
│                                                      │                 │
├──────────────────────────────────────────────────────┤                 │
│ Footer / Status                                      │                 │
├──────────────────────────────────────────────────────┴─────────────────┤
│ 输入区域                                                              │
└────────────────────────────────────────────────────────────────────────┘
```

### 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+B` | 显示/隐藏侧边栏 |
| `Ctrl+1` | 聚焦文件树面板 |
| `Ctrl+2` | 聚焦任务面板 |
| `Ctrl+3` | 聚焦 Agent 面板 |
| `Ctrl+4` | 聚焦上下文面板 |
| `↑/↓` | 在面板内导航 |
| `Enter` | 展开/选中项目 |
| `Esc` | 关闭侧边栏或返回聊天区域 |

## Architecture

### 组件结构

```
SidebarContainer
├── TabBar (4 个标签)
│   ├── FileTreeTab
│   ├── TasksTab
│   ├── AgentTab
│   └── ContextTab
└── ContentArea
    ├── FileTreePanel (文件树)
    ├── TasksPanel (任务列表)
    ├── AgentPanel (Agent 状态)
    └── ContextPanel (上下文信息)
```

## Impact

- Affected specs: TUI 交互体验
- Affected code: `cli/tui/textual_app.py`, 新建 `cli/tui/widgets/sidebar.py`

## ADDED Requirements

### Requirement: 文件树面板

系统 SHALL 显示项目文件结构。

#### Scenario: 显示文件树
- **WHEN** 用户打开侧边栏并选择文件树面板
- **THEN** 显示当前工作目录的文件树

#### Scenario: 展开/折叠目录
- **WHEN** 用户点击目录
- **THEN** 目录展开或折叠

#### Scenario: 切换到文件
- **WHEN** 用户双击文件
- **THEN** 文件路径复制到剪贴板

### Requirement: 任务面板

系统 SHALL 显示当前任务列表。

#### Scenario: 显示任务
- **WHEN** 用户打开任务面板
- **THEN** 显示任务名称和状态

### Requirement: Agent 面板

系统 SHALL 显示 Agent 当前状态。

#### Scenario: 显示 Agent 状态
- **WHEN** 用户打开 Agent 面板
- **THEN** 显示 Agent 名称、状态、当前操作

### Requirement: 上下文面板

系统 SHALL 显示上下文统计信息。

#### Scenario: 显示上下文信息
- **WHEN** 用户打开上下文面板
- **THEN** 显示 Token 计数、消息数量等统计

### Requirement: 侧边栏切换

系统 SHALL 支持侧边栏的显示/隐藏和面板切换。

#### Scenario: 切换侧边栏
- **WHEN** 用户按 Ctrl+B
- **THEN** 侧边栏显示或隐藏

#### Scenario: 切换面板
- **WHEN** 用户点击标签或按 Ctrl+1-4
- **THEN** 显示对应的面板内容

## MODIFIED Requirements

### Requirement: 主布局

修改主布局以支持侧边栏。

#### Scenario: 侧边栏显示
- **WHEN** 侧边栏显示
- **THEN** 主聊天区域宽度相应减少

## Success Criteria

- [ ] 按 Ctrl+B 可以显示/隐藏侧边栏
- [ ] 可以切换到不同面板
- [ ] 文件树显示项目文件
- [ ] 任务面板显示任务列表
- [ ] Agent 面板显示状态
- [ ] 上下文面板显示统计信息
- [ ] 快捷键正常工作