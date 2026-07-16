# Agent-Z 待办事项

> 本文件记录项目的待办功能和优化项

---

## 高优先级

### 上下文系统优化

#### 1. 系统提示缓存

**描述**: 为 ContextManager 添加系统提示缓存，减少重复构建

**参考 Hermes**: `agent._cached_system_prompt` 会话级缓存

**实现思路**:
```python
class ContextManager:
    def __init__(self, ...):
        self._system_prompt_cache: Optional[str] = None
        self._cache_key: str = ""
    
    def build(self, ...):
        # 生成 cache_key
        cache_key = self._make_cache_key(conversation_history, tools, purpose)
        
        # 如果缓存有效，直接返回
        if cache_key == self._cache_key:
            return self._cached_result
        
        # 否则重新构建并缓存
        result = self._do_build(...)
        self._cache_key = cache_key
        self._cached_result = result
        return result
    
    def invalidate_cache(self):
        """使缓存失效（上下文压缩后调用）"""
        self._system_prompt_cache = None
        self._cache_key = ""
```

**验收标准**:
- [x] 添加 `_stable_cache` / `_context_cache` / `_cache_hits` / `_cache_misses`（ContextBuilder 内部）
- [x] 实现 `invalidate_stable_cache()` 方法（ContextManager 顶层 API）
- [x] 实现 `get_cache_stats()` 方法（ContextManager 顶层 API）
- [x] 添加缓存命中/未命中日志（build_parts debug 日志）
- [x] 切换模型时自动清除 stable 缓存（LLMClient.set_active_model）

---

## 中优先级

### 上下文系统增强

#### 2. 三层系统提示架构

**描述**: 参考 Hermes 的系统提示三层架构 (stable/context/volatile)

**参考 Hermes**: `agent/system_prompt.py` 的三层设计

**Hermes 设计**:
```
┌─────────────────────────────────────────────────────────────┐
│ stable (稳定层) ← 每个会话构建一次，缓存复用                  │
│  - Agent 身份 (SOUL.md)                                     │
│  - 工具指导                                                  │
│  - 技能提示                                                  │
├─────────────────────────────────────────────────────────────┤
│ context (上下文层) ← 依赖 cwd，可能变化                      │
│  - system_message (调用者提供)                               │
│  - 上下文文件 (AGENTS.md, .cursorrules)                    │
├─────────────────────────────────────────────────────────────┤
│ volatile (变动层) ← 每次构建都变化                          │
│  - 记忆快照 (memory_manager)                                 │
│  - USER.md profile                                         │
│  - 时间戳/会话/模型信息                                     │
└─────────────────────────────────────────────────────────────┘
```

**实现思路**:
```python
class SystemPromptBuilder:
    """三层系统提示构建器"""
    
    def build(self, system_message=None):
        # 1. stable 层（缓存）
        stable = self._get_cached_stable()
        
        # 2. context 层
        context = self._build_context_layer(system_message)
        
        # 3. volatile 层（每次构建）
        volatile = self._build_volatile_layer()
        
        return f"{stable}\n\n{context}\n\n{volatile}"
    
    def _get_cached_stable(self):
        """获取缓存的 stable 层"""
        if self._stable_cache:
            return self._stable_cache
        
        self._stable_cache = self._build_stable_layer()
        return self._stable_cache
    
    def invalidate_stable_cache(self):
        """使 stable 层缓存失效"""
        self._stable_cache = None
```

**验收标准**:
- [x] 定义 `StableLayer`, `ContextLayer`, `VolatileLayer` 类或方法
- [x] stable 层支持会话级缓存
- [x] volatile 层每次重新构建
- [x] 提供 `invalidate_stable_cache()` 方法
- [x] Base Layer 注入 Agent 自我认知（version/OS/Python/tools_count/技能数）
- [x] Session Layer 注入对话元信息（rounds/used_tools/start_time/session_id）
- [x] stable 层缓存 bug 修复（避免缓存取值后立即被覆盖）
- [x] context 层按内容 hash 缓存
- [x] 缓存命中率日志

---

## 低优先级（未开始）

### LLM 调用优化

#### 3. 前缀缓存优化 (Prompt Caching)

**描述**: 支持 Anthropic 等提供商的前缀缓存功能

**参考 Hermes**: `apply_anthropic_cache_control()` 函数

**Hermes 设计**:
```python
# conversation_loop.py
if agent._use_prompt_caching:
    api_messages = apply_anthropic_cache_control(
        api_messages,
        cache_boundary_first=system_prompt_plus_first_turn,
        cache_boundary_last=max(0, len(messages) - agent._cache_backtrack),
        max_age=agent._cache_max_age
    )
```

**实现思路**:
```python
class PromptCacheOptimizer:
    """提示缓存优化器"""
    
    def __init__(self, provider_type: str = "openai"):
        self.provider_type = provider_type
    
    def apply_cache(
        self,
        messages: List[Dict],
        system_prompt: str,
        cache_boundaries: dict = None
    ) -> List[Dict]:
        """应用提供商特定的缓存优化"""
        if self.provider_type == "anthropic":
            return self._apply_anthropic_cache(messages, cache_boundaries)
        elif self.provider_type == "openai":
            return self._apply_openai_cache(messages)
        return messages
    
    def _apply_anthropic_cache(
        self,
        messages: List[Dict],
        boundaries: dict
    ) -> List[Dict]:
        """Anthropic 缓存控制"""
        # 在适当位置添加 cache_control 字段
        ...
```

**验收标准**:
- [ ] 创建 `PromptCacheOptimizer` 类
- [ ] 支持 Anthropic cache_control
- [ ] 支持 OpenAI 缓存提示
- [ ] 在 `LLMClient` 中集成缓存优化

---

## 已完成

### 上下文系统

- [x] 统一 LLM 调用入口 (`LLMClient`)
- [x] 统一上下文管理 (`ContextManager`)
- [x] 辅助任务分类 (`LLMTaskType`)
- [x] 上下文压缩 (`ContextCompressor`)
- [x] 记忆预取 (`ContextBuilder`)
- [x] 用户画像加载 (`_get_user_profile()`)
- [x] 工具选择上下文 (`TOOL_SELECTION`)
- [x] 直接回复上下文 (`DIRECT_RESPONSE`)
- [x] 模式判断上下文 (`MODE_DECISION`)

### 模块迁移

- [x] Agent 主入口使用 `ContextManager`
- [x] Curator 使用 `LLMClient`
- [x] Task Planner 使用 `LLMClient`

---

## 参考资料

- Hermes 源码: `E:/hermes-agent-study/agent/system_prompt.py`
- Hermes 源码: `E:/hermes-agent-study/agent/conversation_loop.py`
- Hermes 源码: `E:/hermes-agent-study/agent/auxiliary_client.py`
