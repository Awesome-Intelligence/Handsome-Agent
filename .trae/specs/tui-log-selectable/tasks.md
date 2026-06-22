# Tasks - TUI 日志面板改用 Log 组件

## Task 1: 修改 sidebar.py 日志组件

- [x] 1.1: 将 RichLog 导入改为 Log：`from textual.widgets import Log`
- [x] 1.2: LogsPane.compose() 中使用 Log 替代 RichLog
- [x] 1.3: 移除 RichLog 的 markup/wrap 参数，调整为 Log 兼容参数

## Task 2: 修改 log_handler.py 日志写入方法

- [x] 2.1: 将 `widget.write(msg)` 改为 `widget.write_line(msg)`
- [x] 2.2: 测试日志追加效果

## Task 3: 修改日志格式化函数

- [x] 3.1: 修改 format_log_entry() 移除 Rich 颜色标签
- [x] 3.2: 保留日志级别 emoji 图标

## Task Dependencies

- Task 2 依赖 Task 1
- Task 3 可与 Task 1 并行执行
