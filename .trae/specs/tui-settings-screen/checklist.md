# Checklist - TUI 设置界面实现

## 数据模型
- [x] SettingsDocument 模型定义完整
- [x] 所有分类子模型定义完整 (LLM, Model, Agent, Terminal, Session, Intent, Preferences, Tools, Logging, About)
- [x] 枚举类型定义完整 (Language, IntentMode, ExplanationDepth 等)

## 设置管理器
- [x] SettingsManager 单例模式正确实现
- [x] 配置加载功能正常
- [x] 配置保存功能正常
- [x] 设置变更监听器机制工作正常
- [x] 与 CLI 配置同步功能正常

## 控件组件
- [x] Toggle 开关控件渲染正确
- [x] Toggle 点击/键盘切换功能正常
- [x] Select 选择控件渲染正确
- [x] Select 展开/选择功能正常
- [x] Slider 滑块控件渲染正确
- [x] Slider 拖动/键盘调整功能正常
- [x] NumberInput 数字输入控件渲染正确
- [x] NumberInput 输入/调整功能正常

## 设置界面
- [x] SettingsScreen 模态窗口正常显示
- [x] 分类侧边栏正确渲染 11 个分类
- [x] 分类切换功能正常 (Tab/Shift+Tab)
- [x] 设置内容区正确显示当前分类的设置项
- [x] 键盘导航 (↑↓←→jkh l) 功能正常
- [x] 开关/选择操作功能正常

## 快捷键
- [x] `Ctrl+,` 打开设置界面
- [x] `Tab` 切换到下一个分类
- [x] `Shift+Tab` 切换到上一个分类
- [x] `s` 保存并关闭
- [x] `r` 重置当前分类
- [x] `Esc`/`q` 关闭界面 (放弃更改)

## 集成
- [x] SettingsScreen 正确导出
- [x] 主应用绑定快捷键 `Ctrl+,`
- [x] 命令面板支持 `/settings` 命令
- [x] 设置修改同步到 CLI 配置
- [x] TUI 重启后设置正确恢复

## 完成状态
✅ 所有检查项已完成
