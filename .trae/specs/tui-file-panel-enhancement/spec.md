# TUI 文件面板功能增强规范

## Why

当前 Handsome-Agent 的 TUI 文件面板功能相对基础，与 Frogmouth 的优雅实现存在差距。主要不足包括：只显示根目录文件（无嵌套）、隐藏文件未过滤、固定显示数量限制、无交互功能（无法展开目录/打开文件）、缺少搜索过滤、无键盘快捷键支持，以及无文件收藏功能。通过学习 Frogmouth 的设计，可以显著提升文件面板的实用性和用户体验。

## What Changes

### 核心功能增强

1. **递归目录树** - 使用 Textual DirectoryTree 组件替代静态列表，支持无限层级展开
2. **智能文件过滤** - 自动过滤隐藏文件（`.`开头）、常见忽略目录（node_modules, __pycache__ 等）
3. **动态显示数量** - 根据视口大小动态调整显示数量，不再硬编码 15 个限制
4. **键盘快捷键** - 添加 Enter（打开）、r（刷新）、/（搜索）等快捷键
5. **文件搜索过滤** - 添加实时文件名搜索功能
6. **目录收藏** - 添加收藏夹功能，常用目录一键直达
7. **交互式目录导航** - 点击目录展开/折叠，Enter 键打开文件
8. **当前目录高亮** - 侧边栏显示当前工作目录路径

### 设计目标

学习 Frogmouth 的交互设计理念，实现：
- 清晰的目录层级展示
- 流畅的键盘/鼠标交互
- 快速的文件定位能力
- 便捷的目录收藏功能
- 专业的视觉反馈

## Impact

- Affected specs: TUI 用户交互、文件浏览体验
- Affected code: `cli/tui/sidebar.py`, `cli/tui/textual_app.py`, `cli/tui/widgets/`, `cli/config/`

## ADDED Requirements

### Requirement: 递归目录树显示

系统 SHALL 使用 Textual DirectoryTree 组件实现可展开的目录树。

#### Scenario: 目录树初始加载
- **WHEN** 文件面板首次显示时
- **THEN** 加载当前工作目录的完整目录结构
- **AND** 显示根目录及其直接子项（折叠状态）
- **AND** 目录显示 📁 图标

#### Scenario: 目录展开
- **WHEN** 用户点击目录项或按右方向键时
- **THEN** 展开目录显示子项
- **AND** 目录图标从 📁 变为 📂

#### Scenario: 目录折叠
- **WHEN** 用户再次点击展开的目录时
- **THEN** 折叠目录隐藏子项
- **AND** 目录图标恢复为 📁

#### Scenario: 文件显示
- **WHEN** 目录展开显示文件时
- **THEN** 根据文件类型显示对应图标
- **AND** 代码文件显示绿色
- **AND** 文档文件显示黄色

### Requirement: 智能文件过滤

系统 SHALL 自动过滤不需要显示的文件和目录。

#### Scenario: 隐藏文件过滤
- **WHEN** 加载目录内容时
- **THEN** 隐藏以 `.` 开头的文件和目录
- **AND** 包括 `.git`, `.vscode`, `.idea` 等

#### Scenario: 忽略目录过滤
- **WHEN** 加载目录内容时
- **THEN** 自动排除以下目录：
  - `node_modules`
  - `__pycache__`
  - `.pytest_cache`
  - `.venv`
  - `venv`
  - `env`
  - `dist`
  - `build`
  - `.tox`
  - `.mypy_cache`
  - `.ruff_cache`

#### Scenario: 非 Markdown 文件可选过滤
- **WHEN** 用户启用 MarkdownOnly 模式时
- **THEN** 只显示 `.md`, `.markdown`, `.txt` 文件和目录

### Requirement: 键盘快捷键支持

系统 SHALL 为文件面板添加完整的键盘快捷键支持。

#### Scenario: Enter 键打开文件
- **WHEN** 用户选中文件并按 Enter 时
- **THEN** 使用系统默认程序打开文件

#### Scenario: Enter 键进入目录
- **WHEN** 用户选中目录并按 Enter 时
- **THEN** 展开并进入该目录

#### Scenario: Backspace 返回上级
- **WHEN** 用户按 Backspace 时
- **THEN** 返回上级目录或折叠当前目录

#### Scenario: r 键刷新
- **WHEN** 用户按 r 键时
- **THEN** 重新加载当前目录内容

#### Scenario: / 键激活搜索
- **WHEN** 用户按 / 键时
- **THEN** 聚焦到搜索输入框

#### Scenario: Escape 退出搜索
- **WHEN** 用户在搜索时按 Escape 时
- **THEN** 清除搜索内容并返回目录树

### Requirement: 文件搜索过滤

系统 SHALL 支持实时文件名搜索过滤。

#### Scenario: 搜索输入
- **WHEN** 用户在搜索框输入时
- **THEN** 实时过滤显示匹配的文件和目录
- **AND** 高亮匹配文字

#### Scenario: 空搜索显示全部
- **WHEN** 用户清除搜索内容时
- **THEN** 恢复显示完整目录树

#### Scenario: 无匹配结果
- **WHEN** 搜索没有匹配项时
- **THEN** 显示 "未找到匹配项" 提示

### Requirement: 目录收藏功能

系统 SHALL 支持收藏常用目录便于快速访问。

#### Scenario: 收藏当前目录
- **WHEN** 用户按 `Ctrl+d` 时
- **THEN** 将当前目录添加到收藏夹
- **AND** 显示收藏成功提示

#### Scenario: 收藏列表显示
- **WHEN** 文件面板激活时
- **THEN** 在面板顶部显示收藏目录列表
- **AND** 显示 📌 图标

#### Scenario: 跳转到收藏目录
- **WHEN** 用户点击收藏项时
- **THEN** 立即跳转到该目录

#### Scenario: 移除收藏
- **WHEN** 用户按 Delete 键在收藏项上时
- **THEN** 从收藏列表中移除该目录

#### Scenario: 收藏持久化
- **WHEN** 用户添加或移除收藏时
- **THEN** 自动保存到配置文件
- **AND** 重启后保留收藏

### Requirement: 当前目录显示

系统 SHALL 在文件面板中显示当前工作目录路径。

#### Scenario: 目录路径显示
- **WHEN** 文件面板激活时
- **THEN** 在面板顶部显示当前完整路径
- **AND** 使用 `~` 缩写用户主目录

#### Scenario: 路径点击跳转
- **WHEN** 用户点击路径中的某个目录名时
- **THEN** 跳转到该目录

### Requirement: 文件信息提示

系统 SHALL 在悬停或选中文件时显示详细信息。

#### Scenario: 文件大小显示
- **WHEN** 用户选中文件时
- **THEN** 显示文件大小（KB/MB/GB 格式）

#### Scenario: 修改时间显示
- **WHEN** 用户选中文件时
- **AND** 显示最后修改时间

#### Scenario: 文件类型显示
- **WHEN** 用户选中文件时
- **AND** 显示文件扩展名和类型描述

## MODIFIED Requirements

### Requirement: 文件图标系统增强

原有的 Emoji 图标系统应增强以下功能：

#### Scenario: 目录图标动态变化
- **WHEN** 目录处于折叠状态时
- **THEN** 显示 📁 图标

- **WHEN** 目录处于展开状态时
- **THEN** 显示 📂 图标

#### Scenario: 文件类型图标扩展
- **WHEN** 显示文件图标时
- **THEN** 支持以下扩展类型：
  - `.py` → 🐍 Python
  - `.rs` → 🦀 Rust
  - `.js` → 📜 JavaScript
  - `.ts` → 📘 TypeScript
  - `.tsx` → ⚛️ React
  - `.jsx` → ⚛️ React
  - `.vue` → 💚 Vue
  - `.go` → 🐹 Go
  - `.java` → ☕ Java
  - `.c` → 🔧 C
  - `.cpp` → 🔧 C++
  - `.cs` → 💜 C#
  - `.rb` → 💎 Ruby
  - `.md` → 📝 Markdown
  - `.txt` → 📄 文本
  - `.json` → 📋 JSON
  - `.yaml` / `.yml` → 📄 YAML
  - `.xml` → 📄 XML
  - `.html` → 🌐 HTML
  - `.css` → 🎨 CSS
  - `.scss` → 🎨 SCSS
  - `.png` → 🖼️ PNG
  - `.jpg` / `.jpeg` → 🖼️ JPG
  - `.gif` → 🖼️ GIF
  - `.svg` → 📐 SVG
  - `.pdf` → 📕 PDF
  - `.zip` → 📦 ZIP
  - `.tar` → 📦 TAR
  - `.gz` → 📦 GZ
  - `.exe` → ⚙️ EXE
  - `.dll` → ⚙️ DLL
  - `.dockerfile` → 🐳 Docker
  - `.gitignore` → 📁 Git
  - `.env` → 🔐 ENV
  - 默认 → 📄 通用

### Requirement: 文件排序优化

#### Scenario: 目录优先排序
- **WHEN** 显示目录项时
- **THEN** 所有目录显示在文件之前

#### Scenario: 字母排序
- **WHEN** 同类型项排序时
- **THEN** 按字母升序排列（不区分大小写）

#### Scenario: 隐藏项排序
- **WHEN** 隐藏文件显示时（如果启用）
- **THEN** 隐藏项在同类中排在最后

## Technical Implementation

### 1. DirectoryTree 组件实现

```python
# cli/tui/sidebar.py
from textual.widgets import DirectoryTree, Tree
from textual.events import Click
from pathlib import Path

class FileTreePane(SidebarPane):
    """增强的文件树面板"""

    # 忽略的目录列表
    IGNORED_DIRS = {
        'node_modules', '__pycache__', '.pytest_cache',
        '.venv', 'venv', 'env', 'dist', 'build',
        '.tox', '.mypy_cache', '.ruff_cache', '.git'
    }

    def compose(self) -> ComposeResult:
        """组合子组件"""
        # 搜索栏
        yield Input(placeholder="搜索文件...", id="file-search")
        # 当前路径显示
        yield Static(self._get_display_path(), id="current-path")
        # 目录树
        yield DirectoryTree(str(Path.cwd()), id="file-tree")

    def _filter_path(self, path: Path) -> bool:
        """过滤不需要显示的路径"""
        if path.name.startswith('.'):
            return False
        if path.is_dir() and path.name in self.IGNORED_DIRS:
            return False
        return True
```

### 2. 键盘快捷键绑定

```python
class FileTreePane(SidebarPane):
    """增强的文件树面板"""

    BINDINGS = [
        Binding("enter", "open_item", "打开", key_display="↵"),
        Binding("r", "refresh", "刷新", key_display="r"),
        Binding("/", "activate_search", "搜索", key_display="/"),
        Binding("escape", "clear_search", "清除", key_display="esc"),
        Binding("backspace", "go_up", "上级", key_display="⌫"),
        Binding("ctrl+d", "toggle_favorite", "收藏", key_display="⌃D"),
    ]

    def action_open_item(self) -> None:
        """打开选中项"""
        tree = self.query_one("#file-tree", DirectoryTree)
        node = tree.cursor_node
        if node.data:
            path = Path(node.data.path)
            if path.is_dir():
                tree.reload(path)
            else:
                self._open_file(path)

    def action_refresh(self) -> None:
        """刷新目录"""
        tree = self.query_one("#file-tree", DirectoryTree)
        tree.reload()

    def action_activate_search(self) -> None:
        """激活搜索"""
        search_input = self.query_one("#file-search", Input)
        search_input.focus()

    def action_toggle_favorite(self) -> None:
        """添加/移除收藏"""
        tree = self.query_one("#file-tree", DirectoryTree)
        current_path = tree.path
        favorites = self.app.storage.get('favorites', [])
        if current_path in favorites:
            favorites.remove(current_path)
        else:
            favorites.append(current_path)
        self.app.storage.set('favorites', favorites)
```

### 3. 收藏功能实现

```python
# cli/tui/sidebar.py
class FavoritesBar(Static):
    """收藏栏组件"""

    def __init__(self, favorites: list[str]) -> None:
        super().__init__()
        self.favorites = favorites

    def render(self) -> str:
        """渲染收藏列表"""
        if not self.favorites:
            return ""
        lines = ["📌 收藏夹", "-" * 20]
        for fav in self.favorites:
            name = Path(fav).name
            lines.append(f"  {name}")
        return "\n".join(lines)
```

### 4. 搜索过滤实现

```python
# cli/tui/sidebar.py
class FileTreePane(SidebarPane):
    def _on_input_changed(self, event: Input.Changed) -> None:
        """搜索输入变化处理"""
        if event.input.id == "file-search":
            search_term = event.value.lower()
            self._filter_tree(search_term)

    def _filter_tree(self, search_term: str) -> None:
        """过滤目录树"""
        tree = self.query_one("#file-tree", DirectoryTree)
        if not search_term:
            # 显示所有节点
            self._show_all_nodes(tree.root)
        else:
            # 过滤匹配节点
            self._hide_non_matching(tree.root, search_term)

    def _hide_non_matching(self, node: Tree.Node, search_term: str) -> None:
        """隐藏不匹配的节点"""
        for child in node.children:
            path = Path(child.data.path)
            if path.is_dir() or search_term in path.name.lower():
                child.expand()
                self._hide_non_matching(child, search_term)
            else:
                child.remove()
```

### 5. 文件信息显示

```python
# cli/tui/sidebar.py
class FileInfoBar(Static):
    """文件信息栏"""

    def update_info(self, path: Path) -> None:
        """更新文件信息"""
        if path.is_file():
            size = self._format_size(path.stat().st_size)
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
            file_type = self._get_file_type(path.suffix)
            self.update(f"{size} | {mtime:%Y-%m-%d %H:%M} | {file_type}")
        else:
            self.update("")

    @staticmethod
    def _format_size(size: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    @staticmethod
    def _get_file_type(ext: str) -> str:
        """获取文件类型描述"""
        types = {
            '.py': 'Python', '.js': 'JavaScript', '.ts': 'TypeScript',
            '.md': 'Markdown', '.json': 'JSON', '.txt': '文本',
        }
        return types.get(ext.lower(), '文件')
```

## Migration from Current Implementation

### 当前问题

1. 使用 `Static` 组件只显示静态文本
2. 只显示根目录的 15 个项目
3. 无目录嵌套支持
4. 无键盘快捷键
5. 无搜索功能
6. 无收藏功能
7. 无交互功能（只能看不能操作）
8. 隐藏文件未过滤

### 迁移步骤

1. **创建增强的面板类**
   - 继承 `SidebarPane`
   - 添加 `DirectoryTree` 组件
   - 添加搜索输入框
   - 添加收藏栏
   - 添加文件信息栏

2. **实现键盘快捷键**
   - 添加 `BINDINGS` 定义
   - 实现各个动作方法

3. **实现搜索过滤**
   - 添加搜索输入事件处理
   - 实现树节点过滤逻辑

4. **实现收藏功能**
   - 创建收藏栏组件
   - 添加快捷键处理
   - 实现持久化存储

5. **增强文件图标**
   - 添加展开/折叠状态图标
   - 扩展文件类型映射

6. **添加文件信息**
   - 创建文件信息栏组件
   - 实现大小、时间、类型显示

7. **测试验证**
   - 测试目录展开/折叠
   - 测试键盘快捷键
   - 测试搜索功能
   - 测试收藏功能

## Success Criteria

- [ ] DirectoryTree 组件成功替换静态列表
- [ ] 目录可以展开/折叠
- [ ] 隐藏文件和忽略目录被正确过滤
- [ ] Enter 键可以打开文件或进入目录
- [ ] r 键可以刷新目录
- [ ] / 键可以激活搜索
- [ ] Escape 键可以清除搜索
- [ ] 搜索可以实时过滤文件和目录
- [ ] Ctrl+d 可以添加/移除收藏
- [ ] 收藏列表在面板顶部显示
- [ ] 收藏可以持久化保存
- [ ] 展开的目录显示 📂 图标
- [ ] 选中的文件显示详细信息（大小、时间、类型）
- [ ] 文件排序正确（目录优先，字母排序）
