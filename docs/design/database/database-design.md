# Handsome Agent 数据库设计

**版本**: v1.0.0  
**最后更新**: 2026-06-09  
**状态**: 正式版

---

## 目录

1. [概述](#一概述)
2. [存储选型](#二存储选型)
3. [数据库 Schema](#三数据库-schema)
4. [索引设计](#四索引设计)
5. [数据模型](#五数据模型)
6. [备份与恢复](#六备份与恢复)

---

## 一、概述

### 1.1 设计原则

| 原则 | 说明 |
|------|------|
| **本地优先** | 数据存储在本地，保护用户隐私 |
| **结构化存储** | 使用 SQLite 存储结构化数据 |
| **文件存储** | 使用 JSON/Markdown 存储文档数据 |
| **可扩展** | 支持未来迁移到 PostgreSQL/MySQL |

### 1.2 存储架构

```
Handsome Agent 数据存储
├── SQLite (结构化数据)
│   └── handsome_agent.db   # 所有表存储在单一数据库文件
│                           # 包含: sessions, messages, skills 等
│
├── JSON 文件 (配置数据)
│   ├── config.json          # 配置文件
│   └── skills/             # 技能数据
│
├── Markdown 文件 (记忆数据)
│   └── memories/            # 长期记忆
│
└── 文件系统 (会话数据)
    └── sessions/{date}/    # 按日期组织的会话数据
```

### 1.3 数据分类

| 类型 | 存储方式 | 说明 |
|------|----------|------|
| 会话信息 | SQLite + 文件 | 会话元数据 |
| 消息记录 | JSON 文件 | 对话历史 |
| 技能数据 | JSON 文件 | 技能定义和内容 |
| 记忆数据 | Markdown | 长期记忆存储 |
| 轨迹数据 | JSON 文件 | 进化轨迹记录 |
| 配置数据 | JSON 文件 | 系统配置 |

---

## 二、存储选型

### 2.1 SQLite 配置

```python
# common/database.py
import sqlite3
from pathlib import Path
from contextlib import contextmanager

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.db_path = data_dir / "handsome_agent.db"
        self._ensure_db_path()
    
    def _ensure_db_path(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def execute(self, query: str, params=None):
        """执行 SQL 查询"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()
```

### 2.2 存储配置

```json
// config.json
{
  "version": "3.0.0",
  "storage": {
    "data_dir": "~/.handsome_agent",
    "database": {
      "type": "sqlite",
      "path": "~/.handsome_agent/handsome_agent.db"
    },
    "sessions_dir": "~/.handsome_agent/sessions",
    "skills_dir": "~/.handsome_agent/skills",
    "memories_dir": "~/.handsome_agent/memories",
    "logs_dir": "~/.handsome_agent/logs"
  },
  "backup": {
    "enabled": true,
    "interval": "1d",
    "retention": "7d",
    "path": "~/.handsome_agent/backups"
  }
}
```

---

## 三、数据库 Schema

### 3.1 会话表 (sessions)

```sql
-- 会话表
CREATE TABLE sessions (
    id VARCHAR(64) PRIMARY KEY,           -- 会话 ID (UUID)
    user_id VARCHAR(64),                  -- 用户 ID
    status VARCHAR(32) DEFAULT 'active',  -- 状态: active/archived
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_active DATETIME DEFAULT CURRENT_TIMESTAMP,
    message_count INTEGER DEFAULT 0,     -- 消息数量
    metadata JSON                          -- 元数据
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_created_at ON sessions(created_at);
CREATE INDEX idx_sessions_status ON sessions(status);
```

**Python 类型**：

```python
class Session:
    id: str                    # UUID
    user_id: str
    status: str               # active/archived
    created_at: datetime
    last_active: datetime
    message_count: int
    metadata: dict
```

### 3.2 技能表 (skills)

```sql
-- 技能表
CREATE TABLE skills (
    id VARCHAR(64) PRIMARY KEY,           -- 技能 ID
    name VARCHAR(255) NOT NULL,            -- 技能名称
    description TEXT,                     -- 技能描述
    trigger TEXT,                          -- 触发条件
    content TEXT,                          -- 技能内容
    category VARCHAR(64),                  -- 分类
    status VARCHAR(32) DEFAULT 'active',  -- 状态: active/stale/archived
    usage_count INTEGER DEFAULT 0,        -- 使用次数
    success_count INTEGER DEFAULT 0,      -- 成功次数
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_used_at DATETIME
);

CREATE INDEX idx_skills_name ON skills(name);
CREATE INDEX idx_skills_category ON skills(category);
CREATE INDEX idx_skills_status ON skills(status);
CREATE UNIQUE INDEX idx_skills_name_unique ON skills(name);
```

### 3.3 轨迹表 (trajectories)

```sql
-- 轨迹表
CREATE TABLE trajectories (
    id VARCHAR(64) PRIMARY KEY,           -- 轨迹 ID
    session_id VARCHAR(64),               -- 关联会话 ID
    status VARCHAR(32) DEFAULT 'active',  -- 状态: active/processed/archived
    confidence_score FLOAT,               -- 置信度
    execution_time FLOAT,                 -- 执行时间
    success BOOLEAN,                      -- 是否成功
    tool_used VARCHAR(64),                -- 使用的工具
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    processed_at DATETIME,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE INDEX idx_trajectories_session_id ON trajectories(session_id);
CREATE INDEX idx_trajectories_created_at ON trajectories(created_at);
CREATE INDEX idx_trajectories_status ON trajectories(status);
```

### 3.4 工具调用表 (tool_calls)

```sql
-- 工具调用表
CREATE TABLE tool_calls (
    id VARCHAR(64) PRIMARY KEY,           -- 调用 ID
    trajectory_id VARCHAR(64),             -- 关联轨迹 ID
    tool_name VARCHAR(64) NOT NULL,       -- 工具名称
    parameters JSON,                       -- 调用参数
    result JSON,                          -- 调用结果
    status VARCHAR(32) DEFAULT 'success', -- 状态: success/error
    error_message TEXT,                   -- 错误信息
    duration_ms INTEGER,                  -- 执行时长
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (trajectory_id) REFERENCES trajectories(id) ON DELETE CASCADE
);

CREATE INDEX idx_tool_calls_trajectory_id ON tool_calls(trajectory_id);
CREATE INDEX idx_tool_calls_tool_name ON tool_calls(tool_name);
CREATE INDEX idx_tool_calls_created_at ON tool_calls(created_at);
```

### 3.5 系统配置表 (system_config)

```sql
-- 系统配置表
CREATE TABLE system_config (
    key VARCHAR(128) PRIMARY KEY,
    value TEXT,
    type VARCHAR(32) DEFAULT 'string',   -- string/number/boolean/json
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 初始化默认配置
INSERT INTO system_config (key, value, type, description) VALUES
    ('app.name', 'Handsome Agent', 'string', '应用名称'),
    ('app.version', '3.0.0', 'string', '应用版本'),
    ('llm.provider', 'openai', 'string', '默认 LLM 提供商'),
    ('llm.model', 'gpt-4', 'string', '默认模型'),
    ('logging.level', 'INFO', 'string', '日志级别'),
    ('session.max_context_messages', '50', 'number', '最大上下文消息数'),
    ('session.compression_threshold', '20', 'number', '压缩阈值');
```

### 3.6 审计日志表 (audit_logs)

```sql
-- 审计日志表
CREATE TABLE audit_logs (
    id VARCHAR(64) PRIMARY KEY,
    action VARCHAR(64) NOT NULL,          -- 操作类型
    resource_type VARCHAR(32) NOT NULL,    -- 资源类型
    resource_id VARCHAR(64),              -- 资源 ID
    details JSON,                         -- 操作详情
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
```

---

## 四、索引设计

### 4.1 主键索引

| 表名 | 主键 | 类型 |
|------|------|------|
| sessions | id | VARCHAR(64) |
| skills | id | VARCHAR(64) |
| trajectories | id | VARCHAR(64) |
| tool_calls | id | VARCHAR(64) |
| system_config | key | VARCHAR(128) |
| audit_logs | id | VARCHAR(64) |

### 4.2 业务索引

```sql
-- 会话表索引
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_created_at ON sessions(created_at);
CREATE INDEX idx_sessions_status ON sessions(status);

-- 技能表索引
CREATE UNIQUE INDEX idx_skills_name_unique ON skills(name);
CREATE INDEX idx_skills_category ON skills(category);
CREATE INDEX idx_skills_status ON skills(status);

-- 轨迹表索引
CREATE INDEX idx_trajectories_session_id ON trajectories(session_id);
CREATE INDEX idx_trajectories_created_at ON trajectories(created_at);

-- 工具调用表索引
CREATE INDEX idx_tool_calls_trajectory_id ON tool_calls(trajectory_id);
CREATE INDEX idx_tool_calls_tool_name ON tool_calls(tool_name);
```

---

## 五、数据模型

### 5.1 会话消息 JSON Schema

```json
// sessions/{date}/{session_id}_messages.json
{
  "session_id": "uuid",
  "messages": [
    {
      "role": "user",
      "content": "用户输入",
      "timestamp": "2026-06-09T12:00:00Z",
      "metadata": {}
    },
    {
      "role": "assistant",
      "content": "助手回复",
      "timestamp": "2026-06-09T12:00:01Z",
      "metadata": {
        "tool_used": "file_read",
        "confidence_score": 0.9
      }
    }
  ]
}
```

### 5.2 技能 JSON Schema

```json
// skills/{skill_id}.json
{
  "id": "uuid",
  "name": "code_assistant",
  "description": "代码助手技能",
  "trigger": "需要编写代码时",
  "content": "你是一个专业的代码助手...",
  "category": "developer",
  "status": "active",
  "usage_count": 10,
  "success_count": 9,
  "created_at": "2026-06-09T10:00:00Z",
  "updated_at": "2026-06-09T12:00:00Z",
  "last_used_at": "2026-06-09T12:00:00Z"
}
```

### 5.3 轨迹 JSON Schema

```json
// trajectories/{trajectory_id}.json
{
  "id": "uuid",
  "session_id": "session-uuid",
  "steps": [
    {
      "step": 1,
      "action": "tool_call",
      "tool_name": "file_read",
      "parameters": {"path": "/tmp/test.txt"},
      "result": {"content": "file content"},
      "reasoning": "需要读取文件内容",
      "is_error": false
    },
    {
      "step": 2,
      "action": "direct_response",
      "result": "文件内容已读取",
      "is_error": false
    }
  ],
  "confidence_score": 0.9,
  "execution_time": 1.5,
  "success": true,
  "created_at": "2026-06-09T12:00:00Z"
}
```

---

## 六、备份与恢复

### 6.1 自动备份策略

```python
# scripts/backup.py
import shutil
import gzip
from datetime import datetime, timedelta
from pathlib import Path

class BackupManager:
    """备份管理器"""
    
    def __init__(self, data_dir: Path, backup_dir: Path) -> None:
        self.data_dir = data_dir
        self.backup_dir = backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def create_backup(self) -> Path:
        """创建备份"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"handsome_agent_backup_{timestamp}"
        backup_path = self.backup_dir / backup_name
        
        # 备份 SQLite 数据库
        db_backup = backup_path / "db"
        db_backup.mkdir(parents=True)
        
        db_file = self.data_dir / "handsome_agent.db"
        if db_file.exists():
            shutil.copy2(db_file, db_backup / "handsome_agent.db")
        
        # 备份配置文件
        config_backup = backup_path / "config"
        config_backup.mkdir(parents=True)
        
        config_file = self.data_dir / "config.json"
        if config_file.exists():
            shutil.copy2(config_file, config_backup / "config.json")
        
        # 压缩备份
        archive_path = self.backup_dir / f"{backup_name}.tar.gz"
        shutil.make_archive(
            str(archive_path.with_suffix('')),
            'gzip',
            backup_path
        )
        shutil.rmtree(backup_path)
        
        return archive_path
```

### 6.2 备份调度配置

```yaml
# cron.d/handsome-agent-backup
# 每天凌晨 2 点执行备份
0 2 * * * root /opt/handsome-agent/scripts/backup.sh
```

---

## 附录

### A. 数据库版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2026-06-09 | 正式版设计 |

### B. 性能优化建议

| 场景 | 建议 |
|------|------|
| 大量会话 | 使用分区表，按月份分表 |
| 大量轨迹 | 定期归档旧数据 |
| 向量查询 | 未来可集成向量数据库 |

### C. 常见问题

**Q: 如何查看数据库大小？**
```bash
ls -lh ~/.handsome_agent/*.db
du -sh ~/.handsome_agent/
```

**Q: 如何手动备份？**
```bash
cp ~/.handsome_agent/handsome_agent.db ~/backups/
```

**Q: 如何重置数据库？**
```bash
rm ~/.handsome_agent/handsome_agent.db
# 下次启动时会自动创建
```

---

**版权声明**: 本文档采用 MIT 许可证开源。

**最后更新**: 2026-06-09