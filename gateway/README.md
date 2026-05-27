# 🔐 API Gateway - 生产级API网关

## 特性

- ✅ **认证** - API Key 验证
- ✅ **限流** - Token bucket 算法
- ✅ **统计** - 实时监控（含系统指标）
- ✅ **CORS** - 跨域支持
- ✅ **健康检查** - Kubernetes 探针支持
- ✅ **零依赖** - 仅 Python 标准库

## 快速开始

```bash
# 开发测试（无需认证）
python -m gateway --no-auth --no-rate-limit

# 生产部署
python -m gateway --api-key your-key --rate-limit 100
```

## 使用示例

### 启动网关
```bash
python -m gateway --api-key my-secret-key --rate-limit 50
```

### 测试端点
```bash
# 完整健康检查（含系统状态）
curl http://localhost:8000/health

# 存活探针 (liveness probe)
curl http://localhost:8000/health/live

# 就绪探针 (readiness probe)
curl http://localhost:8000/health/ready

# 统计（含 CPU/内存）
curl http://localhost:8000/stats

# 生成响应
curl -X POST http://localhost:8000/respond \
  -H "Content-Type: application/json" \
  -H "X-API-Key: my-secret-key" \
  -d '{"query": "What is Python?"}'
```

## 健康检查端点

| 端点 | 用途 | K8s 探针类型 |
|------|------|-------------|
| `/health` | 完整健康检查 | - |
| `/health/live` | 进程存活检查 | `livenessProbe` |
| `/health/ready` | 依赖就绪检查 | `readinessProbe` |

**响应示例**:
```json
{
  "status": "healthy",
  "uptime_seconds": 3600.5,
  "process": {"status": "alive", "pid": 1234},
  "dependencies": {"status": "ready", "checks": {...}},
  "system": {"cpu_percent": 15.2, "memory_percent": 45.3}
}
```

## 认证配置

```bash
# 单个API Key
python -m gateway --api-key your-32-char-key

# 多个API Key（代码中配置）
from gateway import GatewayConfig, run_gateway

config = GatewayConfig(
    api_keys=["key1", "key2", "key3"],
    enable_auth=True
)
run_gateway(config)
```

## 限流配置

```bash
# 100请求/60秒（默认）
python -m gateway

# 50请求/30秒
python -m gateway --rate-limit 50 --rate-window 30
```

## Docker部署

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY gateway/ /app/
CMD ["python", "-m", "gateway", "--api-key", "prod-key"]
```

```bash
docker build -t agent-gateway .
docker run -d -p 8000:8000 \
  -e API_KEY=your-key \
  agent-gateway
```

## 性能指标

| 指标 | 数值 |
|------|------|
| 延迟 | < 10ms |
| 吞吐 | 1000+ req/s |
| 内存 | < 40MB |

完整文档见 [docs/](docs/)
