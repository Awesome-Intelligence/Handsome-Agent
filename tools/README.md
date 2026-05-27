# Tools Module - 工具系统模块

## 📋 概述

工具系统模块提供各种实用工具，支持文件操作、终端命令、网络搜索、代码执行等功能，使 Agent 能够与外部环境交互。

**在 Harness 架构中的位置**: Tool Abstraction Layer（工具抽象层），为 LLM Intent Recognition 提供执行能力。

## 🏛️ Harness 架构 - Tool Layer

```
┌─────────────────────────────────────────────────────────────┐
│          Harness Architecture - Tool Layer                   │
├─────────────────────────────────────────────────────────────┤
│  1. Intent Recognition (LLM-powered)                      │
│     llm_intent_service.py                                  │
├─────────────────────────────────────────────────────────────┤
│  2. ✨ Tool Abstraction Layer ← YOU ARE HERE             │
│     ToolRegistry │ SkillManager │ Tools                   │
├─────────────────────────────────────────────────────────────┤
│  3. LLM Provider Layer                                  │
│     Adapter Pattern │ 25+ Providers                      │
└─────────────────────────────────────────────────────────────┘
```

**核心原则**: Tool Layer 作为 Harness 架构的执行层，只负责执行由 LLM Intent Recognition 识别的任务，**不包含任何业务逻辑**。

**注意**: 这些工具已整合到 [agent/tool_backends.py](../agent/tool_backends.md) 的 ToolBackend 架构中，可以通过 ToolDispatcher 进行统一调用。

## 🏗️ 架构设计

### 模块结构

```
tools/
├── __init__.py
├── file_tools.py       # 文件操作工具 → FileBackend
├── terminal_tools.py    # 终端命令工具 → TerminalBackend
├── web_tools.py         # 网络搜索工具 → WebBackend
├── code_tools.py       # 代码执行工具 → CodeBackend
└── system_tools.py     # 系统工具
```

### ToolBackend 架构

```
ToolDispatcher (agent/ai_agent.py)
    │
    ├── TerminalBackend (6 种 shell)
    │   └── TerminalTools, SystemTools
    ├── FileBackend
    │   └── FileTools
    ├── WebBackend
    │   └── WebTools
    └── CodeBackend
        └── CodeTools
```

## 🧩 工具列表

### 1. FileTools

**职责**: 文件和目录操作。

**支持的操作**:
| 工具名 | 功能 | 参数 |
|--------|------|------|
| `read_file` | 读取文件内容 | `file_path` |
| `write_file` | 写入文件内容 | `file_path`, `content`, `append` |
| `list_directory` | 列出目录内容 | `path`, `recursive` |
| `create_directory` | 创建目录 | `path` |
| `delete_file` | 删除文件 | `file_path` |
| `rename_file` | 重命名文件 | `old_path`, `new_path` |

**处理流程**:

```
调用请求 → 参数验证 → 执行操作 → 返回结果
               │          │
               ▼          ▼
         路径检查       异常处理
```

### 2. TerminalTools

**职责**: 终端命令执行。

**支持的操作**:
| 工具名 | 功能 | 参数 |
|--------|------|------|
| `run_command` | 执行终端命令 | `command`, `cwd`, `timeout` |
| `run_python` | 执行 Python 代码 | `code`, `timeout` |

**处理流程**:

```
命令请求 → 安全检查 → 执行命令 → 返回输出
               │          │
               ▼          ▼
         命令白名单     超时控制
```

### 3. WebTools

**职责**: 网络搜索和网页抓取。

**支持的操作**:
| 工具名 | 功能 | 参数 |
|--------|------|------|
| `web_search` | 网络搜索 | `query`, `num_results` |
| `fetch_url` | 获取网页内容 | `url` |

### 4. CodeTools

**职责**: 代码分析和执行。

**支持的操作**:
| 工具名 | 功能 | 参数 |
|--------|------|------|
| `analyze_code` | 代码静态分析 | `code`, `language` |
| `format_code` | 代码格式化 | `code`, `language` |

### 5. SystemTools

**职责**: 系统信息获取。

**支持的操作**:
| 工具名 | 功能 | 参数 |
|--------|------|------|
| `get_system_info` | 获取系统信息 | 无 |
| `get_current_time` | 获取当前时间 | 无 |

## 🔄 工具调用流程

```
┌────────────────────────────────────────────────────────────────────┐
│                    工具调用请求                                    │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│  ToolRegistry (model_tools.py)                                    │
│  • 查找工具                                                        │
│  • 验证参数                                                        │
│  • 检查权限                                                        │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│  ToolDispatcher (model_tools.py)                                  │
│  • 调度工具执行                                                    │
│  • 处理异步调用                                                    │
│  • 收集结果                                                        │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│  具体工具执行 (tools/*.py)                                         │
│  • FileTools / TerminalTools / WebTools / CodeTools               │
│  • 执行实际操作                                                    │
│  • 返回结果                                                        │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│                    返回工具执行结果                                │
└────────────────────────────────────────────────────────────────────┘
```

## 📊 工具分类

| 类别 | 工具 | 用途 |
|------|------|------|
| 文件操作 | FileTools | 读写文件、目录操作 |
| 终端命令 | TerminalTools | 执行系统命令 |
| 网络 | WebTools | 搜索、抓取网页 |
| 代码 | CodeTools | 代码分析、格式化 |
| 系统 | SystemTools | 系统信息获取 |

## 🎯 使用示例

```python
from tools.file_tools import FileTools
from tools.terminal_tools import TerminalTools

# 文件操作
file_tools = FileTools()
content = file_tools.read_file("config.json")
file_tools.write_file("output.txt", "Hello World")

# 终端命令
terminal_tools = TerminalTools()
result = terminal_tools.run_command("ls -la", cwd="/home")
```

## 🔒 安全考虑

- 命令执行有白名单限制
- 文件操作有路径限制
- 超时控制防止长时间运行
- 敏感信息过滤

## 🔓 开源替代方案

### 1. 文件操作

| 方案 | 描述 | 适用场景 | GitHub |
|------|------|----------|--------|
| **Pathlib** | Python 标准库路径操作 | 基础文件操作 | [Python 内置](https://docs.python.org/3/library/pathlib.html) |
| **shutil** | 高级文件操作 | 复制、移动、压缩 | [Python 内置](https://docs.python.org/3/library/shutil.html) |
| **watchdog** | 文件系统监控 | 实时监控 | [samuelcolvin/watchdog](https://github.com/samuelcolvin/watchdog) |
| **pathspec** | 文件模式匹配 | 通配符处理 | [cpburnz/python-pathspec](https://github.com/cpburnz/python-pathspec) |
| **增删改查** | 目录树操作 | 目录遍历 | [parrt/lolviz](https://github.com/parrt/lolviz) |

### 2. 终端命令执行

| 方案 | 描述 | 适用场景 | GitHub |
|------|------|----------|--------|
| **subprocess** | 标准库进程管理 | 基础命令 | [Python 内置](https://docs.python.org/3/library/subprocess.html) |
| **pexpect** | 交互式进程控制 | 交互式命令 | [pexpect/pexpect](https://github.com/pexpect/pexpect) |
| **plac** | 命令行参数解析 | 参数解析 | [micheles/plac](https://github.com/micheles/plac) |
| **typer** | 现代 CLI 框架 | CLI 应用 | [tiangolo/typer](https://github.com/tiangolo/typer) |
| **Click** | 命令行接口创建 | CLI 构建 | [pallets/click](https://github.com/pallets/click) |

### 3. 网络工具

| 方案 | 描述 | 适用场景 | GitHub |
|------|------|----------|--------|
| **httpx** | 异步 HTTP 客户端 | HTTP 请求 | [encode/httpx](https://github.com/encode/httpx) |
| **aiohttp** | 异步 HTTP 框架 | 异步网络 | [aio-libs/aiohttp](https://github.com/aio-libs/aiohttp) |
| **requests** | HTTP 请求库 | 同步请求 | [psf/requests](https://github.com/psf/requests) |
| **playwright** | 浏览器自动化 | 网页抓取 | [microsoft/playwright](https://github.com/microsoft/playwright) |
| **selenium** | Web 自动化测试 | 浏览器控制 | [SeleniumHQ/selenium](https://github.com/SeleniumHQ/selenium) |
| **beautifulsoup4** | HTML/XML 解析 | 网页解析 | [crummy/beautifulsoup](https://github.com/crummy/beautifulsoup) |
| **scrapy** | 爬虫框架 | 大规模爬取 | [scrapy/scrapy](https://github.com/scrapy/scrapy) |

**集成建议**:
```python
# 使用 httpx 替代 requests
import httpx

client = httpx.AsyncClient()
response = await client.get("https://api.example.com/data")
data = response.json()
```

### 4. 代码执行

| 方案 | 描述 | 适用场景 | GitHub |
|------|------|----------|--------|
| **codeexec** | 安全代码执行 | 沙箱执行 | [sussman/codeexec](https://github.com/sussman/codeexec) |
| **pyodide** | Python in Browser | Web 执行 | [pyodide/pyodide](https://github.com/pyodide/pyodide) |
| **pysandbox** | Python 沙箱 | 安全隔离 | [Nicolas-Schwartz/pysandbox](https://github.com/Nicolas-Schwartz/pysandbox) |
| **restrictedpython** | 限制性 Python | 语法检查 | [ZPSShaman/restrictedpython](https://github.com/ZPSShaman/restrictedpython) |

### 5. 代码分析

| 方案 | 描述 | 适用场景 | GitHub |
|------|------|----------|--------|
| **astroid** | Python AST 分析 | 代码解析 | [pylint/astroid](https://github.com/pylint/astroid) |
| **ruff** | 超快速 Linter | 代码检查 | [astral-sh/ruff](https://github.com/astral-sh/ruff) |
| **black** | 代码格式化 | 格式统一 | [psf/black](https://github.com/psf/black) |
| **mypy** | 静态类型检查 | 类型检查 | [python/mypy](https://github.com/python/mypy) |
| **pylint** | 代码分析 | 全面检查 | [pylint/pylint](https://github.com/pylint/pylint) |
| **rope** | Python 重构库 | 代码重构 | [python-rope/rope](https://github.com/python-rope/rope) |

**集成建议**:
```python
# 使用 ruff 快速代码检查
import subprocess
result = subprocess.run(["ruff", "check", "file.py"], capture_output=True)
print(result.stdout)
```

### 6. 搜索功能

| 方案 | 描述 | 适用场景 | GitHub |
|------|------|----------|--------|
| **whoosh** | 纯 Python 全文搜索 | 轻量搜索 | [mochicow/whoosh](https://github.com/mochicow/whoosh) |
| **searchIn** | 全文搜索库 | 本地搜索 | [messari/searchIn](https://github.com/messari/searchIn) |
| **elasticsearch-py** | ES 客户端 | 分布式搜索 | [elastic/elasticsearch-py](https://github.com/elastic/elasticsearch-py) |
| **meilisearch** | 超快速搜索 | 即时搜索 | [meilisearch/meilisearch-python](https://github.com/meilisearch/meilisearch-python) |

### 7. 系统工具

| 方案 | 描述 | 适用场景 | GitHub |
|------|------|----------|--------|
| **psutil** | 系统信息获取 | 跨平台系统 | [giampaolo/psutil](https://github.com/giampaolo/psutil) |
| **platformdirs** | 平台目录 | 路径兼容 | [platformdirs/platformdirs](https://github.com/platformdirs/platformdirs) |
| **dotenv** | 环境变量管理 | 配置管理 | [theskumar/python-dotenv](https://github.com/theskumar/python-dotenv) |
| **python-dotenv** | .env 文件解析 | 配置加载 | [theskumar/python-dotenv](https://github.com/theskumar/python-dotenv) |

## 🔧 替换指南

### 使用 httpx 替换 requests

```python
# 当前实现
import requests
response = requests.get("https://api.example.com/data")

# httpx 替代 (支持异步)
import httpx
async with httpx.AsyncClient() as client:
    response = await client.get("https://api.example.com/data")
```

### 使用 ruff 替换 pylint/black

```python
# 当前实现
import subprocess
subprocess.run(["pylint", "file.py"])

# ruff 替代 (快 10-100 倍)
import subprocess
subprocess.run(["ruff", "check", "file.py"])
subprocess.run(["ruff", "format", "file.py"])
```

### 使用 psutil 获取系统信息

```python
# 当前实现
import platform
sys_info = {
    "system": platform.system(),
    "version": platform.version()
}

# psutil 替代 (更丰富)
import psutil
sys_info = {
    "cpu_percent": psutil.cpu_percent(),
    "memory_percent": psutil.virtual_memory().percent,
    "disk_usage": psutil.disk_usage('/').percent
}
```

## 📚 进一步阅读

- [Awesome Python - 命令行工具](https://github.com/vinta/awesome-python)
- [Awesome Python - Web Scraping](https://github.com/pirati-cz/awesome-python-tools)
- [Python 最佳实践](https://docs.python-guide.org)
