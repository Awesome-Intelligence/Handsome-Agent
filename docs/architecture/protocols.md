# 协议架构设计文档

> 定义 Agent-Z 中各种通信协议的组织方式和职责划分

---

## 1. 协议概述

Agent-Z 支持多种通信协议，用于不同的通信场景：

| 协议 | 全称 | 用途 | 成熟度 |
|------|------|------|--------|
| **ACP** | Agent Communication Protocol | Agent ↔ Agent 通信 | ✅ 成熟 |
| **MCP** | Model Context Protocol | Agent ↔ 工具/服务 通信 | ✅ 成熟 |
| **OpenAI API** | OpenAI Compatible API | 前端 ↔ Agent 通信 | ✅ 成熟 |
| **A2A** | Agent-to-Agent Protocol | 多 Agent 协作 (Google) | 🔄 进行中 |

---

## 2. 目录结构

```
Agent-Z/
│
├── agent/                    # 🧠 Decision
│   ├── acp/                 #   💾 Memory - ACP 协议
│   │   ├── __init__.py     #     模块入口
│   │   ├── adapter.py      #     ACP 服务器
│   │   ├── session.py      #     会话管理
│   │   ├── transport.py    #     传输层 (stdio/HTTP/WebSocket)
│   │   ├── tools.py        #     ACP 工具
│   │   └── README.md       #     模块文档
│   │
│   ├── transports/          #   🤖 LLM - 模型传输适配器 (待实现)
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── anthropic.py
│   │   ├── openai.py
│   │   └── types.py
│   │
│   ├── lsp/                 #   🔧 ToolSelect - LSP 协议 (待实现)
│   │   ├── __init__.py
│   │   ├── client.py
│   │   ├── manager.py
│   │   └── protocol.py
│   │
│   └── ...其他核心代码
│
├── tools/                    # 🏃 Execution - 🛠️ ToolExec
│   ├── mcp_tool.py          #   MCP 工具集成
│   └── ...
│
└── gateway/                  # 🚪 Access - 🚪 Gateway
    ├── adapters/            #   渠道适配器
    │   ├── __init__.py
    │   ├── http_adapter.py  #   HTTP 适配器
    │   ├── cli_adapter.py   #   CLI 适配器
    │   └── openai_adapter.py #  OpenAI 兼容 API (2026-06-26 从 api/ 迁移)
    ├── platforms/           #   消息平台适配器 (待清理)
    └── ...
```

---

## 3. 协议设计原则

### 3.1 组织方式分类

| 类型 | 特点 | 组织方式 |
|------|------|---------|
| **通信协议** (ACP, LSP, A2A) | 独立运行、代码量大、接口复杂 | **独立目录** |
| **传输适配** (Transports) | 底层接口、抽象层、多提供商 | **模块子目录** |
| **平台适配** (Gateway platforms) | 按平台类型隔离 | **按平台分组** |
| **工具集成** (MCP) | 作为工具使用，功能单一 | **融合到 tools/** |

### 3.2 分层归属

| 协议 | Layer | Sublayer | 说明 |
|------|-------|----------|------|
| ACP | 🧠 Decision | 💾 Memory | Agent 通信协议 |
| MCP | 🏃 Execution | 🛠️ ToolExec | 工具集成协议 |
| OpenAI API | 🚪 Access | 🚪 Gateway | 前端通信协议 |
| LSP | 🧠 Decision | 🔧 ToolSelect | IDE 集成协议 |
| A2A | 🧠 Decision | 💾 Memory | 多 Agent 协作 |

---

## 4. 各协议详细设计

### 4.1 ACP (Agent Communication Protocol)

**用途**: Agent 与 Agent 之间、Agent 与编辑器之间的通信

**位置**: `agent/acp/`

**传输支持**:
- stdio - 终端集成
- HTTP - 远程调用
- WebSocket - 双向流

**核心方法**:
```
initialize         - 初始化连接
ping              - 心跳检测
session/new       - 创建新会话
session/load       - 加载会话
session/prompt     - 发送提示
session/cancel     - 取消操作
session/list       - 列出会话
session/delete     - 删除会话
tools/list         - 列出工具
fs/read_text_file  - 读取文件
fs/write_text_file - 写入文件
```

### 4.2 MCP (Model Context Protocol)

**用途**: Agent 调用外部工具和服务

**位置**: `tools/mcp_tool.py`

**传输支持**:
- stdio - 本地 MCP 服务器
- HTTP/StreamableHTTP - 远程 MCP 服务器
- SSE - 服务端发送事件

**核心功能**:
- 工具发现和调用
- 资源访问
- 采样支持 (LLM 请求)

### 4.3 OpenAI API

**用途**: 前端应用 (Open WebUI, LobeChat 等) 调用 Agent

**位置**: `api/`

**端点**:
```
GET  /health              - 健康检查
GET  /health/detailed     - 详细状态
GET  /v1/models          - 模型列表
GET  /v1/capabilities     - API 能力
POST /v1/chat/completions - 聊天补全
POST /v1/responses       - 响应 API
POST /v1/runs            - 异步运行
GET  /v1/runs/{id}      - 运行状态
```

### 4.4 LSP (Language Server Protocol) [待实现]

**用途**: IDE 集成、代码智能

**位置**: `agent/lsp/`

**核心功能**:
- 补全建议
- 跳转定义
- 诊断信息
- 代码操作

### 4.5 A2A (Agent-to-Agent Protocol) [待实现]

**用途**: 多 Agent 协作

**位置**: `agent/a2a/` (待创建)

**核心功能**:
- Agent 发现
- 任务委托
- 结果聚合

---

## 5. 传输层设计

### 5.1 传输类型

| 传输 | 适用协议 | 特点 |
|------|---------|------|
| stdio | ACP, MCP | 本地集成、低延迟 |
| HTTP | ACP, MCP, OpenAI API | 远程调用、跨平台 |
| WebSocket | ACP, OpenAI API | 双向流、实时通信 |
| SSE | MCP, OpenAI API | 服务端推送 |
| gRPC | A2A (待实现) | 高性能 RPC |

### 5.2 传输抽象

```python
class Transport(ABC):
    """传输层抽象基类"""

    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...

    @abstractmethod
    async def send(self, message: Dict) -> None: ...

    @abstractmethod
    async def receive(self) -> Optional[Dict]: ...
```

---

## 6. 待实现功能

| 功能 | 优先级 | 说明 |
|------|--------|------|
| ACP 完整实现 | ✅ 已完成 | 基本功能已完成 |
| MCP 增强 | ⚠️ 中 | 增强 Streamable HTTP 支持 |
| transports 模块 | ❌ 待实现 | 模型传输抽象 |
| LSP 协议 | ❌ 待实现 | IDE 集成 |
| A2A 协议 | ❌ 待实现 | 多 Agent 协作 |
| gRPC 传输 | ❌ 待实现 | 高性能 RPC |

---

## 7. 参考资料

- **Hermes ACP**: `e:\hermes-agent-study\acp_adapter\`
- **Hermes MCP**: `e:\hermes-agent-study\tools\mcp_tool.py`
- **Hermes Gateway**: `e:\hermes-agent-study\gateway\platforms\api_server.py`
- **MCP 规范**: https://modelcontextprotocol.io/
- **A2A 规范**: https://google.github.io/A2A/

---

*文档版本: v1.0 | 最后更新: 2026-06-04*
