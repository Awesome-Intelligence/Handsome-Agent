# Handsome Agent 运维手册

**版本**: v1.0.0  
**最后更新**: 2026-06-09  
**状态**: 正式版

---

## 目录

1. [概述](#一概述)
2. [部署指南](#二部署指南)
3. [监控告警](#三监控告警)
4. [备份恢复](#四备份恢复)
5. [故障处理](#五故障处理)
6. [性能优化](#六性能优化)
7. [安全加固](#七安全加固)

---

## 一、概述

### 1.1 文档目的

本文档为运维人员提供 Handsome Agent 系统的运维指南，包括部署、监控、备份、故障处理等内容。

### 1.2 系统要求

| 项目 | 最低配置 | 推荐配置 |
|------|----------|----------|
| CPU | 2 核 | 4 核 |
| 内存 | 4 GB | 8 GB |
| 磁盘 | 10 GB | 50 GB |
| 操作系统 | Ubuntu 20.04+ / Windows 10+ / macOS 12+ | - |
| Python | 3.11+ | 3.11+ |

### 1.3 系统组件

| 组件 | 说明 | 端口 |
|------|------|------|
| CLI | 命令行界面 | - |
| Gateway | HTTP 网关服务 | 8080 |
| API Server | OpenAI 兼容 API | 8081 |
| Agent Core | 核心 Agent 引擎 | - |

---

## 二、部署指南

### 2.1 本地开发部署

```bash
# 克隆项目
git clone https://github.com/your-repo/Handsome-Agent.git
cd Handsome-Agent

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
export HANDSOME_LLM_PROVIDER=openai
export HANDSOME_LLM_API_KEY=your-api-key
```

### 2.2 Docker 部署

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-m", "cli.main", "chat"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  handsome-agent:
    build: .
    container_name: handsome-agent
    ports:
      - "8080:8080"      # Gateway
      - "8081:8081"      # API Server
    volumes:
      - ./data:/root/.handsome_agent
    environment:
      - HANDSOME_LLM_PROVIDER=openai
      - HANDSOME_LLM_API_KEY=${API_KEY}
      - HANDSOME_LOG_LEVEL=INFO
    restart: unless-stopped
```

**部署步骤**:
```bash
# 1. 构建镜像
docker build -t handsome-agent:latest .

# 2. 启动服务
docker-compose up -d

# 3. 检查状态
docker-compose ps

# 4. 查看日志
docker-compose logs -f
```

### 2.3 Gateway 部署

```bash
# 基本启动
python -m gateway

# 带认证启动
python -m gateway --api-key your-secret-key

# 带限流启动
python -m gateway --api-key your-secret-key --rate-limit 100

# 自定义端口
python -m gateway --port 9000

# 禁用认证（仅开发环境）
python -m gateway --no-auth
```

### 2.4 配置管理

```json
// ~/.handsome_agent/config.json
{
  "version": "3.0.0",
  "llm": {
    "provider": "openai",
    "model": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 2000
  },
  "logging": {
    "level": "INFO",
    "format": "json",
    "output": ["console", "file"]
  },
  "session": {
    "auto_save": true,
    "max_context_messages": 50,
    "compression_threshold": 20
  },
  "tools": {
    "shell_timeout": 60,
    "max_file_size": 10485760
  },
  "gateway": {
    "host": "0.0.0.0",
    "port": 8080,
    "auth": {
      "enabled": true,
      "api_key": ""
    },
    "rate_limit": {
      "enabled": true,
      "requests_per_minute": 100
    }
  }
}
```

---

## 三、监控告警

### 3.1 日志系统

Handsome Agent 使用分层的日志系统：

| 日志器 | 说明 | 用途 |
|--------|------|------|
| `decision` | 决策日志 | 意图理解、模式选择 |
| `llm` | LLM 日志 | 模型调用、响应 |
| `task` | 任务日志 | 任务执行、步骤 |
| `execution` | 执行日志 | 工具调用、结果 |
| `session` | 会话日志 | 会话管理、状态 |
| `rail` | Rail 日志 | 拦截器事件 |

### 3.2 日志配置

```yaml
# logging.yaml
version: 1
disable_existing_loggers: false

formatters:
  simple:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  json:
    class: pythonjsonlogger.jsonlogger.JsonFormatter
    format: '%(asctime)s %(name)s %(levelname)s %(message)s'

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: simple
    stream: ext://sys.stdout

  file:
    class: logging.handlers.RotatingFileHandler
    level: DEBUG
    formatter: json
    filename: ~/.handsome_agent/logs/app.log
    maxBytes: 10485760  # 10MB
    backupCount: 5

loggers:
  agent:
    level: DEBUG
    handlers: [console, file]
    propagate: false

root:
  level: INFO
  handlers: [console]
```

### 3.3 监控指标

| 指标 | 类型 | 说明 | 告警阈值 |
|------|------|------|----------|
| **服务可用性** | Gauge | 服务健康状态 | < 1 = 告警 |
| **请求延迟** | Histogram | 平均响应时间 | > 5s = 警告 |
| **请求错误率** | Counter | 失败请求占比 | > 1% = 警告 |
| **对话次数** | Counter | 总对话次数 | - |
| **工具调用次数** | Counter | 工具调用总数 | - |
| **工具错误率** | Counter | 工具错误占比 | > 5% = 警告 |
| **活跃会话数** | Gauge | 当前会话数 | > 1000 = 警告 |
| **CPU 使用率** | Gauge | CPU 占用 | > 80% = 警告 |
| **内存使用率** | Gauge | 内存占用 | > 85% = 警告 |
| **磁盘使用率** | Gauge | 磁盘占用 | > 80% = 警告 |

### 3.4 健康检查

```bash
# 检查服务状态
curl http://localhost:8080/api/v1/health

# 响应示例
{
  "status": "healthy",
  "version": "3.0.0",
  "timestamp": "2026-06-09T12:00:00Z",
  "services": {
    "llm": "connected",
    "session": "active",
    "tools": "available"
  }
}
```

---

## 四、备份恢复

### 4.1 数据目录

```
~/.handsome_agent/
├── config.json           # 配置文件
├── sessions/            # 会话数据
├── skills/              # 技能数据
├── memories/             # 记忆数据
├── logs/                 # 日志文件
└── handsome_agent.db      # SQLite 数据库
```

### 4.2 备份策略

```bash
#!/bin/bash
# backup.sh - 每日备份脚本

BACKUP_DIR="/var/backups/handsome-agent"
DATA_DIR="$HOME/.handsome_agent"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份数据
tar -czf $BACKUP_DIR/handsome-agent_$TIMESTAMP.tar.gz \
  $DATA_DIR/config.json \
  $DATA_DIR/sessions/ \
  $DATA_DIR/skills/ \
  $DATA_DIR/memories/ \
  $DATA_DIR/handsome_agent.db

# 删除 7 天前的备份
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: handsome-agent_$TIMESTAMP.tar.gz"
```

### 4.3 恢复操作

```bash
#!/bin/bash
# restore.sh - 恢复备份脚本

BACKUP_FILE=$1
DATA_DIR="$HOME/.handsome_agent"

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: $0 <backup_file>"
  exit 1
fi

# 停止服务
pkill -f "python -m gateway"

# 清理旧数据
rm -rf $DATA_DIR/sessions/*
rm -rf $DATA_DIR/skills/*
rm -rf $DATA_DIR/memories/*

# 恢复备份
tar -xzf $BACKUP_FILE -C $DATA_DIR

echo "Restore completed from $BACKUP_FILE"
```

### 4.4 自动备份配置

```yaml
# /etc/cron.d/handsome-agent-backup
# 每天凌晨 2 点执行备份
0 2 * * * root /opt/handsome-agent/scripts/backup.sh
```

---

## 五、故障处理

### 5.1 常见问题

#### 问题 1: CLI 无法启动

**症状**: 运行 `python -m cli.main chat` 报错

**排查步骤**:
```bash
# 检查 Python 版本
python --version  # 需要 3.11+

# 检查依赖安装
pip list | grep -E "pydantic|httpx|click"

# 检查配置文件
cat ~/.handsome_agent/config.json
```

**解决方案**:
- 升级 Python 到 3.11+
- 重新安装依赖 `pip install -r requirements.txt`
- 检查配置文件格式是否正确

#### 问题 2: Gateway 无法启动

**症状**: Gateway 启动后立即退出

**排查步骤**:
```bash
# 查看详细错误
python -m gateway --verbose

# 检查端口占用
netstat -tlnp | grep 8080  # Linux
# 或 netstat -ano | findstr 8080  # Windows

# 检查配置文件
cat ~/.handsome_agent/config.json
```

**解决方案**:
- 释放端口或使用其他端口
- 修复配置文件错误
- 检查日志获取详细信息

#### 问题 3: LLM 调用失败

**症状**: 对话响应错误或超时

**排查步骤**:
```bash
# 检查 API Key 配置
echo $HANDSOME_LLM_API_KEY

# 测试 API 连接
curl -X POST https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $HANDSOME_LLM_API_KEY" \
  -d '{"model": "gpt-4", "messages": [{"role": "user", "content": "test"}]}'

# 查看 LLM 日志
grep "llm" ~/.handsome_agent/logs/app.log
```

**解决方案**:
- 确认 API Key 正确
- 检查网络连通性
- 查看 API 配额是否用尽

#### 问题 4: 工具执行失败

**症状**: 工具调用报错或超时

**排查步骤**:
```bash
# 查看执行日志
grep "execution" ~/.handsome_agent/logs/app.log

# 检查工具参数
python -m cli.main tools info <tool_name>

# 测试工具直接调用
python -c "from tools.registry import registry; print(registry.get('<tool_name>'))"
```

**解决方案**:
- 检查工具参数是否正确
- 确认工具依赖是否安装
- 增加超时时间

### 5.2 日志分析

```bash
# 实时查看错误日志
tail -f ~/.handsome_agent/logs/app.log | grep ERROR

# 统计错误类型
grep ERROR ~/.handsome_agent/logs/app.log | \
  awk '{print $5}' | sort | uniq -c | sort -rn

# 查看特定会话日志
grep "session_id" ~/.handsome_agent/logs/app.log
```

### 5.3 服务重启

```bash
# 重启 Gateway
pkill -f "python -m gateway"
python -m gateway &

# 完全重启
pkill -f "handsome-agent"
sleep 2
python -m gateway --no-auth &
```

---

## 六、性能优化

### 6.1 会话管理优化

```json
// config.json - 会话优化配置
{
  "session": {
    "auto_save": true,
    "max_context_messages": 50,
    "compression_threshold": 20,
    "compression_max_messages": 10
  }
}
```

### 6.2 LLM 优化

```json
// config.json - LLM 优化配置
{
  "llm": {
    "provider": "openai",
    "model": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 2000,
    "timeout": 60,
    "retry": {
      "max_attempts": 3,
      "backoff_multiplier": 2
    }
  }
}
```

### 6.3 工具执行优化

```json
// config.json - 工具优化配置
{
  "tools": {
    "shell_timeout": 60,
    "max_file_size": 10485760,
    "cache_enabled": true,
    "cache_ttl": 300
  }
}
```

### 6.4 数据库优化

```sql
-- 清理过期会话
DELETE FROM sessions
WHERE last_active < datetime('now', '-30 days');

-- 清理轨迹记录
DELETE FROM trajectories
WHERE created_at < datetime('now', '-7 days');

-- 重建索引
REINDEX;
ANALYZE;
```

---

## 七、安全加固

### 7.1 API 安全

```yaml
# gateway 安全配置
gateway:
  auth:
    enabled: true
    api_key: "${API_KEY}"
    
  rate_limit:
    enabled: true
    requests_per_minute: 100
    
  cors:
    enabled: true
    allowed_origins:
      - "https://app.example.com"
```

### 7.2 数据加密

```bash
# 使用环境变量存储敏感信息
export HANDSOME_LLM_API_KEY="sk-xxx"
export HANDSOME_DB_PASSWORD="xxx"

# 或使用密钥管理服务
export HANDSOME_KMS_PROVIDER="aws"
export HANDSOME_KMS_KEY_ID="xxx"
```

### 7.3 安全检查清单

| 检查项 | 频率 | 执行方式 |
|--------|------|----------|
| 检查日志中的异常访问 | 每天 | 自动告警 |
| 审计日志分析 | 每周 | 手动审查 |
| 依赖安全扫描 | 每次发布 | CI/CD |
| API Key 轮换 | 每月 | 手动执行 |
| 备份完整性检查 | 每周 | 自动验证 |

---

## 附录

### A. 运维命令速查

| 命令 | 说明 |
|------|------|
| `python -m cli.main chat` | 启动对话 |
| `python -m gateway` | 启动网关 |
| `python -m cli.main tools list` | 列出工具 |
| `python -m cli.main session list` | 列出会话 |
| `curl http://localhost:8080/api/v1/health` | 健康检查 |

### B. 日志位置

| 日志类型 | 路径 |
|----------|------|
| 应用日志 | `~/.handsome_agent/logs/app.log` |
| LLM 日志 | `~/.handsome_agent/logs/llm.log` |
| 会话日志 | `~/.handsome_agent/logs/session.log` |

### C. 变更日志

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0.0 | 2026-06-09 | 初始版本 |

---

**版权声明**: 本文档采用 MIT 许可证开源。

**最后更新**: 2026-06-09