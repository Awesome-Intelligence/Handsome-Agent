# Tasks - CLI/TUI 顶层目录分离

## 阶段一：创建 TUI 顶层目录结构

### Task 1: 创建顶层 tui/ 目录

- [ ] Task 1.1: 创建 `tui/` 根目录
- [ ] Task 1.2: 创建 `tui/__init__.py`
- [ ] Task 1.3: 创建 `tui/main.py` 入口文件

### Task 2: 创建 tui/pyproject.toml

- [ ] Task 2.1: 创建 `tui/pyproject.toml` 配置文件
- [ ] Task 2.2: 配置 Textual 依赖
- [ ] Task 2.3: 配置入口点 `handsome-tui`

## 阶段二：迁移 TUI 子目录

### Task 3: 迁移 core/ 目录

- [ ] Task 3.1: 创建 `tui/core/` 目录结构
- [ ] Task 3.2: 迁移 `cli/tui/core/__init__.py` → `tui/core/__init__.py`
- [ ] Task 3.3: 迁移 `cli/tui/core/curses_ui.py` → `tui/core/curses_ui.py`
- [ ] Task 3.4: 迁移 `cli/tui/core/keybindings.py` → `tui/core/keybindings.py`
- [ ] Task 3.5: 迁移 `cli/tui/core/markdown_renderer.py` → `tui/core/markdown_renderer.py`

### Task 4: 迁移 services/ 目录

- [ ] Task 4.1: 创建 `tui/services/` 目录结构
- [ ] Task 4.2: 迁移 `cli/tui/services/__init__.py` → `tui/services/__init__.py`
- [ ] Task 4.3: 迁移 `cli/tui/services/session_store.py` → `tui/services/session_store.py`

### Task 5: 迁移 views/ 目录

- [ ] Task 5.1: 创建 `tui/views/` 目录结构
- [ ] Task 5.2: 迁移所有 `cli/tui/views/*.py` → `tui/views/*.py`

### Task 6: 迁移 widgets/ 目录

- [ ] Task 6.1: 创建 `tui/widgets/` 目录结构
- [ ] Task 6.2: 迁移所有 `cli/tui/widgets/*.py` → `tui/widgets/*.py`

### Task 7: 迁移 textual_app/ 目录

- [ ] Task 7.1: 创建 `tui/textual_app/` 目录结构
- [ ] Task 7.2: 迁移所有 `cli/tui/textual_app/*.py` → `tui/textual_app/*.py`

### Task 8: 迁移 theming/ 目录

- [ ] Task 8.1: 创建 `tui/theming/` 目录结构
- [ ] Task 8.2: 迁移所有 `cli/tui/theming/` → `tui/theming/`

## 阶段三：更新导入路径

### Task 9: 更新 tui 内部导入

- [ ] Task 9.1: 更新 `tui/core/` 内部导入
- [ ] Task 9.2: 更新 `tui/textual_app/` 内部导入
- [ ] Task 9.3: 更新 `tui/theming/` 内部导入
- [ ] Task 9.4: 更新 `tui/views/` 内部导入
- [ ] Task 9.5: 更新 `tui/widgets/` 内部导入
- [ ] Task 9.6: 更新 `tui/services/` 内部导入

### Task 10: 更新 tui/__init__.py

- [ ] Task 10.1: 配置 `tui/__init__.py` 导出主类
- [ ] Task 10.2: 添加向后兼容的重导出（如需要）

## 阶段四：更新 CLI 调用方

### Task 11: 更新 cli/main.py

- [ ] Task 11.1: 更新 TUI 启动逻辑调用新路径 `tui.textual_app`
- [ ] Task 11.2: 验证 `--textual` 参数正常工作

### Task 12: 更新 proxy/ 目录导入

- [ ] Task 12.1: 检查 `proxy/` 中是否有 `cli.tui` 导入
- [ ] Task 12.2: 更新为 `tui` 导入路径

## 阶段五：创建兼容层（可选）

### Task 13: 保留旧导入路径兼容

- [ ] Task 13.1: 在 `cli/tui/` 创建兼容层 `__init__.py`
- [ ] Task 13.2: 从 `tui` 导入并重导出所有公共 API
- [ ] Task 13.3: 添加废弃警告（DeprecationWarning）

## 阶段六：验证和清理

### Task 14: 功能验证

- [ ] Task 14.1: 运行 `python -m tui.main` 验证 TUI 独立启动
- [ ] Task 14.2: 运行 `python -m cli.main --textual` 验证 CLI 调用
- [ ] Task 14.3: 验证所有 TUI 功能正常工作
- [ ] Task 14.4: 检查没有循环导入

### Task 15: 删除旧目录

- [ ] Task 15.1: 确认所有文件已迁移
- [ ] Task 15.2: 删除 `cli/tui/` 目录
- [ ] Task 15.3: 更新 git 跟踪状态

### Task 16: 代码质量检查

- [ ] Task 16.1: 运行 linter 检查
- [ ] Task 16.2: 运行 type checker 检查
- [ ] Task 16.3: 检查所有文件行数符合规范

## Task Dependencies

```
Phase 1: 创建目录
    Task 1 ──→ Task 2

Phase 2: 迁移文件 (可并行)
    Task 3 ─┬─→ Task 4 ─┬─→ Task 5 ─┬─→ Task 6 ─┬─→ Task 7 ─┬─→ Task 8
            │           │           │           │           │
            └───────────┴───────────┴───────────┴───────────┘
                                                               │
                                                               ▼
Phase 3: 更新导入                                    Task 9 ──→ Task 10
                                                               │
                                                               ▼
Phase 4: 更新调用方                          Task 11 ──→ Task 12
                                                               │
                                                               ▼
Phase 5: 兼容层 (可选)                                   Task 13
                                                               │
                                                               ▼
Phase 6: 验证清理                              Task 14 ──→ Task 15 ──→ Task 16
```

### 并行执行建议

- **第一波并行**: Task 1, 2 可以并行
- **第二波并行**: Task 3-8 可以完全并行（迁移不同目录）
- **第三波并行**: Task 9.1-9.5 可以并行（更新不同目录内部导入）
- **第四波**: Task 10 单独执行
- **第五波**: Task 11, 12 可以并行
- **第六波**: Task 13 可选
- **第七波**: Task 14-16 顺序执行

## 验证方式

- [ ] `python -m tui.main` 启动 TUI 界面
- [ ] `python -m cli.main --textual` 从 CLI 启动 TUI
- [ ] 测试主题切换功能
- [ ] 测试消息显示功能
- [ ] 测试侧边栏功能
- [ ] 检查 `from tui.textual_app import HandsomeAgentApp` 正常工作
- [ ] 检查 `from cli.tui.textual_app import HandsomeAgentApp` 兼容导入（如保留）
