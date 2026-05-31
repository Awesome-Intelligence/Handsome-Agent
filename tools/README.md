# Tools Module - 工具系统模块

## 📋 概述

工具系统模块提供各种实用工具，支持文件操作、终端命令、网络搜索、代码执行、记忆管理等功能，使 Agent 能够与外部环境交互。

**在架构中的位置**: Tool Abstraction Layer（工具抽象层），为 LLM Intent Recognition 提供执行能力。

## 🏛️ Hermes 风格架构 - Tool Layer

```
┌─────────────────────────────────────────────────────────────┐
│          Hermes-style Architecture - Tool Layer            │
├─────────────────────────────────────────────────────────────┤
│  1. Intent Recognition (LLM-powered)                      │
│     llm_intent_service.py                                  │
├─────────────────────────────────────────────────────────────┤
│  2. 🛠️ Tool Abstraction Layer ← YOU ARE HERE              │
│     ToolRegistry │ SkillManager │ Tools                   │
├─────────────────────────────────────────────────────────────┤
│  3. LLM Provider Layer                                     │
│     Adapter Pattern │ 25+ Providers                        │
└─────────────────────────────────────────────────────────────┘
```

## 🏗️ 架构设计

### 模块结构

```
tools/
├── __init__.py              # 包入口，导出所有工具
├── registry.py              # 工具注册表（参考 Hermes）
├── schema_registry.py       # Schema 注册表
├── file_tools.py           # 文件操作工具
├── terminal_tools.py       # 终端命令工具
├── web_tools.py           # 网络搜索工具
├── code_tools.py          # 代码执行工具
├── memory_tool.py         # 记忆工具 ✨ 新增
├── skill_manager_tool.py  # 技能管理工具 ✨ 新增
├── approval_tool.py       # 审批工具 ✨ 新增
├── delegate_tool.py       # 代理工具 ✨ 新增
├── vision_tool.py         # 视觉工具 ✨ 新增
├── mcp_tool.py            # MCP 工具 ✨ 新增
├── kanban_tool.py         # 看板工具 ✨ 新增
├── cronjob_tool.py       # 定时任务工具 ✨ 新增
├── tool_calling.py        # 工具调用
├── definitions/           # 工具定义
│   ├── __init__.py
│   ├── file_tools.py
│   ├── shell_tools.py
│   ├── web_tools.py
│   ├── code_tools.py
│   ├── browser_tools.py
│   ├── multimedia_tools.py
│   └── task_tools.py
└── adapters/              # 工具适配器
    ├── __init__.py
    ├── hermes_adapter.py
    └── openclaw_adapter.py
```

## 🧩 工具列表

### 核心工具（已实现）

| 类别 | 工具 | 功能 | 状态 |
|------|------|------|------|
| **文件操作** | FileTools | 读写文件、目录操作 | ✅ |
| **终端命令** | TerminalTools | 执行系统命令 | ✅ |
| **网络工具** | WebTools | 搜索、抓取网页 | ✅ |
| **代码工具** | CodeTools | 代码分析、格式化 | ✅ |
| **浏览器** | BrowserTools | 浏览器自动化 | ✅ |
| **多媒体** | MultimediaTools | 图像生成、TTS | ✅ |
| **任务工具** | TaskTools | Todo 列表管理 | ✅ |

### 新增工具（参考 Hermes）

| 类别 | 工具 | 功能 | 状态 |
|------|------|------|------|
| **记忆工具** | MemoryTool | 记忆存储和检索 | 📝 框架已创建 |
| **技能管理** | SkillManagerTool | 技能注册和执行 | 📝 框架已创建 |
| **审批工具** | ApprovalTool | 操作审批 | 📝 框架已创建 |
| **代理工具** | DelegateTool | 子任务代理 | 📝 框架已创建 |
| **视觉工具** | VisionTool | 图像分析和 OCR | 📝 框架已创建 |
| **MCP 工具** | MCPTool | MCP 协议集成 | 📝 框架已创建 |
| **看板工具** | KanbanTool | 看板任务管理 | 📝 框架已创建 |
| **定时任务** | CronjobTool | 定时任务调度 | 📝 框架已创建 |

## 🏛️ ToolRegistry 架构

参考 Hermes Agent 的 registry.py 实现：

```python
from tools.registry import registry, ToolEntry, discover_builtin_tools

# 获取所有已注册工具
tools = registry.get_all_tools()

# 获取工具定义（用于 LLM）
definitions = registry.get_definitions()

# 执行工具
result = await registry.execute("tool_name", parameters)

# 获取统计信息
stats = registry.get_stats()
print(stats)
# {
#     "total_tools": 15,
#     "available_tools": 15,
#     "toolsets": ["file", "terminal", "web", ...],
#     "by_toolset": {...}
# }
```

### ToolEntry 结构

```python
@dataclass
class ToolEntry:
    name: str                    # 工具名称
    toolset: str               # 工具集分类
    schema: Dict[str, Any]      # 工具参数模式
    handler: Callable           # 处理函数
    check_fn: Optional[Callable]  # 可用性检查函数
    requires_env: List[str]     # 环境变量要求
    is_async: bool             # 是否异步
    description: str            # 工具描述
    emoji: str                 # 表情图标
    max_result_size_chars: int  # 最大结果大小
```

### 工具注册

```python
# 在工具模块中注册
from tools.registry import registry

def check_terminal_requirements():
    """检查终端工具是否可用"""
    import shutil
    return shutil.which("bash") is not None

def terminal_handler(command: str, timeout: int = 30) -> str:
    """执行终端命令"""
    import subprocess
    result = subprocess.run(command, shell=True, capture_output=True, timeout=timeout)
    return result.stdout.decode()

registry.register(
    name="terminal",
    toolset="shell",
    schema={
        "command": {"type": "string", "description": "要执行的命令"},
        "timeout": {"type": "integer", "description": "超时时间（秒）"}
    },
    handler=terminal_handler,
    check_fn=check_terminal_requirements,
    is_async=False,
    description="Execute terminal commands",
    emoji="🖥️"
)
```

## 🔄 工具调用流程

```
┌────────────────────────────────────────────────────────────────────┐
│                    工具调用请求                                     │
└───────────────────────────────┬────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│  ToolRegistry (registry.py)                                        │
│  • 查找工具                                                        │
│  • 验证参数                                                        │
│  • 检查可用性（带缓存）                                            │
└───────────────────────────────┬────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│  具体工具执行                                                      │
│  • FileTools / TerminalTools / WebTools / CodeTools               │
│  • MemoryTool / SkillManagerTool / ApprovalTool                  │
│  • VisionTool / MCPTool / KanbanTool / CronjobTool               │
│  • 执行实际操作                                                     │
│  • 返回结果                                                        │
└───────────────────────────────┬────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│                    返回工具执行结果                                 │
└────────────────────────────────────────────────────────────────────┘
```

## 🎯 使用示例

### 基础使用

```python
from tools import get_all_tools, get_tool_by_name

# 获取所有工具
all_tools = get_all_tools()
print(f"可用工具数量: {len(all_tools)}")

# 获取单个工具
tool = get_tool_by_name("read_file")
print(f"工具定义: {tool}")
```

### 使用注册表

```python
from tools.registry import registry

# 获取工具定义（用于 LLM）
definitions = registry.get_definitions()
print(f"LLM 可用的工具定义: {definitions}")

# 执行工具
result = await registry.execute("read_file", {"file_path": "/tmp/test.txt"})
```

### 注册新工具

```python
from tools.registry import registry

def my_tool_handler(param1: str, param2: int) -> str:
    """自定义工具处理器"""
    return f"{param1} {param2}"

registry.register(
    name="my_tool",
    toolset="custom",
    schema={
        "param1": {"type": "string", "description": "参数1"},
        "param2": {"type": "integer", "description": "参数2"}
    },
    handler=my_tool_handler,
    is_async=False,
    description="这是一个自定义工具",
    emoji="🔧"
)
```

## 📊 工具分类

| 类别 | 工具 | 用途 |
|------|------|------|
| 文件操作 | FileTools | 读写文件、目录操作 |
| 终端命令 | TerminalTools | 执行系统命令 |
| 网络工具 | WebTools | 搜索、抓取网页 |
| 代码工具 | CodeTools | 代码分析、格式化 |
| 浏览器 | BrowserTools | 浏览器自动化 |
| 多媒体 | MultimediaTools | 图像生成、TTS |
| 任务工具 | TaskTools | Todo 列表管理 |
| 记忆管理 | MemoryTool | 记忆存储和检索 |
| 技能管理 | SkillManagerTool | 技能注册和执行 |
| 审批控制 | ApprovalTool | 操作审批 |
| 任务代理 | DelegateTool | 子任务代理 |
| 视觉处理 | VisionTool | 图像分析和 OCR |
| MCP 集成 | MCPTool | MCP 协议集成 |
| 看板管理 | KanbanTool | 看板任务管理 |
| 定时任务 | CronjobTool | 定时任务调度 |

## 🔒 安全考虑

- ✅ 命令执行有白名单限制
- ✅ 文件操作有路径限制
- ✅ 超时控制防止长时间运行
- ✅ 敏感信息过滤
- ✅ check_fn 缓存防止频繁检查
- ✅ 工具可用性验证

## 🔓 开源替代方案

| 场景 | 推荐库 | GitHub |
|------|--------|--------|
| HTTP 客户端 | `httpx` | [encode/httpx](https://github.com/encode/httpx) |
| 浏览器自动化 | `playwright` | [microsoft/playwright](https://github.com/microsoft/playwright) |
| 代码检查 | `ruff` | [astral-sh/ruff](https://github.com/astral-sh/ruff) |
| 系统信息 | `psutil` | [giampaolo/psutil](https://github.com/giampaolo/psutil) |

## 📚 参考

- [Hermes Agent Tools](https://github.com/...)
- [Awesome Python - 命令行工具](https://github.com/vinta/awesome-python)
- [Awesome Python - Web Scraping](https://github.com/pirati-cz/awesome-python-tools)
