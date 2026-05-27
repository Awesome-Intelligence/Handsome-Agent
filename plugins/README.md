# Plugins Module - 插件系统模块

## 📋 概述

插件系统模块提供可扩展的插件机制，允许动态加载和管理功能扩展，支持记忆管理、上下文引擎等插件。

## 🏗️ 架构设计

### 模块结构

```
plugins/
├── __init__.py
├── base_plugin.py      # 插件基类
├── plugin_manager.py   # 插件管理器
├── hook_manager.py     # 钩子管理器
├── memory/             # 记忆插件
│   └── __init__.py
├── context_engine/     # 上下文引擎插件
│   └── __init__.py
└── ...                 # 其他插件
```

## 🧩 核心组件

### 1. BasePlugin

**职责**: 插件基类，定义插件接口。

**必须实现的方法**:
- `get_info()` - 返回插件信息
- `initialize(context)` - 初始化插件
- `register_tools(tool_registry)` - 注册工具
- `register_hooks(hook_manager)` - 注册钩子

### 2. PluginManager

**职责**: 管理插件的加载、初始化和生命周期。

**处理流程**:

```
启动 → 扫描插件目录 → 加载插件 → 初始化插件 → 注册工具/钩子
          │              │            │
          ▼              ▼            ▼
      目录遍历        模块导入      上下文注入
```

**关键方法**:
- `load_plugin(module_path)` - 加载单个插件
- `load_plugins_from_directory(directory)` - 加载目录下所有插件
- `initialize_plugins(context)` - 初始化所有插件
- `register_plugin_tools(tool_registry)` - 注册插件工具
- `register_plugin_hooks()` - 注册插件钩子

### 3. HookManager

**职责**: 管理钩子和钩子回调，允许插件拦截和修改 Agent 行为。

**支持的钩子**:

| 钩子名称 | 触发时机 | 用途 |
|----------|----------|------|
| `agent_initialized` | Agent 初始化完成 | 初始化插件资源 |
| `before_prompt_build` | Prompt 构建前 | 修改 Prompt |
| `after_prompt_build` | Prompt 构建后 | 后处理 Prompt |
| `before_llm_call` | LLM 调用前 | 修改请求参数 |
| `after_llm_call` | LLM 调用后 | 处理响应 |
| `before_tool_call` | 工具调用前 | 修改工具参数 |
| `after_tool_call` | 工具调用后 | 处理工具结果 |
| `message_received` | 收到消息时 | 记录或修改消息 |
| `response_generated` | 响应生成后 | 修改响应 |
| `session_started` | 会话开始时 | 初始化会话状态 |
| `session_ended` | 会话结束时 | 清理资源 |

## 🔄 插件加载流程

```
┌────────────────────────────────────────────────────────────────────┐
│                    启动插件管理器                                   │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│  PluginManager 扫描插件目录                                         │
│  • 遍历 plugins/ 目录                                              │
│  • 识别插件包（包含 __init__.py 的目录）                            │
│  • 识别插件模块（.py 文件）                                        │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│  加载插件模块                                                       │
│  • 导入模块                                                        │
│  • 查找 BasePlugin 子类                                            │
│  • 实例化插件对象                                                   │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│  初始化插件                                                         │
│  • 调用 plugin.initialize(context)                                 │
│  • 注入上下文依赖                                                  │
│  • 注册工具和钩子                                                  │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│                    插件就绪，等待调用                               │
└────────────────────────────────────────────────────────────────────┘
```

## 📊 内置插件

### 1. MemoryPlugin

**职责**: 提供记忆管理能力。

**功能**:
- 存储长期记忆
- 检索相关记忆
- 记忆反思和提炼

### 2. ContextEnginePlugin

**职责**: 提供上下文管理和压缩能力。

**功能**:
- 上下文压缩
- 消息重要性分析
- 智能截断

## 🎯 创建自定义插件

```python
from plugins import BasePlugin, PluginInfo, HookNames

class MyPlugin(BasePlugin):
    def __init__(self):
        self.data = None
    
    def get_info(self) -> PluginInfo:
        return PluginInfo(
            id="my_plugin",
            name="My Plugin",
            description="A custom plugin",
            version="1.0.0",
            author="Author",
            module_path="plugins.my_plugin"
        )
    
    def initialize(self, context: dict):
        self.data = context.get("data", {})
    
    def register_tools(self, tool_registry):
        # 注册自定义工具
        pass
    
    def register_hooks(self, hook_manager):
        # 注册钩子
        hook_manager.register_hook(
            HookNames.MESSAGE_RECEIVED,
            self._on_message_received,
            priority=10
        )
    
    def _on_message_received(self, **kwargs):
        message = kwargs.get("message")
        # 处理消息
        pass
```

## 📋 插件信息结构

```python
@dataclass
class PluginInfo:
    id: str                    # 插件唯一标识
    name: str                  # 插件名称
    description: str           # 插件描述
    version: str               # 版本号
    author: str                # 作者
    module_path: str           # 模块路径
    enabled: bool = True       # 是否启用
```

## 🔓 开源替代方案

### 1. 插件系统

| 方案 | 描述 | 适用场景 | GitHub |
|------|------|----------|--------|
| **pluggy** | 轻量级插件系统 | 动态加载 | [pluggy-dev/pluggy](https://github.com/pluggy-dev/pluggy) |
| **stevedore** | 插件管理器 | OpenStack 风格 | [openstack/stevedore](https://github.com/openstack/stevedore) |
| **entrypoints** | 入口点发现 | 包发现 | [gwaxe/entrypoints](https://github.com/gwaxe/entrypoints) |
| **importlib-metadata** | 元数据访问 | 包元数据 | [Python 内置](https://docs.python.org/3/library/importlib.metadata.html) |

### 2. 记忆插件

| 方案 | 描述 | 适用场景 | GitHub |
|------|------|----------|--------|
| **MemGPT** | 分层记忆 | 长期记忆 | [cg123/memgpt](https://github.com/cg123/memgpt) |
| **Mem0** | 开发者记忆 API | 嵌入记忆 | [mem0ai/mem0](https://github.com/mem0ai/mem0) |
| **Letta** | 有状态 Agent | 持久化记忆 | [letta-ai/letta](https://github.com/letta-ai/letta) |

### 3. 上下文引擎插件

| 方案 | 描述 | 适用场景 | GitHub |
|------|------|----------|--------|
| **LangChain LCEL** | 链式调用 | 自定义管道 | [langchain-ai/langchain](https://github.com/langchain-ai/langchain) |
| **Haystack** | 管道框架 | NLP 管道 | [deepset-ai/haystack](https://github.com/deepset-ai/haystack) |
| **Ray** | 并行计算 | 分布式管道 | [ray-project/ray](https://github.com/ray-project/ray) |

### 4. 钩子系统

| 方案 | 描述 | 适用场景 | GitHub |
|------|------|----------|--------|
| **FastAPI Middleware** | 中间件钩子 | Web 请求 | [tiangolo/fastapi](https://github.com/tiangolo/fastapi) |
| **Django Signals** | 信号钩子 | Web 事件 | [django/django](https://github.com/django/django) |
| **Blinker** | 信号系统 | 事件发布 | [pytest-dev/blinker](https://github.com/pytest-dev/blinker) |
| **Hooky** | 轻量级钩子 | 装饰器钩子 | [tibordp/hooky](https://github.com/tibordp/hooky) |

### 5. 可观测性

| 方案 | 描述 | 适用场景 | GitHub |
|------|------|----------|--------|
| **OpenTelemetry** | 分布式追踪 | 可观测性 | [open-telemetry/opentelemetry-python](https://github.com/open-telemetry/opentelemetry-python) |
| **LangSmith** | LLM 追踪 | 应用追踪 | [langchain-ai/langsmith-sdk](https://github.com/langchain-ai/langsmith-sdk) |
| **Phoenix** | ML 可视化 | 模型分析 | [Arize-ai/phoenix](https://github.com/Arize-ai/phoenix) |

## 🔧 替换指南

### 使用 pluggy 替换自定义插件系统

```python
# 当前实现
from plugins.base_plugin import BasePlugin
from plugins.plugin_manager import PluginManager

manager = PluginManager()
manager.load_plugins_from_directory("plugins/")

# pluggy 替代
import pluggy

hook_spec = pluggy.HookspecMarker("myplugin")
hookimpl = pluggy.HookimplMarker("myplugin")

@hook_spec
class MyPlugin:
    @hookimpl
    def process(self, data):
        return data
```

### 使用 Blinker 信号系统

```python
# 当前实现
from plugins.hook_manager import HookManager
hook_manager = HookManager()
hook_manager.register_hook("message_received", handler)

# Blinker 替代
from blinker import signal
message_received = signal("message_received")
message_received.connect(handler)
message_received.send(sender=self, message=msg)
```

## 📚 进一步阅读

- [pluggy Documentation](https://pluggy.readthedocs.io)
- [MemGPT Documentation](https://memgpt.readthedocs.io)
- [Blinker Documentation](https://pythonhosted.org/blinker)
- [OpenTelemetry Python](https://opentelemetry.io/docs/python)
