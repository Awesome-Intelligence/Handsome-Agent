# Handsome Agent 编码规范

> Hermes-Brain + OpenClaw-Body 双核驱动的模块化 AI 智能助手

---

## 参考项目路径

**重要提示**：当需要参考 OpenClaw 和 Hermes 项目时，请使用以下路径：
- OpenClaw 项目：`e:\openclaw-for-study`
- Hermes 项目：`e:\hermes-agent-study`

这些路径包含完整的项目代码和配置，可用于参考实现方式。

---

## 一、目标目录结构 ⭐ **强制约束**

### 1.1 目录架构图

```
Handsome-Agent/
│
├── agent/                    # 🤖 Agent 核心
│   ├── agent_loop.py        #   Agent Loop（ReAct 模式）
│   ├── schemas.py           #   数据模型
│   ├── trajectory.py        #   轨迹记录
│   ├── memory.py            #   记忆管理
│   ├── context_engine.py    #   上下文引擎
│   ├── prompt_builder.py    #   提示词构建
│   ├── curator/             #   Curator（自我进化）
│   ├── llm/                 #   LLM Provider
│   └── templates/           #   Agent 模板
│
├── skills/                   # 🛠️ 技能系统
│   ├── matcher.py           #   技能匹配
│   ├── loader.py            #   技能加载
│   ├── registry.py          #   技能注册
│   ├── system/              #   系统内置技能
│   └── user/                #   用户技能
│
├── gateway/                  # 🚪 网关
│   ├── server.py            #   HTTP 服务器
│   ├── middleware.py         #   中间件
│   └── adapters/            #   渠道适配器
│
├── executor/                  # 🏃 执行层
│   ├── shell.py             #   Shell 执行
│   └── docker.py            #   Docker 执行
│
├── tools/                    # 🛠️ 工具定义
│   ├── registry.py          #   注册表
│   └── file_tools.py       #   文件工具
│
├── common/                    # 📦 基础设施
│   ├── config.py            #   配置
│   ├── logging.py           #   日志
│   └── exceptions.py        #   异常
│
├── cli/                      # 💬 CLI
├── tests/                    # 🧪 测试
├── docs/                     # 📚 文档
└── api/                      # 📋 OpenAPI
```

### 1.2 目录职责

| 目录 | 类型 | 职责 | 可导入其他模块 |
|------|------|------|----------------|
| `common/` | **代码** | 基础设施（配置、日志、异常） | ❌ 无 |
| `agent/` | **代码** | Agent 核心逻辑 | `common/` |
| `skills/` | **数据** | 技能系统（用户数据） | `agent/` |
| `tools/` | **代码** | 工具定义 | `agent/` |
| `executor/` | **代码** | 执行层 | `agent/` |
| `gateway/` | **代码** | 网关 | `agent/` |
| `cli/` | **代码** | CLI | `agent/`, `gateway/` |
| `lightweight/` | **代码** | 轻量版（独立） | ❌ 无 |
| `tests/` | **代码** | 测试 | 所有模块 |

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

---

## 二、核心原则

### 2.1 优先使用成熟开源组件

**必须遵循**：优先选择成熟、热门、维护活跃的开源库，避免重复造轮子。

| 场景 | 推荐库 | 原因 |
|------|--------|------|
| 终端菜单 | `inquirer` | 跨平台，成熟稳定 |
| HTTP 客户端 | `httpx` | 异步支持，现代化 |
| 日志 | `structlog` | 结构化，可扩展 |

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

| 禁止做法 | 必须做法 |
|---------|---------|
| 硬编码关键词字典 | LLM 理解意图 |
| 正则表达式匹配意图 | LLM 语义识别 |
| 预定义意图分类 | LLM 动态决策 |

**唯一例外**：当 LLM 不可用时，才可以使用关键词作为降级方案。

### 2.5 容错降级

降级链：LLM → 关键词 → 规则 → 默认值

### 2.6 复杂任务先规划到 TODO

**必须遵循**：做复杂事情（多步骤、跨模块、需多个文件修改）时，必须先将任务分解并记录到 `TODO.md` 中。

---

## 三、代码风格

### 必须遵守

- **PEP 8** 标准
- **缩进**：4 空格
- **行长**：100 字符（软限制 120）
- **编码**：UTF-8
- **导入顺序**：标准库 → 第三方库 → 本地导入

### 命名约定

| 类型 | 规则 | 示例 |
|------|------|------|
| 模块 | `snake_case` | `session_manager.py` |
| 类 | `CamelCase` | `SessionManager` |
| 函数/变量 | `snake_case` | `get_session()` |
| 常量 | `UPPER_SNAKE` | `MAX_RETRY_COUNT` |
| 私有成员 | `_prefix` | `_private_method()` |

---

## 四、测试规范

### 覆盖率要求

| 目录 | 最低覆盖率 |
|------|------------|
| `agent/` | 85% |
| `tools/` | 80% |
| `gateway/` | 75% |
| **整体** | **80%** |

### 测试命名

- 文件：`test_<module>.py`
- 类：`Test<ClassName>`
- 方法：`test_<scenario>`

---

## 五、持续集成（CI）规范

**必须遵循**：每次代码修改完成后，必须确保 CI 检查全部通过。

---

## 六、跨平台兼容

### 必须遵守

- **路径**：使用 `pathlib.Path`，禁止硬编码分隔符
- **系统检测**：`platform.system()` 或 `os.name`
- **命令执行**：使用 `subprocess.run()`，注意平台差异

---

## 七、Git 提交规范

### 格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 类型

| 类型 | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档 |
| `refactor` | 重构 |
| `test` | 测试 |
| `chore` | 构建/工具 |

---

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

---

> 本规范基于 PEP 8、Google Python Style Guide 和行业最佳实践制定。
> 参考：Hermes 项目结构
> 最后更新：2026-06-01 - 新增目标目录结构约束