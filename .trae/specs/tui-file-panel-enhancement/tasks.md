# Tasks - TUI 文件面板功能增强

## 阶段一：基础组件重构

### Task 1: 重构 FileTreePane 为 DirectoryTree 组件

- [ ] Task 1.1: 读取现有 `sidebar.py` 文件，了解当前 `FileTreePane` 实现
- [ ] Task 1.2: 在 `FileTreePane` 中导入 `DirectoryTree` 组件
- [ ] Task 1.3: 修改 `compose()` 方法，用 `DirectoryTree` 替代 `Static` 组件
- [ ] Task 1.4: 定义 `IGNORED_DIRS` 集合，包含要过滤的目录名
- [ ] Task 1.5: 实现 `_filter_path()` 方法过滤隐藏文件和忽略目录
- [ ] Task 1.6: 测试 DirectoryTree 基本功能（展开/折叠）

### Task 2: 添加搜索功能

- [ ] Task 2.1: 在 `compose()` 中添加 `Input` 搜索框组件
- [ ] Task 2.2: 定义搜索框的占位符文本和样式
- [ ] Task 2.3: 实现 `_on_input_changed()` 方法处理搜索输入
- [ ] Task 2.4: 实现 `_filter_tree()` 方法过滤匹配的节点
- [ ] Task 2.5: 实现 `_show_all_nodes()` 方法恢复显示所有节点
- [ ] Task 2.6: 实现 `_hide_non_matching()` 方法递归隐藏不匹配节点
- [ ] Task 2.7: 测试搜索功能（输入、空搜索、无匹配结果）

### Task 3: 添加键盘快捷键绑定

- [ ] Task 3.1: 在 `FileTreePane` 中添加 `BINDINGS` 列表
  - `enter` - 打开项
  - `r` - 刷新
  - `/` - 激活搜索
  - `escape` - 清除搜索
  - `backspace` - 返回上级
  - `ctrl+d` - 切换收藏

- [ ] Task 3.2: 实现 `action_open_item()` 方法打开文件/进入目录
- [ ] Task 3.3: 实现 `action_refresh()` 方法刷新目录
- [ ] Task 3.4: 实现 `action_activate_search()` 方法聚焦搜索框
- [ ] Task 3.5: 实现 `action_clear_search()` 方法清除搜索
- [ ] Task 3.6: 实现 `action_go_up()` 方法返回上级目录
- [ ] Task 3.7: 实现 `action_toggle_favorite()` 方法添加/移除收藏
- [ ] Task 3.8: 测试所有键盘快捷键

## 阶段二：收藏功能

### Task 4: 创建收藏栏组件

- [ ] Task 4.1: 创建 `FavoritesBar` 类继承 `Static`
- [ ] Task 4.2: 实现 `__init__()` 方法接收收藏列表
- [ ] Task 4.3: 实现 `render()` 方法渲染收藏列表
- [ ] Task 4.4: 添加 📌 收藏图标前缀
- [ ] Task 4.5: 美化收藏项的显示格式（使用分隔线）

### Task 5: 实现收藏持久化

- [ ] Task 5.1: 在 `textual_app.py` 中添加 `storage` 属性（使用 JSON 文件）
- [ ] Task 5.2: 创建 `load_favorites()` 函数从配置文件读取收藏
- [ ] Task 5.3: 创建 `save_favorites()` 函数保存收藏到配置文件
- [ ] Task 5.4: 在 `FileTreePane` 中访问 `self.app.storage` 获取收藏
- [ ] Task 5.5: 修改 `action_toggle_favorite()` 使用持久化存储
- [ ] Task 5.6: 测试收藏添加、移除、重启后保留

### Task 6: 收藏交互功能

- [ ] Task 6.1: 在 `compose()` 中添加收藏栏组件
- [ ] Task 6.2: 实现收藏项点击事件处理（跳转到目录）
- [ ] Task 6.3: 添加收藏项的悬停效果样式
- [ ] Task 6.4: 测试点击收藏项跳转功能

## 阶段三：增强显示

### Task 7: 添加当前路径显示

- [ ] Task 7.1: 创建 `CurrentPathBar` 类继承 `Static`
- [ ] Task 7.2: 实现路径格式化（使用 `~` 缩写主目录）
- [ ] Task 7.3: 在 `compose()` 中添加路径显示组件
- [ ] Task 7.4: 实现路径变化时的自动更新
- [ ] Task 7.5: 测试路径显示正确性

### Task 8: 添加文件信息栏

- [ ] Task 8.1: 创建 `FileInfoBar` 类继承 `Static`
- [ ] Task 8.2: 实现 `_format_size()` 方法格式化文件大小
- [ ] Task 8.3: 实现 `_get_file_type()` 方法获取文件类型
- [ ] Task 8.4: 实现 `update_info()` 方法更新显示信息
- [ ] Task 8.5: 在 DirectoryTree 的选中事件中调用 `update_info()`
- [ ] Task 8.6: 测试文件信息显示（大小、时间、类型）

### Task 9: 增强文件图标系统

- [ ] Task 9.1: 读取现有的 `icons.py` 文件
- [ ] Task 9.2: 添加展开状态目录图标 📂
- [ ] Task 9.3: 扩展文件类型图标映射表
- [ ] Task 9.4: 实现目录图标根据展开状态动态变化
- [ ] Task 9.5: 测试图标显示正确性

## 阶段四：样式优化

### Task 10: 文件面板 CSS 样式

- [ ] Task 10.1: 定义文件面板容器样式（padding, background）
- [ ] Task 10.2: 定义搜索框样式（宽度、边框、焦点样式）
- [ ] Task 10.3: 定义路径栏样式（字体、对齐）
- [ ] Task 10.4: 定义收藏栏样式（图标、悬停效果）
- [ ] Task 10.5: 定义文件信息栏样式（颜色、大小）
- [ ] Task 10.6: 定义 DirectoryTree 样式（缩进、图标大小）
- [ ] Task 10.7: 添加滚动条样式
- [ ] Task 10.8: 测试整体视觉效果

### Task 11: 焦点和选中状态样式

- [ ] Task 11.1: 定义 DirectoryTree 焦点样式（`border-left: heavy $accent`）
- [ ] Task 11.2: 定义选中节点样式（背景色、字体加粗）
- [ ] Task 11.3: 定义悬停效果样式
- [ ] Task 11.4: 测试焦点状态切换

## 阶段五：集成和测试

### Task 12: 集成到主应用

- [ ] Task 12.1: 更新 `textual_app.py` 中的面板切换逻辑
- [ ] Task 12.2: 确保快捷键不与其他面板冲突
- [ ] Task 12.3: 确保收藏存储正确初始化
- [ ] Task 12.4: 测试面板切换后文件面板状态正确

### Task 13: 完整功能测试

- [ ] Task 13.1: 测试目录展开/折叠
- [ ] Task 13.2: 测试键盘快捷键（enter, r, /, escape, backspace, ctrl+d）
- [ ] Task 13.3: 测试搜索过滤功能
- [ ] Task 13.4: 测试收藏添加/移除
- [ ] Task 13.5: 测试收藏持久化
- [ ] Task 13.6: 测试文件信息显示
- [ ] Task 13.7: 测试文件图标显示
- [ ] Task 13.8: 测试隐藏文件过滤

### Task 14: 性能优化

- [ ] Task 14.1: 大目录加载性能测试
- [ ] Task 14.2: 搜索响应速度测试
- [ ] Task 14.3: 优化大量文件时的渲染性能
- [ ] Task 14.4: 添加加载指示器

## Task Dependencies

### 依赖关系图

```
Task 1 (DirectoryTree组件) ──┬── Task 2 (搜索功能) ───┬── Task 10 (CSS样式)
        │                    │                       │
        │                    │                       ▼
        │                    │              Task 11 (焦点样式)
        │                    │
        ▼                    ▼
Task 3 (键盘快捷键) ──── Task 13 (完整测试)
        │
        ▼
Task 4 (收藏栏组件) ──── Task 5 (收藏持久化) ──── Task 6 (收藏交互)
        │
        ▼
Task 7 (路径显示) ──── Task 8 (文件信息栏)
        │
        ▼
Task 9 (图标系统)
        │
        ▼
Task 12 (集成测试)
        │
        ▼
Task 14 (性能优化)
```

### 并行执行建议

- **第一波并行**: Task 1, 4, 7, 9 可以并行开发（基础组件）
- **第二波并行**: Task 2, 3 在 Task 1 完成后并行（搜索和快捷键）
- **第三波并行**: Task 5, 6 在 Task 4 完成后并行（收藏功能）
- **第四波并行**: Task 8, 10, 11 在 Task 1 完成后并行（增强和样式）
- **第五波**: Task 12, 13, 14 在其他任务完成后执行

## 验证方式

- [ ] 运行 `python -m cli.main --textual` 启动 TUI
- [ ] 按 Ctrl+2 切换到文件面板
- [ ] 测试目录展开/折叠功能
- [ ] 测试键盘快捷键（enter, r, /, escape, backspace, ctrl+d）
- [ ] 测试文件搜索过滤
- [ ] 测试收藏添加/移除
- [ ] 测试收藏持久化（重启应用后检查）
- [ ] 测试文件信息显示
- [ ] 测试文件图标显示
- [ ] 检查隐藏文件是否被过滤
- [ ] 检查忽略目录是否被过滤
- [ ] 对比 Frogmouth 的文件列表功能
