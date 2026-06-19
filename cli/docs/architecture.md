# Handsome Agent CLI 架构文档

> 🚪 Access - 💬 CLI 入口层架构规范
>
> **版本**: v3.0 (目录结构优化版)
> **最后更新**: 2026-06-19

---

## 一、核心设计原则

> **CLI 是入口，核心逻辑在 agent/、tools/、skills/**

| 层级 | 职责 | 说明 |
|------|------|------|
| `cli/` | 入口 | 解析参数、格式化输出、命令分发 |
| `agent/` | 核心逻辑 | Agent 决策、技能命令、LLM |
| `tools/` | 工具层 | 工具定义、注册、执行 |
| `skills/` | 数据层 | SKILL.md 等数据文件 |

---

## 二、当前目录结构 (v3.0)

```
cli/                              # 🚪 Access - 命令行入口
├── __init__.py
├── main.py                      # 唯一入口，CLI 主程序
├── _parser.py                   # argparse 命令行参数解析器
├── commands.py                  # 斜杠命令注册表 (/help, /compress 等)
│
├── cli_commands/                # CLI 命令模块
│   ├── __init__.py
│   ├── acp.py                   # ACP 服务器管理
│   ├── auth.py                  # 认证管理
│   ├── completion.py            # Shell 补全
│   ├── config.py                # 配置管理
│   ├── cron.py                  # 定时任务
│   ├── debug.py                 # 调试工具
│   ├── doctor.py                # 诊断检查
│   ├── dump.py                  # 配置转储
│   ├── gateway.py               # 网关管理
│   ├── kanban.py                # Kanban 任务管理
│   ├── llm.py                   # LLM 模型管理
│   ├── logs.py                  # 日志查看
│   ├── models.py                # 模型目录
│   ├── providers.py             # Provider 管理
│   ├── session_recap.py         # 会话回顾
│   ├── sessions.py              # 会话管理
│   ├── skills.py                # 技能管理
│   ├── status.py                # 系统状态
│   └── uninstall.py              # 卸载程序
│
├── config/                      # 配置模块
│   ├── __init__.py
│   ├── config.py                # 配置加载/保存
│   ├── config_cli.py            # 配置 CLI
│   ├── model_cli.py             # 模型 CLI
│   ├── profiles.py              # 多配置文件系统
│   ├── skills_config.py         # 技能配置
│   └── tools_config.py          # 工具配置
│
├── proxy/                       # 代理子模块
│   ├── __init__.py
│   ├── cli.py                   # 代理 CLI
│   ├── server.py                # HTTP 代理服务器
│   └── adapters/
│       ├── __init__.py
│       └── base.py              # 适配器基类
│
├── setup/                       # 安装模块
│   ├── __init__.py
│   ├── env_loader.py            # .env 文件加载
│   ├── interactive_select.py     # 交互选择
│   └── setup_wizard.py          # 设置向导
│
├── system/                      # 系统功能模块
│   ├── __init__.py
│   ├── backup.py                # 备份功能
│   ├── callbacks.py              # 回调系统
│   ├── compat.py                 # 兼容性处理
│   ├── hooks.py                 # 生命周期钩子
│   └── relaunch.py              # CLI 自我重启
│
├── ui/                          # UI 层 (纯展示)
│   ├── __init__.py
│   ├── banner.py                # Banner 渲染
│   └── skin_engine.py           # 皮肤/主题系统
│
├── docs/
│   └── architecture.md          # 本文档
│
└── pyproject.toml
```

---

## 三、核心文件职责

### 3.1 核心入口

| 文件 | 职责 | 为什么需要 |
|------|------|-----------|
| `main.py` | CLI 主入口，参数解析 | 唯一入口点，协调所有功能 |
| `_parser.py` | argparse 定义 | 可复用的参数解析 |
| `commands.py` | 斜杠命令注册 | 统一命令管理 |

### 3.2 子目录职责

| 目录 | 职责 |
|------|------|
| `cli_commands/` | CLI 命令实现 (19 个命令) |
| `config/` | 配置相关功能 |
| `proxy/` | HTTP 代理与适配器 |
| `setup/` | 交互式安装向导 |
| `system/` | 系统功能 (备份、重启、钩子等) |
| `ui/` | UI 展示 (Banner、皮肤引擎) |

---

## 四、依赖关系图

```
cli/main.py (入口)
    │
    ├── _parser.py (参数解析)
    ├── commands.py (命令注册)
    │
    ├── cli_commands/*.py (命令实现)
    ├── config/*.py (配置相关)
    ├── proxy/*.py (代理相关)
    ├── setup/*.py (安装相关)
    ├── system/*.py (系统相关)
    └── ui/*.py (UI 展示)

agent/ (核心逻辑层)
    ├── skill_commands.py
    ├── skill_utils.py
    └── llm/
        ├── providers.py
        └── models.py

tools/ (工具层)
    ├── registry.py
    └── skills_tool.py
```

---

## 五、设计原则

### 5.1 单一职责原则

每个文件只做一件事：
- `config.py` - 只做配置
- `auth.py` - 只做认证
- `models.py` - 只做模型目录
- `banner.py` - 只做 Banner

### 5.2 CLI 入口调用核心

```
cli/main.py (入口)
    ↓
cli/_parser.py (参数解析)
    ↓
cli/commands.py (命令注册)
    ↓
cli/cli_commands/*.py (命令实现)
    ↓
agent/* (核心逻辑)
    ↓
tools/* (工具实现)
```

### 5.3 模块按功能域组织

```
cli/
├── cli_commands/     # CLI 命令
├── config/           # 配置相关
├── proxy/            # 代理相关
├── setup/           # 安装相关
├── system/           # 系统相关
└── ui/              # UI 展示相关
```

---

## 六、验收标准

- [ ] 所有功能测试通过
- [ ] 无循环依赖
- [ ] 每个文件 < 500 行
- [ ] 每个函数 < 100 行
- [ ] CLI 命令保持兼容
- [ ] 文档同步更新

---

*最后更新: 2026-06-19*
*版本: v3.0 - 已移除 hermes_cli/ 目录，kanban.py 迁移至 cli/cli_commands/*
