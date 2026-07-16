# Agent 能力完整清单

> Agent-Z 支持的能力矩阵

## 一、核心 Agent 类型

### 1. 轻量版 Agent (Lightweight)

| Agent 类型 | 模块 | 功能 |
|------------|------|------|
| LightweightAgent | lightweight/agent.py | 轻量级响应生成（零依赖） |
| EnhancedAgent | lightweight/agent_v2.py | 支持 Chain of Thought 和 Tool Use |
| ToolSystem | lightweight/tools.py | 工具注册管理 |
| ToolAgent | lightweight/tools.py | 工具检测执行 |

### 2. Core Agent

| Agent 类型 | 模块 | 功能 |
|------------|------|------|
| SimpleAgent | core/simplified_agent.py | 简化版 Agent（展示 LLM 直接决策） |
| ModernAgent | core/modern_agent.py | 现代 Agent（完整功能） |
| CustomAgent | core/agent.py | 主编排器（已废弃） |

### 3. Brain Agent

| Agent 类型 | 模块 | 功能 |
|------------|------|------|
| AgentLoop | brain/agent/agent_loop.py | ReAct 模式的 Agent Loop |
| SelfEvolutionManager | brain/skills/evolution_manager.py | 自我进化管理器 |

### 4. 其他 Agent

| Agent 类型 | 模块 | 功能 |
|------------|------|------|
| OpenHumanAgent | agent/openhuman.py | 情绪检测交互 |
| InteractionManager | agent/interaction.py | 用户交互跟踪 |

## 二、能力矩阵

| 能力 | 支持 | 性能目标 |
|------|------|----------|
| 基础响应生成 | ✅ | < 5ms |
| Chain of Thought 推理 | ✅ | < 50ms |
| 工具使用 (Tool Use) | ✅ | < 10ms |
| 任务规划 (Task Planning) | ✅ | < 100ms |
| 记忆管理 | ✅ | < 20ms |
| 技能系统 | ✅ | < 10ms |
| 自我进化 | ✅ | 后台运行 |
| 情绪检测 | ⚠️ | 部分支持 |
| 知识图谱 | 🚧 | 规划中 |
| 多 Agent 协作 | 🚧 | 规划中 |

**图例**:
- ✅ 已实现
- ⚠️ 部分实现
- 🚧 规划中

## 三、核心能力详解

### 3.1 工具系统 (Tool Use)

支持多种工具类型：

```python
# 文件操作
read_file, write_file, list_directory, search_files

# 应用启动
launch_app, open_file, open_calculator, open_notepad

# 终端命令
terminal, run_python

# 网络
web_search, web_extract

# 技能
skill_discovery, skill_execute
```

### 3.2 记忆系统 (Memory)

- 短期记忆：会话上下文
- 长期记忆：持久化存储
- 语义检索：基于向量搜索

### 3.3 技能系统 (Skills)

- 技能加载：从文件系统
- 技能匹配：基于用户输入
- 技能执行：参数验证
- 生命周期：自动状态转换（active → stale → archived）

### 3.4 自我进化 (Self-Evolution)

- 轨迹记录：记录每个 Thought/Action/Observation
- Curator 评估：分析轨迹生成技能
- 技能合成：合并相似技能

## 四、推理级别

EnhancedAgent 支持多种推理级别：

| 级别 | 说明 | 适用场景 |
|------|------|----------|
| DIRECT | 直接响应 | 简单查询 |
| CHAIN_OF_THOUGHT | 思维链推理 | 复杂问题 |
| REACT | 推理 + 行动 | 工具调用 |
| SELF_REFLECT | 自我反思 | 需要校验的场景 |

## 五、参考项目

- **AutoGPT** - 目标分解
- **Claude** - 思维链 (Chain of Thought)
- **LangChain** - 工具抽象 (Tool Calling)
- **MemGPT** - 记忆管理
- **MetaGPT** - 多 Agent 协作
- **OpenHuman** - 情绪智能

## 六、快速开始

```python
# 轻量版 Agent
from lightweight import LightweightAgent
agent = LightweightAgent()
result = agent.respond("What is Python?")

# 增强版 Agent (CoT + Tools)
from lightweight.agent_v2 import EnhancedAgent, ReasoningLevel
agent = EnhancedAgent(reasoning_level=ReasoningLevel.CHAIN_OF_THOUGHT)
result = await agent.respond("Explain neural networks", include_reasoning=True)
```

## 七、性能指标

| 模块 | 指标 | 目标值 |
|------|------|--------|
| Lightweight Agent | 响应时间 | < 5ms |
| Lightweight Agent | 内存占用 | < 30MB |
| Lightweight Agent | 依赖数量 | 0（仅标准库） |
| Enhanced Agent | 推理时间 | < 50ms |
| Gateway | 并发能力 | 1000+ req/s |

---

*最后更新: 2026-06-01*