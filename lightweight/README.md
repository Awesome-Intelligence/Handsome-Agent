# Lightweight Module - 轻量级代理模块

## 📋 概述

轻量级代理模块提供简化版的 Agent 实现，适用于资源受限环境或简单场景，具有启动快、资源占用低的特点。

## 🏗️ 架构设计

### 模块结构

```
lightweight/
├── __init__.py
├── simple_agent.py       # 简单代理实现
├── simple_prompt.py      # 简化提示词构建
└── simple_session.py     # 简化会话管理
```

## 🧩 核心组件

### 1. SimpleAgent

**职责**: 轻量级代理实现，提供基本的对话功能。

**特点**:
- 简化的对话流程
- 无需复杂配置
- 快速启动

**处理流程**:

```
用户输入 → 构建 Prompt → LLM 调用 → 返回响应
               │          │
               ▼          ▼
         简单提示词      直接调用
```

### 2. SimplePrompt

**职责**: 简化的提示词构建器。

**Prompt 结构**:

```
你是一个友好的助手。请用简洁明了的语言回答问题。

用户: {user_input}
助手:
```

### 3. SimpleSession

**职责**: 简化的会话管理。

**特点**:
- 内存中存储会话
- 固定历史长度限制
- 无需持久化

## 🔄 处理流程

```
┌────────────────────────────────────────────────────────────────────┐
│                    用户输入                                        │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│  SimpleAgent (lightweight/simple_agent.py)                        │
│  • 获取会话历史                                                    │
│  • 构建简化 Prompt                                                 │
│  • 调用 LLM                                                       │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│  LLM 响应                                                         │
│  • 获取响应内容                                                    │
│  • 更新会话历史                                                    │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│                    返回响应                                        │
└────────────────────────────────────────────────────────────────────┘
```

## 📊 与完整版本对比

| 特性 | 轻量级版本 | 完整版本 |
|------|-----------|----------|
| 启动速度 | 快 | 较慢 |
| 资源占用 | 低 | 较高 |
| 功能完整性 | 基础 | 完整 |
| 工具调用 | 不支持 | 支持 |
| 记忆系统 | 简单 | 完整 |
| 插件支持 | 不支持 | 支持 |
| 持久化 | 内存 | SQLite |

## 🎯 使用场景

- **快速原型开发** - 需要快速验证想法
- **资源受限环境** - 低内存、低 CPU 设备
- **简单对话场景** - 不需要复杂功能
- **嵌入式应用** - 需要轻量级集成

## 🎯 使用示例

```python
from lightweight import SimpleAgent

# 创建轻量级代理
agent = SimpleAgent()

# 设置 LLM 配置
agent.set_config(
    provider="openai",
    api_key="your-api-key",
    model="gpt-3.5-turbo"
)

# 对话
response = agent.chat("你好")
print(response)
```

## ⚡ 性能优势

- **启动时间**: < 100ms
- **内存占用**: < 50MB
- **响应延迟**: 取决于 LLM 调用

## 🔓 开源替代方案

### 1. 轻量级 Agent 框架

| 方案 | 描述 | 适用场景 | GitHub |
|------|------|----------|--------|
| **SmolAgents** | Hugging Face 轻量 Agent | 嵌入式 | [huggingface/smolagents](https://github.com/huggingface/smolagents) |
| **NanoGPT** | 最小 GPT 实现 | 学习研究 | [karpathy/nanoGPT](https://github.com/karpathy/nanoGPT) |
| **llama.cpp** | 高性能本地推理 | 资源受限 | [ggerganov/llama.cpp](https://github.com/ggerganov/llama.cpp) |
| **LocalAI** | 本地 LLM 网关 | 自托管 | [mudler/LocalAI](https://github.com/mudler/LocalAI) |
| **Ollama** | 简单本地运行 | 快速部署 | [ollama/ollama](https://github.com/ollama/ollama) |

**集成建议**:
```python
# 使用 SmolAgents 轻量框架
from smolagents import CodeAgent, HuggingFaceModel

model = HuggingFaceModel(model_id="google/gemma-2b")
agent = CodeAgent(model=model, tools=[])
response = agent.run("帮我写一个排序算法")
```

### 2. 轻量级对话

| 方案 | 描述 | 适用场景 | GitHub |
|------|------|----------|--------|
| **Chatterbox** | 简单对话代理 | 最小依赖 | [prosysdev/Chatterbox](https://github.com/prosysdev/Chatterbox) |
| **MiniChain** | 最小 Chain 实现 | 学习研究 | [/sdanierm/MiniChain](https://github.com/sdanierm/MiniChain) |
| **LLM-Function** | 简单函数调用 | 基础功能 | [lm-function/lm-function](https://github.com/lm-function/lm-function) |
| **text-generation-webui** | Web 对话界面 | 对话测试 | [oobabooga/text-generation-webui](https://github.com/oobabooga/text-generation-webui) |

### 3. 简单 Prompt

| 方案 | 描述 | 适用场景 | GitHub |
|------|------|----------|--------|
| **Handlebars** | 模板引擎 | Prompt 模板 | [wycats/handlebars.js](https://github.com/handlebars-lang/handlebars.js) |
| **Jinja2** | Python 模板 | 动态生成 | [pallets/jinja](https://github.com/pallets/jinja) |
| **stringr** | 字符串模板 | R 版本 | [tidyverse/stringr](https://github.com/tidyverse/stringr) |

### 4. 简单会话

| 方案 | 描述 | 适用场景 | GitHub |
|------|------|----------|--------|
| **pickle** | Python 序列化 | 内存持久化 | [Python 内置](https://docs.python.org/3/library/pickle.html) |
| **SQLite** | 轻量数据库 | 本地存储 | [Python 内置](https://docs.python.org/3/library/sqlite3.html) |
| **shelve** | 持久化字典 | 简单存储 | [Python 内置](https://docs.python.org/3/library/shelve.html) |
| **TinyDB** | 轻量 NoSQL | 嵌入式 | [msiemens/tinydb](https://github.com/msiemens/tinydb) |

**集成建议**:
```python
# 使用 TinyDB 简单存储
from tinydb import TinyDB, Query

db = TinyDB('session.json')
session = db.table('sessions')
session.insert({'user': 'msg1', 'assistant': 'reply1'})

# 查询
User = Query()
result = session.search(User.user == 'msg1')
```

### 5. CLI 框架

| 方案 | 描述 | 适用场景 | GitHub |
|------|------|----------|--------|
| **Inquirer** | 交互式 CLI | 用户输入 | [mgedmin/inquirer](https://github.com/mgedmin/inquirer) |
| **questionary** | 交互式问题 | 表单输入 | [tmbo/questionary](https://github.com/tmbo/questionary) |
| **PTy** | 伪终端 | 终端控制 | [pexpect/pty](https://github.com/pexpect/pty) |

### 6. 完整轻量方案

| 方案 | 描述 | 适用场景 | GitHub |
|------|------|----------|--------|
| **ollama + smolagents** | 本地 LLM + 轻量 Agent | 完全本地 | [ollama/ollama](https://github.com/ollama/ollama) + [huggingface/smolagents](https://github.com/huggingface/smolagents) |
| **LocalAI + Guidance** | 本地 + 结构化控制 | 生产轻量 | [mudler/LocalAI](https://github.com/mudler/LocalAI) + [microsoft/guidance](https://github.com/microsoft/guidance) |
| **vLLM + LiteLLM** | 高性能推理 + 统一接口 | 生产级轻量 | [vllm-project/vllm](https://github.com/vllm-project/vllm) + [BerriAI/litellm](https://github.com/BerriAI/litellm) |

## 🔧 替换指南

### 使用 Ollama 替换远程 LLM

```python
# 当前实现
from lightweight import SimpleAgent
agent = SimpleAgent()
agent.set_config(provider="openai", api_key="xxx")

# Ollama 完全本地替代
import ollama

response = ollama.chat(
    model='llama3',
    messages=[{"role": "user", "content": "Hello"}]
)
```

### 使用 TinyDB 替换文件会话

```python
# 当前实现
from lightweight.simple_session import SimpleSession
session = SimpleSession()

# TinyDB 替代
from tinydb import TinyDB

db = TinyDB('sessions.json')
sessions = db.table('sessions')
sessions.insert({
    'id': 'session_1',
    'messages': [
        {'role': 'user', 'content': 'Hello'},
        {'role': 'assistant', 'content': 'Hi!'}
    ]
})
```

## 📚 进一步阅读

- [SmolAgents Documentation](https://smolagents.readthedocs.io)
- [Ollama Documentation](https://github.com/ollama/ollama)
- [TinyDB Documentation](https://tinydb.readthedocs.io)
- [轻量级 LLM 工具箱](https://github.com/zeshy-bot/awesome-lightweight-LLM)
