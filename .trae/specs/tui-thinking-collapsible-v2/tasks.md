# TUI 思考内容可折叠 - 方案A - 实施计划

## [x] Task 1: 修改系统提示词，添加 `<think>` 标签指令
- **Priority**: P0
- **Depends On**: None
- **Description**: 
  - 在 `prompt_templates.py` 的 `TOOL_CALL_FORMAT` 中添加指令，要求 LLM 使用 `<think>` 标签包裹思考内容
  - 修改 `direct_response` 的格式要求，将 `reasoning` 字段改为 `<think>` 标签格式
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `programmatic` TR-1.1: 验证 `prompt_templates.py` 中包含 `<think>` 标签指令
  - `human-judgment` TR-1.2: 检查指令是否清晰明确，LLM 能够理解
- **Notes**: 需要确保 JSON 格式仍然有效，`<think>` 标签应该放在 JSON 外部或作为 JSON 字符串的一部分

## [x] Task 2: 修改 Agent 代码，正确处理 `<think>` 标签格式
- **Priority**: P0
- **Depends On**: Task 1
- **Description**: 
  - 修改 `agent/agent.py` 中的 `_generate_direct_response_stream` 方法
  - 确保 `StreamingThinkScrubber` 能够正确分离 `<think>` 标签内容
  - 将分离出的思考内容通过回调传递给 TUI
- **Acceptance Criteria Addressed**: AC-2
- **Test Requirements**:
  - `programmatic` TR-2.1: 验证 `StreamingThinkScrubber` 能够正确分离思考内容
  - `programmatic` TR-2.2: 验证思考内容回调能够正确触发
- **Notes**: 需要确保流式输出时思考内容能够实时分离和传递

## [x] Task 3: 验证 TUI 的 Collapsible 渲染逻辑
- **Priority**: P1
- **Depends On**: Task 2
- **Description**: 
  - 验证 `tui/widgets/message_list.py` 中的 `_render_message_with_thinking` 方法
  - 确保思考内容能够正确渲染为 Collapsible 子框
  - 确保默认收起状态正确
- **Acceptance Criteria Addressed**: AC-3, AC-4
- **Test Requirements**:
  - `human-judgment` TR-3.1: 检查思考内容是否以 Collapsible 子框形式显示
  - `human-judgment` TR-3.2: 检查默认状态是否为收起
- **Notes**: 之前的实现可能已经完成了这部分，需要验证是否正确工作

## [x] Task 4: 验证展开/收起功能和键盘快捷键
- **Priority**: P1
- **Depends On**: Task 3
- **Description**: 
  - 验证点击 Collapsible 标题能够展开/收起思考内容
  - 验证 `e` 键能够展开所有思考内容
  - 验证 `c` 键能够收起所有思考内容
- **Acceptance Criteria Addressed**: AC-5, AC-6
- **Test Requirements**:
  - `human-judgment` TR-4.1: 检查点击标题是否能够展开/收起
  - `human-judgment` TR-4.2: 检查 `e` 键是否能够展开所有
  - `human-judgment` TR-4.3: 检查 `c` 键是否能够收起所有
- **Notes**: 之前的实现可能已经完成了这部分，需要验证是否正确工作

## [x] Task 5: 端到端测试验证
- **Priority**: P1
- **Depends On**: Task 1-4
- **Description**: 
  - 运行完整的 TUI 应用，发送测试消息
  - 验证思考内容正确分离并以 Collapsible 子框形式显示
  - 验证展开/收起功能和键盘快捷键正常工作
- **Acceptance Criteria Addressed**: AC-1-AC-6
- **Test Requirements**:
  - `human-judgment` TR-5.1: 端到端验证所有功能
- **Notes**: 需要确保整个流程能够正常工作

# Task Dependencies
- Task 2 依赖 Task 1
- Task 3 依赖 Task 2
- Task 4 依赖 Task 3
- Task 5 依赖 Task 1-4
