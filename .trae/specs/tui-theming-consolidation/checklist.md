# Checklist - TUI Theming 目录合并

## 阶段一：目录结构创建

### Task 1: 创建 theming/ 目录

- [x] Task 1.1: `cli/tui/theming/` 目录创建完成
- [x] Task 1.2: `cli/tui/theming/css/` 目录创建完成
- [x] Task 1.3: `cli/tui/theming/css/themes/` 目录创建完成

### Task 2: CSS 文件迁移

- [x] Task 2.1: `theming/css/__init__.py` 创建完成
- [x] Task 2.2: `theming/css/base.css` 迁移完成
- [x] Task 2.3: `theming/css/components.css` 迁移完成
- [x] Task 2.4: `theming/css/layout.css` 迁移完成
- [x] Task 2.5: `theming/css/animations.css` 迁移完成
- [x] Task 2.6: `theming/css/themes/default.css` 迁移完成
- [x] Task 2.7: CSS 加载函数导出正确

### Task 3: Python 模块迁移

- [x] Task 3.1: `theming/__init__.py` 合并导出完成
- [x] Task 3.2: `theming/theme_config.py` 迁移完成
- [x] Task 3.3: `theming/theme_manager.py` 迁移完成
- [x] Task 3.4: `theming/colors.py` 迁移完成
- [x] Task 3.5: `theming/icons.py` 迁移完成
- [x] Task 3.6: `theming/preset_themes.py` 迁移完成
- [x] Task 3.7: `theming/typography.py` 迁移完成

## 阶段二：导入路径更新

### Task 4-8: 内部导入更新

- [x] Task 4: views/ 导入更新完成
- [x] Task 5: widgets/ 导入更新完成
- [x] Task 6: services/ 导入更新完成
- [x] Task 7: textual_app/ 导入更新完成
- [x] Task 8: 其他模块导入更新完成

### Task 9: 顶层导出更新

- [x] Task 9.1: `cli/tui/__init__.py` 从 theming 导出正确
- [x] Task 9.2: 所有公共 API 导出存在

## 阶段三：验证和清理

### Task 10: 导入验证

- [x] Task 10.1: `from cli.tui.theming import ThemeManager` 工作正常
- [x] Task 10.2: `from cli.tui.theming.css import get_stylesheets` 工作正常
- [x] Task 10.3: `from cli.tui.theming import STATUS_ONLINE` 工作正常
- [x] Task 10.4: 没有循环导入错误

### Task 11: 目录清理

- [x] Task 11.1: 旧的 `cli/tui/styles/` 目录已删除
- [x] Task 11.2: 旧的 `cli/tui/themes/` 目录已删除
- [x] Task 11.3: 目录结构验证正确

## 最终验证

### 目录结构验证

- [x] `cli/tui/theming/` 目录存在
- [x] `cli/tui/theming/css/` 目录存在
- [x] `cli/tui/theming/css/themes/` 目录存在
- [x] 所有 Python 模块文件存在
- [x] 所有 CSS 文件存在

### 导入验证

- [x] `from cli.tui.theming import ThemeManager, get_theme_manager` 工作
- [x] `from cli.tui.theming import Theme, ThemeConfig` 工作
- [x] `from cli.tui.theming import STATUS_ONLINE, STATUS_ERROR` 工作
- [x] `from cli.tui.theming.css import get_stylesheets` 工作
- [x] `from cli.tui.theming import MESSAGE_ICONS, FILE_TYPE_ICONS` 工作

### 功能验证

- [x] ThemeManager 可以正常实例化
- [x] get_stylesheets() 返回正确的 CSS 文件列表
- [x] 颜色常量可以正常导入
- [x] 图标常量可以正常导入
