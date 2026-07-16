# Agent-Z Agent 发现机制设计

**版本**: v1.0.0  
**最后更新**: 2026-06-09  
**状态**: 正式版

---

## 目录

1. [概述](#一概述)
2. [设计目标](#二设计目标)
3. [发现目录结构](#三发现目录结构)
4. [Agent Manifest](#四agent-manifest)
5. [发现策略](#五发现策略)
6. [扫描机制](#六扫描机制)

---

## 一、概述

### 1.1 背景

Agent-Z 支持通过 MCP (Model Context Protocol) 和 A2A (Agent-to-Agent) 协议与其他 Agent 进行通信。本文档描述 Agent 自动发现机制的设计。

### 1.2 核心特性

| 特性 | 说明 |
|------|------|
| **自动扫描** | 定时或手动扫描指定目录 |
| **Manifest 解析** | 读取 Agent 清单文件获取元数据 |
| **协议支持** | MCP、A2A 协议支持 |
| **状态同步** | 检测 Agent 的增删改，保持列表最新 |

---

## 二、设计目标

### 2.1 功能目标

| 目标 | 说明 |
|------|------|
| **零配置发现** | 用户只需将 Agent 放入指定目录即可被发现 |
| **完整元数据** | 通过 Manifest 获取 Agent 的完整信息 |
| **灵活注册** | 支持手动注册、自动注册 |
| **实时同步** | 检测目录变化，自动更新 Agent 列表 |

---

## 三、发现目录结构

### 3.1 默认目录

```
~/.agent_z/
├── agents/                          # Agent 发现目录
│   ├── openclaw/                   # OpenClaw Agent
│   │   ├── manifest.json           # Agent 清单 (必需)
│   │   └── config.yaml             # 配置文件 (可选)
│   ├── hermes/                     # Hermes Agent
│   │   └── manifest.json
│   └── custom-agent/               # 自定义 Agent
│       ├── manifest.json
│       └── runner.py              # Agent 启动脚本
└── config.yaml                     # 主配置文件
```

### 3.2 发现源类型

| 类型 | 路径 | 说明 |
|------|------|------|
| `local` | `~/.agent_z/agents/` | 用户本地 Agent |
| `project` | `./.agent_z/agents/` | 项目内 Agent |
| `system` | `/opt/Agent-Z/agents/` | 系统级 Agent |

---

## 四、Agent Manifest

### 4.1 Manifest 格式

```json
{
  "name": "OpenClaw",
  "version": "1.0.0",
  "type": "openclaw",
  "description": "通用任务执行 Agent",
  "author": "Agent-Z Team",
  
  "protocol": "mcp",
  "transport": "stdio",
  
  "capabilities": {
    "tools": ["execute_code", "read_file", "write_file"],
    "resources": ["workspace:///*"],
    "prompts": ["代码助手", "文件操作"]
  },
  
  "requirements": {
    "python_version": ">=3.11"
  },
  
  "auto_connect": false,
  "health_check_interval": 30
}
```

### 4.2 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | ✅ | Agent 名称 |
| `version` | string | ✅ | Agent 版本 |
| `type` | string | ✅ | Agent 类型 |
| `protocol` | string | ✅ | 协议类型 (mcp/a2a) |
| `transport` | string | ❌ | 传输类型 (stdio/http) |
| `capabilities` | object | ❌ | Agent 能力 |
| `auto_connect` | boolean | ❌ | 是否自动连接 |
| `health_check_interval` | number | ❌ | 健康检查间隔 |

---

## 五、发现策略

### 5.1 扫描策略

| 策略 | 说明 | 适用场景 |
|------|------|----------|
| **递归扫描** | 扫描目录及子目录 | 多层目录结构 |
| **扁平扫描** | 仅扫描顶层目录 | 简单目录结构 |
| **增量扫描** | 只扫描变化的文件 | 大型目录 |
| **全量扫描** | 每次扫描全部文件 | 需要完全同步 |

### 5.2 扫描优先级

```
1. 系统发现源 (system) - 优先级最高
2. 本地发现源 (local) - 用户级别 Agent
3. 项目发现源 (project) - 随项目交付的 Agent
```

---

## 六、扫描机制

### 6.1 扫描器实现

```python
# agent/discovery/scanner.py
from pathlib import Path
from typing import List, Dict, Any
import json

class AgentScanner:
    """Agent 扫描器"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.agents_dir = data_dir / "agents"
    
    def scan(self, recursive: bool = True) -> List[Dict[str, Any]]:
        """扫描发现目录"""
        discovered = []
        
        if not self.agents_dir.exists():
            return discovered
        
        for agent_dir in self.agents_dir.iterdir():
            if not agent_dir.is_dir():
                continue
            
            manifest_file = agent_dir / "manifest.json"
            if manifest_file.exists():
                try:
                    with open(manifest_file) as f:
                        manifest = json.load(f)
                    discovered.append({
                        "path": str(agent_dir),
                        "manifest": manifest
                    })
                except Exception as e:
                    # 跳过无效的 manifest
                    pass
        
        return discovered
```

### 6.2 定时扫描

```python
# agent/discovery/scheduler.py
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler

class DiscoveryScheduler:
    """发现调度器"""
    
    def __init__(self, scanner: AgentScanner, interval: int = 300):
        self.scanner = scanner
        self.interval = interval
        self.scheduler = AsyncIOScheduler()
    
    def start(self):
        """启动定时扫描"""
        self.scheduler.add_job(
            self._do_scan,
            'interval',
            seconds=self.interval,
            id='agent_discovery'
        )
        self.scheduler.start()
    
    async def _do_scan(self):
        """执行扫描"""
        discovered = self.scanner.scan()
        # 更新 Agent 列表
```

---

## 附录

### A. 示例 Manifest

**OpenClaw Agent Manifest**:

```json
{
  "name": "OpenClaw",
  "version": "1.0.0",
  "type": "openclaw",
  "description": "通用任务执行 Agent，支持代码执行、文件操作",
  "protocol": "mcp",
  "transport": "stdio",
  "capabilities": {
    "tools": ["execute_code", "read_file", "write_file", "list_directory"],
    "resources": ["workspace:///*"],
    "prompts": ["代码助手", "文件操作助手"]
  },
  "auto_connect": false,
  "health_check_interval": 30
}
```

### B. CLI 命令

```bash
# 扫描所有发现源
python -m cli.main agents discover

# 列出发现的 Agent
python -m cli.main agents list

# 连接 Agent
python -m cli.main agents connect openclaw
```

### C. 变更日志

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0.0 | 2026-06-09 | 初始版本 |

---

**版权声明**: 本文档采用 MIT 许可证开源。

**最后更新**: 2026-06-09