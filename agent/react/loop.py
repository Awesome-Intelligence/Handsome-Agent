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
        max_iterations: int = 20
    ):
        self.llm = llm_provider
        self.session_id = session_id
        self.rails = rails or []
        self.max_iterations = max_iterations
        
        self.logger = get_task_logger("ReActLoop")
        self._state = LoopState.RUNNING
        self._steps: List[StepResult] = []
    
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
        self.logger.info(f"[/✅Task] ReAct 循环开始: {context.task_description[:50]}...")
        
        self._state = LoopState.RUNNING
        self._steps.clear()
        
        while self._state == LoopState.RUNNING:
            context.increment_iteration()
            
            if context.remaining_iterations <= 0:
                self.logger.warning(f"[/✅Task] 达到最大迭代次数 {self.max_iterations}")
                break
            
            self.logger.debug(
                f"[/✅Task] 迭代 {context.current_iteration}/{self.max_iterations}"
            )
            
            try:
                step_result = await self._execute_step(context)
                self._steps.append(step_result)
                
                if step_result.action in ("direct_response", "ask_clarification"):
                    self._state = LoopState.COMPLETED
                    self.logger.info(
                        f"[/✅Task] 循环完成，迭代次数: {context.current_iteration}"
                    )
                    
            except Exception as e:
                self.logger.error(f"[/✅Task] 步骤执行错误: {e}")
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
                    f"[/✅Task] Rail 阻止工具调用: {decision.tool_name}"
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
    
    async def _llm_decide(self, context: "ReActContext") -> Decision:
        """LLM 决策下一步"""
        
        tools_schema = json.dumps(context.get_tools_schema(), ensure_ascii=False, indent=2)
        todo_guide = self._get_todo_guide()
        recent_history = context.get_recent_messages(4)
        
        history_str = "\n".join(
            f"- {m['role']}: {m['content']}"
            for m in recent_history
        ) if recent_history else "(无历史记录)"
        
        prompt = f"""你是一个任务执行助手。当前任务是：{context.task_description}

对话历史：
{history_str}

可用工具：
{tools_schema}

{todo_guide}

请根据当前任务和对话历史，决定下一步行动：

规则：
- 如果任务复杂（3+ 步骤），使用 todo_* 工具管理任务
- 如果需要多个操作，按顺序逐个完成
- 如果遇到问题，先尝试解决，解决不了再询问用户
- 完成任务后给出简洁的总结

返回 JSON 格式：
{{
    "action": "use_tool" 或 "direct_response" 或 "ask_clarification",
    "tool_name": "工具名" (仅当 action 为 use_tool 时),
    "parameters": {{}} (仅当 action 为 use_tool 时),
    "reasoning": "决策理由",
    "content": "直接回答的内容" (仅当 action 为 direct_response 时),
    "questions": ["问题1", "问题2"] (仅当 action 为 ask_clarification 时)
}}

Respond with ONLY the JSON object, no other text."""

        try:
            response = await self.llm.generate(prompt)
            response = response.strip()
            
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
                response = response.strip()
            
            result = json.loads(response)
            
            return Decision(
                action=result.get("action", "direct_response"),
                tool_name=result.get("tool_name"),
                parameters=result.get("parameters", {}),
                reasoning=result.get("reasoning", ""),
                content=result.get("content"),
                questions=result.get("questions", [])
            )
            
        except Exception as e:
            self.logger.error(f"[/✅Task] LLM 决策失败: {e}")
            return Decision(
                action="direct_response",
                content=f"处理出错: {str(e)}"
            )
    
    def _get_todo_guide(self) -> str:
        """获取 Todo 工具使用指南"""
        return """
任务管理工具（当任务复杂时使用）：
- todo_create: 创建任务列表，开始复杂任务时使用
- todo_add: 添加新任务到列表
- todo_complete: 标记任务完成
- todo_list: 查看当前任务列表
- todo_cancel: 取消任务

示例场景：
- 用户说"帮我做一个博客系统" → 使用 todo_create 创建任务列表
- 用户说"再添加一个用户管理功能" → 使用 todo_add
- 完成一个步骤后 → 使用 todo_complete
- 想查看进度 → 使用 todo_list
"""
    
    async def _execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        context: "ReActContext"
    ) -> Any:
        """执行工具"""
        self.logger.info(f"[/✅Task] 执行工具: {tool_name}")
        
        handler = context.tool_handlers.get(tool_name)
        if not handler:
            return {"error": f"Tool '{tool_name}' not found"}
        
        try:
            result = handler(parameters)
            
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except:
                    result = {"result": result}
            
            return result
            
        except Exception as e:
            self.logger.error(f"[/✅Task] 工具执行错误: {e}")
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
                    self.logger.error(f"[/✅Task] Rail before_tool_call 错误: {e}")
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
                    self.logger.error(f"[/✅Task] Rail after_tool_call 错误: {e}")
    
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
        self.logger.info("[/✅Task] 循环已暂停")
    
    def resume(self) -> None:
        """恢复循环"""
        if self._state == LoopState.PAUSED:
            self._state = LoopState.RUNNING
            self.logger.info("[/✅Task] 循环已恢复")
    
    def abort(self) -> None:
        """中止循环"""
        self._state = LoopState.ABORTED
        self.logger.warning("[/✅Task] 循环已中止")


__all__ = ["ReActLoop", "LoopState", "StepResult", "Decision"]