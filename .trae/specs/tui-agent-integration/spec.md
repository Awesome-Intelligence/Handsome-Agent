# TUI Agent 集成规范

## Why

当前 Textual TUI 界面已可以正常显示，但用户输入的消息只是简单地显示在聊天区域，没有发送给真正的 Agent 进行处理。需要将 UI 与 Agent 核心逻辑集成，实现真正的对话功能。

## What Changes

### 核心问题

1. **消息未发送给 Agent** - 用户输入只显示在界面上，没有触发 Agent 处理
2. **缺少异步处理** - Agent 调用是异步的，需要处理流式输出
3. **缺少回复显示** - Agent 的回复没有显示在聊天区域
4. **缺少加载状态** - Agent 处理时没有显示加载/思考状态

### 设计目标

将 Textual TUI 与 Handsome Agent 的核心逻辑集成：
- 用户输入 → Agent 处理 → 回复显示
- 支持流式输出
- 显示加载/思考状态
- 错误处理和反馈

## Architecture

### 集成架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    HandsomeAgentApp                              │
├─────────────────────────────────────────────────────────────────┤
│  UI Layer (Textual)                                             │
│  ├── 输入区域 (TextArea)                                        │
│  ├── 聊天区域 (RichLog)                                         │
│  ├── 状态栏 (Footer)                                           │
│  └── 发送按钮 (Button)                                          │
├─────────────────────────────────────────────────────────────────┤
│  Integration Layer                                              │
│  ├── _submit_user_input()     - 提交用户输入                    │
│  ├── _process_agent_response() - 处理 Agent 响应               │
│  └── _append_message()        - 追加消息到聊天                  │
├─────────────────────────────────────────────────────────────────┤
│  Agent Layer                                                    │
│  └── Agent 类 (agent/agent.py)                                  │
│      └── process_message() - 处理用户消息                       │
└─────────────────────────────────────────────────────────────────┘
```

### 消息流程

1. 用户在 TextArea 输入消息，按 Enter 或点击发送
2. `_submit_user_input()` 被调用
3. 显示用户消息在聊天区域
4. 调用 Agent.process_message()（异步）
5. 流式显示 Agent 的思考过程（可选）
6. 流式显示 Agent 的回复
7. 更新状态栏的 Token 统计

## Impact

- Affected specs: TUI交互体验、Agent核心逻辑
- Affected code: `cli/tui/textual_app.py`, `agent/agent.py`

## ADDED Requirements

### Requirement: 用户输入提交

系统 SHALL 将用户输入发送给 Agent 进行处理。

#### Scenario: 发送消息
- **WHEN** 用户在 TextArea 输入消息并按 Enter 或点击发送
- **THEN** 消息显示在聊天区域，Agent 开始处理

#### Scenario: 空输入处理
- **WHEN** 用户输入为空或只有空白字符
- **THEN** 不发送消息，输入框保持不变

### Requirement: Agent 响应显示

系统 SHALL 实时显示 Agent 的回复。

#### Scenario: 正常回复
- **WHEN** Agent 返回回复
- **THEN** 回复逐字显示在聊天区域

#### Scenario: 流式输出
- **WHEN** Agent 返回长回复
- **THEN** 回复流式显示，用户可以看到实时输出

#### Scenario: 思考过程（可选）
- **WHEN** 用户启用思考显示
- **THEN** Agent 的思考过程单独显示

### Requirement: 加载状态

系统 SHALL 在 Agent 处理时显示加载状态。

#### Scenario: 显示思考状态
- **WHEN** Agent 正在处理
- **THEN** 在聊天区域显示 "正在思考..." 或类似状态

#### Scenario: 状态栏更新
- **WHEN** Agent 开始/结束处理
- **THEN** 状态栏更新显示处理状态

### Requirement: 错误处理

系统 SHALL 优雅处理 Agent 调用中的错误。

#### Scenario: 网络错误
- **WHEN** Agent 调用失败（网络错误）
- **THEN** 显示友好的错误消息，用户可以重试

#### Scenario: API 错误
- **WHEN** Agent 调用失败（API 错误）
- **THEN** 显示错误详情，帮助用户排查问题

## Technical Implementation

### 核心代码结构

```python
async def _submit_user_input(self) -> None:
    """提交用户输入并处理 Agent 响应."""
    text_area = self.query_one("#user-input", TextArea)
    user_input = text_area.text.strip()
    
    if not user_input:
        return
    
    # 清空输入框
    text_area.text = ""
    
    # 添加用户消息
    self._append_message("user", user_input)
    
    # 显示加载状态
    thinking_msg = self._append_message("system", "正在思考...")
    
    try:
        # 异步调用 Agent
        async for chunk in agent.process_message_streaming(user_input):
            # 流式更新回复
            self._update_message(thinking_msg, chunk)
        
        # 移除加载状态
        self._finalize_message(thinking_msg)
        
    except Exception as e:
        # 显示错误
        self._update_message(thinking_msg, f"❌ 错误: {e}")
```

### 消息对象结构

```python
@dataclass
class ChatMessage:
    """聊天消息."""
    role: str          # "user" | "assistant" | "system"
    content: str      # 消息内容
    timestamp: datetime
    is_streaming: bool = False
```

## MODIFIED Requirements

### Requirement: 聊天区域显示

修改聊天区域以支持流式消息更新。

#### Scenario: 流式消息
- **WHEN** 消息正在流式传输
- **THEN** 消息内容实时更新

## Success Criteria

- [ ] 用户输入后显示在聊天区域
- [ ] Agent 处理用户输入
- [ ] Agent 回复显示在聊天区域
- [ ] 显示加载/思考状态
- [ ] 错误时显示友好的错误消息