# Tasks - TUI Theming 目录合并

## 阶段一：创建新目录结构

### Task 1: 创建 theming/ 目录

- [x] Task 1.1: 创建 `cli/tui/theming/` 目录
- [x] Task 1.2: 创建 `cli/tui/theming/css/` 目录
- [x] Task 1.3: 创建 `cli/tui/theming/css/themes/` 目录

### Task 2: 迁移 CSS 文件

- [x] Task 2.1: 移动 `styles/__init__.py` 内容到 `theming/css/__init__.py`
- [x] Task 2.2: 移动 `styles/base.css` 到 `theming/css/base.css`
- [x] Task 2.3: 移动 `styles/components.css` 到 `theming/css/components.css`
- [x] Task 2.4: 移动 `styles/layout.css` 到 `theming/css/layout.css`
- [x] Task 2.5: 移动 `styles/animations.css` 到 `theming/css/animations.css`
- [x] Task 2.6: 移动 `styles/themes/default.css` 到 `theming/css/themes/default.css`
- [x] Task 2.7: 更新 `theming/css/__init__.py` 导出 CSS 加载函数

### Task 3: 迁移 Python 模块

- [x] Task 3.1: 移动 `themes/__init__.py` 内容到 `theming/__init__.py`（合并）
- [x] Task 3.2: 移动 `themes/theme_config.py` 到 `theming/theme_config.py`
- [x] Task 3.3: 移动 `themes/theme_manager.py` 到 `theming/theme_manager.py`
- [x] Task 3.4: 移动 `themes/colors.py` 到 `theming/colors.py`
- [x] Task 3.5: 移动 `themes/icons.py` 到 `theming/icons.py`
- [x] Task 3.6: 移动 `themes/preset_themes.py` 到 `theming/preset_themes.py`
- [x] Task 3.7: 移动 `themes/typography.py` 到 `theming/typography.py`

## 阶段二：更新导入路径

### Task 4: 更新内部导入 - views/

- [x] Task 4.1: 检查 views/ 中对 `cli.tui.styles` 的引用
- [x] Task 4.2: 更新 views/ 中的导入路径

### Task 5: 更新内部导入 - widgets/

- [x] Task 5.1: 检查 widgets/ 中对 `cli.tui.styles` 和 `cli.tui.themes` 的引用
- [x] Task 5.2: 更新 widgets/ 中的导入路径

### Task 6: 更新内部导入 - services/

- [x] Task 6.1: 检查 services/ 中对 `cli.tui.styles` 和 `cli.tui.themes` 的引用
- [x] Task 6.2: 更新 services/ 中的导入路径

### Task 7: 更新内部导入 - textual_app/

- [x] Task 7.1: 检查 textual_app/ 中对 `cli.tui.styles` 和 `cli.tui.themes` 的引用
- [x] Task 7.2: 更新 textual_app/ 中的导入路径

### Task 8: 更新内部导入 - 其他模块

- [x] Task 8.1: 检查 sidebar.py 中的导入
- [x] Task 8.2: 检查 cli/tui/__init__.py 中的导出
- [x] Task 8.3: 更新所有其他引用

### Task 9: 更新 cli/tui/__init__.py

- [x] Task 9.1: 更新 `cli/tui/__init__.py` 从 `theming` 导出
- [x] Task 9.2: 确保向后兼容的导出存在

## 阶段三：验证和清理

### Task 10: 验证导入

- [x] Task 10.1: 运行 `python -c "from cli.tui.theming import ThemeManager"` 验证
- [x] Task 10.2: 运行 `python -c "from cli.tui.theming.css import get_stylesheets"` 验证
- [x] Task 10.3: 运行 `python -c "from cli.tui.theming import STATUS_ONLINE"` 验证
- [x] Task 10.4: 检查没有循环导入

### Task 11: 清理旧目录

- [x] Task 11.1: 删除旧的 `cli/tui/styles/` 目录
- [x] Task 11.2: 删除旧的 `cli/tui/themes/` 目录
- [x] Task 11.3: 验证目录结构正确

## Task Dependencies

```
Task 1 (创建目录) ──→ Task 2 (迁移CSS) ──┐
                                          │
Task 3 (迁移Python) ──────────────────────┼──→ Task 4-8 (更新导入)
                                          │
Task 9 (更新导出) ────────────────────────┘
                                          │
                                          ▼
                               Task 10 (验证导入)
                                          │
                                          ▼
                               Task 11 (清理旧目录)
```

### 并行执行建议

- **第一波并行**: Task 1 可以立即执行（创建目录）
- **第二波并行**: Task 2 和 Task 3 可以并行执行（迁移文件）
- **第三波并行**: Task 4, 5, 6, 7, 8 可以并行执行（更新导入）
- **第四波**: Task 9 单独执行
- **第五波**: Task 10 单独执行
- **第六波**: Task 11 单独执行

## 验证方式

- [x] Python 导入测试
- [x] CSS 文件路径验证
- [x] 目录结构验证
