# 上下文传递修复任务列表

## 任务概述

将 Handsome Agent 的上下文传递机制从"文本块模式"改为"标准消息列表模式"，与 Hermes 保持一致，解决多轮对话中 Agent 无法记住之前说过什么的问题。

---

## 任务列表

- [x] Task 1: 改造 ContextBuilder，支持消息列表模式 ✅
  - [x] SubTask 1.1: 修改 `build_system_prompt()` 方法，新增 `build_messages()` 方法返回标准消息列表
  - [x] SubTask 1.2: 将历史对话从文本块格式改为消息列表格式
  - [x] SubTask 1.3: 保留原有 `build_system_prompt()` 方法（兼容简单模式）

- [x] Task 2: 改造 ContextManager，支持消息列表输出 ✅
  - [x] SubTask 2.1: 修改 `ContextManager.build()` 方法，新增 `build_messages()` 返回消息列表
  - [x] SubTask 2.2: 更新 `ContextPurpose` 枚举，添加新的构建模式

- [x] Task 3: 改造 ReActLoop，使用标准消息列表传递上下文 ✅
  - [x] SubTask 3.1: 修改 `ReActLoop._llm_decide()` 方法，使用消息列表格式传递历史
  - [x] SubTask 3.2: 将工具调用结果维护为消息列表中的 `tool` 角色消息
  - [x] SubTask 3.3: 更新 `ReActContext` 类，支持消息列表操作

- [x] Task 4: 改造 Agent 类，集成消息列表模式 ✅
  - [x] SubTask 4.1: 修改 `_chat_simple()` 方法，使用新的消息列表模式
  - [x] SubTask 4.2: 修改 `_chat_react()` 方法，传递完整的消息历史
  - [x] SubTask 4.3: 确保 `Session` 中的消息正确转换为消息列表格式

- [x] Task 5: 引入系统提示词缓存机制 ✅
  - [x] SubTask 5.1: 在 `Agent` 类中引入 `_cached_system_prompt` 缓存
  - [x] SubTask 5.2: 实现 `_restore_or_build_system_prompt()` 方法（参考 Hermes）
  - [x] SubTask 5.3: 在会话恢复时优先使用缓存的系统提示词

- [x] Task 6: 改造压缩输出格式 ✅
  - [x] SubTask 6.1: 修改 `ContextCompressor.compress()` 方法，确保输出为消息列表格式
  - [x] SubTask 6.2: 压缩后的摘要作为消息列表的一部分，而非文本块

- [x] Task 7: 编写验证测试 ✅
  - [x] SubTask 7.1: 编写单元测试验证消息列表格式正确
  - [x] SubTask 7.2: 编写集成测试验证多轮对话上下文传递

---

## 任务依赖关系

```
Task 1 (ContextBuilder) ─┬─> Task 2 (ContextManager) ─┬─> Task 3 (ReActLoop)
                        │                            │
                        └────> Task 4 (Agent) <──────┘
                                                        │
Task 5 (系统提示缓存) ────────────────────────────────┘
                                                        │
Task 6 (压缩格式) ─────────────────────────────────────┘
                                                        │
Task 7 (测试) ──────────────────────────────────────────┘
```

---

## 实现顺序

1. **Task 1** (ContextBuilder) - 核心基础，是其他任务的前提 ✅
2. **Task 2** (ContextManager) - 依赖 Task 1 ✅
3. **Task 3** (ReActLoop) - 依赖 Task 2 ✅
4. **Task 4** (Agent) - 依赖 Task 1, 2, 3 ✅
5. **Task 5** (系统提示缓存) - 独立，可并行 ✅
6. **Task 6** (压缩格式) - 依赖 Task 1, 2 ✅
7. **Task 7** (测试) - 最后执行，验证所有修改 ✅

---

## 修改的文件

| 文件 | 修改内容 |
|------|----------|
| `agent/context/context_builder.py` | 新增 `build_messages()` 方法 |
| `agent/context/context_manager.py` | 新增 `build_messages()` 方法和 `BuildMessagesResult` 数据类 |
| `agent/react/context.py` | 扩展 `Message` 类，新增 `add_tool_result()` 方法 |
| `agent/react/loop.py` | 修改 `_llm_decide()` 使用消息列表传递上下文 |
| `agent/agent.py` | 修改 LLM 调用使用消息列表模式，新增系统提示缓存机制 |
| `tests/unit/agent/test_context_builder.py` | 新增 `TestBuildMessages` 测试类 |
| `tests/integration/test_context_transfer.py` | 新增集成测试文件 |

---

*最后更新: 2026-06-12*