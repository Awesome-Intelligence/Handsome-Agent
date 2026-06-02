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

jiuwenswarm 的 Rail 机制：
├── TaskPlanningRail      → 通过 register_rail() 注册
├── StreamEventRail       → 通过 register_rail() 注册
├── PermissionsRail       → 通过 register_rail() 注册
└── RuntimePromptRail     → 通过 register_rail() 注册

- [ ] **有些模块不打印日志？**
- [ ] **jiuwen的todo能力是不是也可以作为一个子层**
- [ ] 可以让agent持续不断地思考，像人一样（让用户配置一个便宜的小模型，或者本地的模型）**

### � 循环流程完善（对齐 Hermes）

> 参考 Hermes `agent/conversation_loop.py` 的完整循环实现

#### 🔴 高优先级 - 核心循环机制

- [ ] **实现循环机制**
  - [ ] 将单次 `engine.process()` 改为 `while` 循环
  - [ ] 支持多轮工具调用直到任务完成
  - [ ] 循环条件：`api_call_count < max_iterations and iteration_budget.remaining > 0`

- [ ] **迭代预算控制 (IterationBudget)**
  - [ ] 创建 `IterationBudget` 类
  - [ ] 控制最大迭代次数，防止无限循环
  - [ ] 支持 grace call（预算耗尽后给一次额外机会）

- [ ] **中断处理机制**
  - [ ] 实现 `interrupt_requested` 检查
  - [ ] 支持用户中断正在执行的 Agent
  - [ ] 中断后优雅退出循环

#### 🟡 中优先级 - 错误处理与优化

- [ ] **上下文压缩 (Context Compression)**
  - [ ] Preflight compression：对话前检查是否超限
  - [ ] 循环内压缩：压缩过长的对话历史
  - [ ] `estimate_request_tokens_rough()` 估算 token 数量

- [ ] **重试机制**
  - [ ] `invalid_tool_retries`：工具调用失败重试
  - [ ] `invalid_json_retries`：JSON 解析失败重试
  - [ ] `empty_content_retries`：空响应重试
  - [ ] `incomplete_scratchpad_retries`：不完整思考重试

- [ ] **并发工具执行**
  - [ ] 实现 `execute_tool_calls_concurrent()`
  - [ ] 多个不相关工具并行执行
  - [ ] 工具延迟 (`tool_delay`) 配置

#### 🟢 低优先级 - 高级功能

- [ ] **外部内存预取**
  - [ ] `MemoryManager.prefetch_all()` 在工具执行前预取
  - [ ] 缓存预取结果避免重复调用

- [ ] **插件系统**
  - [ ] `pre_llm_call` 钩子：LLM 调用前处理
  - [ ] `on_session_end` 钩子：会话结束处理
  - [ ] 插件上下文注入

- [ ] **技能/记忆 Nudge**
  - [ ] `skill_nudge_interval`：周期性提示更新技能
  - [ ] `memory_nudge_interval`：周期性提示更新记忆
  - [ ] Background Review：后台异步执行

### 🟡 中优先级

- [ ] setup里的选项内容排序，emoj、排版、高度太低

- [ ] **梦境能力（Dream Capability）**
  - [ ] 设计梦境架构
  - [ ] 模拟人类睡眠时的潜意识处理机制

- [ ] **任务拆解与可打断重规划**
  - [ ] 复杂任务自动分解为子任务
  - [ ] 支持任务执行中断

### 📦 待导入的 Hermes 内置工具

> 参考 `e:\hermes-agent-study\tools\` 目录

#### 🔴 高优先级

- [ ] **browser_cdp_tool.py** - 浏览器 CDP 工具
  - [ ] WebSocket 连接管理
  - [ ] Chrome DevTools Protocol 封装
  - [ ] 跨进程 iframe 路由

- [ ] **send_message_tool.py** - 跨平台消息发送
  - [ ] Telegram / Slack / Discord 集成
  - [ ] WhatsApp / Signal / Matrix 集成
  - [ ] 飞书 / 企业微信 / 钉钉 集成

#### 🟡 中优先级

- [ ] **transcription_tools.py** - 语音转文字 (STT)
  - [ ] Local Whisper (faster-whisper)
  - [ ] Groq / OpenAI / Mistral / xAI 多个提供商
  - [ ] 音频格式验证和转换

- [ ] **tts_tool.py** - 文字转语音 (TTS)
  - [ ] Edge TTS / ElevenLabs / OpenAI TTS
  - [ ] MiniMax / Mistral / Gemini / xAI TTS
  - [ ] 本地 TTS: NeuTTS / KittenTTS / Piper

- [ ] **x_search_tool.py** - X 平台搜索
  - [ ] xAI Responses API 集成
  - [ ] 日期范围和用户过滤
  - [ ] 引用和内联标注解析

- [ ] **skills_hub.py** - 技能中心源适配器
  - [ ] GitHub / WellKnown / UrlSource
  - [ ] LobeHub / ClawHub / ClaudeMarketplace
  - [ ] 并行多源搜索和统一接口

### 🚪 渠道接入

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

### 工具层 (从 Hermes 参考)
- [x] **checkpoint_manager.py** - Git 快照管理器 (自动回滚)
- [x] **todo_tool.py** - 待办事项管理
- [x] **interrupt.py** - 线程级中断信号
- [x] **skill_manager_tool.py** - 技能管理 (已完善)
- [x] **memory_tool.py** - 持久化记忆 (已完善)
- [x] **kanban_tool.py** - 看板任务管理 (已完善)

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




*最后更新: 2026-06-02 - 增加 Hermes 循环流程对齐任务*