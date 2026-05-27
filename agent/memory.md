# Memory System - 记忆系统定义

> **文件位置**: `agent/memory.md`  
> **用途**: 定义 Agent 的记忆类型、存储方式和检索机制  
> **灵感来源**: Hermes Agent Memory System、OpenClaw Memory

---

## 🧠 记忆系统概述

记忆系统是 Agent 理解和响应用户的重要基础。通过不同类型的记忆，Agent 能够：

1. **理解上下文** - 知道当前对话的背景
2. **保持连贯** - 记住之前的交互
3. **个性化服务** - 了解用户的偏好
4. **积累知识** - 从历史中学习

### 记忆类型

```
┌─────────────────────────────────────────────────────────────┐
│                   Memory System Architecture                   │
├─────────────────────────────────────────────────────────────┤
│  1. Working Memory (工作记忆)                                 │
│     - 当前对话上下文                                          │
│     - 短期任务信息                                            │
│     - 容量: ~10-15 个对话轮次                                 │
├─────────────────────────────────────────────────────────────┤
│  2. Session Memory (会话记忆)                                 │
│     - 整个会话的历史                                          │
│     - 用户偏好记录                                            │
│     - 容量: 整个会话                                          │
├─────────────────────────────────────────────────────────────┤
│  3. Semantic Memory (语义记忆)                                │
│     - 结构化的知识                                            │
│     - Agent 能力定义                                          │
│     - 工具使用规范                                            │
│     - 容量: 无限制                                            │
├─────────────────────────────────────────────────────────────┤
│  4. Episodic Memory (情景记忆)                               │
│     - 历史会话摘要                                            │
│     - 重要事件记录                                            │
│     - 容量: 可配置                                            │
├─────────────────────────────────────────────────────────────┤
│  5. Long-term Memory (长期记忆) [待实现]                     │
│     - 跨会话持久化                                            │
│     - 用户画像                                                │
│     - 学习积累                                                │
│     - 容量: 可配置                                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 记忆类型详解

### 1. Working Memory (工作记忆)

**定义**: 当前对话的实时上下文信息

**内容**:
- 最近 10-15 轮对话内容
- 当前任务的状态
- 临时变量和中间结果

**特点**:
- 🔄 **易失性** - 随对话结束而消失
- ⚡ **高速访问** - 最低延迟
- 📉 **容量有限** - 需要定期清理

**示例**:
```
[Working Memory 片段]
- 用户正在询问如何打开浏览器
- 刚刚执行了打开 Edge 浏览器的命令
- 用户还没有确认是否成功
```

### 2. Session Memory (会话记忆)

**定义**: 整个会话的完整记录

**内容**:
- 所有对话消息
- 任务执行历史
- 用户反馈
- 错误记录

**特点**:
- 💾 **会话级持久** - 会话期间完整保留
- 🔍 **可检索** - 支持历史查询
- 🗑️ **会话结束清理** - 可选择存档

**结构**:
```json
{
    "session_id": "abc123",
    "messages": [
        {"role": "user", "content": "打开浏览器", "timestamp": "..."},
        {"role": "assistant", "content": "已为您打开浏览器", "timestamp": "..."}
    ],
    "context": {
        "task": "open_browser",
        "status": "completed"
    }
}
```

### 3. Semantic Memory (语义记忆)

**定义**: Agent 的结构性知识和规范

**内容**:
- **agent.md** - Agent 角色定义
- **tools.md** - 工具使用规范
- **capabilities.md** - 能力清单
- 系统指令
- Prompt 模板

**特点**:
- 📚 **高度结构化** - 清晰定义
- 🔒 **相对稳定** - 变更频率低
- 📖 **可解释** - 易于理解和修改

**访问方式**:
```python
# 语义记忆加载
semantic_memory = {
    "agent_identity": load_file("agent/agent.md"),
    "tools_spec": load_file("agent/tools.md"),
    "capabilities": load_file("agent/capabilities.md")
}
```

### 4. Episodic Memory (情景记忆)

**定义**: 历史会话中的重要事件和模式

**内容**:
- 会话摘要
- 成功案例
- 失败教训
- 用户偏好模式

**特点**:
- 📝 **事件导向** - 记录具体发生的事
- 🎯 **可总结** - 提取通用模式
- 📊 **可分析** - 支持模式识别

**示例**:
```
[Episodic Memory Entry]
{
    "episode_id": "ep_001",
    "timestamp": "2026-05-25 10:00:00",
    "summary": "用户请求打开浏览器并搜索天气",
    "outcome": "success",
    "user_satisfaction": "high",
    "lessons": [
        "用户偏好使用 Edge 浏览器",
        "喜欢简洁的确认信息"
    ]
}
```

### 5. Long-term Memory (长期记忆) [待实现]

**定义**: 跨会话的持久化知识

**内容**:
- 用户画像
- 偏好设置
- 累积学习
- 个性化配置

**特点**:
- 💾 **持久化** - 永久存储
- 🎯 **个性化** - 高度定制
- 🧠 **持续学习** - 不断更新

---

## 🔍 记忆检索机制

### 检索策略

```
用户查询
    ↓
┌────────────────────────────────────┐
│  Query Understanding (LLM)         │
│  - 理解查询意图                     │
│  - 提取关键实体                     │
│  - 确定检索范围                     │
└────────────────────────────────────┘
    ↓
┌────────────────────────────────────┐
│  Memory Retrieval                  │
│  - Working Memory (最高优先级)      │
│  - Session Memory                   │
│  - Episodic Memory                  │
│  - Semantic Memory                  │
│  - Long-term Memory                │
└────────────────────────────────────┘
    ↓
┌────────────────────────────────────┐
│  Relevance Scoring (LLM)          │
│  - 计算相关性分数                    │
│  - 排序结果                         │
│  - 过滤噪音                         │
└────────────────────────────────────┘
    ↓
相关记忆上下文
```

### 检索优先级

| 记忆类型 | 优先级 | 延迟 | 相关性 |
|---------|--------|------|--------|
| Working | 1 (最高) | <1ms | 当前任务 |
| Session | 2 | <5ms | 会话历史 |
| Episodic | 3 | <10ms | 模式匹配 |
| Semantic | 4 | <10ms | 知识查询 |
| Long-term | 5 | <50ms | 用户画像 |

---

## 📊 记忆容量管理

### 容量限制

```python
MEMORY_CONFIG = {
    "working_memory": {
        "max_messages": 15,          # 最大消息数
        "max_tokens": 4000,          # 最大 token 数
        "strategy": "sliding_window" # 滑动窗口
    },
    
    "session_memory": {
        "max_messages": 1000,        # 最大消息数
        "max_storage_mb": 100,        # 最大存储 MB
        "strategy": "summary"         # 到达限制后总结
    },
    
    "episodic_memory": {
        "max_episodes": 100,         # 最大情景数
        "retention_days": 30,         # 保留天数
        "strategy": "importance"       # 基于重要性
    },
    
    "long_term_memory": {
        "max_vectors": 10000,         # 最大向量数
        "retention_days": 365,         # 保留天数
        "strategy": "importance"       # 基于重要性
    }
}
```

### 清理策略

1. **工作记忆清理**: 滑动窗口，保持最近 N 条
2. **会话记忆压缩**: 超过限制时生成摘要
3. **情景记忆淘汰**: 低重要性优先淘汰
4. **长期记忆整合**: 相似记忆合并

---

## 🔄 记忆同步机制

### 同步流程

```
任务执行
    ↓
生成记忆更新
    ↓
┌────────────────────────────────────┐
│  Memory Update                     │
│  1. Working Memory: 即时更新        │
│  2. Session Memory: 延迟批处理       │
│  3. Episodic Memory: 任务完成后      │
│  4. Long-term Memory: 后台异步      │
└────────────────────────────────────┘
    ↓
持久化存储 [可选]
```

### 一致性保证

- **最终一致性** - 不保证实时同步
- **事件驱动** - 重要事件触发同步
- **批量优化** - 减少 IO 操作

---

## 🛠️ 实现接口

### 记忆访问 API

```python
class MemorySystem:
    """Agent 记忆系统接口"""
    
    # 工作记忆
    def get_working_context(self, max_messages: int = 10) -> List[Message]:
        """获取当前工作上下文"""
        
    def add_working(self, message: Message):
        """添加工作记忆"""
        
    # 会话记忆
    def get_session_history(self) -> SessionHistory:
        """获取会话历史"""
        
    def archive_session(self):
        """存档当前会话"""
        
    # 情景记忆
    def add_episode(self, episode: Episode):
        """添加情景记忆"""
        
    def retrieve_episodes(self, query: str) -> List[Episode]:
        """检索情景记忆"""
        
    # 长期记忆
    def store_long_term(self, key: str, value: Any):
        """存储长期记忆"""
        
    def recall_long_term(self, query: str) -> List[Any]:
        """召回长期记忆"""
```

---

## 📝 记忆使用示例

### 示例 1: 理解上下文

```
用户: 打开那个文件夹
Agent: 
  [检索 Working Memory]
  - 最近打开的是"桌面文件夹"
  [结论]: 用户指的是"桌面文件夹"
  [执行]: 打开桌面文件夹
```

### 示例 2: 个性化服务

```
用户: 帮我搜索一下 Python 教程
Agent:
  [检索 Long-term Memory]
  - 用户偏好: 中文内容
  - 上次搜索: JavaScript 教程
  [结论]: 提供中文 Python 教程
  [执行]: 用中文关键词搜索
```

### 示例 3: 从错误中学习

```
用户: 上次那个命令不行
Agent:
  [检索 Episodic Memory]
  - 失败记录: 上次执行了 'start chrome' 但用户使用 Edge
  [结论]: 用户使用 Edge，不是 Chrome
  [调整]: 改用 Edge 浏览器
  [更新]: 记录这次成功
```

---

## 🚀 未来增强

### 待实现功能

1. **向量数据库集成**
   - 使用 FAISS 或 Milvus
   - 高效相似度检索

2. **记忆重要性评分**
   - LLM 自动评估
   - 基于反馈调整

3. **跨 Agent 记忆共享**
   - 多 Agent 协作
   - 知识共享

4. **记忆可视化**
   - 查看记忆状态
   - 调试记忆系统

---

## 📌 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| 1.0 | 2026-05-25 | 初始版本，定义记忆系统架构 |

---

## 🔗 相关文档

- [agent.md](agent.md) - Agent 角色定义
- [tools.md](tools.md) - 工具使用规范
- [capabilities.md](capabilities.md) - 能力清单
- [../core/session.py](../core/session.py) - 会话管理实现
- [../advanced_reasoning/memory_manager.py](../advanced_reasoning/memory_manager.py) - 记忆管理实现 [待实现]