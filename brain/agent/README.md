# Brain Agent 模块

> 决策层核心 - ReAct 模式的 Agent Loop 实现

## 📁 模块结构

```
brain/agent/
├── __init__.py       # 模块导出
├── agent_loop.py     # 核心 Agent Loop
└── schemas.py        # 数据模型
```

## 🎯 核心功能

### AgentLoop - ReAct 模式

AgentLoop 是 Agent 的核心执行引擎，采用 ReAct (Reasoning + Acting) 模式：

```
用户输入
    ↓
Thought (思考) → LLM 判断下一步
    ↓
Action (行动) → 执行工具调用
    ↓
Observation (观察) → 获取执行结果
    ↓
循环直到完成
```

### 核心特性

- **LLM 推理**: 使用 LLM 理解用户意图
- **工具调用**: 支持 Hermes 和 OpenClaw 工具
- **轨迹记录**: 完整记录每个 Thought/Action/Observation
- **自我进化**: 集成 Curator 自动学习和技能合成
- **已学习技能**: 支持加载和使用自动合成的技能
- **会话历史**: 管理对话上下文

## 🚀 快速开始

### 基本使用

```python
from brain.agent import AgentLoop, AgentConfig
from brain.llm import OpenAIProvider

# 配置
config = AgentConfig(
    max_iterations=10,
    enable_trajectory=True,
    enable_curator=True,
    enable_self_evolution=True,  # 启用自我进化
)

# 创建 Agent
provider = OpenAIProvider(api_key="your-key")
agent = AgentLoop(config=config, llm_provider=provider)

# 执行
result = await agent.run(
    user_input="帮我搜索 Python 教程",
    context={"session_id": "sess-123"}
)

print(result["response"])
```

### 集成轨迹记录

```python
from brain.agent import AgentLoop
from brain.trajectory import TrajectoryRecorder

recorder = TrajectoryRecorder()
agent = AgentLoop(
    config=config,
    trajectory_recorder=recorder,
)

# 执行后查看轨迹
result = await agent.run("帮我写一个排序算法")
print(f"Trajectory ID: {result['trajectory_id']}")
print(f"Iterations: {result['iterations']}")
```

### 集成 Curator

```python
from brain.agent import AgentLoop
from brain_curator import Curator

curator = Curator(
    trajectory_recorder=recorder,
    skill_writer=SkillWriter(),
)

agent = AgentLoop(
    config=config,
    trajectory_recorder=recorder,
    curator=curator,
)

# 执行后自动触发 Curator 审查
result = await agent.run("帮我优化代码")
```

### 启用自我进化

```python
from brain.agent import AgentLoop
from brain.skills import get_self_evolution_manager

# 方式1: 自动获取管理器
agent = AgentLoop(config=config)
await agent.start_self_evolution()

# 方式2: 手动设置管理器
manager = get_self_evolution_manager()
agent.set_self_evolution_manager(manager)
await agent.start_self_evolution()

# 执行
result = await agent.run("搜索 Python 教程")

# 停止
await agent.stop_self_evolution()
```

## 📊 执行结果

```python
result = {
    "response": "已为您搜索到以下 Python 教程...",
    "reasoning_steps": [
        "用户想要搜索 Python 教程",
        "需要使用 web_search 工具",
        "执行搜索并返回结果"
    ],
    "tool_calls": [
        {"tool": "web_search", "params": {"query": "Python 教程"}}
    ],
    "iterations": 2,
    "trajectory_id": "traj-abc123",
    "metadata": {
        "state": "done",
        "llm_used": True,
        "learned_skills_used": 0
    }
}
```

## ⚙️ 配置选项

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `max_iterations` | 10 | 最大迭代次数 |
| `timeout_seconds` | 60.0 | 超时时间 |
| `enable_memory` | True | 启用记忆 |
| `enable_skills` | True | 启用技能 |
| `enable_curator` | True | 启用 Curator |
| `enable_trajectory` | True | 启用轨迹记录 |
| `enable_self_evolution` | True | 启用自我进化 |
| `system_prompt` | - | 系统提示词 |

## 🔄 执行流程

```
AgentLoop.run(user_input)
    ↓
创建轨迹记录 (TrajectoryRecorder)
    ↓
循环 (最多 max_iterations 次)
    ├─ Thought: LLM 推理下一步
    ├─ Action: 执行工具
    ├─ Observation: 获取结果
    └─ 检查是否完成
    ↓
结束轨迹记录
    ↓
触发 Curator 审查 (异步)
    ↓
触发自我进化检查 (异步)
    ↓
返回结果
```

### 自我进化触发

- **每 10 轮对话**: 触发 Curator 审查
- **每 5 轮对话**: 触发生命周期检查
- **每次工具调用**: 记录技能使用

## 📝 API 参考

### AgentConfig

```python
@dataclass
class AgentConfig:
    max_iterations: int = 10
    timeout_seconds: float = 60.0
    enable_memory: bool = True
    enable_skills: bool = True
    enable_curator: bool = True
    enable_trajectory: bool = True
    enable_self_evolution: bool = True
    system_prompt: str = "你是一个智能助手..."
```

### AgentLoop

| 方法 | 说明 |
|------|------|
| `run(user_input, context)` | 执行 Agent |
| `set_llm_provider(provider)` | 设置 LLM |
| `set_trajectory_recorder(recorder)` | 设置轨迹记录器 |
| `set_curator(curator)` | 设置 Curator |
| `set_self_evolution_manager(manager)` | 设置自我进化管理器 |
| `start_self_evolution()` | 启动自我进化 |
| `stop_self_evolution()` | 停止自我进化 |
| `record_skill_usage(skill_id)` | 记录技能使用 |
| `get_state()` | 获取状态 |
| `reset()` | 重置 Agent |

## 🧪 测试

```bash
# 运行 Agent Loop 测试
pytest tests/unit/brain/test_agent_loop.py -v
```

## 📚 相关模块

- [brain/llm](../llm/) - LLM Provider
- [brain/trajectory](../trajectory/) - 轨迹记录
- [brain_curator](../brain_curator/) - Curator 自我进化
- [brain/skills](../skills/) - 技能系统

## 🔄 更新日志

- **2026-05-31**: 集成自我进化管理器,添加 `enable_self_evolution` 配置,自动触发技能使用追踪和 Curator 审查

---

*最后更新: 2026-05-31*
