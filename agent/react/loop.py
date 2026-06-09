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
        tools: Optional[Dict[str, Any]] = None
    ):
        self.llm = llm_provider
        self.session_id = session_id
        self.rails = rails or []
        self.max_iterations = max_iterations
        self.tools = tools or {}

        self.logger = get_task_logger("ReActLoop", sublayer="task")
        self._state = LoopState.RUNNING
        self._steps: List[StepResult] = []

        # 初始化统一的 ContextBuilder（复用上下文拼装逻辑）
        from agent.context import ContextBuilder
        self._context_builder = ContextBuilder(tools=self.tools)
    
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
        self.logger.info(f"ReAct 循环开始: {context.task_description[:50]}...")
        
        self._state = LoopState.RUNNING
        self._steps.clear()
        
        while self._state == LoopState.RUNNING:
            context.increment_iteration()
            
            if context.remaining_iterations <= 0:
                self.logger.warning(f"达到最大迭代次数 {self.max_iterations}")
                break
            
            self.logger.info(
                f"迭代 {context.current_iteration}/{self.max_iterations}"
            )
            
            try:
                step_result = await self._execute_step(context)
                self._steps.append(step_result)
                
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
            
            context.add_tool_call(
                decision.tool_name,
                decision.parameters,
                result,
                is_error
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

        # 构建用户消息 - Hermes 风格
        # 注意：任务描述、历史等已由 ContextBuilder 处理
        # user_message 只包含之前的工具调用结果（ContextBuilder 没有的额外信息）
        user_message = ""

        # 添加之前的工具调用结果
        if context.tool_calls:
            user_message += "## Previous Tool Results\n"
            for tc in context.tool_calls:
                user_message += f"- {tc.tool_name}: {tc.result}\n"
            user_message += "\n**IMPORTANT**: If the above results show the task is COMPLETED, respond with direct_response ONLY. Do NOT call tools again!\n"

        # 构建对话历史
        conversation_history = []
        for msg in context.messages:
            conversation_history.append({
                'role': msg.role,
                'content': msg.content
            })

        # 使用 ContextBuilder 构建完整的系统提示词（包含身份、能力、历史、记忆等）
        system_prompt = self._context_builder.build_react_decision_prompt(
            task_description=context.task_description,
            conversation_history=conversation_history
        )

        try:
            response = await self.llm.generate(user_message, system_prompt=system_prompt, tools=tools if tools else None)
            content = response.content if hasattr(response, 'content') else str(response)

            self.logger.debug(f"LLM response content (first 500): {repr(content[:500])}")

            # 检查是否有有效的 function_call
            function_call = getattr(response, 'function_call', None)
            self.logger.debug(f"LLM function_call: {function_call}")

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

                self.logger.info(f"Function call: {tool_name}({arguments})")

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

            # 处理思维链标签（如果 JSON 在思维链之后）
            processed_content = content
            if content.startswith("<think>"):
                # 尝试找到思维链结束后的内容
                think_end = content.rfind("`]")
                think_end_cn = content.rfind("")
                if think_end_cn > think_end:
                    think_end = think_end_cn
                if think_end != -1:
                    end_tag_len = 6 if think_end_cn > content.rfind("`]") else 2
                    processed_content = content[think_end + end_tag_len:].strip()

            if processed_content.startswith("```"):
                parts = processed_content.split("```")
                # 取第一个 ``` 之后的内容
                processed_content = parts[1] if len(parts) > 1 else parts[0]
                if processed_content.startswith("json"):
                    processed_content = processed_content[4:]
                processed_content = processed_content.strip()

            # 尝试提取 JSON
            result = None

            # 方法1：直接解析处理后的内容
            try:
                result = json.loads(processed_content)
            except json.JSONDecodeError:
                # 可能是截断的 JSON，尝试补全并解析
                result = self._try_complete_json(processed_content)

            # 方法2：从处理后的内容中提取 JSON（支持多种字段名）
            if result is None:
                import re
                # 尝试找到任何包含常见字段的 JSON
                for field in ['"action"', '"tool"', '"tool_name"', '"command"', '"toolName"']:
                    action_pos = processed_content.find(field)
                    if action_pos != -1:
                        # 从 action_pos 往前找 {
                        brace_start = processed_content.rfind('{', 0, action_pos)
                        if brace_start != -1:
                            # 使用括号匹配找到完整的 JSON
                            brace_count = 0
                            brace_end = len(processed_content)
                            for i in range(brace_start, len(processed_content)):
                                if processed_content[i] == '{':
                                    brace_count += 1
                                elif processed_content[i] == '}':
                                    brace_count -= 1
                                    if brace_count == 0:
                                        brace_end = i + 1
                                        break
                            try:
                                potential_json = processed_content[brace_start:brace_end]
                                result = json.loads(potential_json)
                                # 标准化字段名
                                if "tool" in result and "tool_name" not in result:
                                    result["tool_name"] = result.pop("tool")
                                if "toolName" in result and "tool_name" not in result:
                                    result["tool_name"] = result.pop("toolName")
                                break
                            except:
                                pass
                    if result:
                        break

            # 方法3：从原始内容中提取 JSON
            if result is None:
                for field in ['"action"', '"tool"', '"tool_name"', '"command"', '"toolName"']:
                    action_pos = content.find(field)
                    if action_pos != -1:
                        brace_start = content.rfind('{', 0, action_pos)
                        if brace_start != -1:
                            brace_count = 0
                            brace_end = len(content)
                            for i in range(brace_start, len(content)):
                                if content[i] == '{':
                                    brace_count += 1
                                elif content[i] == '}':
                                    brace_count -= 1
                                    if brace_count == 0:
                                        brace_end = i + 1
                                        break
                            try:
                                potential_json = content[brace_start:brace_end]
                                result = json.loads(potential_json)
                                if "tool" in result and "tool_name" not in result:
                                    result["tool_name"] = result.pop("tool")
                                if "toolName" in result and "tool_name" not in result:
                                    result["tool_name"] = result.pop("toolName")
                                break
                            except:
                                pass
                    if result:
                        break

            if result is None:
                self.logger.warning("无法解析 LLM 响应为 JSON")
                return Decision(
                    action="direct_response",
                    content="处理出错: LLM 响应无法解析为 JSON"
                )

            # 标准化 action 字段 - 基于工具字段的存在来判断
            # 首先检查是否有任何工具字段
            has_tool_fields = any([
                result.get("tool_name"),
                result.get("tool"),
                result.get("command"),
                result.get("name"),
                result.get("tool_calls"),
                result.get("args"),
                result.get("parameters"),
                result.get("tool_input"),
                result.get("params")
            ])

            if has_tool_fields:
                action = "use_tool"
            else:
                action = result.get("action", "direct_response")
                # 如果 action 不是明确的工具相关动作，保持 direct_response
                if action in ("respond", "response", "reply", "finish", "end", "stop", "done", "allow", "none"):
                    action = "direct_response"

            # 标准化 tool_name 字段
            tool_name = result.get("tool_name") or result.get("tool") or result.get("name")

            # 处理 parameters
            parameters = result.get("parameters", {}) or {}

            # 处理 tool_calls 格式
            if result.get("tool_calls"):
                tool_calls = result.get("tool_calls")
                if isinstance(tool_calls, list) and len(tool_calls) > 0:
                    first_call = tool_calls[0]
                    if isinstance(first_call, dict):
                        tool_name = tool_name or first_call.get("tool") or first_call.get("name")
                        args = first_call.get("args", {})
                        if args:
                            parameters.update(args)

            # 处理 tool_input 格式 (MiniMax 常用格式)
            if result.get("tool_input"):
                tool_input = result.get("tool_input")
                if isinstance(tool_input, dict):
                    parameters.update(tool_input)
                elif isinstance(tool_input, str):
                    parameters["input"] = tool_input

            # 处理 tool 和 params 格式
            if result.get("tool") and not tool_name:
                tool_name = result.get("tool")
            if result.get("params"):
                params = result.get("params")
                if isinstance(params, dict):
                    parameters.update(params)
                elif isinstance(params, str):
                    parameters["param"] = params

            # 处理 action_input 格式
            if result.get("action_input"):
                action_input = result.get("action_input")
                if isinstance(action_input, dict):
                    parameters.update(action_input)
                elif isinstance(action_input, str):
                    parameters["input"] = action_input

            # 如果 parameters 仍然为空，从其他字段提取
            if not parameters:
                for field in ["command", "args", "app", "result", "file", "query"]:
                    if field in result:
                        parameters[field] = result[field]

            return Decision(
                action=action,
                tool_name=tool_name,
                parameters=parameters,
                reasoning=result.get("reasoning", ""),
                content=result.get("content"),
                questions=result.get("questions", [])
            )

        except Exception as e:
            self.logger.error(f"LLM 决策失败: {e}")
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
        
        handler = context.tool_handlers.get(tool_name)
        if not handler:
            return {"error": f"Tool '{tool_name}' not found"}
        
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
            
            return result
            
        except Exception as e:
            self.logger.error(f"工具执行错误: {e}")
            return {"success": False, "error": str(e)}
    
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
