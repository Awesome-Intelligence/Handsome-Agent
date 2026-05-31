# 移除意图识别层 - 架构迁移指南

## 📋 变更概述

### 旧架构（带意图识别）
```
用户输入 → 意图分类器 → 工具选择 → 工具执行 → 响应
           ↓
      预定义意图类型
      (conversation/operation/coding)
```

### 新架构（LLM 直接决策）
```
用户输入 + 工具列表 + 上下文 → LLM 直接决策 → 工具执行 → 响应
                              ↓
                          无预定义意图
                          LLM 自己理解并选择
```

## 🎯 核心变化

### 1. 移除的组件
- ❌ `IntentClassifier` - 意图分类器
- ❌ `LLMIntentService` - LLM 意图服务
- ❌ `IntentResult` - 意图结果数据类
- ❌ 预定义的意图类型（conversation/operation/coding）

### 2. 新增的组件
- ✅ `LLMToolSelector` - LLM 驱动的工具选择器
- ✅ `SimplifiedAgent` - 简化版 Agent
- ✅ `ToolSelectionResult` - 工具选择结果
- ✅ `ToolDefinition` - 工具定义

### 3. 设计原则
1. **LLM 自主决策** - 不做预分类，让 LLM 自己理解
2. **工具 Schema 驱动** - 提供完整工具定义，LLM 理解能力
3. **上下文感知** - 会话历史和记忆提供上下文
4. **简单降级** - 无 LLM 时使用关键词回退

## 📝 迁移步骤

### Step 1: 替换导入

**旧代码：**
```python
from core.router import IntentClassifier, TaskRouter
from core.llm_intent_service import LLMIntentService, IntentResult

# 初始化
intent_classifier = IntentClassifier()
intent_service = LLMIntentService(llm_provider)
```

**新代码：**
```python
from core.llm_tool_selector import LLMDrivenDecisionEngine
from core.simplified_agent import SimplifiedAgent

# 初始化
decision_engine = LLMDrivenDecisionEngine(llm_provider=llm_provider)
```

### Step 2: 替换决策流程

**旧代码：**
```python
# 1. 意图识别
intent = intent_classifier.classify(user_input)

# 2. 根据意图选择工具
if intent == 'operation':
    tool = select_operation_tool(...)
elif intent == 'conversation':
    # 直接回复
    response = await llm.generate(user_input)

# 3. 执行
if tool:
    result = await tool.execute(...)
```

**新代码：**
```python
# 单一决策步骤
result = await decision_engine.process(
    user_input,
    conversation_history=history,
    context={'memory': relevant_memories}
)

# 检查结果类型
if result['type'] == 'tool_execution':
    tool_result = result['result']
    needs_summary = True
elif result['type'] == 'direct_response':
    # 需要 LLM 直接回复
    needs_summary = False
```

### Step 3: 工具注册

**旧代码：**
```python
# 注册到路由器
router.register_route(RouteConfig(
    id='web_search',
    handler=web_search_handler,
    intent_types=['operation']
))
```

**新代码：**
```python
# 注册工具
decision_engine.register_tool(
    name='web_search',
    description='Search the web for information',
    parameters={'query': 'search query string'},
    handler=web_search_handler,
    category='information'
)
```

### Step 4: 处理响应

**旧代码：**
```python
# 意图驱动的响应处理
if intent_result.intent_type == 'conversation':
    response = format_conversation_response(result)
elif intent_result.intent_type == 'operation':
    response = format_operation_response(result)
```

**新代码：**
```python
# 类型驱动的响应处理
if result['type'] == 'tool_execution':
    tool_output = result['result']['result']
    response = f"执行结果: {tool_output}"
elif result['type'] == 'direct_response':
    response = "这里写你的直接回复逻辑"
```

## 🔧 完整示例

### 旧代码
```python
from core.router import IntentClassifier
from core.agent import Agent

class OldAgent:
    def __init__(self, llm):
        self.classifier = IntentClassifier(llm)
        self.agent = Agent(llm)

    async def handle(self, user_input: str):
        # 1. 识别意图
        intent = self.classifier.classify(user_input)

        # 2. 根据意图处理
        if intent == 'operation':
            # 选择工具
            tool = self.select_operation_tool(user_input)
            result = await tool.execute(user_input)
            return f"操作结果: {result}"
        else:
            # 对话回复
            return await self.agent.chat(user_input)
```

### 新代码
```python
from core.llm_tool_selector import LLMDrivenDecisionEngine

class NewAgent:
    def __init__(self, llm):
        self.engine = LLMDrivenDecisionEngine(llm_provider=llm)
        # 注册工具
        self._register_tools()

    def _register_tools(self):
        self.engine.register_tool(
            name='calculator',
            description='Calculate math expressions',
            parameters={'expression': 'math string'},
            handler=self.calc_handler
        )

    async def calc_handler(self, params, context):
        expr = params.get('expression', '0')
        return {'result': eval(expr)}

    async def handle(self, user_input: str, history=None):
        # 单一决策流程
        result = await self.engine.process(
            user_input,
            conversation_history=history or []
        )

        # 根据结果类型处理
        if result['type'] == 'tool_execution':
            return f"计算结果: {result['result']['result']}"
        else:
            # 直接回复逻辑
            return "让我帮你处理..."
```

## 📊 对比

| 方面 | 旧架构 | 新架构 |
|------|--------|--------|
| **决策步骤** | 2步（意图→工具） | 1步（直接决策） |
| **意图类型** | 预定义3种 | 无（LML自己理解） |
| **代码复杂度** | 高 | 低 |
| **灵活性** | 受限于意图类型 | 完全灵活 |
| **LLM 利用** | 部分 | 完整 |
| **延迟** | 较高 | 较低 |

## ⚠️ 注意事项

### 1. LLM Provider 必须可用
新架构强烈依赖 LLM，如果没有 LLM：
```python
# 使用降级模式
engine = LLMDrivenDecisionEngine(
    llm_provider=None,  # 无 LLM
    enable_llm_selection=False  # 禁用 LLM 选择
)
# 会使用关键词回退
```

### 2. 工具描述很重要
LLM 靠工具描述理解能力，描述要清晰：
```python
# ✅ 好描述
"Search for information on the web"

# ❌ 差描述
"Search tool"
```

### 3. 保留会话历史
新架构依赖上下文：
```python
result = await engine.process(
    user_input,
    conversation_history=session.messages[-10:]  # 最近10条
)
```

## 🧪 测试建议

### 1. 基础功能测试
```python
async def test_direct_routing():
    engine = LLMDrivenDecisionEngine(mock_llm)

    # 注册工具
    engine.register_tool(
        name='calculator',
        description='Calculate math',
        handler=calc_handler
    )

    # 测试
    result = await engine.process("What is 2+2?")
    assert result['type'] == 'tool_execution'
    assert result['tool'] == 'calculator'
```

### 2. 降级测试
```python
async def test_fallback():
    engine = LLMDrivenDecisionEngine(llm_provider=None)

    # 注册工具
    engine.register_tool(...)

    # 测试关键词回退
    result = await engine.process("计算 2+2")
    assert result['type'] == 'tool_execution'
```

## 🚀 后续优化

### 1. 工具调用链
支持多步工具调用：
```python
result = await engine.process(user_input, enable_chain=True)
```

### 2. 工具选择优化
学习用户偏好：
```python
engine = LLMDrivenDecisionEngine(
    llm_provider=llm,
    learn_preferences=True  # 学习用户习惯
)
```

### 3. 缓存优化
缓存相似请求的决策：
```python
engine = LLMDrivenDecisionEngine(
    llm_provider=llm,
    enable_cache=True  # 启用决策缓存
)
```

## 📚 相关文件

- `core/llm_tool_selector.py` - LLM 工具选择器
- `core/simplified_agent.py` - 简化版 Agent 示例
- `core/llm_intent_service.py` - 旧意图服务（待移除）
- `core/router.py` - 旧路由器（待移除）

---

**迁移时间**：预计 2-3 小时
**风险等级**：中等（需要充分测试）
**建议**：先在非生产环境测试
