# Cron Panel Empty Debug Session

**Session ID**: `cron-pane-empty`
**Status**: [FIXED]
**Created**: 2026-07-15
**Resolved**: 2026-07-15

## Bug Description
- **Symptom**: 切换到"定时"标签后，面板完全空白（连 `cron-heartbeat` / `cron-summary` / `cron-help` 都没显示）
- **Expected**: 11 个定时任务的列表 + heartbeat / summary / help hints
- **Environment**: Windows, TUI application (Textual 0.85+)
- **Reproduction**: 启动 TUI → 切换到"定时"标签 → 面板完全空白

## Hypotheses Investigated
1. **H1** ❌ `_on_activated` 调度后未真正执行 — **Falsified**: instrumentation 证实 on_mount 调度成功，且 _refresh_data 成功加载 jobs
2. **H2** ❌ `_load_jobs` 抛出异常 — **Falsified**: 11 jobs 正确加载
3. **H3** ❌ ListView 子项被样式隐藏 — **Falsified**: ListView 子项 display=True, region 正确
4. **H4** ✅ **CONFIRMED** — `TabPane` 高度为 0 导致 children 不渲染
5. **H5** ❌ `_render_widgets` None 检查提前 return — **Falsified**: 早期确实是 boolean 检查问题，但已用 is None 修复

## Root Cause

**Textual 0.85+ `TabbedContent` / `ContentSwitcher` 的高度布局问题**：

当切换到 cron tab 时，激活的 `TabPane` 高度保持为 0：

```
CronPane id=cron-pane: size=Size(width=48, height=0)
TabPane id=cron: size=Size(width=48, height=0)
```

**原因**：
- `TabbedContent` 内部用 `ContentSwitcher` 切换显示的 `TabPane`
- `ContentSwitcher` 默认 CSS `height: auto`
- `TabPane` 默认 CSS `height: auto`
- `SidebarContainer ContentSwitcher { height: 1fr; }` 让 ContentSwitcher 有高度
- 但是当 `display: True/False` 切换时，TabPane 的高度没有正确重新计算

**修复**（[sidebar.py:1271-1274](file:///e:/Awesome%20Intelligence/Handsome-Agent/tui/sidebar.py#L1271-L1274)）：

```css
CronPane {
    width: 100%;
    height: 1fr;  /* 改自 height: 100% */
}

CronPane #cron-container {
    width: 100%;
    height: 1fr;  /* 改自 height: 100% */
    padding: 0 1 1 1;
}
```

**为什么用 `1fr` 而不是 `100%`**：
- `100%` 解析为相对父级（hidden 时父级高度=0）的高度
- `1fr` 是 grid fraction，重新计算可用空间
- 在 `display=False → True` 切换后，`1fr` 强制重新布局

## 修复列表

### 1. CSS 高度修复（[sidebar.py:1266-1280](file:///e:/Awesome%20Intelligence/Handsome-Agent/tui/sidebar.py#L1266-L1280)）
- `CronPane` / `#cron-container` 高度从 `100%` 改为 `1fr`

### 2. ID 冲突修复（[sidebar.py:1344](file:///e:/Awesome%20Intelligence/Handsome-Agent/tui/sidebar.py#L1344)）
- `CronPane` id 从 `"cron"` 改为 `"cron-pane"`，避免与外层 `TabPane(id="cron")` 冲突

### 3. ListView 初始 index 修复（[sidebar.py:1372](file:///e:/Awesome%20Intelligence/Handsome-Agent/tui/sidebar.py#L1372)）
- `ListView(id="cron-list")` → `ListView(id="cron-list", initial_index=None)`
- 避免 mount 时自动设置 `index=0` 触发 `watch_index` → `scroll_to_widget` 的副作用

### 4. boolean → is None 检查（[sidebar.py:1611-1625](file:///e:/Awesome%20Intelligence/Handsome-Agent/tui/sidebar.py#L1611-L1625)）
- `_render_widgets` 用 `is None` 检查替代 `not widget` 检查
- 因为 Textual Widget 的 `__bool__` 返回 `self.display`，display=False 时 boolean 评估为 False

### 5. display 检查放宽（[sidebar.py:1567-1569](file:///e:/Awesome%20Intelligence/Handsome-Agent/tui/sidebar.py#L1567-L1569)）
- 首次加载时即使 tab 未激活也加载数据
- 后续刷新才跳过不可见面板

### 6. Tab 切换时聚焦内容（[sidebar.py:1957-1963](file:///e:/Awesome%20Intelligence/Handsome-Agent/tui/sidebar.py#L1957-L1963)）
- `on_tab_activated` 现在调用 `focus_active_tab()`

### 7. focus_active_tab 支持异步（[sidebar.py:1986-2006](file:///e:/Awesome%20Intelligence/Handsome-Agent/tui/sidebar.py#L1986-L2006)）
- 支持 `set_focus_within` 同步或异步方法
- 通过 `asyncio.iscoroutinefunction` 判断并用 `call_later` 调度

### 8. on_mount 懒加载调度（[sidebar.py:1450-1452](file:///e:/Awesome%20Intelligence/Handsome-Agent/tui/sidebar.py#L1450-L1452)）
- `on_mount` 用 `call_later(_on_activated)` 调度首次加载

## 验证

### 单元测试
- `tests/unit/test_cron_pane.py` — 29 tests passed
- `tests/unit/test_cron.py` — 51 tests passed
- **80/80 passed**

### Smoke 测试
- `tests/smoke/smoke_cron_pane.py` — 通过
- 输出: `jobs=2, ListView children=2`

### 真实场景验证（用 Textual pilot 模拟）
- 终端尺寸 80x24: 显示心跳 + 总结 + 1 个任务
- 终端尺寸 120x40: 显示心跳 + 总结 + 全部任务

**为什么小终端只显示 1 个任务**：
- 80x24 终端 → cron-list 高度约 5 行
- 每个 ListItem 高度 2 行
- 80x24 终端只能装下 1 个完整 ListItem
- 用户终端 (典型 80x24+ 但有 sidebar) 应该能看到多个任务

## 清理

- 已删除所有 debug_*.py 临时文件
- 已删除 .dbg/ 调试服务器文件
- 已删除 debug-cron-pane-empty.md 中的诊断脚手架代码
- 已停止 debug server
- 代码恢复到生产状态
