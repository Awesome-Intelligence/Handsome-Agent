# Checklist - CLI 深度整理

## 目录结构检查

### 新建目录
- [ ] `cli/ui/` 目录已创建
- [ ] `cli/ui/__init__.py` 已创建
- [ ] `cli/system/` 目录已创建
- [ ] `cli/system/__init__.py` 已创建

### 根目录文件（最终应只有 4 个）
- [ ] `cli/__init__.py` 保留
- [ ] `cli/main.py` 保留
- [ ] `cli/_parser.py` 保留
- [ ] `cli/commands.py` 保留

## UI 层文件检查 (cli/ui/)

- [ ] `cli/ui/banner.py` 已移动
- [ ] `cli/ui/colors.py` 已移动
- [ ] `cli/ui/cli_output.py` 已移动
- [ ] `cli/ui/curses_ui.py` 已移动
- [ ] `cli/ui/skin_engine.py` 已移动
- [ ] `cli/ui/ui.py` 已移动

## CLI 命令文件检查 (cli/cli_commands/)

- [ ] `cli/cli_commands/auth.py` 已移动
- [ ] `cli/cli_commands/llm.py` 已移动
- [ ] `cli/cli_commands/skills.py` 已移动
- [ ] `cli/cli_commands/config.py` 已移动
- [ ] `cli/cli_commands/providers.py` 已移动
- [ ] `cli/cli_commands/models.py` 已移动
- [ ] `cli/cli_commands/status.py` 已移动
- [ ] `cli/cli_commands/dump.py` 已移动
- [ ] `cli/cli_commands/debug.py` 已移动
- [ ] `cli/cli_commands/completion.py` 已移动

## 系统功能文件检查 (cli/system/)

- [ ] `cli/system/backup.py` 已移动
- [ ] `cli/system/relaunch.py` 已移动
- [ ] `cli/system/hooks.py` 已移动
- [ ] `cli/system/batch_runner.py` 已移动
- [ ] `cli/system/compat.py` 已移动

## 原文件删除检查

### UI 层
- [ ] `cli/banner.py` 已删除
- [ ] `cli/colors.py` 已删除
- [ ] `cli/cli_output.py` 已删除
- [ ] `cli/curses_ui.py` 已删除
- [ ] `cli/skin_engine.py` 已删除
- [ ] `cli/ui.py` 已删除

### CLI 命令
- [ ] `cli/auth_cli.py` 已删除
- [ ] `cli/llm_cli.py` 已删除
- [ ] `cli/skills_cli.py` 已删除
- [ ] `cli/config_cli.py` 已删除
- [ ] `cli/providers.py` 已删除
- [ ] `cli/models.py` 已删除
- [ ] `cli/status.py` 已删除
- [ ] `cli/dump.py` 已删除
- [ ] `cli/debug.py` 已删除
- [ ] `cli/completion.py` 已删除

### 系统功能
- [ ] `cli/backup.py` 已删除
- [ ] `cli/relaunch.py` 已删除
- [ ] `cli/hooks.py` 已删除
- [ ] `cli/batch_runner.py` 已删除
- [ ] `cli/compat.py` 已删除

## 导入路径更新检查

### cli/main.py
- [ ] `from cli.ui.banner import` 更新
- [ ] `from cli.ui.colors import` 更新
- [ ] `from cli.ui.cli_output import` 更新
- [ ] `from cli.ui.curses_ui import` 更新
- [ ] `from cli.ui.skin_engine import` 更新
- [ ] `from cli.ui.ui import` 更新
- [ ] `from cli.cli_commands.auth import` 更新
- [ ] `from cli.cli_commands.llm import` 更新
- [ ] `from cli.cli_commands.skills import` 更新
- [ ] `from cli.cli_commands.config import` 更新
- [ ] `from cli.cli_commands.providers import` 更新
- [ ] `from cli.cli_commands.models import` 更新
- [ ] `from cli.cli_commands.status import` 更新
- [ ] `from cli.cli_commands.dump import` 更新
- [ ] `from cli.cli_commands.debug import` 更新
- [ ] `from cli.cli_commands.completion import` 更新
- [ ] `from cli.system.backup import` 更新
- [ ] `from cli.system.relaunch import` 更新
- [ ] `from cli.system.hooks import` 更新
- [ ] `from cli.system.batch_runner import` 更新
- [ ] `from cli.system.compat import` 更新

### cli/__init__.py
- [ ] 更新所有相对导入

### tests/
- [ ] 更新 `tests/integration/test_cli_commands.py` 中的导入
- [ ] 更新 `tests/unit/cli/test_setup_wizard.py` 中的导入
- [ ] 更新 `tests/unit/cli/test_interactive_select.py` 中的导入
- [ ] 检查并更新其他测试文件

### tui/
- [ ] 检查并更新 `tui/` 中引用 `cli.ui` 的导入

### agent/
- [ ] 检查并更新 `agent/acp/entry.py` 中的导入

## 功能验证检查

- [ ] `python -m cli.main --help` 正常输出
- [ ] `python -m cli.main --version` 正常输出

## 最终目录结构验证

```
cli/
├── __init__.py           # ✅ 核心入口
├── main.py               # ✅ 核心入口
├── _parser.py            # ✅ 核心入口
├── commands.py           # ✅ 核心入口
│
├── ui/                   # ✅ 新目录
│   ├── __init__.py
│   ├── banner.py
│   ├── colors.py
│   ├── cli_output.py
│   ├── curses_ui.py
│   ├── skin_engine.py
│   └── ui.py
│
├── cli_commands/         # ✅ 已有+增补
│   ├── __init__.py
│   ├── acp.py
│   ├── auth.py
│   ├── llm.py
│   ├── skills.py
│   ├── config.py
│   ├── providers.py
│   ├── models.py
│   ├── status.py
│   ├── dump.py
│   ├── debug.py
│   ├── completion.py
│   ├── sessions.py
│   ├── doctor.py
│   ├── gateway.py
│   ├── logs.py
│   ├── session_recap.py
│   ├── uninstall.py
│   └── cron.py
│
├── system/               # ✅ 新目录
│   ├── __init__.py
│   ├── backup.py
│   ├── relaunch.py
│   ├── hooks.py
│   ├── batch_runner.py
│   └── compat.py
│
├── config/               # ✅ 已有
├── setup/                # ✅ 已有
└── proxy/                # ✅ 已有
```
