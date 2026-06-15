# Checklist - TUI Agent 集成

## 阶段一：基础集成

- [x] Task 1.1: 创建 _append_message 方法
- [x] Task 1.2: 使用 Rich 格式化显示消息
- [x] Task 1.3: 添加时间戳和角色标签

- [x] Task 2.1: 导入 Agent 类
- [x] Task 2.2: 修改 _submit_user_input 调用 Agent
- [x] Task 2.3: 处理 Agent 响应

## 阶段二：异步和流式输出

- [x] Task 3.1: 使用 call_later 避免阻塞 UI
- [x] Task 3.2: 显示加载状态
- [x] Task 3.3: 完成后恢复输入框焦点

- [x] Task 4.1: 检查 Agent 是否支持流式输出
- [x] Task 4.2: 实现流式更新消息内容
- [x] Task 4.3: 处理流式输出的完成

## 阶段三：错误处理

- [x] Task 5.1: 捕获异常并显示错误消息
- [x] Task 5.2: 移除加载状态
- [x] Task 5.3: 允许用户重试

## 阶段四：状态更新

- [x] Task 6.1: 显示/隐藏加载指示器
- [x] Task 6.2: 更新 Token 计数
- [x] Task 6.3: 更新上下文占用

## 最终验证

- [x] 用户输入后显示在聊天区域
- [x] Agent 处理用户输入
- [x] Agent 回复显示在聊天区域
- [x] 显示加载/思考状态
- [x] 错误时显示友好的错误消息
- [x] 运行 `python -m cli.main --textual` 并进行对话测试