# Checklist - CLI/TUI 顶层目录分离

## 目录结构检查

- [ ] `tui/` 顶层目录已创建
- [ ] `tui/__init__.py` 已创建
- [ ] `tui/main.py` 入口文件已创建
- [ ] `tui/pyproject.toml` 已创建
- [ ] `tui/core/` 目录结构正确
- [ ] `tui/services/` 目录结构正确
- [ ] `tui/views/` 目录结构正确
- [ ] `tui/widgets/` 目录结构正确
- [ ] `tui/textual_app/` 目录结构正确
- [ ] `tui/theming/` 目录结构正确

## 文件迁移检查

- [ ] `tui/core/` 所有文件已迁移
- [ ] `tui/services/` 所有文件已迁移
- [ ] `tui/views/` 所有文件已迁移
- [ ] `tui/widgets/` 所有文件已迁移
- [ ] `tui/textual_app/` 所有文件已迁移
- [ ] `tui/theming/` 所有文件已迁移
- [ ] `cli/tui/` 旧目录已删除

## 导入路径检查

- [ ] `tui/__init__.py` 正确导出主类
- [ ] `tui/core/__init__.py` 正确导出
- [ ] `tui/textual_app/__init__.py` 正确导出
- [ ] `tui/theming/__init__.py` 正确导出
- [ ] `tui/views/__init__.py` 正确导出
- [ ] `tui/widgets/__init__.py` 正确导出
- [ ] `tui/services/__init__.py` 正确导出

## 功能验证检查

- [ ] `from tui.textual_app import HandsomeAgentApp` 正常工作
- [ ] `from tui.theming import ThemeManager` 正常工作
- [ ] `from tui.core import keybindings` 正常工作
- [ ] `python -m tui.main` 可以启动 TUI
- [ ] `python -m cli.main --textual` 可以从 CLI 启动 TUI

## 依赖关系检查

- [ ] `tui/pyproject.toml` 包含正确依赖
- [ ] 根 `pyproject.toml` 正确引用 cli 和 tui
- [ ] 没有循环导入问题

## 代码质量检查

- [ ] 没有导入错误
- [ ] linter 检查通过
- [ ] type checker 检查通过（如有）
- [ ] 没有遗留的 `cli.tui` 导入（除非保留兼容层）
