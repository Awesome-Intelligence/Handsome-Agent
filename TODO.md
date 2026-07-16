# Agent-Z 待办事项

> 最后更新: 2026-06-04

---

## 协议相关

### ACP (Agent Communication Protocol) ✅

- [x] 创建 `agent/acp/` 模块
- [x] 实现 `adapter.py` - ACP 服务器
- [x] 实现 `session.py` - 会话管理
- [x] 实现 `transport.py` - 传输层
- [x] 实现 `tools.py` - 工具映射系统
- [x] 实现 `auth.py` - 认证方法检测
- [x] 实现 `events.py` - 事件回调系统
- [x] 实现 `permissions.py` - 权限审批系统
- [x] 实现 `entry.py` - CLI 入口
- [x] 更新 `agent/acp_adapter.py` 使用新模块
- [x] 更新 `__init__.py` - 模块入口
- [x] 添加单元测试
- [x] 更新 README
- [x] 更新 docs 架构文档

**状态**: ✅ 已完成

### OpenAI 兼容 API ✅

- [x] 创建 `api/` 模块 [已废弃]
- [x] 实现 `api_server.py` - OpenAI 兼容 API [已迁移到 gateway/adapters/]
- [x] 实现 `server.py` - CLI 入口 [已迁移到 gateway/gateway_cli.py]
- [x] 更新 `brain_service.yaml` - OpenAPI 规范 [已删除]
- [x] 创建 Gateway 平台适配器
- [x] 添加单元测试

**状态**: ✅ 已完成

### MCP (Model Context Protocol) ⚠️

- [x] 基础实现 (已有 `tools/mcp_tool.py`)
- [ ] 增强 Streamable HTTP 支持
- [ ] 增强 SSE 传输支持
- [ ] 添加采样 (sampling) 支持
- [ ] 完善 OAuth 认证

**状态**: ⚠️ 部分完成

### transports 模块 ❌

- [ ] 创建 `agent/transports/` 目录
- [ ] 实现 `base.py` - 传输基类
- [ ] 实现 `openai.py` - OpenAI 传输
- [ ] 实现 `anthropic.py` - Anthropic 传输
- [ ] 实现类型定义

**状态**: ❌ 待实现

### LSP (Language Server Protocol) ❌

- [ ] 创建 `agent/lsp/` 目录
- [ ] 实现 `protocol.py` - LSP 协议
- [ ] 实现 `client.py` - LSP 客户端
- [ ] 实现 `manager.py` - LSP 管理器

**状态**: ❌ 待实现

### A2A (Agent-to-Agent Protocol) ❌

- [ ] 创建 `agent/a2a/` 目录
- [ ] 实现 Agent 发现机制
- [ ] 实现任务委托
- [ ] 实现结果聚合

**状态**: ❌ 待实现

---

## ACP 模块文件清单

```
agent/acp/
├── __init__.py       # 模块入口，导出所有公共 API
├── adapter.py       # ACP 服务器核心
├── session.py       # 会话管理
├── transport.py     # 传输层 (stdio/HTTP/WebSocket)
├── tools.py         # 工具映射和注册
├── auth.py          # 认证方法检测
├── events.py        # 事件回调系统
├── permissions.py    # 权限审批系统
├── entry.py         # CLI 入口
└── README.md        # 模块文档
```

### 模块说明

| 文件 | 说明 | 状态 |
|------|------|------|
| adapter.py | ACPServer 类，处理 JSON-RPC 请求 | ✅ |
| session.py | SessionManager 会话持久化 | ✅ |
| transport.py | StdioTransport, HttpTransport, WebSocketTransport | ✅ |
| tools.py | 工具映射，ACPToolRegistry 注册表 | ✅ |
| auth.py | detect_provider, build_auth_methods | ✅ |
| events.py | ACPSessionNotifier, 事件回调工厂 | ✅ |
| permissions.py | PermissionManager 权限审批 | ✅ |
| entry.py | CLI 入口，支持 stdio/http | ✅ |

---

## 文档相关

- [x] 创建 `docs/architecture/protocols.md` - 协议架构文档
- [x] 更新 README - 添加 acp/ 目录
- [x] 更新 agent/acp/README.md - ACP 模块文档
- [ ] 更新 flows.md - 添加协议流程
- [ ] 更新 rule.md - 添加协议规范

---

## 测试相关

- [x] ACP 单元测试 - `tests/agent/acp/test_acp.py`
- [x] API 单元测试 - `tests/api/test_api_server.py`
- [ ] MCP 集成测试
- [ ] 传输层测试

---

## 代码质量

- [x] 所有新代码通过语法检查
- [ ] 添加 type hints 到所有新代码
- [ ] 添加 docstrings 到公共 API
- [ ] 运行 lint 检查
