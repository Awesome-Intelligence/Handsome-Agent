# 📊 Context Module - 上下文管理

> 🧠 Decision Layer - 💾 Context 子层
>
> 包含上下文拼装 (Assembly) 和上下文压缩 (Compression)

---

## 概述

上下文管理是 Agent-Z 的核心功能之一，负责：

1. **上下文拼装 (Assembly)** - LLM 调用前准备输入
2. **上下文压缩 (Compression)** - 长对话时管理 token 预算

---

## Part 1: 上下文拼装 (Context Assembly)

### 什么是上下文拼装

上下文拼装是 Agent 每次 LLM 调用前准备输入的过程。它将各种来源的信息组装成完整的提示词，使 LLM 能够理解当前状态并做出正确决策。

### 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│              Agent-Z 上下文管理架构                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  ContextBuilder (💾 Context 子层)                    │    │
│  │  ├── AgentDefinitionLoader  # 加载 Agent 定义        │    │
│  │  ├── build_system_prompt()  # 构建系统提示词        │    │
│  │  └── _build_guidance()     # 5 类指导性文本         │    │
│  └─────────────────────────────────────────────────────┘    │
│                          ↓                                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  LLMToolSelector (🔧 ToolSelect 子层)                │    │
│  │  ├── register_tool()        # 工具注册              │    │
│  │  ├── select_tool()         # 工具选择              │    │
│  │  └── execute()             # 工具执行              │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 涉及的模块

| 模块 | 位置 | 职责 | 子层 |
|------|------|------|------|
| `ContextBuilder` | `agent/context/context_builder.py` | 上下文构建器 | 💾 Context |
| `AgentDefinitionLoader` | `agent/context/context_builder.py` | 加载 Agent 定义文件 | 💾 Context |
| `LLMToolSelector` | `agent/tool_selector/llm_tool_selector.py` | 工具选择器 | 🔧 ToolSelect |

### 当前上下文组成

```
┌─────────────────────────────────────────────────────────────┐
│                    LLM Request Messages                    │
├─────────────────────────────────────────────────────────────┤
│  [system] identity_summary          # 身份定义摘要          │
│  [system] capabilities_summary      # 能力摘要             │
│  [system] user_summary              # 用户信息摘要         │
│  [system] guidance                  # 指导性文本 (5 类)     │
│  [system] tools_schema              # 工具列表 (JSON)      │
│  [system] tool_usage_instruction    # 工具使用说明         │
│  [system] recent_conversation       # 最近6条对话          │
│  [user]   user_input               # 用户输入 (动态添加)   │
└─────────────────────────────────────────────────────────────┘
```

### 指导性文本 (Guidance)

| 指导 | 内容 | 状态 |
|------|------|------|
| **Memory Usage** | 记忆保存规范、写作指南 | ✅ 已实现 |
| **Session Search** | 跨会话搜索指导 | ✅ 已实现 |
| **Skills** | 技能保存和维护指导 | ✅ 已实现 |
| **Tool-Use Enforcement** | 工具使用纪律、执行规则 | ✅ 已实现 |
| **Act Without Asking** | 主动行动原则 | ✅ 已实现 |

---

## Hermes 对比 - 上下文拼装

### Hermes 的系统提示词架构（参考）

Hermes 使用三层架构组织系统提示词：

```
┌─────────────────────────────────────────────────────────────┐
│                 Hermes System Prompt                       │
├─────────────────────────────────────────────────────────────┤
│  stable (稳定层)                                          │
│  ├── identity (SOUL.md 或默认)                             │
│  ├── hermes_agent_help_guidance                           │
│  ├── memory_guidance                                      │
│  ├── session_search_guidance                              │
│  ├── skills_guidance                                     │
│  ├── kanban_guidance                                     │
│  ├── tool_use_enforcement                                │
│  ├── model-specific guidance (GPT/Gemini)                │
│  └── platform_hints                                      │
├─────────────────────────────────────────────────────────────┤
│  context (上下文层)                                        │
│  ├── caller-supplied system_message                      │
│  └── context files (.hermes.md, AGENTS.md)                │
├─────────────────────────────────────────────────────────────┤
│  volatile (可变层)                                        │
│  ├── memory snapshot                                     │
│  ├── user profile                                        │
│  └── timestamp/session info                             │
└─────────────────────────────────────────────────────────────┘
```

### Hermes 独特功能

#### 1. Prompt 注入检测

```python
# prompt_builder.py 中的危险模式检测
_CONTEXT_THREAT_PATTERNS = [
    r'ignore\s+(previous|all|above|prior)\s+instructions',
    r'do\s+not\s+tell\s+the\s+user',
    r'system\s+prompt\s+override',
    r'<\s*div\s*style\s*=\s*["\'][\s\S]*?display\s*:\s*none',
    ...
]
```

#### 2. 上下文文件扫描

- 扫描 `.hermes.md`, `HERMES.md` 等上下文文件
- 检测隐藏的 HTML 注入
- 检测不可见的 Unicode 字符

#### 3. 模型特定指导

- **GPT/Codex**: OPENAI_MODEL_EXECUTION_GUIDANCE
- **Gemini/Gemma**: GOOGLE_MODEL_OPERATIONAL_GUIDANCE
- **Alibaba**: 模型名 workaround

#### 4. Kanban 任务指导

完整的看板任务生命周期管理指导（仅在看板模式下注入）

### 拼装差距对比

| 方面 | Agent-Z | Hermes | 状态 |
|------|----------------|--------|------|
| **身份定义** | ✅ 已实现 | ✅ 已有 | 完成 |
| **能力摘要** | ✅ 已实现 | ✅ 已有 | 完成 |
| **用户信息** | ✅ 已实现 | ✅ 已有 | 完成 |
| **工具列表** | ✅ 已实现 | ✅ 已有 | 完成 |
| **对话历史** | ✅ 最近6条 | ✅ 完整历史 | 完成 |
| **记忆指导** | ✅ 已实现 | ✅ 已有 | 完成 |
| **搜索指导** | ✅ 已实现 | ✅ 已有 | 完成 |
| **技能指导** | ✅ 已实现 | ✅ 已有 | 完成 |
| **平台提示** | ⚠️ 基础版 | ✅ 完善 | 待增强 |
| **安全扫描** | ❌ 未实现 | ✅ 已有 | 待实现 |
| **上下文文件** | ❌ 未实现 | ✅ 已有 | 待实现 |
| **模型特定指导** | ❌ 未实现 | ✅ 已有 | 待实现 |
| **Kanban 指导** | ❌ 未实现 | ✅ 特有 | 视情况 |
| **三层架构** | ⚠️ 简化版 | ✅ 完整 | 待增强 |

### 改进计划

#### ✅ Phase 1: 指导性文本 (已完成)

- [x] 添加 `MEMORY_GUIDANCE` - 记忆使用规范
- [x] 添加 `SESSION_SEARCH_GUIDANCE` - 跨会话搜索指导
- [x] 添加 `SKILLS_GUIDANCE` - 技能保存指导
- [x] 添加 `TOOL_USE_ENFORCEMENT` - 工具使用纪律
- [x] 添加 `ACT_WITHOUT_ASKING` - 主动行动原则

#### 🟡 Phase 2: 安全增强 (中优先级)

- [ ] 实现 Prompt 注入检测
- [ ] 实现上下文文件扫描
- [ ] 检测隐藏的 HTML 和 Unicode 字符

#### 🟢 Phase 3: 高级功能 (低优先级)

- [ ] 技能索引动态加载
- [ ] 平台自适应提示
- [ ] 模型特定指导（GPT/Gemini）
- [ ] 三层架构优化（stable/context/volatile）

---

## Part 2: 上下文压缩 (Context Compression)

### 核心特性

- ✅ **自动压缩** - 当对话接近上下文限制时自动触发
- ✅ **有损压缩** - 使用 LLM 生成摘要保留关键信息
- ✅ **工具输出修剪** - 无需 LLM 调用的预压缩阶段
- ✅ **头尾保护** - 保护系统提示和最近的消息
- ✅ **工具对完整性** - 自动修复被压缩打断的 tool_call/result 对
- ✅ **敏感信息脱敏** - 自动移除 API keys、tokens 等敏感信息

---

## 与 Hermes 的功能对比

| 功能 | Hermes | Agent-Z | 状态 |
|------|--------|----------------|------|
| 摘要模板 | 12 字段 (详细) | 6 字段 (简化) | ⚠️ 待增强 |
| 摘要前导语 (Preamble) | 详细安全前缀 | 简化版 | ⚠️ 待增强 |
| 尾部保护 | Token 预算 + 消息数双保险 | ✅ Token 预算 + 消息数 | ✅ 完成 |
| 工具输出摘要化 | ✅ 完整实现 | ✅ 完整实现 | ✅ 完成 |
| 图片处理 | 多格式支持 | 简化支持 | ⚠️ 待增强 |
| 重复内容去重 | MD5 hash | ✅ MD5 hash | ✅ 完成 |
| 迭代摘要更新 | ✅ 支持 | ⚠️ 未实现 | ⚠️ 待实现 |
| 聚焦压缩 (focus_topic) | ✅ 支持 | ⚠️ 参数存在但未使用 | ⚠️ 待实现 |
| 辅助模型摘要 | 支持独立摘要模型 | 依赖主模型 | ⚠️ 待实现 |
| Rail 集成 | 手动触发 | ✅ 自动化集成 | ✅ agentz 更好 |
| CLI 命令 | /compress /usage | ✅ /compress /usage /compression-status | ✅ agentz 更完整 |
| 配置系统 | YAML | ✅ 环境变量 + 配置类 | ✅ agentz 更灵活 |
| 测试覆盖 | 基础测试 | ✅ 75+ 测试 | ✅ agentz 更完善 |
| 文档 | 代码注释 | ✅ 完整 Markdown | ✅ agentz 更完善 |

---

## 待增强功能

### 1. 迭代摘要更新 (Iterative Summary Updates)

**优先级**: 🔴 高

**当前状态**: 未实现 `_previous_summary` 状态追踪

**Hermes 实现**:
```python
if self._previous_summary:
    prompt = f"""...
PREVIOUS SUMMARY:
{self._previous_summary}

NEW TURNS TO INCORPORATE:
{content_to_summarize}
..."""
```

**目标**: 支持基于前一次摘要的增量更新

---

### 2. 聚焦压缩 (Focus Topic)

**优先级**: 🔴 高

**当前状态**: 参数存在但未实际使用

**Hermes 实现**:
```python
if focus_topic:
    prompt += f"\nFOCUS TOPIC: '{focus_topic}'"
```

**目标**: 压缩时保留特定主题的详细信息

---

### 3. 辅助模型摘要

**优先级**: 🟡 中

**当前状态**: 使用主模型生成摘要

**Hermes 实现**:
```python
from agent.auxiliary_client import call_llm
response = call_llm(task="compression", model=self.summary_model, ...)
```

**目标**: 支持使用便宜的辅助模型生成摘要

---

### 4. 增强图片处理

**优先级**: 🟡 中

**当前状态**: 简化版图片占位符

**Hermes 实现**:
- 多格式支持 (base64/截图/截图摘要)
- 多种 placeholder 格式
- 图片 token 精确计算

**目标**: 完善多格式图片处理

---

### 5. 更完整的摘要模板

**优先级**: 🟡 中

**当前状态**: 6 字段简化版

**Hermes 模板 (12 字段)**:
```
## Active Task
## Goal
## Constraints & Preferences
## Completed Actions
## Active State
## In Progress
## Blocked
## Key Decisions
## Resolved Questions
## Pending User Asks
## Relevant Files
## Remaining Work
## Critical Context
```

**当前模板 (6 字段)**:
```
## Active Task
## Goal
## Completed Actions
## Active State
## Key Decisions
## Remaining Work
```

---

## 压缩算法（5 阶段）

```
┌─────────────────────────────────────────────────────────────────┐
│  输入: 消息列表 (可能 50+ 条对话)                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  阶段 1: 预压缩修剪 (无 LLM 调用)                               │
│  - 工具输出摘要化 (200+ chars → 1-line summary)                   │
│  - 重复内容去重 (相同文件读取只保留最新)                        │
│  - JSON 参数截断 (>500 chars → 200 chars)                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  阶段 2: 头部保护                                             │
│  - 系统提示 (role=system) 始终保留                             │
│  - 前 N 条消息 (默认 3 条) 始终保留                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  阶段 3: 尾部保护 (Token 预算)                                │
│  - 最近 ~20K tokens (GPT-4o) 始终保留                         │
│  - 确保最后一条用户消息在保护区域内                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  阶段 4: 中间摘要化 (LLM 调用)                                 │
│  - 收集中间消息并生成结构化摘要                                │
│  - 摘要模板: Active Task / Goal / Completed / Remaining Work    │
│  - 迭代更新: 基于前一次摘要增量更新                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  阶段 5: 工具对修复                                           │
│  - 移除孤立的 tool_result (无对应的 tool_call)                  │
│  - 插入 stub tool_result (有 tool_call 无 result)              │
│  - 修复被压缩打断的请求/响应对                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  输出: 压缩后的消息列表 (~50 条 → ~20 条)                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 核心参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `threshold_percent` | 0.50 | 触发压缩的上下文百分比 (50% = 64K tokens for GPT-4o) |
| `protect_first_n` | 3 | 保护前 N 条消息 |
| `protect_last_n` | 10 | 保护最近 N 条消息 |
| `summary_target_ratio` | 0.20 | 摘要占摘要前内容的比例 |
| `max_summary_tokens` | 4000 | 摘要最大 token 数 |

---

## 快速开始

### 基本使用

```python
from agent.context.context_compressor import ContextCompressor

# 创建压缩器
compressor = ContextCompressor(
    model="gpt-4o",
    threshold_percent=0.50,
)

# 设置 LLM 客户端 (用于摘要生成)
compressor.set_llm_client(llm_provider)

# 检查是否需要压缩
if compressor.should_compress(prompt_tokens):
    messages = compressor.compress(messages)
```

### 集成到 Agent 循环

```python
from agent.context.compression_integration import CompressionIntegration

# 创建集成器
integration = CompressionIntegration(
    session_id="session_123",
    model="gpt-4o",
    llm_client=llm_provider,
)

# 在 LLM 调用前
messages = await integration.before_llm_call(messages, model)

# 调用 LLM
response = await llm.generate(messages)

# 在 LLM 调用后
await integration.after_llm_call(messages, response)
```

---

## CLI 命令

在交互模式下可使用以下命令:

| 命令 | 说明 |
|------|------|
| `/compress` | 手动触发上下文压缩 |
| `/compress --focus=X` | 聚焦压缩，保留特定主题 |
| `/usage` | 显示 Token 使用统计 |
| `/compression-status` | 显示压缩功能状态 |

---

## 环境变量配置

```bash
# 启用压缩 (默认 true)
export AGENTZ_COMPRESSION_ENABLED=true

# 压缩阈值 (默认 0.50 = 50%)
export AGENTZ_COMPRESSION_THRESHOLD=0.50

# 保护前 N 条消息 (默认 3)
export AGENTZ_COMPRESSION_PROTECT_FIRST=3

# 保护最近 N 条消息 (默认 10)
export AGENTZ_COMPRESSION_PROTECT_LAST=10

# 自动压缩 (默认 true)
export AGENTZ_COMPRESSION_AUTO=true

# 摘要比例 (默认 0.20)
export AGENTZ_COMPRESSION_SUMMARY_RATIO=0.20

# 静默模式 (默认 false)
export AGENTZ_COMPRESSION_QUIET=false
```

---

## Anti-Thrashing 保护

压缩器会自动检测并防止"震荡"问题：

- 如果连续 2 次压缩节省 <10%，自动跳过
- 压缩失败后进入 60 秒冷却期
- 支持手动 `/compress --force` 强制压缩

---

## 文件结构

```
agent/context/
├── context_engine.py              # ContextEngine 基类
├── context_compressor.py           # ContextCompressor 实现
├── token_estimator.py            # Token 估算器
├── compression_config.py          # 压缩配置
├── compression_integration.py    # 压缩集成器
└── compression_commands.py       # CLI 命令

agent/rails/
└── context_compression_rail.py   # ContextCompressionRail

agent/react/
└── compression_loop.py           # 压缩感知的 ReAct 循环

common/
└── redact.py                    # 敏感信息脱敏

tests/unit/agent/
├── test_context_compressor_new.py
└── test_compression_commands.py
tests/unit/common/
└── test_redact.py
```

---

## 验证方法

### 1. 运行单元测试

```bash
python -m pytest tests/unit/agent/test_context_compressor_new.py -v
python -m pytest tests/unit/common/test_redact.py -v
python -m pytest tests/unit/agent/test_compression_commands.py -v
```

### 2. 手动验证

```python
# 测试 Token 估算
from agent.context.token_estimator import estimate_messages_tokens_rough

messages = [{"role": "user", "content": "Hello"} * 1000]
tokens = estimate_messages_tokens_rough(messages)
print(f"估算 tokens: {tokens}")

# 测试压缩
from agent.context.context_compressor import ContextCompressor

compressor = ContextCompressor(model="gpt-4o", quiet_mode=True)
result = compressor.compress(messages)
print(f"压缩后: {len(result)} 条消息")
```

### 3. CLI 交互验证

```bash
python -m cli.main chat
> /compression-status   # 查看状态
> /usage              # 查看统计
> /compress           # 手动压缩
> /compress --focus=重构  # 聚焦压缩
```

### 4. 端到端验证

```bash
# 启动带压缩的交互式会话
python -m cli.main chat --verbose

# 在会话中触发多次对话，观察压缩行为
```

---

## 测试结果

```
======================== 75 passed, 1 warning in 0.22s ========================
```

测试覆盖:
- `common/redact.py` - 18 个测试
- `agent/context/token_estimator.py` - 27 个测试
- `agent/context/compression_commands.py` - 18 个测试

---

**最后更新**: 2026-06-02
**版本**: v3.0.0

