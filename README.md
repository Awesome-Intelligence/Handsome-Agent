# Agent-Z

![Logo](docs/images/logo.png)

> Hermes-Brain + OpenClaw-Body 双核驱动的模块化 AI 智能助手

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

***

## 🎯 项目概述

Agent-Z 是一个企业级 AI Agent 系统，融合了：

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
Agent-Z/
│
├── agent/                    # 🧠 Decision
│   ├── agent.py             #   🧠 Decision - Agent 协调器
│   ├── session.py           #   🧠 Decision - 💾 Memory - 会话管理
│   ├── response_router.py  #   🧠 Decision - 响应路由
│   ├── self_improvement.py  #   🧠 Decision - 自我改进
│   ├── context/             #   🧠 Decision - 📊 Context
│   │   ├── context_engine.py
│   │   └── prompt_builder.py
│   ├── curator/             #   🧠 Decision - 🔬 Curator - 自我进化
│   │   ├── curator.py
│   │   ├── trajectory.py
│   │   └── trajectory_recorder.py
│   ├── llm/                 #   🧠 Decision - 🤖 LLM - LLM 提供商
│   │   ├── openai_provider.py
│   │   ├── claude_provider.py
│   │   ├── llm_web_search.py
│   │   └── llm_terminal_command.py
│   ├── memory/              #   🧠 Decision - 💾 Memory - 记忆存储
│   │   └── markdown_memory.py
│   ├── skills/              #   🧠 Decision - 📋 Skills - 技能管理
│   │   └── skill_manager.py
│   ├── task/               #   🧠 Decision - ✅ Task - 任务管理
│   │   ├── task_planner.py
│   │   └── task_executor.py
│   ├── rails/               #   Rail 拦截器（可插拔的 before/after 钩子）
│   │   ├── rail.py          #   Rail 基类
│   │   ├── manager.py       #   Rail 管理器
│   │   ├── task_event_rail.py #   任务事件 Rail
│   │   └── examples.py      #   Rail 示例
│   ├── react/               #   ReAct 执行引擎（LLM 驱动的循环模式）
│   │   ├── loop.py          #   ReAct 循环引擎
│   │   └── context.py       #   执行上下文
│   ├── tool_selector/       #   🧠 Decision - 🔧 ToolSelect - 工具选择
│   │   └── llm_tool_selector.py
│   ├── acp/                  #   🧠 Decision - 💾 Memory - Agent 通信协议
│   │   ├── adapter.py       #   ACP 服务器
│   │   ├── session.py       #   会话管理
│   │   ├── transport.py     #   传输层 (stdio/HTTP/WebSocket)
│   │   └── tools.py         #   ACP 工具
│   ├── a2a/                  #   🧠 Decision - 💾 Memory - A2A 协议 (Google)
│   │   ├── models.py        #   A2A 数据模型
│   │   ├── server.py        #   A2A 服务器
│   │   └── client.py        #   A2A 客户端/代理
│   └── templates/           #   Agent 模板
│
├── tools/                    # 🏃 Execution - 🛠️ ToolExec - 工具定义
│   ├── definitions/         #   工具定义
│   │   ├── file_tools.py     #   文件操作
│   │   ├── shell_tools.py   #   Shell 命令
│   │   ├── web_tools.py     #   网络工具
│   │   ├── code_tools.py    #   代码工具
│   │   ├── browser_tools.py #   浏览器自动化
│   │   ├── multimedia_tools.py  #   多媒体
│   │   └── task_tools.py    #   任务工具
│   ├── registry.py           #   工具注册表
│   ├── schema_registry.py     #   Schema 注册表
│   ├── app_launcher.py       #   应用启动
│   ├── file_tools_bridge.py  #   文件工具桥接
│   ├── cronjob_tool.py       #   定时任务
│   ├── vision_tool.py        #   图片分析
│   ├── memory_tool.py        #   记忆工具
│   ├── web_tools.py          #   网络工具
│   └── skill_manager_tool.py #   技能管理
│
├── skills/                   # 🧠 Decision - 📋 Skills - 技能系统
│   ├── registry.py          #   技能注册表
│   ├── matcher.py           #   技能匹配器
│   ├── loader.py            #   技能加载器
│   ├── lifecycle.py         #   生命周期管理
│   ├── merger.py            #   技能合并器
│   ├── evolution_manager.py #   进化管理器
│   ├── telemetry.py         #   遥测数据
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
│   └── main.py              #   主入口（含压缩命令支持）
│
├── tests/                    # 测试套件
│   ├── unit/
│   └── integration/
│
├── docs/                     # 文档
│   └── flows.md             #   用户交互流程详解
│
├── api/                      # 🚪 Access - [已废弃，请使用 gateway/adapters/openai_adapter.py]
│   └── __init__.py          #   重定向模块（保留向后兼容）
└── workspace/                # 工作空间
```

### 层-子层速查

| 目录 | Layer | Sublayer | 说明 |
|------|-------|----------|------|
| agent/ | 🧠 Decision | 🤖 LLM | LLM 集成 |
| agent/session.py | 🧠 Decision | 💾 Memory | 会话管理 |
| agent/curator/ | 🧠 Decision | 🔬 Curator | 自我进化 |
| agent/acp/ | 🧠 Decision | 💾 Memory | ACP 通信协议 |
| agent/a2a/ | 🧠 Decision | 💾 Memory | A2A 通信协议 (Google) |
| tools/ | 🏃 Execution | 🛠️ ToolExec | 工具执行 |
| executor/shell.py | 🏃 Execution | 🐚 ShellExec | Shell 执行 |
| executor/docker.py | 🏃 Execution | 🐳 DockerExec | Docker 执行 |
| gateway/ | 🚪 Access | 🚪 Gateway | 网关 |
| api/ | 🚪 Access | 🛠️ ToolExec | OpenAI-compatible API |
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

| 类别 | 工具 | 功能 |
|------|------|------|
| **📁 文件** | file_read, file_write, file_edit, directory_list | 读写文件、目录操作 |
| **🖥️ 命令** | shell_execute, python_execute, git_command | 命令执行、代码运行 |
| **🌐 网络** | web_search, web_extract, http_request | 搜索、抓取、HTTP请求 |
| **💻 代码** | code_analysis, code_format | 代码分析和处理 |
| **🌐 浏览器** | browser_open, browser_click | 浏览器自动化 |
| **🎨 多媒体** | image_generate, text_to_speech | 图像生成、语音合成 |
| **✅ 任务** | todo_add, todo_list, todo_complete | Todo 列表管理 |
| **💾 记忆** | memory_save, memory_search | 记忆存储检索 |
| **📋 技能** | skill_register, skill_execute | 技能注册执行 |
| **👁️ 视觉** | vision_analyze, vision_ocr | 图像分析和 OCR |
| **📅 定时** | cronjob_create, cronjob_list | 定时任务调度 |
| **🚀 应用** | app_launch, calculator | 应用启动 |

***

## 🔄 交互流程

### 简单对话
```
用户输入 → Agent → LLM直接回复 → 响应
```

### 工具调用
```
用户请求 → LLM决策 → ToolRegistry → 工具执行 → 格式化响应
```

### 更多流程
详细流程图 (12个)：[docs/flows.md](docs/flows.md)

***

## 📁 数据存储

### 用户数据: `~/.agent_z/`

```
~/.agent_z/
├── config.json           # 配置文件
├── sessions/{date}/      # 对话历史 (按日期组织)
├── skills/user/         # 用户技能
├── memories/            # 长期记忆
├── logs/                # 日志文件
└── agentz.db    # SQLite数据库
```

<br />

### 环境变量

```bash
export AGENT_Z_HOME=/custom/path  # 自定义数据目录
```

***

## 🚀 快速开始

**要求**: Python 3.11+

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

| 文档                                           | 内容     |
| -------------------------------------------- | ------ |
| [快速开始](docs/guides/quick-start.md)           | 5分钟上手  |
| [架构设计](docs/architecture/architecture.md)    | 三层架构详解 |
| [编码规范](.trae/rules/rule.md)                  | 开发规范   |
| [变更日志](docs/CHANGELOG.md)                    | 版本更新   |
| [贡献指南](docs/guides/contributing.md)          | 参与贡献   |

---

## 🧩 模块文档

| 模块      | 文档                                                          |
| ------- | ----------------------------------------------------------- |
| Agent   | [docs/modules/agent/README.md](docs/modules/agent/README.md)      |
| Skills  | [docs/modules/skills/README.md](docs/modules/skills/README.md)    |
| Gateway | [docs/modules/gateway/README.md](docs/modules/gateway/README.md) |
| Tools   | [docs/modules/tools/README.md](docs/modules/tools/README.md)      |
| CLI     | [docs/modules/cli/README.md](docs/modules/cli/README.md)          |

***

## 📄 License

MIT License

***

*Last updated: 2026-06-03*
