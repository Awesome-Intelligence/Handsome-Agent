# Handsome Agent - DirectoryTree 替换自造 Tree PRD

## Overview
- **Summary**: 将 TUI 侧边栏文件树面板从自造的 `Tree` 组件 + `FileTreeNode` 数据结构，替换为 Textual 内置的 `DirectoryTree` 组件，以获得懒加载、异步遍历、内置键盘导航等原生能力
- **Purpose**: 解决当前文件树同步预加载导致的启动卡顿、内存膨胀问题；减少约 200 行冗余代码；对齐 Frogmouth 的成熟实现方案
- **Target Users**: 使用 Handsome Agent TUI 的所有用户，尤其是在大型项目目录下工作的用户

## Goals
- 使用 Textual 内置 `DirectoryTree` 替换自造 `Tree` 组件
- 实现懒加载：只在展开节点时加载子目录，而非启动时递归遍历整棵树
- 保留现有文件图标颜色区分（代码文件/文档文件/其他）
- 保留文件选中事件和 `FileSelected` Message
- 保留基础键盘导航（上下选择、回车展开/打开、Backspace 返回）
- 添加目录黑名单过滤（`.venv`, `node_modules`, `__pycache__`, `.git`）

## Non-Goals (Out of Scope)
- 不改变侧边栏整体布局和其他面板（Tasks/Agent/Logs）
- 不添加新功能（如文件搜索、右键菜单、文件元信息）
- 不修改 `SidebarPane` 基类和 `SidebarContainer` 容器
- 不改变文件选中后的后续处理逻辑

## Background & Context
- 当前实现：[sidebar.py](file:///e:/Awesome%20Intelligence/Handsome-Agent/tui/sidebar.py#L312-L494) 的 `FileTreePane` 使用自造 `FileTreeNode` 数据结构，在 `__init__` 时同步递归遍历整个 cwd，导致启动卡顿
- Frogmouth 实现参考：[local_files.py](file:///E:/frogmouth/frogmouth/widgets/navigation_panes/local_files.py) 使用 `DirectoryTree` + `filter_paths` 子类化实现，仅过滤隐藏文件和 markdown 文件
- 项目开发规范要求：遵循模块化设计，避免重复造轮子

## Functional Requirements
- **FR-1**: 使用 Textual 内置 `DirectoryTree` 组件渲染文件树
- **FR-2**: 实现 `filter_paths` 方法过滤隐藏文件和黑名单目录
- **FR-3**: 保留文件类型图标和颜色区分（代码文件绿色、文档文件黄色）
- **FR-4**: 文件选中时发布 `FileSelected` Message
- **FR-5**: 支持基础键盘导航（上下、回车、Backspace）

## Non-Functional Requirements
- **NFR-1**: 启动时间不超过 1 秒（之前大目录可能数秒）
- **NFR-2**: 内存占用减少 50% 以上（对比预加载方案）
- **NFR-3**: 代码行数减少约 200 行
- **NFR-4**: 异常处理符合项目日志规范（使用 `common.logging_manager`）

## Constraints
- **Technical**: 必须使用 Textual 框架，Python 3.10+
- **Business**: 不影响其他面板功能
- **Dependencies**: 依赖 `tui.theming.icons` 的图标系统

## Assumptions
- 用户使用的是 Textual 0.50+ 版本（支持 `DirectoryTree`）
- `DirectoryTree` 组件的 API 稳定且支持子类化 `filter_paths`
- 现有图标系统 `get_file_icon` 可以继续使用

## Acceptance Criteria

### AC-1: 懒加载性能提升
- **Given**: 用户在包含 1000+ 文件的大型项目目录启动 TUI
- **When**: 打开侧边栏文件树面板
- **Then**: 文件树立即显示根目录内容，不等待子目录遍历完成
- **Verification**: `human-judgment`

### AC-2: 目录黑名单过滤
- **Given**: 项目目录包含 `.venv`, `node_modules`, `__pycache__`, `.git`
- **When**: 展开文件树
- **Then**: 黑名单目录不出现在树中
- **Verification**: `programmatic`

### AC-3: 文件图标颜色区分
- **Given**: 文件树中包含 `.py`（代码）、`.md`（文档）、`.json`（其他）文件
- **When**: 查看文件树显示
- **Then**: 代码文件显示绿色，文档文件显示黄色，其他文件使用默认颜色
- **Verification**: `human-judgment`

### AC-4: 文件选中事件
- **Given**: 用户在文件树中选中一个文件
- **When**: 按下 Enter 键或点击文件
- **Then**: 发布 `FileSelected` Message，包含文件路径
- **Verification**: `programmatic`

### AC-5: 键盘导航
- **Given**: 文件树获得焦点
- **When**: 按下上下键、Enter、Backspace
- **Then**: 光标移动、目录展开/文件打开、返回上级目录
- **Verification**: `human-judgment`

## Open Questions
- [ ] 是否需要保留 `go_root`（返回根目录）快捷键？DirectoryTree 有内置 Home 键支持
- [ ] 黑名单是否需要可配置（通过配置文件）？目前先硬编码常见黑名单
