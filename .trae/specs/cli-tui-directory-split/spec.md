# CLI/TUI 顶层目录分离规范

## Why

当前项目结构存在 CLI 和 TUI 职责混淆的问题：

1. **TUI 嵌套过深** - `cli/tui/` 导致导入路径冗长：`from cli.tui.textual_app import ...`
2. **CLI 根目录膨胀** - 33 个独立 Python 文件散落，缺乏组织
3. **CodeWhale 参考** - Rust 项目将 CLI/TUI 作为独立 crate 顶层分离

需要将 TUI 从 `cli/tui/` 提升到顶层 `tui/`，并重组 CLI 目录结构。

## What Changes

### 目录结构变更

**变更前：**
```
handsome-agent/
├── cli/                        # 所有代码堆在一起
│   ├── cli_commands/           # 命令（部分文件）
│   ├── components/             # 组件（部分文件）
│   ├── proxy/                  # 代理服务
│   ├── tui/                    # ❌ TUI 嵌套过深
│   │   ├── core/
│   │   ├── services/
│   │   ├── textual_app/
│   │   ├── theming/
│   │   ├── views/
│   │   └── widgets/
│   ├── main.py
│   ├── auth_cli.py             # ❌ 散落文件
│   ├── banner.py
│   ├── config.py
│   ├── doctor.py
│   ├── setup.py
│   ├── skills_cli.py
│   ├── status.py
│   └── ... (共 33 个 .py 文件)
```

**变更后：**
```
handsome-agent/
├── cli/                        # CLI 入口和命令
│   ├── pyproject.toml
│   ├── __init__.py
│   ├── main.py                 # CLI 入口
│   ├── _parser.py              # 参数解析
│   │
│   ├── cli_commands/           # CLI 命令实现
│   │   ├── __init__.py
│   │   ├── acp.py
│   │   ├── cron.py
│   │   ├── doctor.py
│   │   ├── gateway.py
│   │   ├── logs.py
│   │   ├── session_recap.py
│   │   ├── sessions.py
│   │   └── uninstall.py
│   │
│   ├── components/             # CLI 通用组件
│   │   ├── __init__.py
│   │   ├── banner.py
│   │   ├── colors.py
│   │   ├── output.py
│   │   └── ui.py
│   │
│   └── (配置文件)               # 可选：移到顶层
│       ├── auth_cli.py
│       ├── config_cli.py
│       ├── models.py
│       ├── profiles.py
│       └── providers.py
│
├── tui/                        # TUI（提升到顶层）
│   ├── pyproject.toml
│   ├── __init__.py
│   ├── main.py                 # TUI 入口
│   │
│   ├── core/                   # 基础设施
│   │   ├── __init__.py
│   │   ├── curses_ui.py
│   │   ├── keybindings.py
│   │   └── markdown_renderer.py
│   │
│   ├── services/               # 服务层
│   │   ├── __init__.py
│   │   └── session_store.py
│   │
│   ├── views/                  # 视图
│   │   ├── __init__.py
│   │   ├── chat_view.py
│   │   ├── help_view.py
│   │   ├── onboarding_screen.py
│   │   ├── session_picker.py
│   │   └── welcome_screen.py
│   │
│   ├── widgets/                # 组件
│   │   ├── __init__.py
│   │   ├── approval_dialog.py
│   │   ├── command_palette.py
│   │   ├── message_list.py
│   │   ├── status_bar.py
│   │   └── streaming_text.py
│   │
│   ├── textual_app/            # Textual 应用
│   │   ├── __init__.py
│   │   ├── app.py
│   │   ├── css.py
│   │   ├── helpers.py
│   │   ├── log_handler.py
│   │   ├── notifications.py
│   │   └── text_area.py
│   │
│   └── theming/                # 主题系统
│       ├── __init__.py
│       ├── theme_manager.py
│       ├── theme_config.py
│       ├── preset_themes.py
│       ├── colors.py
│       ├── icons.py
│       ├── typography.py
│       └── css/
│           ├── base.css
│           ├── layout.css
│           ├── components.css
│           ├── animations.css
│           └── themes/
│               └── default.css
│
├── proxy/                      # 代理服务（保持位置）
├── core/                       # 共享核心（未来扩展）
└── pyproject.toml               # 根 pyproject
```

### 导入路径变更

| 旧路径 | 新路径 |
|--------|--------|
| `from cli.tui.textual_app import ...` | `from tui.textual_app import ...` |
| `from cli.tui.theming import ...` | `from tui.theming import ...` |
| `from cli.tui.core import ...` | `from tui.core import ...` |
| `from cli.tui.widgets import ...` | `from tui.widgets import ...` |
| `from cli.tui.views import ...` | `from tui.views import ...` |

### 入口文件变更

| 旧入口 | 新入口 |
|--------|--------|
| `python -m cli.main` | `python -m cli.main` (CLI 不变) |
| `python -m cli.main --textual` | `python -m tui.main` (TUI 独立入口) |

## Impact

### 影响的规格
- `tui-architecture-refactor` - 需更新导入路径
- `cli-to-tui-rename` - 可合并到本规范

### 影响的代码
- 所有 `cli/tui/` 下的 Python 文件
- 所有引用 `cli.tui.*` 的导入语句
- `cli/main.py` 中的 TUI 启动逻辑
- `proxy/` 目录（如果依赖 tui 模块）

## ADDED Requirements

### Requirement: TUI 顶层分离
系统 SHALL 提供独立的 `tui/` 顶层目录，与 `cli/` 平级。

### Requirement: CLI 入口保持
系统 SHALL 保持 `python -m cli.main` 作为 CLI 主入口。

### Requirement: TUI 独立入口
系统 SHALL 提供 `python -m tui.main` 作为 TUI 独立入口。

### Requirement: 导入兼容性
重构后，原有导入路径需要通过兼容层或更新导入保持工作。

## MODIFIED Requirements

### Requirement: CLI 目录结构
CLI 相关代码 SHALL 组织到 `cli/` 目录下，包括：
- `cli_commands/` - CLI 命令实现
- `components/` - CLI 通用组件

### Requirement: TUI 目录结构
TUI 相关代码 SHALL 组织到 `tui/` 目录下，包括：
- `core/` - 基础设施
- `views/` - 视图
- `widgets/` - 组件
- `textual_app/` - 主应用
- `theming/` - 主题系统
- `services/` - 服务层

## REMOVED Requirements

无

## 技术细节

### 1. 迁移策略

#### Phase 1: 创建新目录
1. 创建顶层 `tui/` 目录
2. 创建 `tui/pyproject.toml`
3. 创建 `tui/main.py` 入口
4. 迁移 `cli/tui/` 下所有文件到 `tui/`

#### Phase 2: 更新导入
1. 更新所有 Python 文件中的导入路径
2. 更新 `tui/__init__.py` 导出
3. 更新 `proxy/` 中的导入

#### Phase 3: 创建兼容层
1. 在 `cli/tui/` 创建兼容层，导入新位置
2. 或者创建 `cli/tui/__init__.py` 重导出

#### Phase 4: 验证和清理
1. 验证 `python -m tui.main` 正常工作
2. 验证 `python -m cli.main --textual` 正常工作
3. 删除旧的 `cli/tui/` 目录

### 2. pyproject.toml 配置

```toml
# tui/pyproject.toml
[project]
name = "handsome-agent-tui"
version = "0.1.0"
dependencies = [
    "textual>=0.50.0",
    "rich>=13.0.0",
]

[project.scripts]
handsome-tui = "tui.main:main"
```

### 3. 入口文件

```python
# tui/main.py
"""TUI 独立入口"""
from tui.textual_app import main

if __name__ == "__main__":
    main()
```

```python
# cli/main.py (更新)
# CLI 启动 TUI 时调用
def launch_textual():
    from tui.textual_app import main
    main()
```

### 4. 与现有 spec 的关系

本规范与以下规范存在依赖或重叠：
- `tui-architecture-refactor` - 完成本规范后，需要更新其导入路径
- `cli-to-tui-rename` - 已完成，可作为本规范的前置参考

## Success Criteria

- [ ] `tui/` 目录独立于 `cli/` 顶层存在
- [ ] `python -m tui.main` 可以启动 TUI
- [ ] 所有 `cli.tui.*` 导入更新为 `tui.*`
- [ ] `cli/` 根目录文件数量减少
- [ ] 目录结构与 CodeWhale 参考结构一致
