# Handsome Agent

## 🎯 项目概述

**Hermes-Brain + OpenClaw-Body** 双核驱动的模块化 AI 智能助手架构。

> 融合 OpenClaw 的多渠道接入能力和 Hermes 的智能决策能力，打造企业级 AI Agent 系统。

---

## 🏛️ 架构设计

### 三层分层解耦架构

```
┌─────────────────────────────────────────────────────────────┐
│                   接入层 (OpenClaw 接管)                      │
│  WhatsApp / Telegram / Slack / Discord / 飞书 / 邮件 / CLI    │
│  ↓                                                          │
│  Gateway (消息路由 / 鉴权 / 会话管理 / 多端同步)               │
└─────────────────────────────┬───────────────────────────────┘
                              │ (标准化 JSON 消息)
┌─────────────────────────────▼───────────────────────────────┐
│                   决策层 (Hermes 接管)                        │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  核心 Agent Loop (ReAct / Tool Calling)            │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐│    │
│  │  │ 意图识别层   │  │ 记忆检索层   │  │ 路由层       ││    │
│  │  │ (Classifier) │  │ (SQLite+FTS5)│  │ (TaskRouter) ││    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘│    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐│    │
│  │  │ 工具选择层   │  │ 上下文压缩   │  │ 知识层       ││    │
│  │  │ (SkillMgr)  │  │ (Summarizer)│  │ (Knowledge) ││    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘│    │
│  └─────────────────────────────┬───────────────────────┘    │
│                                │ (Tool Call 指令)           │
│  ┌─────────────────────────────▼───────────────────────┐    │
│  │  后处理层 (PostProcessing)                           │    │
│  │  响应生成 → 格式优化 → 缓存更新                      │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Curator (异步)                                     │    │
│  │  轨迹评估 → 技能提炼/修补 → 写入 Skill DB            │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────┬───────────────────────────────┘
                              │ (执行指令)
┌─────────────────────────────▼───────────────────────────────┐
│                   执行层 (混合/可选)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Local Shell │  │ Docker/SSH   │  │ Computer Use│ (OC)   │
│  │ (Hermes)    │  │ (Hermes)     │  │ (OpenClaw)  │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

#### 决策层子层说明

| 子层 | 职责 | 组件 |
|------|------|------|
| **意图识别层** | 识别用户意图类型 | IntentClassifier |
| **记忆检索层** | 会话记忆、缓存查询 | MemoryCache、LRUCache |
| **路由层** | 任务路由分发 | TaskRouter |
| **工具选择层** | 技能发现与执行 | SkillManager |
| **上下文压缩层** | 对话摘要、上下文管理 | Summarizer |
| **知识层** | 知识库检索 | KnowledgeBase |
| **后处理层** | 响应生成与优化 | ResponseProcessor |
| **Curator** | 异步自我进化 | TrajectoryEvaluator、SkillSynthesizer |

#### 三层架构与目录映射

| 架构层 | 对应目录 | 说明 |
|--------|----------|------|
| **接入层** | `adapter/` | 多渠道接入、消息路由、鉴权 |
| **决策层** | `brain/` | 核心 Agent Loop、LLM 集成、记忆、技能 |
| **决策层** | `brain_curator/` | 异步自我进化（Curator） |
| **决策层** | `core/` | 核心模块（路由、会话、日志） |
| **执行层** | `executor/` | Shell 执行、Docker 隔离执行 |
| **工具层** | `tools/` | 工具 Schema 定义与对齐 |

### 项目目录结构

```
handsome-agent/
├── adapter/                    # 接入层 (Access Layer)
│   ├── gateway.py            # Gateway 核心
│   ├── message.py            # 标准化消息格式
│   ├── adapters/              # 渠道适配器
│   │   ├── http_adapter.py  # HTTP/WebSocket
│   │   └── cli_adapter.py   # 命令行
│   └── protocols/           # 通信协议
│
├── brain/                     # 决策层 (Decision Layer)
│   ├── service.py           # Brain Service API
│   ├── service_cli.py      # CLI 入口
│   ├── trajectory.py       # 轨迹记录器
│   ├── agent/               # Agent 核心循环
│   │   ├── agent_loop.py   # ReAct 核心循环
│   │   └── schemas.py      # 工具 Schema
│   ├── llm/                 # LLM 集成
│   │   ├── base.py         # LLM Provider 基类
│   │   ├── openai_provider.py  # OpenAI Provider
│   │   ├── claude_provider.py  # Claude Provider
│   │   └── factory.py      # LLM Factory
│   ├── memory/             # 记忆检索层
│   │   ├── vector_store.py # 向量存储
│   │   ├── sqlite_store.py # SQLite + FTS5
│   │   ├── summarizer.py   # 上下文压缩
│   │   └── chromadb_store.py  # ChromaDB 支持
│   └── skills/             # 工具选择层
│       ├── matcher.py      # 技能匹配
│       ├── loader.py       # 技能加载
│       └── registry.py     # 技能注册表
│
├── brain_curator/            # 决策层 - Curator (异步后处理)
│   ├── curator.py           # Curator 主逻辑
│   ├── evaluator.py        # 轨迹评估器
│   ├── synthesizer.py      # 技能合成器
│   └── writer.py           # 技能写入器
│
├── executor/                  # 执行层 (Execution Layer)
│   ├── base.py              # Executor 基类
│   ├── shell_executor.py   # Shell 执行器
│   └── docker_executor.py   # Docker 隔离执行器
│
├── tools/                    # 工具 Schema 对齐层
│   ├── schema_registry.py   # 统一 Schema 注册表
│   ├── adapters/          # Hermes/OpenClaw 适配器
│   └── definitions/        # 标准化工具定义
│       ├── file_tools.py
│       ├── shell_tools.py
│       └── openclaw_tools.py
│
├── core/                     # 核心模块
│   ├── agent.py            # CustomAgent 实现
│   ├── skill_manager.py    # 技能管理器
│   ├── router.py           # 路由层
│   ├── session.py          # 会话管理
│   └── layer_logger.py     # 分层日志
│
├── shared/                   # 共享模块
│   ├── config.py           # 配置管理
│   ├── logging.py         # 日志配置
│   ├── exceptions.py      # 公共异常
│   └── models.py         # 公共数据模型
│
├── api/
│   └── brain_service.yaml # OpenAPI 规范
│
├── tests/                   # 测试
│   ├── unit/              # 单元测试
│   ├── integration/       # 集成测试
│   └── brain_curator/     # 自我进化测试
│
├── docker-compose.yml      # Docker 部署
├── requirements.txt
├── TODO.md                # 任务清单
└── README.md
```

---

## 🔑 核心特性

### 1. Tool Schema 对齐
- **UnifiedToolSchema** 统一所有工具格式
- **HermesToolAdapter** / **OpenClawToolAdapter** 处理来源转换

### 2. LLM 集成
- **OpenAI Provider** - GPT-4 / GPT-3.5-turbo
- **Claude Provider** - Claude 3 Opus / Sonnet / Haiku
- 流式响应支持

### 3. 执行层分层
- **ShellExecutor** - 本地执行（白名单保护）
- **DockerExecutor** - 容器隔离执行

### 4. Curator 异步后处理
- **TrajectoryEvaluator** - 轨迹评估
- **SkillSynthesizer** - 从成功案例提取技能
- **SkillWriter** - 写入 `~/.skills/` 目录

### 5. 自我进化系统（越用越好用）

```
┌─────────────────────────────────────────────────────────────────┐
│                 Hermes 自我进化循环                                │
├─────────────────────────────────────────────────────────────────┤
│  用户输入 → 执行任务 → 记录轨迹 (TrajectoryRecorder)           │
│       ↓         ↓           ↓                                   │
│  ┌─────────────────────────────────────────┐                   │
│  │  TrajectoryRecorder                       │                   │
│  │  记录每个 Thought/Action/Observation     │                   │
│  │  持久化到 .trajectories/ 目录           │                   │
│  └─────────────────────────────────────────┘                   │
│                        ↓                                        │
│  ┌─────────────────────────────────────────┐                   │
│  │  Curator (后处理)                        │                   │
│  │                                         │                   │
│  │  1. 轨迹评估器 (TrajectoryEvaluator)    │                   │
│  │     → 分析成功/失败原因                  │                   │
│  │                                         │                   │
│  │  2. 技能合成器 (SkillSynthesizer)      │                   │
│  │     → 从成功案例提取可复用技能           │                   │
│  │                                         │                   │
│  │  3. 技能写入器 (SkillWriter)           │                   │
│  │     → 写入 ~/.skills/ 供下次使用         │                   │
│  └─────────────────────────────────────────┘                   │
│                        ↓                                        │
│  ┌─────────────────────────────────────────┐                   │
│  │  技能注册表更新                          │                   │
│  │  下次遇到类似问题 → 直接调用技能         │                   │
│  └─────────────────────────────────────────┘                   │
│  循环往复 → 系统越来越智能                                       │
└─────────────────────────────────────────────────────────────────┘
```

### 6. API 端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/v1/trajectories` | GET | 获取最近轨迹 |
| `/api/v1/trajectories/stats` | GET | 获取轨迹统计 |
| `/api/v1/trajectories/{id}/feedback` | POST | 添加用户反馈 |
| `/api/v1/skills/learned` | GET | 获取已学习技能 |

---

## 🚀 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行 Brain Service

```bash
# 规则模式（无需 API Key）
python -m brain.service

# LLM 模式
python -m brain.service --llm openai --api-key YOUR_KEY

# Docker 运行
docker-compose up -d

# 运行测试
pytest tests/unit/ -v
```

### 测试结果

```
tests/unit/brain_curator/ - 19 个测试全部通过 ✅
```

---

## 📚 文档

- [架构设计](docs/ARCHITECTURE.md)
- [任务清单](TODO.md)
- [工具系统](tools/README.md)
- [LLM 集成](llm_integration/README.md)

---

## 🧪 测试

```bash
# 运行所有测试
pytest tests/unit/ -v

# 运行自我进化测试
pytest tests/unit/brain_curator/ -v

# 查看测试覆盖
pytest tests/unit/ --cov=brain --cov-report=html
```

---

## 🐳 Docker 部署

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

---

## 📄 许可证

MIT License

---

*Handsome Agent - Hermes-Brain + OpenClaw-Body*