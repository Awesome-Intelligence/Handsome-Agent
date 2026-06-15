# Tasks - TUI Composer 增强

## 阶段一：多行 TextArea 替换 Input

- [ ] Task 1: 替换 Input 为 TextArea
  - [ ] 1.1: 修改 compose() 中的 yield 语句
  - [ ] 1.2: 更新导入语句（移除 Input，保留 TextArea）
  - [ ] 1.3: 更新 CSS 样式以适应 TextArea

- [ ] Task 2: 配置 TextArea 属性
  - [ ] 2.1: 设置 placeholder 文本
  - [ ] 2.2: 配置 Tab 导航
  - [ ] 2.3: 设置初始焦点

## 阶段二：快捷键处理

- [ ] Task 3: 实现 Enter/Ctrl+Enter 区分
  - [ ] 3.1: 添加 _on_text_area_key_down 处理器
  - [ ] 3.2: 检测 Enter 和 Ctrl+Enter
  - [ ] 3.3: 阻止 Enter 默认发送行为（改为 Ctrl+Enter 发送）

- [ ] Task 4: 实现方向键导航
  - [ ] 4.1: 检测上下箭头按键
  - [ ] 4.2: 阻止默认的移动行为

## 阶段三：命令历史

- [ ] Task 5: 添加历史状态管理
  - [ ] 5.1: 在 __init__ 中初始化历史列表
  - [ ] 5.2: 添加历史索引和临时输入变量

- [ ] Task 6: 实现历史导航方法
  - [ ] 6.1: 实现 _history_prev() 方法
  - [ ] 6.2: 实现 _history_next() 方法
  - ] 6.3: 实现 _submit_from_history() 方法

- [ ] Task 7: 历史提交集成
  - [ ] 7.1: 修改消息提交逻辑以支持历史
  - [ ] 7.2: 添加历史持久化（可选）

## 阶段四：其他快捷键

- [ ] Task 8: 实现编辑快捷键
  - [ ] 8.1: Ctrl+A 跳转到行首
  - [ ] 8.2: Ctrl+E 跳转到行尾
  - [ ] 8.3: Ctrl+U 删除到行首
  - [ ] 8.4: Ctrl+W 删除上一个单词

## Task Dependencies

- Task 2 依赖 Task 1
- Task 3、4 依赖 Task 1
- Task 5 可以在任何时候完成
- Task 6、7 依赖 Task 5
- Task 8 可以与 Task 3、4 并行

## 验证方式

- [ ] 手动测试多行输入
- [ ] 手动测试历史导航
- [ ] 手动测试 Ctrl+Enter 换行