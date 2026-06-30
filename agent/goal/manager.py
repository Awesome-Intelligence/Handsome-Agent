#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Goal Manager - 参考 Hermes 的 Ralph loop

工作流程：
1. 用户发起复杂任务 → 创建 Goal
2. Agent 循环每轮执行完成后 → 调用 Judge 判断
3. Judge 认为未完成 → 生成 Continuation Prompt → 继续
4. Judge 认为完成 / 轮次耗尽 → 结束

设计原则：
- Goal 只负责 Judge 机制（单一职责）
- 轮次消耗和预算检查由 AgentState 统一管理
- 任务列表统一由 SessionTodoStore 管理
- Judge 通过读取 Todo 判断目标是否完成
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from typing import Optional, Tuple, List, Dict, Any, TYPE_CHECKING

from .models import GoalState, GoalStatus
from agent.state.enums import ExitDecision, ExitReason
from common.logging_manager import get_decision_logger

# ──────────────────────────────────────────────────────────────────────
# Constants & defaults
# ──────────────────────────────────────────────────────────────────────

# 参考 Hermes 的默认值：父代理 90 次，子代理 50 次
DEFAULT_MAX_TURNS = 90
DEFAULT_JUDGE_TIMEOUT = 30.0
DEFAULT_JUDGE_MAX_TOKENS = 4096
# Cap how much of the last response we send to the judge.
_JUDGE_RESPONSE_SNIPPET_CHARS = 4000
# After this many consecutive judge *parse* failures, the loop auto-pauses.
DEFAULT_MAX_CONSECUTIVE_PARSE_FAILURES = 3

# Judge 系统提示词 - 参考 Hermes 简洁设计
JUDGE_SYSTEM_PROMPT = (
    "You are a strict judge evaluating whether an autonomous agent has "
    "achieved a user's stated goal.\n\n"
    "A goal is DONE only when:\n"
    "- The response explicitly confirms the goal was completed, OR\n"
    "- The response clearly shows the final deliverable was produced, OR\n"
    "- The response explains the goal is unachievable / blocked / needs "
    "user input\n\n"
    "Otherwise the goal is NOT done — CONTINUE.\n\n"
    'Reply ONLY with a single JSON object on one line:\n'
    '{"done": <true|false>, "reason": "<one-sentence rationale>"}'
)

# Judge 用户提示词模板
JUDGE_USER_PROMPT_TEMPLATE = (
    "Goal:\n{goal}\n\n"
    "Agent's most recent response:\n{response}\n\n"
    "Current time: {current_time}\n\n"
    "Is the goal satisfied?"
)

# 带子目标的 Judge 用户提示词模板
JUDGE_USER_PROMPT_WITH_SUBGOALS_TEMPLATE = (
    "Goal:\n{goal}\n\n"
    "Additional criteria the user added mid-loop (all must also be "
    "satisfied for the goal to be DONE):\n{subgoals_block}\n\n"
    "Agent's most recent response:\n{response}\n\n"
    "Current time: {current_time}\n\n"
    "Decision: For each numbered criterion above, find concrete "
    "evidence in the agent's response that the criterion is "
    "satisfied. Do not accept generic phrases like 'all requirements "
    "met' or 'implying it was done' — require specific evidence. If "
    "ANY criterion lacks specific evidence in the response, the goal "
    "is NOT done — return CONTINUE.\n\n"
    "Is the goal AND every additional criterion satisfied?"
)

# Continuation Prompt 模板
CONTINUATION_PROMPT_TEMPLATE = (
    "[Continuing toward your standing goal]\n"
    "Goal: {goal}\n\n"
    "Continue working toward this goal. Take the next concrete step. "
    "If you believe the goal is complete, state so explicitly and stop. "
    "If you are blocked and need input from the user, say so clearly and stop."
)

# 带子目标的 Continuation Prompt 模板
CONTINUATION_PROMPT_WITH_SUBGOALS_TEMPLATE = (
    "[Continuing toward your standing goal]\n"
    "Goal: {goal}\n\n"
    "Additional criteria the user added mid-loop:\n"
    "{subgoals_block}\n\n"
    "Continue working toward the goal AND all additional criteria. Take "
    "the next concrete step. If you believe the goal and every "
    "additional criterion are complete, state so explicitly and stop. "
    "If you are blocked and need input from the user, say so clearly "
    "and stop."
)


class GoalManager:
    """Per-session goal state + continuation decisions.

    工作流程：
    1. 用户发起复杂任务 → 创建 Goal
    2. Agent 循环每轮执行完成后 → 调用 Judge 判断
    3. Judge 认为未完成 → 生成 Continuation Prompt → 继续
    4. Judge 认为完成 / 轮次耗尽 → 结束

    单一职责原则：
    - 轮次消耗和预算检查由 AgentState 统一管理
    - GoalManager 只负责 Judge 评估逻辑

    Methods:
        - ``set(goal)`` — start a new standing goal.
        - ``clear()`` — remove the active goal.
        - ``pause()`` / ``resume()`` — explicit user controls.
        - ``status_line()`` — printable one-liner.
        - ``evaluate(last_response, current_turn, max_turns)`` — **唯一入口**，
          call the judge and return ExitDecision.
        - ``next_continuation_prompt()`` — the canonical user-role message to
          feed back into ``run_conversation``.
    """

    def __init__(
        self,
        session_id: str = None,
        *,
        judge_llm_provider=None,
        default_max_turns: int = DEFAULT_MAX_TURNS,
        judge_timeout: float = DEFAULT_JUDGE_TIMEOUT,
        judge_max_tokens: int = DEFAULT_JUDGE_MAX_TOKENS,
        on_state_change=None,
    ):
        self._session_id = session_id
        self._default_max_turns = int(default_max_turns or DEFAULT_MAX_TURNS)
        self._judge_timeout = float(judge_timeout)
        self._judge_max_tokens = int(judge_max_tokens)
        self._current_goal: Optional[GoalState] = None
        self._memory_store: Dict[str, Any] = {}  # 简单的内存存储后备
        self._judge_llm = judge_llm_provider  # Judge LLM provider
        self._on_state_change = on_state_change

        # 初始化统一日志
        self.logger = get_decision_logger(self.__class__.__name__, sublayer="task")

        # 尝试从 DB 加载已有 goal
        if session_id:
            self._current_goal = self._load_goal_from_db()

    # ──────────────────────────────────────────────────────────────────────
    # Introspection
    # ──────────────────────────────────────────────────────────────────────

    @property
    def state(self) -> Optional[GoalState]:
        """返回当前 GoalState 或 None"""
        return self._current_goal

    def is_active(self) -> bool:
        """检查是否有活跃目标"""
        return self._current_goal is not None and self._current_goal.status == GoalStatus.ACTIVE.value

    def has_goal(self) -> bool:
        """检查是否有活跃或暂停的 Goal"""
        return self._current_goal is not None and self._current_goal.status in {GoalStatus.ACTIVE.value, GoalStatus.PAUSED.value}

    def status_line(self) -> str:
        """返回可打印的状态行"""
        s = self._current_goal
        if s is None or s.status == GoalStatus.CLEARED.value:
            return "No active goal. Set one with /goal <text>."

        turns = f"{s.current_turn}/{s.max_turns} turns"
        sub = f", {len(s.subgoals)} subgoal{'s' if len(s.subgoals) != 1 else ''}" if s.subgoals else ""

        if s.status == GoalStatus.ACTIVE.value:
            return f"⊙ Goal (active, {turns}{sub}): {s.goal}"
        if s.status == GoalStatus.PAUSED.value:
            extra = f" — {s.paused_reason}" if s.paused_reason else ""
            return f"⏸ Goal (paused, {turns}{sub}{extra}): {s.goal}"
        if s.status == GoalStatus.DONE.value:
            return f"✓ Goal done ({turns}{sub}): {s.goal}"
        return f"Goal ({s.status}, {turns}{sub}): {s.goal}"

    # ──────────────────────────────────────────────────────────────────────
    # Mutation
    # ──────────────────────────────────────────────────────────────────────

    def set(self, goal: str, *, max_turns: Optional[int] = None) -> GoalState:
        """创建新目标"""
        goal = (goal or "").strip()
        if not goal:
            raise ValueError("goal text is empty")

        state = GoalState(
            goal=goal,
            max_turns=int(max_turns) if max_turns else self._default_max_turns,
            current_turn=0,
            status=GoalStatus.ACTIVE.value,
        )
        self._current_goal = state
        self._save_goal()
        self.logger.info(f"Goal set: {goal[:50]} (max_turns={state.max_turns})")
        return state

    # 别名：兼容旧代码
    create_goal = set

    def pause(self, reason: Optional[str] = None):
        """暂停目标"""
        if self._current_goal and self._current_goal.status == GoalStatus.ACTIVE.value:
            self._current_goal.set_status(GoalStatus.PAUSED.value, reason or "User paused")
            self._current_goal.paused_reason = reason
            self.logger.info(f"Goal paused: {reason or 'User paused'}")
            self._save_goal()

    def resume(self, *, reset_budget: bool = True):
        """恢复目标"""
        if self._current_goal and self._current_goal.status == GoalStatus.PAUSED.value:
            self._current_goal.set_status(GoalStatus.ACTIVE.value, "User resumed")
            self._current_goal.paused_reason = None
            if reset_budget:
                self._current_goal.current_turn = 0
            self.logger.info(f"Goal resumed (reset_budget={reset_budget})")
            self._save_goal()

    def clear(self):
        """清除目标（用户主动清除，保留审计记录）"""
        if self._current_goal:
            self._current_goal.set_status(GoalStatus.CLEARED.value, "User cleared")
            self.logger.info(f"Goal cleared: {self._current_goal.goal[:50]}...")
            self._save_goal()
        self._current_goal = None
        if self._on_state_change:
            self._on_state_change(None)

    def mark_done(self, reason: str) -> None:
        """标记 Goal 完成"""
        if not self._current_goal:
            return
        self._current_goal.set_status(GoalStatus.DONE.value, reason)
        self._current_goal.last_verdict = True
        self._current_goal.last_reason = reason
        self.logger.info(f"Goal marked done: {reason}")
        self._save_goal()

    # ──────────────────────────────────────────────────────────────────────
    # Subgoal management
    # ──────────────────────────────────────────────────────────────────────

    def add_subgoal(self, text: str) -> str:
        """添加子目标。返回清理后的文本。"""
        if not self.has_goal():
            raise RuntimeError("no active goal")
        text = (text or "").strip()
        if not text:
            raise ValueError("subgoal text is empty")
        self._current_goal.subgoals.append(text)
        self.logger.info(f"Subgoal added: {text[:50]}... (total: {len(self._current_goal.subgoals)})")
        self._save_goal()
        return text

    def remove_subgoal(self, index_1based: int) -> str:
        """移除子目标（1-based 索引）"""
        if not self.has_goal():
            raise RuntimeError("no active goal")
        idx = int(index_1based) - 1
        if idx < 0 or idx >= len(self._current_goal.subgoals):
            raise IndexError(f"index out of range (1..{len(self._current_goal.subgoals)})")
        removed = self._current_goal.subgoals.pop(idx)
        self.logger.info(f"Subgoal removed: {removed[:50]}...")
        self._save_goal()
        return removed

    def clear_subgoals(self) -> int:
        """清空所有子目标，返回之前的数量"""
        if not self.has_goal():
            raise RuntimeError("no active goal")
        prev = len(self._current_goal.subgoals)
        self._current_goal.subgoals = []
        self._save_goal()
        return prev

    def get_subgoals(self) -> List[str]:
        """获取所有子目标"""
        if not self._current_goal:
            return []
        return self._current_goal.subgoals.copy()

    def render_subgoals_block(self) -> str:
        """渲染子目标为编号块"""
        if not self._current_goal or not self._current_goal.subgoals:
            return ""
        return "\n".join(f"- {i}. {text}" for i, text in enumerate(self._current_goal.subgoals, start=1))

    def next_continuation_prompt(self) -> Optional[str]:
        """返回 continuation prompt 字符串"""
        if not self._current_goal or self._current_goal.status != GoalStatus.ACTIVE.value:
            return None
        if self._current_goal.subgoals:
            return CONTINUATION_PROMPT_WITH_SUBGOALS_TEMPLATE.format(
                goal=self._current_goal.goal,
                subgoals_block=self.render_subgoals_block(),
            )
        return CONTINUATION_PROMPT_TEMPLATE.format(goal=self._current_goal.goal)

    # ──────────────────────────────────────────────────────────────────────
    # Judge 调用（支持 auxiliary 模型）
    # ──────────────────────────────────────────────────────────────────────

    async def _call_judge_async(
        self,
        goal: str,
        last_response: str,
        subgoals: Optional[List[str]] = None,
    ) -> Tuple[str, str, bool]:
        """异步调用 Judge 模型，返回 (verdict_str, reason, parse_failed)"""
        if not goal.strip():
            return "skipped", "empty goal", False
        if not last_response.strip():
            return "continue", "empty response (nothing to evaluate)", False

        # 尝试使用 auxiliary 模型
        verdict_str, reason, parse_failed = await self._call_auxiliary_judge(goal, last_response, subgoals)
        if verdict_str != "skipped":
            return verdict_str, reason, parse_failed

        # 回退到主模型（如果有配置 judge_llm）
        if hasattr(self, "_judge_llm") and self._judge_llm:
            return await self._call_main_judge(goal, last_response, subgoals)

        return "continue", "no judge client configured", False

    async def _call_auxiliary_judge(
        self,
        goal: str,
        last_response: str,
        subgoals: Optional[List[str]] = None,
    ) -> Tuple[str, str, bool]:
        """尝试使用 auxiliary.goal_judge 模型"""
        try:
            from agent.llm.auxiliary_client import acall_llm
        except ImportError:
            return "skipped", "auxiliary client unavailable", False

        # 构建 prompt
        clean_subgoals = [s.strip() for s in (subgoals or []) if s and s.strip()]
        current_time = datetime.now(tz=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")

        if clean_subgoals:
            subgoals_block = self._render_subgoals_block_static(clean_subgoals)
            user_content = JUDGE_USER_PROMPT_WITH_SUBGOALS_TEMPLATE.format(
                goal=self._truncate(goal, 2000),
                subgoals_block=self._truncate(subgoals_block, 2000),
                response=self._truncate(last_response, _JUDGE_RESPONSE_SNIPPET_CHARS),
                current_time=current_time,
            )
        else:
            user_content = JUDGE_USER_PROMPT_TEMPLATE.format(
                goal=self._truncate(goal, 2000),
                response=self._truncate(last_response, _JUDGE_RESPONSE_SNIPPET_CHARS),
                current_time=current_time,
            )

        try:
            resp = await acall_llm(
                messages=[
                    {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                task="goal_judge",
                temperature=0,
                max_tokens=self._judge_max_tokens,
            )
        except Exception as exc:
            self.logger.info("GoalManager: auxiliary judge API call failed (%s)", exc)
            return "skipped", f"judge error: {type(exc).__name__}", False

        try:
            raw = resp.content if hasattr(resp, "content") else str(resp)
        except Exception:
            raw = ""

        done, reason, parse_failed = self._parse_judge_response(raw)
        verdict = "done" if done else "continue"
        self.logger.info(f"Goal judge: verdict={verdict} reason={self._truncate(reason, 120)}")
        return verdict, reason, parse_failed

    async def _call_main_judge(
        self,
        goal: str,
        last_response: str,
        subgoals: Optional[List[str]] = None,
    ) -> Tuple[str, str, bool]:
        """使用主模型作为 Judge（回退方案）"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        subgoals_block = ""
        if subgoals:
            subgoals_block = self._render_subgoals_block_static(subgoals)

        prompt = f"""{JUDGE_SYSTEM_PROMPT}

Goal: {goal}
{subgoals_block}
Agent's most recent response:
{self._truncate(last_response, _JUDGE_RESPONSE_SNIPPET_CHARS)}

Current time: {current_time}
"""
        try:
            response = await self._judge_llm.generate(
                prompt=prompt,
                max_tokens=self._judge_max_tokens,
                temperature=0.0,
            )
            content = response.content if hasattr(response, "content") else str(response)
        except Exception as exc:
            self.logger.warning("GoalManager: main judge call failed: %s", exc)
            return "continue", f"judge error: {exc}", False

        done, reason, parse_failed = self._parse_judge_response(content)
        return ("done" if done else "continue"), reason, parse_failed

    @staticmethod
    def _truncate(text: str, limit: int) -> str:
        """截断文本到指定长度"""
        if not text:
            return ""
        if len(text) <= limit:
            return text
        return text[:limit] + "… [truncated]"

    @staticmethod
    def _render_subgoals_block_static(subgoals: List[str]) -> str:
        """静态方法渲染子目标块"""
        return "\n".join(f"- {i}. {text}" for i, text in enumerate(subgoals, start=1))

    def _parse_judge_response(self, raw: str) -> Tuple[bool, str, bool]:
        """解析 Judge 响应。解析失败返回 (False, reason, True)"""
        if not raw:
            return False, "judge returned empty response", True

        text = raw.strip()

        # 去除 markdown 代码块
        if text.startswith("```"):
            text = text.strip("`")
            nl = text.find("\n")
            if nl != -1:
                text = text[nl + 1:]

        # 尝试解析 JSON
        data: Optional[Dict[str, Any]] = None
        try:
            data = json.loads(text)
        except Exception:
            # 尝试提取第一个 JSON 对象
            match = re.search(r"\{.*?\}", text, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(0))
                except Exception:
                    data = None

        if not isinstance(data, dict):
            return False, f"judge reply was not JSON: {self._truncate(raw, 200)!r}", True

        done_val = data.get("done")
        if isinstance(done_val, str):
            done = done_val.strip().lower() in {"true", "yes", "1", "done"}
        else:
            done = bool(done_val)

        reason = str(data.get("reason") or "").strip()
        if not reason:
            reason = "no reason provided"

        return done, reason, False

    # ──────────────────────────────────────────────────────────────────────
    # Persistence
    # ──────────────────────────────────────────────────────────────────────

    def _get_session_db(self):
        """获取 SessionDB 实例"""
        try:
            from agent.session import FileSessionStore
            from common.config import get_sessions_dir
            return FileSessionStore(str(get_sessions_dir()))
        except ImportError:
            return None

    def _save_goal(self):
        """保存目标到 SessionDB"""
        if not self._current_goal or not self._session_id:
            return

        try:
            db = self._get_session_db()
            if db:
                # 使用 session_id 保存，添加元数据
                db.save(self._session_id, {
                    "goal": self._current_goal.to_json(),
                    "_goal_meta": {
                        "session_id": self._session_id,
                        "goal_text": self._current_goal.goal[:100],
                        "status": self._current_goal.status,
                    }
                })
                self.logger.debug("Goal saved to SessionDB for session: %s", self._session_id)
            else:
                key = f"goal:{self._session_id}"
                self._memory_store[key] = {"goal": self._current_goal.to_json()}
                self.logger.debug("Goal saved to memory store: %s", key)
        except Exception as e:
            self.logger.warning("Failed to save goal: %s", e)

    def _load_goal_from_db(self) -> Optional[GoalState]:
        """从 SessionDB 加载目标"""
        if not self._session_id:
            return None

        try:
            db = self._get_session_db()
            if db:
                data = db.load(self._session_id)
                if data and "goal" in data:
                    return GoalState.from_json(data["goal"])
            else:
                key = f"goal:{self._session_id}"
                data = self._memory_store.get(key)
                if data and "goal" in data:
                    return GoalState.from_json(data["goal"])
        except Exception as e:
            self.logger.debug(f"Failed to load goal from SessionDB: {e}")
        return None

    def load_goal(self, session_id: str) -> Optional[GoalState]:
        """公开方法：从 SessionDB 加载目标"""
        self._session_id = session_id
        return self._load_goal_from_db()

    def has_saved_goal(self, session_id: str) -> bool:
        """检查是否存在保存的目标"""
        goal = self.load_goal(session_id)
        return goal is not None

    # ──────────────────────────────────────────────────────────────────────
    # Exit Decision（统一退出判断接口）
    # ──────────────────────────────────────────────────────────────────────

    async def evaluate(
        self,
        last_response: str,
        current_turn: int,
        max_turns: int,
    ) -> ExitDecision:
        """
        异步评估是否应该退出（Goal 模式唯一入口）

        设计原则（单一职责）：
        - 只负责 Judge 评估逻辑
        - 轮次消耗由 AgentState 统一管理
        - 预算检查由 AgentState 统一管理

        注意：此方法不消耗轮次，轮次信息通过参数传入

        Args:
            last_response: 最后一次 Agent 响应
            current_turn: 当前轮次（由 AgentState 传入）
            max_turns: 最大轮次（由 AgentState 传入）

        Returns:
            ExitDecision: 统一退出决策
        """
        state = self._current_goal

        # 无活跃 Goal：立即退出
        if state is None or state.status != GoalStatus.ACTIVE.value:
            return ExitDecision(
                should_exit=True,
                reason=ExitReason.UNKNOWN,
                message="no active goal",
            )

        # 更新状态（但不消耗轮次，由 AgentState 管理）
        state.last_turn_at = time.time()
        state.current_turn = current_turn

        # 调用 Judge
        verdict_str, reason, parse_failed = await self._call_judge_async(
            state.goal, last_response, state.subgoals or None
        )
        state.last_verdict = verdict_str == "done"
        state.last_reason = reason

        # 跟踪连续解析失败
        if parse_failed:
            state.consecutive_parse_failures += 1
        else:
            state.consecutive_parse_failures = 0

        if verdict_str == "done":
            # Goal 完成
            state.set_status(GoalStatus.DONE.value, "Judge confirmed completion")
            self._save_goal()
            return ExitDecision(
                should_exit=True,
                reason=ExitReason.GOAL_COMPLETED,
                message=f"✓ 目标达成: {reason}",
                metadata={"verdict": "done"},
            )

        # Auto-pause: Judge 连续解析失败
        if state.consecutive_parse_failures >= DEFAULT_MAX_CONSECUTIVE_PARSE_FAILURES:
            state.set_status(
                GoalStatus.PAUSED.value,
                f"judge model returned unparseable output {state.consecutive_parse_failures} turns in a row"
            )
            state.paused_reason = f"judge model returned unparseable output {state.consecutive_parse_failures} turns in a row"
            self._save_goal()
            return ExitDecision(
                should_exit=True,
                reason=ExitReason.GOAL_PAUSED,
                message=f"⚠ Goal 暂停 — Judge 模型连续 {state.consecutive_parse_failures} 次返回不可解析输出",
                metadata={"verdict": "parse_failure"},
            )

        # 轮次耗尽（由 AgentState 检查后传入）
        if current_turn >= max_turns:
            state.set_status(GoalStatus.PAUSED.value, f"turn budget exhausted ({current_turn}/{max_turns})")
            state.paused_reason = f"turn budget exhausted ({current_turn}/{max_turns})"
            self._save_goal()
            return ExitDecision(
                should_exit=True,
                reason=ExitReason.GOAL_PAUSED,
                message=f"⚠ Goal 暂停 — {current_turn}/{max_turns} 轮次已用完",
                metadata={"verdict": "budget_exhausted"},
            )

        # 继续执行
        self._save_goal()
        return ExitDecision(
            should_exit=False,
            reason=ExitReason.UNKNOWN,
            message=f"↻ 继续目标 ({current_turn}/{max_turns}): {reason}",
            continuation_prompt=self.next_continuation_prompt(),
            metadata={"verdict": "continue"},
        )