# Checklist - TUI 文件面板功能增强

## 阶段一：基础组件重构

### Task 1: DirectoryTree 组件重构

- [ ] Task 1.1: 读取现有 `sidebar.py` 文件完成
- [ ] Task 1.2: `DirectoryTree` 组件导入成功
- [ ] Task 1.3: `compose()` 方法已修改使用 `DirectoryTree`
- [ ] Task 1.4: `IGNORED_DIRS` 集合定义完成
- [ ] Task 1.5: `_filter_path()` 方法实现并正确过滤
- [ ] Task 1.6: DirectoryTree 基本功能测试通过（展开/折叠）

### Task 2: 搜索功能

- [ ] Task 2.1: 搜索框组件添加到 `compose()`
- [ ] Task 2.2: 搜索框样式定义完成
- [ ] Task 2.3: `_on_input_changed()` 方法实现
- [ ] Task 2.4: `_filter_tree()` 方法实现
- [ ] Task 2.5: `_show_all_nodes()` 方法实现
- [ ] Task 2.6: `_hide_non_matching()` 方法实现
- [ ] Task 2.7: 搜索功能测试通过

### Task 3: 键盘快捷键

- [ ] Task 3.1: `BINDINGS` 列表定义完成
- [ ] Task 3.2: `action_open_item()` 方法实现
- [ ] Task 3.3: `action_refresh()` 方法实现
- [ ] Task 3.4: `action_activate_search()` 方法实现
- [ ] Task 3.5: `action_clear_search()` 方法实现
- [ ] Task 3.6: `action_go_up()` 方法实现
- [ ] Task 3.7: `action_toggle_favorite()` 方法实现
- [ ] Task 3.8: 所有键盘快捷键测试通过

## 阶段二：收藏功能

### Task 4: 收藏栏组件

- [ ] Task 4.1: `FavoritesBar` 类创建完成
- [ ] Task 4.2: `__init__()` 方法实现
- [ ] Task 4.3: `render()` 方法实现
- [ ] Task 4.4: 📌 收藏图标前缀添加
- [ ] Task 4.5: 收藏列表显示格式正确

### Task 5: 收藏持久化

- [ ] Task 5.1: `storage` 属性添加到主应用
- [ ] Task 5.2: `load_favorites()` 函数实现
- [ ] Task 5.3: `save_favorites()` 函数实现
- [ ] Task 5.4: `FileTreePane` 正确访问收藏数据
- [ ] Task 5.5: 收藏持久化测试通过

### Task 6: 收藏交互

- [ ] Task 6.1: 收藏栏组件添加到 `compose()`
- [ ] Task 6.2: 收藏项点击事件处理实现
- [ ] Task 6.3: 悬停效果样式添加
- [ ] Task 6.4: 点击跳转功能测试通过

## 阶段三：增强显示

### Task 7: 当前路径显示

- [ ] Task 7.1: `CurrentPathBar` 类创建完成
- [ ] Task 7.2: 路径格式化正确（`~` 缩写）
- [ ] Task 7.3: 路径组件添加到 `compose()`
- [ ] Task 7.4: 路径变化自动更新
- [ ] Task 7.5: 路径显示正确性测试通过

### Task 8: 文件信息栏

- [ ] Task 8.1: `FileInfoBar` 类创建完成
- [ ] Task 8.2: `_format_size()` 方法实现正确
- [ ] Task 8.3: `_get_file_type()` 方法实现正确
- [ ] Task 8.4: `update_info()` 方法实现
- [ ] Task 8.5: 选中事件中正确调用 `update_info()`
- [ ] Task 8.6: 文件信息显示测试通过（大小、时间、类型）

### Task 9: 文件图标系统

- [ ] Task 9.1: 读取 `icons.py` 完成
- [ ] Task 9.2: 📂 展开状态目录图标添加
- [ ] Task 9.3: 文件类型图标映射表扩展
- [ ] Task 9.4: 目录图标动态变化逻辑实现
- [ ] Task 9.5: 图标显示正确性测试通过

## 阶段四：样式优化

### Task 10: 文件面板 CSS

- [ ] Task 10.1: 文件面板容器样式定义
- [ ] Task 10.2: 搜索框样式定义
- [ ] Task 10.3: 路径栏样式定义
- [ ] Task 10.4: 收藏栏样式定义
- [ ] Task 10.5: 文件信息栏样式定义
- [ ] Task 10.6: DirectoryTree 样式定义
- [ ] Task 10.7: 滚动条样式定义
- [ ] Task 10.8: 整体视觉效果测试通过

### Task 11: 焦点和选中状态

- [ ] Task 11.1: DirectoryTree 焦点样式定义
- [ ] Task 11.2: 选中节点样式定义
- [ ] Task 11.3: 悬停效果样式定义
- [ ] Task 11.4: 焦点状态切换测试通过

## 阶段五：集成和测试

### Task 12: 集成到主应用

- [ ] Task 12.1: `textual_app.py` 面板切换逻辑更新
- [ ] Task 12.2: 快捷键不与其他面板冲突
- [ ] Task 12.3: 收藏存储正确初始化
- [ ] Task 12.4: 面板切换后状态正确

### Task 13: 完整功能测试

- [ ] Task 13.1: 目录展开/折叠功能测试通过
- [ ] Task 13.2: 键盘快捷键测试通过
- [ ] Task 13.3: 搜索过滤功能测试通过
- [ ] Task 13.4: 收藏添加/移除测试通过
- [ ] Task 13.5: 收藏持久化测试通过
- [ ] Task 13.6: 文件信息显示测试通过
- [ ] Task 13.7: 文件图标显示测试通过
- [ ] Task 13.8: 隐藏文件过滤测试通过

### Task 14: 性能优化

- [ ] Task 14.1: 大目录加载性能可接受
- [ ] Task 14.2: 搜索响应速度可接受
- [ ] Task 14.3: 渲染性能优化完成
- [ ] Task 14.4: 加载指示器添加

## 最终验证

### 功能验证

- [ ] TUI 应用可以正常启动
- [ ] 文件面板可以正常显示
- [ ] 目录树可以展开/折叠
- [ ] 键盘快捷键全部正常工作
- [ ] 搜索功能可以实时过滤
- [ ] 收藏功能可以添加/移除/持久化
- [ ] 文件信息正确显示
- [ ] 图标系统正常工作

### 视觉对比

- [ ] 目录层级展示清晰
- [ ] 文件图标正确显示
- [ ] 焦点状态指示明确
- [ ] 搜索框样式美观
- [ ] 收藏栏样式一致

### 代码质量

- [ ] 代码风格保持一致
- [ ] 没有引入新的错误
- [ ] 注释和文档更新
- [ ] 与 Frogmouth 风格对比通过

### 与 Frogmouth 对比

- [ ] 目录树功能与 Frogmouth 一致
- [ ] 搜索功能与 Frogmouth 类似
- [ ] 键盘导航与 Frogmouth 类似
- [ ] 整体用户体验接近 Frogmouth
