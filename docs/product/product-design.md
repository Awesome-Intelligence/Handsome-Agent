# Agent-Z 产品设计书

**版本**: v1.0.0  
**最后更新**: 2026-06-09  
**状态**: 正式版

---

## 目录

1. [产品概述](#一产品概述)
2. [系统架构](#二系统架构)
3. [核心模块设计](#三核心模块设计)
4. [接口设计](#四接口设计)
5. [数据模型](#五数据模型)
6. [技能系统](#六技能系统)
7. [自我进化机制](#七自我进化机制)
8. [命令行工具](#八命令行工具)
9. [可观测性设计](#九可观测性设计)
10. [部署与运维](#十部署与运维)
11. [开发路线图](#十一开发路线图)

---

## 一、产品概述

### 1.1 产品定位

Agent-Z 是一个**企业级 AI Agent 系统**，采用 **Hermes-Brain + OpenClaw-Body** 双核驱动架构。

**核心价值**：
- **智能决策** - LLM 驱动的意图理解和工具选择
- **自我进化** - Curator 机制实现持续学习和优化
- **技能系统** - 完整的技能生命周期管理
- **多渠道接入** - CLI、Gateway、API Server 多端支持

### 1.2 目标用户

| 用户类型 | 使用场景 | 主要需求 |
|----------|----------|----------|
| AI 开发者 | 构建和测试 Agent | 快速开发、灵活配置、调试能力 |
| 运维工程师 | 部署和维护系统 | 稳定可靠、易于管理、监控告警 |
| 企业用户 | 使用 Agent 完成业务任务 | 简单易用、结果可信、安全可控 |

### 1.3 核心功能矩阵

| 功能 | 说明 | 优先级 |
|------|------|--------|
| **Agent 核心** | LLM 驱动的决策引擎 | P0 |
| **ReAct 模式** | 多步骤复杂任务执行 | P0 |
| **工具系统** | 50+ 预置工具覆盖全场景 | P0 |
| **会话管理** | 多会话、上下文压缩 | P0 |
| **技能系统** | 技能匹配、加载、生命周期 | P1 |
| **自我进化** | Curator 轨迹分析、技能合成 | P1 |
| **Rail 机制** | 可插拔的拦截器钩子 | P1 |
| **Gateway** | 认证、限流、统计 | P2 |
| **API Server** | OpenAI 兼容接口 | P2 |
| **A2A/ACP 协议** | 多 Agent 通信 | P2 |

### 1.4 技术选型

| 层级 | 技术 | 说明 |
|------|------|------|
| 后端框架 | Python 3.11+ | 核心语言 |
| LLM 集成 | 25+ 提供商 | OpenAI、Claude、Gemini 等 |
| 会话存储 | SQLite | 本地持久化 |
| 记忆存储 | Markdown | 可读性好 |
| 工具执行 | Shell/Docker | 安全隔离 |
| CLI | 标准库 | 无外部依赖 |
| 测试 | pytest + pytest-asyncio | 异步测试支持 |

---

## 二、系统架构

### 2.1 三层架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Agent-Z 三层架构                             │
└─────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────────┐
                              │   🚪 Access     │
                              │   接入层         │
                              │ CLI/Gateway/API │
                              └────────┬────────┘
                                       │
                              ┌────────▼────────┐
                              │   🧠 Decision    │
                              │   决策层         │
                              │                  │
                              │ ┌──────────────┐ │
                              │ │ Agent        │ │
                              │ │ ReAct Loop   │ │
                              │ └──────────────┘ │
                              │                  │
                              │ ┌────────────┐  │
                              │ │LLMProvider │  │
                              │ │(25+ 提供商) │  │
                              │ └────────────┘  │
                              │                  │
                              │ Memory │ Skills  │
                              │ Curator │ Rails  │
                              └────────┬────────┘
                                       │
                              ┌────────▼────────┐
                              │   🏃 Execution   │
                              │   执行层         │
                              │                  │
                              │ Tool Registry   │
                              │ Shell Executor  │
                              │ Docker Executor │
                              └─────────────────┘
```

### 2.2 数据流设计

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            数据流图                                     │
└─────────────────────────────────────────────────────────────────────────┘

[用户输入] ──► [Agent] ──► [模式判断] ──► [ReAct Loop / 直接响应]
                                       │
                                       ▼
                             [LLM 决策]
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
              [工具调用]         [直接回答]         [询问澄清]
                    │                  │                  │
                    ▼                  ▼                  ▼
           [Tool Registry]      [格式化响应]      [生成问题]
                    │
                    ▼
           [工具执行器]
           [Shell/Docker]
                    │
                    ▼
           [结果聚合] ──► [Curator 分析] ──► [技能进化]
```

### 2.3 模块依赖关系

```
agent/
├── agent.py           ← Agent 核心协调器
├── session.py         ← 会话管理
├── response_router.py ← 响应路由
├── self_improvement.py ← 自我改进
├── context/           ← 上下文管理
│   ├── context_engine.py
│   ├── context_compressor.py
│   └── prompt_builder.py
├── curator/           ← 自我进化
│   ├── curator.py
│   ├── trajectory.py
│   └── trajectory_recorder.py
├── llm/               ← LLM 提供商
│   ├── providers/
│   │   ├── openai.py
│   │   ├── claude.py
│   │   └── ...
├── memory/            ← 记忆存储
│   └── markdown_memory.py
├── skills/            ← 技能管理
│   └── skill_manager.py
├── react/             ← ReAct 引擎
│   └── loop.py
├── rails/             ← Rail 拦截器
│   ├── rail.py
│   └── manager.py
├── acp/               ← ACP 协议
└── a2a/               ← A2A 协议

tools/
├── registry.py        ← 工具注册表
└── definitions/       ← 工具定义
    ├── file_tools.py
    ├── shell_tools.py
    ├── web_tools.py
    └── ...
```

---

## 三、核心模块设计

### 3.1 Agent 模块

**职责**：Agent 核心协调器，统一管理会话、上下文、LLM 调用

**核心组件**：
- `Agent` - 主类，协调各模块
- `AgentResponse` - 响应数据结构
- `ActionType` - 动作类型枚举

**决策流程**：
```python
class Agent:
    async def chat(self, user_input, conversation_history=None):
        # 1. 判断使用哪种模式
        use_react = await self._should_use_react(user_input)
        
        # 2. 执行对应模式
        if use_react:
            return await self._chat_react(user_input, history)
        return await self._chat_simple(user_input, history)
```

### 3.2 ReAct 模块

**职责**：LLM 驱动的 ReAct 循环执行引擎

**核心组件**：
- `ReActLoop` - 循环引擎
- `LoopState` - 循环状态枚举
- `StepResult` - 步骤执行结果
- `Decision` - LLM 决策结果

**执行流程**：
```
1. LLM 决策下一步（工具/直接响应/询问）
     │
     ▼
2. [可选] Rail before_tool_call 拦截
     │
     ▼
3. 执行工具或生成响应
     │
     ▼
4. [可选] Rail after_tool_call 处理
     │
     ▼
5. 检查是否完成，否则继续循环
```

### 3.3 工具系统

**职责**：统一的工具注册和执行

**核心组件**：
- `ToolRegistry` - 工具注册表
- `ToolEntry` - 工具条目

**工具分类**：

| 类别 | 工具 | 说明 |
|------|------|------|
| **文件操作** | file_read, file_write, file_edit | 读写编辑文件 |
| **命令执行** | shell_execute, python_execute | Shell 和 Python |
| **网络工具** | web_search, web_extract | 搜索和抓取 |
| **浏览器** | browser_open, browser_click | 浏览器自动化 |
| **多媒体** | image_generate, text_to_speech | 图像和语音 |
| **任务管理** | todo_add, todo_list | Todo 列表 |
| **记忆** | memory_save, memory_search | 记忆存储检索 |
| **技能** | skill_register, skill_execute | 技能管理 |

### 3.4 技能系统

**职责**：技能匹配、加载、生命周期管理

**核心组件**：
- `SkillRegistry` - 技能注册表
- `SkillMatcher` - 技能匹配器
- `SkillLoader` - 技能加载器
- `LifecycleManager` - 生命周期管理

**生命周期状态**：
```
active → stale → archived
  ↑       │
  └───────┘ (重新激活)
```

### 3.5 Curator 模块

**职责**：自我进化，轨迹分析和技能合成

**核心组件**：
- `Curator` - 进化引擎
- `TrajectoryRecorder` - 轨迹记录器
- `SkillWriter` - 技能编写器

**进化流程**：
```
用户对话 → 轨迹记录 → Curator 评估 → 技能合成 → 越用越聪明
```

### 3.6 Rail 机制

**职责**：可插拔的拦截器钩子

**核心组件**：
- `Rail` - Rail 基类
- `RailManager` - Rail 管理器

**钩子类型**：
- `before_tool_call` - 工具调用前拦截
- `after_tool_call` - 工具调用后处理
- `on_task_event` - 任务事件处理

---

## 四、接口设计

### 4.1 REST API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/chat` | POST | 对话接口 |
| `/api/v1/sessions` | GET/POST | 会话管理 |
| `/api/v1/sessions/{id}/messages` | GET/POST | 消息管理 |
| `/api/v1/tools` | GET | 工具列表 |
| `/api/v1/tools/{name}/execute` | POST | 工具执行 |
| `/api/v1/health` | GET | 健康检查 |

### 4.2 CLI 命令

| 命令 | 说明 |
|------|------|
| `python -m cli.main chat` | 交互式对话 |
| `python -m cli.main setup` | 首次配置 |
| `python -m cli.main session list` | 会话列表 |
| `python -m cli.main session show <id>` | 会话详情 |
| `python -m cli.main tools list` | 工具列表 |

### 4.3 Gateway 配置

```yaml
gateway:
  host: "0.0.0.0"
  port: 8080
  auth:
    enabled: true
    api_key: "${API_KEY}"
  rate_limit:
    enabled: true
    requests_per_minute: 100
```

---

## 五、数据模型

### 5.1 会话数据模型

```python
class Session:
    session_id: str           # 会话 ID (UUID)
    user_id: str              # 用户 ID
    messages: List[Message]   # 消息列表
    created_at: datetime      # 创建时间
    last_active: datetime     # 最后活跃时间
    metadata: Dict           # 元数据
```

### 5.2 消息数据模型

```python
class Message:
    role: str                 # user/assistant/system
    content: str              # 消息内容
    timestamp: datetime       # 时间戳
    metadata: Dict            # 元数据
```

### 5.3 技能数据模型

```python
class Skill:
    name: str                 # 技能名称
    description: str         # 技能描述
    trigger: str             # 触发条件
    content: str             # 技能内容
    status: SkillStatus      # active/stale/archived
    usage_count: int         # 使用次数
    created_at: datetime      # 创建时间
    updated_at: datetime      # 更新时间
```

### 5.4 轨迹数据模型

```python
class Trajectory:
    trajectory_id: str       # 轨迹 ID
    session_id: str          # 关联会话
    steps: List[Step]        # 步骤列表
    confidence_score: float   # 置信度
    created_at: datetime     # 创建时间
```

---

## 六、技能系统

### 6.1 技能注册

```python
from skills import SkillRegistry

registry = SkillRegistry()

# 注册技能
registry.register(
    name="code_assistant",
    trigger="需要编写代码时",
    content="""
    你是一个代码助手...
    """,
    category="developer"
)
```

### 6.2 技能匹配

```python
# 匹配技能
matched = await registry.match(user_input)
if matched:
    skill = matched[0]
    # 使用技能内容处理请求
```

### 6.3 技能生命周期

```
┌─────────────────────────────────────────────────────────┐
│                    技能生命周期                          │
└─────────────────────────────────────────────────────────┘

创建 ──► active ──► stale ──► archived
              ↑       │
              └───────┘ (重新激活)
```

---

## 七、自我进化机制

### 7.1 轨迹记录

```python
from agent.curator import TrajectoryRecorder

recorder = TrajectoryRecorder()
recorder.initialize(session_id)

# 记录对话
recorder.add_human_message(user_input)
recorder.add_tool_call(tool_name, arguments, reasoning)
recorder.add_tool_response(tool_name, content)
recorder.add_gpt_message(response)

# 保存轨迹
recorder.save_trajectory()
```

### 7.2 Curator 分析

```python
from agent.curator import Curator, SkillWriter

curator = Curator(
    trajectory_recorder=recorder,
    skill_writer=SkillWriter(),
    enable_auto_learn=True
)

# 处理轨迹
result = await curator.process_trajectory(trajectory)
if result:
    # 生成新技能
    print(f"Generated skill: {result.name}")
```

### 7.3 进化策略

| 策略 | 说明 | 触发条件 |
|------|------|----------|
| 技能合成 | 从成功轨迹合成新技能 | 多次成功 |
| 技能优化 | 改进现有技能 | 失败轨迹 |
| 技能归档 | 归档不常用技能 | 长时间未使用 |

---

## 八、命令行工具

### 8.1 命令结构

```
Agent-Z
├── chat                 # 交互式对话
├── setup               # 首次配置
├── session             # 会话管理
│   ├── list           # 列出会话
│   ├── show <id>     # 查看会话
│   └── delete <id>    # 删除会话
├── tools               # 工具管理
│   ├── list           # 列出工具
│   └── execute <name> # 执行工具
└── gateway             # 网关管理
    ├── start          # 启动网关
    └── stop           # 停止网关
```

### 8.2 常用命令

```bash
# 交互式对话
python -m cli.main chat

# 新建会话
python -m cli.main chat --new-session

# 指定会话
python -m cli.main chat --session <session_id>

# 配置 LLM
python -m cli.main setup

# 启动网关
python -m gateway

# 带认证启动网关
python -m gateway --api-key KEY --rate-limit 100
```

---

## 九、可观测性设计

### 9.1 日志分层

| 日志器 | 说明 | 用途 |
|--------|------|------|
| `decision` | 决策日志 | 意图理解、模式选择 |
| `llm` | LLM 日志 | 模型调用、响应 |
| `task` | 任务日志 | 任务执行、步骤 |
| `execution` | 执行日志 | 工具调用、结果 |
| `session` | 会话日志 | 会话管理、状态 |
| `rail` | Rail 日志 | 拦截器事件 |

### 9.2 日志配置

```python
from common.logging_manager import get_logger, set_log_level

# 设置日志级别
set_log_level("INFO")  # DEBUG/INFO/WARNING/ERROR

# 获取专用日志器
logger = get_logger("Agent", sublayer="decision")
```

### 9.3 统计指标

| 指标 | 类型 | 说明 |
|------|------|------|
| `chat_requests_total` | Counter | 对话请求总数 |
| `chat_duration_seconds` | Histogram | 对话响应时间 |
| `tool_calls_total` | Counter | 工具调用次数 |
| `tool_errors_total` | Counter | 工具错误次数 |
| `active_sessions` | Gauge | 当前活跃会话数 |

---

## 十、部署与运维

### 10.1 部署模式

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| **本地开发** | 单机运行，开发调试 | 开发环境 |
| **Docker** | 容器化部署 | 小规模部署 |
| **Docker Compose** | 多服务编排 | 生产环境 |

### 10.2 环境要求

**最低配置**：
- CPU: 2 核
- 内存: 4GB
- 磁盘: 10GB

**推荐配置**：
- CPU: 4 核
- 内存: 8GB
- 磁盘: 50GB

### 10.3 数据目录

```
~/.agent_z/
├── config.json           # 配置文件
├── sessions/{date}/      # 对话历史
├── skills/user/         # 用户技能
├── memories/            # 长期记忆
├── logs/                # 日志文件
└── agentz.db    # SQLite 数据库
```

### 10.4 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `AGENT_Z_HOME` | 数据目录 | `~/.agent_z` |
| `AGENTZ_LLM_PROVIDER` | LLM 提供商 | - |
| `AGENTZ_LLM_API_KEY` | API Key | - |
| `AGENTZ_LOG_LEVEL` | 日志级别 | `INFO` |

---

## 十一、开发路线图

### 11.1 版本规划

| 版本 | 目标 | 里程碑 |
|------|------|--------|
| **v3.x** | **当前版本** | 三层架构、ReAct、工具系统 |
| v4.0 | 技能生态系统 | 技能市场、技能评分 |
| v4.1 | 高级协作 | A2A/ACP 协议增强 |
| v5.0 | 企业特性 | 多租户、审计日志 |

### 11.2 开发阶段

#### Phase 1: 核心能力 (已完成)
- [x] 三层架构
- [x] LLM 集成
- [x] ReAct 引擎
- [x] 工具系统

#### Phase 2: 智能进化 (已完成)
- [x] 技能系统
- [x] Curator 机制
- [x] 轨迹记录
- [x] Rail 拦截器

#### Phase 3: 企业特性 (进行中)
- [ ] 多租户支持
- [ ] 审计日志
- [ ] 权限管理
- [ ] 高可用部署

#### Phase 4: 生态系统 (规划中)
- [ ] 技能市场
- [ ] 插件系统
- [ ] 云端同步
- [ ] 团队协作

---

## 附录

### A. 术语表

| 术语 | 说明 |
|------|------|
| ReAct | Reasoning + Acting，推理和行动结合的执行模式 |
| Curator | Curator 进化引擎，负责轨迹分析和技能合成 |
| Rail | 可插拔的拦截器，用于权限控制、事件追踪等 |
| Skill | 技能，一段可复用的提示词或代码 |
| Trajectory | 轨迹，一次完整交互的执行路径记录 |

### B. 参考资料

- [Hermes Agent](https://github.com/handong1587/hermes-agent)
- [OpenClaw](https://github.com/handong1587/openclaw)
- [ReAct 论文](https://arxiv.org/abs/2210.03629)

### C. 变更日志

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0.0 | 2026-06-09 | 初始版本，参考 AgentZoo 文档结构 |

---

**版权声明**: 本文档采用 MIT 许可证开源。

**最后更新**: 2026-06-09
