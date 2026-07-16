# Agent-Z API 规范

**版本**: v1.0.0  
**最后更新**: 2026-06-09  
**状态**: 正式版

---

## 目录

1. [概述](#一概述)
2. [认证](#二认证)
3. [通用规范](#三通用规范)
4. [对话 API](#四对话-api)
5. [会话 API](#五会话-api)
6. [错误码](#六错误码)

---

## 一、概述

### 1.1 API 基础信息

| 项目 | 说明 |
|------|------|
| 基础 URL | `http://localhost:8080/api/v1` |
| 内容类型 | `application/json` |
| 字符编码 | UTF-8 |
| 时间格式 | ISO 8601 (RFC 3339) |

### 1.2 请求格式

```bash
# 标准请求格式
curl -X <METHOD> <URL> \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '<JSON_BODY>'
```

---

## 二、认证

### 2.1 Bearer Token

```bash
# 请求示例
curl -X GET http://localhost:8080/api/v1/sessions \
  -H "Authorization: Bearer your-api-key"
```

### 2.2 API Key 配置

启动 Gateway 时指定 API Key：
```bash
python -m gateway --api-key your-api-key
```

---

## 三、通用规范

### 3.1 通用响应格式

**成功响应**：

```json
{
  "success": true,
  "data": { },
  "timestamp": "2026-06-09T12:00:00Z"
}
```

**错误响应**：

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述",
    "details": {}
  },
  "timestamp": "2026-06-09T12:00:00Z"
}
```

---

## 四、对话 API

### 4.1 发送对话

```
POST /api/v1/chat
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| message | string | ✅ | 用户消息 |
| session_id | string | ❌ | 会话 ID，不指定则自动创建 |
| use_react | boolean | ❌ | 是否使用 ReAct 模式 |

**请求示例**：

```bash
curl -X POST http://localhost:8080/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "message": "帮我读取 /tmp/test.txt 文件",
    "session_id": "optional-session-id"
  }'
```

**响应示例**：

```json
{
  "success": true,
  "data": {
    "session_id": "abc-123",
    "content": "文件内容是：Hello World",
    "tool_used": "file_read",
    "confidence_score": 0.95,
    "execution_time": 0.5
  },
  "timestamp": "2026-06-09T12:00:00Z"
}
```

### 4.2 流式对话

```
POST /api/v1/chat/stream
```

**请求参数**：同 4.1

**响应**：Server-Sent Events (SSE)

```bash
curl -X POST http://localhost:8080/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{"message": "写一首诗"}'
```

**SSE 响应格式**：

```
data: {"type": "start", "session_id": "abc-123"}

data: {"type": "chunk", "content": "春风"}

data: {"type": "chunk", "content": "吹绿"}

data: {"type": "end", "final": true}
```

---

## 五、会话 API

### 5.1 获取会话列表

```
GET /api/v1/sessions
```

**查询参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| page | int | 页码 (从 1 开始) |
| page_size | int | 每页数量 (默认: 20) |

**响应示例**：

```json
{
  "success": true,
  "data": {
    "sessions": [
      {
        "id": "abc-123",
        "user_id": "user-001",
        "status": "active",
        "created_at": "2026-06-09T10:00:00Z",
        "last_active": "2026-06-09T12:00:00Z",
        "message_count": 15
      }
    ],
    "total": 10,
    "page": 1,
    "page_size": 20
  }
}
```

### 5.2 获取会话详情

```
GET /api/v1/sessions/{id}
```

**响应示例**：

```json
{
  "success": true,
  "data": {
    "id": "abc-123",
    "user_id": "user-001",
    "status": "active",
    "created_at": "2026-06-09T10:00:00Z",
    "last_active": "2026-06-09T12:00:00Z",
    "message_count": 15,
    "messages": [
      {
        "role": "user",
        "content": "你好",
        "timestamp": "2026-06-09T10:00:00Z"
      },
      {
        "role": "assistant",
        "content": "你好！有什么可以帮助你的吗？",
        "timestamp": "2026-06-09T10:00:01Z"
      }
    ]
  }
}
```

### 5.3 删除会话

```
DELETE /api/v1/sessions/{id}
```

**响应示例**：

```json
{
  "success": true,
  "data": {
    "deleted": true
  }
}
```

### 5.4 获取工具列表

```
GET /api/v1/tools
```

**响应示例**：

```json
{
  "success": true,
  "data": {
    "tools": [
      {
        "name": "file_read",
        "description": "读取文件内容",
        "category": "file",
        "parameters": {
          "type": "object",
          "properties": {
            "path": {
              "type": "string",
              "description": "文件路径"
            }
          },
          "required": ["path"]
        }
      }
    ],
    "total": 50
  }
}
```

### 5.5 健康检查

```
GET /api/v1/health
```

**响应示例**：

```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "version": "3.0.0",
    "timestamp": "2026-06-09T12:00:00Z",
    "services": {
      "llm": "connected",
      "session": "active",
      "tools": "available"
    }
  }
}
```

---

## 六、错误码

### 6.1 错误码列表

| 错误码 | 名称 | HTTP 状态码 | 说明 |
|--------|------|-------------|------|
| 1000 | `VALIDATION_ERROR` | 400 | 请求参数验证失败 |
| 1001 | `INVALID_MESSAGE` | 400 | 消息格式错误 |
| 2000 | `SESSION_NOT_FOUND` | 404 | 会话不存在 |
| 2001 | `TOOL_NOT_FOUND` | 404 | 工具不存在 |
| 3000 | `SESSION_LIMIT_EXCEEDED` | 429 | 会话数量超限 |
| 4000 | `LLM_ERROR` | 500 | LLM 调用失败 |
| 4001 | `TOOL_EXECUTION_FAILED` | 500 | 工具执行失败 |
| 4002 | `TOOL_TIMEOUT` | 504 | 工具执行超时 |
| 5000 | `UNAUTHORIZED` | 401 | 未认证 |
| 5001 | `INVALID_API_KEY` | 401 | API Key 无效 |
| 5002 | `RATE_LIMIT_EXCEEDED` | 429 | 请求频率超限 |

---

## 附录

### A. API 使用示例

**Python 示例**：

```python
import httpx

class AgentZClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_key}"}
    
    async def chat(self, message: str, session_id: str = None):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/chat",
                json={"message": message, "session_id": session_id},
                headers=self.headers
            )
            return response.json()
    
    async def get_sessions(self):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/sessions",
                headers=self.headers
            )
            return response.json()
```

### B. 限流说明

| 端点类型 | 限制 |
|----------|------|
| 读操作 | 100 次/分钟 |
| 写操作 | 50 次/分钟 |
| 对话请求 | 30 次/分钟 |

### C. 变更日志

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0.0 | 2026-06-09 | 初始版本 |

---

**版权声明**: 本文档采用 MIT 许可证开源。

**最后更新**: 2026-06-09