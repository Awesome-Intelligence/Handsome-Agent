# TUI 设置界面设计方案

> 版本: v1.0.0
> 日期: 2026-06-22
> 状态: 设计中

---

## 一、概述

### 1.1 设计目标

为 Handsome Agent TUI 提供一套完整的设置界面，使设置项与 CLI `setup` 向导保持一致，支持：

- 键盘导航操作
- 实时预览效果
- 配置持久化
- 分类清晰的设置项

### 1.2 设计原则

1. **一致性**: 设置项与 `cli/setup/setup_wizard.py` 完全对齐
2. **易用性**: 支持键盘完全操作，Tab 切换分类，Enter/Space 切换选项
3. **可发现性**: 使用图标和分组提高可读性
4. **实时性**: 修改后立即生效，无需重启

---

## 二、设置项分类

### 2.1 分类总览

```
设置界面
├── 🌐 语言 (Language)
├── 🤖 大模型 (LLM)
│   ├── Provider 选择
│   ├── API Key
│   └── 模型配置
├── 🔧 模型参数 (Model Parameters)
│   ├── Temperature
│   ├── Max Tokens
│   └── Context Window
├── 💻 终端 (Terminal)
│   └── 执行后端
├── ⚙️ Agent 设置 (Agent Settings)
│   ├── 最大迭代次数
│   └── 超时时间
├── 🔄 会话 (Session)
│   ├── 重置策略
│   ├── 记忆系统
│   └── Context 压缩
├── 🧠 意图识别 (Intent Recognition)
│   └── 识别模式
├── 📝 响应偏好 (Response Preferences)
│   ├── 详细程度
│   ├── 响应格式
│   └── 响应缓存
├── 🛠️ 工具 (Tools)
│   ├── STT
│   ├── TTS
│   ├── Browser
│   └── Debug
├── 📄 日志 (Logging)
│   └── 文件日志
└── ℹ️ 关于 (About)
    ├── 版本信息
    └── 许可证
```

### 2.2 设置项详细定义

#### 2.2.1 🌐 语言 (Language)

| 设置项 | 键路径 | 类型 | 选项 | 默认值 |
|--------|--------|------|------|--------|
| 显示语言 | `display.language` | 选择 | zh (中文), en (English) | zh |

#### 2.2.2 🤖 大模型 (LLM)

| 设置项 | 键路径 | 类型 | 选项 | 默认值 |
|--------|--------|------|------|--------|
| Provider | `llm.provider` | 选择 | deepseek, openai, anthropic, gemini, ollama, none | - |
| API Key | `llm.api_key` | 密码 | - | - |
| 模型 | `llm.model` | 选择/输入 | Provider 相关 | - |
| Base URL | `llm.base_url` | 输入 | - | - |

#### 2.2.3 🔧 模型参数 (Model Parameters)

| 设置项 | 键路径 | 类型 | 范围 | 默认值 |
|--------|--------|------|------|--------|
| Temperature | `model.temperature` | 滑块 | 0.0 - 2.0 | 0.7 |
| Max Tokens | `model.max_tokens` | 数字 | 1 - 32000 | 4096 |
| Context Window | `model.context_window` | 数字 | 1000 - 1000000 | 128000 |

#### 2.2.4 💻 终端 (Terminal)

| 设置项 | 键路径 | 类型 | 选项 | 默认值 |
|--------|--------|------|------|--------|
| 执行后端 | `terminal.backend` | 选择 | local (本地), docker (Docker容器) | local |

#### 2.2.5 ⚙️ Agent 设置

| 设置项 | 键路径 | 类型 | 范围 | 默认值 |
|--------|--------|------|------|--------|
| 最大迭代次数 | `agent.max_iterations` | 数字 | 1 - 100 | 10 |
| 超时时间(秒) | `agent.timeout_seconds` | 数字 | 1 - 600 | 60 |

#### 2.2.6 🔄 会话 (Session)

| 设置项 | 键路径 | 类型 | 选项 | 默认值 |
|--------|--------|------|------|--------|
| 重置策略 | `session_reset.mode` | 选择 | both, daily, idle, none | both |
| 记忆系统 | `memory.enabled` | 开关 | true/false | false |
| Context 压缩 | `compression.enabled` | 开关 | true/false | true |

#### 2.2.7 🧠 意图识别

| 设置项 | 键路径 | 类型 | 选项 | 默认值 |
|--------|--------|------|------|--------|
| 识别模式 | `intent_mode` | 选择 | llm, hybrid, keyword | llm |

#### 2.2.8 📝 响应偏好

| 设置项 | 键路径 | 类型 | 选项 | 默认值 |
|--------|--------|------|------|--------|
| 详细程度 | `preferences.explanation_depth` | 选择 | brief, moderate, detailed | detailed |
| 响应格式 | `preferences.response_format` | 选择 | markdown, plain | markdown |
| 响应缓存 | `preferences.enable_caching` | 开关 | true/false | true |

#### 2.2.9 🛠️ 工具 (Tools)

| 设置项 | 键路径 | 类型 | 默认值 |
|--------|--------|------|--------|
| STT (语音转文字) | `stt.enabled` | 开关 | false |
| TTS (文字转语音) | `tts.enabled` | 开关 | false |
| Browser | `browser.enabled` | 开关 | false |
| Web Debug | `debug_tools.web_tools` | 开关 | false |
| Vision Debug | `debug_tools.vision_tools` | 开关 | false |

#### 2.2.10 📄 日志

| 设置项 | 键路径 | 类型 | 默认值 |
|--------|--------|------|--------|
| 文件日志 | `logging.file_enabled` | 开关 | false |

---

## 三、界面设计

### 3.1 布局结构

```
┌─────────────────────────────────────────────────────────────────────┐
│  ⚙ 设置                                            [×] Esc 关闭  │
├───────────────┬─────────────────────────────────────────────────────┤
│               │                                                     │
│  🌐 语言      │  当前分类设置内容...                                 │
│  🤖 大模型    │                                                     │
│  🔧 模型参数  │  ┌─────────────────────────────────────────────┐   │
│  💻 终端      │  │ 设置项 1: [当前值]                     ▼   │   │
│  ⚙️ Agent    │  ├─────────────────────────────────────────────┤   │
│  🔄 会话      │  │ 设置项 2: [×] 启用                          │   │
│  🧠 意图      │  ├─────────────────────────────────────────────┤   │
│  📝 响应      │  │ 设置项 3: [━━━━━━●━━━━━] 50%              │   │
│  🛠️ 工具      │  └─────────────────────────────────────────────┘   │
│  📄 日志      │                                                     │
│  ℹ️ 关于      │                                                     │
│               │                                                     │
├───────────────┴─────────────────────────────────────────────────────┤
│  ↑↓ 移动  Space/Enter 切换  Tab 切换分类  Esc 关闭  r 重置当前   │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 控件类型

#### 3.2.1 选择控件 (Select)
```
┌─────────────────────────────────────────┐
│ Temperature: [0.7 ▼]                   │
└─────────────────────────────────────────┘
         ↑ 展开后
┌─────────────────────────────────────────┐
│ Temperature: [0.7 ▼]                   │
├─────────────────────────────────────────┤
│  > 0.0                                 │
│    0.3                                 │
│    0.5                                 │
│    0.7                                 │
│    1.0                                 │
│    1.5                                 │
│    2.0                                 │
└─────────────────────────────────────────┘
```

#### 3.2.2 开关控件 (Toggle)
```
┌─────────────────────────────────────────┐
│  [×] 启用记忆系统                        │
│  [ ] 启用 Context 压缩                   │
└─────────────────────────────────────────┘
```

#### 3.2.3 滑块控件 (Slider)
```
┌─────────────────────────────────────────┐
│  Context Window                        │
│  [━━━━━━━●━━━━━━━━━] 128000           │
│  最小: 1K          最大: 1M            │
└─────────────────────────────────────────┘
```

#### 3.2.4 数字输入控件 (NumberInput)
```
┌─────────────────────────────────────────┐
│  Max Tokens: [4096]  ▲▼               │
└─────────────────────────────────────────┘
```

#### 3.2.5 密码输入控件 (PasswordInput)
```
┌─────────────────────────────────────────┐
│  API Key: [••••••••••••••••] [👁 显示] │
└─────────────────────────────────────────┘
```

#### 3.2.6 文本输入控件 (TextInput)
```
┌─────────────────────────────────────────┐
│  Base URL: [https://api.example.com]   │
└─────────────────────────────────────────┘
```

### 3.3 键盘操作

| 按键 | 操作 |
|------|------|
| `↑` / `k` | 上移选择项 |
| `↓` / `j` | 下移选择项 |
| `←` / `h` | 切换到左侧分类列表 |
| `→` / `l` | 切换到右侧设置内容 |
| `Tab` | 切换分类（循环） |
| `Space` / `Enter` | 切换开关 / 打开下拉 / 确认输入 |
| `Esc` / `q` | 关闭设置界面 |
| `r` | 重置当前分类为默认值 |
| `s` | 保存所有更改并关闭 |
| `?` | 显示帮助 |

---

## 四、技术实现

### 4.1 文件结构

```
tui/
├── views/
│   ├── settings_screen.py      # 设置界面主屏幕
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── models.py           # Pydantic 数据模型
│   │   ├── manager.py           # 设置管理器
│   │   └── widgets.py          # 自定义控件
│   └── __init__.py
└── ...
```

### 4.2 数据模型

```python
# tui/views/settings/models.py

from pydantic import BaseModel, Field
from typing import Optional, Literal
from enum import Enum

class Language(str, Enum):
    ZH = "zh"
    EN = "en"

class ExplanationDepth(str, Enum):
    BRIEF = "brief"
    MODERATE = "moderate"
    DETAILED = "detailed"

class ResponseFormat(str, Enum):
    MARKDOWN = "markdown"
    PLAIN = "plain"

class IntentMode(str, Enum):
    LLM = "llm"
    HYBRID = "hybrid"
    KEYWORD = "keyword"

class SessionResetMode(str, Enum):
    BOTH = "both"
    DAILY = "daily"
    IDLE = "idle"
    NONE = "none"

class TerminalBackend(str, Enum):
    LOCAL = "local"
    DOCKER = "docker"

class DisplaySettings(BaseModel):
    """显示设置"""
    language: Language = Language.ZH

class LLMProvider(BaseModel):
    """LLM Provider (不存储敏感信息)"""
    provider: str = ""
    model: str = ""
    base_url: str = ""

class ModelParameters(BaseModel):
    """模型参数"""
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1, le=32000)
    context_window: int = Field(default=128000, ge=1000, le=1000000)

class AgentSettings(BaseModel):
    """Agent 设置"""
    max_iterations: int = Field(default=10, ge=1, le=100)
    timeout_seconds: float = Field(default=60.0, ge=1.0, le=600.0)

class TerminalSettings(BaseModel):
    """终端设置"""
    backend: TerminalBackend = TerminalBackend.LOCAL

class SessionSettings(BaseModel):
    """会话设置"""
    reset_mode: SessionResetMode = SessionResetMode.BOTH
    memory_enabled: bool = False
    compression_enabled: bool = True

class IntentSettings(BaseModel):
    """意图识别设置"""
    mode: IntentMode = IntentMode.LLM

class ResponsePreferences(BaseModel):
    """响应偏好"""
    explanation_depth: ExplanationDepth = ExplanationDepth.DETAILED
    response_format: ResponseFormat = ResponseFormat.MARKDOWN
    enable_caching: bool = True

class ToolSettings(BaseModel):
    """工具设置"""
    stt_enabled: bool = False
    tts_enabled: bool = False
    browser_enabled: bool = False
    web_debug: bool = False
    vision_debug: bool = False

class LoggingSettings(BaseModel):
    """日志设置"""
    file_enabled: bool = False

class SettingsDocument(BaseModel):
    """完整设置文档"""
    display: DisplaySettings = DisplaySettings()
    llm: LLMProvider = LLMProvider()
    model: ModelParameters = ModelParameters()
    agent: AgentSettings = AgentSettings()
    terminal: TerminalSettings = TerminalSettings()
    session: SessionSettings = SessionSettings()
    intent: IntentSettings = IntentSettings()
    preferences: ResponsePreferences = ResponsePreferences()
    tools: ToolSettings = ToolSettings()
    logging: LoggingSettings = LoggingSettings()
```

### 4.3 设置管理器

```python
# tui/views/settings/manager.py

class SettingsManager:
    """设置管理器 - 单例模式"""

    _instance: Optional["SettingsManager"] = None

    def __init__(self):
        self._settings: SettingsDocument = SettingsDocument()
        self._listeners: list[callable] = []
        self._dirty: bool = False
        self._load()

    @classmethod
    def get_instance(cls) -> "SettingsManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _get_config_path(self) -> Path:
        """获取配置文件路径"""
        config_dir = Path.home() / ".handsome_agent"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "tui_settings.json"

    def _load(self) -> None:
        """从文件加载设置"""
        path = self._get_config_path()
        if path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                    self._settings = SettingsDocument(**data)
            except Exception:
                pass

    def save(self) -> None:
        """保存设置到文件"""
        path = self._get_config_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._settings.model_dump(), f, indent=2, ensure_ascii=False)
        self._dirty = False
        self._notify_listeners()

    def get_settings(self) -> SettingsDocument:
        """获取当前设置"""
        return self._settings

    def update(self, **kwargs) -> None:
        """更新设置"""
        for key, value in kwargs.items():
            if hasattr(self._settings, key):
                setattr(self._settings, key, value)
        self._dirty = True
        self._notify_listeners()

    def add_listener(self, callback: callable) -> None:
        """添加设置变更监听器"""
        self._listeners.append(callback)

    def remove_listener(self, callback: callable) -> None:
        """移除设置变更监听器"""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self) -> None:
        """通知所有监听器"""
        for listener in self._listeners:
            try:
                listener(self._settings)
            except Exception:
                pass

    def reset_to_defaults(self) -> None:
        """重置所有设置为默认值"""
        self._settings = SettingsDocument()
        self._dirty = True
```

### 4.4 设置界面实现

```python
# tui/views/settings_screen.py

class SettingsScreen(ModalScreen):
    """TUI 设置界面模态窗口"""

    CSS = """
    SettingsScreen {
        align: center middle;
    }

    #settings-container {
        width: 90%;
        height: 90%;
        border: solid $primary;
        background: $surface;
    }

    #sidebar {
        width: 25%;
        height: 100%;
        background: $panel;
        border-right: solid $border;
    }

    #content {
        width: 75%;
        height: 100%;
    }

    .setting-item {
        height: auto;
        padding: 1 2;
        border-bottom: solid $border;
    }

    .setting-item:focus {
        background: $accent 15%;
    }

    .category-item {
        padding: 1 2;
        color: $text-muted;
    }

    .category-item:focus,
    .category-item.active {
        background: $accent 15%;
        color: $accent;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "关闭", show=False),
        Binding("q", "close", "关闭", show=False),
        Binding("tab", "next_category", "下一分类", show=False),
        Binding("shift+tab", "prev_category", "上一分类", show=False),
        Binding("s", "save_and_close", "保存", show=False),
        Binding("r", "reset_category", "重置", show=False),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._settings_manager = SettingsManager.get_instance()
        self._current_category: str = "language"
        self._current_item_index: int = 0
        self._focus_area: str = "sidebar"  # sidebar | content

    def compose(self) -> ComposeResult:
        with Container(id="settings-container"):
            with Container(id="sidebar"):
                yield from self._compose_sidebar()
            with Container(id="content"):
                yield from self._compose_content()

    def _compose_sidebar(self) -> ComposeResult:
        """生成侧边栏分类列表"""
        categories = [
            ("language", "🌐", "语言"),
            ("llm", "🤖", "大模型"),
            ("model", "🔧", "模型参数"),
            ("terminal", "💻", "终端"),
            ("agent", "⚙️", "Agent"),
            ("session", "🔄", "会话"),
            ("intent", "🧠", "意图识别"),
            ("preferences", "📝", "响应偏好"),
            ("tools", "🛠️", "工具"),
            ("logging", "📄", "日志"),
            ("about", "ℹ️", "关于"),
        ]

        for cat_id, icon, name in categories:
            yield Static(
                f"{icon} {name}",
                id=f"cat-{cat_id}",
                classes="category-item"
            )

    def _compose_content(self) -> ComposeResult:
        """生成设置内容区"""
        settings = self._settings_manager.get_settings()

        with ScrollableContainer(id="settings-content"):
            yield from self._get_category_items(self._current_category, settings)

    def _get_category_items(self, category: str, settings: SettingsDocument) -> list:
        """获取指定分类的设置项"""
        # 根据分类返回对应的设置项组件
        ...

    def action_close(self) -> None:
        """关闭设置界面"""
        self.dismiss()

    def action_save_and_close(self) -> None:
        """保存并关闭"""
        self._settings_manager.save()
        self.dismiss()

    def action_next_category(self) -> None:
        """切换到下一个分类"""
        categories = ["language", "llm", "model", "terminal", "agent",
                     "session", "intent", "preferences", "tools", "logging", "about"]
        idx = categories.index(self._current_category)
        self._current_category = categories[(idx + 1) % len(categories)]
        self._refresh_content()
```

---

## 五、与 CLI 的集成

### 5.1 共享配置存储

TUI 设置界面与 CLI 共享同一配置文件 `~/.handsome_agent/config.json`，通过 `cli/config/config.py` 的 `load_config()` 和 `set_config_value()` 操作。

```python
# 设置界面保存时同步到 CLI 配置
def sync_to_cli_config(settings: SettingsDocument) -> None:
    """将 TUI 设置同步到 CLI 配置"""
    from cli.config.config import set_config_value

    # 映射 TUI 设置到 CLI 配置
    mappings = {
        "display.language": ("display.language", settings.display.language),
        "model.temperature": ("model.temperature", settings.model.temperature),
        # ... 其他映射
    }

    for tui_key, (cli_key, value) in mappings.items():
        set_config_value(cli_key, value)
```

### 5.2 快捷键入口

| 入口 | 快捷键 | 说明 |
|------|--------|------|
| 主界面 | `Ctrl+,` | 打开设置 |
| 命令面板 | `/settings` | 打开设置 |
| 欢迎界面 | "设置" 按钮 | 打开设置 |

---

## 六、验收标准

### 6.1 功能验收

- [ ] 所有设置项均可编辑
- [ ] 设置修改后立即生效
- [ ] 关闭设置界面时提示保存
- [ ] 所有键盘快捷键正常工作

### 6.2 界面验收

- [ ] 分类列表清晰可区分
- [ ] 当前选中项有视觉反馈
- [ ] 下拉菜单可正常展开/收起
- [ ] 开关状态正确显示

### 6.3 数据验收

- [ ] 设置保存到 `~/.handsome_agent/tui_settings.json`
- [ ] 设置同步到 CLI 配置
- [ ] 重启后设置正确恢复
- [ ] 重置功能正常工作

---

## 七、附录

### 7.1 配置字段映射表

| TUI 设置键 | CLI 配置键 | 说明 |
|-----------|-----------|------|
| `display.language` | `display.language` | 显示语言 |
| `llm.provider` | `llm.provider` | LLM 提供商 |
| `llm.model` | `llm.model` | 模型名称 |
| `model.temperature` | `model.temperature` | 温度参数 |
| `model.max_tokens` | `model.max_tokens` | 最大 token |
| `model.context_window` | `model.context_window` | 上下文窗口 |
| `terminal.backend` | `terminal.backend` | 终端后端 |
| `agent.max_iterations` | `agent.max_iterations` | 最大迭代 |
| `agent.timeout_seconds` | `agent.timeout_seconds` | 超时时间 |
| `session.reset_mode` | `session_reset.mode` | 重置模式 |
| `session.memory_enabled` | `memory.enabled` | 记忆系统 |
| `session.compression_enabled` | `compression.enabled` | 压缩 |
| `intent.mode` | `intent_mode` | 意图模式 |
| `preferences.explanation_depth` | `preferences.explanation_depth` | 详细程度 |
| `preferences.response_format` | `preferences.response_format` | 响应格式 |
| `preferences.enable_caching` | `preferences.enable_caching` | 缓存 |
| `tools.stt_enabled` | `stt.enabled` | STT |
| `tools.tts_enabled` | `tts.enabled` | TTS |
| `tools.browser_enabled` | `browser.enabled` | Browser |
| `tools.web_debug` | `debug_tools.web_tools` | Web Debug |
| `tools.vision_debug` | `debug_tools.vision_tools` | Vision Debug |
| `logging.file_enabled` | `logging.file_enabled` | 文件日志 |

### 7.2 参考实现

- **CodeWhale**: `E:/CodeWhale-study/crates/tui/src/settings.rs`
- **CLI Setup**: `cli/setup/setup_wizard.py`
- **配置管理**: `cli/config/config.py`
