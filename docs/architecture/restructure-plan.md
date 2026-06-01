# Handsome Agent 目录结构重构计划

> 参考 Hermes 项目结构，制定的目标目录架构
>
> **状态**：规划中（未执行）
>
> **最后更新**：2026-06-01

---

## 一、为什么需要重构

### 当前问题

| 问题 | 说明 |
|------|------|
| **命名冲突** | `agent/` vs `brain/agent/` 都叫 agent |
| **职责不清** | `core/` 和 `agent/` 有大量重复 |
| **层次混乱** | `brain/` 和 `brain_curator/` 是同级但功能包含 |
| **空目录** | `plugins/`, `llm_integration/` 几乎为空 |
| **跨层依赖** | shared → core → tools → core（违反分层原则） |

### 参考：Hermes 项目结构

```
hermes-agent-study/
├── agent/                    # 核心 Agent（扁平化）
│   ├── conversation_loop.py
│   ├── curator.py            # Curator 与 agent 同级
│   ├── trajectory.py
│   └── llm/                  # LLM Provider 子目录
├── hermes_cli/               # CLI（大型模块）
├── gateway/                  # 网关
│   └── platforms/           # 多渠道适配器
├── tools/                    # 工具（扁平化）
├── skills/                  # 用户技能
└── providers/               # LLM Provider 抽象
```

**Hermes 设计哲学**：
1. **扁平化** - 减少嵌套层级
2. **职责分离** - 每层独立目录
3. **同源合并** - 相关功能放在同一目录

---

## 二、目标目录结构

```
Handsome-Agent/
│
├── agent/                    # 🤖 Agent 核心
│   ├── __init__.py
│   ├── agent_loop.py        # Agent Loop（ReAct 模式）
│   ├── schemas.py           # 数据模型（ToolCall, AgentConfig）
│   ├── trajectory.py        # 轨迹记录
│   ├── memory.py            # 记忆管理
│   ├── context_engine.py    # 上下文引擎
│   ├── prompt_builder.py    # 提示词构建
│   │
│   ├── curator/             # 🔬 Curator（自我进化）
│   │   ├── __init__.py
│   │   ├── curator.py       # 主逻辑
│   │   ├── evaluator.py     # 轨迹评估
│   │   ├── synthesizer.py   # 技能合成
│   │   └── writer.py        # 技能写入
│   │
│   ├── llm/                 # 🤖 LLM Provider
│   │   ├── __init__.py
│   │   ├── base.py         # Provider 基类
│   │   ├── openai.py       # OpenAI
│   │   ├── claude.py       # Claude
│   │   └── factory.py       # 工厂
│   │
│   └── templates/           # 📝 Agent 模板
│       ├── agent.md
│       ├── capabilities.md
│       ├── memory.md
│       └── tools.md
│
├── skills/                   # 🛠️ 技能系统
│   ├── __init__.py
│   ├── matcher.py           # 技能匹配
│   ├── loader.py            # 技能加载
│   ├── registry.py          # 技能注册
│   ├── telemetry.py         # 使用追踪
│   ├── lifecycle.py         # 生命周期
│   ├── merger.py            # 技能合并
│   ├── evolution_manager.py # 进化管理
│   │
│   ├── system/              # 系统内置技能
│   │   └── computer-use/
│   └── user/                # 用户安装的技能
│
├── gateway/                  # 🚪 网关
│   ├── __init__.py
│   ├── server.py            # HTTP 服务器
│   ├── config.py            # 配置
│   ├── middleware.py         # 中间件（认证、限流）
│   ├── message.py           # 消息格式
│   └── adapters/            # 渠道适配器
│       ├── __init__.py
│       ├── http.py
│       └── cli.py
│
├── executor/                # 🏃 执行层
│   ├── __init__.py
│   ├── base.py              # 基类
│   ├── shell.py             # Shell 执行
│   └── docker.py            # Docker 执行
│
├── tools/                   # 🛠️ 工具定义
│   ├── __init__.py
│   ├── registry.py          # 注册表
│   ├── file_tools.py        # 文件工具
│   ├── shell_tools.py       # Shell 工具
│   ├── web_tools.py         # Web 工具
│   ├── app_launcher.py       # 应用启动
│   └── integrated_tools.py   # 集成工具
│
├── common/                   # 📦 基础设施
│   ├── __init__.py
│   ├── config.py            # 配置
│   ├── logging.py           # 日志
│   ├── exceptions.py        # 异常
│   └── models.py            # 数据模型
│
├── lightweight/             # ⚡ 轻量版（零依赖）
│   ├── __init__.py
│   ├── agent.py             # 知识库版
│   ├── agent_v2.py          # CoT + Tools 版
│   ├── server.py
│   └── tools.py
│
├── cli/                      # 💬 CLI
│   ├── __init__.py
│   ├── main.py              # 主入口
│   ├── ui.py                # 界面
│   ├── setup_wizard.py       # 设置向导
│   ├── skills_cli.py        # 技能管理
│   └── batch_runner.py       # 批处理
│
├── tests/                    # 🧪 测试
│   ├── unit/
│   ├── integration/
│   └── conftest.py
│
├── docs/                     # 📚 文档
│   ├── index.md
│   ├── architecture/
│   ├── guides/
│   ├── modules/
│   └── references/
│
├── api/                      # 📋 OpenAPI
│   └── brain_service.yaml
│
└── scripts/                  # 📜 脚本
    └── setup.py
```

---

## 三、目录职责说明

### 代码模块 vs 用户数据

| 类型 | 目录 | 说明 |
|------|------|------|
| **代码** | `agent/` | 系统核心逻辑，可编辑 |
| **代码** | `tools/` | 工具定义，可编辑 |
| **代码** | `gateway/` | 网关逻辑，可编辑 |
| **代码** | `executor/` | 执行层，可编辑 |
| **代码** | `common/` | 基础设施，可编辑 |
| **代码** | `lightweight/` | 轻量版，可编辑 |
| **代码** | `cli/` | CLI，可编辑 |
| **数据** | `skills/` | 用户技能，只读或用户写入 |
| **数据** | `tests/` | 测试用例，可编辑 |

### 模块依赖关系

```
common/           # 最底层，无依赖
    ↑
agent/           # 核心逻辑，依赖 common
    ├── curator/  # 自我进化
    ├── llm/      # LLM Provider
    └── templates/ # 模板
    ↑
gateway/         # 依赖 agent（通过 ACP 协议）
    ↑
cli/             # 依赖 agent、gateway
    ↑
tools/           # 依赖 agent（通过抽象接口）
    ↑
executor/         # 依赖 agent（通过抽象接口）
```

---

## 四、重构变更清单

### 4.1 目录重命名/移动

| 原路径 | 新路径 | 说明 |
|--------|--------|------|
| `brain/agent/` | `agent/` | 合并到 agent 目录 |
| `brain/llm/` | `agent/llm/` | 合并到 agent 目录 |
| `brain/memory/` | `agent/memory.py` | 合并为单文件 |
| `brain/trajectory.py` | `agent/trajectory.py` | 合并到 agent |
| `brain_curator/` | `agent/curator/` | 作为 agent 子目录 |
| `brain/skills/` | `skills/` | 合并到 skills 目录 |
| `skills/` | `skills/user/` | 用户技能子目录 |
| `agent/templates/` | `agent/templates/` | 保留原名 |
| `shared/` | `common/` | 重命名基础设施 |
| `llm_integration/` | → 删除 | 合并到 `agent/llm/` |
| `adapter/` | → 删除 | 合并到 `gateway/` |
| `core/` | → 删除 | 合并到 `agent/` 或 `common/` |

### 4.2 根目录文件移动

| 原路径 | 新路径 |
|--------|--------|
| `hermes_state.py` | `common/state.py` |
| `hermes_constants.py` | `common/constants.py` |
| `model_tools.py` | `tools/model_tools.py` |
| `batch_runner.py` | `cli/batch_runner.py` |
| `main.py` | `cli/main.py` |
| `cli.py` | → 删除 |
| `run_agent.py` | → 删除 |

### 4.3 删除空目录

| 目录 | 原因 |
|------|------|
| `plugins/` | 几乎为空 |
| `plugins/context_engine/` | 空 |
| `plugins/memory/` | 空 |
| `llm_integration/` | 功能已合并 |
| `lightweight/` | → 删除 | 功能已合并到 `agent/` |
| `adapter/` | 功能已合并 |
| `brain/` | 功能已合并 |
| `core/` | 功能已合并 |

---

## 五、执行阶段

### 阶段 1：准备工作

- [ ] 备份当前代码库
- [ ] 在 git 中创建 `refactor/architecture` 分支
- [ ] 编写迁移脚本

### 阶段 2：创建新目录结构

- [ ] 创建 `agent/curator/` 目录
- [ ] 创建 `agent/llm/` 目录
- [ ] 创建 `agent/templates/` 目录
- [ ] 创建 `skills/system/` 和 `skills/user/` 目录
- [ ] 创建 `gateway/adapters/` 目录
- [ ] 创建 `common/` 目录

### 阶段 3：移动文件（不修改代码）

- [ ] 移动 `brain_curator/*` → `agent/curator/`
- [ ] 移动 `brain/agent/*` → `agent/`
- [ ] 移动 `brain/llm/*` → `agent/llm/`
- [ ] 移动 `brain/skills/*` → `skills/`
- [ ] 移动 `brain/trajectory.py` → `agent/trajectory.py`
- [ ] 移动 `core/*` → `agent/` 或 `common/`
- [ ] 移动 `adapter/gateway.py` → `gateway/message.py`
- [ ] 移动 `adapter/adapters/*` → `gateway/adapters/`
- [ ] 移动根目录文件到对应目录
- [ ] 删除空目录

### 阶段 4：修复导入路径

- [ ] 更新所有 `from brain.` 导入
- [ ] 更新所有 `from adapter.` 导入
- [ ] 更新所有 `from core.` 导入
- [ ] 更新所有 `from shared.` 导入
- [ ] 更新 `tools/integrated_tools.py`
- [ ] 更新 `agent/agent_loop.py`

### 阶段 5：测试验证

- [ ] 运行测试套件
- [ ] 手动测试关键功能
- [ ] 更新所有文档中的路径引用
- [ ] 更新 rule.md 中的目录约束
- [ ] 合并到主分支

---

## 六、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 导入路径大规模修改 | 高 | 分批执行，每批测试 |
| 删除目录误删文件 | 中 | 先移动后删除，使用 git |
| git 历史丢失 | 低 | 使用 `git mv` 保留历史 |
| 测试失败 | 高 | 每阶段运行测试 |

---

## 七、参考文档

- [Hermes 项目结构](e:\hermes-agent-study)
- [编码规范](../.trae/rules/rule.md)
- [架构设计](architecture.md)

---

*本计划将作为 TODO.md 中的高优先级任务执行*