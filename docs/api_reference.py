# 📡 API Reference

## Endpoints

### Health Check
```
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "gateway": true
}
```

### Generate Response
```
POST /respond
```

**Request:**
```json
{
  "query": "What is Python?"
}
```

**Response:**
```json
{
  "content": "Python is a high-level...",
  "confidence": 0.9,
  "execution_time": 0.005
}
```

### Statistics
```
GET /stats
```

**Response:**
```json
{
  "total": 1250,
  "allowed": 1200,
  "denied": 50,
  "uptime": 3600.5,
  "limit": 100,
  "window": 60
}
```

## Configuration

### Lightweight Agent

```python
from lightweight import AgentConfig, LightweightAgent

config = AgentConfig(
    name="MyAgent",
    enable_caching=True,
    max_response_length=2000
)

agent = LightweightAgent(config)
```

### Gateway

```python
from gateway import GatewayConfig, run_gateway

config = GatewayConfig(
    host="0.0.0.0",
    port=8000,
    api_keys=["key1", "key2"],
    rate_limit=100,
    rate_window=60,
    enable_auth=True,
    enable_rate_limit=True,
    enable_cors=True
)

run_gateway(config)
```

## CLI Options

### Lightweight
```bash
# 交互模式
python -m lightweight

# API服务器
python -m lightweight.server --host 0.0.0.0 --port 8000
```

### Gateway
```bash
python -m gateway [options]

Options:
  --host HOST              Host (default: 0.0.0.0)
  --port PORT              Port (default: 8000)
  --api-key KEY            API key for authentication
  --rate-limit LIMIT       Requests per window (default: 100)
  --rate-window WINDOW     Window in seconds (default: 60)
  --no-auth               Disable authentication
  --no-rate-limit        Disable rate limiting
```

## Error Codes

| Code | Meaning | Solution |
|------|---------|----------|
| 200 | Success | - |
| 400 | Bad Request | Check JSON format |
| 401 | Unauthorized | Check API key |
| 404 | Not Found | Check endpoint URL |
| 429 | Rate Limited | Wait and retry |
| 500 | Server Error | Check logs |

## Rate Limits

Default: 100 requests per 60 seconds

Headers in response:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 97
```

## CORS

Enabled by default for all origins.

For production, restrict in `gateway/config.py`:
```python
config = GatewayConfig(
    enable_cors=True,
    cors_origins=["https://yourapp.com"]
)
```
