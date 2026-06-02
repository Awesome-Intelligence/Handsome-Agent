# Handsome Agent

> Hermes-Brain + OpenClaw-Body 双核驱动的模块化 AI 智能助手

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

***

## 🎯 项目概述

Handsome Agent 是一个企业级 AI Agent 系统，融合了：

- **OpenClaw** 的多渠道接入能力和工具抽象
- **Hermes** 的智能决策和自我进化能力

**核心特性**：智能意图理解 + 工具选择、自动学习进化、技能生命周期管理。

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
│  ┌───────────────────────────────────────────────────────┐  │
│  │  🤖 LLMDrivenDecisionEngine                           │  │
│  │  Smart intent understanding + tool selection      │  │
│  └───────────────────────────────────────────────────────┘  │
│  💾 Memory │ 📋 Skills │ 📝 Trajectory │ 🔬 Curator         │
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
├── agent/                    # 🚪 Access / 🧠 Decision / 🏃 Execution
│   ├── modern_agent.py      #   🧠 Decision - Agent 协调器
│   ├── llm_tool_selector.py #   🧠 Decision - 🤖 LLM - 工具选择器
│   ├── session.py           #   🧠 Decision - 💾 Memory - 会话管理
│   ├── context_engine.py    #   🧠 Decision - 📊 Context - 上下文引擎
│   ├── prompt_builder.py    #   🧠 Decision - 📊 Context - 提示词构建
│   ├── curator/             #   🧠 Decision - 🔬 Curator - 自我进化
│   │   ├── curator.py
│   │   └── synthesizer.py
│   └── llm/                 #   🧠 Decision - 🤖 LLM - LLM 提供商
│       ├── openai_provider.py
│       ├── claude_provider.py
│       └── deepseek_provider.py
│
├── tools/                    # 🏃 Execution - 🛠️ ToolExec - 工具定义
│   ├── registry.py           #   工具注册表
│   ├── app_launcher.py       #   应用启动
│   ├── file_tools_bridge.py  #   文件工具
│   ├── cronjob_tool.py       #   定时任务
│   ├── vision_tool.py        #   图片分析
│   ├── memory_tool.py        #   记忆工具
│   ├── web_tools.py          #   网络工具
│   └── skill_manager_tool.py #   技能管理
│
├── skills/                   # 🧠 Decision - 📋 Skills - 技能系统
│   ├── registry.py
│   ├── matcher.py
│   ├── loader.py
│   ├── lifecycle.py
│   ├── merger.py
│   ├── evolution_manager.py
│   ├── telemetry.py
│   ├── system/              #   系统内置技能
│   └── user/                #   用户技能
│
├── gateway/                  # 🚪 Access - 网关
│   ├── server.py            #   HTTP 服务器
│   ├── gateway.py           #   网关核心
│   ├── gateway_cli.py       #   网关 CLI
│   └── adapters/            #   渠道适配器
│
├── executor/                 # 🏃 Execution - 执行器
│   ├── shell.py             #   🐚 ShellExec - Shell 执行器
│   └── docker.py            #   🐳 DockerExec - Docker 执行器
│
├── common/                   # 🔧 System - 基础设施
│   ├── config.py            #   配置管理
│   ├── logging_manager.py   #   日志管理
│   ├── exceptions.py         #   异常定义
│   └── state.py             #   状态管理
│
├── cli/                      # 🚪 Access - 💬 CLI - 命令行
│   ├── main.py              #   主入口
│   └── modern_cli.py        #   现代 CLI
│
├── tests/                    # 测试套件
│   ├── unit/
│   └── integration/
│
├── docs/                     # 文档
│   └── flows.md             #   用户交互流程详解
│
├── api/                      # OpenAPI 规范
└── workspace/                # 工作空间
```

### 层-子层速查

| 目录 | Layer | Sublayer | 说明 |
|------|-------|----------|------|
| agent/ | 🧠 Decision | 🤖 LLM | LLM 集成 |
| agent/session.py | 🧠 Decision | 💾 Memory | 会话管理 |
| agent/curator/ | 🧠 Decision | 🔬 Curator | 自我进化 |
| tools/ | 🏃 Execution | 🛠️ ToolExec | 工具执行 |
| executor/shell.py | 🏃 Execution | 🐚 ShellExec | Shell 执行 |
| executor/docker.py | 🏃 Execution | 🐳 DockerExec | Docker 执行 |
| gateway/ | 🚪 Access | 🚪 Gateway | 网关 |
| cli/ | 🚪 Access | 💬 CLI | 命令行 |
| common/ | 🔧 System | - | 基础设施 |

***

## 🔑 核心特性

### 1. 技能系统

技能加载、匹配、执行、追踪（use/view/patch 事件）、生命周期管理（active → stale → archived）

### 2. 自我进化

```
用户对话 → 轨迹记录 → Curator 评估 → 技能合成 → 越用越聪明
```

### 3. 工具生态

| 类别    | 工具                                     |
| ----- | -------------------------------------- |
| 📁 文件 | read\_file, write\_file, search\_files |
| 🚀 应用 | launch\_app, calculator, notepad       |
| 💻 终端 | terminal, run\_python                  |
| 🔍 网络 | web\_search                            |
| 🧠 记忆 | memory\_save, memory\_search           |

***

## 🔄 交互流程

### 流程 1: 简单对话（无需工具）

```
用户输入 → ModernAgent → LLM直接回复 → 响应
```

### 流程 2: 文件操作

```
用户请求 → LLM决策 → 执行层(Shell/File) → 格式化响应
```

### 流程 3: 代码执行

```
用户请求 → LLM决策 → ShellExecutor(安全验证) → 输出结果
```

### 流程 4: 会话恢复

```
启动CLI → 检测今日会话 → 加载历史 → 继续对话
```

**更多流程** (12个完整流程图): [docs/flows.md](docs/flows.md)

***

## 📁 数据存储

### 用户数据: `~/.handsome_agent/`

```
~/.handsome_agent/
├── config.json           # 配置文件
├── sessions/{date}/      # 对话历史 (按日期组织)
├── skills/user/         # 用户技能
├── memories/            # 长期记忆
├── logs/                # 日志文件
└── handsome_agent.db    # SQLite数据库
```

<br />

### 环境变量

```bash
export HANDSOME_HOME=/custom/path  # 自定义数据目录
```

***

## 🚀 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 配置 LLM（首次运行会提示）
python -m cli.main setup

# 启动交互式对话（自动继续今日会话）
python -m cli.main chat

# 强制新建会话
python -m cli.main chat --new-session

# 指定会话
python -m cli.main chat --session <session_id>
```

***

## 📚 文档导航

| 文档                                        | 内容     |
| ----------------------------------------- | ------ |
| [快速开始](docs/guides/quick-start.md)        | 5分钟上手  |
| [架构设计](docs/architecture/architecture.md) | 三层架构详解 |
| [编码规范](.trae/rules/rule.md)               | 开发规范   |

***

## 🧩 模块文档

| 模块      | 文档                                                               |
| ------- | ---------------------------------------------------------------- |
| Agent   | [docs/modules/agent/README.md](docs/modules/agent/README.md)     |
| Skills  | [docs/modules/skills/README.md](docs/modules/skills/README.md)   |
| Gateway | [docs/modules/gateway/README.md](docs/modules/gateway/README.md) |
| Tools   | [docs/modules/tools/README.md](docs/modules/tools/README.md)     |

***

## 📄 License

MIT License

***

*Last updated: 2026-06-01*
