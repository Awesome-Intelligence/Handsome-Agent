# TUI 日志面板改用 Log 组件规范

## Why

当前日志面板使用 `RichLog` 组件，不支持鼠标选择和复制文本。用户希望能够选中并复制日志内容，需要切换到 Textual 原生的 `Log` 组件。

## What Changes

1. **[tui/sidebar.py](file:///e:/Awesome Intelligence/Handsome-Agent/tui/sidebar.py#L17)** - 导入 `Log` 替代 `RichLog`
2. **[tui/sidebar.py](file:///e:/Awesome Intelligence/Handsome-Agent/tui/sidebar.py#L389)** - `LogsPane` 使用 `Log` 组件
3. **[tui/textual_app/log_handler.py](file:///e:/Awesome Intelligence/Handsome-Agent/tui/textual_app/log_handler.py#L103)** - `write()` 改为 `write_line()`

### 日志格式化调整

- `format_log_entry()` 函数移除 Rich 颜色标签，改为纯文本输出
- 保留日志级别图标（emoji）

## Impact

- Affected specs: TUI 侧边栏日志面板
- Affected code:
  - `tui/sidebar.py` - LogsPane 组件
  - `tui/textual_app/log_handler.py` - 日志写入方法

## MODIFIED Requirements

### Requirement: 日志面板文本选择

**变更**: 系统 SHALL 支持鼠标选择和复制日志文本。

#### Scenario: 文本选择
- **WHEN** 用户在日志面板中用鼠标拖选文本
- **THEN** 选中文本高亮显示，可通过 Ctrl+C 复制

### Requirement: 日志格式化

**变更**: 日志消息显示为纯文本，保留 emoji 图标但移除颜色标签。

#### Scenario: 日志显示
- **WHEN** 后端产生日志消息
- **THEN** 日志以纯文本格式显示（带级别图标）

## Breaking Changes

- 日志面板不再显示 Rich 格式颜色（纯文本替代）
