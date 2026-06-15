# 🧠 Decision - ✅ Task - ReAct 循环引擎

"""
ReActLoop - LLM 驱动的 ReAct 循环执行引擎

注意：ReAct 不是子层，是执行模式。Rail 不是子层，是拦截器。

ReAct = Reasoning + Acting

核心流程：
1. LLM 决策下一步（选择工具，直接回答、询问澄清）
2. 可选的 Rails 前置拦截
3. 执行工具或生成响应
4. 可选的 Rails 后置处理
5. 检查状态，决定是否继续循环

子层标识：✅ Task
主层：🧠 Decision
"""

import json
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from agent.rails import Rail, RailResult

from common.logging_manager import get_task_logger
from agent.error import classify_tool_error, ToolExecutionError


class LoopState(Enum):
    """循环状态"""
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABORTED = "aborted"


@dataclass
class StepResult:
    """步骤执行结果"""
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
    """LLM 决策结果"""
    action: str
    tool_name: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""
    content: Optional[str] = None
    questions: List[str] = field(default_factory=list)


class ReActInterruptedError(Exception):
    """用户请求中断异常"""
    pass


class ReActLoop:
    """
    ReAct 循环引擎
    
    使用示例：
    ```python
    loop = ReActLoop(
        llm_provider=llm,
        session_id="session_123",
        rails=[TaskEventRail("session_123")]
    )
    
    context = ReActContext(
        task_description="帮我做一个博客系统",
        tools=tools_schema,
        tool_handlers=tool_handlers
    )
    
    result = await loop.run(context)
    ```
    """
    
    def __init__(
        self,
        llm_provider,
        session_id: str,
        rails: Optional[List["Rail"]] = None,
        max_iterations: int = 20,
        tools: Optional[Dict[str, Any]] = None,
        stream_emitter=None
    ):
        self.llm = llm_provider
        self.session_id = session_id
        self.rails = rails or []
        self.max_iterations = max_iterations
        self.tools = tools or {}
        self._stream_emitter = stream_emitter

        self.logger = get_task_logger("ReActLoop", sublayer="task")
        self._state = LoopState.RUNNING
        self._steps: List[StepResult] = []

        # 初始化统一的 ContextBuilder（复用上下文拼装逻辑）
        from agent.context import ContextBuilder
        self._context_builder = ContextBuilder(tools=self.tools)
    
    def set_stream_emitter(self, emitter):
        """设置流式发射器"""
        self._stream_emitter = emitter
    
    def _emit_tool_start(self, tool_name: str, parameters: Dict[str, Any]):
        """发射工具开始事件"""
        if self._stream_emitter:
            self._stream_emitter.emit_tool_start(tool_name, parameters)
    
    def _emit_tool_end(self, tool_name: str, result: Any):
        """发射工具结束事件"""
        if self._stream_emitter:
            # 格式化结果
            if isinstance(result, dict):
                tool_output = result
            elif isinstance(result, str):
                try:
                    import json
                    tool_output = json.loads(result)
                except:
                    tool_output = {"result": result}
            else:
                tool_output = {"result": str(result)}
            self._stream_emitter.emit_tool_end(tool_name, tool_output)
    
    @property
    def state(self) -> LoopState:
        """当前状态"""
        return self._state
    
    @property
    def steps(self) -> List[StepResult]:
        """执行步骤记录"""
        return self._steps
    
    async def run(self, context: "ReActContext") -> Dict[str, Any]:
        """
        运行 ReAct 循环
        
        Args:
            context: 执行上下文
            
        Returns:
            执行结果字典
        """
        self.logger.debug(f"ReAct 循环开始: {context.task_description[:50]}...")
        
        self._state = LoopState.RUNNING
        self._steps.clear()
        
        while self._state == LoopState.RUNNING:
            # 检查中断请求
            if self._check_interrupt():
                self._state = LoopState.ABORTED
                self._steps.append(StepResult(
                    step=context.current_iteration,
                    action="interrupted",
                    result={"message": "用户请求中断"}
                ))
                break
            
            context.increment_iteration()
            
            if context.remaining_iterations <= 0:
                self.logger.warning(f"达到最大迭代次数 {self.max_iterations}")
                break
            
            self.logger.debug(
                f"迭代 {context.current_iteration}/{self.max_iterations}"
            )
            
            try:
                step_result = await self._execute_step(context)
                self._steps.append(step_result)
                
                # 输出子任务进度
                self._log_progress(context, step_result)
                
                # 检查中断请求（步骤执行后）
                if self._check_interrupt():
                    self._state = LoopState.ABORTED
                    self._steps.append(StepResult(
                        step=context.current_iteration,
                        action="interrupted",
                        result={"message": "用户请求中断"}
                    ))
                    break
                
                if step_result.action in ("direct_response", "ask_clarification"):
                    self._state = LoopState.COMPLETED
                    self.logger.info(
                        f"循环完成，迭代次数: {context.current_iteration}"
                    )
                    
            except Exception as e:
                self.logger.error(f"步骤执行错误: {e}")
                self._steps.append(StepResult(
                    step=context.current_iteration,
                    action="error",
                    result={"error": str(e)},
                    is_error=True
                ))
                self._state = LoopState.ABORTED
                break
        
        return self._build_result(context)
    
    def _log_progress(self, context: "ReActContext", step_result: StepResult):
        """输出子任务执行进度"""
        subtasks = context.get('subtasks', [])
        if not subtasks:
            return
        
        # 计算已完成的工具调用数量（作为子任务完成的近似）
        completed = len([tc for tc in context.tool_calls if tc.tool_name not in ('think', 'reasoning')])
        total = len(subtasks)
        current_tool = step_result.tool_name if step_result.tool_name else "思考中..."
        
        # 输出进度
        self.logger.info(f"进度 {completed}/{total} | 🔄 {current_tool}")
        
        # 如果有自定义数据中的当前任务描述，使用它
        current_task_desc = context.get('current_task', '')
        if current_task_desc:
            self.logger.info(f"       🔄 {current_task_desc}")
    
    def _check_interrupt(self) -> bool:
        """检查是否有中断请求
        
        Returns:
            True if interrupted, False otherwise
        """
        # 如果有 stream_emitter，检查它的中断状态
        if self._stream_emitter and hasattr(self._stream_emitter, '_interrupt_requested'):
            if self._stream_emitter._interrupt_requested:
                self.logger.warning("检测到中断请求")
                return True
        return False
    
    async def _execute_step(self, context: "ReActContext") -> StepResult:
        """执行单个步骤"""
        
        decision = await self._llm_decide(context)
        
        if decision.action == "use_tool":
            rail_result = await self._trigger_before_tool(
                decision.tool_name,
                decision.parameters
            )
            
            if rail_result and not rail_result.allowed:
                self.logger.warning(
                    f"Rail 阻止工具调用: {decision.tool_name}"
                )
                return StepResult(
                    step=context.current_iteration,
                    action="blocked",
                    tool_name=decision.tool_name,
                    parameters=decision.parameters,
                    result=rail_result.error or "Blocked by Rail",
                    reasoning=decision.reasoning,
                    is_blocked=True,
                    block_reason=rail_result.error
                )
            
            result = await self._execute_tool(
                decision.tool_name,
                decision.parameters,
                context
            )
            
            await self._trigger_after_tool(
                decision.tool_name,
                decision.parameters,
                result
            )
            
            is_error = self._is_error_result(result)
            
            # 添加工具调用记录到上下文（同时添加到消息列表）
            tool_call_id = context.add_tool_call(
                decision.tool_name,
                decision.parameters,
                result,
                is_error
            )
            
            # 添加工具结果消息（tool 角色）
            context.add_tool_result(
                tool_call_id,
                decision.tool_name,
                result
            )
            
            return StepResult(
                step=context.current_iteration,
                action="tool_call",
                tool_name=decision.tool_name,
                parameters=decision.parameters,
                result=result,
                reasoning=decision.reasoning,
                is_error=is_error
            )
        
        else:
            content = decision.content or "\n".join(decision.questions)
            return StepResult(
                step=context.current_iteration,
                action=decision.action,
                result=content,
                reasoning=decision.reasoning
            )

    def _try_complete_json(self, content: str) -> Optional[dict]:
        """尝试补全不完整的 JSON"""
        import re

        # 移除代码块标记
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*', '', content)

        # 移除思维链标签
        content = re.sub(r'<think>.*?`]\s*', '', content, flags=re.DOTALL)
        content = re.sub(r'<think>.*?\n\s*', '', content, flags=re.DOTALL)

        # 尝试找到 JSON 起始位置
        json_start = content.find('{')
        if json_start == -1:
            return None

        # 找到最后一个可能的 JSON 结束位置
        # 我们需要找到 content 中所有 { 和 } 的匹配
        brace_count = 0
        json_end = -1
        in_string = False
        escape_next = False

        for i in range(json_start, len(content)):
            char = content[i]

            if escape_next:
                escape_next = False
                continue

            if char == '\\':
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if in_string:
                continue

            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    json_end = i + 1
                    break

        if json_end == -1:
            return None

        # 提取 JSON 并尝试解析
        potential_json = content[json_start:json_end]
        try:
            return json.loads(potential_json)
        except json.JSONDecodeError:
            return None

    async def _llm_decide(self, context: "ReActContext") -> Decision:
        """LLM 决策下一步 - Hermes 风格"""

        try:
            # 构建 tools 参数（用于 function calling）
            tools = []
            for tool_name, tool in self.tools.items():
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "description": getattr(tool, 'description', f'Tool: {tool_name}'),
                        "parameters": getattr(tool, 'parameters', {"type": "object", "properties": {}})
                    }
                })

            # 构建消息历史（使用标准消息列表格式）
            # 消息格式：
            # - system: {"role": "system", "content": "..."}
            # - user: {"role": "user", "content": "..."}
            # - assistant: {"role": "assistant", "content": "...", "tool_calls": [...]}
            # - tool: {"role": "tool", "tool_call_id": "...", "content": "..."}
            messages = context.to_messages_dict() or []
            self.logger.debug(f"Message history: {len(messages)} messages")

            # 使用 ContextBuilder 构建完整的消息列表（包含系统消息、用户任务、对话历史等）
            messages = self._context_builder.build_messages(
                conversation_history=messages,
                include_tools=True,
                user_message=context.task_description,
                model=None
            ) or []
            self.logger.debug(f"Context built: {len(messages)} messages")

            # 添加用户任务消息（追加到消息列表末尾）
            messages.append({
                "role": "user",
                "content": f"Current Task: {context.task_description}\n\nPlease decide the next action."
            })
            self.logger.debug(f"Final messages: {len(messages)} messages")

            response = await self.llm.generate(
                prompt="",  # 使用 messages 参数，prompt 设为空
                messages=messages,
                tools=tools if tools else None
            )
            raw_content = response.content if hasattr(response, 'content') else None
            content = raw_content if raw_content is not None else str(response)
            self.logger.debug(f"LLM response content type: {type(content)}, value: {repr(content)[:100]}")

            # 截断显示：头部30字符 + 中间省略 + 尾部30字符
            if content and len(content) > 90:
                truncated = f"{content[:30]}...{content[-30:]}"
            else:
                truncated = content
            
            # 检查是否有有效的 function_call
            function_call = getattr(response, 'function_call', None)

            if function_call:
                # MiniMax 的 function_call 结构: {'function': {'name': '...', 'arguments': '...'}}
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

                # Hermes 风格：完全信任 LLM 的决策
                # 如果 LLM 说要调用工具，就调用，让 LLM 自己判断是否重复
                return Decision(
                    action="use_tool",
                    tool_name=tool_name,
                    parameters=arguments or {},
                    reasoning=f"Called function: {tool_name}"
                )

            # 如果没有 function_call，检查 content 是否表示任务完成
            if content.strip():
                # 移除思维链标签
                cleaned = content.strip()
                if cleaned.startswith("<think>"):
                    end_idx = cleaned.find("]")
                    if end_idx > 0:
                        cleaned = cleaned[end_idx+1:].strip()

                # 如果有实质内容，认为任务完成
                if len(cleaned) > 0 and "error" not in cleaned.lower():
                    return Decision(
                        action="direct_response",
                        content=cleaned
                    )

            return Decision(
                action="direct_response",
                content="处理出错: LLM 响应无法解析"
            )
        except Exception as e:
            import traceback
            self.logger.error(f"LLM 决策失败: {e}\n{traceback.format_exc()}")
            return Decision(
                action="direct_response",
                content=f"处理出错: {str(e)}"
            )

    async def _execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        context: "ReActContext"
    ) -> Any:
        """执行工具"""
        self.logger.info(f"执行工具: {tool_name}")
        
        # 发射工具开始事件
        self._emit_tool_start(tool_name, parameters)
        
        handler = context.tool_handlers.get(tool_name)
        if not handler:
            result = {"error": f"Tool '{tool_name}' not found"}
            self._emit_tool_end(tool_name, result)
            return result
        
        try:
            import inspect
            result = handler(parameters)
            
            if inspect.iscoroutine(result):
                result = await result
            
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except:
                    result = {"result": result}
            
            # 发射工具结束事件
            self._emit_tool_end(tool_name, result)
            
            return result
            
        except Exception as e:
            # 使用错误分类器进行结构化错误处理
            error_info = classify_tool_error(e)
            self.logger.error(
                f"工具执行错误 - tool={tool_name} type={error_info['error_type']} "
                f"retryable={error_info['retryable']} msg={str(e)[:200]}"
            )
            result = {
                "success": False,
                "error": str(e),
                "error_type": error_info["error_type"],
                "retryable": error_info["retryable"],
            }
            self._emit_tool_end(tool_name, result)
            return result
    
    async def _trigger_before_tool(
        self,
        tool_name: str,
        args: Dict[str, Any]
    ) -> Optional["RailResult"]:
        """触发 before_tool_call Rails"""
        for rail in self.rails:
            if hasattr(rail, "before_tool_call"):
                try:
                    result = await rail.before_tool_call(tool_name, args)
                    if result and hasattr(result, "allowed") and not result.allowed:
                        return result
                except Exception as e:
                    self.logger.error(f"Rail before_tool_call 错误: {e}")
        return None
    
    async def _trigger_after_tool(
        self,
        tool_name: str,
        args: Dict[str, Any],
        result: Any
    ) -> None:
        """触发 after_tool_call Rails"""
        for rail in self.rails:
            if hasattr(rail, "after_tool_call"):
                try:
                    await rail.after_tool_call(tool_name, args, result)
                except Exception as e:
                    self.logger.error(f"Rail after_tool_call 错误: {e}")
    
    def _is_error_result(self, result: Any) -> bool:
        """判断结果是否为错误"""
        if isinstance(result, dict):
            if not result.get("success", True):
                return True
            if result.get("error"):
                return True
        return False
    
    def _build_result(self, context: "ReActContext") -> Dict[str, Any]:
        """构建最终结果"""
        final_step = self._steps[-1] if self._steps else None
        
        return {
            "success": self._state == LoopState.COMPLETED,
            "state": self._state.value,
            "iterations": context.current_iteration,
            "steps": [
                {
                    "step": s.step,
                    "action": s.action,
                    "tool_name": s.tool_name,
                    "is_error": s.is_error,
                    "is_blocked": s.is_blocked
                }
                for s in self._steps
            ],
            "final_result": final_step.result if final_step else None,
            "final_action": final_step.action if final_step else None,
            "tool_call_count": len(context.tool_calls)
        }
    
    def pause(self) -> None:
        """暂停循环"""
        self._state = LoopState.PAUSED
        self.logger.info("循环已暂停")
    
    def resume(self) -> None:
        """恢复循环"""
        if self._state == LoopState.PAUSED:
            self._state = LoopState.RUNNING
            self.logger.info("循环已恢复")
    
    def abort(self) -> None:
        """中止循环"""
        self._state = LoopState.ABORTED
        self.logger.warning("循环已中止")


__all__ = ["ReActLoop", "LoopState", "StepResult", "Decision"]
