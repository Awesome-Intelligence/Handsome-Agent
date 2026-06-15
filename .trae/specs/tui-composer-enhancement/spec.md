# TUI Composer 增强规范

## Why

当前 TUI 的输入框只是一个简单的单行 Input 组件，无法满足复杂对话场景的需求。用户需要：
- 输入多行文本（代码、段落等）
- 访问之前的命令历史
- 正常粘贴多行内容

## What Changes

### 核心功能

1. **多行编辑** - 使用 TextArea 替代 Input，支持多行文本输入
   - Enter 发送消息
   - Ctrl+Enter 或 Alt+Enter 插入换行
   - 方向键在文本内移动
   - Home/End 跳转到行首/行尾

2. **命令历史** - 支持浏览之前的输入
   - 上箭头 ↑ 查看上一条历史
   - 下箭头 ↓ 查看下一条历史
   - 自动补全历史记录

3. **粘贴支持** - 正常处理剪贴板粘贴
   - 支持多行粘贴
   - 支持大段文本粘贴

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Composer Widget                          │
├─────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────┐  │
│  │ TextArea (多行输入)                                    │  │
│  │ - 占位符: "输入消息，Ctrl+Enter 换行..."              │  │
│  │ - 自动聚焦                                             │  │
│  │ - 支持 Tab 导航                                        │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────┐ ┌─────────────┐   │
│  │ [发送]                              │ │ 提示文字    │   │
│  └─────────────────────────────────────┘ └─────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 快捷键

| 快捷键 | 功能 |
|--------|------|
| Enter | 发送消息 |
| Ctrl+Enter / Alt+Enter | 插入换行 |
| ↑ | 上一条历史 |
| ↓ | 下一条历史 |
| Ctrl+P / Ctrl+N | 历史导航（替代方案） |
| Ctrl+A / Home | 行首 |
| Ctrl+E / End | 行尾 |
| Ctrl+U | 删除到行首 |
| Ctrl+W | 删除上一个单词 |
| Ctrl+V | 粘贴 |
| Esc | 取消输入 |

## Impact

- Affected specs: TUI 交互体验
- Affected code: `cli/tui/textual_app.py`

## ADDED Requirements

### Requirement: 多行文本输入

系统 SHALL 支持在输入框中输入多行文本。

#### Scenario: 基本输入
- **WHEN** 用户在 TextArea 中输入文本
- **THEN** 文本正常显示，支持多行

#### Scenario: 插入换行
- **WHEN** 用户按下 Ctrl+Enter 或 Alt+Enter
- **THEN** 在光标位置插入换行符

#### Scenario: 发送消息
- **WHEN** 用户按下 Enter（无修饰键）
- **THEN** 发送消息，清空输入框

### Requirement: 命令历史

系统 SHALL 支持浏览之前的输入历史。

#### Scenario: 查看历史
- **WHEN** 用户按上箭头 ↑ 
- **THEN** 显示上一条历史记录

#### Scenario: 继续导航
- **WHEN** 用户连续按上箭头
- **THEN** 继续显示更早的历史

#### Scenario: 回到最新
- **WHEN** 用户按完上箭头后按下箭头 ↓
- **THEN** 恢复到较新的历史或空输入

### Requirement: 剪贴板粘贴

系统 SHALL 正常处理剪贴板粘贴。

#### Scenario: 粘贴多行文本
- **WHEN** 用户粘贴多行文本
- **THEN** 文本正确插入，包含换行符

## Technical Implementation

### 状态管理

```python
class HandsomeAgentApp(App):
    def __init__(self, ...):
        # 历史记录
        self._input_history: list[str] = []
        self._history_index: int = -1  # -1 表示当前输入
        self._current_input: str = ""   # 临时保存当前输入
```

### 快捷键处理

```python
def _on_text_area_key_down(self, event: TextArea.KeyDown) -> None:
    """处理 TextArea 按键事件."""
    if event.key == "enter":
        if event.modifiers & (KeyModifier.CTRL | KeyModifier.ALT):
            # 插入换行
            return  # 不阻止默认行为
        else:
            # 发送消息
            self._submit_from_history()
            event.prevent_default()
    elif event.key == "up":
        self._history_prev()
        event.prevent_default()
    elif event.key == "down":
        self._history_next()
        event.prevent_default()
```

### 历史导航

```python
def _history_prev(self) -> None:
    """显示上一条历史."""
    text_area = self.query_one("#user-input", TextArea)
    
    if not self._input_history:
        return
    
    # 保存当前输入
    if self._history_index == -1:
        self._current_input = text_area.text
    
    # 移动到上一条
    if self._history_index < len(self._input_history) - 1:
        self._history_index += 1
        text_area.text = self._input_history[self._history_index]

def _history_next(self) -> None:
    """显示下一条历史."""
    text_area = self.query_one("#user-input", TextArea)
    
    if self._history_index == -1:
        return
    
    # 移动到下一条
    if self._history_index > 0:
        self._history_index -= 1
        text_area.text = self._input_history[self._history_index]
    else:
        # 恢复到原始输入
        self._history_index = -1
        text_area.text = self._current_input

def _submit_from_history(self) -> None:
    """从历史模式提交消息."""
    text_area = self.query_one("#user-input", TextArea)
    user_input = text_area.text.strip()
    
    if user_input:
        # 添加到历史
        self._input_history.insert(0, user_input)
    
    # 重置历史索引
    self._history_index = -1
    self._current_input = ""
    
    # 调用原来的提交逻辑
    self._do_submit(user_input)
```

## Success Criteria

- [ ] 支持多行文本输入
- [ ] Enter 发送，Ctrl+Enter 换行
- [ ] 上下箭头浏览历史
- [ ] 粘贴多行文本正常
- [ ] 所有快捷键正常工作