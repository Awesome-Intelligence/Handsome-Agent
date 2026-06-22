# TUI 设置界面规范

## Why
Handsome Agent TUI 缺少设置界面，用户无法在 TUI 中方便地修改配置。需要实现一套与 CLI setup 向导设置项一致的设置界面。

## What Changes
- 新增 TUI 设置界面模块 (`tui/views/settings_screen.py`)
- 新增设置数据模型 (`tui/views/settings/models.py`)
- 新增设置管理器 (`tui/views/settings/manager.py`)
- 新增设置控件组件 (`tui/views/settings/widgets.py`)
- 集成到主应用 (`tui/textual_app/app.py`)
- 添加快捷键绑定 (`Ctrl+,` 打开设置)

## Impact
- Affected specs: TUI 交互体验
- Affected code:
  - `tui/views/settings_screen.py` (新增)
  - `tui/views/settings/` (新增目录)
  - `tui/textual_app/app.py` (修改)
  - `tui/views/__init__.py` (修改)

## ADDED Requirements

### Requirement: 设置界面显示
系统应提供模态设置界面，包含左侧分类列表和右侧设置内容区。

#### Scenario: 打开设置界面
- **WHEN** 用户按下 `Ctrl+,` 或在命令面板输入 `/settings`
- **THEN** 显示设置界面模态窗口

### Requirement: 设置分类导航
系统应支持在 11 个分类间切换导航。

#### Scenario: 切换分类
- **WHEN** 用户按下 `Tab` 或 `Shift+Tab`
- **THEN** 焦点切换到上一个/下一个分类

### Requirement: 设置项编辑
系统应支持以下控件类型：
- 开关 (Toggle): Space/Enter 切换
- 选择 (Select): Enter 展开，方向键选择
- 滑块 (Slider): 方向键调整
- 数字输入: 直接输入或方向键调整
- 密码输入: 输入并可切换显示

### Requirement: 设置保存
- 修改立即生效，关闭时自动保存到 `~/.handsome_agent/tui_settings.json`
- 支持 `s` 快捷键手动保存
- 支持 `Esc` 放弃更改

### Requirement: 设置项列表
设置项与 CLI setup 向导保持一致：

| 分类 | 设置项 |
|------|--------|
| 🌐 语言 | 显示语言 (zh/en) |
| 🤖 大模型 | Provider, API Key, 模型, Base URL |
| 🔧 模型参数 | Temperature, Max Tokens, Context Window |
| 💻 终端 | 执行后端 (local/docker) |
| ⚙️ Agent | 最大迭代次数, 超时时间 |
| 🔄 会话 | 重置策略, 记忆系统, Context压缩 |
| 🧠 意图识别 | 识别模式 (llm/hybrid/keyword) |
| 📝 响应偏好 | 详细程度, 响应格式, 响应缓存 |
| 🛠️ 工具 | STT, TTS, Browser, Web Debug, Vision Debug |
| 📄 日志 | 文件日志 |
| ℹ️ 关于 | 版本信息, 许可证 |

## Implementation Notes

### 文件结构
```
tui/views/settings/
├── __init__.py
├── models.py      # Pydantic 数据模型
├── manager.py     # 设置管理器 (单例)
└── widgets.py     # 自定义控件
tui/views/settings_screen.py  # 设置界面主屏幕
```

### 配置存储
- TUI 专用: `~/.handsome_agent/tui_settings.json`
- CLI 同步: 通过 `cli/config/config.py` 读写 `~/.handsome_agent/config.json`

### 快捷键
| 按键 | 功能 |
|------|------|
| `Ctrl+,` | 打开设置 |
| `↑/↓` 或 `j/k` | 上/下移动 |
| `←/→` 或 `h/l` | 切换侧边栏/内容区 |
| `Tab` / `Shift+Tab` | 切换分类 |
| `Space` / `Enter` | 切换开关/确认 |
| `s` | 保存并关闭 |
| `r` | 重置当前分类 |
| `Esc` / `q` | 关闭 (放弃更改) |
