# CLI 深度整理规范

## Why

当前 `cli/` 根目录仍有 26 个文件散落，需要按功能分类整理到子目录。

## What Changes

### 整理后目标结构

```
cli/
├── __init__.py           # 核心入口（保留）
├── main.py               # 核心入口（保留）
├── _parser.py            # 参数解析（保留）
├── commands.py           # 斜杠命令注册（保留）
│
├── ui/                   # UI 层（新建）
│   ├── __init__.py
│   ├── banner.py         # ← cli/banner.py
│   ├── colors.py         # ← cli/colors.py
│   ├── cli_output.py     # ← cli/cli_output.py
│   ├── curses_ui.py      # ← cli/curses_ui.py
│   ├── skin_engine.py    # ← cli/skin_engine.py
│   └── ui.py             # ← cli/ui.py
│
├── cli_commands/         # CLI 命令（增补）
│   ├── __init__.py
│   ├── acp.py            # 已有
│   ├── auth.py           # ← cli/auth_cli.py
│   ├── llm.py            # ← cli/llm_cli.py
│   ├── skills.py         # ← cli/skills_cli.py
│   ├── config.py         # ← cli/config_cli.py
│   ├── providers.py      # ← cli/providers.py
│   ├── models.py         # ← cli/models.py
│   ├── status.py         # ← cli/status.py
│   ├── dump.py           # ← cli/dump.py
│   ├── debug.py          # ← cli/debug.py
│   ├── completion.py     # ← cli/completion.py
│   ├── sessions.py       # 已有
│   ├── doctor.py         # 已有
│   ├── gateway.py        # 已有
│   ├── logs.py           # 已有
│   ├── session_recap.py  # 已有
│   ├── uninstall.py      # 已有
│   └── cron.py           # 已有
│
├── system/               # 系统功能（新建）
│   ├── __init__.py
│   ├── backup.py         # ← cli/backup.py
│   ├── relaunch.py       # ← cli/relaunch.py
│   ├── hooks.py          # ← cli/hooks.py
│   ├── batch_runner.py   # ← cli/batch_runner.py
│   └── compat.py         # ← cli/compat.py
│
├── config/               # 配置（已有）
├── setup/                # 安装（已有）
└── proxy/                # 代理（已有）
```

### 文件重命名映射

| 原路径 | 新路径 |
|--------|--------|
| `cli/banner.py` | `cli/ui/banner.py` |
| `cli/colors.py` | `cli/ui/colors.py` |
| `cli/cli_output.py` | `cli/ui/cli_output.py` |
| `cli/curses_ui.py` | `cli/ui/curses_ui.py` |
| `cli/skin_engine.py` | `cli/ui/skin_engine.py` |
| `cli/ui.py` | `cli/ui/ui.py` |
| `cli/auth_cli.py` | `cli/cli_commands/auth.py` |
| `cli/llm_cli.py` | `cli/cli_commands/llm.py` |
| `cli/skills_cli.py` | `cli/cli_commands/skills.py` |
| `cli/config_cli.py` | `cli/cli_commands/config.py` |
| `cli/providers.py` | `cli/cli_commands/providers.py` |
| `cli/models.py` | `cli/cli_commands/models.py` |
| `cli/status.py` | `cli/cli_commands/status.py` |
| `cli/dump.py` | `cli/cli_commands/dump.py` |
| `cli/debug.py` | `cli/cli_commands/debug.py` |
| `cli/completion.py` | `cli/cli_commands/completion.py` |
| `cli/backup.py` | `cli/system/backup.py` |
| `cli/relaunch.py` | `cli/system/relaunch.py` |
| `cli/hooks.py` | `cli/system/hooks.py` |
| `cli/batch_runner.py` | `cli/system/batch_runner.py` |
| `cli/compat.py` | `cli/system/compat.py` |

## Impact

- 所有引用旧路径的导入需要更新
- CLI 入口 `python -m cli.main` 保持不变

## Success Criteria

- [ ] 根目录只保留 4 个核心入口文件
- [ ] UI 功能移到 `cli/ui/`
- [ ] CLI 命令移到 `cli/cli_commands/`
- [ ] 系统功能移到 `cli/system/`
- [ ] 所有导入路径更新
- [ ] CLI 功能验证通过
