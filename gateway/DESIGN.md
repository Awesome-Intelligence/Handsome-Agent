# 🔐 Gateway - API网关详细设计文档

> **版本**: 1.0.0  
> **参考项目**: Hermes Agent, Kong Gateway, Express.js  
> **设计目标**: 企业级安全、高性能、易扩展

---

## 📋 目录

1. [模块概述](#1-模块概述)
2. [设计哲学](#2-设计哲学)
3. [架构设计](#3-架构设计)
4. [中间件系统](#4-中间件系统)
5. [安全设计](#5-安全设计)
6. [API参考](#6-api参考)
7. [部署指南](#7-部署指南)
8. [运维监控](#8-运维监控)

---

## 1. 模块概述

### 1.1 什么是Gateway？

**Gateway** 是 Handsome Agent 的企业级网关模块，提供：

| 功能 | 描述 | 参考来源 |
|------|------|----------|
| **认证** | API Key验证 | Hermes Agent |
| **限流** | Token Bucket算法 | Kong Gateway |
| **统计** | 请求监控 | Prometheus |
| **CORS** | 跨域请求处理 | Express.js |
| **日志** | 请求日志记录 | 标准日志最佳实践 |

### 1.2 为什么需要Gateway？

```
┌─────────────────────────────────────────────┐
│           Without Gateway                    │
├─────────────────────────────────────────────┤
│                                             │
│   User ──► Agent ──► Response               │
│                                             │
│   问题:                                       │
│   ❌ 无认证 - 任何人都可以访问               │
│   ❌ 无限流 - 可能被滥用                     │
│   ❌ 无监控 - 不知道谁在使用                  │
│                                             │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│           With Gateway                      │
├─────────────────────────────────────────────┤
│                                             │
│   User ──► Gateway ──► Agent ──► Response   │
│              │  │  │                        │
│              │  │  └─ 统计收集             │
│              │  └──── 限流检查              │
│              └───────── 认证验证             │
│                                             │
└─────────────────────────────────────────────┘
```

### 1.3 核心特性

| 特性 | 描述 | 性能 |
|------|------|------|
| **零依赖** | 仅使用Python标准库 | - |
| **高性能** | < 10ms延迟 | < 10ms |
| **高并发** | 1000+ 并发连接 | 1000 req/s |
| **安全** | 企业级认证 | - |
| **可观测** | 实时统计 | - |

---

## 2. 设计哲学

### 2.1 Hermes Agent理念

**参考来源**: Hermes Enterprise AI Agent

**核心理念**:

> "Security is not an add-on, it's a foundation."

**设计原则**:

1. **纵深防御** - 多层安全检查
2. **最小权限** - 按需授权
3. **可观测性** - 全面监控
4. **容错设计** - 优雅降级

### 2.2 Kong Gateway模式

**参考来源**: Kong API Gateway开源项目

**借鉴的模式**:

| Kong特性 | Gateway实现 | 说明 |
|----------|------------|------|
| Plugin Architecture | Middleware | 中间件链 |
| Rate Limiting | Token Bucket | 限流算法 |
| Authentication | API Key | 认证方式 |
| Analytics | Stats Collector | 统计分析 |

### 2.3 Express.js中间件

**参考来源**: Express.js Web框架

**中间件模式**:

```python
# Express风格的中间件链
class Gateway:
    def __init__(self):
        self.middlewares = []
    
    def use(self, middleware):
        """注册中间件"""
        self.middlewares.append(middleware)
    
    async def handle(self, request):
        """中间件链处理"""
        ctx = {"request": request}
        
        for middleware in self.middlewares:
            result = await middleware.process(ctx)
            if not result["allowed"]:
                return result
        
        return await self.agent.respond(ctx["request"])
```

---

## 3. 架构设计

### 3.1 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Gateway架构                           │
├─────────────────────────────────────────────────────────────┤
│                                                      │
│  ┌─────────────────────────────────────────────┐        │
│  │            HTTP Server (Python)            │        │
│  │                                              │        │
│  │  BaseHTTPRequestHandler                    │        │
│  │  └─► do_GET()                             │        │
│  │  └─► do_POST()                            │        │
│  │  └─► do_OPTIONS()                         │        │
│  └─────────────────────────────────────────────┘        │
│                      │                                  │
│                      ▼                                  │
│  ┌─────────────────────────────────────────────┐        │
│  │           Middleware Chain                   │        │
│  │                                              │        │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  │        │
│  │  │   CORS   │→ │  Stats   │→ │   Auth   │→ │        │        │
│  │  └──────────┘  └──────────┘  └──────────┘  │        │
│  │                                              │        │
│  │  ┌──────────┐                               │        │
│  │  │  Rate    │                               │        │
│  │  │  Limit   │                               │        │
│  │  └──────────┘                               │        │
│  └─────────────────────────────────────────────┘        │
│                      │                                  │
│                      ▼                                  │
│  ┌─────────────────────────────────────────────┐        │
│  │            Agent (Lightweight)               │        │
│  │                                              │        │
│  │  ┌──────────────────────────────────────┐  │        │
│  │  │         Agent.respond()                │  │        │
│  │  └──────────────────────────────────────┘  │        │
│  └─────────────────────────────────────────────┘        │
│                      │                                  │
│                      ▼                                  │
│  ┌─────────────────────────────────────────────┐        │
│  │            Response Builder                   │        │
│  └─────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 请求流程

```
Client Request
    │
    ▼
┌────────────────┐
│ 1. Parse      │ ◄── BaseHTTPRequestHandler
│    Request    │
└────────────────┘
    │
    ▼
┌────────────────┐
│ 2. CORS       │ ◄── 跨域处理
│    Check      │
└────────────────┘
    │
    ▼
┌────────────────┐
│ 3. Stats      │ ◄── 统计收集
│    Record     │
└────────────────┘
    │
    ▼
┌────────────────┐
│ 4. Auth       │ ◄── API Key验证
│    Check      │
└────────────────┘
    │
    ▼
┌────────────────┐
│ 5. Rate      │ ◄── 限流检查
│    Limit     │
└────────────────┘
    │
    ▼
┌────────────────┐
│ 6. Agent      │ ◄── 核心处理
│    Process    │
└────────────────┘
    │
    ▼
Response
```

### 3.3 中间件链设计

**参考来源**: Express.js和Kong的中间件模式

```python
class MiddlewareChain:
    """中间件链管理器"""
    
    def __init__(self):
        self.middlewares = []
    
    def add(self, middleware):
        """添加中间件"""
        self.middlewares.append(middleware)
        return self  # 支持链式调用
    
    async def execute(self, request):
        """执行中间件链"""
        context = {"request": request}
        
        for middleware in self.middlewares:
            result = await middleware.process(context)
            
            # 如果中间件拒绝请求
            if result.get("allowed") == False:
                return {
                    "allowed": False,
                    "status": result.get("status", 401),
                    "body": result.get("body", {"error": "Unauthorized"})
                }
            
            # 传递上下文
            context.update(result)
        
        return {
            "allowed": True,
            "context": context
        }
```

---

## 4. 中间件系统

### 4.1 认证中间件

**设计参考**: Hermes Agent的认证机制

```python
class AuthMiddleware:
    """API Key认证中间件
    
    参考来源: Hermes Agent的API Key验证
    
    设计特点:
    - 支持多个API Key
    - Key格式灵活
    - 详细的错误消息
    """
    
    def __init__(self, config: GatewayConfig):
        self.config = config
        self.api_keys = set(config.api_keys or [])
    
    async def process(self, context: dict) -> dict:
        """处理认证检查"""
        request = context.get("request", {})
        api_key = request.get("headers", {}).get("X-API-Key", "")
        
        # 禁用认证时直接通过
        if not self.config.enable_auth:
            return {"allowed": True}
        
        # 验证API Key
        if api_key in self.api_keys:
            return {"allowed": True}
        
        # 无效的Key
        return {
            "allowed": False,
            "status": 401,
            "body": {
                "error": "Unauthorized",
                "message": "Invalid or missing API key"
            }
        }
```

### 4.2 限流中间件

**设计参考**: Kong Gateway的Token Bucket算法

```python
class RateLimitMiddleware:
    """Token Bucket限流中间件
    
    参考来源: Kong Gateway的限流插件
    
    算法: Token Bucket
    - 每个客户端有固定数量的token
    - 每个请求消耗一个token
    - Token以固定速率补充
    """
    
    def __init__(self, config: GatewayConfig):
        self.config = config
        self.limit = config.rate_limit
        self.window = config.rate_window
        self.buckets: Dict[str, dict] = {}
    
    async def process(self, context: dict) -> dict:
        """处理限流检查"""
        client_id = self._get_client_id(context)
        
        # 禁用限流时直接通过
        if not self.config.enable_rate_limit:
            return {"allowed": True}
        
        # 获取/创建bucket
        bucket = self.buckets.get(client_id, {
            "tokens": self.limit,
            "last_refill": time.time()
        })
        
        # 检查token
        if bucket["tokens"] <= 0:
            return {
                "allowed": False,
                "status": 429,
                "body": {
                    "error": "Rate limit exceeded",
                    "message": f"Max {self.limit} req/{self.window}s",
                    "retry_after": self.window
                }
            }
        
        # 消耗token
        bucket["tokens"] -= 1
        self.buckets[client_id] = bucket
        
        # 添加限流头
        context["rate_limit"] = {
            "limit": self.limit,
            "remaining": bucket["tokens"]
        }
        
        return {"allowed": True}
```

### 4.3 统计中间件

**设计参考**: Prometheus监控模式

```python
class StatsMiddleware:
    """统计收集中间件
    
    参考来源: Prometheus监控
    
    收集指标:
    - total_requests: 总请求数
    - successful_requests: 成功请求
    - failed_requests: 失败请求
    - rate_limited: 限流请求
    """
    
    def __init__(self, config: GatewayConfig):
        self.config = config
        self.stats = {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "rate_limited": 0,
            "auth_failed": 0,
            "start_time": time.time()
        }
    
    async def process(self, context: dict) -> dict:
        """记录统计信息"""
        self.stats["total"] += 1
        context["stats"] = self.stats
        return {"allowed": True}
    
    def record_success(self):
        """记录成功"""
        self.stats["successful"] += 1
    
    def record_failure(self):
        """记录失败"""
        self.stats["failed"] += 1
    
    def record_rate_limit(self):
        """记录限流"""
        self.stats["rate_limited"] += 1
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        uptime = time.time() - self.stats["start_time"]
        return {
            **self.stats,
            "uptime": uptime,
            "requests_per_second": self.stats["total"] / max(uptime, 1)
        }
```

### 4.4 CORS中间件

**设计参考**: Express.js的CORS处理

```python
class CORSMiddleware:
    """CORS处理中间件
    
    参考来源: Express.js的cors中间件
    
    支持的选项:
    - Access-Control-Allow-Origin
    - Access-Control-Allow-Methods
    - Access-Control-Allow-Headers
    """
    
    def __init__(self, config: GatewayConfig):
        self.config = config
        self.origins = config.get("cors_origins", ["*"])
    
    async def process(self, context: dict) -> dict:
        """处理CORS预检请求"""
        if context.get("request", {}).get("method") == "OPTIONS":
            return {
                "allowed": False,
                "status": 200,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, X-API-Key"
                },
                "body": {"status": "ok"}
            }
        
        return {"allowed": True}
```

---

## 5. 安全设计

### 5.1 安全层次

```
┌─────────────────────────────────────────┐
│           Security Layers                 │
├─────────────────────────────────────────┤
│                                         │
│  Layer 1: Network                       │
│  ├── HTTPS (Nginx/Load Balancer)       │
│  └── Firewall                          │
│                                         │
│  Layer 2: Gateway                       │
│  ├── Authentication                    │
│  ├── Rate Limiting                     │
│  └── Input Validation                  │
│                                         │
│  Layer 3: Application                  │
│  ├── API Key Validation                │
│  ├── Request Sanitization               │
│  └── Response Validation                │
│                                         │
└─────────────────────────────────────────┘
```

### 5.2 认证机制

**API Key最佳实践**:

```python
# 推荐的API Key格式
API_KEY_FORMAT = {
    "prefix": "agt_",           # 前缀标识
    "length": 32,               # 最小长度
    "entropy": "high",          # 高熵值
    "format": "hex"             # 十六进制格式
}

# Key生成示例
import secrets

def generate_api_key():
    return f"agt_{secrets.token_hex(16)}"
    # 结果: agt_3f8a9b2c4d5e6f7a8b9c0d1e2f3a4b5
```

### 5.3 输入验证

```python
class InputValidator:
    """输入验证器
    
    安全检查:
    - 请求大小限制
    - JSON格式验证
    - 特殊字符过滤
    """
    
    MAX_REQUEST_SIZE = 1024 * 1024  # 1MB
    BLOCKED_PATTERNS = ["<script>", "javascript:", "SELECT ", "DROP "]
    
    def validate(self, request_body: bytes) -> tuple[bool, str]:
        """验证请求内容"""
        # 大小检查
        if len(request_body) > self.MAX_REQUEST_SIZE:
            return False, "Request too large"
        
        # JSON解析
        try:
            data = json.loads(request_body)
        except json.JSONDecodeError:
            return False, "Invalid JSON"
        
        # query字段检查
        query = data.get("query", "")
        if not isinstance(query, str):
            return False, "query must be string"
        
        # 特殊字符检查
        for pattern in self.BLOCKED_PATTERNS:
            if pattern.lower() in query.lower():
                return False, f"Invalid input: potential injection"
        
        return True, ""
```

---

## 6. API参考

### 6.1 GatewayConfig

```python
@dataclass
class GatewayConfig:
    """Gateway配置类"""
    
    # 网络配置
    host: str = "0.0.0.0"                    # 监听地址
    port: int = 8000                          # 监听端口
    
    # 认证配置
    api_keys: List[str] = field(default_factory=list)  # API Key列表
    enable_auth: bool = True                    # 启用认证
    
    # 限流配置
    rate_limit: int = 100                     # 请求数/窗口
    rate_window: int = 60                     # 窗口大小(秒)
    enable_rate_limit: bool = True             # 启用限流
    
    # CORS配置
    enable_cors: bool = True                  # 启用CORS
    cors_origins: List[str] = field(default_factory=["*"])  # 允许的源
    
    # 安全配置
    max_request_size: int = 1024 * 1024       # 最大请求大小
```

### 6.2 中间件API

```python
class Middleware(ABC):
    """中间件基类"""
    
    @abstractmethod
    async def process(self, context: dict) -> dict:
        """处理中间件
        
        Args:
            context: 请求上下文
        
        Returns:
            dict: {
                "allowed": bool,      # 是否允许请求
                "status": int,        # HTTP状态码
                "body": dict,         # 响应体
                "headers": dict       # 响应头
            }
        """
        pass
```

### 6.3 HTTP端点

| 端点 | 方法 | 描述 | 认证 |
|------|------|------|------|
| `/health` | GET | 健康检查 | ❌ |
| `/stats` | GET | 统计信息 | ❌ |
| `/respond` | POST | 生成响应 | ✅ |
| `/metrics` | GET | Prometheus格式 | ❌ |

---

## 7. 部署指南

### 7.1 Docker部署

**参考来源**: 12-Factor App容器化最佳实践

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 复制应用
COPY lightweight/ ./lightweight/
COPY gateway/ ./gateway/

# 运行用户
RUN useradd -m appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "gateway", "--host", "0.0.0.0"]
```

### 7.2 Nginx反向代理

```nginx
upstream agent_backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    # SSL配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    location / {
        proxy_pass http://agent_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-API-Key $http_x_api_key;
        proxy_set_header Connection "";
        
        # 超时配置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

### 7.3 Kubernetes部署

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent-gateway
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agent-gateway
  template:
    metadata:
      labels:
        app: agent-gateway
    spec:
      containers:
      - name: gateway
        image: agent-gateway:latest
        ports:
        - containerPort: 8000
        env:
        - name: API_KEY
          valueFrom:
            secretKeyRef:
              name: agent-secrets
              key: api-key
        resources:
          requests:
            memory: "64Mi"
            cpu: "100m"
          limits:
            memory: "128Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
```

---

## 8. 运维监控

### 8.1 监控指标

**参考来源**: Prometheus监控

```python
# Prometheus格式指标
METRICS = {
    "gateway_requests_total": "请求总数",
    "gateway_requests_success": "成功请求数",
    "gateway_requests_failed": "失败请求数",
    "gateway_requests_rate_limited": "限流请求数",
    "gateway_requests_auth_failed": "认证失败数",
    "gateway_request_duration_seconds": "请求延迟",
    "gateway_active_connections": "活跃连接数"
}
```

### 8.2 日志格式

```python
LOG_FORMAT = """%(asctime)s - %(name)s - %(levelname)s - %(message)s"""

# 结构化日志
structured_log = {
    "timestamp": "2024-01-01T12:00:00Z",
    "level": "INFO",
    "service": "gateway",
    "client_ip": "192.168.1.1",
    "method": "POST",
    "path": "/respond",
    "status": 200,
    "duration_ms": 5.2,
    "api_key_prefix": "agt_abc1"
}
```

### 8.3 告警规则

```yaml
# Prometheus告警规则
groups:
- name: gateway
  rules:
  - alert: HighErrorRate
    expr: rate(gateway_requests_failed[5m]) > 0.1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Gateway error rate is high"
      
  - alert: RateLimitActive
    expr: gateway_requests_rate_limited > 100
    for: 1m
    labels:
      severity: info
    annotations:
      summary: "Many requests are being rate limited"
```

---

## 📚 参考文档

1. **Hermes Agent** - Enterprise AI Gateway设计
2. **Kong Gateway** - API Gateway开源实现
3. **Express.js** - Middleware Architecture
4. **Prometheus** - 监控指标设计
5. **12-Factor App** - 云原生部署最佳实践

---

**文档版本**: v1.0.0  
**维护者**: Handsome Agent Team  
**最后更新**: 2024年
