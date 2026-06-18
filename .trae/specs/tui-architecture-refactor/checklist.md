# Checklist - TUI 架构重构

## 阶段一：themes/ 子包

### Task 1: 创建 themes/ 目录结构

- [ ] Task 1.1: `cli/tui/themes/` 目录创建完成
- [ ] Task 1.2: `themes/__init__.py` 规划完成
- [ ] Task 1.3: `themes/theme_config.py` 创建完成
- [ ] Task 1.4: `themes/preset_themes.py` 创建完成
- [ ] Task 1.5: `themes/icons.py` 创建完成
- [ ] Task 1.6: `themes/colors.py` 创建完成
- [ ] Task 1.7: `themes/theme_manager.py` 创建完成

### Task 2: 迁移 themes.py

- [ ] Task 2.1: Theme 和 ThemeConfig 数据类迁移完成
- [ ] Task 2.2: 预设主题迁移完成
- [ ] Task 2.3: 图标映射迁移完成
- [ ] Task 2.4: 透明颜色函数迁移完成
- [ ] Task 2.5: ThemeManager 迁移完成
- [ ] Task 2.6: `themes/__init__.py` 导出完成
- [ ] Task 2.7: 向后兼容重导出完成

## 阶段二：textual_app/ 子包

### Task 3: 创建 textual_app/ 目录结构

- [ ] Task 3.1: `cli/tui/textual_app/` 目录创建完成
- [ ] Task 3.2: `textual_app/__init__.py` 规划完成
- [ ] Task 3.3: `textual_app/css.py` 创建完成
- [ ] Task 3.4: `textual_app/log_handler.py` 创建完成
- [ ] Task 3.5: `textual_app/notifications.py` 创建完成
- [ ] Task 3.6: `textual_app/text_area.py` 创建完成
- [ ] Task 3.7: `textual_app/helpers.py` 创建完成

### Task 4: 创建 textual_app/app.py

- [ ] Task 4.1: `textual_app/app.py` 框架创建完成
- [ ] Task 4.2: 主应用逻辑迁移完成
- [ ] Task 4.3: CSS 引用更新完成
- [ ] Task 4.4: 内部类迁移完成
- [ ] Task 4.5: `__init__.py` 导出完成

## 阶段三：core/ 子包

### Task 5: 创建 core/ 目录结构

- [ ] Task 5.1: `cli/tui/core/` 目录创建完成
- [ ] Task 5.2: `core/__init__.py` 创建完成
- [ ] Task 5.3: `core/keybindings.py` 迁移完成
- [ ] Task 5.4: `core/markdown_renderer.py` 迁移完成
- [ ] Task 5.5: `core/curses_ui.py` 迁移完成

## 阶段四：更新导入

### Task 6: 更新 cli/tui/__init__.py

- [ ] Task 6.1: 导出路径更新完成
- [ ] Task 6.2: 向后兼容重导出完成

### Task 7: 更新内部导入

- [ ] Task 7.1: widgets/ 导入更新完成
- [ ] Task 7.2: views/ 导入更新完成
- [ ] Task 7.3: services/ 导入更新完成
- [ ] Task 7.4: 循环导入检查通过

### Task 8: 填充 styles/ CSS 模块

- [ ] Task 8.1: `styles/base.css` 实现完成
- [ ] Task 8.2: `styles/layout.css` 实现完成
- [ ] Task 8.3: `styles/components.css` 实现完成
- [ ] Task 8.4: `styles/animations.css` 实现完成
- [ ] Task 8.5: `styles/__init__.py` 更新完成

### Task 9: 删除旧文件

- [ ] Task 9.1: 功能迁移验证完成
- [ ] Task 9.2: `textual_app.py` 删除完成
- [ ] Task 9.3: `themes.py` 删除完成
- [ ] Task 9.4: 根目录旧文件删除完成

## 阶段五：验证和测试

### Task 10: 功能验证

- [ ] Task 10.1: TUI 启动测试通过
- [ ] Task 10.2: 所有 TUI 功能正常
- [ ] Task 10.3: 导入路径兼容性验证通过
- [ ] Task 10.4: 无循环导入

### Task 11: 代码质量检查

- [ ] Task 11.1: 文件行数符合目标（≤800行）
- [ ] Task 11.2: Linter 检查通过
- [ ] Task 11.3: Type checker 检查通过

## 最终验证

### 架构验证

- [ ] `textual_app/` 子包结构正确
- [ ] `themes/` 子包结构正确
- [ ] `core/` 子包结构正确
- [ ] 所有文件行数 ≤ 800 行

### 兼容性验证

- [ ] 旧导入路径继续工作
- [ ] `from cli.tui.themes import Theme` 工作正常
- [ ] `from cli.tui.textual_app import HandsomeAgentApp` 工作正常
- [ ] `from cli.tui.core import keybindings` 工作正常

### 功能验证

- [ ] TUI 应用正常启动
- [ ] 主题切换功能正常
- [ ] 消息显示功能正常
- [ ] 侧边栏功能正常
- [ ] CSS 模块加载正常
