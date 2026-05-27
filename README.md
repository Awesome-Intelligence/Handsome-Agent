```
░█░█░█▀█░█▀█░█▀▄░█▀▀░█▀█░█▄█░█▀▀ 
░█▀█░█▀█░█░█░█░█░▀▀█░█░█░█░█░█▀▀ 
░▀░▀░▀░▀░▀░▀░▀▀░░▀▀▀░▀▀▀░▀░▀░▀▀▀
```

# Handsome Agent

## 🎯 项目概述

一个基于 **Harness 架构**的模块化 AI 智能助手，**完全使用 LLM 进行意图识别**（无硬编码规则），支持多 LLM 提供商集成，具有高级推理能力和强大的工具调用系统。

> **核心原则**: "If LLM fails, the system fails gracefully, **NO hardcoded fallback**."

项目设计**完全借鉴了 Hermes Agent** 的架构理念，实现了完整的模块化架构：

### 🏛️ Harness 架构参考

**Harness 架构**是一种标准化的 Agent 框架模式，定义了清晰的分层和职责：

```
┌─────────────────────────────────────────────────────────────┐
│              Harness Architecture - Agent 标准架构            │
├─────────────────────────────────────────────────────────────┤
│  1. Interface Layer (接口层)                                 │
│     CLI │ Gateway │ WebSocket │ ACP Adapter                │
├─────────────────────────────────────────────────────────────┤
│  2. Intent Recognition Layer (意图识别层)                    │
│     ✨ LLM-powered Intent Parser (纯 LLM，无规则)            │
│     - llm_intent_service.py                                 │
│     - llm_web_search.py                                    │
│     - llm_terminal_command.py                              │
├─────────────────────────────────────────────────────────────┤
│  3. Task Planning Layer (任务规划层)                         │
│     Sub-task Decomposition │ Dependency Management          │
├─────────────────────────────────────────────────────────────┤
│  4. Memory System (记忆系统)                                 │
│     Short-term Session │ Long-term Persistence             │
├─────────────────────────────────────────────────────────────┤
│  5. Tool Abstraction Layer (工具抽象层)                      │
│     ToolRegistry │ SkillManager │ @register_tool          │
├─────────────────────────────────────────────────────────────┤
│  6. LLM Provider Layer (LLM 提供商层)                       │
│     Adapter Pattern │ 25+ Providers Support                │
└─────────────────────────────────────────────────────────────┘
```

### 🎯 纯 LLM Intent Recognition (意图识别)

**关键特性**:
- ✅ **NO Hardcoded Keywords** - 移除所有硬编码关键词匹配
- ✅ **NO Hardcoded Mappings** - 移除所有硬编码命令映射
- ✅ **NO Fallback Rules** - 移除所有 fallback 降级逻辑
- ✅ **Pure LLM Understanding** - 100% 依赖 LLM 进行意图理解

**实现文件**:
- [core/llm_intent_service.py](core/llm_intent_service.py) - 统一 LLM 意图服务
- [core/llm_web_search.py](core/llm_web_search.py) - LLM 驱动的搜索
- [core/llm_terminal_command.py](core/llm_terminal_command.py) - LLM 驱动的命令理解

**架构文档**:
- [docs/llm_intent_architecture.md](docs/llm_intent_architecture.md) - LLM 意图识别架构
- [docs/ARCHITECTURE_COMPLIANCE.md](docs/ARCHITECTURE_COMPLIANCE.md) - 架构合规性报告

### 🗂️ 核心文件结构 (与 Hermes Agent 对齐)

| 文件 | 功能 |
|------|------|
| `run_agent.py` | AIAgent 核心对话循环 |
| `cli.py` | CLI 入口，交互式终端 UI |
| `cli/` | CLI 子命令和设置向导 |
| `model_tools.py` | 工具发现、Schema 收集、调度 |
| `toolsets.py` | 工具分组和平台预设 |
| `hermes_state.py` | SQLite + FTS5 会话/状态数据库 |
| `hermes_constants.py` | 常量定义、HERMES_HOME、路径配置 |
| `batch_runner.py` | 批量轨迹生成 |
| `agent/` | Agent 内部模块 |
| `plugins/` | 插件系统（memory、context_engine 等） |

### 🧩 核心组件

- **Prompt Builder** - 系统提示词组装器
- **Context Engine** - 可插拔上下文管理与压缩
- **Memory Manager** - 记忆管理编排系统
- **Task Router** - 智能任务路由
- **Skill Manager** - 技能注册与执行
- **Tool Registry** - 70+ 工具支持
- **SQLite + FTS5** - 会话持久化与全文搜索
- **25+ LLM 提供商集成**
- **插件系统** - 支持 memory、context_engine 等插件

***

## 🏗️ 架构设计

### 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        Entry Points                              │
├─────────────────────────────────────────────────────────────────┤
│  CLI (cli.py)    Gateway (gateway/)    ACP Adapter             │
│  Batch Runner    API Server            Python Library          │
└──────────┬──────────────┬───────────────────────┬───────────────┘
           │              │                       │
           ▼              ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AIAgent (agent/ai_agent.py)                  │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐              │
│  │ Prompt       │ │ Provider     │ │ Tool         │              │
│  │ Builder      │ │ Resolution   │ │ Dispatch     │              │
│  │              │ │              │ │              │              │
│  │ • 压缩       │ │ • 3 API Modes│ │ • Backend    │              │
│  │ • 缓存       │ │ • chat_comp. │ │   Registry   │              │
│  └──────────────┘ └──────────────┘ │ • 48 tools   │              │
│                                   └──────────────┘              │
│  ┌──────────────────────────────────────────────────────┐      │
│  │ ContextEngine | MemoryManager | TrajectoryRecorder  │      │
│  └──────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
           │                                    │
           ▼                                    ▼
┌───────────────────┐              ┌──────────────────────────────┐
│ Session Storage   │              │ Tool Backends                │
│ (hermes_state.py) │              │                              │
│                   │              │ • Terminal (6 shells)        │
│ • SQLite + FTS5   │              │ • File (read/write/list)     │
│ • Session 持久化   │              │ • Web (http/search/fetch)   │
│ • Cache 缓存       │              │ • Code (run/format/lint)     │
└───────────────────┘              └──────────────────────────────┘
```

**架构说明：**

1. **Entry Points** - 多个入口：CLI / Gateway / ACP Adapter / Python Library
2. **AIAgent** - 核心大脑，协调 PromptBuilder、ProviderResolver、ToolDispatcher
3. **推理层** - AdvancedReasoningModule, InputClassifier, KnowledgeBase
4. **LLM层** - 25+ 提供商，支持 3 种 API 模式
5. **工具层** - ToolBackends 抽象，支持 Terminal/File/Web/Code
6. **存储层** - SQLite + FTS5 持久化

**调用关系：**
```
用户输入
    ↓
Entry Point (CLI/Gateway/ACP)
    ↓
┌─────────────────────────────────────────────────────────────────┐
│                    AIAgent (核心大脑)                           │
│  PromptBuilder → ProviderResolver → ToolDispatcher             │
└─────────────────────────────────────────────────────────────────┘
           │                                    │
           ▼                                    ▼
     ┌──────────┐                    ┌─────────────────┐
     │ Storage  │                    │ Tool Backends   │
     └──────────┘                    └─────────────────┘
```
         │            │ ◄── 工具层: File I/O
         └─────────────┘
```

### 层级 - 模块对应关系

| 层级 | Emoji | 模块 | 职责 |
|------|-------|------|------|
| **用户层** | 👤 | CLI 模块 (`cli.py`) | 命令行交互界面 |
| | | Gateway 模块 (`gateway/`) | REST API 网关 |
| **控制层** | 🎛️ | 核心框架 (`core/`) | CustomAgent、TaskRouter、SkillManager、SessionManager |
| **推理层** | 🧠 | AIAgent 核心 (`run_agent.py`) | 核心对话循环、Prompt 构建、上下文管理 |
| | | 高级推理 (`advanced_reasoning/`) | 智能推理与决策 |
| **LLM层** | 🤖 | LLM 集成 (`llm_integration/`) | 25+ 大模型提供商统一接入 |
| **工具层** | 🔧 | 工具系统 (`tools/`) | 文件、终端、网络、代码等工具 |
| | | 工具注册 (`model_tools.py`) | 工具发现与调度 |
| | | 工具集 (`toolsets.py`) | 工具分组与平台预设 |
| **存储层** | 💾 | 状态存储 (`hermes_state.py`) | SQLite + FTS5 会话存储 |

***

## 🔄 请求处理流程

### 单条指令的完整执行流程

```
用户输入 → CLI → AIAgent → TaskRouter → SkillManager → 工具/LLM → 返回结果
     │      │       │          │             │              │          │
     │      ▼       ▼          ▼             ▼              ▼          ▼
  1.输入 2.初始化  3.构建 Prompt  4.意图分类   5.技能匹配    6.执行操作   7.格式化输出
          会话管理   上下文管理   任务路由      工具选择      (LLM/工具)   返回用户
                   Memory 管理
```

### 详细流程图（基于最新架构）

```
┌────────────────────────────────────────────────────────────────────┐
│                      用户输入 "帮我读取 config.json 文件"            │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│  CLI 层 (cli.py / cli/main.py)                                    │
│  • 解析命令行参数                                                 │
│  • 加载配置 (hermes_constants.py)                                │
│  • 初始化 AIAgent 实例 (run_agent.py)                             │
│  • 创建 Session 会话 (hermes_state.py - SQLite + FTS5)            │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│  AIAgent 核心 (run_agent.py)                                       │
│  • PromptBuilder 构建系统提示词 (agent/prompt_builder.py)         │
│  • ContextEngine 管理上下文 (agent/context_engine.py)             │
│  • MemoryManager 加载记忆 (agent/memory_manager.py)               │
│  • 注入工具定义 (model_tools.py)                                  │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│  TaskRouter (core/router.py)                                     │
│  • IntentClassifier 分类：tool_use (工具使用)                     │
│  • 匹配路由：file_read 工具                                       │
│  • 计算匹配置信度                                                 │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│  SkillManager (core/skill_manager.py)                            │
│  • 根据路由匹配发现相关技能                                      │
│  • 调用 FileTools.read_file()                                     │
│  • 参数验证与权限检查                                             │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│  FileTools (tools/file_tools.py)                                  │
│  • 执行 read_file("config.json")                                 │
│  • 返回文件内容                                                   │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│  响应返回链                                                       │
│  • FileTools → SkillManager → AIAgent → CLI                      │
│  • 保存到 SQLite (hermes_state.py)                               │
│  • MemoryManager 提炼记忆 (agent/memory_manager.py)               │
│  • Trajectory 记录轨迹 (agent/trajectory.py)                      │
│  • CLI 格式化输出给用户                                            │
└────────────────────────────────────────────────────────────────────┘
```

### 任务路由决策流程

```
用户请求 → TaskRouter (core/router.py)
              │
              ▼
       IntentClassifier 分类
              │
    ┌─────────┼─────────┬─────────┬─────────┐
    ▼         ▼         ▼         ▼         ▼
 conversation  coding   question  tool_use  creation
    │         │         │         │         │
    ▼         ▼         ▼         ▼         ▼
 闲聊响应   代码处理    LLM 问答   工具调用   内容创作
```

### 工具调用决策流程

```
用户请求 → TaskRouter 识别意图
              │
              ▼
       需要工具调用？
              │
    ┌─────────┴─────────┐
    │                   │
   是                  否
    │                   │
    ▼                   ▼
SkillManager       AdvancedReasoningModule
    │                       │
    ▼                       ▼
发现并执行工具         直接生成响应
    │
    ▼
需要多轮调用？
    │
    ┌─────────┴─────────┐
    │                   │
   是                  否
    │                   │
    ▼                   ▼
循环执行工具      ToolCallingAgent 总结
    │                   │
    └─────────┬─────────┘
              │
              ▼
         返回最终响应
```

***

## 🌟 核心特性

### 1. 模块化设计

- **松耦合**: 各模块独立，易于扩展
- **可替换**: LLM 提供商可动态切换
- **可组合**: 按需启用/禁用模块
- **依赖注入**: 通过配置注入依赖

### 2. 核心框架 (core/)

| 组件 | 职责 | 文件路径 |
|------|------|----------|
| CustomAgent | 主编排器 | `core/agent.py` |
| TaskRouter | 任务路由 | `core/router.py` |
| SkillManager | 技能管理 | `core/skill_manager.py` |
| SessionManager | 会话管理 | `core/session.py` |

### 3. AIAgent 核心 (run_agent.py)

| 组件 | 职责 | 文件路径 |
|------|------|----------|
| AIAgent | 核心对话循环 | `run_agent.py` |
| PromptBuilder | 提示词构建 | `agent/prompt_builder.py` |
| ContextEngine | 上下文管理 | `agent/context_engine.py` |
| MemoryManager | 记忆管理 | `agent/memory_manager.py` |
| Trajectory | 轨迹记录 | `agent/trajectory.py` |

### 4. 工具系统

- **FileTools**: 文件读写、目录操作
- **TerminalTools**: 终端命令执行
- **WebTools**: 网络搜索、网页抓取
- **CodeTools**: 代码执行、静态分析
- **ToolCallingAgent**: 智能工具调用

### 5. LLM 集成

支持 25+ 大模型提供商：
- **国内**: 通义千问、智谱 AI、MiniMax、DeepSeek、Moonshot 等
- **国际**: OpenAI、Anthropic、Google、Meta 等

***

## 🚀 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 首次运行

```bash
python cli.py setup
```

### 启动 Agent

```bash
python cli.py chat
```

### 可用命令

| 命令 | 功能 |
|------|------|
| `python cli.py chat` | 启动交互式对话 |
| `python cli.py setup` | 运行设置向导 |
| `python cli.py sessions` | 查看所有会话 |
| `python cli.py batch -i input.json` | 批量处理 |
| `python cli.py version` | 显示版本信息 |

***

## 📚 文档

- [架构设计](docs/architecture.md)
- [快速上手](docs/quickstart.md)
- [错误状态码](docs/error_codes.md)
- [工具使用指南](docs/tools.md)

***

## 📄 许可证

MIT License
