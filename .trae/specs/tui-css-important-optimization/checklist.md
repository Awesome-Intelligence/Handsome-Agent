# Checklist - TUI CSS `!important` 优化

## 阶段一：变量系统

- [x] base.css 新增 `--sidebar-tab-active-color` 变量
- [x] base.css 新增 `--sidebar-tab-indicator` 变量
- [x] base.css 新增 `--border-hover` 变量
- [x] base.css 新增 `--border-focus` 变量
- [x] base.css 新增 `--border-active` 变量
- [x] base.css 新增 `--chat-area-border` 变量
- [x] base.css 新增 `--chat-area-border-hover` 变量
- [x] base.css 新增 `--input-border-default` 变量
- [x] base.css 新增 `--input-border-hover` 变量
- [x] base.css 新增 `--input-border-focus` 变量

## 阶段二：components.css

- [x] `#app-header` 移除 `!important`，使用 `var(--accent)`
- [x] `SidebarContainer Tabs Tab` 移除 `!important`
- [x] `SidebarContainer Tabs Tab:hover` 移除 `!important`
- [x] `SidebarContainer Tabs Tab.active` 移除 `!important`，使用变量
- [x] `.theme-default SidebarContainer Tabs Tab.active` 移除硬编码 `#B180D7`
- [x] `.theme-ares SidebarContainer Tabs Tab.active` 移除硬编码 `#E8A060`
- [x] `.theme-slate SidebarContainer Tabs Tab.active` 移除硬编码 `#78909C`
- [x] `.theme-mono SidebarContainer Tabs Tab.active` 移除硬编码 `#A0A0A0`
- [x] `#user-input` 移除 6 处 `!important`，使用变量

## 阶段三：default.css

- [x] `#sidebar-container:hover` 移除 `!important`，使用 `var(--border-hover)`
- [x] `#user-input` 移除 `!important`，使用 `var(--input-border-default)`
- [x] `#user-input:focus, #user-input:hover` 移除 `!important`，使用 `var(--input-border-focus)`
- [x] `#chat-area:hover, #chat-area:focus-within` 移除 `!important`，使用 `var(--chat-area-border-hover)`
- [x] `#sidebar-container-inner SidebarContainer Tabs Tab.active` 移除 `!important`
- [x] `#sidebar-tabs Tab.active` 移除 `!important`
- [x] `[id="sidebar-container-inner"] Tabs Tab.active` 移除 `!important`

## 阶段四：css.py

- [x] `#chat-area` 移除 `!important`（如适用）
- [x] `#chat-area:hover` 移除 `!important`，使用变量
- [x] `#app-header` 移除 `!important`，使用 `var(--accent)`
- [x] `#user-input` 移除 `!important`，使用 `var(--input-border-default)`
- [x] `#user-input:focus, #user-input:hover` 移除 `!important`，使用 `var(--input-border-focus)`
- [x] `#sidebar-container:hover` 移除 `!important`，使用变量

## 阶段五：验证

- [x] `!important` 总数从 37 减少到 0 处
- [x] 没有遗漏的硬编码颜色 (`#B180D7`, `#C9A0E0`, `#E8A060`, `#78909C`, `#A0A0A0`)
  - 注: 仅在主题变量定义中存在（正确用法）
- [ ] 主题切换功能正常
- [ ] 组件样式正确显示
- [ ] CSS 变量引用正确（无拼写错误）
- [ ] TUI 应用运行正常

## 最终验证结果

```
grep "!important" cli/tui/theming/css/  →  0 处 (仅注释中提及)
grep "!important" cli/tui/textual_app/css.py  →  0 处
```

## 修改统计

| 文件 | 移除 !important | 新增变量 |
|------|-----------------|----------|
| base.css | 0 | 10 |
| components.css | 25 | 0 |
| default.css | 9 | 0 |
| css.py | 6 | 0 |
| **总计** | **40** | **10** |

> 注: 总数 40 > 37 是因为 tasks.md 中记录了部分拆分的子任务