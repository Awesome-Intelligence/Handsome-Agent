# Agent Module - AIAgent 核心模块

## 📋 概述

AIAgent 核心模块是整个 Agent 的**推理层**，负责实现核心对话循环、Prompt 构建、上下文管理、记忆管理和轨迹记录等高级功能。

**在 Harness 架构中的位置**: LLM Provider Layer（LLM 提供商层）+ Memory System（记忆系统）。

> **核心原则**: 所有 Agent 设定都通过 Markdown 文件定义，遵循 Hermes Agent 和 OpenClaw 的最佳实践。

## 🏛️ Harness 架构 - Agent Layer

```
┌─────────────────────────────────────────────────────────────┐
│          Harness Architecture - Full Stack                    │
├─────────────────────────────────────────────────────────────┤
│  1. Intent Recognition (LLM-powered)                      │
│     llm_intent_service.py ← Pure LLM                      │
├─────────────────────────────────────────────────────────────┤
│  2. Task Planning                                       │
│     Sub-task Decomposition                                │
├─────────────────────────────────────────────────────────────┤
│  3. ✨ Memory System ← YOU ARE HERE                    │
│     Short-term │ Long-term │ Session                      │
├─────────────────────────────────────────────────────────────┤
│  4. LLM Provider                                        │
│     25+ Providers │ Adapter Pattern                      │
├─────────────────────────────────────────────────────────────┤
│  5. Tool Execution                                      │
│     ToolRegistry │ @register_tool                         │
└─────────────────────────────────────────────────────────────┘
```

## 📝 Agent 定义文件

Agent 的所有设定都存储在 Markdown 文件中，由 PromptBuilder 自动加载：

| 文件 | 用途 | 说明 |
|------|------|------|
| **[agent.md](agent.md)** | Agent 角色定义 | 身份、性格、能力边界、行为准则 |
| **[memory.md](memory.md)** | 记忆系统定义 | 记忆类型、检索机制、容量管理 |
| **[tools.md](tools.md)** | 工具使用规范 | 工具分类、使用规范、安全规则 |
| **[capabilities.md](capabilities.md)** | 能力清单 | 完整能力列表、技术限制、示例 |

**核心原则**: Agent Layer 负责与 LLM Provider 交互，管理对话记忆，**不直接处理用户意图**（这是 Intent Recognition Layer 的职责）。

## 🏗️ 架构设计

### 模块结构

```
agent/
├── __init__.py
├── ai_agent.py           # AIAgent 核心类 (新增)
├── acp_adapter.py        # ACP 协议适配器 (新增)
├── tool_backends.py      # 工具后端抽象 (新增)
├── prompt_builder.py     # 提示词构建器
├── context_engine.py     # 上下文引擎
├── memory_provider.py     # 记忆提供商接口
├── memory_manager.py     # 记忆管理器
└── trajectory.py        # 轨迹记录器
```

### Hermes 风格架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Entry Points                                  │
├─────────────────────────────────────────────────────────────────────┤
│  CLI (cli.py)    Gateway (gateway/)    ACP Adapter (acp_adapter/) │
│  Batch Runner    API Server            Python Library              │
└──────────┬──────────────┬───────────────────────┬─────────────────┘
           │              │                       │
           ▼              ▼                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     AIAgent (ai_agent.py)                           │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                  │
│  │ Prompt       │ │ Provider     │ │ Tool         │                  │
│  │ Builder      │ │ Resolution   │ │ Dispatch     │                  │
│  │              │ │              │ │              │                  │
│  │ • Compress   │ │ • 3 API Modes│ │ • Backend    │                  │
│  │ • Cache      │ │ • chat_comp. │ │   Registry   │                  │
│  │              │ │ • completion │ │ • 48 tools   │                  │
│  └──────────────┘ └──────────────┘ └──────────────┘                  │
└─────────────────────────────────────────────────────────────────────┘
           │                                    │
           ▼                                    ▼
┌───────────────────┐              ┌──────────────────────┐
│ Session Storage   │              │ Tool Backends        │
│ (hermes_state.py) │              │                      │
│                   │              │ • Terminal (6 shells)│
│ • SQLite + FTS5   │              │ • File               │
│ • Session persist │              │ • Web                │
│ • Cache           │              │ • Code               │
└───────────────────┘              └──────────────────────┘
```

## 🧩 核心组件

### 1. AIAgent (ai_agent.py) - 新架构

**职责**: 核心对话循环，协调所有组件完成推理任务。

**组成**:

| 组件 | 描述 |
|------|------|
| **PromptBuilder** | 提示词构建、压缩、缓存 |
| **ProviderResolver** | 多 API 模式支持 (chat_completion, completion, anthropic) |
| **ToolDispatcher** | 工具分发到各个 Backend |
| **ContextEngine** | 上下文压缩管理 |
| **MemoryManager** | 记忆管理 |
| **TrajectoryRecorder** | 轨迹记录 |

**处理流程**:

```
用户输入 → PromptBuilder → ProviderResolver → ToolDispatcher → 返回
               │              │                │
               ▼              ▼                ▼
          压缩提示词      生成响应          执行工具
```

### 2. ProviderResolver - 多 API 模式

**支持的 API 模式**:

| 模式 | 描述 | 提供商 |
|------|------|--------|
| `chat_completion` | OpenAI chat 格式 | OpenAI, Azure, 通义千问 |
| `completion` | 传统 completion | GPT-3 |
| `anthropic` | Claude 格式 | Anthropic Claude |

### 3. ToolDispatcher & ToolBackends

**工具分发架构**:

```
ToolDispatcher
    │
    ├── TerminalBackend (powershell, bash, cmd...)
    ├── FileBackend (read, write, list, exists)
    ├── WebBackend (http_request, web_search, fetch_url)
    └── CodeBackend (run_code, format_code, lint_code)
```

### 4. ACP Adapter - 外部通信协议

**ACP 协议支持**:

| 动作 | 描述 |
|------|------|
| `respond` | 发送请求获取响应 |
| `register_tool` | 动态注册工具 |
| `register_provider` | 动态注册 Provider |
| `get_stats` | 获取统计信息 |
| `list_tools` | 列出可用工具 |
| `health_check` | 健康检查 |

### 2. PromptBuilder

**职责**: 构建系统提示词，整合指令、个性、工具定义等信息。

**处理流程**:

```
配置 → 指令部分 → 个性部分 → 工具定义 → 上下文 → 输出完整 Prompt
         │            │            │          │
         ▼            ▼            ▼          ▼
      系统指令      角色设定      工具列表    历史消息
```

**Prompt 结构**:

```
## Instructions
[系统指令]

## Personality
[个性描述]

## Tools
[工具定义 JSON]

## Context
[对话历史]

## User
[用户输入]
```

### 3. ContextEngine

**职责**: 可插拔上下文管理与压缩，优化上下文窗口使用。

**处理流程**:

```
消息列表 → 分析重要性 → 压缩上下文 → 返回优化后消息
               │              │
               ▼              ▼
         语义分析        智能截断
```

**支持的策略**:
- `SimpleContextEngine` - 简单保留所有消息
- `TruncatingContextEngine` - 按token数截断
- `SummarizingContextEngine` - 智能总结压缩

### 4. MemoryManager

**职责**: 记忆管理编排系统，负责存储、检索和反思记忆。

**处理流程**:

```
输入 → 存储记忆 → 检索相关记忆 → 反思总结 → 输出
         │            │              │
         ▼            ▼              ▼
      短期记忆        长期记忆       记忆提炼
```

**记忆类型**:
- **短期记忆**: 当前会话上下文
- **长期记忆**: 跨会话知识存储
- **反思记忆**: 从历史中提炼的关键信息

### 5. Trajectory

**职责**: 轨迹保存助手，记录代理执行历史，支持回溯和分析。

**处理流程**:

```
执行开始 → 记录步骤 → 保存轨迹 → 执行结束
               │           │
               ▼           ▼
         每步状态       持久化存储
```

**轨迹内容**:
- 时间戳
- 思考过程
- 工具调用
- 中间结果

## 🔄 完整执行流程

```
┌────────────────────────────────────────────────────────────────────┐
│                        用户输入                                    │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│  PromptBuilder (agent/prompt_builder.py)                          │
│  • 加载系统指令                                                    │
│  • 添加个性设定                                                    │
│  • 注入工具定义                                                    │
│  • 整合上下文历史                                                  │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│  ContextEngine (agent/context_engine.py)                          │
│  • 分析消息重要性                                                  │
│  • 压缩上下文到合适长度                                            │
│  • 返回优化后的上下文                                              │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│  MemoryManager (agent/memory_manager.py)                          │
│  • 检索相关长期记忆                                                │
│  • 提炼反思信息                                                    │
│  • 注入到上下文                                                    │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│  LLM 调用 (llm_integration/)                                      │
│  • 发送完整 Prompt                                                 │
│  • 获取响应                                                        │
│  • 解析工具调用指令                                                │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│  Trajectory (agent/trajectory.py)                                 │
│  • 记录执行步骤                                                    │
│  • 保存轨迹到数据库                                                │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│                        返回响应                                    │
└────────────────────────────────────────────────────────────────────┘
```

## 📊 组件协作关系

| 组件 | 职责 | 依赖 |
|------|------|------|
| AIAgent | 核心对话循环 | 所有其他组件 |
| PromptBuilder | 提示词构建 | ContextEngine, MemoryManager |
| ContextEngine | 上下文管理 | 无 |
| MemoryManager | 记忆管理 | memory_provider |
| Trajectory | 轨迹记录 | hermes_state |

## 🎯 使用示例

```python
from run_agent import AIAgent
from agent.prompt_builder import PromptBuilder

# 创建 Agent
agent = AIAgent()

# 构建提示词
builder = PromptBuilder()
builder.add_instructions("你是一个帮助用户的助手")
builder.add_personality("友好、专业")
builder.add_tools(tools)
prompt = builder.build()

# 处理请求
response = await agent.respond("你好")
```

## 🔓 开源替代方案

### 1. Prompt 构建

| 方案 | 描述 | 适用场景 | GitHub |
|------|------|----------|--------|
| **LangChain Prompt Templates** | 模板化管理 | 动态提示词 | [langchain-ai/langchain](https://github.com/langchain-ai/langchain) |
| **Promptify** | Prompt 优化库 | Prompt 工程 | [promptslab/Promptify](https://github.com/promptslab/Promptify) |
| **GPTTools** | Prompt 工具集 | 开发辅助 | [usaobo/GPT-tools](https://github.com/usaobo/GPT-tools) |
| **PromptTools** | Prompt 测试框架 | 实验对比 | [PromptEngineers/PromptTools](https://github.com/PromptEngineers/PromptTools) |
| **Hint** | 结构化 Prompt | YAML 定义 | [cogni糯/Hint](https://github.com/cogni糯/Hint) |

### 2. 上下文管理

| 方案 | 描述 | 适用场景 | GitHub |
|------|------|----------|--------|
| **LangChain Memory** | 多种记忆类型 | 对话上下文 | [langchain-ai/langchain](https://github.com/langchain-ai/langchain) |
| **context7** | RAG 上下文管理 | 长上下文 | [context7/context7](https://github.com/context7/context7) |
| **MemGPT** | 分层上下文 | Agent 记忆 | [cg123/memgpt](https://github.com/cg123/memgpt) |
| **LongContext** | 长上下文处理 | 百万 token | [KelvinDaWizard/long-context](https://github.com/KelvinDaWizard/long-context) |

**集成建议**:
```python
# 使用 LangChain 管理对话上下文
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain

memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True
)

conversation = ConversationChain(
    llm=llm,
    memory=memory,
    verbose=True
)
```

### 3. 记忆管理

| 方案 | 描述 | 适用场景 | GitHub |
|------|------|----------|--------|
| **MemGPT** | 分层记忆 | 复杂 Agent | [cg123/memgpt](https://github.com/cg123/memgpt) |
| **Letta** | 有状态 Agent | 持久化 | [letta-ai/letta](https://github.com/letta-ai/letta) |
| **Recall** | 分层记忆 | 认知模拟 | [topoteres/Recall](https://github.com/topoteres/Recall) |
| **AutoGen Memory** | 多代理记忆 | 协作场景 | [microsoft/autogen](https://github.com/microsoft/autogen) |

### 4. 轨迹记录

| 方案 | 描述 | 适用场景 | GitHub |
|------|------|----------|--------|
| **LangSmith** | LLM 可观测性 | 生产监控 | [langchain-ai/langsmith-sdk](https://github.com/langchain-ai/langsmith-sdk) |
| **AgentOps** | Agent 监控 | 性能追踪 | [AgentOps-AI/agentops](https://github.com/AgentOps-AI/agentops) |
| **Phoenix** | LLM 可视化 | 调试分析 | [Arize-ai/phoenix](https://github.com/Arize-ai/phoenix) |
| **Weights & Biases** | 实验追踪 | 模型监控 | [wandb/wandb](https://github.com/wandb/wandb) |

**集成建议**:
```python
# 使用 LangSmith 追踪轨迹
from langsmith import trace

@trace
async def agent_loop(user_input):
    # Agent 执行逻辑
    return response
```

### 5. 对话管理

| 方案 | 描述 | 适用场景 | GitHub |
|------|------|----------|--------|
| **ChatUI** | 对话界面 | UI 组件 | [Chatsona/ChatUI](https://github.com/Chatsona/ChatUI) |
| **Streamlit** | 数据应用 | 快速原型 | [streamlit/streamlit](https://github.com/streamlit/streamlit) |
| **Gradio** | ML 界面 | 对话 Demo | [gradio-app/gradio](https://github.com/gradio-app/gradio) |
| **Chainlit** | ChatGPT 风格 | 生产聊天 | [Chainlit/chainlit](https://github.com/Chainlit/chainlit) |

### 6. 完整 Agent 框架

| 方案 | 描述 | 适用场景 | GitHub |
|------|------|----------|--------|
| **LangChain Agents** | 完整框架 | 通用 Agent | [langchain-ai/langchain](https://github.com/langchain-ai/langchain) |
| **LlamaIndex** | 数据 Agent | RAG 增强 | [run-llama/llama_index](https://github.com/run-llama/llama_index) |
| **AutoGen** | 多代理框架 | 协作场景 | [microsoft/autogen](https://github.com/microsoft/autogen) |
| **CrewAI** | 角色协作 | 团队 Agent | [joaomdmoura/crewAI](https://github.com/joaomdmoura/crewAI) |
| **MetaGPT** | SOP 驱动 | 软件开发 | [datawhalechina/MetaGPT](https://github.com/datawhalechina/MetaGPT) |
| **OpenDevin** | AI 开发者 | 代码任务 | [OpenDevin/OpenDevin](https://github.com/OpenDevin/OpenDevin) |

## 🔧 替换指南

### 使用 LangChain 管理上下文

```python
# 当前实现
from agent.context_engine import TruncatingContextEngine
context_engine = TruncatingContextEngine(max_tokens=8192)
compressed = context_engine.compress(messages)

# LangChain 替代
from langchain.memory import ConversationBufferMemory
memory = ConversationBufferMemory(
    memory_key="chat_history",
    max_token_limit=8192
)
```

### 使用 LangSmith 追踪轨迹

```python
# 当前实现
from agent.trajectory import TrajectoryManager
trajectory = TrajectoryManager()
trajectory.record_step(step)

# LangSmith 替代
from langsmith import trace, traceable

@traceable
async def agent_loop(input_text):
    # Agent 执行逻辑
    return response
```

## 📚 进一步阅读

- [LangChain Documentation](https://docs.langchain.com)
- [MemGPT Documentation](https://memgpt.readthedocs.io)
- [LangSmith Documentation](https://docs.smith.langchain.com)
- [Chainlit Documentation](https://docs.chainlit.io)
