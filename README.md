# Handsome Agent

> Hermes-Brain + OpenClaw-Body 双核驱动的模块化 AI 智能助手

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 🎯 项目概述

Handsome Agent 是一个企业级 AI Agent 系统，融合了：
- **OpenClaw** 的多渠道接入能力和工具抽象
- **Hermes** 的智能决策和自我进化能力

**核心特性**：LLM 驱动的意图识别 + 工具选择、自动学习进化、技能生命周期管理。

---

## 🏛️ 架构设计

### 三层分层架构

```
┌─────────────────────────────────────────────────────────────┐
│                    🚪 接入层 (Interface Layer)              │
│  CLI │ Gateway │ HTTP Adapter │ WebSocket                   │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                    🧠 决策层 (Decision Layer)                 │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  🤖 LLMDrivenDecisionEngine                            │ │
│  │  LLM 直接理解用户意图 + 选择工具（无预定义意图分类）    │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ 💾 Memory     │  │ 📋 Skills    │  │ 📝 Trajectory │      │
│  │ (记忆管理)    │  │ (技能系统)    │  │ (轨迹记录)    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  🔬 Curator (异步后处理)                                │ │
│  │  轨迹评估 → 技能合成 → 自我进化                         │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                    🏃 执行层 (Execution Layer)              │
│  Shell Executor │ Docker Executor │ Tool Executor           │
└─────────────────────────────────────────────────────────────┘
```

### 架构层与目录映射

| 架构层 | 组件 | 目录 |
|--------|------|------|
| 🚪 接入层 | Gateway, CLI, HTTP Adapter | `adapter/`, `gateway/`, `cli/` |
| 🧠 决策层 | LLMDrivenDecisionEngine | `core/llm_tool_selector.py` |
| 🧠 决策层 | Memory, Skills, Trajectory | `core/`, `brain/` |
| 🧠 决策层 | AgentLoop (ReAct) | `brain/agent/agent_loop.py` |
| 🔬 Curator | Curator, Synthesizer | `brain_curator/` |
| 🏃 执行层 | Shell, Docker Executor | `executor/` |
| 🛠️ 工具层 | ToolRegistry | `tools/` |

---

## 📁 项目目录结构

```
Handsome-Agent/
├── adapter/                  # 🚪 接入层 - 消息路由、协议适配
├── agent/                     # 🤖 Agent 模板和提示词
├── api/                       # 📋 OpenAPI 规范
├── brain/                     # 🧠 决策层核心
│   ├── agent/                 #   AgentLoop (ReAct 模式)
│   ├── llm/                   #   LLM Provider (OpenAI/Claude)
│   ├── memory/                #   记忆存储 (SQLite/FTS5/Vector)
│   └── skills/                #   技能系统
├── brain_curator/             # 🔬 Curator 自我进化
├── cli/                       # 💬 终端界面
├── core/                      # 🧠 核心模块
│   ├── llm_tool_selector.py   #   LLM 驱动的工具选择
│   ├── session.py             #   会话管理
│   ├── memory_manager.py      #   记忆管理
│   └── task_planner.py        #   任务规划
├── docs/                      # 📚 完整文档系统
│   ├── index.md               #   文档索引 ← 点击查看全部
│   ├── architecture/          #   架构文档
│   ├── guides/                #   使用指南
│   ├── modules/               #   模块文档
│   ├── references/            #   参考资料
│   └── development/           #   开发文档
├── executor/                  # 🏃 执行层 (Shell/Docker)
├── gateway/                   # 🚪 网关 (认证/限流)
├── lightweight/               # ⚡ 轻量版 (<30MB, 零依赖)
├── llm_integration/           # 🤖 LLM 集成 (25+ 提供商)
├── plugins/                   # 🔌 插件系统
├── shared/                    # 📦 共享模块
├── skills/                    # 🛠️ 用户技能目录
├── tests/                     # 🧪 测试套件
└── tools/                     # 🛠️ 工具注册与执行
```

---

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

详情：[LLM 工具选择](docs/architecture/llm-tool-selection.md)

### 2. 技能系统 (Skills)

- 技能加载、匹配、执行
- 技能使用追踪（use/view/patch 事件）
- 生命周期管理（active → stale → archived）
- 技能合并（相似技能自动聚合）

详情：[Brain Skills](docs/modules/brain/skills.md)

### 3. 自我进化 (Self-Evolution)

```
用户对话 → 轨迹记录 → Curator 评估 → 技能合成 → 自动学习
                                                      ↓
                                           越聊越好用 ✨
```

详情：[Curator 模块](docs/modules/brain_curator/README.md)

### 4. 轻量版 Agent

零依赖（仅标准库），<30MB，适合移动端/IoT/边缘计算。

```bash
# 直接运行，无需安装
python -m lightweight
```

详情：[轻量版模块](docs/modules/lightweight/README.md)

### 5. 完整工具生态

| 类别 | 工具 |
|------|------|
| 📁 文件 | read_file, write_file, list_directory, search_files, open_file |
| 🚀 应用 | launch_app, open_calculator, open_notepad, open_explorer |
| 💻 终端 | terminal, run_python |
| 🔍 网络 | web_search, web_extract |
| 🧠 记忆 | memory_save, memory_search |

详情：[Tools 模块](docs/modules/tools/README.md)

---

## 🚀 快速开始

### 方式一：轻量版（推荐新手）

```bash
# 无需安装依赖
python -m lightweight
```

### 方式二：完整版

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

### 方式三：Docker

```bash
docker-compose up -d
```

---

## 📚 文档导航

> 完整文档系统位于 [docs/index.md](docs/index.md)

### 新手入门

| 文档 | 内容 | 预计时间 |
|------|------|----------|
| [快速开始](docs/guides/quick-start.md) | 5分钟快速上手 | 5min |
| [系统设计](docs/guides/system-design.md) | 设计文档 | 10min |

### 架构与设计

| 文档 | 内容 |
|------|------|
| [架构设计](docs/architecture/architecture.md) | 三层架构详解 |
| [LLM 工具选择](docs/architecture/llm-tool-selection.md) | LLM 直接决策 |
| [迁移指南](docs/guides/migration-guide.md) | 意图识别层迁移 ⚠️ 已废弃 |

### 模块文档

| 模块 | 文档 |
|------|------|
| Core | [docs/modules/core/README.md](docs/modules/core/README.md) |
| Tools | [docs/modules/tools/README.md](docs/modules/tools/README.md) |
| Brain | [docs/modules/brain/README.md](docs/modules/brain/README.md) |
| Skills | [docs/modules/brain/skills.md](docs/modules/brain/skills.md) |
| Curator | [docs/modules/brain_curator/README.md](docs/modules/brain_curator/README.md) |
| Gateway | [docs/modules/gateway/README.md](docs/modules/gateway/README.md) |
| Lightweight | [docs/modules/lightweight/README.md](docs/modules/lightweight/README.md) |
| CLI | [docs/modules/cli/README.md](docs/modules/cli/README.md) |

### 参考资料

| 文档 | 内容 |
|------|------|
| [LLM 集成](docs/references/llm-integration.md) | 25+ LLM 提供商 |
| [能力清单](docs/references/capabilities-overview.md) | Agent 能力矩阵 |
| [测试报告](docs/development/testing-summary.md) | 测试覆盖报告 |
| [编码规范](.trae/rules/rule.md) | 开发规范 |

### 开发

| 文档 | 内容 |
|------|------|
| [API 参考](docs/guides/api-reference.md) | 完整 API 文档 |
| [部署指南](docs/guides/deployment.md) | Docker/云平台 |
| [贡献指南](docs/guides/contributing.md) | 如何贡献 |

---

## 🧪 测试

```bash
# 运行所有测试
pytest tests/unit/ -v

# 带覆盖率
pytest tests/unit/ --cov=. --cov-report=term-missing

# 特定模块
pytest tests/unit/brain_curator/ -v
pytest tests/unit/tools/ -v
```

---

## 🐳 Docker 部署

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止
docker-compose down
```

---

## 📄 许可证

MIT License

---

*Handsome Agent - 让 AI 越用越聪明* ✨
*最后更新: 2026-06-01*