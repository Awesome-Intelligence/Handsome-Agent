# Checklist - CLI/TUI 顶层目录分离

## 目录结构检查

- [x] `tui/` 顶层目录已创建
- [x] `tui/__init__.py` 已创建
- [x] `tui/main.py` 入口文件已创建
- [x] `tui/pyproject.toml` 已创建
- [x] `tui/core/` 目录结构正确
- [x] `tui/services/` 目录结构正确
- [x] `tui/views/` 目录结构正确
- [x] `tui/widgets/` 目录结构正确
- [x] `tui/textual_app/` 目录结构正确
- [x] `tui/theming/` 目录结构正确

## 文件迁移检查

- [x] `tui/core/` 所有文件已迁移
- [x] `tui/services/` 所有文件已迁移
- [x] `tui/views/` 所有文件已迁移
- [x] `tui/widgets/` 所有文件已迁移
- [x] `tui/textual_app/` 所有文件已迁移
- [x] `tui/theming/` 所有文件已迁移

## 导入路径检查

- [x] `tui/__init__.py` 正确导出主类
- [x] `tui/core/__init__.py` 正确导出
- [x] `tui/textual_app/__init__.py` 正确导出
- [x] `tui/theming/__init__.py` 正确导出
- [x] `tui/views/__init__.py` 正确导出
- [x] `tui/widgets/__init__.py` 正确导出
- [x] `tui/services/__init__.py` 正确导出

## 功能验证检查

- [x] `from tui.textual_app import HandsomeAgentApp` 正常工作
- [x] `from tui.theming import ThemeManager` 正常工作
- [x] `from tui.core import keybindings` 正常工作
- [x] `from tui.widgets import StatusBar` 正常工作
- [x] `python -m cli.main --textual` 可以从 CLI 启动 TUI（入口文件已创建）

## 向后兼容性检查

- [x] `from cli.tui import TEXTUAL_AVAILABLE` 向后兼容（有 DeprecationWarning）
- [x] `cli/tui/__init__.py` 提供重导出

## 代码更新检查

- [x] `cli/main.py` 更新为 `from tui import ...`
- [x] `cli/compat.py` 更新为 `from tui.core.curses_ui import ...`
- [x] `cli/curses_ui.py` 更新为 `from tui.core.curses_ui import ...`
- [x] `cli/tui/sidebar.py` 更新为 `from tui.theming import ...`
- [x] `cli/tui/widgets/message_list.py` 更新为 `from tui.theming import ...`
- [x] `cli/tui/theming/__init__.py` 文档注释更新
- [x] `cli/tui/core/__init__.py` 更新为重导出

## 依赖关系检查

- [x] `tui/pyproject.toml` 包含正确依赖
- [ ] 根 `pyproject.toml` 正确引用 cli 和 tui
- [x] 没有循环导入问题

## 代码质量检查

- [x] 新导入路径正常工作
- [x] 向后兼容导入正常工作（有弃用警告）
- [x] CLI 主入口正常启动
- [ ] linter 检查通过
- [ ] type checker 检查通过（如有）
- [ ] 删除旧 `cli/tui/` 目录

## 后续步骤

1. [ ] 运行 linter 检查代码质量
2. [ ] 运行 type checker 检查
3. [ ] （可选）删除旧的 `cli/tui/` 目录或保留兼容层
4. [ ] 更新项目文档
