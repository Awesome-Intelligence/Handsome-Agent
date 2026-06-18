# TUI CSS `!important` 优化规范

## Why

当前 TUI CSS 中存在 37 处 `!important` 使用，其中大部分是不必要的：
- **硬编码颜色** (18处): 主题切换时需要 `!important` 强制覆盖
- **嵌套选择器** (15处): 选择器优先级不足，用 `!important` 补偿
- **基础样式** (4处): 基础样式定义时滥用 `!important`

这导致：
1. 主题切换逻辑复杂
2. CSS 难以维护和扩展
3. 样式优先级混乱

## What Changes

### CSS 变量驱动重构

将所有硬编码颜色替换为 CSS 变量，实现主题切换零 `!important`。

**优化前:**
```css
#app-header {
    border-bottom: solid #B180D7 !important;  /* 硬编码紫色 */
}

.theme-default #app-header {
    border-bottom: solid #B180D7 !important;  /* 又硬编码紫色 */
}
```

**优化后:**
```css
#app-header {
    border-bottom: solid var(--accent);  /* 使用变量 */
}

.theme-default {
    --accent: #B180D7;  /* 主题覆盖只需修改变量 */
}
```

### 变量系统完善

在 `base.css` 中新增必要的变量：

```css
:root {
    /* 侧边栏 Tab 变量 */
    --sidebar-tab-active-color: var(--tab-active-color);
    --sidebar-tab-indicator: var(--tab-indicator);

    /* 边框交互变量 */
    --border-hover: var(--accent);
    --border-focus: var(--accent);
    --border-active: var(--accent);

    /* 聊天区域边框变量 */
    --chat-area-border: transparent;
    --chat-area-border-hover: var(--accent);
}
```

### 选择器优先级优化

用具体 ID 选择器替代嵌套选择器 + `!important`：

**优化前:**
```css
SidebarContainer Tabs Tab.active {
    background: transparent !important;
    color: var(--tab-active-color) !important;
}
```

**优化后:**
```css
#sidebar-tabs Tab.active {
    background: transparent;
    color: var(--tab-active-color);
}
```

## Impact

- Affected specs: `tui-theming-consolidation`
- Affected code:
  - `cli/tui/theming/css/base.css`
  - `cli/tui/theming/css/components.css`
  - `cli/tui/theming/css/themes/default.css`
  - `cli/tui/textual_app/css.py`

## ADDED Requirements

### Requirement: CSS 变量完整性

系统 SHALL 通过 CSS 变量实现所有主题色覆盖，无需 `!important`。

#### Scenario: 主题切换
- **WHEN** 用户切换主题时
- **THEN** 只需修改变量值，所有使用该变量的组件自动更新

#### Scenario: 侧边栏 Tab 样式
- **WHEN** 侧边栏 Tab 组件渲染时
- **THEN** 使用 `var(--sidebar-tab-active-color)` 而非硬编码颜色

### Requirement: 选择器优先级

系统 SHALL 使用足够具体的选择器避免 `!important` 的使用。

#### Scenario: 嵌套组件样式覆盖
- **WHEN** 需要覆盖嵌套组件样式时
- **THEN** 使用 ID 选择器提升优先级，而非 `!important`

## MODIFIED Requirements

### Requirement: 基础组件样式定义

系统 SHALL 在 `components.css` 中定义基础组件样式，使用 CSS 变量。

**变更前:**
```css
#app-header {
    border-bottom: solid #B180D7 !important;
}
```

**变更后:**
```css
#app-header {
    border-bottom: solid var(--accent);
}
```

## REMOVED Requirements

### Requirement: 双重 CSS 定义

**Reason**: `css.py` 中的 APP_CSS 与 `theming/css/` 中的 CSS 文件功能重复，导致维护困难。

**Migration**: 将 `css.py` 中的样式定义迁移到 `theming/css/` 目录下，删除 `css.py` 中的内联 CSS。

## Technical Implementation

### 文件变更清单

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `theming/css/base.css` | 修改 | 新增必要的 CSS 变量 |
| `theming/css/components.css` | 修改 | 移除 25 处 `!important`，使用变量 |
| `theming/css/themes/default.css` | 修改 | 移除 9 处 `!important`，使用变量 |
| `textual_app/css.py` | 修改 | 移除 3 处 `!important`，考虑合并到 theming |

### 变量定义

```css
/* base.css - 新增变量 */
:root {
    /* 侧边栏 Tab */
    --sidebar-tab-active-color: var(--tab-active-color);
    --sidebar-tab-indicator: var(--tab-indicator);

    /* 边框交互 */
    --border-hover: var(--accent);
    --border-focus: var(--accent);
    --border-active: var(--accent);

    /* 聊天区域 */
    --chat-area-border: transparent;
    --chat-area-border-hover: var(--accent);

    /* 输入框 */
    --input-border-default: var(--border);
    --input-border-hover: var(--accent);
    --input-border-focus: var(--accent);
}
```

### `!important` 移除映射表

| 位置 | 原代码 | 新代码 |
|------|--------|--------|
| components.css:9 | `#B180D7 !important` | `var(--accent)` |
| components.css:108 | `var(--text-muted) !important` | `var(--text-muted)` (移除) |
| components.css:225-230 | 多处 `!important` | 使用变量，移除 |
| default.css:45 | `#B180D7 !important` | `var(--border-hover)` |
| default.css:50 | `#C9A0E0 !important` | `var(--input-border-default)` |

## Success Criteria

- [ ] `!important` 使用数量从 37 处减少到 0-2 处
- [ ] 所有硬编码颜色替换为 CSS 变量
- [ ] 主题切换功能正常工作
- [ ] 没有选择器优先级冲突导致的样式问题
- [ ] CSS 文件结构清晰：base.css → components.css → themes/*.css