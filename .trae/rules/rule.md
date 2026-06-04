# Handsome Agent 编码规范

> Hermes-Brain + OpenClaw-Body 双核驱动的模块化 AI 智能助手

***

回复的最后一句话请使用“我已经帅帅地完成了任务！”。

**每次写完代码，必须同步更新相关的readme等文档及测试用例。**

**每次修改或增加功能代码都要跑一遍ci确保功能正常。**

## 参考项目路径

**重要提示**：当需要参考 OpenClaw、Hermes 和 jiuwenswarm 项目时，请使用以下路径：

- OpenClaw 项目：`e:\openclaw-for-study`
- Hermes 项目：`e:\hermes-agent-study`
- jiuwenswarm 项目：`e:\jiuwenswarm-study`

这些路径包含完整的项目代码和配置，可用于参考实现方式。

***

## 一、目标目录结构 ⭐ **强制约束**

### 1.1 目录架构图

```
Handsome-Agent/
│
├── agent/                    # 🧠 Decision
│   ├── agent.py             #   🧠 Decision - Agent 协调器
│   ├── session.py           #   🧠 Decision - 💾 Memory - 会话管理
│   ├── response_router.py  #   🧠 Decision - 响应路由
│   ├── self_improvement.py  #   🧠 Decision - 自我改进
│   ├── context/             #   🧠 Decision - 📊 Context
│   │   ├── context_engine.py
│   │   └── prompt_builder.py
│   ├── curator/             #   🧠 Decision - 🔬 Curator - 自我进化
│   │   ├── curator.py
│   │   ├── trajectory.py
│   │   └── trajectory_recorder.py
│   ├── llm/                 #   🧠 Decision - 🤖 LLM - LLM 提供商
│   │   ├── openai_provider.py
│   │   ├── claude_provider.py
│   │   ├── llm_web_search.py
│   │   └── llm_terminal_command.py
│   ├── memory/              #   🧠 Decision - 💾 Memory - 记忆存储
│   │   └── markdown_memory.py
│   ├── skills/              #   🧠 Decision - 📋 Skills - 技能管理
│   │   └── skill_manager.py
│   ├── task/               #   🧠 Decision - ✅ Task - 任务管理
│   │   ├── task_planner.py
│   │   └── task_executor.py
│   ├── rails/               #   Rail 拦截器（不是子层）
│   │   ├── rail.py          #   Rail 基类
│   │   ├── manager.py       #   Rail 管理器
│   │   ├── task_event_rail.py #   任务事件 Rail
│   │   └── examples.py      #   Rail 示例
│   ├── react/               #   ReAct 执行引擎（不是子层）
│   │   ├── loop.py          #   ReAct 循环引擎
│   │   └── context.py       #   执行上下文
│   ├── tool_selector/       #   🧠 Decision - 🔧 ToolSelect - 工具选择
│   │   └── llm_tool_selector.py
│   └── templates/           #   Agent 模板
│
├── tools/                    # 🏃 Execution - 🛠️ ToolExec - 工具定义
│   ├── registry.py           #   工具注册表
│   ├── app_launcher.py      #   应用启动
│   ├── file_tools_bridge.py #   文件工具
│   ├── cronjob_tool.py      #   定时任务
│   ├── vision_tool.py       #   图片分析
│   ├── memory_tool.py       #   记忆工具
│   └── web_tools.py         #   网络工具
│
├── skills/                   # 🧠 Decision - 📋 Skills - 技能系统
│   ├── registry.py          #   技能注册
│   ├── matcher.py          #   技能匹配
│   ├── loader.py            #   技能加载
│   ├── lifecycle.py         #   生命周期
│   ├── merger.py            #   技能合并
│   ├── system/              #   系统内置技能
│   └── user/                #   用户技能
│
├── gateway/                  # 🚪 Access - 🚪 Gateway - HTTP 网关
│   ├── server.py           #   HTTP 服务器
│   ├── gateway.py           #   网关核心
│   ├── gateway_cli.py      #   网关 CLI
│   └── adapters/            #   渠道适配器
│
├── executor/                 # 🏃 Execution - 执行器
│   ├── shell.py            #   🏃 Execution - 🐚 ShellExec - Shell 执行
│   └── docker.py           #   🏃 Execution - 🐳 DockerExec - Docker 执行
│
├── common/                   # 🔧 System - 基础设施
│   ├── config.py           #   配置管理
│   ├── logging_manager.py  #   日志管理
│   ├── exceptions.py        #   异常定义
│   └── state.py            #   状态管理
│
├── cli/                      # 🚪 Access - 💬 CLI - 命令行
│   ├── main.py             #   主入口
│   └── modern_cli.py       #   现代 CLI
│
├── tests/                    # 测试套件
│   ├── unit/
│   └── integration/
│
├── docs/                     # 文档
│   └── flows.md            #   用户交互流程详解
│
└── api/                      # OpenAPI 规范
```

### 1.2 目录职责

| 目录             | 类型     | 职责             | 可导入其他模块              |
| -------------- | ------ | -------------- | -------------------- |
| `common/`      | **代码** | 基础设施（配置、日志、异常） | ❌ 无                  |
| `agent/`       | **代码** | Agent 核心逻辑     | `common/`            |
| `skills/`      | **数据** | 技能系统（用户数据）     | `agent/`             |
| `tools/`       | **代码** | 工具定义           | `agent/`             |
| `executor/`    | **代码** | 执行层            | `agent/`             |
| `gateway/`     | **代码** | 网关             | `agent/`             |
| `cli/`         | **代码** | CLI            | `agent/`, `gateway/` |
| `lightweight/` | **代码** | 轻量版（独立）        | ❌ 无                  |
| `tests/`       | **代码** | 测试             | 所有模块                 |

### 1.3 禁止的目录 ⛔

以下目录已废弃，**禁止新建文件**：

- `core/` → 已合并到 `agent/` 或 `common/`
- `brain/` → 已合并到 `agent/`
- `brain_curator/` → 已合并到 `agent/curator/`
- `adapter/` → 已合并到 `gateway/`
- `shared/` → 已重命名为 `common/`
- `llm_integration/` → 已合并到 `agent/llm/`
- `plugins/` → 已废弃
- `lightweight/` → 已废弃（功能已合并到 `agent/`）

### 1.4 层级与目录结构约束 ⭐ **强制约束**

#### 核心原则

| 原则          | 说明                            |
| ----------- | ----------------------------- |
| **层级决定职责**  | Layer 和 Sublayer 是逻辑分层，决定代码职责 |
| **目录是物理组织** | Directory 是代码文件位置             |
| **目录可含多层**  | 一个目录可以包含多个层/子层的代码             |
| **子层可跨目录**  | 一个子层的代码可以分布在多个目录              |

#### 层-子层定义

| Layer        | Emoji | Sublayers                                                                   | 说明        |
| ------------ | ----- | --------------------------------------------------------------------------- | --------- |
| 🚪 Access    | 🚪    | 💬 CLI, 🚪 Gateway                                                          | 用户接入、请求入口 |
| 🧠 Decision  | 🧠    | 🤖 LLM, 🔧 ToolSelect, ✅ Task, 💾 Memory, 📋 Skills, 🔬 Curator, 📊 Context | 智能决策、推理   |
| 🏃 Execution | 🏃    | 🐚 ShellExec, 🐳 DockerExec, 🛠️ ToolExec                                   | 工具执行、操作   |
| 🔧 System    | 🔧    | (无)                                                                         | 系统基础设施    |

#### 核心概念澄清

| 概念        | 本质   | 说明                            |
| --------- | ---- | ----------------------------- |
| **子层**    | 日志分类 | `💾 Memory`, `✅ Task` 等用于区分日志 |
| **ReAct** | 执行模式 | 循环 → 决策 → 执行，不是子层             |
| **Rail**  | 拦截器  | 可插拔的 before/after 钩子，不是子层     |

#### 目录与层级映射

| 目录               | Primary Layer | Sublayers                                 | 约束                |
| ---------------- | ------------- | ----------------------------------------- | ----------------- |
| `agent/`         | 🧠 Decision   | 🤖 LLM, 💾 Memory, 🔬 Curator, 📊 Context | Agent 核心代码        |
| `agent/llm/`     | 🧠 Decision   | 🤖 LLM                                    | LLM Provider 实现   |
| `agent/curator/` | 🧠 Decision   | 🔬 Curator                                | 自我进化              |
| `agent/task/`    | 🧠 Decision   | ✅ Task                                    | 任务规划与执行           |
| `agent/rails/`   | 🧠 Decision   | (无固定子层)                                   | Rail 拦截器机制        |
| `agent/react/`   | 🧠 Decision   | (无固定子层)                                   | ReAct 执行引擎        |
| `tools/`         | 🏃 Execution  | 🛠️ ToolExec                              | 工具定义（主体）          |
| `executor/`      | 🏃 Execution  | 🐚 ShellExec, 🐳 DockerExec               | 执行器               |
| `gateway/`       | 🚪 Access     | 🚪 Gateway                                | HTTP 网关           |
| `cli/`           | 🚪 Access     | 💬 CLI                                    | 命令行入口             |
| `common/`        | 🔧 System     | (无)                                       | 基础设施，**禁止放其他层代码** |
| `skills/`        | 🧠 Decision   | 📋 Skills                                 | 技能系统              |

#### 文件注释规范

**新增文件必须在注释中标注层和子层**：

```python
# ✅ 正确：标注层-子层
def read_file(path):
    """Read file content."""
    # 🏃 Execution - 🛠️ ToolExec - 文件读取

# ❌ 错误：未标注
def read_file(path):
    """Read file content."""
```

**注释格式**：

```
# {Layer} - {Sublayer} - 功能描述
```

**示例**：

```python
# agent/llm_tool_selector.py
# 🧠 Decision - 🤖 LLM - 工具选择器

# tools/app_launcher.py
# 🏃 Execution - 🛠️ ToolExec - 应用启动

# agent/session.py
# 🧠 Decision - 💾 Memory - 会话管理

# executor/shell.py
# 🏃 Execution - 🐚 ShellExec - 命令执行
```

#### 约束规则

| 规则                          | 说明                                 | 违规处理  |
| --------------------------- | ---------------------------------- | ----- |
| `common/` 只属于 🔧 System     | 不能放其他层的代码                          | ⛔ 禁止  |
| `agent/` 可含多子层              | 🤖 LLM, 💾 Memory, 🔬 Curator 都在这里 | ✅ 允许  |
| `tools/` 主要在 🏃 Execution   | 但可以有 Decision 层的工具                 | ✅ 允许  |
| `executor/` 只在 🏃 Execution | 只放 Shell/Docker 执行器                | ✅ 允许  |
| 新文件必须标注层-子层                 | 在文件顶部注释中标注                         | ⚠️ 警告 |
| 层级变更必须同步文档                  | README, flows.md, rule.md          | ⚠️ 警告 |

#### 层级一致性检查

修改任何层级相关内容时，必须同步更新以下文档：

| 文档                  | 位置                           | 更新内容                        |
| ------------------- | ---------------------------- | --------------------------- |
| README              | `/README.md`                 | 项目目录结构                      |
| flows.md            | `/docs/flows.md`             | 层-子层-模块速查表                  |
| rule.md             | `/.trae/rules/rule.md`       | 层级定义、约束规则                   |
| logging\_manager.py | `/common/logging_manager.py` | LOG\_LAYERS, SUB\_LAYERS 定义 |

***

## 二、核心原则

### 2.0 强制约束声明 ⭐⭐⭐

**⚠️ 警告：以下约束由 Lint 检查强制执行，违反将导致 CI 失败**

#### 硬编码检测规则

| 违规类型 | 检测模式 | 正确做法 |
|---------|---------|---------|
| 意图理解硬编码 | `if "关键词" in text`, `re.match(".*关键词.*", ...)` | 使用 LLM 判断意图 |
| 敏感信息硬编码 | `password = "xxx"`, `api_key = "xxx"` | 从环境变量读取 |
| 路径分隔符硬编码 | `path.replace("/", "\\")` | 使用 `pathlib.Path` |
| ReAct 模式硬编码 | `if "做个" in query: use_react()` | 使用 LLM 决策 |

#### 自检清单（每次代码修改前必须检查）

- [ ] 代码中是否有意图判断的硬编码关键词？
- [ ] 代码中是否有敏感信息（密钥、密码）硬编码？
- [ ] 代码中是否有路径分隔符硬编码？
- [ ] 代码中是否有用硬编码判断 ReAct 模式的逻辑？
- [ ] 涉及用户意图理解的部分是否使用了 LLM？

#### 违反后果

- ❌ **Lint 失败**：Ruff 会检测到硬编码并报告错误
- ❌ **CI 阻塞**：PR 将无法合并直到修复
- ❌ **代码审查不通过**：违反规则将被要求重写

### 2.1 优先使用成熟开源组件

**必须遵循**：优先选择成熟、热门、维护活跃的开源库，避免重复造轮子。

| 场景       | 推荐库         | 原因       |
| -------- | ----------- | -------- |
| 终端菜单     | `inquirer`  | 跨平台，成熟稳定 |
| HTTP 客户端 | `httpx`     | 异步支持，现代化 |
| 日志       | `structlog` | 结构化，可扩展  |

**判断标准**：

- GitHub Stars > 1000
- 最近 6 个月有更新
- 有完善的文档和社区支持

### 2.2 模块化架构

**依赖规则**：

```
common/ (最底层，无依赖)
    ↑
agent/ (核心逻辑)
    ├── curator/ (自我进化)
    ├── llm/ (LLM Provider)
    └── templates/ (模板)
    ↑
gateway/ (通过 ACP 协议)
    ↑
cli/ (通过 API)
    ↑
tools/ (通过抽象接口)
    ↑
executor/ (通过抽象接口)
```

**禁止**：

- `common/` 依赖任何其他模块
- `executor/` 直接依赖 `agent/` 的具体实现
- `tools/` 直接依赖 `core/` 的具体实现

### 2.3 安全零信任

- **输入验证**：白名单机制，禁止信任用户输入
- **敏感信息**：从环境变量获取，日志中脱敏
- **路径安全**：防止路径遍历攻击
- **命令执行**：白名单 + 危险模式检测

### 2.4 意图理解必须使用 LLM

**必须遵循**：所有涉及用户意图理解、自然语言解析、语义识别的操作，必须优先使用 LLM。

| 禁止做法           | 必须做法     |
| -------------- | -------- |
| 硬编码关键词字典       | LLM 理解意图 |
| 正则表达式匹配意图      | LLM 语义识别 |
| 预定义意图分类        | LLM 动态决策 |
| 硬编码判断 ReAct 模式 | LLM 决策   |

**禁止行为示例**：

- ❌ `if "做个" in text: use_react()`
- ✅ `llm.judge(text): return use_react`

**唯一例外**：当 LLM 不可用时，才可以使用关键词作为降级方案。

### 2.5 容错降级

降级链：LLM → 关键词 → 规则 → 默认值

### 2.6 复杂任务先规划到 TODO

**必须遵循**：做复杂事情（多步骤、跨模块、需多个文件修改）时，必须先将任务分解并记录到 `TODO.md` 中。

### 2.7 层级架构一致性约束

**必须遵循**：README、日志系统、目录架构三者中的层级定义必须保持严格一致，禁止各自独立修改。

**英文命名约束**：所有与层级、模块相关的名称（如目录名、模块名、层级标识）必须使用英文命名，禁止翻译为中文。

**英文命名规则**：

| 类型          | 示例                                                    | 说明     |
| ----------- | ----------------------------------------------------- | ------ |
| 主层名称        | `access`, `decision`, `execution`, `system`           | 使用英文标识 |
| 子层名称        | `memory`, `skills`, `trajectory`, `curator`           | 使用英文标识 |
| 目录名称        | `agent/`, `skills/`, `gateway/`, `executor/`          | 使用英文命名 |
| 模块名称        | `memory.py`, `context_engine.py`, `prompt_builder.py` | 使用英文命名 |
| README 标题   | `Architecture`, `Key Features`, `Quick Start`         | 使用英文标题 |
| README 表格内容 | `Agent Core`, `Skills System`, `Gateway`              | 使用英文描述 |

**一致性约束范围**：

| 文档/模块     | 文件路径                         | 层级相关内容                       |
| --------- | ---------------------------- | ---------------------------- |
| README.md | `/README.md`                 | 三层架构图、目录结构、模块职责              |
| 日志系统      | `/common/logging_manager.py` | `LOG_LAYERS`、`SUB_LAYERS` 定义 |
| 编码规范      | `/.trae/rules/rule.md`       | 层级映射表、日志规范                   |

**禁止做法**：

- ❌ 修改 README 中的架构图但不同步日志系统配置
- ❌ 修改日志系统层级但不同步规则文档
- ❌ 修改目录结构但不更新 README 和日志映射

**必须做法**：

- ✅ 修改任何层级相关内容时，同步更新所有相关文档
- ✅ 在 PR 描述中明确说明层级变更范围
- ✅ 确保 CI 检查包含层级一致性验证

**责任归属**：

- 架构师：负责制定和维护层级定义规范
- 开发者：负责在修改时保持一致性
- 审核者：负责检查 PR 中的层级一致性

### 2.8 CI 与代码质量 ⭐ **强制约束**

**每次代码修改后，必须运行 CI 检查确保代码质量**：

```bash
# 运行测试
pytest tests/unit/ -v

# 检查语法
python -m py_compile agent/ tools/ cli/ common/
```

**禁止行为**：

- ❌ 修改代码但不运行测试
- ❌ 提交有测试失败的代码
- ❌ 提交有语法错误的代码

**必须行为**：

- ✅ 运行 `pytest tests/unit/` 确保测试通过
- ✅ 运行 `python -m py_compile <module>` 确保语法正确
- ✅ 检查日志输出是否有 ERROR 级别错误

### 2.9 Logging with Unified LayerLogger

**Must follow**: All logging must use the unified logger from `common/logging_manager.py`. Direct use of `logging.getLogger()` is prohibited.

**Layer and Sublayer definitions**: See [1.4 层级与目录结构约束](#14-层级与目录结构约束-⭐-强制约束) for complete definitions.

**Log Format Specification**:

```
# With sublayer
INFO - [🚪MainLayer] - [/💾SublayerName] - (ModuleName) message

# Without sublayer
INFO - [🚪MainLayer] - (ModuleName) message
```

**Examples**:

```
# With sublayer (Memory)
INFO - 🧠 [Decision] - [/💾Memory] - (MemoryManager) Retrieving memory

# With sublayer (ToolExec)
INFO - 🏃 [Execution] - [/🛠️ToolExec] - (ToolExecutionEngine) Executing tool

# Without sublayer (Config loading)
INFO - 🧠 [Decision] - (LLMDrivenDecisionEngine) Initialization complete
```

**Module-Layer Mapping**:

| Module/Directory             | Logger Function          | Main Layer   | Recommended Sublayer    |
| ---------------------------- | ------------------------ | ------------ | ----------------------- |
| `agent/`                     | `get_decision_logger()`  | 🧠 Decision  | Based on submodule      |
| `agent/memory.py`            | `get_decision_logger()`  | 🧠 Decision  | `memory`                |
| `agent/curator/`             | `get_decision_logger()`  | 🧠 Decision  | `curator`               |
| `agent/llm/`                 | `get_decision_logger()`  | 🧠 Decision  | `llm`                   |
| `agent/llm_tool_selector.py` | `get_decision_logger()`  | 🧠 Decision  | `tool_select`           |
| `agent/task/`                | `get_task_logger()`      | 🧠 Decision  | `task`                  |
| `agent/rails/`               | `get_task_logger()`      | 根据 Rail 类型   | Rail 拦截器                |
| `agent/react/`               | `get_task_logger()`      | ✅ Task       | ReAct 执行引擎              |
| `executor/`                  | `get_execution_logger()` | 🏃 Execution | Based on execution type |
| `tools/`                     | `get_execution_logger()` | 🏃 Execution | `tool_exec`             |
| `gateway/`                   | `get_access_logger()`    | 🚪 Access    | `gateway`               |
| `cli/`                       | `get_access_logger()`    | 🚪 Access    | `cli`                   |
| `common/`                    | `get_system_logger()`    | 🔧 System    | None                    |

**Prohibited**:

- ❌ `logging.getLogger(__name__)`
- ❌ `logging.getLogger(self.__class__.__name__)`

**Required**:

- ✅ `from common.logging_manager import get_decision_logger`
- ✅ `self.logger = get_decision_logger(self.__class__.__name__)`
- ✅ `self.logger = get_decision_logger(self.__class__.__name__, sublayer="memory")`

**Logging Standards**:

- Must include timestamp, layer identifier, log level, module name
- Log messages should clearly describe the operation being performed
- Error logs should include complete exception information
- Use sublayer parameter to distinguish different sub-functions within the same module

**LLM Logging Standards** (for agent/llm/ providers):

- Use `DEBUG` level for detailed input/output logging
- Log input messages: role and content preview (first 200 chars)
- Log output content: preview (first 500 chars)
- Log usage stats: prompt\_tokens, completion\_tokens, total\_tokens
- Log latency: request completion time in milliseconds
- Example log format:
  ```
  DEBUG - 🧠 [Decision] - [/🤖LLM] - (OpenAIProvider) LLM Input Messages:
  DEBUG - 🧠 [Decision] - [/🤖LLM] - (OpenAIProvider)   [0] system: ...
  DEBUG - 🧠 [Decision] - [/🤖LLM] - (OpenAIProvider)   [1] user: ...
  INFO - 🧠 [Decision] - [/🤖LLM] - (OpenAIProvider) LLM request completed - latency: 1234.56ms
  DEBUG - 🧠 [Decision] - [/🤖LLM] - (OpenAIProvider) LLM Output Content (preview): ...
  DEBUG - 🧠 [Decision] - [/🤖LLM] - (OpenAIProvider) LLM Usage - prompt_tokens: 100, completion_tokens: 50
  ```

***

## 三、代码风格

### 必须遵守

- **PEP 8** 标准
- **缩进**：4 空格
- **行长**：100 字符（软限制 120）
- **编码**：UTF-8
- **导入顺序**：标准库 → 第三方库 → 本地导入

### 命名约定

| 类型    | 规则            | 示例                   |
| ----- | ------------- | -------------------- |
| 模块    | `snake_case`  | `session_manager.py` |
| 类     | `CamelCase`   | `SessionManager`     |
| 函数/变量 | `snake_case`  | `get_session()`      |
| 常量    | `UPPER_SNAKE` | `MAX_RETRY_COUNT`    |
| 私有成员  | `_prefix`     | `_private_method()`  |

***

## 四、测试规范

### 覆盖率要求

| 目录         | 最低覆盖率   |
| ---------- | ------- |
| `agent/`   | 85%     |
| `tools/`   | 80%     |
| `gateway/` | 75%     |
| **整体**     | **80%** |

### 测试命名

- 文件：`test_<module>.py`
- 类：`Test<ClassName>`
- 方法：`test_<scenario>`

***

## 五、持续集成（CI）规范

**必须遵循**：每次代码修改完成后，必须确保 CI 检查全部通过。

***

## 六、跨平台兼容

### 必须遵守

- **路径**：使用 `pathlib.Path`，禁止硬编码分隔符
- **系统检测**：`platform.system()` 或 `os.name`
- **命令执行**：使用 `subprocess.run()`，注意平台差异

***

## 七、Git 提交规范

### 格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 类型

| 类型         | 说明     |
| ---------- | ------ |
| `feat`     | 新功能    |
| `fix`      | Bug 修复 |
| `docs`     | 文档     |
| `refactor` | 重构     |
| `test`     | 测试     |
| `chore`    | 构建/工具  |

***

## 八、新增文件约束 ⭐

### 8.1 文件必须属于某个目录

每个文件必须属于上述目录之一，禁止在根目录创建新的 `.py` 文件。

### 8.2 新增模块必须更新文档

- 新增目录 → 创建 `README.md`
- 新增功能 → 更新父级 `README.md`
- 新增测试 → 更新 `docs/development/testing-summary.md`

### 8.3 禁止的命名

- ❌ `core_*.py`（应改为 `agent_*.py` 或 `common_*.py`）
- ❌ `brain_*.py`（应改为 `agent_*.py`）
- ❌ `shared_*.py`（应改为 `common_*.py`）
- ❌ `adapter_*.py`（应改为 `gateway_*.py`）

***

> 本规范基于 PEP 8、Google Python Style Guide 和行业最佳实践制定。
> 参考：Hermes 项目结构
> 最后更新：2026-06-01 - 新增目标目录结构约束

