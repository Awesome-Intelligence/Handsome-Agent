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

**核心特性**：智能意图理解 + 工具选择、自动学习进化、技能生命周期管理、多平台适配。

***

## 🏛️ 架构

### 四层架构

```
┌─────────────────────────────────────────────────────────────┐
│                    🚪 Access Layer                          │
│         CLI │ TUI │ Gateway │ HTTP/WebSocket                │
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
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                    🔧 System Layer                          │
│       Config │ Logging │ i18n │ Security │ State           │
└─────────────────────────────────────────────────────────────┘
```

### 平台适配

支持多种即时通讯平台，通过统一协议接入：

| 平台 | 状态 | 说明 |
|------|------|------|
| **飞书** | ✅ 完善 | 完整适配，支持消息、卡片、图片 |
| **微信** | ✅ 完善 | 企业微信、个人微信 |
| **Telegram** | ✅ 完善 | Bot API 完整支持 |
| **Slack** | 🔄 开发中 | 基础消息支持 |
| **Discord** | 🔄 开发中 | 基础消息支持 |
| **钉钉** | ✅ 完善 | 企业内部使用 |
| **Microsoft Teams** | ✅ 完善 | 企业内部使用 |
| **WhatsApp** | 🔄 开发中 | 基础消息支持 |
| **IRC** | ✅ 完善 | 传统协议支持 |
| **Email** | ✅ 完善 | IMAP/SMTP |

### 通信协议

| 协议 | 说明 |
|------|------|
| **ACP** | Agent-Z 内部通信协议 (stdio/HTTP/WebSocket) |
| **A2A** | Google A2A (Agent to Agent) 协议 |

***

## 📁 目录结构

```
Agent-Z/
│
├── agent/                    # 🧠 Decision - Agent 核心
│   ├── agent.py             #   Agent 协调器
│   ├── session.py           #   💾 Memory - 会话管理
│   ├── response_router.py   #   响应路由
│   ├── self_improvement.py  #   自我改进
│   ├── context/             #   📊 Context - 上下文管理
│   ├── curator/             #   🔬 Curator - 自我进化
│   ├── llm/                 #   🤖 LLM - LLM 提供商
│   ├── memory/              #   💾 Memory - 记忆存储
│   ├── skills/              #   📋 Skills - 技能管理
│   ├── task/                #   ✅ Task - 任务管理
│   ├── acp/                 #   ACP 通信协议
│   ├── a2a/                 #   A2A 协议 (Google)
│   └── rails/               #   Rail 拦截器
│
├── tools/                    # 🏃 Execution - 🛠️ ToolExec
│   ├── definitions/         #   工具定义
│   ├── registry.py          #   工具注册表
│   └── *.py                 #   各类工具实现
│
├── skills/                   # 🧠 Decision - 📋 Skills
│   ├── registry.py          #   技能注册表
│   ├── matcher.py           #   技能匹配器
│   ├── lifecycle.py         #   生命周期管理
│   └── */                   #   系统/用户技能
│
├── gateway/                  # 🚪 Access - 网关
│   ├── server.py            #   HTTP 服务器
│   ├── gateway.py           #   网关核心
│   ├── session.py           #   会话管理
│   └── adapters/            #   渠道适配器 (OpenAI/CLI)
│
├── executor/                 # 🏃 Execution - 执行器
│   ├── shell.py             #   🐚 Shell 执行器
│   └── docker.py            #   🐳 Docker 执行器
│
├── tui/                      # 🚪 Access - TUI 界面
│   ├── textual_app/         #   Textual 应用
│   ├── views/               #   视图组件
│   ├── widgets/             #   自定义控件
│   └── consumers/           #   消息消费者
│
├── cli/                      # 🚪 Access - 💬 CLI
│   └── cli_commands/        #   CLI 命令
│
├── common/                   # 🔧 System - 基础设施
│   ├── config.py            #   配置管理
│   ├── logging_manager.py   #   日志管理
│   ├── i18n.py              #   国际化 (zh/en/ja/ko)
│   ├── exceptions.py        #   异常定义
│   └── state.py             #   状态管理
│
├── cron/                     # 定时任务调度
├── plugins/                  # 插件系统
├── tests/                    # 测试套件
└── docs/                     # 文档
```

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

### 4. 国际化

支持中文 (zh)、英文 (en)、日文 (ja)、韩文 (ko) 四种语言。

### 5. TUI 界面

基于 Textual 的富终端用户界面，支持实时流式输出、侧边栏导航、主题切换。

***

## 🚀 快速开始

**要求**: Python 3.11+

```bash
# 安装依赖
pip install -r requirements.txt

# 配置 LLM（首次运行会提示）
python -m cli.main setup

# 启动 TUI 界面（推荐）
python -m tui

# 启动交互式 CLI
python -m cli.main chat

# 启动 ACP 服务
python -m agent.acp.entry

# 启动网关
python -m gateway.server
```

***

## 📚 文档导航

| 文档                                           | 内容     |
| -------------------------------------------- | ------ |
| [快速开始](docs/guides/quick-start.md)           | 5分钟上手  |
| [架构设计](docs/architecture/architecture.md)    | 架构详解 |
| [开发规范](.claude/rules/)                       | 代码规范  |
| [变更日志](docs/CHANGELOG.md)                    | 版本更新   |

---

## 🧩 模块文档

| 模块      | 文档                                                          |
| ------- | ----------------------------------------------------------- |
| Agent   | [docs/modules/agent/README.md](docs/modules/agent/README.md)      |
| Skills  | [docs/modules/skills/README.md](docs/modules/skills/README.md)    |
| Gateway | [docs/modules/gateway/README.md](docs/modules/gateway/README.md) |
| Tools   | [docs/modules/tools/README.md](docs/modules/tools/README.md)      |
| CLI     | [docs/modules/cli/README.md](docs/modules/cli/README.md)          |
| TUI     | [docs/modules/tui/README.md](docs/modules/tui/README.md)          |

***

## 📄 License

MIT License
