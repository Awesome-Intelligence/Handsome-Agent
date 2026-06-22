# Handsome Agent - DirectoryTree 替换自造 Tree 实现计划

## [x] Task 1: 创建 FilteredDirectoryTree 子类
- **Priority**: P0
- **Depends On**: None
- **Description**: 
  - 创建 `FilteredDirectoryTree` 类，继承自 Textual `DirectoryTree`
  - 实现 `filter_paths` 方法，过滤隐藏文件（`.` 开头）和黑名单目录（`.venv`, `node_modules`, `__pycache__`, `.git`, `.idea`, `.vscode`）
  - 处理 `PermissionError` 异常
- **Acceptance Criteria Addressed**: AC-2
- **Test Requirements**:
  - `programmatic` TR-1.1: `FilteredDirectoryTree.filter_paths` 正确过滤黑名单目录名 ✓
  - `programmatic` TR-1.2: `filter_paths` 在遇到 `PermissionError` 时返回空列表而非崩溃 ✓
- **Notes**: 参考 Frogmouth 的 `FilteredDirectoryTree` 实现

## [x] Task 2: 重写 FileTreePane 使用 DirectoryTree
- **Priority**: P0
- **Depends On**: Task 1
- **Description**: 
  - 替换 `FileTreePane` 中的 `Tree` 组件为 `FilteredDirectoryTree`
  - 删除自造的 `FileTreeNode` 数据结构和 `_build_tree_node` 方法
  - 删除 `_add_children_to_tree`, `_find_tree_node`, `_get_node_label` 方法
  - 使用 `DirectoryTree` 的 `path` 属性设置初始目录
  - 保留 `FileSelected` Message 定义
- **Acceptance Criteria Addressed**: AC-1, AC-4
- **Test Requirements**:
  - `human-judgment` TR-2.1: 文件树启动时不再卡顿，立即显示根目录 ✓
  - `programmatic` TR-2.2: `FileTreePane.on_directory_tree_file_selected` 正确发布 `FileSelected` Message ✓
- **Notes**: `DirectoryTree` 内置懒加载，无需手动实现

## [x] Task 3: 保留文件图标颜色区分
- **Priority**: P1
- **Depends On**: Task 2
- **Description**: 
  - 使用 `DirectoryTree` 的自定义标签功能，为不同类型文件添加图标和颜色
  - 代码文件（`.py`, `.rs`, `.js` 等）使用绿色
  - 文档文件（`.md`, `.txt`, `.pdf` 等）使用黄色
  - 目录使用青色
  - 其他文件使用默认颜色
- **Acceptance Criteria Addressed**: AC-3
- **Test Requirements**:
  - `human-judgment` TR-3.1: 代码文件显示绿色图标和文本 ✓
  - `human-judgment` TR-3.2: 文档文件显示黄色图标和文本 ✓
- **Notes**: 使用 `DirectoryTree` 的 `file_label` 和 `directory_label` 回调

## [x] Task 4: 保留键盘导航绑定
- **Priority**: P1
- **Depends On**: Task 2
- **Description**: 
  - 删除自定义快捷键绑定（`DirectoryTree` 内置支持）
  - 保留 `set_focus_within` 方法确保焦点正确设置
- **Acceptance Criteria Addressed**: AC-5
- **Test Requirements**:
  - `human-judgment` TR-4.1: 上下键移动光标 ✓
  - `human-judgment` TR-4.2: Enter 键展开目录或打开文件 ✓
  - `human-judgment` TR-4.3: Backspace 返回上级目录 ✓
- **Notes**: `DirectoryTree` 内置这些键盘行为，只需确保焦点正确设置

## [x] Task 5: 更新 CSS 样式适配 DirectoryTree
- **Priority**: P2
- **Depends On**: Task 2
- **Description**: 
  - 更新 `FileTreePane` 的 `DEFAULT_CSS`，将选择器从 `Tree` 改为 `DirectoryTree`
  - 保持一致的光标高亮样式（`$accent 25%` 背景）
  - 保持展开指示器颜色（`$accent`）
- **Acceptance Criteria Addressed**: AC-3
- **Test Requirements**:
  - `human-judgment` TR-5.1: 文件树样式与之前一致（光标高亮、展开指示器） ✓
- **Notes**: 参考 Frogmouth 的 CSS 样式

## [x] Task 6: 清理无用代码和导入
- **Priority**: P2
- **Depends On**: Task 2
- **Description**: 
  - 删除 `NodeType` 枚举和 `FileTreeNode` 数据类（不再使用）
  - 清理不再需要的导入（`Tree`, `dataclass`, `Enum`, `Dict`, `List`, `Optional`）
  - 更新 `__all__` 导出列表，移除 `NodeType` 和 `FileTreeNode`，添加 `FilteredDirectoryTree`
- **Acceptance Criteria Addressed**: NFR-3
- **Test Requirements**:
  - `programmatic` TR-6.1: 代码行数从 790 行减少到 675 行，减少约 115 行 ✓
  - `programmatic` TR-6.2: 无未使用的导入 ✓
- **Notes**: 使用 `ruff check` 验证清理效果
