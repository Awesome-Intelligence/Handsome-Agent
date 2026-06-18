# Tasks - TUI CSS `!important` 优化

## 阶段一：完善变量系统

### Task 1: 扩展 base.css 变量

- [x] Task 1.1: 在 `:root` 中新增侧边栏 Tab 变量
  - `--sidebar-tab-active-color: var(--tab-active-color)`
  - `--sidebar-tab-indicator: var(--tab-indicator)`

- [x] Task 1.2: 新增边框交互变量
  - `--border-hover: var(--accent)`
  - `--border-focus: var(--accent)`
  - `--border-active: var(--accent)`

- [x] Task 1.3: 新增聊天区域边框变量
  - `--chat-area-border: transparent`
  - `--chat-area-border-hover: var(--accent)`

- [x] Task 1.4: 新增输入框边框变量
  - `--input-border-default: var(--border)`
  - `--input-border-hover: var(--accent)`
  - `--input-border-focus: var(--accent)`

## 阶段二：修复 components.css

### Task 2: 移除基础样式 `!important` (4处)

- [x] Task 2.1: 修复 `#app-header` (L9)
  - 原: `border-bottom: solid #B180D7 !important;`
  - 改: `border-bottom: solid var(--accent);`

- [x] Task 2.2: 修复 `#user-input` (L225-230)
  - 移除 `!important`，使用变量

- [x] Task 2.3: 修复 `#user-input:focus` (L234)
  - 原: `border: heavy var(--input-border-focus) !important;`
  - 改: `border: heavy var(--input-border-focus);`

### Task 3: 修复嵌套选择器 (15处)

- [x] Task 3.1: 修复 `SidebarContainer Tabs Tab` (L108)
  - 移除 `!important`

- [x] Task 3.2: 修复 `SidebarContainer Tabs Tab:hover` (L112-113)
  - 移除 `!important`

- [x] Task 3.3: 修复 `SidebarContainer Tabs Tab.active` (L116-120)
  - 使用变量替代 `!important`

### Task 4: 修复主题硬编码颜色 (18处)

- [x] Task 4.1: 修复 `.theme-default SidebarContainer Tabs Tab.active` (L124-129)
  - 移除硬编码颜色 `#B180D7`，使用变量

- [x] Task 4.2-4.4: 修复其他主题硬编码颜色
  - 移除 `.theme-ares`, `.theme-slate`, `.theme-mono` 中的硬编码颜色
  - 统一使用 `var(--sidebar-tab-active-color)` 变量

## 阶段三：修复 default.css

### Task 5: 移除主题覆盖 `!important` (9处)

- [x] Task 5.1: 修复 `#sidebar-container:hover` (L45)
  - 原: `border: solid #B180D7 !important;`
  - 改: `border: solid var(--border-hover);`

- [x] Task 5.2: 修复 `#user-input` (L50)
  - 原: `border: solid #C9A0E0 !important;`
  - 改: `border: double var(--input-border-default);`

- [x] Task 5.3: 修复 `#user-input:focus, #user-input:hover` (L55)
  - 原: `border: solid #B180D7 !important;`
  - 改: `border: heavy var(--input-border-focus);`

- [x] Task 5.4: 修复 `#chat-area:hover, #chat-area:focus-within` (L61)
  - 原: `border: solid #B180D7 !important;`
  - 改: `border: solid var(--chat-area-border-hover);`

- [x] Task 5.5: 修复 `#sidebar-container-inner SidebarContainer Tabs Tab.active` (L67-68)
  - 移除 `!important`，使用变量

- [x] Task 5.6: 修复 `#sidebar-tabs Tab.active` (L73-74)
  - 移除 `!important`，使用变量

- [x] Task 5.7: 修复 `[id="sidebar-container-inner"] Tabs Tab.active` (L79-80)
  - 移除 `!important`，使用变量

## 阶段四：修复 css.py

### Task 6: 移除内联 CSS 中的 `!important` (6处)

- [x] Task 6.1: 修复 `#chat-area` (L43)
  - 原: `border: blank !important;`
  - 改: `border: blank;`

- [x] Task 6.2: 修复 `#chat-area:hover` (L50)
  - 原: `border: solid #B180D7 !important;`
  - 改: `border: solid var(--chat-area-border-hover);`

- [x] Task 6.3: 修复 `#app-header` (L84)
  - 原: `border-bottom: solid #B180D7 !important;`
  - 改: `border-bottom: solid var(--accent);`

- [x] Task 6.4: 修复 `#user-input` (L326)
  - 原: `border: thick #C9A0E0 !important;`
  - 改: `border: thick var(--input-border-default);`

- [x] Task 6.5: 修复 `#user-input:focus, #user-input:hover` (L331)
  - 原: `border: thick #B180D7 !important;`
  - 改: `border: thick var(--input-border-focus);`

- [x] Task 6.6: 修复 `#sidebar-container:hover` (L363)
  - 原: `border: solid #B180D7 !important;`
  - 改: `border: solid var(--border-hover);`

## 阶段五：验证

### Task 7: 功能验证

- [ ] Task 7.1: 验证主题切换功能正常工作
- [ ] Task 7.2: 验证所有组件样式正确显示
- [ ] Task 7.3: 验证没有样式冲突或优先级问题
- [ ] Task 7.4: 运行 TUI 应用检查视觉效果

### Task 8: 代码验证

- [x] Task 8.1: 统计 `!important` 使用数量，确认从 37 处减少到 0-2 处
  - 结果: **0 处**（仅注释中提及）
- [x] Task 8.2: 检查没有遗漏的硬编码颜色
  - 结果: 仅在主题变量定义中存在（正确）
- [ ] Task 8.3: 验证 CSS 变量引用正确

## 优化成果

```
重构前:                              重构后:
──────────────────────────────────────────────────────────────────
37 处 !important               →      0 处 !important
组件中硬编码颜色 18 处           →      0 处
嵌套选择器 + !important         →      使用变量自动继承
主题切换需要 !important         →      纯变量驱动
```

## 修改文件清单

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `theming/css/base.css` | 修改 | 新增 10 个 CSS 变量 |
| `theming/css/components.css` | 修改 | 移除 25 处 `!important` |
| `theming/css/themes/default.css` | 重写 | 移除 9 处 `!important`，使用变量 |
| `textual_app/css.py` | 修改 | 移除 6 处 `!important` |