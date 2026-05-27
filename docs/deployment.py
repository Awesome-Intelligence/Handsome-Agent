# 🐳 Deployment Guide

## Docker (推荐)

### Dockerfile
```dockerfile
FROM python:3.11-slim
WORKDIR /app

# 轻量版
COPY lightweight/ ./lightweight/
CMD ["python", "-m", "lightweight"]

# 或Gateway版
# COPY gateway/ ./gateway/
# COPY lightweight/ ./lightweight/
# CMD ["python", "-m", "gateway", "--api-key", "YOUR_KEY"]
```

### 构建运行
```bash
# 构建
docker build -t agent-lite .

# 运行
docker run -d -p 8000:8000 \
  --name agent \
  agent-lite

# 查看日志
docker logs -f agent

# 停止
docker stop agent && docker rm agent
```

## Docker Compose

```yaml
version: '3.8'
services:
  agent:
    build: .
    ports:
      - "8000:8000"
    environment:
      - API_KEY=${API_KEY}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

```bash
# 启动
docker-compose up -d

# 扩缩容
docker-compose up -d --scale agent=3
```

## 云平台

### AWS ECS
```bash
# 构建镜像
docker build -t agent:latest .

# 推送到ECR
aws ecr create-repository --repository-name agent
docker tag agent:latest <account>.dkr.ecr.<region>.amazonaws.com/agent:latest
docker push <account>.dkr.ecr.<region>.amazonaws.com/agent:latest

# 部署到ECS
aws ecs create-service --cluster agent-cluster --service-name agent
```

### Google Cloud Run
```bash
# 构建
gcloud builds submit --tag gcr.io/PROJECT_ID/agent

# 部署
gcloud run deploy agent \
  --image gcr.io/PROJECT_ID/agent \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Heroku
```bash
# 创建应用
heroku create agent-backend

# 部署
git push heroku main
```

### Railway
```bash
# Railway自动检测Python项目
# 只需创建railway.json配置
{
  "build": {"command": "pip install -r requirements.txt"},
  "start": {"command": "python -m gateway --api-key $API_KEY"}
}
```

## Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agent
  template:
    metadata:
      labels:
        app: agent
    spec:
      containers:
      - name: agent
        image: agent:latest
        ports:
        - containerPort: 8000
        env:
        - name: API_KEY
          valueFrom:
            secretKeyRef:
              name: agent-secrets
              key: api-key
```

```bash
kubectl apply -f deployment.yaml
kubectl get pods -l app=agent
```

## Nginx反向代理

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-API-Key $http_x_api_key;
    }
}
```

## 环境变量

```bash
# 必需
export API_KEY="your-secret-key"

# 可选
export RATE_LIMIT=100
export RATE_WINDOW=60
```

## 监控

```bash
# 查看统计
curl http://localhost:8000/stats

# Prometheus格式（可配置）
# 在代码中添加/metrics端点
```

## 安全检查清单

- [ ] 使用HTTPS
- [ ] 配置API Key认证
- [ ] 设置限流规则
- [ ] 配置CORS白名单
- [ ] 启用日志记录
- [ ] 定期更新依赖
- [ ] 监控错误率
- [ ] 备份配置
