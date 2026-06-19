# CLI 根目录文件整理规范

## Why

当前 `cli/` 根目录存在 **35 个 .py 文件**散落问题：

1. **功能重复**: 根目录与子目录存在同名文件（如 `config.py` vs `config/config.py`）
2. **职责不清**: UI、配置、诊断等功能混在一起
3. **不符合架构规范**: 根据 `cli/docs/architecture.md`，根目录应只保留入口和核心文件

## What Changes

### 1. 删除重复文件（保留子目录版本）

| 根目录文件 | 子目录文件 | 操作 |
|-----------|-----------|------|
| `config.py` | `config/config.py` | 删除根目录 |
| `setup.py` | `setup/setup_wizard.py` | 删除根目录 |
| `setup_wizard.py` | `setup/setup_wizard.py` | 删除根目录 |
| `env_loader.py` | `setup/env_loader.py` | 删除根目录 |
| `interactive_select.py` | `setup/interactive_select.py` | 删除根目录 |
| `skills_config.py` | `config/skills_config.py` | 删除根目录 |
| `tools_config.py` | `config/tools_config.py` | 删除根目录 |
| `model_cli.py` | `config/model_cli.py` | 删除根目录 |
| `profiles.py` | `config/profiles.py` | 删除根目录 |

### 2. 保留根目录的核心文件

| 文件 | 原因 |
|------|------|
| `main.py` | CLI 唯一入口 |
| `_parser.py` | 参数解析器 |
| `commands.py` | 斜杠命令注册表 |
| `__init__.py` | 包标识文件 |

### 3. 保留根目录的独立功能文件

| 文件 | 功能 |
|------|------|
| `banner.py` | Banner 渲染 |
| `colors.py` | 颜色定义 |
| `cli_output.py` | 输出格式化 |
| `skin_engine.py` | 皮肤系统 |
| `curses_ui.py` | Curses UI |
| `auth_cli.py` | 认证 CLI |
| `llm_cli.py` | LLM CLI |
| `skills_cli.py` | 技能 CLI |
| `providers.py` | Provider 注册 |
| `models.py` | 模型定义 |
| `compat.py` | 兼容性模块 |
| `status.py` | 状态显示 |
| `dump.py` | 配置转储 |
| `debug.py` | 调试工具 |
| `hooks.py` | 生命周期钩子 |
| `callbacks.py` | 回调系统 |
| `completion.py` | Shell 补全 |
| `backup.py` | 备份功能 |
| `relaunch.py` | 重启功能 |
| `batch_runner.py` | 批量运行器 |
| `ui.py` | UI 入口（需清理） |

### 4. 清理 `ui.py`

`ui.py` 职责过重，需要将职责委托给独立模块：
- 颜色相关 → `colors.py`
- 输出相关 → `cli_output.py`
- Banner 相关 → `banner.py`

## Impact

- **导入路径变更**: 删除重复文件后，子目录版本成为唯一版本
- **向后兼容**: 如有外部导入使用根目录路径，需要更新

## ADDED Requirements

### Requirement: 文件唯一性
系统 SHALL 确保同一模块只有一个物理位置，删除重复文件。

### Requirement: 核心入口清晰
系统 SHALL 确保 `cli/` 根目录只包含入口文件和核心基础设施。

## MODIFIED Requirements

### Requirement: CLI 目录结构
CLI 相关代码 SHALL 组织到子目录：
- `cli_commands/` - CLI 命令
- `config/` - 配置相关
- `proxy/` - 代理服务
- `setup/` - 安装向导

## REMOVED Requirements

无

## Success Criteria

- [ ] 无重复文件（根目录 vs 子目录）
- [ ] `cli/` 根目录文件数量减少到合理范围（< 25 个）
- [ ] 所有现有导入仍然工作
- [ ] CLI 功能验证通过
