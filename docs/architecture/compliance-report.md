# 架构合规性分析报告

> **分析日期**: 2026-05-25  
> **项目**: Agent-Z  
> **目标架构**: 统一 Agent Harness 架构

---

## 1. 架构概览

### 1.1 当前架构层级

```
┌─────────────────────────────────────────┐
│         CLI / Gateway (用户层)          │
├─────────────────────────────────────────┤
│     CustomAgent (控制层/编排层)           │
├─────────────────────────────────────────┤
│  Router │ SkillManager │ SessionManager │
├─────────────────────────────────────────┤
│       LLM Providers (推理层)             │
├─────────────────────────────────────────┤
│        Tools (工具层)                    │
└─────────────────────────────────────────┘
```

### 1.2 标准 Harness 架构

```
┌─────────────────────────────────────────────┐
│           Interface Layer (接口层)          │
│     CLI │ API Gateway │ WebSocket           │
├─────────────────────────────────────────────┤
│           Agent Core (Agent核心)            │
│  ┌─────────────────────────────────────┐   │
│  │         Intent Recognition           │   │
│  │     (LLM-powered Intent Parser)      │   │
│  └─────────────────────────────────────┘   │
│  ┌─────────────────────────────────────┐   │
│  │         Task Planning                │   │
│  │     (Sub-task Decomposition)          │   │
│  └─────────────────────────────────────┘   │
│  ┌─────────────────────────────────────┐   │
│  │         Memory System               │   │
│  │   (Short-term + Long-term)           │   │
│  └─────────────────────────────────────┘   │
├─────────────────────────────────────────────┤
│        Tool Abstraction Layer              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ Browser  │ │ Terminal │ │  File    │   │
│  │  Tools   │ │  Tools   │ │  System   │   │
│  └──────────┘ └──────────┘ └──────────┘   │
├─────────────────────────────────────────────┤
│        LLM Provider Layer                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ MiniMax │ │ OpenAI  │ │  Local   │   │
│  │  API    │ │   API   │ │  Model   │   │
│  └──────────┘ └──────────┘ └──────────┘   │
└─────────────────────────────────────────────┘
```

---

## 2. 合规性评估

### 2.1 当前状态

| 组件 | 状态 | 说明 |
|------|------|------|
| **接口层** | ⚠️ 部分合规 | CLI 完整，Gateway 简化 |
| **Intent Recognition** | ✅ 已改造 | 使用 LLM |
| **Task Planning** | ❌ 缺失 | 无子任务分解 |
| **Memory System** | ⚠️ 基础 | 仅 Session 会话 |
| **Tool Abstraction** | ✅ 完整 | 统一 ToolRegistry |
| **LLM Provider** | ✅ 完整 | 适配器模式 |

### 2.2 详细分析

#### ✅ 已符合 Harness 的部分

1. **模块化设计**
   - `BaseAgentModule` 抽象基类
   - `Router` 与 `Handler` 分离
   - `SkillManager` 与 `ToolRegistry` 解耦

2. **LLM 集成**
   - `llm_intent_service.py` - 统一 LLM 意图服务
   - `llm_provider` 适配器模式
   - 降级策略（尽管用户要求移除 fallback）

3. **工具抽象**
   - `@register_tool` 装饰器
   - `ToolRegistry` 统一管理
   - 类型安全的参数定义

#### ❌ 需要增强的部分

1. **Task Planning**
   - 当前没有子任务分解能力
   - 无法处理复杂的多步骤请求
   - 建议：添加 `TaskPlanner` 模块

2. **Memory System**
   - 仅支持短期会话内存
   - 缺少长期记忆能力
   - 建议：集成 `plugins/memory` 模块

3. **Interface Layer**
   - Gateway 功能简化
   - 缺少流式响应支持
   - 建议：完善 Gateway 中间件

---

## 3. 架构调整建议

### 3.1 短期调整（立即执行）

#### 3.1.1 移除所有 Hardcoded Fallback

**当前问题**:
```python
# router_handlers.py 中仍有 fallback 逻辑
try:
    # LLM 意图识别
except:
    # 降级到规则匹配 ❌ 这是不允许的
```

**调整方案**:
```python
# 删除所有 fallback 逻辑，改为错误传播
if not llm_intent_service.is_llm_available():
    raise SystemError("LLM provider not configured")
    
result = await llm_intent_service.recognize_intent(...)
if not result.success:
    return f"Intent recognition failed: {result.error}"
```

#### 3.1.2 完善 LLM Intent Service

**调整**:
- 在 `CustomAgent.__init__` 中初始化 `llm_intent_service`
- 所有 handler 都通过 `llm_intent_service` 获取意图
- 移除 `router.py` 中的硬编码关键词匹配

### 3.2 中期调整（1-2周）

#### 3.2.1 添加 Task Planner

```python
# core/task_planner.py
class TaskPlanner:
    """Decompose complex tasks into sub-tasks using LLM."""
    
    async def plan(self, task: str, context: Dict) -> List[SubTask]:
        prompt = f"""将以下任务分解为可执行的子任务：
        
任务：{task}
上下文：{context}

返回 JSON 格式的子任务列表：
{{
    "subtasks": [
        {{"id": 1, "description": "子任务描述", "depends_on": []}},
        ...
    ]
}}"""
        # LLM 调用和解析
```

#### 3.2.2 增强 Memory System

```python
# plugins/memory/memory_manager.py
class MemoryManager:
    """Manage both short-term and long-term memory."""
    
    def __init__(self):
        self.short_term = SessionMemory()  # 当前会话
        self.long_term = PersistentMemory()  # 跨会话
```

### 3.3 长期调整（1个月+）

#### 3.3.1 完善 Gateway

- 添加认证中间件
- 实现流式响应
- 添加限流和监控

---

## 4. 实施路线图

### Phase 1: 纯 LLM 意图识别 ✅
- [x] 创建 `llm_intent_service.py`
- [x] 移除 `router.py` 中的硬编码关键词
- [ ] 删除所有 fallback 逻辑
- [ ] 统一所有 handler 使用 `llm_intent_service`

### Phase 2: Task Planning
- [ ] 创建 `TaskPlanner` 模块
- [ ] 实现子任务分解
- [ ] 添加依赖管理

### Phase 3: Memory Enhancement
- [ ] 集成 `plugins/memory`
- [ ] 实现长期记忆
- [ ] 添加记忆检索

### Phase 4: Interface Enhancement
- [ ] 完善 Gateway 中间件
- [ ] 添加流式响应
- [ ] 实现监控和日志

---

## 5. 架构检查清单

### 5.1 核心原则

- [x] 所有意图识别使用 LLM
- [ ] 无硬编码的 fallback 逻辑
- [ ] 统一的错误处理
- [ ] 模块间松耦合

### 5.2 代码质量

- [ ] 所有 handler 使用 `llm_intent_service`
- [ ] 移除 `IntentClassifier` 的硬编码关键词
- [ ] 移除 `router_handlers.py` 中的 command_mapping
- [ ] 移除 `router_handlers.py` 中的 folder_mapping

### 5.3 文档更新

- [ ] 更新 `architecture_decisions.md`
- [ ] 更新 `core/README.md`
- [ ] 添加新的 ADR 记录
- [ ] 更新架构图

---

## 6. 结论

当前项目架构**基本符合** Harness 模式，但存在以下问题需要调整：

1. **Intent Recognition**: 需要移除所有硬编码 fallback
2. **Task Planning**: 需要添加子任务分解能力
3. **Memory System**: 需要增强记忆管理

**建议立即执行**：
1. 移除 `router_handlers.py` 中所有硬编码映射
2. 统一使用 `llm_intent_service` 进行意图识别
3. 添加 TaskPlanner 模块支持复杂任务

---

**下一步行动**：
1. 删除 `router.py` 中的 `IntentClassifier` 硬编码关键词
2. 删除 `router_handlers.py` 中的 `command_mapping` 和 `folder_mapping`
3. 完成纯 LLM 架构改造