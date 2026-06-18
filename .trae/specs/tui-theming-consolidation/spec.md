# TUI Theming 目录合并规范

## Why

当前 `cli/tui/` 目录存在 `styles/` 和 `themes/` 两个与样式相关的目录，职责边界模糊：
- `styles/` 包含 CSS 文件（base.css, components.css 等）
- `themes/` 包含 Python 代码（theme_manager.py, colors.py 等）

这种分离虽然有一定逻辑，但命名不够直观，且主题相关的代码分散在两处（`styles/themes/` 目录下的 CSS 和 `themes/` 目录下的 Python 配置）。

## What Changes

### 方案二：合并到单一 theming 目录

将 `styles/` 和 `themes/` 合并为统一的 `theming/` 目录：

**合并前：**
```
cli/tui/
├── styles/
│   ├── __init__.py
│   ├── base.css
│   ├── components.css
│   ├── layout.css
│   ├── animations.css
│   └── themes/
│       └── default.css
└── themes/
    ├── __init__.py
    ├── theme_manager.py
    ├── theme_config.py
    ├── colors.py
    ├── icons.py
    ├── preset_themes.py
    └── typography.py
```

**合并后：**
```
cli/tui/
└── theming/
    ├── __init__.py
    ├── css/
    │   ├── base.css
    │   ├── components.css
    │   ├── layout.css
    │   ├── animations.css
    │   └── themes/
    │       └── default.css
    ├── theme_manager.py
    ├── theme_config.py
    ├── colors.py
    ├── icons.py
    ├── preset_themes.py
    └── typography.py
```

### 关键变更

1. **目录重命名**: `styles/` → `theming/css/`
2. **目录合并**: `themes/` → `theming/` (内容合并到同级)
3. **Python 模块位置调整**: 保持 Python 代码在根目录，CSS 在 css/ 子目录
4. **导入路径更新**: 所有引用 `cli.tui.styles` 和 `cli.tui.themes` 的代码需要更新

### 向后兼容策略

- **删除旧的 `cli.tui.themes` 和 `cli.tui.styles` 导入路径**
- 更新所有内部导入指向新的 `cli.tui.theming` 路径

## Impact

- Affected specs: `tui-architecture-refactor`
- Affected code: 所有引用 `cli.tui.styles` 和 `cli.tui.themes` 的模块

## ADDED Requirements

### Requirement: 统一的 theming 模块

系统 SHALL 提供统一的 `theming/` 模块来管理所有与主题和样式相关的代码。

#### Scenario: 主题管理器导入
- **WHEN** 需要主题管理功能时
- **THEN** 使用 `from cli.tui.theming import ThemeManager`

#### Scenario: CSS 样式加载
- **WHEN** TUI 应用需要加载 CSS 时
- **THEN** 使用 `from cli.tui.theming.css import get_stylesheets`

#### Scenario: 颜色常量导入
- **WHEN** 需要颜色常量时
- **THEN** 使用 `from cli.tui.theming import STATUS_ONLINE, STATUS_ERROR`

### Requirement: 主题配置导入

系统 SHALL 通过统一的入口导出所有主题相关的公共 API。

#### Scenario: 完整主题系统导入
- **WHEN** 需要导入整个主题系统时
- **THEN** 使用 `from cli.tui.theming import *`

## Technical Implementation

### 1. 新目录结构

```
cli/tui/theming/
├── __init__.py                    # 导出所有公共 API
├── css/
│   ├── __init__.py                # CSS 加载函数
│   ├── base.css
│   ├── components.css
│   ├── layout.css
│   ├── animations.css
│   └── themes/
│       └── default.css
├── theme_manager.py
├── theme_config.py
├── preset_themes.py
├── colors.py
├── icons.py
└── typography.py
```

### 2. 迁移策略

#### Phase 1: 创建新目录结构
1. 创建 `theming/` 目录
2. 创建 `theming/css/` 目录
3. 移动 `styles/` 内容到 `theming/css/`
4. 移动 `themes/` 内容到 `theming/`

#### Phase 2: 更新 Python 导入路径
1. 更新 `theming/__init__.py` 导出所有公共 API
2. 更新 `theming/css/__init__.py` 导出 CSS 加载函数
3. 更新所有引用 `cli.tui.styles` 的代码
4. 更新所有引用 `cli.tui.themes` 的代码

#### Phase 3: 验证和清理
1. 验证所有导入正常工作
2. 删除旧的 `styles/` 目录
3. 删除旧的 `themes/` 目录

### 3. 导入路径变更

| 旧路径 | 新路径 |
|--------|--------|
| `cli.tui.styles` | `cli.tui.theming.css` |
| `cli.tui.styles.get_stylesheets` | `cli.tui.theming.css.get_stylesheets` |
| `cli.tui.themes` | `cli.tui.theming` |
| `cli.tui.themes.ThemeManager` | `cli.tui.theming.ThemeManager` |
| `cli.tui.themes.STATUS_ONLINE` | `cli.tui.theming.STATUS_ONLINE` |

### 4. 关键文件内容

```python
# theming/__init__.py
"""TUI Theming 系统 - 统一的样式和主题管理"""
from .theme_config import Theme, ThemeConfig
from .theme_manager import ThemeManager, get_theme_manager
from .colors import STATUS_ONLINE, STATUS_ERROR, transparent, TRANSPARENCY_LEVELS
from .icons import MESSAGE_ICONS, FILE_TYPE_ICONS, TASK_STATUS_ICONS
from .typography import TypographyConfig, DEFAULT_TYPOGRAPHY
from .preset_themes import _PRESET_THEMES

__all__ = [
    # 数据类
    "Theme",
    "ThemeConfig",
    "TypographyConfig",
    # 管理器
    "ThemeManager",
    "get_theme_manager",
    # 颜色
    "STATUS_ONLINE",
    "STATUS_ERROR",
    "transparent",
    "TRANSPARENCY_LEVELS",
    # 图标
    "MESSAGE_ICONS",
    "FILE_TYPE_ICONS",
    "TASK_STATUS_ICONS",
    # 配置
    "DEFAULT_TYPOGRAPHY",
    "_PRESET_THEMES",
]
```

```python
# theming/css/__init__.py
"""CSS 样式模块化架构"""
from pathlib import Path
from typing import List

def get_stylesheets() -> List[str]:
    """获取所有样式表文件路径"""
    css_dir = Path(__file__).parent
    return [
        str(css_dir / "base.css"),
        str(css_dir / "layout.css"),
        str(css_dir / "components.css"),
        str(css_dir / "animations.css"),
    ]

def get_theme_css(theme_id: str) -> str:
    """获取主题 CSS 文件内容"""
    theme_path = Path(__file__).parent / "themes" / f"{theme_id}.css"
    if theme_path.exists():
        return theme_path.read_text(encoding="utf-8")
    return ""
```

## Success Criteria

- [ ] `theming/` 目录包含所有样式和主题相关代码
- [ ] `theming/css/` 目录包含所有 CSS 文件
- [ ] 所有 Python 模块正常工作
- [ ] 所有 CSS 样式正常加载
- [ ] 没有遗留的旧目录或文件
- [ ] 所有导入路径已更新
