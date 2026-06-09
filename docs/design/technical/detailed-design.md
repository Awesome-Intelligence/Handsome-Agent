# Handsome Agent 详细设计文档

**版本**: v1.0.0  
**最后更新**: 2026-06-09  
**状态**: 正式版

---

## 目录

1. [概述](#一概述)
2. [核心模块类图](#二核心模块类图)
3. [时序图](#三时序图)
4. [核心流程设计](#四核心流程设计)
5. [状态机设计](#五状态机设计)
6. [模块详细设计](#六模块详细设计)

---

## 一、概述

### 1.1 文档目的

本文档提供 Handsome Agent 核心模块的详细设计，包括类图、时序图、流程设计和状态机定义。

### 1.2 设计范围

```
详细设计范围
├── Agent 模块
│   ├── Agent (协调器)
│   ├── AgentResponse
│   └── ActionType
├── ReAct 模块
│   ├── ReActLoop
│   ├── LoopState
│   ├── StepResult
│   └── Decision
├── 工具系统
│   ├── ToolRegistry
│   └── ToolEntry
├── 技能系统
│   ├── SkillRegistry
│   ├── SkillMatcher
│   └── LifecycleManager
├── Curator 模块
│   ├── Curator
│   ├── TrajectoryRecorder
│   └── SkillWriter
└── Rail 模块
    ├── Rail
    └── RailManager
```

---

## 二、核心模块类图

### 2.1 Agent 模块类图

```
┌─────────────────────────────────────────────────────────────────┐
│                         Agent 模块类图                           │
└─────────────────────────────────────────────────────────────────┘

┌───────────────────────────────┐     ┌───────────────────────────────┐
│           Agent               │     │      AgentResponse             │
├───────────────────────────────┤     ├───────────────────────────────┤
│ - llm_provider               │     │ - content: str                │
│ - enable_session: bool      │     │ - tool_used: Optional[str]    │
│ - enable_curator: bool      │     │ - tool_result: Any            │
│ - engine                    │     │ - confidence_score: float     │
│ - _context_manager         │     │ - metadata: Dict              │
│ - _llm_client               │     │ - execution_time: float       │
│ - _session                  │     └───────────────────────────────┘
│ - _trajectory_recorder      │
│ - _curator                  │     ┌───────────────────────────────┐
├───────────────────────────────┤     │       ActionType (Enum)       │
│ + chat()                    │     ├───────────────────────────────┤
│ + _chat_simple()           │     │ TOOL_CALL = "tool_call"       │
│ + _chat_react()            │     │ DIRECT_RESPONSE = "direct"     │
│ + _should_use_react()      │     │ CLARIFICATION = "clarify"      │
│ + get_tool_list()          │     └───────────────────────────────┘
└───────────────┬───────────────┘
                │
                │ uses
                ▼
┌───────────────────────────────┐
│      IntegratedEngine          │
├───────────────────────────────┤
│ - tool_selector                │
│ - _context_manager            │
│ - _llm_client                 │
├───────────────────────────────┤
│ + process()                   │
│ + get_tools_schema()          │
└───────────────────────────────┘
```

### 2.2 ReAct 模块类图

```
┌─────────────────────────────────────────────────────────────────┐
│                        ReAct 模块类图                            │
└─────────────────────────────────────────────────────────────────┘

┌───────────────────────────────┐
│         ReActLoop              │
├───────────────────────────────┤
│ - llm                        │
│ - session_id: str             │
│ - rails: List[Rail]          │
│ - max_iterations: int         │
│ - tools: Dict                 │
│ - _state: LoopState          │
│ - _steps: List[StepResult]    │
├───────────────────────────────┤
│ + run(context)                │
│ + pause()                    │
│ + resume()                   │
│ + abort()                    │
│ + state                      │
│ + steps                      │
└───────────────┬───────────────┘
                │
                │ uses
                ▼
┌───────────────────────────────┐  ┌───────────────────────────────┐
│       LoopState (Enum)        │  │       StepResult              │
├───────────────────────────────┤  ├───────────────────────────────┤
│ RUNNING = "running"          │  │ - step: int                   │
│ PAUSED = "paused"            │  │ - action: str                  │
│ COMPLETED = "completed"      │  │ - tool_name: Optional[str]     │
│ ABORTED = "aborted"          │  │ - parameters: Dict            │
└───────────────────────────────┘  │ - result: Any                │
                                    │ - reasoning: str              │
                                    │ - is_error: bool             │
                                    │ - is_blocked: bool           │
                                    └───────────────────────────────┘

┌───────────────────────────────┐
│         Decision               │
├───────────────────────────────┤
│ - action: str                 │
│ - tool_name: Optional[str]    │
│ - parameters: Dict           │
│ - reasoning: str              │
│ - content: Optional[str]      │
│ - questions: List[str]       │
└───────────────────────────────┘
```

### 2.3 工具系统类图

```
┌─────────────────────────────────────────────────────────────────┐
│                       工具系统类图                              │
└─────────────────────────────────────────────────────────────────┘

┌───────────────────────────────┐
│       ToolRegistry            │
├───────────────────────────────┤
│ - _tools: Dict[str, ToolEntry]│
│ - _toolsets: Dict[str, Set]   │
├───────────────────────────────┤
│ + register(...)              │
│ + unregister(name)           │
│ + get(name)                  │
│ + get_all_tools()            │
│ + get_definitions()          │
│ + execute(name, params)      │
└───────────────┬───────────────┘
                │
                │ creates
                ▼
┌───────────────────────────────┐
│        ToolEntry              │
├───────────────────────────────┤
│ - name: str                   │
│ - toolset: str               │
│ - schema: Dict               │
│ - handler: Callable          │
│ - check_fn: Optional[Callable]│
│ - is_async: bool             │
│ - description: str          │
├───────────────────────────────┤
│ + is_available()             │
│ + get_schema()              │
└───────────────────────────────┘
```

### 2.4 Curator 模块类图

```
┌─────────────────────────────────────────────────────────────────┐
│                       Curator 模块类图                           │
└─────────────────────────────────────────────────────────────────┘

┌───────────────────────────────┐
│          Curator              │
├───────────────────────────────┤
│ - trajectory_recorder         │
│ - skill_writer               │
│ - enable_auto_learn: bool    │
├───────────────────────────────┤
│ + process_trajectory()       │
│ + analyze()                  │
│ + synthesize_skill()         │
└───────────────┬───────────────┘
                │
                │ uses
                ▼
┌───────────────────────────────┐  ┌───────────────────────────────┐
│   TrajectoryRecorder          │  │      SkillWriter              │
├───────────────────────────────┤  ├───────────────────────────────┤
│ - session_id                  │  │ + write(skill)                 │
│ - trajectory: Dict            │  │ + update(skill)                │
│ - _save_path                  │  │ + delete(name)                 │
├───────────────────────────────┤  └───────────────────────────────┘
│ + initialize()               │
│ + add_human_message()        │
│ + add_tool_call()           │
│ + add_tool_response()       │
│ + add_gpt_message()         │
│ + save_trajectory()          │
│ + get_trajectory()           │
└───────────────────────────────┘
```

---

## 三、时序图

### 3.1 对话处理时序图

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Client  │     │  Agent  │     │ ReActLoop│     │  LLM     │     │  Tools   │
└────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                │                │                │
     │ chat(input)    │                │                │                │
     │───────────────►│                │                │                │
     │                │                │                │                │
     │                │ mode decision │                │                │
     │                │───────────────►│                │                │
     │                │                │                │                │
     │                │◄──────────────│ use_react       │                │
     │                │                │                │                │
     │                │ [if ReAct]    │                │                │
     │                │ run(context)  │                │                │
     │                │───────────────►│                │                │
     │                │                │                │                │
     │                │                │ LLM decision  │                │
     │                │                │───────────────►│                │
     │                │                │                │                │
     │                │                │◄──────────────│ decision       │
     │                │                │                │                │
     │                │                │ [if tool_call]│                │
     │                │                │ execute_tool │                │
     │                │                │───────────────────────────────►│
     │                │                │                │                │
     │                │                │◄───────────────────────────────│ result
     │                │                │                │                │
     │                │                │ [repeat until done]│          │
     │                │                │                │                │
     │                │ result        │                │                │
     │◄──────────────│                │                │                │
     │                │                │                │                │
```

### 3.2 工具执行时序图

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Client  │     │  Agent   │     │  Rails   │     │  Tools   │
└────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                │                │
     │ call_tool      │                │                │
     │───────────────►│                │                │
     │                │                │                │
     │                │ before_tool_call │            │
     │                │───────────────►│                │
     │                │                │                │
     │                │◄──────────────│ allowed=true    │
     │                │                │                │
     │                │ execute(tool, params)│          │
     │                │──────────────────────────────────────►│
     │                │                │                │
     │                │◄──────────────────────────────────────│ result
     │                │                │                │
     │                │ after_tool_call │               │
     │                │───────────────►│                │
     │                │                │                │
     │                │◄──────────────│                │
     │                │                │                │
     │ result         │                │                │
     │◄──────────────│                │                │
     │                │                │                │
```

### 3.3 Curator 进化时序图

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Agent   │     │Recorder │     │ Curator │     │  Writer  │
└────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                │                │
     │ chat complete  │                │                │
     │───────────────►│                │                │
     │                │                │                │
     │                │ save_trajectory │              │
     │                │───────────────►│                │
     │                │                │                │
     │                │                │ analyze()     │
     │                │                │                │
     │                │◄──────────────│ trajectory     │
     │                │                │                │
     │                │                │ [if good]     │
     │                │                │ synthesize_skill │
     │                │                │                │
     │                │                │ write(skill)   │
     │                │                │─────────────────────────────►│
     │                │                │                │
     │                │                │◄─────────────────────────────│
     │                │                │                │
     │ completion     │                │                │
     │◄──────────────│                │                │
     │                │                │                │
```

---

## 四、核心流程设计

### 4.1 Agent 决策流程

```
┌─────────────────────────────────────────────────────────────────┐
│                       Agent 决策流程                             │
└─────────────────────────────────────────────────────────────────┘

[用户输入]
      │
      ▼
┌─────────────┐
│ 模式判断    │ ← LLM 判断任务复杂度
└──────┬──────┘
       │
  ┌────┴────┐
  │         │
  ▼         ▼
[简单任务] [复杂任务]
  │         │
  ▼         ▼
┌─────────────┐    ┌─────────────────────────────────────────┐
│ 直接响应   │    │            ReAct 循环                    │
└──────┬─────┘    │                                          │
       │          │ ┌─────────────────────────────────┐    │
       │          │ │ 1. LLM 决策下一步                │    │
       │          │ └───────────────┬─────────────────┘    │
       │          │                 │                      │
       │          │    ┌────────────┴────────────┐        │
       │          │    ▼                         ▼        │
       │          │ [工具调用]           [直接响应]        │
       │          │    │                         │        │
       │          │    ▼                         │        │
       │          │ ┌─────────────┐              │        │
       │          │ │ Rail 前置   │              │        │
       │          │ └──────┬──────┘              │        │
       │          │        │                     │        │
       │          │        ▼                     │        │
       │          │ ┌─────────────┐              │        │
       │          │ │ 执行工具    │              │        │
       │          │ └──────┬──────┘              │        │
       │          │        │                     │        │
       │          │        ▼                     │        │
       │          │ ┌─────────────┐              │        │
       │          │ │ Rail 后置   │              │        │
       │          │ └──────┬──────┘              │        │
       │          │        │                     │        │
       │          │        └──────────┬──────────┘        │
       │          │                   │                     │
       │          │                   ▼                     │
       │          │            [继续循环?]                │
       │          │                   │                   │
       │          └───────────────────┼───────────────────┘
       │                              │
       ▼                              ▼
┌─────────────┐                 ┌─────────────┐
│ 返回结果    │                 │ 返回结果    │
└──────┬──────┘                 └──────┬──────┘
       │                              │
       └──────────────┬───────────────┘
                      ▼
              [Curator 分析] (可选)
                      │
                      ▼
                [轨迹保存]
```

### 4.2 上下文压缩流程

```
┌─────────────────────────────────────────────────────────────────┐
│                     上下文压缩流程                              │
└─────────────────────────────────────────────────────────────────┘

[对话历史过长]
      │
      ▼
┌─────────────┐
│ 检查阈值    │ ← 超过 max_context_messages
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 构建摘要    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ LLM 摘要    │ ← 保留关键信息
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 压缩完成    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 继续对话    │
└─────────────┘
```

### 4.3 技能匹配流程

```
┌─────────────────────────────────────────────────────────────────┐
│                       技能匹配流程                              │
└─────────────────────────────────────────────────────────────────┘

[用户输入]
      │
      ▼
┌─────────────┐
│ 获取技能    │ ← 从 SkillRegistry 获取所有技能
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 计算匹配度  │ ← LLM 或规则匹配
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 排序技能    │ ← 按匹配度排序
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 返回最佳    │ ← 返回匹配度最高的技能
└─────────────┘
```

---

## 五、状态机设计

### 5.1 ReAct 循环状态机

```
┌─────────────────────────────────────────────────────────────────┐
│                   ReAct Loop State Machine                      │
└─────────────────────────────────────────────────────────────────┘

                    ┌──────────────────────────────────┐
                    │                                  │
                    ▼                                  │
              ┌─────────┐                              │
         ────►│ RUNNING │◄──────                       │
              └────┬────┘                              │
                   │                                   │
       ┌──────────┼──────────┐                       │
       │          │          │                         │
  pause()  complete()   abort()                       │
       │          │          │                         │
       ▼          ▼          ▼                         │
  ┌─────────┐ ┌─────────┐ ┌─────────┐               │
  │ PAUSED  │ │COMPLETED│ │ ABORTED │               │
  └────┬────┘ └─────────┘ └─────────┘               │
       │                                              │
 resume()│                                           │
       │                                              │
       ▼                                              │
  ┌─────────┐                                        │
  │RUNNING  │──────────────────────────────────────┘
  └─────────┘         start()
```

**状态定义**:
| 状态 | 说明 | 可转换状态 |
|------|------|-----------|
| `RUNNING` | 执行中 | `PAUSED` (pause), `COMPLETED` (complete), `ABORTED` (abort) |
| `PAUSED` | 已暂停 | `RUNNING` (resume) |
| `COMPLETED` | 已完成 | - |
| `ABORTED` | 已中止 | - |

### 5.2 工具执行状态机

```
┌─────────────────────────────────────────────────────────────────┐
│                    Tool Execution State Machine                 │
└─────────────────────────────────────────────────────────────────┘

              ┌──────────────────────────────────┐
              │                                  │
              ▼                                  │
        ┌───────────┐                         │
   ────►│  PENDING  │◄──────                      │
        └──────┬─────┘                         │
               │                                │
         execute()│                              │
               │                                │
               ▼                                │
        ┌───────────┐                         │
        │ EXECUTING │──── success ────► SUCCESS│
        └──────┬─────┘                         │
               │                                │
        ┌──────┴──────┐                        │
        │             │                        │
   error│       timeout│                        │
        │             │                        │
        ▼             ▼                        │
  ┌───────────┐ ┌───────────┐                   │
  │  ERROR    │ │ TIMEOUT   │───────────────────┘
  └───────────┘ └───────────┘
```

### 5.3 技能生命周期状态机

```
┌─────────────────────────────────────────────────────────────────┐
│                 Skill Lifecycle State Machine                   │
└─────────────────────────────────────────────────────────────────┘

              ┌──────────────────────────────────┐
              │                                  │
              ▼                                  │
        ┌─────────┐                             │
   ────►│  idle   │                             │
        └───┬─────┘                             │
            │                                    │
       register()│                               │
            │                                    │
            ▼                                    │
        ┌─────────┐                             │
        │ active  │──── usage ────► stale      │
        └───┬─────┘                             │
            │                                    │
     ┌─────┴─────┐                              │
     │           │                              │
activate() archive()                              │
     │           │                              │
     ▼           ▼                              │
┌─────────┐ ┌─────────┐                         │
│ active  │ │archived │                         │
└─────────┘ └─────────┘
```

---

## 六、模块详细设计

### 6.1 Agent 核心逻辑

```python
# agent/agent.py
class Agent:
    """Agent 核心类"""
    
    async def chat(
        self,
        user_input: str,
        conversation_history: Optional[List[Dict]] = None,
        use_react: Optional[bool] = None
    ) -> AgentResponse:
        """
        处理用户输入（主要接口）
        
        自动判断使用哪种模式：
        - 复杂任务 → ReAct 模式
        - 简单任务 → 直接模式
        """
        # 1. 模式判断
        if use_react is None:
            use_react = await self._should_use_react(user_input, conversation_history)
        
        # 2. 执行对应模式
        if use_react:
            return await self._chat_react(user_input, conversation_history)
        return await self._chat_simple(user_input, conversation_history)
    
    async def _should_use_react(self, user_input: str, history: List[Dict]) -> bool:
        """
        判断是否使用 ReAct 模式
        
        使用 LLM 判断任务复杂度：
        - 多步骤规划
        - 需要多个工具
        - 复杂推理
        """
        # 构建判断 prompt
        prompt = f"""Task: {user_input}
        
判断是否需要 ReAct 模式（多步骤、多工具调用）。
回答 JSON: {{"use_react": true/false}}
"""
        # 调用 LLM 判断
        response = await self.llm_provider.generate(prompt)
        result = json.loads(response.content)
        return result.get("use_react", False)
```

### 6.2 ReActLoop 核心逻辑

```python
# agent/react/loop.py
class ReActLoop:
    """ReAct 循环引擎"""
    
    async def run(self, context: ReActContext) -> Dict[str, Any]:
        """运行 ReAct 循环"""
        self._state = LoopState.RUNNING
        
        while self._state == LoopState.RUNNING:
            context.increment_iteration()
            
            # 检查最大迭代次数
            if context.remaining_iterations <= 0:
                break
            
            try:
                # 执行步骤
                step_result = await self._execute_step(context)
                self._steps.append(step_result)
                
                # 检查是否完成
                if step_result.action in ("direct_response", "ask_clarification"):
                    self._state = LoopState.COMPLETED
                    
            except Exception as e:
                self.logger.error(f"步骤执行错误: {e}")
                self._state = LoopState.ABORTED
                break
        
        return self._build_result(context)
    
    async def _execute_step(self, context: ReActContext) -> StepResult:
        """执行单个步骤"""
        # 1. LLM 决策
        decision = await self._llm_decide(context)
        
        if decision.action == "use_tool":
            # 2. Rail 前置拦截
            rail_result = await self._trigger_before_tool(
                decision.tool_name,
                decision.parameters
            )
            
            if rail_result and not rail_result.allowed:
                return StepResult(
                    step=context.current_iteration,
                    action="blocked",
                    tool_name=decision.tool_name,
                    is_blocked=True,
                    block_reason=rail_result.error
                )
            
            # 3. 执行工具
            result = await self._execute_tool(
                decision.tool_name,
                decision.parameters,
                context
            )
            
            # 4. Rail 后置处理
            await self._trigger_after_tool(
                decision.tool_name,
                decision.parameters,
                result
            )
            
            return StepResult(
                step=context.current_iteration,
                action="tool_call",
                tool_name=decision.tool_name,
                result=result,
                is_error=self._is_error_result(result)
            )
        
        else:
            return StepResult(
                step=context.current_iteration,
                action=decision.action,
                result=decision.content or "\n".join(decision.questions)
            )
```

### 6.3 ToolRegistry 核心逻辑

```python
# tools/registry.py
class ToolRegistry:
    """工具注册表"""
    
    def register(
        self,
        name: str,
        toolset: str,
        schema: Dict[str, Any],
        handler: Callable,
        check_fn: Optional[Callable] = None,
        **kwargs
    ) -> None:
        """注册一个工具"""
        entry = ToolEntry(
            name=name,
            toolset=toolset,
            schema=schema,
            handler=handler,
            check_fn=check_fn,
            **kwargs
        )
        
        with self._lock:
            self._tools[name] = entry
            if toolset not in self._toolsets:
                self._toolsets[toolset] = set()
            self._toolsets[toolset].add(name)
    
    def get_definitions(
        self,
        toolsets: Optional[List[str]] = None,
        include_unavailable: bool = False,
    ) -> List[Dict[str, Any]]:
        """获取工具定义列表（用于 LLM）"""
        tools = self._tools.values()
        
        if toolsets:
            tool_names = set()
            for ts in toolsets:
                tool_names.update(self._toolsets.get(ts, set()))
            tools = [t for t in tools if t.name in tool_names]
        
        if not include_unavailable:
            tools = [t for t in tools if t.is_available()]
        
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.get_schema().get("parameters", {})
                },
                "metadata": {
                    "toolset": tool.toolset,
                    "emoji": tool.emoji
                }
            }
            for tool in tools
        ]
```

---

## 附录

### A. 类图图例

| 符号 | 说明 |
|------|------|
| `─►` | 依赖关系 (uses) |
| `──►` | 关联关系 (has) |
| `◄──` | 反向关联 |
| `─●` | 聚合关系 |
| `─▼` | 实现关系 |
| `─▲` | 泛化关系 |

### B. 变更日志

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0.0 | 2026-06-09 | 初始版本 |

---

**版权声明**: 本文档采用 MIT 许可证开源。

**最后更新**: 2026-06-09