# 架构规范

> 适用于：设计/修改项目架构、新增模块、定义模块职责、目录结构变更

---

## 一、核心设计目标

| 目标 | 说明 |
|------|------|
| **前端优先** | 主要能力在前端实现（Web + Desktop） |
| **协议统一** | 通过 MCP 协议统一接入外部 Agent |
| **本地优先** | 数据本地存储，保护隐私 |
| **可扩展** | 模块化设计，便于接入新的 Agent |

---

## 二、目录结构

```
Agent-Z/
├── agent/        # 🧠 Decision - Agent 核心
├── tools/        # 🏃 Execution - 工具定义
├── skills/       # 🧠 Decision - 技能系统
├── gateway/      # 🚪 Access - HTTP 网关
├── executor/     # 🏃 Execution - 执行器
├── common/       # 🔧 System - 基础设施
├── cli/          # 🚪 Access - 命令行
├── tui/          # 🚪 Access - Textual TUI 界面
├── tests/        # 测试套件
└── docs/         # 文档
```

### 禁止的目录

| 废弃目录 | 迁移位置 |
|----------|---------|
| `core/`, `brain/` | → `agent/` |
| `shared/` | → `common/` |
| `llm_integration/` | → `agent/llm/` |
| `adapter/` | → `gateway/` |
| `lightweight/` | → 已废弃 |
| `api/` | → `gateway/adapters/openai_adapter.py` (2026-06-26 合并) |

---

## 三、层级 Emoji 速查表

### 3.1 主层 (4个)

| Layer | Emoji | 说明 |
|-------|-------|------|
| Access | 🚪 | 入口层（CLI、Gateway） |
| Decision | 🧠 | 决策层（LLM、Task、Memory） |
| Execution | 🏃 | 执行层（Shell、Docker、Tool） |
| System | 🔧 | 系统层（基础设施） |

### 3.2 子层 (完整定义)

| 主层 | 子层 | Emoji | 说明 |
|------|------|-------|------|
| 🚪 Access | CLI | 💬 | 命令行交互 |
| | Gateway | 🚪 | HTTP 网关入口 |
| 🧠 Decision | LLM | 🤖 | 大语言模型 |
| | ToolSelect | 🔧 | 工具选择决策 |
| | Task | ✅ | 任务规划与分解 |
| | Memory | 💾 | 记忆存储 |
| | Skills | 📋 | 技能系统 |
| | Curator | 🔬 | 自我进化/优化 |
| | Context | 📊 | 上下文管理 |
| 🏃 Execution | ShellExec | 🐚 | Shell 命令执行 |
| | DockerExec | 🐳 | Docker 容器执行 |
| | ToolExec | 🛠️ | 工具调用执行 |
| 🔧 System | (无) | - | 基础设施，无子层 |

### 3.3 日志格式模板

```
INFO - [🚪MainLayer] - [/💾SublayerName] - (ModuleName) message
```

---

## 四、目录与层级映射

| 目录 | Primary Layer | 约束 |
|------|---------------|------|
| `agent/` | 🧠 Decision | Agent 核心代码 |
| `agent/llm/` | 🧠 Decision | LLM Provider |
| `agent/curator/` | 🧠 Decision | 自我进化 |
| `agent/task/` | 🧠 Decision | 任务规划 |
| `tools/` | 🏃 Execution | 工具定义 |
| `executor/` | 🏃 Execution | Shell/Docker 执行器 |
| `gateway/` | 🚪 Access | HTTP 网关 |
| `gateway/adapters/` | 🚪 Access | 渠道适配器（HTTP/CLI/OpenAI） |
| `cli/` | 🚪 Access | 命令行入口 |
| `common/` | 🔧 System | 基础设施，**禁止放其他层代码** |
| `tui/` | 🚪 Access | Textual TUI 界面 |
| `tests/` | 🧪 Test | 测试套件 |
| `docs/` | 📖 Docs | 文档 |
| `skills/` | 🧠 Decision | 技能系统 |

---

## 五、新增文件约束

1. **文件必须属于某个目录**：禁止在根目录创建 `.py` 文件
2. **新文件必须标注层-子层**：在文件顶部注释
3. **禁止的命名**：`core_*.py`, `brain_*.py`, `shared_*.py`, `adapter_*.py`

---

## 六、模块化架构 - 依赖规则

```
common/ (最底层)
    ↑
agent/ (核心)
    ↑
gateway/ (通过 ACP 协议)
    ↑
cli/ (通过 API)
    ↑
tools/, executor/ (通过抽象接口)
```

**禁止**：
- `common/` 依赖任何其他模块
- `executor/` 直接依赖 `agent/` 的具体实现

---

## 七、命名约定

| 对象 | 规则 | 示例 |
|------|------|------|
| 模块目录 | 小写下划线 | `session_manager` |
| Python 包 | 小写下划线 | `agent/llm/` |
| React 组件 | PascalCase | `WorkflowCanvas` |
| TypeScript 类型 | PascalCase | `WorkflowNode` |
| 测试文件 | `test_*.py` | `test_session_manager.py` |

---

## 八、参考项目

| 项目 | 配置方式 |
|------|---------|
| OpenClaw | E:\openclaw-study\ |
| Hermes | E:\hermes-agent-study\ |
