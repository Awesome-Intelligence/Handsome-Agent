# 上下文传递问题分析报告

## 问题概述

用户反馈多轮对话中 Agent 无法记住之前说过什么。经过深入分析，发现问题**不在于压缩机制**，而在于**上下文的拼装方式**和**消息历史的管理机制**。

---

## 一、根本原因分析

### 问题1：消息历史没有作为真正的消息列表传递

**现象位置**：[context_builder.py:184-191](file:///e:/Awesome%20Intelligence/Handsome-Agent/agent/context/context_builder.py#L184-L191)

```python
# 只取最近6条消息，每条截取200字符
recent = conversation_history[-6:]
history_context = "\n\nRecent conversation:\n"
for msg in recent:
    role = msg.get('role', 'unknown')
    content = msg.get('content', '')[:200]
    history_context += f"- {role}: {content}\n"
```

**问题**：
- 历史被拼装成一段**文本块**，放在系统提示词末尾
- **不是**标准的消息列表格式 `[{"role": "user", ...}, {"role": "assistant", ...}]`
- LLM 无法正确理解这是对话历史，只能当作普通文本参考

**对比 Hermes**：
```python
# Hermes conversation_loop.py 使用标准消息列表格式
# 直接传递 conversation_history 作为真正的消息列表
response = call_llm(messages=[{"role": "system", ...}, ...conversation_history...])
```

### 问题2：工具调用结果没有维护为消息历史

**现象位置**：[agent.py:585-595](file:///e:/Awesome%20Intelligence/Handsome-Agent/agent/agent.py#L585-L595)

```python
self._trajectory_recorder.add_tool_call(
    tool_name=tool_name,
    arguments=result.get('parameters', {}),
    reasoning=result.get('reasoning', '')
)
self._trajectory_recorder.add_tool_response(
    tool_name=tool_name,
    content=tool_result
)
```

**问题**：
- 工具调用记录在 `TrajectoryRecorder` 中
- 但这些记录**没有**作为对话历史传递给后续 LLM 调用
- `ReActLoop` 中的 `tool_calls` 只是 `StepResult` 列表

**对比 Hermes**：
```python
# Hermes 使用标准工具调用格式
messages.append({"role": "assistant", "tool_calls": [...], "content": ""})
messages.append({"role": "tool", "tool_call_id": "...", "content": "..."})
```

### 问题3：系统提示词没有缓存机制

**现象位置**：[context_builder.py:79-84](file:///e:/Awesome%20Intelligence/Handsome-Agent/agent/context/context_builder.py#L79-L84)

```python
self._system_prompt_builder = SystemPromptBuilder(
    tools=self.tools,
    enable_guidance=enable_guidance,
    enable_memory_prefetch=enable_memory_prefetch,
    session_id=session_id
)
```

**问题**：
- 每次调用都重新构建系统提示词
- 没有类似 Hermes 的 `agent._cached_system_prompt` 缓存机制

**对比 Hermes**：
```python
# Hermes system_prompt.py
def _restore_or_build_system_prompt(agent, system_message, conversation_history):
    if stored_prompt:
        # 复用缓存的系统提示词
        agent._cached_system_prompt = stored_prompt
        return
    # 首次构建并缓存
    agent._cached_system_prompt = agent._build_system_prompt(system_message)
```

### 问题4：压缩机制只影响系统提示词

**现象位置**：[context_manager.py:155-180](file:///e:/Awesome%20Intelligence/Handsome-Agent/agent/context/context_manager.py#L155-L180)

```python
# 压缩后的历史只用于构建系统提示词
if should_compress and self._context_compressor:
    result = await self._context_compressor.compress(
        conversation_history,
        max_messages=self._compression_threshold
    )
    processed_history = result.compressed_messages
```

**问题**：
- 压缩后的历史仍然是文本块格式
- 不是真正的消息列表，无法传递工具调用上下文

---

## 二、与 Hermes 的差距

| 功能 | Hermes | Handsome Agent | 差距 |
|------|--------|-----------------|------|
| 消息历史格式 | 标准消息列表 `[{"role": "user", ...}]` | 文本块 `"## Recent Conversation:\n- user: ..."` | ⚠️ 严重 |
| 工具调用上下文 | `tool_calls` + `tool` 消息对 | `TrajectoryRecorder` 独立记录 | ⚠️ 严重 |
| 系统提示缓存 | `agent._cached_system_prompt` 会话级缓存 | 每次重新构建 | ⚠️ 中等 |
| 压缩输出格式 | 压缩后的消息列表 | 压缩后的文本块 | ⚠️ 严重 |
| 消息传递方式 | `messages=[...]` 参数传递 | `system_prompt` + `user_message` 分离 | ⚠️ 严重 |

---

## 三、问题影响链

```
1. 用户输入 → 2. Agent 处理 → 3. 工具调用
                                      ↓
4. 结果记录在 TrajectoryRecorder（独立存储）
                                      ↓
5. 下一轮对话 → 6. ContextBuilder 构建系统提示
                                      ↓
7. 历史作为文本块传入（丢失工具调用关联）
                                      ↓
8. LLM 无法理解之前的工具执行结果
                                      ↓
9. "Agent 不记得之前说过什么"
```

---

## 四、核心修复方向

### 方向1：消息列表化改造

将历史从文本块改为真正的消息列表：
```python
# 修复前
system_prompt = "## Recent Conversation:\n- user: xxx\n- assistant: yyy"

# 修复后
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_input}
]
```

### 方向2：工具调用消息化

将工具调用结果维护为消息列表中的 `tool` 角色消息：
```python
messages.append({"role": "assistant", "tool_calls": [...], "content": ""})
messages.append({"role": "tool", "tool_call_id": "...", "content": tool_result})
```

### 方向3：系统提示缓存

引入会话级系统提示缓存机制。

### 方向4：压缩输出消息列表化

压缩输出应该是消息列表格式，不是文本块。

---

## 五、验证方法

1. 检查 `context_builder.build_system_prompt()` 返回的内容
2. 检查 `ReActLoop._llm_decide()` 中的消息传递方式
3. 检查工具调用结果是否作为消息列表的一部分传递

---

*本分析基于 v1.0.0 版本代码*