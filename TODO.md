# Handsome Agent 开发任务清单

> Hermes-Brain + OpenClaw-Body 架构实现任务

---

## 📋 待完成任务

### 🔴 高优先级

- [ ] **完善单元测试**
  - [ ] 修复剩余测试失败问题
  - [ ] 添加集成测试
  - [ ] 添加 E2E 测试
  - [ ] 确保 CI 通过

- [ ] **遗忘机制（删除低置信度技能）**
- [ ] **满足harness架构**

- [ ] **日志里的层级没有显示全**
- [ ] **有些模块不打印日志？**
- [ ] **jiuwen的todo能力是不是也可以作为一个子层**
- [ ] 可以让agent持续不断地思考，像人一样（让用户配置一个便宜的小模型，或者本地的模型）**

### 🟡 中优先级

- [ ] setup里的选项内容排序，emoj、排版、高度太低

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

### 目录结构重构 ✅ v3.0.0

**已完成的重构工作**：
- [x] 删除 `brain/`, `brain_curator/`, `core/`, `shared/`, `adapter/`, `llm_integration/` 目录
- [x] 重命名 `shared/` → `common/`
- [x] 合并 `brain_curator/` → `agent/curator/`
- [x] 合并 `advanced_reasoning/` → `agent/advanced_reasoning/`
- [x] 合并 `brain/llm/` → `agent/llm/`
- [x] 删除 `config/`, `logs/`, `sessions/` 目录
- [x] 更新所有导入路径
- [x] 更新 docs/index.md
- [x] 更新 README.md
- [x] 更新 rule.md

**最终目录结构**：
```
Handsome-Agent/
├── agent/                    # 🤖 Agent 核心
│   ├── curator/             #   Curator（自我进化）
│   ├── llm/                 #   LLM Provider
│   ├── advanced_reasoning/   #   高级推理
│   └── templates/           #   模板
│
├── skills/                   # 🛠️ 技能系统
├── gateway/                  # 🚪 网关
├── executor/                 # 🏃 执行层
├── tools/                    # 🛠️ 工具定义
├── common/                   # 📦 基础设施
├── cli/                      # 💬 CLI
├── tests/                    # 🧪 测试
├── docs/                     # 📚 文档
└── api/                      # 📋 OpenAPI
```

### 架构设计
- [x] 架构设计文档
- [x] 目标目录结构设计（参考 Hermes）
- [x] 编码规范 (rule.md)

### 决策层
- [x] Agent Loop (ReAct 实现 + 自我进化集成)
- [x] LLM Provider 接口 (OpenAI/Claude)
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
- [x] CLI 适配器

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
# CLI 交互
pip install -r requirements.txt
python -m cli.main setup
python -m cli.main chat

# Docker
docker-compose up -d

# 测试
pytest tests/unit/ -v
```

---

*最后更新: 2026-06-01 - v3.0.0 目录结构重构完成*