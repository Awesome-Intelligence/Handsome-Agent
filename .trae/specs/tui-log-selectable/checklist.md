# Checklist - TUI 日志面板改用 Log 组件

## sidebar.py 修改

- [x] 1.1: RichLog 导入已改为 Log
- [x] 1.2: LogsPane 使用 Log 组件
- [x] 1.3: Log 参数正确（auto_scroll, max_lines, highlight）

## log_handler.py 修改

- [x] 2.1: write() 已改为 write_line()
- [x] 2.2: 日志能正确追加显示

## 日志格式化修改

- [x] 3.1: format_log_entry() 移除颜色标签
- [x] 3.2: 日志级别 emoji 正确显示

## 功能验证

- [ ] 日志面板支持鼠标选择文本（需运行时验证）
- [ ] 日志能正常追加显示（需运行时验证）
- [ ] 滚动功能正常（需运行时验证）
