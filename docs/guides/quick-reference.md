# 🚀 Agent-Z - 快速参考

> 所有命令、API和最佳实践的快速查阅

---

## ⚡ 快速开始

### 1. Lightweight Agent (Zero Claw风格)

```python
# 基本使用
from lightweight.agent import LightweightAgent
import asyncio

agent = LightweightAgent()
response = asyncio.run(agent.respond("What is Python?"))
print(response.content)

# 带缓存
agent = LightweightAgent(AgentConfig(enable_caching=True))
```

### 2. Enhanced Agent (AutoGPT + Claude风格)

```python
# Chain of Thought推理
from lightweight.agent_v2 import EnhancedAgent, ReasoningLevel

agent = EnhancedAgent(reasoning_level=ReasoningLevel.CHAIN_OF_THOUGHT)
result = asyncio.run(agent.respond(
    "Explain neural networks",
    include_reasoning=True,
    use_tools=True
))
```

### 3. Gateway (Hermes + Kong风格)

```bash
# 启动网关
python -m gateway --api-key YOUR_KEY --rate-limit 100

# 测试端点
curl http://localhost:8000/health
curl -X POST http://localhost:8000/respond \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_KEY" \
  -d '{"query": "test"}'
```

---

## 🎯 API速查

### Lightweight Agent

```python
# 核心API
agent = LightweightAgent(
    enable_caching=True,      # 启用缓存
    max_response_length=2000   # 最大响应长度
)

response = await agent.respond(query)  # 异步响应
agent.clear_cache()                 # 清空缓存
```

### Enhanced Agent (CoT + Tools)

```python
# 推理级别
agent = EnhancedAgent(
    reasoning_level=ReasoningLevel.CHAIN_OF_THOUGHT  # CHAIN_OF_THOUGHT, DIRECT, REACT, SELF_REFLECT
)

# 响应结构
result = await agent.respond(
    query,
    include_reasoning=True,   # 包含思维链
    use_tools=True            # 使用工具
)

# 结果包含
result["response"]        # 最终响应
result["reasoning"]       # 推理过程
result["confidence"]      # 置信度
result["execution_time"]  # 执行时间
```

### Gateway

```python
# 配置
config = GatewayConfig(
    api_keys=["key1", "key2"],      # API密钥列表
    rate_limit=100,                     # 请求限制
    rate_window=60,                   # 时间窗口
    enable_auth=True,                   # 启用认证
    enable_rate_limit=True,             # 启用限流
    enable_cors=True                   # 启用CORS
)

# 中间件
from gateway.middleware import AuthMiddleware, RateLimitMiddleware
```

---

## 🔧 配置选项

### Lightweight Agent

```python
AgentConfig(
    name="Agent",
    enable_caching=True,
    max_response_length=2000
)
```

### Enhanced Agent

```python
EnhancedAgent(
    name="EnhancedAgent",
    reasoning_level=ReasoningLevel.CHAIN_OF_THOUGHT,
    enable_caching=True,
    max_reasoning_steps=5
)
```

### Gateway

```python
GatewayConfig(
    host="0.0.0.0",
    port=8000,
    api_keys=["key1", "key2"],
    rate_limit=100,
    rate_window=60,
    enable_auth=True,
    enable_rate_limit=True,
    enable_cors=True,
    max_request_size=1024*1024
)
```

---

## 🧪 测试命令

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_lightweight.py -v
pytest tests/test_gateway.py -v

# 性能测试
pytest tests/ -k performance -v

# 代码覆盖率
pytest --cov=lightweight --cov-report=html
```

---

## 📊 性能基准

| 模块 | 指标 | 目标 |
|------|------|------|
| Lightweight | 响应时间 | < 5ms |
| Lightweight | 内存 | < 30MB |
| Enhanced Agent | 推理时间 | < 50ms |
| Gateway | 并发 | 1000+ req/s |

---

## 🛠️ 故障排除

### 问题: 导入错误

```bash
# 确保在项目根目录
cd custom-ai-agent

# 检查Python路径
python -c "import lightweight; import gateway"
```

### 问题: Gateway连接拒绝

```bash
# 检查端口占用
lsof -i :8000

# 重启Gateway
pkill -9 $(lsof -t -i :8000)
python -m gateway
```

### 问题: 测试失败

```bash
# 详细输出
pytest -vv --tb=long

# 仅运行快速测试
pytest -k "not slow" -v
```

---

## 📚 更多资源

- [System Design](system-design.md) - 系统设计文档
- [State of Art Research](../../references/state-of-art-research.md) - 业界最佳实践
- [Acknowledgements](../../references/acknowledgements.md) - 参考项目
- [lightweight/DESIGN.md](lightweight/DESIGN.md) - 轻量版设计
- [gateway/DESIGN.md](gateway/DESIGN.md) - 网关设计

---

**版本**: v1.0  
**更新**: 持续对标AutoGPT, Claude, LangChain
