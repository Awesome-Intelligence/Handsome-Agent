# 🏗️ Architecture

## Overview

```
┌─────────────────────────────────────────┐
│           Mobile/Web Clients              │
└─────────────────┬───────────────────────┘
                  │ HTTP/REST
                  ▼
┌─────────────────────────────────────────┐
│           Gateway (Optional)              │
│  ┌─────────────────────────────────┐   │
│  │ • Authentication                 │   │
│  │ • Rate Limiting                  │   │
│  │ • Statistics                     │   │
│  │ • CORS                           │   │
│  └─────────────────────────────────┘   │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│         Lightweight Agent                │
│  ┌─────────────────────────────────┐   │
│  │ • Knowledge Base                  │   │
│  │ • Response Generation            │   │
│  │ • Caching                        │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

## Modules

### Lightweight Agent
- **Purpose**: Core AI response generation
- **Dependencies**: None (standard library only)
- **Memory**: < 30MB
- **Use**: Mobile apps, IoT, edge computing

### Gateway
- **Purpose**: Production features (auth, rate limiting)
- **Dependencies**: None (standard library only)
- **Memory**: < 40MB
- **Use**: Production deployments

### Core (Full Version)
- **Purpose**: Advanced features, testing
- **Dependencies**: pytest, etc.
- **Use**: Development, complex scenarios

## Data Flow

```
1. Client Request
   ↓
2. Gateway (if enabled)
   ├── Auth Check
   ├── Rate Limit Check
   └── Pass Through
   ↓
3. Lightweight Agent
   ├── Cache Check
   ├── Knowledge Lookup
   └── Response Generation
   ↓
4. Response to Client
```

## Performance

| Component | Latency | Memory | CPU |
|-----------|----------|--------|-----|
| Agent | < 5ms | < 30MB | < 5% |
| Gateway | < 10ms | < 40MB | < 10% |
| Docker | < 15ms | < 50MB | < 15% |

## Scalability

### Horizontal Scaling
```yaml
# docker-compose.yml
services:
  agent1:
    build: .
  agent2:
    build: .
  agent3:
    build: .
  nginx:
    image: nginx
    # Load balancer
```

### Kubernetes
```yaml
apiVersion: apps/v1
kind: Deployment
spec:
  replicas: 5
  # Auto-scaling based on CPU/memory
```

## Security

1. **Authentication**: API Key validation
2. **Rate Limiting**: Token bucket algorithm
3. **Input Validation**: JSON parsing checks
4. **Output Sanitization**: Content validation
5. **HTTPS**: Required for production
