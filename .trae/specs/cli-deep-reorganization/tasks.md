# Tasks - CLI 深度整理

## 阶段一：创建目录结构

### Task 1: 创建新子目录

- [ ] Task 1.1: 创建 `cli/ui/` 目录及 `__init__.py`
- [ ] Task 1.2: 创建 `cli/system/` 目录及 `__init__.py`

## 阶段二：移动 UI 层文件

### Task 2: 移动 UI 文件到 cli/ui/

- [ ] Task 2.1: 移动 `cli/banner.py` → `cli/ui/banner.py`
- [ ] Task 2.2: 移动 `cli/colors.py` → `cli/ui/colors.py`
- [ ] Task 2.3: 移动 `cli/cli_output.py` → `cli/ui/cli_output.py`
- [ ] Task 2.4: 移动 `cli/curses_ui.py` → `cli/ui/curses_ui.py`
- [ ] Task 2.5: 移动 `cli/skin_engine.py` → `cli/ui/skin_engine.py`
- [ ] Task 2.6: 移动 `cli/ui.py` → `cli/ui/ui.py`

## 阶段三：移动 CLI 命令文件

### Task 3: 移动 CLI 命令到 cli/cli_commands/

- [ ] Task 3.1: 移动 `cli/auth_cli.py` → `cli/cli_commands/auth.py`
- [ ] Task 3.2: 移动 `cli/llm_cli.py` → `cli/cli_commands/llm.py`
- [ ] Task 3.3: 移动 `cli/skills_cli.py` → `cli/cli_commands/skills.py`
- [ ] Task 3.4: 移动 `cli/config_cli.py` → `cli/cli_commands/config.py`
- [ ] Task 3.5: 移动 `cli/providers.py` → `cli/cli_commands/providers.py`
- [ ] Task 3.6: 移动 `cli/models.py` → `cli/cli_commands/models.py`
- [ ] Task 3.7: 移动 `cli/status.py` → `cli/cli_commands/status.py`
- [ ] Task 3.8: 移动 `cli/dump.py` → `cli/cli_commands/dump.py`
- [ ] Task 3.9: 移动 `cli/debug.py` → `cli/cli_commands/debug.py`
- [ ] Task 3.10: 移动 `cli/completion.py` → `cli/cli_commands/completion.py`

## 阶段四：移动系统功能文件

### Task 4: 移动系统功能到 cli/system/

- [ ] Task 4.1: 移动 `cli/backup.py` → `cli/system/backup.py`
- [ ] Task 4.2: 移动 `cli/relaunch.py` → `cli/system/relaunch.py`
- [ ] Task 4.3: 移动 `cli/hooks.py` → `cli/system/hooks.py`
- [ ] Task 4.4: 移动 `cli/batch_runner.py` → `cli/system/batch_runner.py`
- [ ] Task 4.5: 移动 `cli/compat.py` → `cli/system/compat.py`

## 阶段五：更新导入路径

### Task 5: 更新所有导入

- [ ] Task 5.1: 更新 `cli/main.py` 中的导入
- [ ] Task 5.2: 更新 `cli/__init__.py` 中的导入
- [ ] Task 5.3: 更新 `cli/_parser.py` 中的导入（如有）
- [ ] Task 5.4: 更新 `cli/commands.py` 中的导入（如有）
- [ ] Task 5.5: 更新移动后文件内部的相对导入
- [ ] Task 5.6: 更新 `tui/` 中引用 `cli/ui/` 的导入（如有）
- [ ] Task 5.7: 更新 `tests/` 中引用旧路径的导入
- [ ] Task 5.8: 更新 `agent/` 中引用 `cli/` 的导入（如有）

## 阶段六：验证

### Task 6: 验证 CLI 功能

- [ ] Task 6.1: 运行 `python -m cli.main --help` 验证
- [ ] Task 6.2: 验证 `python -m cli.main --version`
- [ ] Task 6.3: 确认根目录文件数量

## Task Dependencies

```
Task 1 (创建目录) ──→ Task 2 ──→ Task 3 ──→ Task 4 ──→ Task 5 ──→ Task 6
                         │            │            │
                     (并行移动)    (并行移动)    (并行移动)
```

### 并行执行建议

- Task 2、3、4 可并行执行（移动不同目录的文件）
- Task 5 在 Task 2、3、4 完成后执行
- Task 6 最后执行
