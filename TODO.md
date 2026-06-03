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

- [ ] **上下文压缩 Rail (ContextCompressionRail)**
  
  > 基于 Rail 机制的上下文压缩实现，参考 Hermes 的 ContextCompressor
  
  #### 📐 设计方案
  
  **目标**：通过 Rail 机制将上下文压缩插入到 Agent 执行流程中
  
  **核心组件**：
  ```
  agent/rails/
  ├── rail.py                    # Rail 基类 (已有)
  ├── manager.py                 # Rail 管理器 (已有)
  ├── context_compression_rail.py # ⭐ 上下文压缩 Rail (新增)
  └── ...
  
  agent/context/
  ├── context_engine.py          # ContextEngine 基类 (已有)
  ├── context_compressor.py      # ⭐ 压缩引擎实现 (新增)
  └── token_estimator.py        # ⭐ Token 估算器 (新增)
  
  common/
  ├── redact.py                  # ⭐ 敏感信息脱敏 (新增)
  └── ...
  ```
  
  **压缩算法（5阶段）**：
  1. **预压缩修剪** (no LLM) → 工具输出摘要化、去重、截断
  2. **头部保护** → 系统提示 + 前 N 条消息
  3. **尾部保护** (token预算) → 最近 ~20K tokens
  4. **中间摘要化** (LLM) → 结构化摘要模板
  5. **工具对修复** → 修复孤立的 tool_call/result 对
  
  **Rail Hook 触发点**：
  | Hook | 用途 |
  |------|------|
  | `before_llm_call` | 检查 token 预算，判断是否需要压缩 |
  | `after_llm_call` | 获取实际 token 使用量，触发压缩 |
  | `on_checkpoint` | 在关键节点主动触发压缩 |
  
  #### 📋 实现步骤
  
  **阶段 1：基础架构 (核心)**
  - [x] 1.1 创建 `common/redact.py` - 敏感信息脱敏模块 ✅
    - [x] `redact_sensitive_text()` - 脱敏 API keys, tokens, passwords
    - [x] `redact_messages()` - 批量消息脱敏
    - [x] `redact_json()` - JSON 对象递归脱敏
    - [x] 支持多种密钥格式检测
  - [x] 1.2 创建 `agent/context/token_estimator.py` - Token 估算器 ✅
    - [x] `estimate_messages_tokens_rough()` - 粗略估算
    - [x] `estimate_request_tokens_rough()` - 完整请求估算
    - [x] `get_model_context_length()` - 模型上下文长度
    - [x] `TokenBudget` 类 - Token 预算追踪
  - [x] 1.3 创建 `agent/context/context_compressor.py` - 压缩引擎 ✅
    - [x] `ContextCompressor` 类（继承 ContextEngine）
    - [x] `_prune_old_tool_results()` - 工具输出修剪
    - [x] `_generate_summary()` - LLM 摘要生成
    - [x] `_sanitize_tool_pairs()` - 工具对修复
    - [x] `compress()` - 主压缩入口
  
  **阶段 2：Rail 实现**
  - [x] 2.1 创建 `agent/rails/context_compression_rail.py` ✅
    - [x] `ContextCompressionRail` 类（继承 Rail）
    - [x] `before_llm_call()` - 预检查
    - [x] `after_llm_call()` - 压缩触发
    - [x] `on_checkpoint()` - 主动压缩点
  - [x] 2.2 更新 `agent/rails/manager.py` ✅
    - [x] 添加压缩 Rail 注册支持
    - [x] 添加压缩状态查询接口
  
  **阶段 3：集成与优化**
  - [x] 3.1 更新 Agent 主循环集成压缩 Rail ✅
    - [x] `CompressedReActLoop` - 带压缩的 ReAct 循环
    - [x] `CompressionAwareReActLoop` - 压缩感知的 ReAct 循环
    - [x] 迭代后自动检查压缩
  - [x] 3.2 添加配置文件支持 ✅
    - [x] `CompressionConfig` - 压缩配置类
    - [x] `compression_config.py` - 配置模块
    - [x] 支持环境变量配置 (`HANDSOME_COMPRESSION_*`)
  - [x] 3.3 Anti-thrashing 保护 ✅
    - [x] 跟踪压缩效率
    - [x] 连续低效压缩后自动回退
    - [x] 压缩失败冷却期
  
  **阶段 4：CLI 命令**
  - [x] 4.1 添加 `/compress` 命令 ✅
    - [x] 手动触发压缩
    - [x] 支持 `--focus` 参数
  - [x] 4.2 添加压缩状态查询 ✅
    - [x] `/usage` - 显示 Token 使用统计
    - [x] `/compression-status` - 显示压缩状态

### 🔵 待增强功能 (对齐 Hermes)

> 参考 `e:\hermes-agent-study\agent\prompt_builder.py` 和 `context_engine.py`

#### 🔴 高优先级 - 上下文拼装 (Context Assembly)

> 对标 Hermes 的完整上下文拼装实现 ✅ Phase 1 已完成

**目标**：让 Handsome Agent 的上下文拼装与 Hermes 一样完善

**架构设计**：
```
ContextBuilder (💾 Context)     # 上下文构建
    ├── AgentDefinitionLoader  # 加载 Agent 定义
    ├── build_system_prompt()  # 构建系统提示词
    └── _build_guidance()     # 5 类指导性文本

LLMToolSelector (🔧 ToolSelect) # 工具选择
    ├── register_tool()        # 工具注册
    ├── select_tool()         # 工具选择
    └── execute()             # 工具执行
```

| 任务 | 状态 | 说明 |
|------|------|------|
| **创建 ContextBuilder 模块** | ✅ 完成 | 独立的上下文构建器 |
| **添加指导性文本** | ✅ 完成 | 5 类指导文本（参考 Hermes） |
| **LLMToolSelector 简化** | ✅ 完成 | 移除上下文拼装逻辑，改为委托 |
| **增强 guidance 内容** | ✅ 完成 | 参考 Hermes 完善所有 guidance |
| **Prompt 注入检测** | 🟡 中优先级 | 危险模式扫描 |
| **上下文文件扫描** | 🟡 中优先级 | .handsome.md 等文件 |
| **模型特定指导** | 🟢 低优先级 | GPT/Gemini 专用指导 |
| **三层架构优化** | 🟢 低优先级 | stable/context/volatile |

**已完成的功能**：
- ✅ Memory Usage - 记忆使用规范
- ✅ Session Search - 跨会话搜索指导
- ✅ Skills - 技能保存和维护指导
- ✅ Tool-Use Enforcement - 工具使用纪律
- ✅ Act Without Asking - 主动行动原则

**文档位置**：`docs/modules/context-compression.md` (上下文拼装 + 上下文压缩)

#### 🔴 高优先级

- [x] **迭代摘要更新 (Iterative Summary)** ✅
  - [x] 实现 `_previous_summary` 状态追踪
  - [x] 支持基于前一次摘要的增量更新
  - [x] 避免重复信息丢失

- [x] **聚焦压缩 (Focus Topic)** ✅
  - [x] `_generate_summary()` 中使用 focus_topic 参数
  - [x] CLI 命令 `/compress --focus=X` 实际生效
  - [x] 保留特定主题的详细信息

- [x] **更完整的摘要模板 (12 字段)** ✅
  - [x] 添加 `## Constraints & Preferences`
  - [x] 添加 `## In Progress`
  - [x] 添加 `## Blocked`
  - [x] 添加 `## Relevant Files`
  - [x] 添加 `## Critical Context`

#### 🟡 中优先级

- [ ] **辅助模型摘要**
  - [ ] 实现 `auxiliary_client` 模块
  - [ ] 支持便宜的辅助模型 (如 GPT-4o-mini)
  - [ ] 配置 `summary_model` 参数

- [ ] **增强图片处理**
  - [ ] 支持 base64 截图处理
  - [ ] 实现多种图片 placeholder 格式
  - [ ] 精确计算图片 token

- [ ] **更详细的安全前导语 (Preamble)**
  - [ ] 添加防注入提示
  - [ ] 明确标注摘要为参考内容

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




*最后更新: 2026-06-02 - 对齐 Hermes 待增强功能清单*