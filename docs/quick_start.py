# 🚀 Quick Start - 5分钟上手

## 1. 安装 (无需安装)

```bash
# 直接运行，无需pip install
python -m lightweight
```

## 2. 测试

```bash
# 终端交互
python -m lightweight

# REST API
python -m lightweight.server
```

## 3. 测试API

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/respond \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Python?"}'
```

## 4. 生产部署

```bash
# Gateway（带认证限流）
python -m gateway --api-key YOUR_KEY --rate-limit 100

# 或Docker
docker run -p 8000:8000 python:3.11-slim \
  python -m gateway --api-key KEY
```

## 5. 移动端集成

**Python:**
```python
from lightweight import LightweightAgent
agent = LightweightAgent()
response = asyncio.run(agent.respond("Hello"))
```

**iOS/Android/Flutter**: 见 [Mobile Integration](mobile_integration.md)

## 快速命令

| 命令 | 用途 |
|------|------|
| `python -m lightweight` | 交互模式 |
| `python -m lightweight.server` | REST API |
| `python -m gateway --no-auth` | 开发网关 |
| `python -m gateway --api-key KEY` | 生产网关 |

## 下一步

- [API参考](api_reference.md) - 完整API文档
- [移动端集成](mobile_integration.md) - iOS/Android/Flutter
- [部署指南](deployment.md) - Docker/云平台
