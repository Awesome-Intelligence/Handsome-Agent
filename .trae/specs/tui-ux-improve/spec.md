# TUI 用户体验优化规范

## Why

当前 Handsome-Agent 的 Textual TUI 界面与 CodeWhale 存在较大差距，用户反馈"界面有点怪，不太会用"。需要重新设计界面布局和交互体验，参考 CodeWhale 的成熟设计。

## What Changes

### 核心问题

1. **布局结构不清晰** - 输入区域位置和样式与 CodeWhale 差异大
2. **状态信息不足** - 缺少模型信息、Token 计数等关键状态
3. **交互习惯不同** - 用户不熟悉当前的交互方式
4. **欢迎横幅问题** - 横幅显示位置和样式需要调整

### 设计目标

参考 CodeWhale 的 TUI 布局，实现以下目标：
- 界面布局清晰：Header → Chat → Composer → Footer
- 状态信息完整：显示模型、上下文占用、Token 统计
- 交互直觉化：符合常见 CLI 工具的交互习惯
- 输入体验流畅：输入框固定在底部，上方显示聊天历史

## Layout Design

### 布局结构（从上到下）

```
┌─────────────────────────────────────────────────────────┐
│ [模型标签] Handsome Agent    [上下文: 45%] [模型: GPT-4] │  ← Header (1行)
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 欢迎使用 Handsome Agent                           │   │
│  │ 键入你的问题或请求...                            │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │  ← Chat Area (弹性高度)
│  用户: 你好                                             │
│  Agent: 你好！有什么可以帮助你的？                      │
│                                                         │
│                                                         │
├─────────────────────────────────────────────────────────┤
│ [cwd: ~/project]  [tokens: 1024/4096]  [Ctrl+K: 命令]   │  ← Footer (1行)
├─────────────────────────────────────────────────────────┤
│ > 请输入消息...                                   [发送] │  ← Composer (2-3行)
└─────────────────────────────────────────────────────────┘
```

### 组件说明

| 组件 | 位置 | 内容 | 特点 |
|------|------|------|------|
| **Header** | 顶部固定 | 模型名称、工作目录、上下文占用 | 1行高度，信息密集 |
| **Chat Area** | 中间弹性 | 欢迎信息+聊天历史 | 可滚动，自动跟随新消息 |
| **Footer** | 底部固定(输入框上方) | 快捷键提示、状态信息 | 1行高度 |
| **Composer** | 最底部固定 | 输入框+发送按钮 | 2-3行高度，支持多行输入 |

### 关键设计决策

1. **输入框固定在底部** - 用户始终可以看到输入框，符合聊天工具习惯
2. **聊天历史可滚动** - 上方区域显示完整对话历史
3. **欢迎信息简洁** - 首次使用时显示简洁的欢迎语
4. **状态信息集中** - 底部状态栏显示所有状态信息

## Impact

- Affected specs: TUI交互体验
- Affected code: `cli/tui/textual_app.py`, `cli/tui/widgets/`

## ADDED Requirements

### Requirement: Header 信息展示

系统 SHALL 在顶部 Header 显示关键状态信息。

#### Scenario: Header 内容
- **WHEN** TUI 应用启动
- **THEN** 显示模型名称、工作目录、上下文占用百分比

#### Scenario: Header 动态更新
- **WHEN** 模型响应时 Token 使用变化
- **THEN** 实时更新上下文占用百分比

### Requirement: 底部输入区设计

系统 SHALL 在底部提供固定的输入区域。

#### Scenario: 输入框位置
- **WHEN** 用户打开 TUI 应用
- **THEN** 输入框固定在屏幕最底部

#### Scenario: 多行输入支持
- **WHEN** 用户输入多行文本
- **THEN** 输入框自动扩展高度（最大3行）

#### Scenario: 发送消息
- **WHEN** 用户按下 Enter 或点击发送按钮
- **THEN** 发送消息，清空输入框，滚动到聊天底部

### Requirement: 聊天历史区设计

系统 SHALL 在中间区域显示聊天历史。

#### Scenario: 欢迎信息
- **WHEN** 用户首次打开应用（无聊天历史）
- **THEN** 显示简洁欢迎信息和提示

#### Scenario: 历史消息显示
- **WHEN** 有聊天历史时
- **THEN** 显示完整对话历史，最新消息在底部

#### Scenario: 自动滚动
- **WHEN** 新消息到达时
- **THEN** 自动滚动到最新消息（除非用户手动滚动到上方）

### Requirement: Footer 状态栏设计

系统 SHALL 在底部显示快捷键提示和状态信息。

#### Scenario: Footer 内容
- **WHEN** TUI 应用运行时
- **THEN** 显示当前目录、Token 统计、快捷键提示

#### Scenario: 快捷键提示
- **WHEN** 用户悬停或查看 Footer
- **THEN** 显示常用快捷键提示

## MODIFIED Requirements

### Requirement: 移除冗余标签页

当前的多标签页系统功能过于复杂，对于基本使用不需要。

#### Scenario: 简化标签页
- **WHEN** 用户打开 TUI
- **THEN** 默认显示单一聊天视图，不显示标签栏

#### Scenario: 标签页可选
- **WHEN** 用户启用多会话功能时
- **THEN** 可以通过 Ctrl+T 打开新标签页

### Requirement: 简化欢迎横幅

当前的欢迎横幅过于复杂，需要简化。

#### Scenario: 欢迎横幅简化
- **WHEN** 用户首次打开应用
- **THEN** 显示简洁的欢迎语，不显示复杂的功能列表

## Technical Implementation

### 布局实现（Textual）

```python
def compose(self) -> ComposeResult:
    yield Header()  # 自定义 Header，包含状态信息
    
    # 主聊天区域
    with VerticalScroll(id="chat-scroll"):
        yield Static("", id="welcome-banner")  # 欢迎信息
        yield RichLog(id="chat-log")  # 聊天历史
    
    # Footer 状态栏
    with StatusBar():
        yield Static("[模型]", id="model-info")
        yield Static("[目录]", id="cwd-info")
        yield Static("[快捷键]", id="key-hints")
    
    # 输入区域（固定底部）
    with InputArea():
        yield TextArea(id="user-input", placeholder="请输入消息...")
        yield Button("发送", id="send-button")
```

### 样式调整

```css
/* 主屏幕：深色背景 */
Screen {
    background: #0d1117;
}

/* 聊天区域：保持深色 */
#chat-log {
    background: #0d1117;
    padding: 1 2;
}

/* 输入区域：边框分明 */
InputArea {
    height: 3;
    background: #161b22;
    border-top: solid #30363d;
}

/* 状态栏：紧凑显示 */
StatusBar {
    height: 1;
    background: #21262d;
    color: #8b949e;
}
```

## Migration from Current Implementation

### 当前问题

1. 输入区域在 `#input-area` 位置不明确
2. Tabs 标签栏显示但功能不完整
3. 欢迎横幅位置不正确
4. 缺少 Footer 自定义内容

### 迁移步骤

1. 移除 Tabs 组件，使用简化的单一视图
2. 重构布局：Header → Chat → Footer → Composer
3. 自定义 Header 显示模型信息
4. 自定义 Footer 显示快捷键和状态
5. 将输入区域固定在底部
6. 简化欢迎横幅内容

## Success Criteria

- [ ] 界面布局从上到下为：Header → Chat → Footer → Composer
- [ ] Header 显示模型名称和上下文占用
- [ ] Footer 显示快捷键提示
- [ ] 输入框固定在底部
- [ ] 欢迎信息简洁明了
- [ ] 用户可以轻松上手使用