# TUI 视觉美化增强规范

## Why

当前 Handsome Agent 的 TUI 界面"感觉有点不好看"，需要通过视觉美化提升用户体验。包括：消息样式优化、交互反馈增强、动画效果添加等。

## What Changes

### 视觉问题清单

1. **消息使用 Panel 边框太重** - 视觉上拥挤，需要改为轻量级 Markdown 渲染
2. **Tab 按钮缺少视觉指示** - 没有底部高亮指示器，激活状态不明确
3. **流式输出缺少动画** - 用户不知道消息正在生成
4. **Header 缺少状态指示** - 没有在线状态/忙碌状态视觉反馈
5. **快捷键提示文字拥挤** - 没有分组显示，不易阅读

### 设计目标

参考 CodeWhale 风格，实现：
- 消息使用 Markdown 样式而非厚重 Panel
- Tab 按钮有底部高亮指示器
- 流式输出有打字动画效果
- Header 有状态指示器（绿色=在线/忙碌）
- 快捷键分组显示，使用小方框样式

## Impact

- Affected specs: TUI 视觉体验
- Affected code: `cli/tui/textual_app.py`, `cli/tui/widgets/`

## ADDED Requirements

### Requirement: 消息 Markdown 渲染

系统 SHALL 使用 Markdown 样式替代 Panel 边框显示消息。

#### Scenario: 用户消息渲染
- **WHEN** 显示用户消息时
- **THEN** 使用 `**You**` 粗体 + 蓝色 `#58a6ff`，下方显示消息内容

#### Scenario: 助手消息渲染
- **WHEN** 显示助手消息时
- **THEN** 使用 `**Assistant**` 粗体 + 绿色 `#3fb950`，下方显示消息内容

#### Scenario: 工具消息渲染
- **WHEN** 显示工具执行消息时
- **THEN** 使用缩进 + 图标 `🛠️`，显示工具名称和结果

### Requirement: Tab 按钮底部高亮指示器

系统 SHALL 在激活的 Tab 按钮底部显示高亮指示器。

#### Scenario: Tab 激活状态
- **WHEN** 用户切换到某个 Tab
- **THEN** 该 Tab 按钮底部显示 2px 蓝色 `#58a6ff` 线条

#### Scenario: Tab 默认状态
- **WHEN** Tab 未激活时
- **THEN** 底部线条为透明或与背景同色

### Requirement: 流式输出动画

系统 SHALL 在流式输出时显示打字机/闪烁动画。

#### Scenario: 流式指示器
- **WHEN** 消息正在流式输出时
- **THEN** 在消息末尾显示闪烁的 `▌` 光标

#### Scenario: 思考内容动画
- **WHEN** 助手正在思考时
- **THEN** 显示 `💭 思考中...` 并带有旋转/闪烁动画

### Requirement: Header 状态指示器

系统 SHALL 在 Header 显示在线/忙碌状态指示。

#### Scenario: 空闲状态
- **WHEN** Agent 空闲时
- **THEN** Header 显示绿色圆点 `🟢`

#### Scenario: 处理中状态
- **WHEN** Agent 正在处理请求时
- **THEN** Header 显示橙色圆点 `🟡` + "处理中..."

#### Scenario: 错误状态
- **WHEN** 发生错误时
- **THEN** Header 显示红色圆点 `🔴` + 错误摘要

### Requirement: 快捷键分组显示

系统 SHALL 在 Footer 分组显示快捷键，使用小方框样式。

#### Scenario: 快捷键分组
- **WHEN** Footer 渲染快捷键提示时
- **THEN** 快捷键使用 `[Ctrl+K]` 样式，方框背景为 `#30363d`

#### Scenario: 快捷键分组
- **THEN** 不同分组的快捷键使用 `|` 分隔

## Technical Implementation

### 1. 消息 Markdown 渲染

```python
def _append_message(self, role: str, content: str) -> None:
    log = self.query_one("#chat-log", RichLog)

    if role == "user":
        # 用户消息：蓝色粗体标题 + 消息内容
        formatted = f"[bold #58a6ff]**You**[/]\n\n{content}"
    elif role == "assistant":
        # 助手消息：绿色粗体标题 + 消息内容
        formatted = f"[bold #3fb950]**Assistant**[/]\n\n{content}"
    else:
        # 其他消息：灰色标题 + 消息内容
        formatted = f"[dim]**System**[/]\n\n{content}"

    log.write(formatted)
```

### 2. Tab 按钮高亮指示器

```css
.sidebar-tab.active {
    background: #30363d;
    color: #c9d1d9;
    border-bottom: solid #58a6ff 2px;  /* 底部高亮 */
}
```

### 3. 流式输出动画

```css
.streaming-indicator {
    color: #8b949e;
    animation: blink 1s infinite;
}

@keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
}

/* 思考内容动画 */
.thinking-indicator {
    color: #f0883e;
    animation: spin 2s linear infinite;
}

@keyframes spin {
    0% { content: "💭"; }
    25% { content: "💭"; }
    50% { content: "💭"; }
    75% { content: "💭"; }
    100% { content: "💭"; }
}
```

### 4. Header 状态指示器

```python
# 状态指示器颜色
STATUS_ONLINE = "#3fb950"    # 绿色 - 空闲
STATUS_BUSY = "#f0883e"      # 橙色 - 处理中
STATUS_ERROR = "#f85149"      # 红色 - 错误
```

### 5. 快捷键分组样式

```css
.footer-key {
    color: #c9d1d9;
    background: #30363d;
    padding: 0 2;
    border-radius: 3;
}

.footer-group-separator {
    color: #6e7681;
    margin: 0 2;
}
```

## Success Criteria

- [ ] 消息使用 Markdown 样式显示，不再使用厚重 Panel
- [ ] Tab 按钮有底部高亮指示器
- [ ] 流式输出有闪烁动画
- [ ] Header 显示在线/忙碌状态指示
- [ ] Footer 快捷键使用分组样式
- [ ] 整体视觉风格与 CodeWhale 接近