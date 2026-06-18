# Tasks - TUI 架构重构

## 阶段一：创建 themes/ 子包

### Task 1: 创建 themes/ 目录结构

- [ ] Task 1.1: 创建 `cli/tui/themes/` 目录
- [ ] Task 1.2: 创建 `themes/__init__.py` 并规划导出
- [ ] Task 1.3: 创建 `themes/theme_config.py` - Theme 和 ThemeConfig 数据类
- [ ] Task 1.4: 创建 `themes/preset_themes.py` - 预设主题定义（从 themes.py 迁移）
- [ ] Task 1.5: 创建 `themes/icons.py` - 图标映射常量
- [ ] Task 1.6: 创建 `themes/colors.py` - 颜色常量和 transparent() 函数
- [ ] Task 1.7: 创建 `themes/theme_manager.py` - ThemeManager 类

### Task 2: 迁移 themes.py 到子包

- [ ] Task 2.1: 从 themes.py 提取 Theme 和 ThemeConfig 数据类到 theme_config.py
- [ ] Task 2.2: 从 themes.py 提取预设主题到 preset_themes.py
- [ ] Task 2.3: 从 themes.py 提取图标映射到 icons.py
- [ ] Task 2.4: 从 themes.py 提取透明颜色函数到 colors.py
- [ ] Task 2.5: 从 themes.py 提取 ThemeManager 到 theme_manager.py
- [ ] Task 2.6: 更新 themes/__init__.py 导出所有公共 API
- [ ] Task 2.7: 添加向后兼容重导出（旧路径迁移）

## 阶段二：创建 textual_app/ 子包

### Task 3: 创建 textual_app/ 目录结构

- [ ] Task 3.1: 创建 `cli/tui/textual_app/` 目录
- [ ] Task 3.2: 创建 `textual_app/__init__.py` 并规划导出
- [ ] Task 3.3: 创建 `textual_app/css.py` - CSS 内容提取
- [ ] Task 3.4: 创建 `textual_app/log_handler.py` - TuiLogHandler 类
- [ ] Task 3.5: 创建 `textual_app/notifications.py` - 通知管理类
- [ ] Task 3.6: 创建 `textual_app/text_area.py` - 文本区域组件
- [ ] Task 3.7: 创建 `textual_app/helpers.py` - 辅助函数

### Task 4: 创建 textual_app/app.py

- [ ] Task 4.1: 创建 `textual_app/app.py` 主应用类框架
- [ ] Task 4.2: 迁移主应用逻辑（绑定、消息处理）
- [ ] Task 4.3: 移除内联 CSS，引用 css.py
- [ ] Task 4.4: 迁移内部类（CompatibleLog、LogDescriptor 等）
- [ ] Task 4.5: 更新 __init__.py 导出主类

## 阶段三：创建 core/ 子包

### Task 5: 创建 core/ 目录结构

- [ ] Task 5.1: 创建 `cli/tui/core/` 目录
- [ ] Task 5.2: 创建 `core/__init__.py`
- [ ] Task 5.3: 迁移 `keybindings.py` 到 `core/keybindings.py`
- [ ] Task 5.4: 迁移 `markdown_renderer.py` 到 `core/markdown_renderer.py`
- [ ] Task 5.5: 迁移 `curses_ui.py` 到 `core/curses_ui.py`

## 阶段四：更新导入和验证

### Task 6: 更新 cli/tui/__init__.py

- [ ] Task 6.1: 更新导出路径指向新子包
- [ ] Task 6.2: 添加向后兼容重导出

### Task 7: 更新所有内部导入

- [ ] Task 7.1: 更新 widgets/ 中的导入
- [ ] Task 7.2: 更新 views/ 中的导入
- [ ] Task 7.3: 更新 services/ 中的导入
- [ ] Task 7.4: 检查循环导入问题

### Task 8: 填充 styles/ CSS 模块

- [ ] Task 8.1: 实现 styles/base.css（从 css.py 提取变量）
- [ ] Task 8.2: 实现 styles/layout.css
- [ ] Task 8.3: 实现 styles/components.css
- [ ] Task 8.4: 实现 styles/animations.css
- [ ] Task 8.5: 更新 styles/__init__.py

### Task 9: 删除旧文件

- [ ] Task 9.1: 确认所有功能已迁移
- [ ] Task 9.2: 删除旧的 textual_app.py
- [ ] Task 9.3: 删除旧的 themes.py
- [ ] Task 9.4: 删除根目录的 keybindings.py、markdown_renderer.py、curses_ui.py

## 阶段五：验证和测试

### Task 10: 功能验证

- [ ] Task 10.1: 运行 `python -m cli.main --textual` 验证启动
- [ ] Task 10.2: 测试所有 TUI 功能正常工作
- [ ] Task 10.3: 检查导入路径兼容性
- [ ] Task 10.4: 验证没有循环导入

### Task 11: 代码质量检查

- [ ] Task 11.1: 检查所有文件行数符合目标
- [ ] Task 11.2: 运行 linter 检查
- [ ] Task 11.3: 运行 type checker 检查

## Task Dependencies

```
Task 1 (创建themes目录) ──→ Task 2 (迁移themes.py)
                                    │
                                    ▼
Task 3 (创建textual_app目录) ──→ Task 4 (创建app.py)
        │                                   │
        │                                   │
        ▼                                   ▼
Task 5 (创建core目录)              Task 6-7 (更新导入)
        │                                   │
        │                                   ▼
        └──────────────┬──→ Task 8 (填充CSS)
                       │
                       ▼
              Task 9 (删除旧文件)
                       │
                       ▼
              Task 10-11 (验证测试)
```

### 并行执行建议

- **第一波并行**: Task 1, 3, 5 可以并行创建目录结构
- **第二波并行**: Task 2, 4, 5.3-5.5 可以并行迁移代码
- **第三波并行**: Task 6, 7 可以并行更新导入
- **第四波**: Task 8 单独执行
- **第五波**: Task 9 单独执行
- **第六波**: Task 10-11 单独执行

## 验证方式

- [ ] 运行 `python -m cli.main --textual` 启动 TUI
- [ ] 测试主题切换功能
- [ ] 测试消息显示功能
- [ ] 测试侧边栏功能
- [ ] 检查 Python 导入无错误
- [ ] 检查文件行数符合目标
