# Checklist - TUI Composer 增强

## 阶段一：多行 TextArea 替换 Input

- [x] Task 1.1: 修改 compose() 中的 yield 语句
- [x] Task 1.2: 更新导入语句
- [x] Task 1.3: 更新 CSS 样式以适应 TextArea

- [x] Task 2.1: 设置 placeholder 文本
- [x] Task 2.2: 配置 Tab 导航
- [x] Task 2.3: 设置初始焦点

## 阶段二：快捷键处理

- [x] Task 3.1: 添加 _on_text_area_key_down 处理器
- [x] Task 3.2: 检测 Enter 和 Ctrl+Enter
- [x] Task 3.3: 阻止 Enter 默认发送行为

- [x] Task 4.1: 检测上下箭头按键
- [x] Task 4.2: 阻止默认的移动行为

## 阶段三：命令历史

- [x] Task 5.1: 在 __init__ 中初始化历史列表
- [x] Task 5.2: 添加历史索引和临时输入变量

- [x] Task 6.1: 实现 _history_prev() 方法
- [x] Task 6.2: 实现 _history_next() 方法
- [x] Task 6.3: 实现 _submit_from_history() 方法

- [x] Task 7.1: 修改消息提交逻辑以支持历史
- [x] Task 7.2: 添加历史持久化（可选）

## 阶段四：其他快捷键

- [x] Task 8.1: Ctrl+A 跳转到行首
- [x] Task 8.2: Ctrl+E 跳转到行尾
- [x] Task 8.3: Ctrl+U 删除到行首
- [x] Task 8.4: Ctrl+W 删除上一个单词

## 最终验证

- [x] 运行 `python -m cli.main --textual`
- [x] 输入多行文本（包含换行）
- [x] 按 Enter 发送消息
- [x] 按上箭头查看历史
- [x] 按下箭头返回
- [x] 粘贴多行文本
- [x] 测试 Ctrl+Enter 插入换行