# Handsome Agent CLI 架构文档

> 基于 Hermes Agent 的 CLI 设计，目标支持大型项目扩展
>
> **参考版本**: Hermes Agent CLI (`hermes_cli/`)
> **最后更新**: 2026-06-03

---

## ⚠️ 核心设计原则

> **CLI 是入口，核心逻辑在 agent/、tools/、skills/**
>
> | 层级 | 职责 | 说明 |
> |------|------|------|
> | `cli/` | 入口 | 解析参数、格式化输出、命令分发 |
> | `agent/` | 核心逻辑 | Agent 决策、技能命令、LLM |
> | `tools/` | 工具层 | 工具定义、注册、执行 |
> | `skills/` | 数据层 | SKILL.md 等数据文件 |

---

## 一、目标目录结构

```
Handsome-Agent/
├── cli/                          # 🚪 Access - 命令行入口
│   ├── __init__.py
│   │
│   ├── # === 核心入口 ===
│   ├── main.py                  # ⭐ 唯一入口，CLI 主程序
│   ├── _parser.py               # ⭐ argparse 命令行参数解析器
│   ├── commands.py               # ⭐ 斜杠命令注册表 (/help, /compress 等)
│   │
│   ├── # === UI 层 (纯展示，无业务逻辑) ===
│   ├── colors.py                # ⭐ ANSI 颜色定义
│   ├── cli_output.py            # ⭐ 输出格式化 (print_info/error/success)
│   ├── banner.py                # ⭐ Banner 渲染 + ASCII Art
│   ├── skin_engine.py           # ⭐ 皮肤/主题系统
│   ├── curses_ui.py             # ⭐ Curses TUI (多选/单选)
│   ├── interactive_select.py     # 交互选择封装
│   │
│   ├── # === 配置与认证 ===
│   ├── config_cli.py            # 配置 CLI (→ common/config.py)
│   ├── config.py                # 配置加载/保存
│   ├── setup.py                 # 交互式设置向导
│   ├── env_loader.py            # .env 文件加载
│   ├── auth_cli.py              # 认证 CLI (→ agent/auth.py)
│   ├── profiles.py              # 多配置文件系统
│   │
│   ├── # === 模型与 Provider ===
│   ├── model_cli.py             # 模型 CLI (→ agent/llm/)
│   ├── providers_cli.py         # Provider CLI
│   ├── models.py               # 模型目录定义
│   ├── providers.py             # Provider 注册表
│   ├── model_switch.py          # 模型切换命令
│   │
│   ├── # === 技能系统 ===
│   ├── skills_cli.py            # 技能 CLI (→ agent/skill_commands.py)
│   ├── skills_config.py         # 技能配置
│   ├── bundles.py               # 技能捆绑包
│   │
│   ├── # === 工具配置 ===
│   ├── tools_cli.py             # 工具 CLI (→ tools/)
│   ├── tools_config.py          # 工具集配置
│   │
│   ├── # === 代理子模块 (独立功能) ===
│   ├── proxy/
│   │   ├── __init__.py
│   │   ├── server.py            # HTTP 代理服务器
│   │   ├── cli.py               # 代理 CLI 命令
│   │   └── adapters/
│   │       ├── __init__.py
│   │       └── base.py          # 适配器基类
│   │
│   ├── # === 诊断与调试 ===
│   ├── status.py                # 系统状态显示
│   ├── doctor.py                # 诊断检查
│   ├── debug.py                 # 调试工具
│   ├── dump.py                  # 配置转储
│   │
│   ├── # === 定时任务 ===
│   ├── cron.py                  # 定时任务 CLI
│   ├── checkpoints.py           # 文件系统检查点
│   │
│   ├── # === 高级功能 ===
│   ├── hooks.py                 # 生命周期钩子
│   ├── callbacks.py              # 回调系统
│   ├── voice_cli.py             # 语音模式 CLI
│   ├── completion.py             # Shell 补全
│   │
│   └── # === 辅助工具 ===
│       ├── relaunch.py          # CLI 自我重启
│       ├── backup.py            # 备份功能
│       └── uninstall.py          # 卸载程序
│
├── agent/                        # 🧠 Decision - 核心逻辑
│   ├── agent.py                 # Agent 主类
│   ├── session.py               # 会话管理
│   ├── skill_commands.py         # ⭐ 技能命令处理
│   ├── skill_utils.py           # ⭐ 技能工具函数
│   └── llm/                     # ⭐ LLM 相关
│       ├── providers.py          # Provider 注册表
│       ├── models.py             # 模型目录
│       ├── model_switch.py       # 模型切换
│       └── ...
│
├── tools/                       # 🏃 Execution - 工具
│   ├── registry.py              # 工具注册表
│   ├── skills_tool.py           # ⭐ 技能目录扫描
│   └── ...
│
├── skills/                      # 📋 Skills - 数据目录
│   └── ...                      # SKILL.md 等数据文件
│
└── common/                      # 🔧 System - 基础设施
    └── config.py                # 配置基础
```

---

## 二、文件职责表

### 2.1 核心入口

| 文件 | 职责 | 为什么需要 |
|------|------|-----------|
| `main.py` | CLI 主入口，参数解析 | 唯一入口点，协调所有功能 |
| `_parser.py` | argparse 定义 | 可复用的参数解析 |
| `commands.py` | 斜杠命令注册 | 统一命令管理 |

### 2.2 UI 层

| 文件 | 职责 | 为什么需要 |
|------|------|-----------|
| `colors.py` | ANSI 颜色定义 | 统一颜色系统 |
| `cli_output.py` | 输出格式化 | 一致用户体验 |
| `banner.py` | Banner + ASCII Art | 品牌展示 |
| `skin_engine.py` | 皮肤/主题 | 个性化界面 |
| `curses_ui.py` | Curses TUI | 原生键盘导航 |

### 2.3 配置与认证

| 文件 | 职责 | 调用关系 |
|------|------|----------|
| `config_cli.py` | 配置 CLI | → `common/config.py` |
| `config.py` | 配置加载/保存 | 单一配置入口 |
| `setup.py` | 设置向导 | 友好首次体验 |
| `auth_cli.py` | 认证 CLI | → `agent/auth.py` |
| `profiles.py` | 多配置文件 | 环境隔离 |

### 2.4 模型与 Provider

| 文件 | 职责 | 调用关系 |
|------|------|----------|
| `model_cli.py` | 模型 CLI | → `agent/llm/` |
| `providers_cli.py` | Provider CLI | → `agent/llm/` |
| `models.py` | 模型目录 | - |
| `providers.py` | Provider 注册 | - |

### 2.5 技能与工具

| 文件 | 职责 | 调用关系 |
|------|------|----------|
| `skills_cli.py` | 技能 CLI | → `agent/skill_commands.py` |
| `skills_config.py` | 技能配置 | - |
| `bundles.py` | 技能捆绑包 | - |
| `tools_cli.py` | 工具 CLI | → `tools/` |
| `tools_config.py` | 工具配置 | - |

### 2.6 代理子模块

| 文件 | 职责 | 为什么需要 |
|------|------|-----------|
| `proxy/server.py` | HTTP 代理 | OAuth 认证桥接 |
| `proxy/cli.py` | 代理 CLI | 代理管理 |
| `proxy/adapters/base.py` | 适配器基类 | 多平台支持 |

### 2.7 诊断与调试

| 文件 | 职责 | 为什么需要 |
|------|------|-----------|
| `status.py` | 状态显示 | 快速诊断 |
| `doctor.py` | 诊断检查 | 系统性检查 |
| `debug.py` | 调试工具 | 问题定位 |
| `dump.py` | 配置转储 | 调试支持 |

---

## 三、当前结构 vs 目标结构

### 当前结构 (问题)

```
cli/
├── __init__.py
├── main.py
├── ui.py                    # ❌ 职责过重 (颜色+输出+Banner+状态栏)
├── banner.py                # ✅ 已有 (需增强)
├── setup_wizard.py         # ❌ 命名不规范
├── interactive_select.py    # ✅ 已有
├── skills_cli.py           # ✅ 已有
├── llm_cli.py             # ✅ 已有
├── modern_cli.py          # ⚠️ 可能多余
├── batch_runner.py        # ⚠️ 功能不清
├── colors.py              # ✅ 已有
├── skin_engine.py        # ✅ 已有
├── cli_output.py         # ✅ 已有
└── docs/
    └── architecture.md   # ✅ 已有
```

**问题**：
1. `ui.py` 职责过重
2. 缺少 `_parser.py` 和 `commands.py`
3. `setup_wizard.py` 命名不标准
4. 缺少诊断/调试模块
5. 缺少 Proxy 子模块
6. 缺少定时任务模块

### 目标结构 (正确)

```
cli/
├── __init__.py
├── main.py                  # ⭐ 唯一入口
├── _parser.py               # ⭐ 参数解析
├── commands.py              # ⭐ 命令注册
│
├── # UI 层
├── colors.py                # ✅ 独立
├── cli_output.py            # ✅ 独立
├── banner.py                # ✅ 增强
├── skin_engine.py           # ✅ 已有
├── curses_ui.py            # ⭐ 新增
├── interactive_select.py     # ✅ 已有
│
├── # 配置认证
├── config_cli.py            # ⭐ 改名
├── config.py                # ⭐ 改名
├── setup.py                 # ⭐ 重命名
├── env_loader.py            # ⭐ 新增
├── auth_cli.py              # ⭐ 新增
├── profiles.py              # ⭐ 新增
│
├── # 模型
├── model_cli.py             # ⭐ 改名
├── models.py                # ⭐ 改名
├── providers.py             # ⭐ 改名
├── model_switch.py          # ⭐ 新增
│
├── # 技能
├── skills_cli.py            # ✅ 已有
├── skills_config.py         # ⭐ 新增
├── bundles.py              # ⭐ 新增
│
├── # 工具
├── tools_cli.py            # ⭐ 改名
├── tools_config.py         # ⭐ 新增
│
├── # 代理
├── proxy/                   # ⭐ 新增
│   ├── __init__.py
│   ├── server.py
│   ├── cli.py
│   └── adapters/
│       └── base.py
│
├── # 诊断
├── status.py                # ⭐ 新增
├── doctor.py               # ⭐ 新增
├── debug.py                # ⭐ 新增
├── dump.py                 # ⭐ 新增
│
├── # 定时任务
├── cron.py                  # ⭐ 新增
├── checkpoints.py          # ⭐ 新增
│
├── # 高级功能
├── hooks.py                 # ⭐ 新增
├── callbacks.py             # ⭐ 新增
├── voice_cli.py            # ⭐ 新增
├── completion.py            # ⭐ 新增
│
├── # 辅助
├── relaunch.py             # ⭐ 新增
├── backup.py               # ⭐ 新增
├── uninstall.py            # ⭐ 新增
│
└── docs/
    └── architecture.md
```

---

## 四、实施计划

### 阶段 1: UI 层重构 (优先级最高)

| 任务 | 文件 | 描述 | 优先级 |
|------|------|------|--------|
| 1.1 | 已有 `colors.py` | 确认已独立，无业务依赖 | ⭐⭐⭐ |
| 1.2 | 已有 `cli_output.py` | 确认已独立，无业务依赖 | ⭐⭐⭐ |
| 1.3 | 已有 `banner.py` | 确认使用 rich | ⭐⭐⭐ |
| 1.4 | 已有 `skin_engine.py` | 确认已有 | ⭐⭐ |
| 1.5 | 新增 `curses_ui.py` | 从 Hermes 移植 curses 多选/单选 | ⭐⭐ |
| 1.6 | 已有 `interactive_select.py` | 确认集成 curses | ⭐ |
| 1.7 | 清理 `ui.py` | 删除重复代码，委托到新模块 | ⭐⭐ |

### 阶段 2: 核心入口

| 任务 | 文件 | 描述 | 优先级 |
|------|------|------|--------|
| 2.1 | 新增 `_parser.py` | argparse 命令行参数解析器 | ⭐⭐⭐ |
| 2.2 | 新增 `commands.py` | 斜杠命令注册表 | ⭐⭐⭐ |
| 2.3 | 更新 `main.py` | 使用 `_parser.py` | ⭐⭐⭐ |

### 阶段 3: 配置与认证

| 任务 | 文件 | 描述 | 优先级 |
|------|------|------|--------|
| 3.1 | 新增 `config.py` | 配置加载/保存 | ⭐⭐⭐ |
| 3.2 | 重命名 `setup_wizard.py` → `setup.py` | 与 Hermes 一致 | ⭐⭐ |
| 3.3 | 新增 `env_loader.py` | .env 文件加载 | ⭐⭐ |
| 3.4 | 新增 `auth_cli.py` | 认证 CLI | ⭐⭐ |
| 3.5 | 新增 `profiles.py` | 多配置文件系统 | ⭐⭐ |

### 阶段 4: 模型与 Provider

| 任务 | 文件 | 描述 | 优先级 |
|------|------|------|--------|
| 4.1 | 已有 `llm_cli.py` | 重命名为 `model_cli.py` | ⭐⭐ |
| 4.2 | 新增 `models.py` | 模型目录定义 | ⭐⭐ |
| 4.3 | 新增 `providers.py` | Provider 注册表 | ⭐⭐ |
| 4.4 | 新增 `model_switch.py` | 模型切换命令 | ⭐ |

### 阶段 5: 技能系统

| 任务 | 文件 | 描述 | 优先级 |
|------|------|------|--------|
| 5.1 | 已有 `skills_cli.py` | 增强调用核心 | ⭐⭐⭐ |
| 5.2 | 新增 `skills_config.py` | 技能配置 | ⭐⭐ |
| 5.3 | 新增 `bundles.py` | 技能捆绑包 | ⭐ |
| 5.4 | 新增 `agent/skill_commands.py` | 技能命令处理 (核心) | ⭐⭐⭐ |
| 5.5 | 新增 `agent/skill_utils.py` | 技能工具函数 | ⭐⭐ |
| 5.6 | 新增 `tools/skills_tool.py` | 技能目录扫描 | ⭐⭐⭐ |

### 阶段 6: 工具配置

| 任务 | 文件 | 描述 | 优先级 |
|------|------|------|--------|
| 6.1 | 已有 `tools_cli.py` | 确认调用 tools/ | ⭐⭐ |
| 6.2 | 新增 `tools_config.py` | 工具集配置 | ⭐⭐ |

### 阶段 7: 代理子模块

| 任务 | 文件 | 描述 | 优先级 |
|------|------|------|--------|
| 7.1 | 新增 `proxy/` 目录 | 代理子模块 | ⭐⭐ |
| 7.2 | 新增 `proxy/server.py` | HTTP 代理服务器 | ⭐ |
| 7.3 | 新增 `proxy/cli.py` | 代理 CLI | ⭐ |
| 7.4 | 新增 `proxy/adapters/base.py` | 适配器基类 | ⭐ |

### 阶段 8: 诊断与调试

| 任务 | 文件 | 描述 | 优先级 |
|------|------|------|--------|
| 8.1 | 新增 `status.py` | 系统状态显示 | ⭐⭐ |
| 8.2 | 新增 `doctor.py` | 诊断检查 | ⭐⭐ |
| 8.3 | 新增 `debug.py` | 调试工具 | ⭐ |
| 8.4 | 新增 `dump.py` | 配置转储 | ⭐ |

### 阶段 9: 定时任务与高级功能

| 任务 | 文件 | 描述 | 优先级 |
|------|------|------|--------|
| 9.1 | 新增 `cron.py` | 定时任务 CLI | ⭐ |
| 9.2 | 新增 `checkpoints.py` | 文件系统检查点 | ⭐ |
| 9.3 | 新增 `hooks.py` | 生命周期钩子 | ⭐ |
| 9.4 | 新增 `callbacks.py` | 回调系统 | ⭐ |
| 9.5 | 新增 `voice_cli.py` | 语音模式 CLI | ⭐ |
| 9.6 | 新增 `completion.py` | Shell 补全 | ⭐ |

### 阶段 10: 辅助工具

| 任务 | 文件 | 描述 | 优先级 |
|------|------|------|--------|
| 10.1 | 新增 `relaunch.py` | CLI 自我重启 | ⭐ |
| 10.2 | 新增 `backup.py` | 备份功能 | ⭐ |
| 10.3 | 新增 `uninstall.py` | 卸载程序 | ⭐ |
| 10.4 | 清理 `modern_cli.py` | 合并或删除 | ⭐ |
| 10.5 | 清理 `batch_runner.py` | 合并或删除 | ⭐ |

---

## 五、依赖关系图

```
cli/main.py (入口)
    │
    ├── _parser.py (参数解析)
    ├── commands.py (命令注册)
    │
    ├── # UI 层 - 无依赖
    │   colors.py
    │   cli_output.py
    │   banner.py
    │   skin_engine.py
    │   curses_ui.py
    │   interactive_select.py
    │
    ├── # 配置认证
    │   config.py → common/config.py
    │   setup.py → config.py, auth_cli.py
    │   auth_cli.py → agent/auth.py
    │   profiles.py → config.py
    │
    ├── # 模型
    │   model_cli.py → agent/llm/providers.py
    │   models.py
    │   providers.py
    │   model_switch.py → models.py, config.py
    │
    ├── # 技能
    │   skills_cli.py → agent/skill_commands.py
    │   skills_config.py → config.py
    │   bundles.py → skills_cli.py
    │
    ├── # 工具
    │   tools_cli.py → tools/
    │   tools_config.py → config.py
    │
    ├── # 代理
    │   proxy/cli.py → proxy/server.py
    │   proxy/server.py → proxy/adapters/
    │
    ├── # 诊断
    │   status.py → auth_cli.py, config.py, models.py
    │   doctor.py → 多个核心模块
    │
    └── # 定时任务
        cron.py → checkpoints.py

agent/ (核心逻辑层)
    ├── skill_commands.py
    ├── skill_utils.py
    └── llm/
        ├── providers.py
        ├── models.py
        └── model_switch.py

tools/ (工具层)
    ├── registry.py
    └── skills_tool.py
```

---

## 六、参考 Hermes 的关键设计

### 6.1 模块按功能域组织

```
hermes_cli/
├── kanban/          # 看板系统 (6 个文件)
├── proxy/            # 代理系统 (子目录)
├── kanban*.py        # 看板相关
├── codex*.py         # Codex 相关
└── ...
```

### 6.2 单一职责原则

每个文件只做一件事：
- `config.py` - 只做配置
- `auth.py` - 只做认证
- `models.py` - 只做模型目录
- `banner.py` - 只做 Banner

### 6.3 CLI 入口调用核心

```
hermes_cli/skills_hub.py
    ↓
agent/skill_commands.py    # 核心逻辑
    ↓
tools/skills_tool.py         # 工具实现
```

---

## 七、验收标准

每个阶段完成后需要满足：
- [ ] 所有功能测试通过
- [ ] 无循环依赖
- [ ] 每个文件 < 500 行
- [ ] 每个函数 < 100 行
- [ ] CLI 命令保持兼容
- [ ] 文档同步更新

---

## 八、TODO 任务清单

### 高优先级 (必须实现)

| ID | 任务 | 文件 | 阶段 |
|----|------|------|------|
| P1 | 新增 `_parser.py` | _parser.py | 阶段2 |
| P2 | 新增 `commands.py` | commands.py | 阶段2 |
| P3 | 更新 `main.py` 使用 `_parser` | main.py | 阶段2 |
| P4 | 新增 `curses_ui.py` | curses_ui.py | 阶段1 |
| P5 | 清理 `ui.py` 重复代码 | ui.py | 阶段1 |
| P6 | 新增 `config.py` | config.py | 阶段3 |
| P7 | 重命名 `setup_wizard.py` → `setup.py` | setup.py | 阶段3 |
| P8 | 新增 `agent/skill_commands.py` | agent/skill_commands.py | 阶段5 |
| P9 | 新增 `tools/skills_tool.py` | tools/skills_tool.py | 阶段5 |

### 中优先级 (重要功能)

| ID | 任务 | 文件 | 阶段 |
|----|------|------|------|
| M1 | 新增 `auth_cli.py` | auth_cli.py | 阶段3 |
| M2 | 新增 `profiles.py` | profiles.py | 阶段3 |
| M3 | 新增 `models.py` | models.py | 阶段4 |
| M4 | 新增 `providers.py` | providers.py | 阶段4 |
| M5 | 新增 `status.py` | status.py | 阶段8 |
| M6 | 新增 `doctor.py` | doctor.py | 阶段8 |
| M7 | 新增 `skills_config.py` | skills_config.py | 阶段5 |

### 低优先级 (增强功能)

| ID | 任务 | 文件 | 阶段 |
|----|------|------|------|
| L1 | 新增 `proxy/` 子模块 | proxy/* | 阶段7 |
| L2 | 新增 `cron.py` | cron.py | 阶段9 |
| L3 | 新增 `hooks.py` | hooks.py | 阶段9 |
| L4 | 新增 `voice_cli.py` | voice_cli.py | 阶段9 |
| L5 | 清理 `modern_cli.py` | modern_cli.py | 阶段10 |
| L6 | 清理 `batch_runner.py` | batch_runner.py | 阶段10 |

---

## 十、与 Hermes 差距对比 (需优化)

### 当前完成度

| 维度 | Hermes | Handsome | 完成度 |
|------|--------|----------|--------|
| **总文件数** | ~90 个 | ~40 个 | 45% |
| **认证系统** | 完整 OAuth 多提供商 | 基础 CLI | 10% |
| **Profile 管理** | 1560+ 行，导入/导出 | 220 行，基础 | 15% |
| **命令系统** | 60+ 命令，自动补全 | ~10 命令 | 15% |
| **工具配置** | 20+ 工具集 | ~4 工具集 | 10% |
| **诊断系统** | 800+ 行，30+ 检查项 | 170 行，6 项 | 20% |

### 需优化的模块

| 优先级 | 模块 | 当前状态 | 目标 |
|--------|------|----------|------|
| **P0** | 认证后端 | `auth_cli.py` (CLI接口) | 实现 `agent/auth.py` |
| **P0** | 命令补全 | 基础 `commands.py` | 增强自动补全 |
| **P0** | Profile导入导出 | 基础 `profiles.py` | 添加 tar.gz 导入/导出 |
| **P1** | Doctor 增强 | 6 项检查 | 增加 API Key 检测等 |
| **P1** | 模型别名 | 基础 `model_cli.py` | 名称规范化 |
| **P1** | 工具集扩展 | 4 个工具集 | 20+ 工具集 |
| **P2** | Profile 元数据 | 无 | `profile.yaml` |
| **P2** | 平台认证 | 无 | `copilot_auth.py` 等 |
| **P2** | Web 服务 | 无 | 基础仪表盘 |

### 优化 TODO

| ID | 任务 | 文件 | 优先级 |
|----|------|------|--------|
| OPT1 | 新增 `agent/auth.py` 实现 OAuth 认证逻辑 | agent/auth.py | 🔴 高 |
| OPT2 | 增强 `commands.py` 添加自动补全支持 | commands.py | 🔴 高 |
| OPT3 | 增强 `profiles.py` 添加 backup/restore | profiles.py | 🔴 高 |
| OPT4 | 增强 `doctor.py` 增加 API Key 检测等 | doctor.py | 🟡 中 |
| OPT5 | 增强 `model_cli.py` 名称规范化 | model_cli.py | 🟡 中 |
| OPT6 | 增强 `tools_config.py` 增加工具集 | tools_config.py | 🟡 中 |
| OPT7 | 添加 Profile 元数据 `profile.yaml` | profiles.py | 🟢 低 |
| OPT8 | 添加 `copilot_auth.py` 等平台认证 | cli/*.py | 🟢 低 |
| OPT9 | 实现基础 Web 仪表盘 | web_server.py | 🟢 低 |

---

## 九、已确认的文件状态

### 已有且正确

| 文件 | 状态 | 说明 |
|------|------|------|
| `colors.py` | ✅ 正确 | 独立颜色定义 |
| `cli_output.py` | ✅ 正确 | 独立输出函数 |
| `banner.py` | ✅ 正确 | rich 渲染 |
| `skin_engine.py` | ✅ 正确 | 皮肤系统 |
| `interactive_select.py` | ✅ 正确 | 交互选择 |
| `skills_cli.py` | ✅ 正确 | 需增强调用核心 |

### 需要改名

| 原文件 | 目标文件 | 说明 |
|--------|----------|------|
| `setup_wizard.py` | `setup.py` | 与 Hermes 一致 |
| `llm_cli.py` | `model_cli.py` | 更通用命名 |

### 需要清理

| 文件 | 处理方式 |
|------|----------|
| `ui.py` | 删除重复代码，委托到 colors.py, cli_output.py |
| `modern_cli.py` | 合并到 main.py 或删除 |
| `batch_runner.py` | 合并到 main.py 或删除 |

---

*最后更新: 2026-06-03*
*参考: Hermes Agent CLI 架构 (hermes_cli/)*