# Tool Extension Guide - 工具扩展指南

> 🏃 Execution - 🛠️ ToolExec - 用户自定义工具扩展

---

## 概述

Handsome Agent 支持用户自定义工具扩展，允许用户添加自己的工具供 Agent 调用。

## 扩展方式

### 方式一：装饰器注册（推荐）

最简单的扩展方式，使用 `@register_tool` 装饰器：

```python
from tools import register_tool, ToolResult

@register_tool(
    name="my_custom_tool",
    description="这是一个自定义工具的描述",
    parameters=[
        {"name": "param1", "type": "string", "required": True, "description": "参数1描述"},
        {"name": "param2", "type": "integer", "required": False, "description": "参数2描述"}
    ],
    category="custom",  # 可选：工具分类
    examples=["示例输入"]  # 可选：使用示例
)
def my_custom_tool(param1: str, param2: int = 0) -> ToolResult:
    """工具函数文档"""
    try:
        # 工具逻辑
        result = f"处理了 {param1}"
        return ToolResult(success=True, output=result)
    except Exception as e:
        return ToolResult(success=False, output="", error=str(e))
```

### 方式二：直接注册

```python
from tools.registry import registry

def my_handler(parameters: dict, context: dict = None) -> dict:
    """处理函数"""
    return {"result": "success"}

registry.register(
    name="another_tool",
    description="另一个自定义工具",
    handler=my_handler,
    schema={
        "description": "工具描述",
        "parameters": {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "参数1"}
            },
            "required": ["param1"]
        }
    },
    toolset="custom"  # 工具集分类
)
```

---

## 注册位置

### 内置工具

内置工具位于 `tools/` 目录：

```
tools/
├── file_tools.py      # 文件操作
├── terminal_tools.py   # 终端命令
├── web_tools.py        # Web 操作
├── memory_tool.py      # 记忆管理
├── skill_manager_tool.py  # 技能管理
└── ...
```

### 用户自定义工具

用户自定义工具放在用户配置目录：

```
~/.handsome_agent/
├── tools/             # 用户自定义工具目录
│   ├── __init__.py
│   ├── my_tools.py
│   └── custom_tools.py
├── agent.md           # Agent 身份定义
├── capabilities.md    # 能力定义
└── user.md            # 用户信息
```

---

## 工具结构

### ToolResult 返回格式

```python
from tools import ToolResult

# 成功返回
ToolResult(success=True, output="处理结果")

# 失败返回
ToolResult(success=False, output="", error="错误信息")

# 带元数据的返回
ToolResult(
    success=True,
    output="结果",
    metadata={"key": "value"}
)
```

### 工具定义结构

```python
{
    "name": "tool_name",           # 工具名称（唯一）
    "description": "工具描述",      # 供 LLM 理解的描述
    "parameters": [                # 参数定义
        {
            "name": "param_name",   # 参数名
            "type": "string",       # 类型：string/integer/boolean/array/object
            "required": True,       # 是否必需
            "description": "描述"   # 参数描述
        }
    ],
    "category": "custom",          # 分类
    "examples": ["example1"]        # 示例（可选）
}
```

---

## 分类规范

| 分类 | 说明 | 示例 |
|------|------|------|
| `file` | 文件操作 | read_file, write_file |
| `terminal` | 终端命令 | terminal, run_command |
| `web` | Web 操作 | web_search, web_fetch |
| `memory` | 记忆管理 | memory |
| `skill` | 技能管理 | skill_manage |
| `code` | 代码相关 | code_analysis |
| `calendar` | 日历相关 | calendar_event |
| `custom` | 用户自定义 | 用户自己的工具 |

---

## 工具标识（Emoji）

为便于识别，建议为工具添加 Emoji 标识：

### 格式规范

```
🔧=类型图标 工具名
例如: 🔧=📁 read_file, 🔧=🌐 web_search
```

### 类型图标

| 分类 | Emoji | 说明 |
|------|-------|------|
| `file` | 📁 | 文件操作 |
| `terminal` | 🖥️ | 终端命令 |
| `web` | 🌐 | Web 操作 |
| `memory` | 💾 | 记忆管理 |
| `skill` | 📋 | 技能管理 |
| `code` | 💻 | 代码相关 |
| `calendar` | 📅 | 日历相关 |
| `custom` | 🔧 | 用户自定义 |

### 日志显示示例

```
INFO - 🏃 [Execution] - [/🛠️ToolExec] - (LLMToolSelector) Executing tool: (🔧·📁)read_file
INFO - 🏃 [Execution] - [/🛠️ToolExec] - (LLMToolSelector) Executing tool: (🔧·🌐)web_search
INFO - 🏃 [Execution] - [/🛠️ToolExec] - (LLMToolSelector) Executing tool: (🔧·💾)memory
```

在 `register_tool()` 中指定：
```python
engine.register_tool(
    name="my_tool",
    description="...",
    emoji="📁"  # 类型图标，外部会自动加上 (🔧·)
)
```

---

## 日志集成

### 日志输出位置

工具执行时，日志会显示在以下位置：

```
INFO - 🏃 [Execution] - [/🛠️ToolExec] - (MyTool) Tool execution started: my_tool
INFO - 🏃 [Execution] - [/🛠️ToolExec] - (MyTool) Tool execution completed: my_tool (0.5s)
```

### 日志格式

工具日志包含：
- **层标识**: 🏃 [Execution]
- **子层标识**: [/🛠️ToolExec]
- **模块名**: (MyTool)
- **消息**: 工具执行信息

### 添加自定义日志

```python
from common.logging_manager import get_execution_logger

logger = get_execution_logger(__name__, sublayer="tool_exec")

def my_tool(param: str):
    logger.info(f"Starting my_tool with param={param}")
    try:
        result = do_something(param)
        logger.info(f"my_tool completed successfully")
        return ToolResult(success=True, output=result)
    except Exception as e:
        logger.error(f"my_tool failed: {e}")
        return ToolResult(success=False, output="", error=str(e))
```

---

## 完整示例

### 示例 1：简单工具

```python
from tools import register_tool, ToolResult

@register_tool(
    name="greet_user",
    description="向用户发送问候语",
    parameters=[
        {"name": "name", "type": "string", "required": False, "description": "用户名"}
    ]
)
def greet_user(name: str = "朋友") -> ToolResult:
    """生成问候语"""
    return ToolResult(success=True, output=f"你好，{name}！有什么我可以帮你的吗？")
```

### 示例 2：异步工具

```python
import asyncio
from tools import register_tool, ToolResult

@register_tool(
    name="async_task",
    description="执行异步任务",
    parameters=[
        {"name": "task_id", "type": "string", "required": True, "description": "任务ID"}
    ]
)
async def async_task(task_id: str) -> ToolResult:
    """异步任务处理"""
    await asyncio.sleep(0.1)  # 模拟异步操作
    return ToolResult(success=True, output=f"任务 {task_id} 已完成")
```

### 示例 3：带环境检查的工具

```python
import os
from tools.registry import registry

def check_api_key():
    """检查 API 密钥是否存在"""
    return os.getenv("MY_API_KEY") is not None

def api_call_handler(parameters: dict, context: dict = None):
    """API 调用处理"""
    api_key = os.getenv("MY_API_KEY")
    return {"result": f"使用 {api_key[:8]}... 调用 API"}

registry.register(
    name="api_call",
    description="调用外部 API",
    handler=api_call_handler,
    check_fn=check_api_key,  # 可用性检查函数
    schema={
        "description": "调用外部 API 获取数据",
        "parameters": {
            "type": "object",
            "properties": {
                "endpoint": {"type": "string", "description": "API 端点"}
            },
            "required": ["endpoint"]
        }
    }
)
```

---

## 调试技巧

### 1. 查看已注册工具

```python
from tools.registry import registry

# 列出所有工具
for name, entry in registry._tools.items():
    print(f"{entry.emoji or '🔧'} {name}: {entry.description}")

# 查看特定工具的 schema
schema = registry._tools["my_tool"].get_schema()
print(schema)
```

### 2. 检查工具可用性

```python
from tools.registry import registry

tool = registry._tools.get("my_tool")
if tool:
    available = tool.is_available()
    print(f"工具可用: {available}")
```

### 3. 测试工具执行

```python
from tools.registry import registry

# 直接执行工具
result = registry._tools["my_tool"].handler({"param1": "value"})
print(result)
```

---

## 常见问题

### Q: 工具注册后不生效？

检查：
1. 文件是否在正确的目录
2. 导入是否成功（运行 `python -c "import tools.my_tools"`）
3. 装饰器是否正确使用

### Q: 如何让工具只对特定用户可用？

```python
def check_user():
    return os.getenv("CURRENT_USER") == "admin"

registry.register(
    name="admin_tool",
    description="管理员专用工具",
    handler=admin_handler,
    check_fn=check_user
)
```

### Q: 如何传递额外上下文？

工具接收 `context` 参数：

```python
def my_tool(parameters: dict, context: dict = None):
    user_id = context.get("user_id") if context else None
    session_id = context.get("session_id") if context else None
    # 使用上下文信息
```

---

## 相关文档

- [Tools Module](../modules/tools/README.md) - 工具模块说明
- [Context Assembly](./context-assembly.md) - 上下文拼装
- [LLM Tool Selection](../architecture/llm-tool-selection.md) - LLM 工具选择