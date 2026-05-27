# LLM Integration Module - LLM 集成模块

## 📋 概述

LLM 集成模块负责统一管理多个大模型提供商的接入，提供一致的 API 接口，支持 25+ 大模型提供商。

**在 Harness 架构中的位置**: LLM Provider Layer（LLM 提供商层），为 Intent Recognition 和 Tool Execution 提供 LLM 调用能力。

## 🏛️ Harness 架构 - LLM Layer

```
┌─────────────────────────────────────────────────────────────┐
│          Harness Architecture - LLM Provider Layer         │
├─────────────────────────────────────────────────────────────┤
│  1. Intent Recognition                                      │
│     ✨ Pure LLM Intent Understanding                         │
│     ↓                                                         │
│  2. Task Planning                                          │
│     LLM-powered Sub-task Decomposition                       │
│     ↓                                                         │
│  3. ✨ LLM Provider Layer ← YOU ARE HERE                  │
│     25+ Providers │ Adapter Pattern                         │
│     ↓                                                         │
│  4. Tool Execution                                         │
│     ToolRegistry │ @register_tool                         │
└─────────────────────────────────────────────────────────────┘
```

**核心原则**: LLM Provider Layer 为整个 Harness 架构提供统一的 LLM 调用接口，**不包含业务逻辑**，只负责 LLM 调用。

> **关键**: LLM Provider 用于 Intent Recognition、Task Planning 和 Tool Execution，但不直接处理用户意图。

## 🏗️ 架构设计

### 模块结构

```
llm_integration/
├── __init__.py
├── providers/           # 提供商实现
│   ├── openai.py
│   ├── anthropic.py
│   ├── minimax.py
│   ├── deepseek.py
│   ├── qianwen.py
│   ├── zhipu.py
│   └── ...
├── provider_registry.py # 提供商注册中心
├── llm_config.py       # 配置管理
└── model_info.py       # 模型信息
```

### 与 AIAgent 的关系

```
AIAgent (agent/ai_agent.py)
    │
    ├── ProviderResolver (3 API 模式)
    │       │
    │       ▼
    │   LLM Integration (25+ 提供商)
    │       │
    │       ▼
    │   具体 Provider (OpenAI/Claude/Gemini...)
```

**说明**: AIAgent 通过 ProviderResolver 调用 LLM Integration，后者封装了 25+ 提供商的统一接口。

### 3 种 API 模式

| 模式 | 描述 | 提供商示例 |
|------|------|-----------|
| `chat_completion` | OpenAI chat 格式 | OpenAI, Azure, 通义千问 |
| `completion` | 传统 completion | GPT-3 |
| `anthropic` | Claude 格式 | Anthropic Claude |

## 🧩 核心组件

### 1. ProviderRegistry

**职责**: 管理所有 LLM 提供商的注册和发现。

**处理流程**:

```
请求 → 查找提供商 → 创建实例 → 执行调用 → 返回结果
           │           │          │
           ▼           ▼          ▼
      注册表查找     配置加载     API 调用
```

**关键方法**:
- `register_provider(provider)` - 注册提供商
- `get_provider(provider_id)` - 获取提供商
- `list_providers()` - 列出所有提供商

### 2. LLMConfig

**职责**: 管理 LLM 配置，包括 API Key、模型选择、参数设置等。

**配置项**:
| 配置项 | 描述 | 默认值 |
|--------|------|--------|
| `provider` | 提供商 ID | `openai` |
| `api_key` | API 密钥 | 空 |
| `model` | 模型名称 | 提供商默认 |
| `api_base` | API 地址 | 提供商默认 |
| `max_tokens` | 最大响应 tokens | 4096 |
| `temperature` | 温度参数 | 0.7 |

### 3. ModelInfo

**职责**: 管理模型信息，包括模型名称、支持的功能等。

**模型分类**:
- **通用模型**: GPT-4, Claude 3, 通义千问等
- **代码模型**: CodeLlama, GPT-4 Code 等
- **多模态模型**: GPT-4V, Claude 3 Opus 等

## 🔄 调用流程

```
┌────────────────────────────────────────────────────────────────────┐
│                    LLM 调用请求                                    │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│  ProviderRegistry (llm_integration/provider_registry.py)          │
│  • 根据配置查找提供商                                              │
│  • 加载提供商配置                                                  │
│  • 创建提供商实例                                                  │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│  具体提供商实现 (llm_integration/providers/*.py)                   │
│  • OpenAIProvider / AnthropicProvider / MiniMaxProvider 等        │
│  • 构建请求                                                        │
│  • 发送 HTTP 请求                                                  │
│  • 解析响应                                                        │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│                    返回响应给调用者                                │
└────────────────────────────────────────────────────────────────────┘
```

## 📊 支持的提供商

### 国际提供商

| 提供商 | 支持的模型 |
|--------|------------|
| OpenAI | GPT-4o, GPT-4 Turbo, GPT-3.5 |
| Anthropic | Claude 3 Opus, Claude 3 Sonnet, Claude 3 Haiku |
| Google | Gemini Pro, Gemini Ultra |
| Meta | Llama 2, Llama 3 |
| Mistral | Mistral 7B, Mistral 8x7B |

### 国内提供商

| 提供商 | 支持的模型 |
|--------|------------|
| 阿里云 | 通义千问 Qwen-7B, Qwen-14B, Qwen-72B |
| 智谱 AI | ChatGLM3-6B, ChatGLM3-6B-Chat |
| MiniMax | abab6-chat, abab5-chat, abab5.5-chat |
| DeepSeek | DeepSeek-R1, DeepSeek-Coder |
| 月之暗面 | Moonshot-v1-8k, Moonshot-v1-32k |
| 商汤 | SenseChat |
| 字节跳动 | Doubao |

## 🎯 使用示例

```python
from llm_integration.provider_registry import ProviderRegistry
from llm_integration.llm_config import LLMConfig

# 创建配置
config = LLMConfig(
    provider="minimax",
    api_key="your-api-key",
    model="abab6-chat"
)

# 获取提供商
registry = ProviderRegistry()
provider = registry.get_provider("minimax")

# 调用 LLM
response = provider.chat("你好", config)
print(response.content)
```

## 🔧 自定义 API 地址

支持用户自定义 API 地址：

```python
config = LLMConfig(
    provider="minimax",
    api_key="your-api-key",
    api_base="https://api.minimaxi.com/anthropic"
)
```

## 🔓 开源替代方案

### 1. 统一 LLM 接口框架

| 方案 | 描述 | 适用场景 | GitHub |
|------|------|----------|--------|
| **LangChain** | 最流行的 LLM 应用框架，支持 100+ 模型 | 通用场景 | [langchain-ai/langchain](https://github.com/langchain-ai/langchain) |
| **LlamaIndex** | 专注于数据增强的 LLM 框架 | RAG 场景 | [run-llama/llama_index](https://github.com/run-llama/llama_index) |
| **LiteLLM** | 统一调用 100+ LLM API | 多模型切换 | [BerriAI/litellm](https://github.com/BerriAI/litellm) |
| **AIOHTTP Client** | 异步 HTTP 客户端 | 自定义实现 | [aio-libs/aiohttp](https://github.com/aio-libs/aiohttp) |
| **Instructor** | 结构化输出 | JSON 模式 | [jxnl/instructor](https://github.com/jxnl/instructor) |

**集成建议**:
```python
# 使用 LiteLLM 统一调用多个 LLM
from litellm import completion

# OpenAI
response = completion(model="gpt-4", messages=[{"role": "user", "content": "Hello"}])

# Anthropic
response = completion(model="claude-3-opus", messages=[{"role": "user", "content": "Hello"}])

# 切换为 DeepSeek
response = completion(model="deepseek/deepseek-chat", messages=[{"role": "user", "content": "Hello"}])
```

### 2. 本地部署模型

| 方案 | 描述 | 适用场景 | GitHub |
|------|------|----------|--------|
| **Ollama** | 本地 LLM 运行框架 | 本地部署 | [ollama/ollama](https://github.com/ollama/ollama) |
| **llama.cpp** | 高性能 LLM 推理 | 本地加速 | [ggerganov/llama.cpp](https://github.com/ggerganov/llama.cpp) |
| **text-generation-webui** | Web UI for LLMs | 对话界面 | [oobabooga/text-generation-webui](https://github.com/oobabooga/text-generation-webui) |
| **LocalAI** | 本地 LLM 网关 | 自托管 | [mudler/LocalAI](https://github.com/mudler/LocalAI) |
| **vLLM** | 高吞吐量 LLM 推理 | 生产环境 | [vllm-project/vllm](https://github.com/vllm-project/vllm) |

**集成建议**:
```python
# 使用 Ollama 本地模型
import ollama

response = ollama.chat(model='llama3', messages=[
    {'role': 'user', 'content': 'Hello!'},
])
print(response['message']['content'])

# 或通过 LiteLLM
from litellm import completion
response = completion(model="ollama/llama3", messages=[{"role": "user", "content": "Hello"}])
```

### 3. 开源模型提供商

| 提供商 | 模型 | 特点 | GitHub |
|--------|------|------|--------|
| **Hugging Face** | Llama 3, Mistral, Falcon | 模型市场 | [huggingface/transformers](https://github.com/huggingface/transformers) |
| **Groq** | Llama 3, Mixtral | 超快推理 | [groq/groq-python](https://github.com/groq/groq-python) |
| **Together AI** | Llama 3, Mistral | 开源模型托管 | [togethercomputer/together-python](https://github.com/togethercomputer/together-python) |
| **Anyscale** | Llama 3, Mistral | 端点托管 | [anyscale/endpoints](https://github.com/anyscale/endpoints) |
| **Fireworks AI** | Llama 3, Mixtral | 高性能推理 | [fireworks-ai/fireworks-python](https://github.com/fireworks-ai/fireworks-python) |

### 4. 模型推理库

| 库 | 描述 | 适用场景 | GitHub |
|----|------|----------|--------|
| **Transformers** | Hugging Face 核心库 | 模型推理 | [huggingface/transformers](https://github.com/huggingface/transformers) |
| **Axolotl** | LLM 微调工具 | 模型训练 | [OpenAccess-AI-Collective/axolotl](https://github.com/OpenAccess-AI-Collective/axolotl) |
| **DeepSpeed** | 深度学习优化 | 训练加速 | [microsoft/DeepSpeed](https://github.com/microsoft/DeepSpeed) |
| **加速推理** | vLLM, TGI, LMDeploy | 生产推理 | [vllm-project/vllm](https://github.com/vllm-project/vllm) |

**集成建议**:
```python
# 使用 Hugging Face Transformers 本地推理
from transformers import AutoModelForCausalLM, AutoTokenizer

model_name = "meta-llama/Llama-3-8b"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

inputs = tokenizer("Hello, how are you?", return_tensors="pt")
outputs = model.generate(**inputs)
print(tokenizer.decode(outputs[0]))
```

### 5. Embedding 模型

| 模型 | 描述 | 适用场景 | GitHub |
|------|------|----------|--------|
| **sentence-transformers** | 句子嵌入 | 语义搜索 | [UKPLab/sentence-transformers](https://github.com/UKPLab/sentence-transformers) |
| **OpenAI Embeddings** | OpenAI 嵌入 | 云端嵌入 | [openai/openai-python](https://github.com/openai/openai-python) |
| **Instructor** | 结构化嵌入 | 自定义嵌入 | [jxnl/instructor](https://github.com/jxnl/instructor) |

### 6. 向量数据库

| 数据库 | 描述 | 适用场景 | GitHub |
|--------|------|----------|--------|
| **Chroma** | 轻量级向量库 | 原型开发 | [chroma-core/chroma](https://github.com/chroma-core/chroma) |
| **Qdrant** | 高性能向量搜索 | 生产环境 | [qdrant/qdrant](https://github.com/qdrant/qdrant) |
| **Weaviate** | 混合搜索 | 语义搜索 | [weaviate/weaviate](https://github.com/weaviate/weaviate) |
| **Milvus** | 大规模向量检索 | 企业级 | [milvus-io/milvus](https://github.com/milvus-io/milvus) |
| **FAISS** | Facebook 向量索引 | 本地快速 | [facebookresearch/faiss](https://github.com/facebookresearch/faiss) |
| **Pinecone** | 云端向量数据库 | 完全托管 | [pinecone-io/pinecone-client](https://github.com/pinecone-io/pinecone-client) |

**集成建议**:
```python
# 使用 Chroma 向量数据库
import chromadb

client = chromadb.Client()
collection = client.create_collection("documents")

# 添加文档
collection.add(
    documents=["这是第一个文档", "这是第二个文档"],
    ids=["1", "2"]
)

# 查询相似文档
results = collection.query(
    query_texts=["第一个文档相关"],
    n_results=1
)
```

### 7. RAG 框架

| 框架 | 描述 | 适用场景 | GitHub |
|------|------|----------|--------|
| **RAGatouille** | RAG 工具包 | 检索增强 | [BMCEagles/ragatouille](https://github.com/BMCEagles/ragatouille) |
| **FastRAG** | 高效 RAG | 生产环境 | [RaptorGolang/FastRAG](https://github.com/RaptorGolang/FastRAG) |
| **Haystack** | 完整 RAG 框架 | 企业级 | [deepset-ai/haystack](https://github.com/deepset-ai/haystack) |

## 🔧 替换指南

### 替换为本项目 LLM 接口 + Ollama 本地模型

```python
# 当前实现
from llm_integration import LLMConfig, setup_llm_integration
config = LLMConfig(provider="openai", api_key="xxx", model="gpt-4")
llm = setup_llm_integration(config)

# Ollama 本地模型
import ollama
response = ollama.chat(model='llama3', messages=[{"role": "user", "content": "Hello"}])
```

### 替换为 LiteLLM 统一接口

```python
# 当前实现
from llm_integration.provider_registry import ProviderRegistry
provider = registry.get_provider("minimax")

# LiteLLM 统一接口
from litellm import completion
response = completion(
    model="anthropic/claude-3-opus",
    messages=[{"role": "user", "content": "Hello"}],
    api_key="your-api-key"
)
```

### 替换向量存储为 Chroma

```python
# 当前实现 - 文件存储
from core.session import SessionManager
session = session_manager.create_session(session_id)

# Chroma 向量存储
import chromadb
client = chromadb.Client()
collection = client.create_collection("knowledge")
collection.add(
    documents=["知识条目1", "知识条目2"],
    embeddings=[[0.1, 0.2], [0.3, 0.4]],
    ids=["1", "2"]
)
```

## 📚 进一步阅读

- [LangChain Providers](https://python.langchain.com/docs/integrations/chat)
- [LiteLLM Documentation](https://docs.litellm.ai)
- [Ollama Documentation](https://github.com/ollama/ollama)
- [Hugging Face Models](https://huggingface.co/models)
- [向量数据库对比](https://github.com/zilliztech/AwesomeVectorSearch)
