# Core Module - 核心框架模块

## 📋 概述

核心框架模块是整个 Agent 的**控制层**，负责协调各个组件的工作，实现任务路由，技能管理和会话管理等核心功能。

**架构位置**: Core Layer 处于用户层和推理层之间，负责编排调度。

> **核心原则**: "所有意图识别使用 LLM，**NO hardcoded rules**，无 fallback 降级逻辑。"

## 🏛️ Harness 架构中的 Core Layer

在 Harness 架构中，Core Layer 负责：

```
┌─────────────────────────────────────────────────────────────┐
│          Harness Architecture - Core Layer Position           │
├─────────────────────────────────────────────────────────────┤
│  1. Interface Layer                                        │
│     CLI │ Gateway                                         │
├─────────────────────────────────────────────────────────────┤
│  2. ✨ Intent Recognition Layer (LLM-powered)              │
│     llm_intent_service.py (NEW!)                          │
├─────────────────────────────────────────────────────────────┤
│  3. Core Layer ← YOU ARE HERE                            │
│     CustomAgent │ TaskRouter │ SkillManager │ Session    │
├─────────────────────────────────────────────────────────────┤
│  4. Tool Abstraction Layer                                │
│     ToolRegistry │ @register_tool                          │
├─────────────────────────────────────────────────────────────┤
│  5. LLM Provider Layer                                  │
│     Adapter Pattern │ 25+ Providers                      │
└─────────────────────────────────────────────────────────────┘
```

## 🎯 纯 LLM Intent Recognition

### 不再使用的（已废弃）

```python
# ❌ DEPRECATED - 硬编码关键词
INTENT_KEYWORDS = {
    'terminal': ['打开', '启动', '运行', ...]  # 已移除
}

# ❌ DEPRECATED - 硬编码命令映射
command_mapping = {
    'chrome': 'start chrome',  # 已移除
    '桌面': 'start explorer shell:desktop'  # 已移除
}

# ❌ DEPRECATED - fallback 降级逻辑
try:
    result = llm_intent_recognition()
except:
    result = hardcoded_fallback()  # 已移除
```

### 现在使用的（LLM驱动）

```python
# ✅ NEW - 纯 LLM 意图识别
from core.llm_intent_service import get_llm_intent_service

intent_service = get_llm_intent_service()
result = await intent_service.recognize_intent(
    input_text="帮我打开桌面文件夹",
    domain='terminal_command'
)
# LLM 返回结构化 JSON：
# {
#     "intent_type": "terminal_command",
#     "action_type": "open_folder",
#     "target": "桌面",
#     "command": "start explorer shell:desktop"
# }
```

## 🏗️ 架构设计

### 模块结构

```
core/
├── __init__.py
├── agent.py          # CustomAgent 主编排器（控制层大脑）
├── router.py         # TaskRouter 任务路由 + IntentClassifier 意图分类
├── skill_manager.py  # SkillManager 技能管理
├── session.py        # SessionManager 会话管理
├── cache.py         # LRUCache 响应缓存
├── layer_logger.py   # 分层日志系统
└── config.py         # 配置管理
```

### 与 AIAgent 的关系

```
Entry Points (CLI/Gateway/ACP)
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│               Core Layer - 控制层                               │
│  CustomAgent → TaskRouter → SkillManager → SessionManager     │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│               AIAgent (agent/ai_agent.py) - 推理层             │
│  PromptBuilder → ProviderResolver → ToolDispatcher             │
└─────────────────────────────────────────────────────────────────┘
```

**说明**: Core 层负责控制流编排，AIAgent 负责推理和工具执行，两者协同工作。

## 🧩 核心组件

### 1. CustomAgent (控制层大脑)

**职责**: 核心编排器，协调各个模块的工作流程。

**处理流程**:

```
用户请求 → CustomAgent → TaskRouter → SkillManager → 工具/LLM → 返回结果
               │              │              │
               ▼              ▼              ▼
          会话管理        意图分类        技能执行
```

**关键方法**:
- `respond(input_text)` - 处理用户输入并返回响应
- `route_request(input_text)` - 路由请求到合适的处理器
- `execute_skill(skill_id, **kwargs)` - 执行技能

### 2. TaskRouter + IntentClassifier

**职责**: 智能任务路由，根据用户意图将请求路由到合适的处理程序。

**处理流程**:

```
用户输入 → IntentClassifier → 意图分类 → 路由匹配 → 返回 RouteMatch
               │                           │
               ▼                           ▼
         关键词提取                    置信度计算
```

**支持的意图类型**:
- `conversation` - 闲聊对话
- `coding` - 代码处理
- `question` - 问答
- `tool_use` - 工具使用
- `creation` - 内容创作

### 3. SkillManager

**职责**: 技能注册、发现和执行管理。

**处理流程**:

```
路由匹配 → 技能发现 → 参数验证 → 技能执行 → 返回结果
               │              │           │
               ▼              ▼           ▼
          技能注册表        输入校验      异常处理
```

**关键方法**:
- `register_skill(skill)` - 注册技能
- `get_skill(skill_id)` - 获取技能
- `execute_skill(skill_id, **kwargs)` - 执行技能

### 4. SessionManager

**职责**: 会话管理，负责上下文保留和历史跟踪。

**处理流程**:

```
用户请求 → 获取会话 → 添加消息 → 保存会话 → 返回响应
               │              │           │
               ▼              ▼           ▼
          会话查找        消息追加      持久化存储
```

**关键特性**:
- 支持多会话管理
- 历史记录长度限制
- 上下文压缩优化

## 🔄 请求处理流程

```
┌────────────────────────────────────────────────────────────────────┐
│                    用户请求到达                                     │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│  CustomAgent (core/agent.py)                                      │
│  • 接收请求                                                        │
│  • 获取或创建会话                                                  │
│  • 调用 TaskRouter                                                │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│  TaskRouter (core/router.py)                                      │
│  • IntentClassifier 分类意图                                       │
│  • 匹配最佳路由                                                    │
│  • 返回 RouteMatch 对象                                            │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│  SkillManager (core/skill_manager.py)                             │
│  • 根据路由发现技能                                                │
│  • 验证参数                                                        │
│  • 执行技能并获取结果                                               │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│  SessionManager (core/session.py)                                 │
│  • 保存会话历史                                                    │
│  • 更新上下文                                                      │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│                    返回响应给用户                                   │
└────────────────────────────────────────────────────────────────────┘
```

## 📊 模块协作关系

| 组件 | 上游依赖 | 下游依赖 | 职责 |
|------|----------|----------|------|
| CustomAgent | CLI | TaskRouter, SkillManager | 主编排 |
| TaskRouter | CustomAgent | SkillManager | 任务路由 |
| SkillManager | TaskRouter | tools/ | 技能执行 |
| SessionManager | CustomAgent | hermes_state | 会话管理 |

## 🎯 使用示例

```python
from core.agent import CustomAgent
from core.session import SessionManager

# 初始化 Agent
agent = CustomAgent()

# 处理用户请求
response = agent.respond("帮我读取 config.json 文件")

# 获取会话历史
session = SessionManager().get_session(session_id)
```

## 🔓 开源替代方案

本模块中的各个组件都有成熟的的开源替代方案，可以根据需求选择：

### 1. 任务路由 (TaskRouter)

| 方案 | 描述 | 适用场景 | GitHub |
|------|------|----------|--------|
| **LangChain Agents** | 完整的 Agent 框架，包含 ReAct、MRKL 等路由策略 | 复杂 Agent 构建 | [langchain-ai/langchain](https://github.com/langchain-ai/langchain) |
| **LlamaIndex** | 基于检索增强的 Agent 框架 | RAG 场景 | [run-llama/llama_index](https://github.com/run-llama/llama_index) |
| **AutoGen** | Microsoft 多代理协作框架 | 多代理场景 | [microsoft/autogen](https://github.com/microsoft/autogen) |
| **CrewAI** | 多代理协作框架 | 角色扮演协作 | [joaomdmoura/crewAI](https://github.com/joaomdmoura/crewAI) |
| **SmolAgents** | 轻量级 Agent 框架 | 嵌入式场景 | [huggingface/smolagents](https://github.com/huggingface/smolagents) |

**集成建议**:
```python
# 使用 LangChain 替代 TaskRouter
from langchain.agents import initialize_agent, AgentType
from langchain.chat_models import ChatOpenAI

llm = ChatOpenAI(model="gpt-4")
agent = initialize_agent(
    tools,
    llm,
    agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
    verbose=True
)
```

### 2. 会话管理 (SessionManager)

| 方案 | 描述 | 适用场景 | GitHub |
|------|------|----------|--------|
| **ChatMemory** | LangChain 对话记忆 | 对话上下文 | [langchain-ai/langchain](https://github.com/langchain-ai/langchain) |
| **Django Chat** | Django 会话框架 | Web 应用 | [django/django](https://github.com/django/django) |
| **Redis Session** | Redis 会话存储 | 高性能生产环境 | [redis/redis-py](https://github.com/redis/redis-py) |
| **SQLAlchemy Session** | ORM 会话管理 | 关系型数据库 | [sqlalchemy/sqlalchemy](https://github.com/sqlalchemy/sqlalchemy) |
| ** elephant-dtl** | PostgreSQL 会话 | 持久化存储 | [psycopg/psycopg2](https://github.com/psycopg/psycopg2) |

**集成建议**:
```python
# 使用 LangChain ConversationBufferMemory
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain

memory = ConversationBufferMemory()
conversation = ConversationChain(
    llm=llm,
    memory=memory,
    verbose=True
)
```

### 3. 技能管理 (SkillManager)

| 方案 | 描述 | 适用场景 | GitHub |
|------|------|----------|--------|
| **ToolManager (LangChain)** | LangChain 工具管理 | 工具注册执行 | [langchain-ai/langchain](https://github.com/langchain-ai/langchain) |
| **OpenAI Function Calling** | OpenAI 原生工具调用 | GPT-4 函数调用 | [openai/openai-cookbook](https://github.com/openai/openai-cookbook) |
| **ToolBench** | 工具学习基准 | 研究场景 | [google-research/toolbench](https://github.com/google-research/toolbench) |
| **Gorilla** | 工具调用大模型 | 工具调用优化 | [gorilla-llm/gorilla](https://github.com/gorilla-llm/gorilla) |

### 4. Agent 编排

| 方案 | 描述 | 适用场景 | GitHub |
|------|------|----------|--------|
| **Haystack** | NLP 框架 | RAG、问答 | [deepset-ai/haystack](https://github.com/deepset-ai/haystack) |
| **Guidance** | 结构化 LLM 输出 | 生成控制 | [microsoft/guidance](https://github.com/microsoft/guidance) |
| **Sematic** | Agent 工作流 | 生产级管道 | [sematic-ai/sematic](https://github.com/sematic-ai/sematic) |

### 5. 缓存优化

| 方案 | 描述 | 适用场景 | GitHub |
|------|------|----------|--------|
| **DiskCache** | 磁盘缓存 | 持久化缓存 | [grantjenks/blueprint_django](https://github.com/grantjenks/blueprint_django) |
| **cachetools** | TTL 缓存 | 内存缓存 | [tkashem/cachetools](https://github.com/tkashem/cachetools) |
| **Redis Cache** | Redis 分布式缓存 | 分布式环境 | [redis/redis-py](https://github.com/redis/redis-py) |
| **Memcached** | 内存缓存 | 高性能缓存 | [p最/memcached](https://github.com/peletiah/memcached) |

## 🔧 替换指南

### 替换 TaskRouter 为 LangChain Agent

```python
# 当前实现
from core.router import TaskRouter
router = TaskRouter()
route_match = router.route(user_input)

# LangChain 替代
from langchain.agents import initialize_agent, AgentType
agent = initialize_agent(
    tools,
    llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)
result = agent.run(user_input)
```

### 替换 SessionManager 为 LangChain Memory

```python
# 当前实现
from core.session import SessionManager
session_manager = SessionManager()
session = session_manager.create_session(session_id)
session.add_message('user', message)

# LangChain 替代
from langchain.memory import ConversationBufferMemory
memory = ConversationBufferMemory(memory_key="chat_history")
memory.save_context({"input": message}, {"output": response})
```

### 替换 SkillManager 为 LangChain Tools

```python
# 当前实现
from core.skill_manager import SkillManager
skill_manager = SkillManager()
result = await skill_manager.execute_skill(skill_id, **kwargs)

# LangChain 替代
from langchain.tools import Tool
from langchain.agents import initialize_agent

def my_function(query):
    return f"Result for: {query}"

tools = [
    Tool(name="my_tool", func=my_function, description="描述")
]
agent = initialize_agent(tools, llm, AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION)
```

## 📚 进一步阅读

- [LangChain Documentation](https://docs.langchain.com)
- [LlamaIndex Documentation](https://gpt-index.readthedocs.io)
- [AutoGen Documentation](https://microsoft.github.io/autogen)
- [CrewAI Documentation](https://docs.crewai.com)
