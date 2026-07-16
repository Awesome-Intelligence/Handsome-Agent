# Agent-Z 架构设计文档
## Hermes-Brain + OpenClaw-Body 双核驱动架构

> 融合 OpenClaw 的多渠道接入能力和 Hermes 的智能决策能力，打造企业级 AI Agent 系统

---

## 1. 架构概览

### 1.1 设计理念

本系统采用 **三层分层解耦架构**，每层各取所长：

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
│  │  │ 记忆检索层   │  │ 技能匹配层   │  │ 上下文压缩   ││    │
│  │  │ (SQLite+FTS5)│  │ (~/.skills/) │  │ (Summarizer)││    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘│    │
│  └─────────────────────────────┬───────────────────────┘    │
│                                │ (Tool Call 指令)           │
│  ┌─────────────────────────────▼───────────────────────┐    │
│  │  后处理层：Curator (异步)                           │    │
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

### 1.2 核心设计原则

1. **分层解耦**：每一层都是独立的服务，通过标准化接口通信
2. **Brain-Service 化**：Hermes Core 封装为 HTTP/RPC 服务
3. **Tool Schema 对齐**：Hermes 负责"想"，Executor 负责"做"
4. **异步后处理**：Curator 异步处理轨迹评估和技能学习
5. **安全沙箱**：执行层使用 Docker/VM 隔离

---

## 2. 项目目录结构

```
Agent-Z/
├── # 三层架构核心
├── adapter/                    # 接入层 (Adapter Layer)
│   ├── __init__.py
│   ├── gateway.py            # Gateway 核心（抽象接口）
│   ├── adapters/              # 具体渠道适配器
│   │   ├── __init__.py
│   │   ├── http_adapter.py  # HTTP/WebSocket
│   │   ├── cli_adapter.py    # 命令行
│   │   └── webhook_adapter.py # Webhook
│   └── protocols/            # 通信协议定义
│       ├── __init__.py
│       └── message.proto    # Protobuf 消息格式
│
├── brain/                     # 决策层 (Brain Layer)
│   ├── __init__.py
│   ├── service.py           # Brain Service 主入口
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── agent_loop.py    # 核心 Agent Loop (ReAct)
│   │   ├── tools.py         # Tool Registry
│   │   └── schemas.py      # Tool Schema 定义
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── vector_store.py  # 向量存储 (embedding)
│   │   ├── sqlite_store.py  # SQLite + FTS5
│   │   └── summarizer.py    # 上下文压缩
│   ├── skills/
│   │   ├── __init__.py
│   │   ├── matcher.py       # 技能匹配
│   │   ├── loader.py        # 技能加载 (~/.skills/)
│   │   └── registry.py      # 技能注册表
│   └── curator/
│       ├── __init__.py
│       ├── synthesizer.py   # 技能提炼
│       └── writer.py        # Skill DB 写入
│
├── executor/                  # 执行层 (Executor Layer)
│   ├── __init__.py
│   ├── base.py              # Executor 基类
│   ├── shell_executor.py    # Local Shell 执行器
│   ├── docker_executor.py   # Docker 沙箱执行器
│   ├── ssh_executor.py      # SSH 远程执行器
│   └── computer_use.py      # OpenClaw Computer Use
│
├── # Tool Schema 对齐层（关键）
├── tools/
│   ├── __init__.py
│   ├── schema_registry.py   # 统一的 Tool Schema 注册表
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── hermes_adapter.py    # Hermes Tool → 通用 Schema
│   │   └── openclaw_adapter.py  # OpenClaw Tool → 通用 Schema
│   └── definitions/        # 标准化的 Tool Schema
│       ├── __init__.py
│       ├── file_tools.py
│       ├── shell_tools.py
│       ├── web_tools.py
│       └── computer_tools.py
│
├── # 共享模块
├── shared/
│   ├── __init__.py
│   ├── config.py           # 配置管理
│   ├── logging.py          # 日志配置
│   ├── exceptions.py      # 公共异常
│   └── models.py          # 公共数据模型
│
├── # API 和文档
├── api/
│   └── brain_service.yaml  # OpenAPI 规范
│
├── tests/                   # 测试
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── docs/
│   └── ARCHITECTURE.md     # 本文档
│
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## 3. 核心模块设计

### 3.1 接入层 (Adapter Layer)

#### Gateway 核心职责
- 接收来自各个渠道的消息（WhatsApp/Telegram/Slack/CLI/WebSocket）
- 统一消息格式转换为标准 JSON
- 处理鉴权、会话管理、多端同步
- **关键改造**：不直接调用 Agent，而是发 HTTP/RPC 到 Brain Service

#### 标准消息格式
```json
{
  "message_id": "uuid",
  "channel": "telegram",
  "user_id": "user123",
  "session_id": "session456",
  "content": {
    "type": "text",
    "text": "帮我写一个排序算法"
  },
  "metadata": {
    "timestamp": "2024-01-01T00:00:00Z",
    "language": "zh"
  }
}
```

### 3.2 决策层 (Brain Layer)

#### Agent Loop 核心流程 (ReAct)
```
Thought → Action → Observation → Thought → ...
```

#### Memory Layer
- **向量存储**：使用 embedding 模型进行语义检索
- **SQLite + FTS5**：支持全文搜索的历史对话
- **上下文压缩**：当上下文过长时，使用 Summarizer 压缩

#### Skills Layer
- **技能目录**：`~/.skills/` 目录下的可执行脚本
- **技能匹配**：根据用户意图匹配合适的技能
- **技能注册表**：维护技能的元数据和调用接口

#### Curator Layer (异步)
- **轨迹评估**：评估每次 Tool Call 的效果
- **技能提炼**：从成功案例中提取可复用的技能
- **Skill DB 写入**：将新技能写入数据库

### 3.3 执行层 (Executor Layer)

#### Executor 接口定义
```python
class BaseExecutor(ABC):
    @abstractmethod
    async def execute(self, tool_call: ToolCall) -> ExecutionResult:
        """执行工具调用，返回执行结果"""
        pass
    
    @abstractmethod
    async def validate(self, tool_call: ToolCall) -> bool:
        """验证工具调用是否安全"""
        pass
```

#### 执行器类型
| 执行器 | 用途 | 隔离级别 |
|--------|------|---------|
| ShellExecutor | 本地命令执行 | 低（需配合白名单） |
| DockerExecutor | Docker 容器隔离 | 中 |
| SSHExecutor | 远程机器执行 | 中 |
| ComputerUseExecutor | GUI 自动化（OpenClaw） | 高（VM 级别） |

### 3.4 Tool Schema 对齐层（关键）

#### 设计目标
- Hermes 负责"想"（生成 Tool Call 意图）
- Executor 负责"做"（实际执行工具）
- 两边 Schema 互不依赖，通过 Adapter 层转换

#### 统一 Tool Schema
```python
class ToolCall(BaseModel):
    tool_name: str                    # 工具名称（通用）
    parameters: Dict[str, Any]         # 参数（标准化）
    reasoning: str                     # 思考过程
    confidence: float                  # 置信度
    safety_level: SafetyLevel          # 安全级别

class ToolSchema(BaseModel):
    name: str                          # 工具名称
    description: str                    # 工具描述
    parameters: JSONSchema              # 参数 schema
    returns: JSONSchema                 # 返回值 schema
    examples: List[ToolCallExample]     # 使用示例
```

---

## 4. 通信协议设计

### 4.1 Adapter → Brain Service
```
HTTP POST /api/v1/process
Content-Type: application/json

{
  "message": { ... },
  "context": {
    "conversation_history": [...],
    "user_profile": {...}
  }
}
```

### 4.2 Brain Service → Executor
```
HTTP POST /api/v1/execute
Content-Type: application/json

{
  "tool_call": {
    "tool_name": "file_edit",
    "parameters": {
      "file_path": "/path/to/file.py",
      "edits": [...]
    }
  },
  "executor_type": "docker",
  "safety_policy": "strict"
}
```

### 4.3 Executor → Brain Service
```
HTTP POST /api/v1/execution_result
Content-Type: application/json

{
  "execution_id": "uuid",
  "status": "success|error",
  "result": {...},
  "logs": [...],
  "metrics": {
    "execution_time_ms": 123
  }
}
```

---

## 5. 安全设计

### 5.1 分层安全策略

| 层级 | 安全措施 |
|------|---------|
| 接入层 | API Key / OAuth / 速率限制 |
| 决策层 | 输入验证 / Prompt Injection 检测 |
| 执行层 | Docker 隔离 / 命令白名单 / 权限控制 |

### 5.2 命令白名单示例
```yaml
allowed_commands:
  - git
  - npm
  - pip
  - python
  - mkdir
  - rm:  # 需要确认
  - chmod:  # 需要确认

blocked_patterns:
  - ".* --no-sandbox.*"
  - "curl.*\|.*sh"
  - ".*\.env.*"
```

---

## 6. 实现路线图

### Phase 1: 核心框架搭建
- [x] 设计架构文档
- [ ] 创建项目目录结构
- [ ] 实现 Brain Service 基本框架
- [ ] 实现 Tool Schema Registry

### Phase 2: 决策层实现
- [ ] 实现 Agent Loop (ReAct)
- [ ] 实现 Memory Layer
- [ ] 实现 Skills Matcher
- [ ] 实现 Curator (基础版)

### Phase 3: 执行层实现
- [ ] 实现 Base Executor 接口
- [ ] 实现 Shell Executor
- [ ] 实现 Docker Executor
- [ ] 实现 Computer Use Executor

### Phase 4: 接入层实现
- [ ] 实现 HTTP/WebSocket Gateway
- [ ] 实现 CLI Adapter
- [ ] 实现多渠道消息统一格式

### Phase 5: 集成与测试
- [ ] End-to-End 测试
- [ ] 性能测试
- [ ] 安全审计
- [ ] 文档完善

---

## 7. 技术选型

| 组件 | 技术选型 | 说明 |
|------|---------|------|
| 语言 | Python 3.11+ | 主开发语言 |
| Web 框架 | FastAPI | Brain Service API |
| 数据库 | SQLite + FTS5 | 轻量级存储 |
| 向量检索 | ChromaDB / Qdrant | 语义检索（可选） |
| 异步任务 | Celery / Redis | Curator 后处理 |
| 容器化 | Docker | 沙箱隔离 |
| RPC | gRPC | 内部服务通信 |
| 配置管理 | Pydantic Settings | 类型安全配置 |

---

## 8. 参考资料

- **Hermes Agent**: https://github.com/AICadet/hermes
- **OpenClaw**: https://github.com/pietervdvn/OpenClaw
- **LangChain Agent**: ReAct 实现参考
- **AutoGPT**: Tool Calling 实现参考

---

*文档版本: v1.0*
*最后更新: 2024*