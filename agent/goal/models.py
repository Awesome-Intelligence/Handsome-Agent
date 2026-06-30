#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Goal Manager Data Models
"""

import json
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Dict, Optional, Any


class GoalStatus(Enum):
    """
    Goal 状态枚举

    状态转换规则：
    - ACTIVE ↔ PAUSED: 用户手动暂停/恢复
    - ACTIVE → DONE: Judge 判定完成
    - ACTIVE → EXPIRED: 轮次耗尽
    - ACTIVE/PAUSED → CLEARED: 用户主动清除
    - PAUSED → ACTIVE: 用户恢复
    - EXPIRED/DONE/CLEARED → 不可转换（需重新创建）
    """
    ACTIVE = "active"      # 活跃状态，正在执行
    PAUSED = "paused"     # 暂停状态（用户暂停/Judge 解析失败自动暂停）
    DONE = "done"         # 完成状态（Judge 判定完成）
    CLEARED = "cleared"   # 清除状态（用户主动清除，保留审计）
    EXPIRED = "expired"   # 过期状态（轮次耗尽未完成）


@dataclass
class JudgeVerdict:
    """Judge 判决结果"""
    done: bool  # 目标是否完成
    reason: str  # 判决理由
    todo_list: Optional[List[Dict]] = None  # Judge 认为的 todo 状态


@dataclass
class GoalState:
    """目标状态

    注意：任务列表（subtasks）不再存储在 GoalState 中，
    统一由 SessionTodoStore 管理，GoalManager 通过读取 Todo 判断完成状态。

    Subgoal 机制：
    - 用户可以通过 /subgoal <text> 追加额外验收标准
    - Judge 会同时评估原始目标和所有 subgoals

    状态机：
    - status: 当前状态（ACTIVE/PAUSED/DONE/CLEARED/EXPIRED）
    - status_history: 状态转换审计记录
    """
    goal: str  # 用户原始目标
    max_turns: int = 90  # 最大轮次（参考 Hermes）
    current_turn: int = 0  # 当前轮次
    status: str = GoalStatus.ACTIVE.value  # 当前状态
    status_history: List[Dict] = field(default_factory=list)  # 状态转换审计记录
    paused_reason: Optional[str] = None  # 暂停原因
    verdict_history: List[Dict] = field(default_factory=list)  # Judge 判决历史
    continuation_count: int = 0  # 连续 Judge 认为未完成次数
    last_verdict: Optional[bool] = None  # 上次判决结果
    last_reason: Optional[str] = None  # 上次判决理由
    last_turn_at: float = field(default_factory=lambda: time.time())  # 上次轮次更新时间
    created_at: float = field(default_factory=lambda: time.time())  # 创建时间
    completed_at: Optional[float] = None  # 完成时间（DONE/EXPIRED/CLEARED）
    consecutive_parse_failures: int = 0  # 连续解析失败次数
    subgoals: List[str] = field(default_factory=list)  # 用户追加的子目标列表

    def set_status(self, new_status: str, reason: Optional[str] = None):
        """
        设置状态并记录转换历史

        Args:
            new_status: 新状态
            reason: 状态转换原因
        """
        if self.status != new_status:
            self.status_history.append({
                "from_status": self.status,
                "to_status": new_status,
                "reason": reason or "",
                "timestamp": time.time(),
            })
            self.status = new_status
            if new_status in [GoalStatus.DONE.value, GoalStatus.EXPIRED.value, GoalStatus.CLEARED.value]:
                self.completed_at = time.time()

    def to_json(self) -> str:
        """序列化为 JSON 字符串"""
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str) -> "GoalState":
        """从 JSON 字符串反序列化"""
        data = json.loads(raw)
        return cls(
            goal=data.get("goal", ""),
            max_turns=int(data.get("max_turns", 90) or 90),
            current_turn=int(data.get("current_turn", 0) or 0),
            status=data.get("status", GoalStatus.ACTIVE.value),
            status_history=data.get("status_history") or [],
            verdict_history=data.get("verdict_history") or [],
            continuation_count=int(data.get("continuation_count", 0) or 0),
            created_at=float(data.get("created_at", time.time()) or time.time()),
            last_turn_at=float(data.get("last_turn_at", time.time()) or time.time()),
            completed_at=data.get("completed_at"),
            last_verdict=data.get("last_verdict"),
            last_reason=data.get("last_reason"),
            paused_reason=data.get("paused_reason"),
            consecutive_parse_failures=int(data.get("consecutive_parse_failures", 0) or 0),
            subgoals=data.get("subgoals") or [],
        )