# Handsome Agent

> Hermes-Brain + OpenClaw-Body 双核驱动的模块化 AI 智能助手

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

***

## 🎯 项目概述

Handsome Agent 是一个企业级 AI Agent 系统，融合了：

- **OpenClaw** 的多渠道接入能力和工具抽象
- **Hermes** 的智能决策和自我进化能力

**核心特性**：LLM 驱动的意图识别 + 工具选择、自动学习进化、技能生命周期管理。

***

## 🏛️ Architecture

### Three-Tier Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    🚪 Access Layer                          │
│  CLI │ Gateway │ HTTP Adapter │ WebSocket                   │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                    🧠 Decision Layer                        │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  🤖 LLMDrivenDecisionEngine                           │  │
│  │  LLM directly understands intent + selects tools      │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ 💾 Memory    │  │ 📋 Skills    │  │ 📝 Trajectory│      │
│  │              │  │              │  │              │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  🔬 Curator (Async Post-Processing)                   │  │
│  │  Trajectory Evaluation → Skill Synthesis → Evolution  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                    🏃 Execution Layer                       │
│  Shell Executor │ Docker Executor │ Tool Executor           │
└─────────────────────────────────────────────────────────────┘
```

***

## 📁 项目目录结构

```
Handsome-Agent/
│
├── agent/                    # 🤖 Agent 核心
│   ├── agent_loop.py        #   Agent Loop（ReAct 模式）
│   ├── schemas.py           #   数据模型
│   ├── trajectory.py        #   轨迹记录
│   ├── memory.py            #   记忆管理
│   ├── context_engine.py    #   上下文引擎
│   ├── prompt_builder.py    #   提示词构建
│   ├── modern_agent.py      #   现代 Agent 实现
│   ├── llm_tool_selector.py #   LLM 驱动的工具选择器
│   ├── workspace.py         #   工作空间管理
│   ├── curator/             #   Curator（自我进化）
│   ├── llm/                 #   LLM Provider (OpenAI/Claude/DeepSeek等)
│   └── templates/           #   Agent 模板
│
├── skills/                   # 🛠️ 技能系统
│   ├── matcher.py           #   技能匹配
│   ├── loader.py            #   技能加载
│   ├── registry.py          #   技能注册
│   ├── system/             #   系统内置技能
│   └── user/               #   用户技能
│
├── gateway/                  # 🚪 网关
│   ├── server.py           #   HTTP 服务器
│   ├── middleware.py       #   中间件（认证/限流）
│   └── adapters/           #   渠道适配器
│
├── executor/                 # 🏃 执行层
│   ├── shell.py            #   Shell 执行器
│   └── docker.py          #   Docker 执行器
│
├── tools/                    # 🛠️ 工具定义
│   ├── registry.py          #   注册表
│   ├── integrated_tools.py #   集成工具
│   └── file_tools.py       #   文件工具
│
├── common/                   # 📦 基础设施
│   ├── config.py           #   配置
│   ├── logging_manager.py  #   日志管理（统一 LayerLogger）
│   ├── exceptions.py       #   异常
│   └── logging.py          #   简化日志配置
│
├── cli/                      # 💬 CLI
│   ├── main.py             #   主入口
│   ├── modern_cli.py       #   现代 CLI 实现
│   └── setup_wizard.py     #   配置向导
│
├── tests/                    # 🧪 测试套件
│   ├── unit/               #   单元测试
│   ├── integration/        #   集成测试
│   └── performance/        #   性能测试
│
├── docs/                     # 📚 文档系统
│   ├── index.md            #   文档索引
│   ├── architecture/       #   架构文档
│   ├── guides/             #   使用指南
│   ├── modules/            #   模块文档
│   └── references/         #   参考资料
│
├── api/                      # 📋 OpenAPI 规范
│   └── brain_service.yaml  #   网关 HTTP API 的 OpenAPI 规范
│
└── workspace/                # 💾 工作空间
    ├── logs/               #   日志目录
    └── sessions/           #   会话目录
```

***

## 🔑 核心特性

### 1. LLM 驱动的意图识别（无预定义意图）

```python
# 旧架构：预定义意图 → 工具选择
# 新架构：LLM 直接理解 + 选择工具
result = await engine.process(
    user_input="打开 agent.md 看看内容",
    available_tools=["read_file", "open_file", "launch_app"]
)
# → LLM 直接决定使用 read_file
```

### 2. 技能系统 (Skills)

- 技能加载、匹配、执行
- 技能使用追踪（use/view/patch 事件）
- 生命周期管理（active → stale → archived）
- 技能合并（相似技能自动聚合）

### 3. 自我进化 (Self-Evolution)

```
用户对话 → 轨迹记录 → Curator 评估 → 技能合成 → 自动学习
                                                      ↓
                                           越聊越好用 ✨
```

### 4. 完整工具生态

| 类别    | 工具                                                      |
| ----- | ------------------------------------------------------- |
| 📁 文件 | read\_file, write\_file, list\_directory, search\_files |
| 🚀 应用 | launch\_app, open\_calculator, open\_notepad            |
| 💻 终端 | terminal, run\_python                                   |
| 🔍 网络 | web\_search, web\_extract                               |
| 🧠 记忆 | memory\_save, memory\_search                            |

***

## 🔄 User Interaction Flows

This section documents all possible user interaction flows through the system. Understanding these flows helps developers trace issues and extend functionality.

### Flow Notation

```
User Input → [Component] → [Component] → ... → Response
```

---

### Flow 1: Simple Conversation

**Trigger**: User asks a general question or chat

```
┌─────────────────────────────────────────────────────────────────────────┐
│ User: "你好，今天天气怎么样？"                                          │
└─────────────────────────────────────────────────────────────────┬────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼────┐
│ 🚪 Access Layer                                                         │
│   [CLI/main.py] → [ModernAgent] → [Session Management]                   │
│   - Records user input to session                                        │
│   - Loads conversation history                                             │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🧠 Decision Layer                                                      │
│   [LLMDrivenDecisionEngine]                                             │
│   - LLM processes input directly                                        │
│   - Decision: direct_response (no tool needed, confidence: 1.0)          │
│   - LLM generates response                                              │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🚪 Access Layer                                                         │
│   [ModernAgent] → [Session]                                             │
│   - Records response to session                                          │
│   - Displays to user                                                   │
└─────────────────────────────────────────────────────────────────────────┘

Result: Direct text response from LLM
```

---

### Flow 2: File Reading

**Trigger**: User asks to read a file

```
┌─────────────────────────────────────────────────────────────────────────┐
│ User: "帮我看看 agent.md 的内容"                                        │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🧠 Decision Layer                                                      │
│   [LLMDrivenDecisionEngine]                                             │
│   - LLM identifies need: read_file tool                                 │
│   - Decision: tool_call (tool: read_file, confidence: high)              │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🏃 Execution Layer                                                     │
│   [ToolExecutionEngine] → [FileTools] → [ShellExecutor]                  │
│   - Executes file read operation                                         │
│   - Returns file content                                                 │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🧠 Decision Layer                                                      │
│   [LLMDrivenDecisionEngine]                                             │
│   - Formats response with file content                                   │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🚪 Access Layer                                                         │
│   [ModernAgent] → [Session]                                             │
│   - Displays formatted response                                          │
└─────────────────────────────────────────────────────────────────────────┘

Result: File content displayed to user
```

---

### Flow 3: Code Execution

**Trigger**: User asks to run code or execute a command

```
┌─────────────────────────────────────────────────────────────────────────┐
│ User: "帮我运行这个 Python 脚本：test.py"                               │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🧠 Decision Layer                                                      │
│   [LLMDrivenDecisionEngine]                                             │
│   - Decision: tool_call (tool: terminal_execute)                        │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🏃 Execution Layer                                                     │
│   [ShellExecutor]                                                      │
│   - Validates command (security check)                                   │
│   - Executes Python script                                              │
│   - Captures output/error                                               │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🧠 Decision Layer                                                      │
│   - Formats output for display                                          │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🚪 Access Layer                                                         │
│   - Displays execution result                                           │
└─────────────────────────────────────────────────────────────────────────┘

Security: Commands validated against whitelist patterns
```

---

### Flow 4: Application Launch

**Trigger**: User asks to open an application

```
┌─────────────────────────────────────────────────────────────────────────┐
│ User: "打开计算器"                                                    │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🧠 Decision Layer                                                      │
│   [LLMDrivenDecisionEngine]                                             │
│   - Decision: tool_call (tool: launch_app)                             │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🏃 Execution Layer                                                     │
│   [AppLauncher] → [Subprocess]                                          │
│   - Finds application path (calc.exe)                                    │
│   - Launches application                                                │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🚪 Access Layer                                                         │
│   - Confirms application launched                                        │
└─────────────────────────────────────────────────────────────────────────┘

Supported Apps: calculator, notepad, explorer, cmd, powershell, etc.
```

---

### Flow 5: Web Search

**Trigger**: User asks to search the web

```
┌─────────────────────────────────────────────────────────────────────────┐
│ User: "帮我搜索一下最新的 AI 新闻"                                       │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🧠 Decision Layer                                                      │
│   [LLMDrivenDecisionEngine]                                             │
│   - Decision: tool_call (tool: web_search)                              │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🏃 Execution Layer                                                     │
│   [WebTools] → [HTTPClient]                                            │
│   - Executes web search                                                │
│   - Returns search results                                              │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🧠 Decision Layer                                                      │
│   [LLMDrivenDecisionEngine]                                             │
│   - Summarizes results with LLM                                          │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🚪 Access Layer                                                         │
│   - Displays summarized results                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### Flow 6: Memory Operations

**Trigger**: User asks to save or recall information

```
┌─────────────────────────────────────────────────────────────────────────┐
│ User: "记住我的生日是 6 月 1 日"                                       │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🧠 Decision Layer                                                      │
│   [LLMDrivenDecisionEngine]                                             │
│   - Decision: tool_call (tool: memory_save)                              │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🏃 Execution Layer                                                     │
│   [MemoryTool] → [SessionStore]                                        │
│   - Saves memory to session/memory store                                │
│   - Persists to memory.md                                              │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🚪 Access Layer                                                         │
│   - Confirms memory saved                                              │
└─────────────────────────────────────────────────────────────────────────┘

Memory Types: Session (short-term), Memory (long-term via memory.md)
```

---

### Flow 7: Skill Creation

**Trigger**: User asks to learn/create a new skill

```
┌─────────────────────────────────────────────────────────────────────────┐
│ User: "教我怎么部署 Docker 容器"                                       │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🧠 Decision Layer                                                      │
│   [LLMDrivenDecisionEngine]                                             │
│   - LLM generates response with skill content                           │
│   - User confirms save                                                 │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🧠 Decision Layer                                                      │
│   [SkillManager]                                                       │
│   - Creates skill from conversation                                     │
│   - Saves to user/skills/ directory                                    │
│   - Registers in skill registry                                        │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🔬 Curator (Self-Evolution)                                             │
│   - Tracks skill usage pattern                                         │
│   - Evaluates skill effectiveness                                      │
└─────────────────────────────────────────────────────────────────────────┘

Skills stored in: ~/.handsome_agent/skills/
```

---

### Flow 8: Session Resume

**Trigger**: User resumes previous conversation

```
┌─────────────────────────────────────────────────────────────────────────┐
│ User: (Starts CLI with --continue or automatic today detection)          │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🚪 Access Layer                                                         │
│   [CLI] → [SessionManager]                                             │
│   - Detects today's existing session                                   │
│   - Loads session history                                             │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🚪 Access Layer                                                         │
│   [ModernAgent] → [Session]                                            │
│   - Displays conversation recap (last 10 exchanges)                      │
│   - User sees previous context                                         │
└─────────────────────────────────────────────────────────────────────────┘

Session Storage: ~/.handsome_agent/sessions/{YYYY-MM-DD}/
Session Format: {YYYYMMDD_HHMMSS}_{random}.json
```

---

### Flow 9: Docker Operations

**Trigger**: User asks to run a Docker container

```
┌─────────────────────────────────────────────────────────────────────────┐
│ User: "帮我启动一个 nginx 容器"                                        │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🧠 Decision Layer                                                      │
│   [LLMDrivenDecisionEngine]                                             │
│   - Decision: tool_call (tool: docker_run)                              │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🏃 Execution Layer                                                     │
│   [DockerExecutor]                                                     │
│   - Pulls image if needed                                              │
│   - Runs container                                                     │
│   - Returns container status                                            │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🚪 Access Layer                                                         │
│   - Displays container status                                           │
└─────────────────────────────────────────────────────────────────────────┘

Docker requires: Docker daemon running, proper permissions
```

---

### Flow 10: Scheduled Tasks (Cron)

**Trigger**: User asks to set up a scheduled task

```
┌─────────────────────────────────────────────────────────────────────────┐
│ User: "每天早上 9 点提醒我开会"                                         │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🧠 Decision Layer                                                      │
│   [LLMDrivenDecisionEngine]                                             │
│   - Decision: tool_call (tool: cron_create)                            │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🏃 Execution Layer                                                     │
│   [CronjobTool] → [System Scheduler]                                   │
│   - Parses natural language schedule                                    │
│   - Registers cron job                                                │
│   - Saves to ~/.handsome_agent/cronjobs.json                           │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🚪 Access Layer                                                         │
│   - Confirms scheduled task created                                    │
└─────────────────────────────────────────────────────────────────────────┘

Supported: cron expressions, natural language ("daily at 9am")
```

---

### Flow 11: Image Analysis

**Trigger**: User asks to analyze an image

```
┌─────────────────────────────────────────────────────────────────────────┐
│ User: "帮我看看这张图片里有什么" (with image attachment)           │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🧠 Decision Layer                                                      │
│   [LLMDrivenDecisionEngine]                                             │
│   - Detects image attachment                                          │
│   - Decision: tool_call (tool: vision_analyze)                          │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🏃 Execution Layer                                                     │
│   [VisionTool] → [LLM with Vision]                                     │
│   - Encodes image to base64                                           │
│   - Sends to vision-capable LLM                                       │
│   - Receives analysis                                                 │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🚪 Access Layer                                                         │
│   - Displays image analysis                                           │
└─────────────────────────────────────────────────────────────────────────┘

Supported formats: PNG, JPG, JPEG, GIF, BMP, WebP
```

---

### Flow 12: Agent Delegation (Sub-Agent)

**Trigger**: User asks to delegate a complex task

```
┌─────────────────────────────────────────────────────────────────────────┐
│ User: "帮我重构整个 backend 项目"                                      │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🧠 Decision Layer                                                      │
│   [LLMDrivenDecisionEngine]                                             │
│   - Identifies complex multi-step task                                 │
│   - Decision: tool_call (tool: delegate_task)                            │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🏃 Execution Layer                                                     │
│   [DelegateTool] → [SubAgent]                                          │
│   - Creates sub-agent instance                                         │
│   - Delegates sub-task                                                 │
│   - Sub-agent processes with its own ReAct loop                        │
│   - Aggregates results                                                 │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🧠 Decision Layer                                                      │
│   - Formats delegation report                                           │
└─────────────────────────────────────────────────────────────────┬───────────┘
                                                                          │
┌─────────────────────────────────────────────────────────────────────▼───────────┐
│ 🚪 Access Layer                                                         │
│   - Displays delegation results                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### Component Reference

| Component | Location | Purpose |
|-----------|----------|---------|
| [ModernAgent](agent/modern_agent.py) | `agent/modern_agent.py` | Main agent orchestrator |
| [Session](agent/session.py) | `agent/session.py` | Conversation state management |
| [ToolRegistry](tools/registry.py) | `tools/registry.py` | Tool registration and discovery |
| [LLMDrivenDecisionEngine](agent/llm_tool_selector.py) | `agent/llm_tool_selector.py` | LLM-based tool selection |
| [FileTools](tools/file_tools.py) | `tools/file_tools.py) | File operations |
| [ShellExecutor](executor/shell.py) | `executor/shell.py` | Command execution |
| [Curator](agent/curator/curator.py) | `agent/curator/curator.py` | Self-evolution and skill synthesis |

---

### Architecture Summary

```
                    🚪 Access Layer
                    ┌────────────────────────────────────────┐
                    │  CLI / Gateway / HTTP / WebSocket    │
                    │  Session Management                 │
                    │  Response Formatting               │
                    └────────────────┬───────────────────┘
                                     │
                    🧠 Decision Layer
                    ┌────────────────▼───────────────────┐
                    │  LLMDrivenDecisionEngine          │
                    │  ┌──────────────────────────────┐ │
                    │  │  LLM Provider (OpenAI/Claude/DeepSeek)  │ │
                    │  └──────────────────────────────┘ │
                    │  Memory | Skills | Trajectory      │
                    │  Curator (Self-Evolution)          │
                    └────────────────┬───────────────────┘
                                     │
                    🏃 Execution Layer
                    ┌────────────────▼───────────────────┐
                    │  ToolExecutionEngine               │
                    │  Shell | Docker | File | Network   │
                    └────────────────────────────────────┘
```

---

## 🚀 Quick Start

### 方式一：CLI 交互

```bash
# 安装依赖
pip install -r requirements.txt

# 配置 LLM（首次运行会提示）
python -m cli.main setup

# 启动交互式对话
python -m cli.main chat

# 运行测试
pytest tests/unit/ -v
```

### 方式二：Docker

```bash
docker-compose up -d
```

***

## 📚 文档导航

> 完整文档系统位于 [docs/index.md](docs/index.md)

### 新手入门

| 文档                                   | 内容      | 预计时间  |
| ------------------------------------ | ------- | ----- |
| [快速开始](docs/guides/quick-start.md)   | 5分钟快速上手 | 5min  |
| [系统设计](docs/guides/system-design.md) | 设计文档    | 10min |

### 架构与设计

| 文档                                            | 内容             |
| --------------------------------------------- | -------------- |
| [架构设计](docs/architecture/architecture.md)     | 三层架构详解         |
| [重构计划](docs/architecture/restructure-plan.md) | 目录结构重构计划       |
| [迁移指南](docs/guides/migration-guide.md)        | 意图识别层迁移 ⚠️ 已废弃 |

### 模块文档

| 模块                                        | 文档       |
| ----------------------------------------- | -------- |
| [Agent](docs/modules/agent/README.md)     | Agent 核心 |
| [Skills](docs/modules/skills/README.md)   | 技能系统     |
| [Gateway](docs/modules/gateway/README.md) | 网关       |
| [Tools](docs/modules/tools/README.md)     | 工具定义     |
| [CLI](docs/modules/cli/README.md)         | 命令行界面    |
| [Common](docs/modules/common/README.md)   | 基础设施     |

### 参考资料

| 文档                                               | 内容          |
| ------------------------------------------------ | ----------- |
| [LLM 集成](docs/references/llm-integration.md)     | 25+ LLM 提供商 |
| [能力清单](docs/references/capabilities-overview.md) | Agent 能力矩阵  |
| [编码规范](.trae/rules/rule.md)                      | 开发规范        |

***

## 🧪 Testing

```bash
# Run all tests
pytest tests/unit/ -v

# With coverage
pytest tests/unit/ --cov=. --cov-report=term-missing

# Specific modules
pytest tests/unit/curator/ -v
pytest tests/unit/tools/ -v
```

***

## 📄 License

MIT License

***

*Handsome Agent - Making AI smarter with use* ✨
*Last updated: 2026-06-01*
*Version: v3.0.0 - Architecture restructuring complete, unified logging system online*
