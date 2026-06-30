# -*- coding: utf-8 -*-
"""
AgentLoop - LLM 驱动的统一循环执行引擎

核心设计：
1. 纯执行器：只负责执行单步操作，不控制循环退出
2. 循环控制在 agent.py 的 _run_loop() 中统一管理
3. 支持通过 on_after_step 回调扩展功能（如 Judge 判断）

核心流程：
1. step() - 执行单步：LLM 决策 → Rails 拦截 → 执行工具/生成响应
2. 循环控制由外部（_run_loop）负责

设计原则：
- 意图理解使用 LLM 动态判断，禁止硬编码关键词
- 任务完成由 LLM 自主判断何时结束
- 无显式的 Goal 模式，简化处理流程
- 状态管理统一使用 agent.state.AgentState

子层标识：✅ Task
主层：🧠 Decision
"""

import json
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Awaitable, TYPE_CHECKING

if TYPE_CHECKING:
    from agent.rails import Rail, RailResult
    from agent.state import AgentState
    from agent.state.enums import ExitReason

from agent.state import ExitReason

# 回调返回类型：None=继续，False=停止，其他字符串=继续并追加消息
AfterStepCallback = Callable[["LoopStepResult", Any], Awaitable[Optional[str]]]

from common.logging_manager import get_task_logger


class LoopState(Enum):
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABORTED = "aborted"


@dataclass
class LoopStepResult:
    step: int
    action: str
    tool_name: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: Any = None
    reasoning: str = ""
    is_error: bool = False
    is_blocked: bool = False
    block_reason: Optional[str] = None


@dataclass
class Decision:
    action: str
    tool_name: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""
    content: Optional[str] = None
    questions: List[str] = field(default_factory=list)


class AgentLoop:
    """
    Agent 循环引擎（纯执行器）

    职责：
    - 执行单步操作（LLM 决策 + 工具执行）
    - 维护执行步骤记录
    - 触发回调钩子
    - 循环控制（预算检查、中断处理、退出判断）

    不负责：
    - 状态持久化
    - Rail 注册（由 agent.py 统一管理）

    使用示例：
    ```python
    # agent.py 中的用法
    from agent.state import AgentState

    state = AgentState(max_iterations=20)
    loop = AgentLoop(
        llm_provider=llm,
        session_id="session_123",
        tools=tools_dict,
        agent_state=state,  # 使用统一状态管理器
    )

    context = ExecutionContext(...)
    result = await loop.run(context)
    ```
    """

    def __init__(
        self,
        llm_provider,
        session_id: str,
        tools: Optional[Dict[str, Any]] = None,
        stream_emitter=None,
        context_manager=None,
        tool_executor=None,
        todo_store=None,
        on_after_step: Optional[AfterStepCallback] = None,
        agent_state: Optional["AgentState"] = None,
        agent: Optional[Any] = None,  # 父 Agent 实例，用于工具上下文
    ):
        """
        初始化 AgentLoop

        Args:
            llm_provider: LLM 提供者
            session_id: 会话 ID
            tools: 工具字典
            stream_emitter: 流式输出发射器
            context_manager: 上下文管理器
            tool_executor: 工具执行器（可选，默认自动创建）
            todo_store: Todo 存储
            on_after_step: 每步执行后的回调
            agent_state: 统一状态管理器（必填）
            agent: 父 Agent 实例（可选，用于传递 parent_agent 给工具）

        注意：
            Rails 始终从 RailRegistry 获取，不接受外部传入。
            如需注册 Rails，请在 agent.py 中调用 registry.register()。
        """
        if agent_state is None:
            raise ValueError("agent_state is required. Use agent.state.AgentState.")

        self.llm = llm_provider
        self.session_id = session_id
        self.tools = tools or {}
        self._stream_emitter = stream_emitter
        self._context_manager = context_manager
        self._todo_store = todo_store
        self._on_after_step = on_after_step
        self._agent_state = agent_state
        self._agent = agent  # 保存父 Agent 引用

        self.logger = get_task_logger("AgentLoop", sublayer="task")
        self._state = LoopState.RUNNING
        self._steps: List[LoopStepResult] = []

        self._tool_executor = tool_executor

        # 始终从 Registry 获取 Rails（统一入口，v2.0.0）
        from agent.rails.registry import get_rail_registry
        self._rail_registry = get_rail_registry()

        # 最后一次响应（用于 Judge 评估）
        self._last_response = ""

    def set_stream_emitter(self, emitter):
        self._stream_emitter = emitter

    def _ensure_tool_executor(self, context) -> Any:
        if self._tool_executor is None:
            from common.tool_executor import ToolExecutor

            self._tool_executor = ToolExecutor(
                tool_registry=context.tool_handlers,
                rails=self.rails,
                stream_emitter=self._stream_emitter,
                session_id=self.session_id,
            )
        return self._tool_executor

    @property
    def state(self) -> LoopState:
        return self._state

    @property
    def rails(self) -> List["Rail"]:
        """从 Registry 获取当前 session 的 Rails 列表

        注意：
        - Rails 拦截统一通过 AgentLoop._trigger_before_tool/_trigger_after_tool 调用
        - ToolExecutor 不直接持有 Rails（避免双重拦截）
        """
        return self._rail_registry.get_rails(self.session_id)

    @property
    def steps(self) -> List[LoopStepResult]:
        return self._steps

    def reset(self):
        """重置状态，准备新一轮执行"""
        self._state = LoopState.RUNNING
        self._steps.clear()

    def pause(self) -> None:
        self._state = LoopState.PAUSED
        self.logger.info("循环已暂停")

    def resume(self) -> None:
        if self._state == LoopState.PAUSED:
            self._state = LoopState.RUNNING
            self.logger.info("循环已恢复")

    def abort(self) -> None:
        self._state = LoopState.ABORTED
        self.logger.warning("循环已中止")

    async def step(self, context, step_num: int) -> LoopStepResult:
        """
        执行单步操作（纯执行器核心方法）

        执行流程：
        1. LLM 决策下一步
        2. Rails 前置拦截检查
        3. 执行工具或生成响应
        4. Rails 后置处理
        5. 调用 on_after_step 回调
        6. 记录步骤结果

        注意：
        - 中断检查统一由外部（_run_loop）负责，此方法不再检查
        - 循环退出条件由外部控制，此方法不控制循环退出

        Args:
            context: 执行上下文
            step_num: 当前步骤编号

        Returns:
            LoopStepResult: 步骤执行结果
        """
        try:
            step_result = await self._execute_step(context, step_num)
            self._steps.append(step_result)

            self._log_progress(context, step_result)

            # 调用 after_step 回调（用于 Judge 等扩展逻辑）
            if self._on_after_step is not None:
                callback_result = await self._on_after_step(step_result, context)
                if callback_result is False:
                    # 回调返回 False，停止循环
                    self._state = LoopState.COMPLETED
                elif callback_result:
                    # 回调返回字符串，追加为用户消息
                    context.add_message("user", callback_result)

            return step_result

        except Exception as e:
            self.logger.error(f"步骤执行错误: {e}")
            result = LoopStepResult(
                step=step_num,
                action="error",
                result={"error": str(e)},
                is_error=True,
            )
            self._steps.append(result)
            self._state = LoopState.ABORTED
            return result

    def _log_progress(self, context, step_result: LoopStepResult):
        if self._todo_store:
            todos = self._todo_store.read()
        else:
            todos = context.get("subtasks", [])

        if not todos:
            return

        completed = sum(1 for t in todos if t.get("status") == "completed")
        total = len(todos)
        current_tool = step_result.tool_name if step_result.tool_name else "思考中..."

        current_task_desc = ""
        for todo in todos:
            if todo.get("status") == "in_progress":
                current_task_desc = todo.get("content", "")
                break
        if not current_task_desc:
            for todo in todos:
                if todo.get("status") == "pending":
                    current_task_desc = todo.get("content", "")
                    break

        self.logger.info(f"进度 {completed}/{total} | {current_tool}")

        if current_task_desc:
            self.logger.info(f"       {current_task_desc}")

    def _emit_plan_progress(self, context, todos: List[Dict[str, Any]] = None) -> None:
        if self._stream_emitter is None:
            return

        if todos is None:
            if self._todo_store is None:
                return
            todos = self._todo_store.read()

        if not todos:
            return

        total = len(todos)
        completed = sum(1 for t in todos if t.get("status") == "completed")
        current_task = ""

        for todo in todos:
            if todo.get("status") == "in_progress":
                current_task = todo.get("content", "")
                break

        if not current_task:
            for todo in todos:
                if todo.get("status") == "pending":
                    current_task = todo.get("content", "")
                    break

        progress_percent = int((completed / total) * 100) if total > 0 else 0

        try:
            self._stream_emitter.emit_plan_progress(
                subtasks=todos,
                completed=completed,
                total=total,
                current_task=current_task,
                progress_percent=progress_percent,
            )
        except Exception as e:
            self.logger.debug(f"发送进度事件失败: {e}")

    async def _execute_step(self, context, step_num: int) -> LoopStepResult:
        decision = await self._llm_decide(context)

        # 参考 Hermes：判断是否只有 execute_code（纯计算轮次不消耗预算）
        is_execute_code_only = (
            decision.action == "use_tool"
            and decision.tool_name == "execute_code"
            # 注意：这里只检查单个工具，如果是多工具调用会在下面处理
        )

        if decision.action == "use_tool":
            rail_result = await self._trigger_before_tool(
                decision.tool_name, decision.parameters
            )

            if rail_result and not rail_result.allowed:
                self.logger.warning(f"Rail 阻止工具调用: {decision.tool_name}")
                return LoopStepResult(
                    step=step_num,
                    action="blocked",
                    tool_name=decision.tool_name,
                    parameters=decision.parameters,
                    result=rail_result.error or "Blocked by Rail",
                    reasoning=decision.reasoning,
                    is_blocked=True,
                    block_reason=rail_result.error,
                )

            # Tool Loop Guardrail 前置检查（允许执行，但记录警告）
            tool_loop_decision = self._agent_state._ensure_tool_loop_controller().before_call(
                decision.tool_name, decision.parameters
            )
            if tool_loop_decision.should_halt:
                self.logger.warning(f"Tool Loop 检测到循环: {tool_loop_decision.message}")

            result = await self._execute_tool(
                decision.tool_name, decision.parameters, context
            )

            await self._trigger_after_tool(
                decision.tool_name, decision.parameters, result
            )

            # 参考 Hermes：execute_code 成功执行后，如果本轮只有它，则退还预算
            is_error = self._is_error_result(result)
            if not is_error and is_execute_code_only:
                self._agent_state.refund()
                self.logger.debug(f"Tool execute_code refunded budget (only tool in this turn)")

            tool_call_id = context.add_tool_call(
                decision.tool_name, decision.parameters, result, is_error
            )

            context.add_tool_result(tool_call_id, decision.tool_name, result)

            return LoopStepResult(
                step=step_num,
                action="tool_call",
                tool_name=decision.tool_name,
                parameters=decision.parameters,
                result=result,
                reasoning=decision.reasoning,
                is_error=is_error,
            )

        else:
            content = decision.content or "\n".join(decision.questions)
            return LoopStepResult(
                step=step_num,
                action=decision.action,
                result=content,
                reasoning=decision.reasoning,
            )

    def _try_complete_json(self, content: str) -> Optional[dict]:
        import re

        content = re.sub(r"```json\s*", "", content)
        content = re.sub(r"```\s*", "", content)

        content = re.sub(r"<think>.*?`]\s*", "", content, flags=re.DOTALL)
        content = re.sub(r"<think>.*?\n\s*", "", content, flags=re.DOTALL)

        json_start = content.find("{")
        if json_start == -1:
            return None

        brace_count = 0
        json_end = -1
        in_string = False
        escape_next = False

        for i in range(json_start, len(content)):
            char = content[i]

            if escape_next:
                escape_next = False
                continue

            if char == "\\":
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if in_string:
                continue

            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0:
                    json_end = i + 1
                    break

        if json_end == -1:
            return None

        potential_json = content[json_start:json_end]
        try:
            return json.loads(potential_json)
        except json.JSONDecodeError:
            return None

    async def _llm_decide(self, context) -> Decision:
        try:
            from tools.schema_registry import generate_openai_tools_schema

            tools = generate_openai_tools_schema(self.tools)

            messages = context.to_messages_dict() or []
            self.logger.debug(f"Message history: {len(messages)} messages")

            # 使用 ContextManager 构建上下文（统一入口）
            if self._context_manager:
                from agent.context import ContextPurpose

                messages_result = await self._context_manager.build_messages(
                    user_message=context.task_description,
                    conversation_history=messages,
                    purpose=ContextPurpose.AGENT_LOOP,
                    tools=self.tools,
                    include_tools=True,
                )
                messages = messages_result.messages
                self.logger.debug(
                    f"Context built via ContextManager: {len(messages)} messages, "
                    f"compressed={messages_result.compressed}"
                )
            else:
                self.logger.warning(
                    "ContextManager not available, using raw messages"
                )

            todo_context = ""
            if self._todo_store:
                todo_context = self._todo_store.format_for_llm_context()

            user_content = f"Current Task: {context.task_description}\n\n"
            if todo_context:
                user_content += f"Task Progress:\n{todo_context}\n\n"
            user_content += (
                "You can use tools or provide a direct response. "
                "For complex tasks, consider using the `todo` tool to plan first. "
                "Always update the task list to reflect your progress."
            )

            if messages and messages[-1].get("role") == "user":
                messages[-1]["content"] = user_content
            else:
                messages.append(
                    {
                        "role": "user",
                        "content": user_content,
                    }
                )
            self.logger.debug(f"Final messages: {len(messages)} messages")

            response = await self.llm.generate(
                prompt="", messages=messages, tools=tools if tools else None
            )
            raw_content = response.content if hasattr(response, "content") else None
            content = raw_content if raw_content is not None else str(response)
            self.logger.debug(
                f"LLM response content type: {type(content)}, value: {repr(content)[:100]}"
            )

            if content and len(content) > 90:
                truncated = f"{content[:30]}...{content[-30:]}"
            else:
                truncated = content

            function_call = getattr(response, "function_call", None)

            if function_call:
                func_data = function_call.get("function", function_call)
                tool_name = func_data.get("name")
                arguments = func_data.get("arguments")
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except:
                        arguments = {"input": arguments}

                args_str = str(arguments)
                if len(args_str) > 90:
                    args_truncated = f"{args_str[:30]}...{args_str[-30:]}"
                else:
                    args_truncated = args_str
                self.logger.info(f"Function call: {tool_name}({args_truncated})")

                return Decision(
                    action="use_tool",
                    tool_name=tool_name,
                    parameters=arguments or {},
                    reasoning=f"Called function: {tool_name}",
                )

            if content.strip():
                cleaned = content.strip()
                if cleaned.startswith("<think>"):
                    end_idx = cleaned.find("]")
                    if end_idx > 0:
                        cleaned = cleaned[end_idx + 1 :].strip()

                if len(cleaned) > 0 and "error" not in cleaned.lower():
                    return Decision(action="direct_response", content=cleaned)

            return Decision(
                action="direct_response", content="处理出错: LLM 响应无法解析"
            )
        except Exception as e:
            import traceback

            self.logger.error(f"LLM 决策失败: {e}\n{traceback.format_exc()}")
            return Decision(action="direct_response", content=f"处理出错: {str(e)}")

    async def _execute_tool(
        self, tool_name: str, parameters: Dict[str, Any], context
    ) -> Any:
        """执行工具

        Rail 拦截由 AgentLoop._execute_step() 统一处理，
        此方法只负责工具执行逻辑。
        """
        self.logger.info(f"执行工具: {tool_name}")

        executor = self._ensure_tool_executor(context)

        # 构建 extra_context，传递父 Agent 实例给需要 parent_agent 的工具
        extra_context = {}
        if self._agent is not None:
            extra_context["parent_agent"] = self._agent

        # ToolExecutor 只负责执行，Rails 拦截已在 _execute_step 中处理
        result = await executor.execute(tool_name, parameters, extra_context=extra_context)

        return result.get_output()

    async def _trigger_before_tool(
        self, tool_name: str, args: Dict[str, Any]
    ) -> Optional["RailResult"]:
        """触发 before_tool_call 拦截（使用 Registry 统一入口）"""
        return await self._rail_registry.trigger_before_tool_call(
            self.session_id, tool_name, args
        )

    async def _trigger_after_tool(
        self, tool_name: str, args: Dict[str, Any], result: Any
    ) -> None:
        """触发 after_tool_call 拦截（使用 Registry 统一入口）"""
        await self._rail_registry.trigger_after_tool_call(
            self.session_id, tool_name, args, result
        )

    def _is_error_result(self, result: Any) -> bool:
        if isinstance(result, dict):
            if not result.get("success", True):
                return True
            if result.get("error"):
                return True
        return False

    def build_result(self, context, iterations: int = 0) -> Dict[str, Any]:
        """构建执行结果

        Args:
            context: 执行上下文
            iterations: 已使用的迭代次数（由外部传入）
        """
        final_step = self._steps[-1] if self._steps else None

        return {
            "success": self._state == LoopState.COMPLETED,
            "state": self._state.value,
            "iterations": iterations,
            "steps": [
                {
                    "step": s.step,
                    "action": s.action,
                    "tool_name": s.tool_name,
                    "is_error": s.is_error,
                    "is_blocked": s.is_blocked,
                }
                for s in self._steps
            ],
            "final_result": final_step.result if final_step else None,
            "final_action": final_step.action if final_step else None,
            "tool_call_count": len(context.tool_calls),
        }

    async def run(
        self,
        context,
    ) -> Dict[str, Any]:
        """
        单一循环执行（核心方法）

        流程：
        1. 预算检查（首次）
        2. 循环迭代：
           a. 中断检查
           b. 预算耗尽检查（先检查再消耗，确保能执行完整的 max_turns 轮）
           c. 消耗预算
           d. 执行单步 (step)
           e. 记录响应
           f. 退出判断（使用 AgentState）
           g. 处理继续/终止

        Args:
            context: 执行上下文

        Returns:
            执行结果字典
        """
        step_num = 0

        # ── 1. 预算检查（首次） ──
        if not self._agent_state.can_iterate():
            self.logger.warning(f"预算耗尽，循环结束: {self._agent_state.get_budget_status()}")
            return self.build_result(context, iterations=0)

        # ── 2. 主循环 ──
        while True:
            # ── a. 重置 ToolLoopController（每个 turn 开始时） ──
            self._agent_state.reset_tool_loop_controller()

            # ── b. 中断检查 ──
            if self._agent_state.is_interrupt_requested:
                self._agent_state.abort("loop_interrupt")
                self._state = LoopState.ABORTED
                self.logger.info("收到中断请求，循环终止")
                break

            # ── c. 预算耗尽检查（先检查再消耗，确保能执行完整的 max_turns 轮） ──
            if not self._agent_state.can_iterate():
                self.logger.info(f"预算耗尽，循环结束")
                break

            # ── d. 消耗预算 ──
            consumed = self._agent_state.consume()
            remaining = self._agent_state.budget_remaining
            self.logger.debug(f"{self._agent_state.get_budget_status()} (剩余 {remaining})")

            # ── e. 执行单步 ──
            step_num += 1
            step_result = await self.step(context, step_num)
            self.logger.debug(f"步骤 {step_num} 完成: {step_result.action}")

            # 中断响应（防御性检查）
            if step_result.action == "interrupted":
                self.logger.info("收到中断响应，循环终止")
                self._state = LoopState.ABORTED
                self._agent_state.abort("step_interrupted")
                break

            # ── f. 记录响应 ──
            if step_result.result is not None:
                self._last_response = str(step_result.result)

            # ── g. 退出判断 ──
            if self._agent_state.is_goal_mode:
                # Goal 模式：使用 Judge 评估
                exit_decision = await self._agent_state.should_exit_with_judge(step_result)
            else:
                # 非 Goal 模式：简单退出判断
                exit_decision = self._agent_state.should_exit(step_result)

            if exit_decision.should_exit:
                # 根据退出原因设置状态
                if exit_decision.reason == ExitReason.GOAL_COMPLETED:
                    self._agent_state.complete("goal_completed")
                    self._state = LoopState.COMPLETED
                elif exit_decision.reason == ExitReason.BUDGET_EXHAUSTED:
                    # 预算耗尽不是正常完成，保持 RUNNING 状态
                    self._state = LoopState.RUNNING
                else:
                    # 其他正常退出原因（如直接响应、错误等）
                    self._state = LoopState.COMPLETED
                self.logger.info(
                    f"退出原因: {exit_decision.reason.value} - {exit_decision.message}"
                )
                break

            # 处理继续执行（Goal模式）
            if exit_decision.continuation_prompt:
                self.logger.debug(f"继续执行: {exit_decision.continuation_prompt[:50]}...")
                context.add_message("user", exit_decision.continuation_prompt)

        # ── 3. 构建结果 ──
        return self.build_result(context, iterations=step_num)

    def get_last_response(self) -> str:
        """获取最后一次响应"""
        return self._last_response


__all__ = ["AgentLoop", "LoopState", "LoopStepResult", "Decision"]