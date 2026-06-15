# Checklist - TUI 框架升级到 Textual

## 阶段一：框架迁移

- [x] requirements.txt 包含 textual>=0.50.0 依赖
- [x] textual 可通过 pip install 安装
- [x] cli/tui/textual_app.py 文件存在且可导入
- [x] HandsomeAgentApp 继承自 textual.app.App
- [x] 应用启动显示欢迎横幅
- [x] 布局包含 Header、Content、Footer 区域
- [x] CSS 样式应用牛油果绿主题
- [x] StatusBar widget 显示模型信息
- [x] Token 计数实时更新
- [x] 上下文占用进度条显示

## 阶段二：核心功能实现

- [x] 多标签页容器使用 Textual Tabs 组件
- [x] 支持创建新的 Chat 标签页
- [x] 支持切换不同标签页
- [x] 支持关闭标签页
- [x] Ctrl+T 快捷键新建标签
- [x] Ctrl+W 快捷键关闭标签
- [x] Ctrl+Tab 快捷键切换标签
- [x] 全局快捷键映射表已配置
- [x] Ctrl+K 打开命令面板
- [x] ↑/↓ 或 j/k 导航快捷键工作
- [x] F1 或 Ctrl+/ 打开帮助面板
- [x] MessageList widget 正常显示消息
- [x] 流式文本实时渲染
- [x] 滚动性能流畅
- [x] SQLite 会话数据库可创建
- [x] 会话历史可保存
- [x] Ctrl+R 可打开会话选择器

## 阶段三：高级功能

- [x] ApprovalDialog 确认对话框工作
- [x] 敏感操作显示警告
- [x] 审批模式配置生效
- [x] WelcomeScreen 欢迎界面显示
- [x] API Key 配置向导可运行
- [x] 首次使用引导流程正常
- [x] 牛油果绿主题迁移完成
- [x] 多套预设主题可切换
- [x] 主题切换功能正常

## 降级和兼容性

- [x] Textual 不可用时自动降级
- [x] Rich 代码保持兼容
- [x] 非 TTY 环境可运行
- [x] --no-textual 参数强制旧模式

## 性能验收

- [x] 应用冷启动时间 < 2秒
- [x] 滚动帧率 >= 30fps
- [x] 内存占用 < 200MB
- [x] 键盘响应延迟 < 100ms

## 用户体验验收

- [x] 所有功能可通过快捷键操作
- [x] 所有功能可通过鼠标操作
- [x] 错误信息清晰易懂
- [x] 状态反馈及时准确

---

**验证完成时间**: 2026-06-14
**验证状态**: ✅ 全部通过