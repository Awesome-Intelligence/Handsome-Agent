# Tools Specification - 工具使用规范

> **文件位置**: `agent/tools.md`  
> **用途**: 定义 Agent 可用的工具类型、使用规范和最佳实践  
> **灵感来源**: Hermes Agent Tools、OpenClaw Tool System

---

## 🛠️ 工具系统概述

工具系统是 Agent 执行任务的核心能力。通过统一的工具抽象，Agent 可以：

1. **扩展能力** - 通过工具调用执行各种操作
2. **标准化交互** - 统一工具调用接口
3. **安全执行** - 工具级别的权限和验证
4. **动态注册** - 运行时添加新工具

### 工具架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Tool System Architecture                   │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐  │
│  │  ToolRegistry (工具注册表)                            │  │
│  │  - 工具元数据管理                                      │  │
│  │  - 参数验证                                          │  │
│  │  - 权限控制                                          │  │
│  └─────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ File Tools   │  │ Terminal     │  │ Browser     │    │
│  │ 文件工具      │  │ Tools        │  │ Tools       │    │
│  │              │  │ 终端工具      │  │ 浏览器工具   │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ Web Tools    │  │ Code Tools   │  │ System      │    │
│  │ 网络工具      │  │ 代码工具      │  │ Tools       │    │
│  │              │  │              │  │ 系统工具     │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 工具分类

### 1. 浏览器工具 (Browser Tools)

**用途**: 控制浏览器进行网页访问和搜索

#### open_browser
```python
open_browser(
    browser_name: str = None,  # "chrome", "edge", "firefox", None=默认
    url: str = None            # 要访问的网址
)
```

**使用场景**:
- 打开浏览器访问特定网站
- 使用搜索引擎搜索信息
- 打开本地 HTML 文件

**示例**:
```
用户: 帮我打开百度
Agent: 调用 open_browser(url="https://www.baidu.com")

用户: 用 Chrome 打开 Google
Agent: 调用 open_browser(browser_name="chrome", url="https://www.google.com")
```

#### detect_browsers
```python
detect_browsers() -> List[str]
```

**用途**: 检测系统中已安装的浏览器

### 2. 终端工具 (Terminal Tools)

**用途**: 执行系统命令和操作

#### execute_terminal
```python
execute_terminal(
    command: str,              # 要执行的命令
    workdir: str = None,       # 工作目录
    timeout: int = 60,         # 超时时间（秒）
    shell: bool = True         # 是否使用 shell
)
```

**使用场景**:
- 执行系统命令
- 运行程序
- 获取系统信息

**示例**:
```
用户: 打开计算器
Agent: 调用 execute_terminal(command="start calc")

用户: 查看当前目录
Agent: 调用 execute_terminal(command="dir")
```

#### run_python
```python
run_python(
    code: str,                 # Python 代码
    timeout: int = 30
)
```

**用途**: 执行 Python 代码

### 3. 文件工具 (File Tools)

**用途**: 文件和目录操作

#### read_file
```python
read_file(
    path: str,                 # 文件路径
    encoding: str = "utf-8"
)
```

#### write_file
```python
write_file(
    path: str,                 # 文件路径
    content: str,              # 文件内容
    encoding: str = "utf-8",
    mode: str = "w"           # 写入模式
)
```

#### list_directory
```python
list_directory(
    path: str,                 # 目录路径
    recursive: bool = False
)
```

#### search_files
```python
search_files(
    directory: str,            # 搜索目录
    pattern: str,             # 搜索模式 (glob)
    recursive: bool = True
)
```

### 4. 网络工具 (Web Tools)

**用途**: 网络信息获取

#### web_search
```python
web_search(
    query: str,                # 搜索关键词
    engine: str = "baidu",    # 搜索引擎
    limit: int = 5
)
```

#### fetch_url
```python
fetch_url(
    url: str,                  # 网页 URL
    extract: str = "text"     # 提取内容类型
)
```

### 5. 代码工具 (Code Tools)

**用途**: 代码编写和分析

#### execute_code
```python
execute_code(
    code: str,                 # 代码
    language: str,             # 编程语言
    timeout: int = 30
)
```

#### analyze_code
```python
analyze_code(
    code: str,
    language: str
)
```

---

## 📋 工具使用规范

### 1. 工具调用原则

#### ✅ 正确做法

```python
# 1. 确认用户意图后再调用
用户: 打开浏览器
Agent: (确认意图) → 调用 open_browser()

# 2. 提供必要的参数
用户: 打开百度
Agent: 调用 open_browser(url="https://www.baidu.com")

# 3. 处理执行结果
Agent: 调用工具 → 获取结果 → 向用户报告
```

#### ❌ 错误做法

```python
# 1. 盲目调用
用户: 打开浏览器 (用户还没说去哪)
Agent: ❌ 调用 open_browser()  # 无参数调用

# 2. 忽略错误
用户: 打开不存在的程序
Agent: ❌ 调用 execute_terminal() → 失败但不报告

# 3. 过度调用
用户: 打开浏览器
Agent: ❌ 调用 open_browser() → 调用 detect_browsers() → 调用其他无关工具
```

### 2. 参数验证

#### 必须参数
```python
# 必须参数缺失时，向用户询问
用户: 打开浏览器
Agent: "好的，请问要访问哪个网址？"
```

#### 可选参数
```python
# 可选参数使用默认值
用户: 打开浏览器
Agent: 使用默认浏览器打开空白页
```

### 3. 错误处理

```python
# 工具执行失败时的处理
try:
    result = execute_terminal(command="invalid_command")
    if not result.success:
        # 向用户报告错误
        # 提供可能的解决方案
        # 建议替代方案
except Exception as e:
    # 报告异常情况
    # 记录错误日志
```

### 4. 工具调用链

```python
# 复杂任务可能需要多个工具调用
用户: 帮我打开浏览器，用百度搜索天气，然后打开桌面文件夹

Agent: 
  步骤 1: open_browser(url="https://www.baidu.com/s?wd=天气")
  步骤 2: execute_terminal(command="start explorer shell:desktop")
  报告: 已完成所有操作
```

---

## 🔒 安全规范

### 1. 危险命令禁止

```python
# 以下命令被禁止执行
DANGEROUS_COMMANDS = [
    "rm -rf /",           # 删除根目录
    "format",             # 格式化磁盘
    "del /f /s /q",      # 强制删除
    "shutdown",           # 关机 (需要确认)
    "net user",           # 用户管理 (需要确认)
]
```

### 2. 确认机制

```python
# 执行以下操作前必须确认
NEED_CONFIRMATION = [
    "删除文件",
    "格式化",
    "关机/重启",
    "安装软件",
    "修改系统设置"
]

用户: 删除 C 盘的文件
Agent: "这个操作可能会导致数据丢失，请确认是否继续？"
```

### 3. 权限限制

```python
# 不同权限级别的工具
TOOL_PERMISSIONS = {
    "read_file": "basic",      # 基础权限
    "write_file": "user",     # 用户权限
    "execute_terminal": "user",# 用户权限
    "system_config": "admin"   # 管理员权限
}
```

---

## 📊 工具元数据

### 工具注册

```python
@register_tool(
    name="open_browser",
    description="打开浏览器访问网址",
    parameters=[
        {"name": "browser_name", "type": "string", "required": False},
        {"name": "url", "type": "string", "required": False}
    ],
    returns="执行结果"
)
def open_browser(...):
    ...
```

### 参数类型

| 类型 | 描述 | 示例 |
|------|------|------|
| string | 字符串 | "chrome", "https://..." |
| integer | 整数 | 10, 60, 100 |
| boolean | 布尔值 | True, False |
| array | 数组 | ["item1", "item2"] |
| object | 对象 | {"key": "value"} |

---

## 🎯 工具选择策略

### 1. 任务匹配

```
用户输入 → LLM Intent Recognition → 确定任务类型 → 选择工具
```

### 2. 工具优先级

```python
TOOL_PRIORITY = {
    "browser": ["open_browser", "detect_browsers"],
    "terminal": ["execute_terminal", "run_python"],
    "file": ["read_file", "write_file", "list_directory"],
    "web": ["web_search", "fetch_url"],
    "code": ["execute_code", "analyze_code"]
}
```

### 3. 工具组合

```python
# 复杂任务需要工具组合
用户: 搜索 Python 教程并保存到文件

Agent:
  1. web_search(query="Python 教程")
  2. write_file(path="python_tutorial.txt", content=结果)
  3. 向用户报告完成情况
```

---

## 📝 工具使用示例

### 示例 1: 浏览器操作

```
用户: 用 Chrome 打开 Google 搜索 Python
Agent: 
  工具: open_browser(browser_name="chrome", url="https://www.google.com/search?q=Python")
  结果: 已用 Chrome 打开 Google 搜索结果页
```

### 示例 2: 文件操作

```
用户: 读取当前目录下的 readme.txt
Agent:
  工具: read_file(path="readme.txt")
  结果: [文件内容]
```

### 示例 3: 命令执行

```
用户: 打开计算器和记事本
Agent:
  工具 1: execute_terminal(command="start calc")
  工具 2: execute_terminal(command="start notepad")
  结果: 已打开计算器和记事本
```

### 示例 4: 综合操作

```
用户: 在网上搜索最新的 AI 新闻，然后打开浏览器查看
Agent:
  步骤 1:
    工具: web_search(query="最新 AI 新闻", limit=5)
    结果: [新闻列表]
  
  步骤 2:
    工具: open_browser(url="https://www.google.com/search?q=最新AI新闻")
    结果: 已在浏览器中打开搜索结果
  
  向用户报告: 已为您搜索并打开最新的 AI 新闻
```

---

## 🚀 工具扩展

### 添加新工具

```python
# 1. 定义工具函数
@register_tool(
    name="my_tool",
    description="工具描述",
    parameters=[
        {"name": "param1", "type": "string", "required": True},
        {"name": "param2", "type": "integer", "required": False}
    ]
)
def my_tool(param1: str, param2: int = None) -> ToolResult:
    # 工具实现
    return ToolResult(success=True, output="结果")
```

### 工具分类

```python
TOOL_CATEGORIES = {
    "browser": "浏览器操作",
    "terminal": "终端命令",
    "file": "文件操作",
    "web": "网络搜索",
    "code": "代码执行",
    "system": "系统操作"
}
```

---

## 📌 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| 1.0 | 2026-05-25 | 初始版本，定义工具规范 |

---

## 🔗 相关文档

- [agent.md](agent.md) - Agent 角色定义
- [memory.md](memory.md) - 记忆系统定义
- [capabilities.md](capabilities.md) - 能力清单
- [../tools/__init__.py](../tools/__init__.py) - 工具注册系统
- [../core/skill_manager.py](../core/skill_manager.py) - 技能管理器