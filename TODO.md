# Handsome Agent 开发任务清单

> Hermes-Brain + OpenClaw-Body 架构实现任务

---

## 📋 待完成任务

### 🔴 高优先级

- [ ] **完善单元测试**
  - [ ] 修复剩余 6 个失败的测试
  - [ ] 添加集成测试
  - [ ] 添加 E2E 测试
  - [ ] 确保 CI 通过

- [ ] **自我进化完善**（越用越好用）
  - [ ] 真实工具执行集成（目前是模拟）
  - [ ] LLM 辅助轨迹分析
  - [ ] 技能优先级和排序
  - [ ] 技能版本管理
  - [ ] 遗忘机制（删除低置信度技能）

- [ ] **梦境能力（Dream Capability）**
  - [ ] 设计梦境架构（梦境生成、梦境分析、梦境学习）
  - [ ] 模拟人类睡眠时的潜意识处理机制
  - [ ] 梦境场景生成（模拟各种环境和情境）
  - [ ] 从梦境中提取有价值的洞察和创意
  - [ ] 参考：agent/dreaming.py 模块设计

- [ ] **任务拆解与可打断重规划**
  - [ ] 复杂任务自动分解为子任务
  - [ ] 支持任务执行中断
  - [ ] 中断后智能重规划能力
  - [ ] 子任务状态追踪和回滚机制
  - [ ] 参考：agent/trajectory.py 轨迹机制

- [ ] **OpenHuman 能力集成**
  - [ ] OAuth 2.0 认证流程实现
  - [ ] 获取用户数据压缩片段能力
  - [ ] 数据隐私和安全处理
  - [ ] 参考：agent/openhuman.py 模块

### 🟡 中优先级

- [ ] **多渠道适配器**
  - [ ] Telegram 适配器
  - [ ] Discord 适配器
  - [ ] Slack 适配器
  - [ ] 飞书适配器

- [ ] **性能优化（高级语言替代）**
  - [ ] 评估热点模块性能瓶颈
  - [ ] 核心路由模块考虑 Rust/Go/C 重写
  - [ ] LLM 推理加速（考虑 TensorRT、vLLM）
  - [ ] 向量检索性能优化
  - [ ] 保持 Python 胶水层和插件扩展能力

- [ ] **OpenClaw & Hermes 用例借鉴**
  - [ ] 研究 OpenClaw computer-use 场景
  - [ ] 研究 Hermes 高级推理模式
  - [ ] 整合优秀用例到 Handsome Agent
  - [ ] 保持架构兼容性和扩展性

- [ ] **监控与日志**
  - [ ] 集成 Prometheus 指标
  - [ ] 添加结构化日志
  - [ ] 实现告警机制

- [ ] **性能优化（基础）**
  - [ ] 实现响应缓存
  - [ ] 添加连接池
  - [ ] 性能基准测试

---

## ✅ 已完成

### 架构设计
- [x] 架构设计文档 (docs/ARCHITECTURE.md)
- [x] 三层架构目录结构
- [x] 项目依赖清单 (requirements.txt)
- [x] TODO.md 任务清单

### 接入层 (Adapter Layer)
- [x] Gateway 核心接口
- [x] 标准化消息格式 (message.py)
- [x] HTTP/WebSocket 适配器
- [x] CLI 适配器
- [x] 通信协议定义
- [x] Gateway CLI 入口

### 决策层 (Brain Layer)
- [x] Brain Service API
- [x] Agent Loop (ReAct 实现 + 自我进化集成)
- [x] LLM Provider 接口
- [x] OpenAI Provider
- [x] Claude Provider
- [x] LLM Factory
- [x] Tool Schema 定义
- [x] Tool Registry
- [x] 向量存储 (简化版)
- [x] SQLite + FTS5 存储
- [x] 上下文压缩器 (Summarizer)
- [x] 技能匹配器
- [x] 技能加载器
- [x] 技能注册表
- [x] ChromaDB 向量存储支持
- [x] Brain Service CLI 入口
- [x] **自我进化集成**
  - 轨迹记录集成到 Agent Loop
  - Curator 自动触发
  - 已学习技能加载和使用
  - 新 API: /api/v1/trajectories, /api/v1/trajectories/stats

### 执行层 (Executor Layer)
- [x] Executor 基类
- [x] Shell 执行器
- [x] Docker 执行器

### Tool Schema 对齐层
- [x] Schema Registry
- [x] Hermes Tool Adapter
- [x] OpenClaw Tool Adapter
- [x] 文件工具定义
- [x] Shell 工具定义
- [x] Web 工具定义
- [x] **OpenClaw 高级工具定义**
  - str_replace_editor (字符串替换编辑)
  - computer_use (GUI 自动化)
  - multi_edit (多位置编辑)
  - create_file (创建新文件)
  - search_files (文件内容搜索)
  - insert_content_at_line (行插入)
  - view_lines (行范围查看)

### 后处理层 (Curator)
- [x] 轨迹评估器
- [x] 技能合成器
- [x] 技能写入器
- [x] **TrajectoryRecorder 轨迹记录器**
  - 记录每个 Thought/Action/Observation
  - 持久化到 JSON 文件
  - 支持反馈机制
- [x] **Curator 自我进化核心**
  - 轨迹自动评估
  - 技能自动合成
  - 自动学习到 ~/.skills/
  - 用户反馈闭环

### 共享模块
- [x] 配置管理 (shared/config.py)
- [x] 日志配置 (shared/logging.py)
- [x] 公共异常 (shared/exceptions.py)
- [x] 公共数据模型 (shared/models.py)

### 容器化部署
- [x] docker-compose.yml
- [x] Dockerfile.brain
- [x] Dockerfile.gateway

### 测试
- [x] Agent Loop 测试
- [x] LLM 模块测试
- [x] Gateway 测试
- [x] Message 测试
- [x] Executor 测试
- [x] Tool Registry 测试

### 其他
- [x] OpenAPI 规范 (api/brain_service.yaml)

---

## 📝 技术栈

| 组件 | 技术选型 | 状态 |
|------|---------|------|
| 语言 | Python 3.11+ | ✅ |
| Web 框架 | FastAPI | ✅ |
| 数据库 | SQLite + FTS5 | ✅ |
| LLM | OpenAI / Claude | ✅ |
| 向量检索 | ChromaDB / 简单实现 | ✅ |
| 容器化 | Docker | ✅ |
| 异步任务 | Celery | ⏳ 可选 |

---

## 🚀 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 运行 Brain Service (规则模式)
python -m brain.service

# 运行 Brain Service (LLM 模式)
python -m brain.service --llm openai --api-key YOUR_KEY

# 运行 Gateway
python -m adapter.gateway --cli

# Docker 运行
docker-compose up -d

# 运行测试
pytest tests/unit/ -v
```

---

## 🐳 Docker 部署

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| BRAIN_SERVICE_PORT | 8001 | Brain Service 端口 |
| GATEWAY_PORT | 8000 | Gateway 端口 |
| BRAIN_SERVICE_URL | http://brain:8001 | Brain Service 地址 |
| MAX_ITERATIONS | 10 | Agent 最大迭代次数 |
| TIMEOUT_SECONDS | 60 | 超时时间 |

---

*最后更新: 2024*