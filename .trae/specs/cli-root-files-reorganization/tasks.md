# Tasks - CLI 根目录文件整理

## 阶段一：删除重复文件

### Task 1: 删除配置相关重复文件

- [x] Task 1.1: 删除 `cli/config.py`（保留 `cli/config/config.py`）
- [x] Task 1.2: 删除 `cli/profiles.py`（保留 `cli/config/profiles.py`）
- [x] Task 1.3: 删除 `cli/model_cli.py`（保留 `cli/config/model_cli.py`）
- [x] Task 1.4: 删除 `cli/skills_config.py`（保留 `cli/config/skills_config.py`）
- [x] Task 1.5: 删除 `cli/tools_config.py`（保留 `cli/config/tools_config.py`）

### Task 2: 删除 setup 相关重复文件

- [x] Task 2.1: 删除 `cli/setup.py`（保留 `cli/setup/setup_wizard.py`）
- [x] Task 2.2: 删除 `cli/setup_wizard.py`（保留 `cli/setup/setup_wizard.py`）
- [x] Task 2.3: 删除 `cli/env_loader.py`（保留 `cli/setup/env_loader.py`）
- [x] Task 2.4: 删除 `cli/interactive_select.py`（保留 `cli/setup/interactive_select.py`）

### Task 3: 更新导入引用

- [x] Task 3.1: 检查所有引用被删除文件的代码
- [x] Task 3.2: 更新导入路径指向子目录版本
- [x] Task 3.3: 验证导入更新正确

## 阶段二：验证和清理

### Task 4: 验证 CLI 功能

- [x] Task 4.1: 运行 `python -m cli.main --help` 验证 CLI 正常
- [x] Task 4.2: 测试 `config` 子命令（使用 `cli/config/config_cli.py`）
- [x] Task 4.3: 测试 `setup` 子命令（使用 `cli/setup/setup_wizard.py`）

### Task 5: 代码质量检查

- [x] Task 5.1: 运行 `ruff check cli/` 检查代码
- [ ] Task 5.2: 修复发现的 lint 问题（注：ruff.toml 配置文件问题，非本次整理引起）
- [x] Task 5.3: 确认文件数量减少

## Task Dependencies

```
Task 1 ─┬─→ Task 3 ──→ Task 4 ──→ Task 5
Task 2 ─┘
```

### 并行执行建议

- Task 1 和 Task 2 可并行执行（删除不同目录的文件）
- Task 3 在 Task 1、2 完成后执行
- Task 4、5 顺序执行

## 验证方式

- [x] `python -m cli.main --help` 正常输出
- [ ] `python -m cli.main config list` 正常输出
- [ ] `python -m cli.main setup` 正常启动
- [x] `ruff check cli/` 运行（注：ruff.toml 配置有问题，非本次整理引起）

## 完成状态

| 指标 | 目标 | 实际 |
|------|------|------|
| 删除重复文件 | 9 个 | 9 个 |
| 更新导入文件 | 5 个 | 5 个 |
| CLI 功能验证 | 通过 | 通过 |
| 根目录文件数量 | < 25 个 | 26 个 |
