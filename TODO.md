# Handsome Agent 开发任务清单

> Hermes-Brain + OpenClaw-Body 架构实现任务

---

## 📋 待完成任务

### 🔴 高优先级

- [ ] **目录结构重构** ⭐ 新增
  - [ ] 制定详细的重构执行计划
  - [ ] 创建新目录结构
  - [ ] 移动文件（不修改代码）
  - [ ] 修复导入路径
  - [ ] 测试验证
  - [ ] 更新 rule.md 约束

- [ ] **完善单元测试**
  - [ ] 修复剩余 6 个失败的测试
  - [ ] 添加集成测试
  - [ ] 添加 E2E 测试
  - [ ] 确保 CI 通过

- [ ] **遗忘机制（删除低置信度技能）**

### 🟡 中优先级

- [ ] **梦境能力（Dream Capability）**
  - [ ] 设计梦境架构
  - [ ] 模拟人类睡眠时的潜意识处理机制

- [ ] **任务拆解与可打断重规划**
  - [ ] 复杂任务自动分解为子任务
  - [ ] 支持任务执行中断

- [ ] **多渠道适配器**
  - [ ] Telegram 适配器
  - [ ] Discord 适配器
  - [ ] Slack 适配器

- [ ] **用户自定义 Skill 导入**
  - [ ] skills search 命令（搜索技能市场）
  - [ ] 技能评分和反馈机制

---

## ✅ 已完成

### 架构设计
- [x] 架构设计文档
- [x] 目标目录结构设计（参考 Hermes）
- [x] TODO.md 任务清单
- [x] 编码规范 (rule.md)

### 目录结构重构（规划中）
> 详见 [docs/architecture/restructure-plan.md](docs/architecture/restructure-plan.md)

**目标结构**：
```
Handsome-Agent/
├── agent/                    # 🤖 Agent 核心
│   ├── agent_loop.py        # Agent Loop
│   ├── schemas.py           # 数据模型
│   ├── curator/             # Curator（自我进化）
│   ├── llm/                 # LLM Provider
│   └── templates/           # Agent 模板
│
├── skills/                   # 🛠️ 技能系统（用户数据）
├── gateway/                  # 🚪 网关
├── executor/                  # 🏃 执行层
├── tools/                    # 🛠️ 工具定义
├── common/                    # 📦 基础设施
├── lightweight/              # ⚡ 轻量版（零依赖）
├── cli/                      # 💬 CLI
├── tests/                    # 🧪 测试
├── docs/                     # 📚 文档
└── api/                      # 📋 OpenAPI
```

### 决策层
- [x] Agent Loop (ReAct 实现 + 自我进化集成)
- [x] LLM Provider 接口
- [x] OpenAI Provider / Claude Provider
- [x] Tool Registry
- [x] 技能系统（匹配、加载、注册、追踪、生命周期、合并）
- [x] Curator 自我进化（轨迹评估、技能合成）

### 执行层
- [x] Executor 基类
- [x] Shell 执行器
- [x] Docker 执行器

### 接入层
- [x] Gateway 核心接口
- [x] 标准化消息格式
- [x] HTTP/WebSocket 适配器
- [x] CLI 适配器

### 其他
- [x] 容器化部署 (Docker)
- [x] OpenAPI 规范
- [x] 测试套件

---

## 📝 技术栈

| 组件 | 技术选型 | 状态 |
|------|---------|------|
| 语言 | Python 3.11+ | ✅ |
| Web 框架 | 标准库 HTTP Server | ✅ |
| 数据库 | SQLite + FTS5 | ✅ |
| LLM | OpenAI / Claude | ✅ |
| 向量检索 | ChromaDB / 简单实现 | ✅ |
| 容器化 | Docker | ✅ |

---

## 🚀 快速开始

```bash
# 轻量版（无需依赖）
python -m lightweight

# 完整版
pip install -r requirements.txt
python -m cli.main chat

# Docker
docker-compose up -d

# 测试
pytest tests/unit/ -v
```

---

*最后更新: 2026-06-01 - 添加目录结构重构任务*