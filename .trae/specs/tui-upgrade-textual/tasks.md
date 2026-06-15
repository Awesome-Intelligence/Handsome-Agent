# Tasks - TUI 框架升级到 Textual

## 阶段一：框架迁移

### Task 1: 环境准备和依赖配置
- [x] SubTask 1.1: 在 requirements.txt 中添加 textual>=0.50.0 依赖
- [x] SubTask 1.2: 创建 cli/tui/textual_app.py 作为新的 TUI 入口
- [x] SubTask 1.3: 配置 pyproject.toml 或 setup.py 确保 textual 可选安装

### Task 2: 基础 Textual App 结构
- [x] SubTask 2.1: 实现 HandsomeAgentApp 主类，继承 textual.app.App
- [x] SubTask 2.2: 实现基础布局（Header、Content、Footer）
- [x] SubTask 2.3: 配置 CSS 样式，适配牛油果绿主题
- [x] SubTask 2.4: 实现启动欢迎横幅渲染

### Task 3: 状态栏迁移
- [x] SubTask 3.1: 创建 StatusBar widget 显示模型信息
- [x] SubTask 3.2: 实现 Token 计数和上下文占用显示
- [x] SubTask 3.3: 实现实时状态更新机制

## 阶段二：核心功能实现

### Task 4: 多标签页系统
- [x] SubTask 4.1: 使用 Textual Tabs 组件实现标签页容器
- [x] SubTask 4.2: 实现 Chat 标签页内容区域
- [x] SubTask 4.3: 实现标签页创建、切换、关闭功能
- [x] SubTask 4.4: 添加 Ctrl+T 新建标签快捷键
- [x] SubTask 4.5: 添加 Ctrl+W 关闭标签快捷键

### Task 5: 快捷键绑定系统
- [x] SubTask 5.1: 实现全局快捷键映射表
- [x] SubTask 5.2: 实现 Ctrl+K 命令面板
- [x] SubTask 5.3: 实现 ↑/↓ 或 j/k 导航快捷键
- [x] SubTask 5.4: 实现 F1/Ctrl+/ 帮助面板快捷键
- [x] SubTask 5.5: 实现 Ctrl+Tab 标签切换快捷键

### Task 6: 流式输出增强
- [x] SubTask 6.1: 创建 MessageList widget 显示消息
- [x] SubTask 6.2: 实现流式文本渲染（StreamingText）
- [x] SubTask 6.3: 实现思考过程显示（可选功能）
- [x] SubTask 6.4: 优化大量输出时的滚动性能

### Task 7: 会话持久化
- [x] SubTask 7.1: 设计会话数据库 schema（SQLite）
- [x] SubTask 7.2: 实现会话存储服务（SessionStore）
- [x] SubTask 7.3: 实现会话历史加载和恢复
- [x] SubTask 7.4: 实现 Ctrl+R 会话选择器

## 阶段三：高级功能

### Task 8: 权限审批系统
- [x] SubTask 8.1: 创建 ApprovalDialog 确认对话框
- [x] SubTask 8.2: 实现工具执行前的确认流程
- [x] SubTask 8.3: 配置审批模式（Auto/Suggest/Manual）
- [x] SubTask 8.4: 添加敏感操作警告提示

### Task 9: 新用户引导
- [x] SubTask 9.1: 创建 WelcomeScreen 欢迎界面
- [x] SubTask 9.2: 实现 API Key 配置向导
- [x] SubTask 9.3: 实现首次使用引导流程
- [x] SubTask 9.4: 添加跳过和后续配置选项

### Task 10: 主题系统增强
- [x] SubTask 10.1: 迁移现有牛油果绿主题到 Textual CSS
- [x] SubTask 10.2: 实现多套预设主题（default/ares/mono/slate）
- [x] SubTask 10.3: 实现主题切换功能
- [x] SubTask 10.4: 保持与现有皮肤引擎的兼容性

### Task 11: 降级和兼容性
- [x] SubTask 11.1: 实现 Textual 不可用时的降级机制
- [x] SubTask 11.2: 保持与现有 Rich 代码的兼容性
- [x] SubTask 11.3: 实现非 TTY 环境回退
- [x] SubTask 11.4: 添加 --no-textual 参数强制使用旧模式

## Task Dependencies

```
Task 1 (环境准备) ✅
    ↓
Task 2 (基础结构) ✅
    ↓
Task 3 (状态栏) ✅
    ↓
Task 4 (多标签页) ✅ ← Task 5 (快捷键) ✅
    ↓
Task 6 (流式输出) ✅
    ↓
Task 7 (会话持久化) ✅
    ↓
Task 8 (权限审批) ✅ ← Task 9 (新用户引导) ✅
    ↓
Task 10 (主题系统) ✅ ← Task 11 (降级兼容性) ✅
```

## 验收标准

1. 所有核心功能可通过快捷键和鼠标操作
2. 性能达到 30fps 以上滚动流畅度
3. 保持与现有业务逻辑的兼容性
4. 提供降级方案确保在不支持的环境可运行

---

**完成状态**: ✅ 全部完成（11 个主要任务，44 个子任务）