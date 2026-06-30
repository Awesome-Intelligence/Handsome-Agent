#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AgentState - 统一状态管理器

核心设计：
1. 聚合所有子状态（GoalState, BudgetController, LoopState, InterruptController）
2. 提供单一状态查询接口
3. 原子性状态转换
4. 状态变更事件通知

使用示例：
```python
state = AgentState()

# 启动
state.start(goal_text="完成某个任务")

# 检查状态
if state.is_running:
    if not state.should_exit(step_result).should_exit:
        # 继续执行
        pass

# 状态转换
state.pause("用户暂停")
state.resume()
state.complete("任务完成")
```

状态转换图：
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                         ┌─────────┐                                         │
│                         │  IDLE   │                                         │
│                         └────┬────┘                                         │
│                              │ start()                                       │
│                              ▼                                              │
│    ┌──────────────────────────────────────────────────────────────┐          │
│    │                     RUNNING 状态                              │          │
│    │  循环中...                                              │          │
│    │  检查点：should_exit() → COMPLETED                        │          │
│    │  pause()      → PAUSED                                    │          │
│    │  abort()      → ABORTED                                   │          │
│    └──────────────────────────────────────────────────────────────┘          │
│                              │                           │                   │
│           ┌──────────────────┘                           │                   │
│           ▼                                              ▼                   │
│    ┌────────────┐                                  ┌────────────┐           │
│    │  PAUSED    │                                  │ COMPLETED  │           │
│    └─────┬──────┘                                  └────────────┘           │
│          │ resume()                                                         │
│          ▼                                                                  │
│    ┌────────────┐                                                           │
│    │  RUNNING   │                                                           │
│    └────────────┘                                                           │
│                                                                             │
│    ┌────────────┐                                                           │
│    │  ABORTED   │  (任何状态可转换)                                         │
│    └────────────┘                                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
"""

import time
import threading
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable, TYPE_CHECKING

# 统一状态枚举 - 从 enums 导入
from agent.state.enums import AgentStatus, BudgetMode, ExitReason, ExitDecision

if TYPE_CHECKING:
    from agent.execution.loop import LoopStepResult

logger = logging.getLogger(__name__)


# 状态监听器类型
StateListener = Callable[[AgentStatus, AgentStatus, str], None]


@dataclass
class StateTransition:
    """状态转换记录"""
    from_status: AgentStatus
    to_status: AgentStatus
    reason: str
    timestamp: float = field(default_factory=time.time)


class AgentState:
    """
    统一状态管理器（参考 Hermes 设计）

    核心职责：
    1. 基础循环状态管理（RUNNING/PAUSED/COMPLETED/IDLE/ABORTED）
    2. 预算控制（迭代次数/轮次限制）
    3. 中断请求处理
    4. 状态变更事件通知
    5. 退出决策（配合 GoalManager 实现 Judge 评估）

    重要设计（参考 Hermes）：
    - Goal 相关功能完全委托给 GoalManager
    - AgentState 只负责状态查询代理，不持有 GoalState
    - 预算消耗由 AgentState 统一管理
    - GoalManager.evaluate() 只负责 Judge 评估，不处理轮次逻辑

    Attributes:
        status: 当前 Agent 状态
        goal: Goal 状态（代理到 GoalManager，只读）
        budget: 预算控制器
        interrupt_reason: 中断原因（如果有）
    """

    # 非Goal模式下立即结束的 action 类型
    TERMINAL_ACTIONS = {"direct_response", "ask_clarification", "error"}

    # 工具调用总数上限（放宽到 20，原 5）
    _MAX_TOOL_CALLS_TOTAL = 20

    def __init__(
        self,
        max_iterations: int = 90,  # 参考 Hermes：父代理默认 90 次
        max_turns: int = 90,
        tool_loop_config: Optional["ToolLoopConfig"] = None,
    ):
        # ── 核心状态 ──
        self._status: AgentStatus = AgentStatus.IDLE
        self._status_history: List[StateTransition] = []

        # ── Goal 相关（代理到 GoalManager）──
        self._goal_manager = None

        # ── 预算相关 ──
        self._mode: BudgetMode = BudgetMode.ITERATION
        self._max_iterations: int = max_iterations
        self._max_turns: int = max_turns
        self._current: int = 0
        self._lock: threading.Lock = threading.Lock()

        # ── 中断相关 ──
        self._interrupt_requested: bool = False
        self._interrupt_reason: Optional[str] = None

        # ── 事件监听器 ──
        self._listeners: List[StateListener] = []

        # ── 最后一步结果 ──
        self._last_step_result: Optional["LoopStepResult"] = None
        self._last_response: str = ""

        # ── Tool Loop Guardrail 相关 ──
        self._tool_loop_config = tool_loop_config
        self._tool_loop_controller: Optional["ToolLoopController"] = None
        self._tool_loop_warning: Optional[str] = None

        # ── Todo Store 引用（用于检查 todo 完成度）──
        self._todo_store = None

        # 日志器（统一使用）
        self.logger = logger

    # ── 状态属性 ──
    @property
    def status(self) -> AgentStatus:
        """当前状态"""
        return self._status

    @property
    def status_history(self) -> List[StateTransition]:
        """状态转换历史"""
        return self._status_history.copy()

    @property
    def is_idle(self) -> bool:
        """是否为空闲状态"""
        return self._status == AgentStatus.IDLE

    @property
    def is_running(self) -> bool:
        """是否在运行"""
        return self._status == AgentStatus.RUNNING

    @property
    def is_paused(self) -> bool:
        """是否暂停"""
        return self._status == AgentStatus.PAUSED

    @property
    def is_completed(self) -> bool:
        """是否完成"""
        return self._status == AgentStatus.COMPLETED

    @property
    def is_aborted(self) -> bool:
        """是否中止"""
        return self._status == AgentStatus.ABORTED

    @property
    def is_active(self) -> bool:
        """是否为活跃状态"""
        return self._status.is_active()

    @property
    def is_terminal(self) -> bool:
        """是否为终止状态"""
        return self._status.is_terminal()

    # ── Goal 相关（代理到 GoalManager，参考 Hermes）──
    @property
    def goal(self) -> Optional["GoalState"]:
        """获取 Goal 状态（代理到 GoalManager）"""
        if self._goal_manager:
            return self._goal_manager.state
        return None

    @property
    def is_goal_mode(self) -> bool:
        """是否为 Goal 模式（代理到 GoalManager）"""
        if self._goal_manager:
            return self._goal_manager.is_active()
        return False

    def set_goal_manager(self, goal_manager) -> None:
        """设置 Goal 管理器"""
        self._goal_manager = goal_manager

    # 注意：set_goal/clear_goal/pause_goal/resume_goal 已移除
    # 这些功能由 GoalManager 统一管理，AgentState 只负责代理查询

    # ── 预算相关 ──
    @property
    def budget_mode(self) -> BudgetMode:
        """当前预算模式"""
        return self._mode

    @property
    def budget_used(self) -> int:
        """已使用预算"""
        return self._current

    @property
    def budget_max(self) -> int:
        """最大预算"""
        if self._mode == BudgetMode.TURN:
            return self._max_turns
        return self._max_iterations

    @property
    def budget_remaining(self) -> int:
        """剩余预算"""
        return max(0, self.budget_max - self._current)

    def can_iterate(self) -> bool:
        """是否可以继续迭代"""
        return self._current < self.budget_max

    def consume(self) -> int:
        """消耗预算"""
        with self._lock:
            self._current += 1
            return self._current

    def refund(self) -> None:
        """
        退还预算（例如用于 execute_code 回合）

        参考 Hermes 设计：纯计算操作不消耗预算
        """
        with self._lock:
            if self._current > 0:
                self._current -= 1

    def get_budget_status(self) -> str:
        """获取预算状态描述"""
        mode_name = "轮次" if self._mode == BudgetMode.TURN else "迭代"
        return f"{mode_name}: {self._current}/{self.budget_max}"

    def _enable_goal_mode(self, max_turns: Optional[int] = None) -> None:
        """启用 Goal 模式"""
        with self._lock:
            self._mode = BudgetMode.TURN
            if max_turns is not None:
                self._max_turns = max_turns
            self._current = 0

    def _enable_iteration_mode(self, max_iterations: Optional[int] = None) -> None:
        """启用迭代模式"""
        with self._lock:
            self._mode = BudgetMode.ITERATION
            if max_iterations is not None:
                self._max_iterations = max_iterations
            self._current = 0

    def sync_from_goal_state(self, goal_state) -> None:
        """从 GoalState 同步预算状态（参考 Hermes）

        注意：此方法只同步预算相关的状态（模式、最大轮次、当前轮次）
        不再同步 GoalState 本身，因为 GoalState 由 GoalManager 统一管理
        """
        if goal_state is None:
            self._enable_iteration_mode()
            return
        self._enable_goal_mode(goal_state.max_turns)
        with self._lock:
            self._current = goal_state.current_turn

    # ── 中断相关 ──
    @property
    def is_interrupt_requested(self) -> bool:
        """是否请求中断"""
        return self._interrupt_requested

    @property
    def interrupt_reason(self) -> Optional[str]:
        """中断原因"""
        return self._interrupt_reason

    def request_interrupt(self, reason: str = "user_requested") -> None:
        """请求中断"""
        self._interrupt_reason = reason
        self._interrupt_requested = True

    def clear_interrupt(self) -> None:
        """清除中断请求"""
        self._interrupt_requested = False
        self._interrupt_reason = None

    # ── 状态转换 ──
    def start(self) -> None:
        """
        启动 Agent（参考 Hermes 设计）

        注意：Goal 相关操作由 GoalManager 统一管理
        如果需要设置 Goal，应先通过 GoalManager.set() 设置，
        然后在外部调用 sync_from_goal_state() 同步预算信息
        """
        if self._status == AgentStatus.IDLE:
            self._transition_to(AgentStatus.RUNNING, "Agent started")
        elif self._status == AgentStatus.PAUSED:
            self._transition_to(AgentStatus.RUNNING, "Agent resumed")
        else:
            # 重置并启动
            self.reset()
            self._transition_to(AgentStatus.RUNNING, "Agent started")
        
        self._current = 0
        self._interrupt_requested = False

    def pause(self, reason: str = "user_paused") -> None:
        """暂停 Agent（参考 Hermes 设计）

        注意：Goal 暂停由 GoalManager.pause() 统一管理
        此方法只负责 Agent 级别的状态转换
        """
        if self._status == AgentStatus.RUNNING:
            self._transition_to(AgentStatus.PAUSED, reason)

    def resume(self) -> None:
        """恢复 Agent（参考 Hermes 设计）

        注意：Goal 恢复由 GoalManager.resume() 统一管理
        此方法只负责 Agent 级别的状态转换
        """
        if self._status == AgentStatus.PAUSED:
            self._transition_to(AgentStatus.RUNNING, "Agent resumed")

    def complete(self, reason: str = "completed") -> None:
        """完成 Agent"""
        self._transition_to(AgentStatus.COMPLETED, reason)

    def abort(self, reason: str = "aborted") -> None:
        """中止 Agent"""
        self._interrupt_reason = reason
        self._interrupt_requested = True
        self._transition_to(AgentStatus.ABORTED, reason)

    def reset(self) -> None:
        """重置状态（参考 Hermes 设计）

        注意：Goal 清除由 GoalManager.clear() 统一管理
        此方法只负责重置 Agent 级别的状态
        """
        old_status = self._status
        self._status = AgentStatus.IDLE
        self._status_history.append(StateTransition(
            from_status=old_status,
            to_status=AgentStatus.IDLE,
            reason="reset",
        ))
        # 预算重置
        self._current = 0
        self._mode = BudgetMode.ITERATION  # 重置为迭代模式
        self._interrupt_requested = False
        self._interrupt_reason = None
        self._last_step_result = None
        self._last_response = ""
        self._tool_call_history = []  # 重置工具调用历史
        # 重置 ToolLoopController
        if self._tool_loop_controller:
            self._tool_loop_controller.reset()
        self._tool_loop_warning = None
        self._notify_listeners(old_status, AgentStatus.IDLE, "reset")

    def _transition_to(self, new_status: AgentStatus, reason: str) -> None:
        """状态转换（内部方法）"""
        if self._status == new_status:
            return
        
        old_status = self._status
        self._status = new_status
        
        # 记录历史
        self._status_history.append(StateTransition(
            from_status=old_status,
            to_status=new_status,
            reason=reason,
        ))
        
        # 通知监听器
        self._notify_listeners(old_status, new_status, reason)

    def _notify_listeners(self, old_status: AgentStatus, new_status: AgentStatus, reason: str) -> None:
        """通知状态变更"""
        for listener in self._listeners:
            try:
                listener(old_status, new_status, reason)
            except Exception:
                pass

    def add_listener(self, listener: StateListener) -> None:
        """添加状态监听器"""
        self._listeners.append(listener)

    def remove_listener(self, listener: StateListener) -> None:
        """移除状态监听器"""
        if listener in self._listeners:
            self._listeners.remove(listener)

    def set_todo_store(self, todo_store) -> None:
        """设置 Todo Store 引用（用于检查 todo 完成度）"""
        self._todo_store = todo_store

    def _ensure_tool_loop_controller(self) -> "ToolLoopController":
        """懒加载 ToolLoopController"""
        if self._tool_loop_controller is None:
            from agent.rails.tool_loop import ToolLoopController, ToolLoopConfig

            if self._tool_loop_config is None:
                self._tool_loop_config = ToolLoopConfig()
            self._tool_loop_controller = ToolLoopController(self._tool_loop_config)
        return self._tool_loop_controller

    def reset_tool_loop_controller(self) -> None:
        """重置 ToolLoopController（在每个 turn 开始时调用）"""
        controller = self._ensure_tool_loop_controller()
        controller.reset()
        self._tool_loop_warning = None

    def get_tool_loop_warning(self) -> Optional[str]:
        """获取最后一条 Tool Loop 警告"""
        if self._tool_loop_controller:
            return self._tool_loop_controller.last_warning
        return None

    # ── 退出判断 ──
    def should_exit(self, step_result: "LoopStepResult") -> ExitDecision:
        """
        同步退出判断（非 Goal 模式使用）

        职责：
        - 中断检查
        - 预算检查
        - Action 类型判断

        注意：Goal 模式应使用 should_exit_with_judge() 进行异步 Judge 评估

        Args:
            step_result: 当前步骤结果
            
        Returns:
            ExitDecision: 退出决策
        """
        # 记录最后一步结果
        self._last_step_result = step_result
        if step_result and step_result.result is not None:
            self._last_response = str(step_result.result)
        
        # 1. 中断检查
        if self._interrupt_requested:
            return ExitDecision(
                should_exit=True,
                reason=ExitReason.INTERRUPTED,
                message=f"中断请求: {self._interrupt_reason or 'unknown'}",
            )
        
        # 2. 预算耗尽检查
        if not self.can_iterate():
            mode_name = "轮次" if self._mode == BudgetMode.TURN else "迭代"
            return ExitDecision(
                should_exit=True,
                reason=ExitReason.BUDGET_EXHAUSTED,
                message=f"{mode_name}预算耗尽 ({self._current}/{self.budget_max})",
                metadata={
                    "mode": "turn" if self._mode == BudgetMode.TURN else "iteration",
                    "current": self._current,
                    "max": self.budget_max,
                    "remaining": 0,
                },
            )
        
        # 3. Action 类型判断
        return self._check_action_exit(step_result)

    async def should_exit_with_judge(self, step_result: "LoopStepResult") -> ExitDecision:
        """
        带 Judge 评估的异步退出判断（Goal 模式使用）

        职责（单一入口，统一管理）：
        - 中断检查
        - 预算检查
        - 轮次消耗（在此统一处理）
        - Goal Judge 评估（委托给 GoalManager，只负责 Judge 逻辑）
        - Action 类型判断（降级）

        设计原则：
        - 轮次消耗由 AgentState 统一管理，避免 GoalManager 重复消耗
        - GoalManager.evaluate() 只负责 Judge 评估，不处理轮次逻辑

        Args:
            step_result: 当前步骤结果

        Returns:
            ExitDecision: 退出决策
        """
        # 记录最后一步结果
        self._last_step_result = step_result
        if step_result and step_result.result is not None:
            self._last_response = str(step_result.result)

        # 1. 中断检查
        if self._interrupt_requested:
            return ExitDecision(
                should_exit=True,
                reason=ExitReason.INTERRUPTED,
                message=f"中断请求: {self._interrupt_reason or 'unknown'}",
            )

        # 2. 预算耗尽检查
        if not self.can_iterate():
            mode_name = "轮次" if self._mode == BudgetMode.TURN else "迭代"
            return ExitDecision(
                should_exit=True,
                reason=ExitReason.BUDGET_EXHAUSTED,
                message=f"{mode_name}预算耗尽 ({self._current}/{self.budget_max})",
                metadata={
                    "mode": "turn" if self._mode == BudgetMode.TURN else "iteration",
                    "current": self._current,
                    "max": self.budget_max,
                    "remaining": 0,
                },
            )

        # 3. 如果有 GoalManager，委托给 Judge 评估
        #    注意：Judge 评估只负责判断是否完成，不消耗预算
        #    预算消耗已在 AgentLoop.run() 循环开始时统一处理
        if self._goal_manager:
            try:
                # 传入当前已消耗的轮次数量（不重复消耗）
                # 注意：这里的 _current 已经是循环开始时消耗后的值
                return await self._goal_manager.evaluate(
                    last_response=self._last_response,
                    current_turn=self._current,
                    max_turns=self.budget_max,
                )
            except Exception as e:
                self.logger.error(f"GoalManager.evaluate failed: {e}")
                return ExitDecision(
                    should_exit=True,
                    reason=ExitReason.ERROR,
                    message=f"Judge评估失败: {e}",
                )

        # 4. 没有 GoalManager：降级使用 action 类型判断
        return self._check_action_exit(step_result)

    def _check_action_exit(self, step_result: "LoopStepResult") -> ExitDecision:
        """基于 action 类型的退出检查（非 Goal 模式）"""
        if step_result is None:
            return ExitDecision(should_exit=False, reason=ExitReason.UNKNOWN)

        action = step_result.action

        if action in self.TERMINAL_ACTIONS:
            if action == "error":
                return ExitDecision(
                    should_exit=True,
                    reason=ExitReason.ERROR,
                    message=f"执行错误: {step_result.result.get('error', '未知错误') if isinstance(step_result.result, dict) else 'unknown'}",
                    metadata={"action": action},
                )
            elif action == "direct_response":
                return ExitDecision(
                    should_exit=True,
                    reason=ExitReason.DIRECT_RESPONSE,
                    message="LLM直接响应，循环结束",
                    metadata={"action": action},
                )
            else:
                return ExitDecision(
                    should_exit=True,
                    reason=ExitReason.ASK_CLARIFICATION,
                    message="需要澄清，循环结束",
                    metadata={"action": action},
                )

        if action in ("use_tool", "tool_call"):
            return self._check_tool_call_exit(step_result)

        return ExitDecision(
            should_exit=False,
            reason=ExitReason.UNKNOWN,
            message="继续执行",
        )

    def _check_tool_call_exit(self, step_result: "LoopStepResult") -> ExitDecision:
        """
        检查工具调用是否应该退出循环（优化版）

        核心改进：
        1. 使用 ToolLoopController 只追踪失败的工具调用
        2. 成功执行清除失败计数
        3. 检查 Todo 完成度
        4. 放宽总调用次数限制
        """
        tool_name = step_result.tool_name
        parameters = step_result.parameters or {}
        result = step_result.result
        is_error = step_result.is_error

        # 1. 获取 ToolLoopController 并更新状态
        controller = self._ensure_tool_loop_controller()
        decision = controller.after_call(
            tool_name=tool_name,
            args=parameters,
            result=result,
            failed=is_error,
        )

        # 2. 如果需要 halt，退出循环
        if decision.should_halt:
            return ExitDecision(
                should_exit=True,
                reason=ExitReason.TOOL_LOOP_HALT,
                message=f"[Tool Loop] {decision.message}",
                metadata={
                    "action": "halt",
                    "tool_name": tool_name,
                    "code": decision.code,
                    "count": decision.count,
                },
            )

        # 3. 记录警告信息（不退出，让 LLM 看到警告）
        if decision.is_warning:
            self._tool_loop_warning = decision.message

        # 4. 检查 Todo 完成度
        if self._should_continue_for_todos():
            return ExitDecision(
                should_exit=False,
                reason=ExitReason.UNKNOWN,
                message="继续执行: todo 列表还有待完成任务",
            )

        # 5. 检查工具调用总数上限（放宽到 20）
        if not hasattr(self, "_tool_call_history"):
            self._tool_call_history = []
        self._tool_call_history.append(tool_name)
        total_tool_calls = len(self._tool_call_history)

        if total_tool_calls >= self._MAX_TOOL_CALLS_TOTAL:
            return ExitDecision(
                should_exit=True,
                reason=ExitReason.DIRECT_RESPONSE,
                message=f"工具调用总数超过 {self._MAX_TOOL_CALLS_TOTAL} 次，强制总结",
                metadata={"action": "use_tool", "total_count": total_tool_calls},
            )

        return ExitDecision(
            should_exit=False,
            reason=ExitReason.UNKNOWN,
            message="继续执行",
        )

    def _should_continue_for_todos(self) -> bool:
        """
        检查是否应该继续执行（因为 todo 还有任务）

        条件：
        1. 没有 Tool Loop 警告（避免在循环检测触发时继续）
        2. Todo Store 有任务
        3. 有 pending 或 in_progress 状态的任务
        """
        # 有警告时不自动继续（让 LLM 处理警告）
        if self._tool_loop_warning:
            return False

        # 检查 todo 列表
        if self._todo_store and self._todo_store.has_items():
            todos = self._todo_store.read()
            pending_count = sum(
                1
                for t in todos
                if t.get("status") in {"pending", "in_progress"}
            )
            if pending_count > 0:
                return True

        return False

    # ── 调试和序列化 ──
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "status": self._status.value,
            "is_goal_mode": self.is_goal_mode,
            "goal": self.goal.to_json() if self.goal else None,  # 通过 GoalManager 获取
            "budget_mode": self._mode.value,
            "budget_used": self._current,
            "budget_max": self.budget_max,
            "budget_remaining": self.budget_remaining,
            "interrupt_requested": self._interrupt_requested,
            "interrupt_reason": self._interrupt_reason,
            "status_history": [
                {"from": t.from_status.value, "to": t.to_status.value, "reason": t.reason, "timestamp": t.timestamp}
                for t in self._status_history
            ],
        }

    def __repr__(self) -> str:
        return f"AgentState(status={self._status.value}, goal_mode={self.is_goal_mode}, budget={self._current}/{self.budget_max})"


__all__ = [
    "AgentState",
    "AgentStatus",
    "BudgetMode",
    "ExitReason",
    "ExitDecision",
    "StateTransition",
]