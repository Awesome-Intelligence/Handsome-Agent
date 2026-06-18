# TUI 架构重构规范

## Why

当前 Handsome-Agent 的 TUI 代码存在严重的架构问题：
- **超大文件**：单个文件超过 3000 行，严重违反单一职责原则
- **模块化不足**：CSS 文件为空，样式仍以内联字符串形式存在
- **目录结构混乱**：基础设施代码分散在根目录，缺乏组织

参考 Frogmouth 的最佳实践，需要对 TUI 代码进行系统性重构。

## What Changes

### 核心重构目标

1. **拆分 `textual_app.py`** - 从 3377 行拆分为 6 个专注的文件
2. **拆分 `themes.py`** - 从 1375 行拆分为 4 个配置类文件
3. **填充 `styles/` CSS 模块** - 实现真正的 CSS 模块化
4. **创建 `core/` 子包** - 重组基础设施代码
5. **建立统一的导出模式** - 通过 `__init__.py` 控制公共 API

### 文件拆分方案

#### textual_app/ 子包（替代单个文件）

```
cli/tui/textual_app/
├── __init__.py              # 导出主类
├── app.py                   # HandsomeAgentApp 主类 (~800行)
├── css.py                   # 内联 CSS 内容 (~800行)
├── log_handler.py           # TuiLogHandler 类 (~150行)
├── notifications.py         # NotificationAnimationManager (~200行)
├── text_area.py             # SubmitTextArea 等组件 (~300行)
└── helpers.py              # 辅助函数 (~100行)
```

#### themes/ 子包（替代单个文件）

```
cli/tui/themes/
├── __init__.py              # 导出所有公共 API
├── theme_config.py          # Theme、ThemeConfig 数据类 (~200行)
├── preset_themes.py         # 预设主题定义 (~400行)
├── icons.py                 # 图标映射常量 (~300行)
├── theme_manager.py         # ThemeManager 类 (~300行)
└── colors.py                # 颜色常量 + 半透明函数 (~200行)
```

#### core/ 子包（新增）

```
cli/tui/core/
├── __init__.py              # 导出基础设施
├── keybindings.py          # 快捷键系统 (~500行)
├── markdown_renderer.py     # Markdown 渲染器 (~500行)
└── curses_ui.py            # 跨平台 curses UI (~600行)
```

## Impact

- Affected specs: `tui-frogmouth-style`（CSS 模块化部分依赖本规范）
- Affected code: `cli/tui/` 整个目录

## ADDED Requirements

### Requirement: textual_app 子包结构

系统 SHALL 将超大的 `textual_app.py` 拆分为职责明确的子模块。

#### Scenario: 主应用类导入
- **WHEN** 其他模块需要导入主应用时
- **THEN** 使用 `from cli.tui.textual_app import HandsomeAgentApp`

#### Scenario: CSS 加载
- **WHEN** 主应用初始化时
- **THEN** 从 `textual_app.css` 模块加载 CSS 内容

#### Scenario: 日志处理器
- **WHEN** 需要 TUI 日志处理器时
- **THEN** 从 `textual_app.log_handler` 导入

### Requirement: themes 子包结构

系统 SHALL 将配置密集的 `themes.py` 拆分为数据类和配置模块。

#### Scenario: 主题配置导入
- **WHEN** 需要主题数据类时
- **THEN** 使用 `from cli.tui.themes import Theme, ThemeConfig`

#### Scenario: 主题管理器导入
- **WHEN** 需要主题管理功能时
- **THEN** 使用 `from cli.tui.themes import ThemeManager`

#### Scenario: 图标常量导入
- **WHEN** 需要消息类型图标时
- **THEN** 使用 `from cli.tui.themes import MESSAGE_ICONS`

### Requirement: core 子包结构

系统 SHALL 将基础设施代码组织到 `core/` 子包中。

#### Scenario: 快捷键导入
- **WHEN** 需要快捷键绑定时
- **THEN** 使用 `from cli.tui.core import keybindings`

#### Scenario: Markdown 渲染导入
- **WHEN** 需要 Markdown 渲染功能时
- **THEN** 使用 `from cli.tui.core import markdown_renderer`

### Requirement: 样式模块化实现

系统 SHALL 实现真正的 CSS 模块化架构。

#### Scenario: 样式加载
- **WHEN** TUI 应用启动时
- **THEN** 按顺序加载 base.css → layout.css → components.css

#### Scenario: 变量引用
- **WHEN** 组件使用 CSS 变量时
- **THEN** 变量在 base.css 中定义，其他模块引用

### Requirement: 向后兼容性

系统 SHALL 在重构过程中保持向后兼容。

#### Scenario: 现有导入路径
- **WHEN** 现有代码使用旧导入路径时
- **THEN** 通过 `__init__.py` 中的重导出保持兼容

## Technical Implementation

### 1. textual_app/ 子包结构

```python
# textual_app/__init__.py
"""Textual TUI 主应用模块"""
from .app import HandsomeAgentApp
from .css import APP_CSS
from .log_handler import TuiLogHandler
from .notifications import NotificationAnimationManager, NotificationType
from .text_area import SubmitTextArea

__all__ = [
    "HandsomeAgentApp",
    "APP_CSS",
    "TuiLogHandler",
    "NotificationAnimationManager",
    "NotificationType",
    "SubmitTextArea",
]
```

```python
# textual_app/app.py
"""主应用类 - 专注于应用逻辑"""
class HandsomeAgentApp(App):
    # 移除内联 CSS（约 800-1000 行）
    # 保留核心应用逻辑、绑定、消息处理
```

```python
# textual_app/css.py
"""CSS 内容 - 从原 textual_app.py 提取"""
APP_CSS = """
/* 完整的 CSS 内容 */
Screen {
    ...
}
"""
```

### 2. themes/ 子包结构

```python
# themes/__init__.py
"""主题系统模块"""
from .theme_config import Theme, ThemeConfig
from .preset_themes import AVOCADO_DARK, AVOCADO_LIGHT, PRESET_THEMES
from .icons import MESSAGE_ICONS, FILE_TYPE_ICONS, TASK_STATUS_ICONS
from .theme_manager import ThemeManager
from .colors import transparent, TRANSPARENCY_LEVELS

__all__ = [
    "Theme",
    "ThemeConfig",
    "AVOCADO_DARK",
    "AVOCADO_LIGHT",
    "PRESET_THEMES",
    "MESSAGE_ICONS",
    "FILE_TYPE_ICONS",
    "TASK_STATUS_ICONS",
    "ThemeManager",
    "transparent",
    "TRANSPARENCY_LEVELS",
]
```

### 3. core/ 子包结构

```python
# core/__init__.py
"""基础设施核心模块"""
from . import keybindings
from . import markdown_renderer
from . import curses_ui

__all__ = ["keybindings", "markdown_renderer", "curses_ui"]
```

### 4. 迁移策略

#### Phase 1: 创建新目录结构
1. 创建 `textual_app/`、`themes/`、`core/` 目录
2. 创建 `__init__.py` 文件
3. 逐步迁移代码到新文件

#### Phase 2: 更新导入路径
1. 更新 `cli/tui/__init__.py` 中的导出
2. 更新所有内部模块的导入
3. 验证没有循环导入

#### Phase 3: 删除旧文件
1. 确认所有功能已迁移
2. 删除旧的 `textual_app.py`
3. 删除旧的 `themes.py`

### 5. 文件行数目标

| 目标文件 | 目标行数 | 说明 |
|---------|---------|------|
| `textual_app/app.py` | ≤ 800 | 主应用逻辑 |
| `textual_app/css.py` | ≤ 800 | CSS 内容 |
| `textual_app/log_handler.py` | ≤ 150 | 日志处理器 |
| `textual_app/notifications.py` | ≤ 200 | 通知管理 |
| `textual_app/text_area.py` | ≤ 300 | 文本区域组件 |
| `themes/theme_config.py` | ≤ 200 | 数据类 |
| `themes/preset_themes.py` | ≤ 400 | 主题定义 |
| `themes/icons.py` | ≤ 300 | 图标映射 |
| `themes/theme_manager.py` | ≤ 300 | 主题管理器 |
| `themes/colors.py` | ≤ 200 | 颜色工具 |
| `core/keybindings.py` | ≤ 500 | 快捷键系统 |
| `core/markdown_renderer.py` | ≤ 500 | Markdown 渲染 |
| `core/curses_ui.py` | ≤ 600 | curses 封装 |

## Success Criteria

- [ ] `textual_app/` 子包包含所有主应用相关代码
- [ ] `themes/` 子包包含所有主题相关代码
- [ ] `core/` 子包包含所有基础设施代码
- [ ] 所有单个文件不超过 800 行
- [ ] 通过 `__init__.py` 保持向后兼容
- [ ] 没有循环导入
- [ ] 所有现有导入路径继续工作
- [ ] TUI 应用可以正常启动
