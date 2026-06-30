#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tool Loop Guardrail - 参考 Hermes 设计

核心原则：
1. 只追踪失败的工具调用
2. 成功执行清除失败计数
3. 区分三种检测类型：exact_failure / same_tool_failure / no_progress
4. 默认只警告，不阻止（可通过配置启用硬停止）

检测流程：
1. before_call: 检查是否应该阻止
2. 执行工具
3. after_call: 更新计数，判断是否警告/阻止

子层标识：✅ Task
主层：🧠 Decision
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Dict, Tuple, List

# 幂等工具（只读，不产生副作用）
IDEMPOTENT_TOOL_NAMES: frozenset = frozenset({
    "read_file",
    "search_files",
    "web_search",
    "web_extract",
    "session_search",
    "list_directory",
    "get_file_info",
    "read_multiple_files",
    "browser_snapshot",
    "browser_console",
    "get_file_tree",
})

# 变更工具（会产生副作用）- 用于判断非幂等
MUTATING_TOOL_NAMES: frozenset = frozenset({
    "write_file",
    "patch",
    "terminal",
    "execute_code",
    "todo",
    "create_directory",
    "delete_file",
    "browser_click",
    "browser_type",
    "browser_press",
    "browser_scroll",
    "browser_navigate",
})


@dataclass
class ToolLoopConfig:
    """Tool Loop 检测配置"""

    # 是否启用警告
    warnings_enabled: bool = True
    # 是否启用硬停止（阻止工具执行）
    hard_stop_enabled: bool = False

    # exact_failure: 完全相同的调用（tool_name + args）重复失败
    exact_failure_warn_after: int = 2  # 警告阈值
    exact_failure_block_after: int = 5  # 阻止阈值

    # same_tool_failure: 同一工具名称重复失败
    same_tool_failure_warn_after: int = 3
    same_tool_failure_halt_after: int = 8

    # no_progress: 幂等工具返回相同结果（无进展）
    no_progress_warn_after: int = 2
    no_progress_block_after: int = 5

    @classmethod
    def from_mapping(cls, data: Optional[Mapping[str, Any]]) -> "ToolLoopConfig":
        """从配置字典加载"""
        if not data:
            return cls()

        # 解析 warn_after
        warn_after = data.get("warn_after", {})
        if not isinstance(warn_after, Mapping):
            warn_after = {}

        # 解析 hard_stop_after
        hard_stop_after = data.get("hard_stop_after", {})
        if not isinstance(hard_stop_after, Mapping):
            hard_stop_after = {}

        return cls(
            warnings_enabled=data.get("warnings_enabled", True),
            hard_stop_enabled=data.get("hard_stop_enabled", False),
            exact_failure_warn_after=warn_after.get(
                "exact_failure", data.get("exact_failure_warn_after", 2)
            ),
            exact_failure_block_after=hard_stop_after.get(
                "exact_failure", data.get("exact_failure_block_after", 5)
            ),
            same_tool_failure_warn_after=warn_after.get(
                "same_tool_failure", data.get("same_tool_failure_warn_after", 3)
            ),
            same_tool_failure_halt_after=hard_stop_after.get(
                "same_tool_failure", data.get("same_tool_failure_halt_after", 8)
            ),
            no_progress_warn_after=warn_after.get(
                "idempotent_no_progress", data.get("no_progress_warn_after", 2)
            ),
            no_progress_block_after=hard_stop_after.get(
                "idempotent_no_progress", data.get("no_progress_block_after", 5)
            ),
        )


@dataclass
class ToolCallSignature:
    """工具调用的稳定标识（用于检测 exact_failure）"""

    tool_name: str
    args_hash: str

    @classmethod
    def from_call(
        cls, tool_name: str, args: Optional[Mapping[str, Any]]
    ) -> "ToolCallSignature":
        """从工具名称和参数生成签名"""
        if args is None:
            args = {}
        # 规范化参数为 JSON（排序键以保证一致性）
        canonical = json.dumps(
            dict(args), sort_keys=True, ensure_ascii=False, default=str
        )
        args_hash = hashlib.sha256(canonical.encode()).hexdigest()[:16]
        return cls(tool_name=tool_name, args_hash=args_hash)

    def __hash__(self) -> int:
        return hash((self.tool_name, self.args_hash))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ToolCallSignature):
            return False
        return self.tool_name == other.tool_name and self.args_hash == other.args_hash


@dataclass
class ToolLoopDecision:
    """Tool Loop 检测决策"""

    action: str = "allow"  # allow | warn | block | halt
    code: str = ""
    message: str = ""
    count: int = 0
    tool_name: str = ""

    @property
    def allows_execution(self) -> bool:
        """是否允许执行（warn 状态也允许）"""
        return self.action in {"allow", "warn"}

    @property
    def should_halt(self) -> bool:
        """是否应该停止循环"""
        return self.action in {"block", "halt"}

    @property
    def is_warning(self) -> bool:
        """是否是警告"""
        return self.action == "warn"


def _classify_tool_failure(tool_name: str, result: Any) -> Tuple[bool, str]:
    """
    分类工具调用是否失败。

    Returns:
        (is_failed, reason): 是否失败及原因摘要
    """
    if result is None:
        return False, ""

    # 字典结果检查
    if isinstance(result, dict):
        if result.get("success") is False:
            return True, "[failed]"
        if result.get("error"):
            return True, "[error]"
        # terminal 特殊检查 exit_code
        if tool_name == "terminal":
            exit_code = result.get("exit_code")
            if exit_code is not None and exit_code != 0:
                return True, f"[exit {exit_code}]"
        # memory 特殊检查容量限制
        if tool_name == "memory":
            if result.get("success") is False and "exceed the limit" in str(
                result.get("error", "")
            ):
                return True, "[full]"

    # 字符串结果检查（取前 500 字符加速）
    result_str = str(result)[:500].lower()
    if '"error"' in result_str or '"failed"' in result_str:
        return True, "[error]"
    if isinstance(result, str) and result.startswith("Error"):
        return True, "[error]"

    return False, ""


class ToolLoopController:
    """
    Per-turn 工具循环检测控制器

    负责追踪工具调用模式，检测以下情况：
    1. exact_failure: 完全相同的调用重复失败
    2. same_tool_failure: 同一工具重复失败
    3. no_progress: 幂等工具返回相同结果（无进展）

    设计原则：
    - 成功执行会清除失败计数
    - 默认只警告，不阻止
    - 每个 turn 开始时重置状态
    """

    def __init__(self, config: Optional[ToolLoopConfig] = None):
        self.config = config or ToolLoopConfig()
        self.reset()

    def reset(self) -> None:
        """重置每轮状态（在每个 turn 开始时调用）"""
        self._exact_failure_counts: Dict[ToolCallSignature, int] = {}
        self._same_tool_failure_counts: Dict[str, int] = {}
        self._no_progress: Dict[ToolCallSignature, Tuple[str, int]] = {}  # (result_hash, count)
        self._halt_decision: Optional[ToolLoopDecision] = None
        self._last_warning: Optional[str] = None

    @property
    def halt_decision(self) -> Optional[ToolLoopDecision]:
        """获取 halt 决策（如果触发过）"""
        return self._halt_decision

    @property
    def last_warning(self) -> Optional[str]:
        """获取最后一条警告信息"""
        return self._last_warning

    def before_call(
        self, tool_name: str, args: Optional[Mapping[str, Any]]
    ) -> ToolLoopDecision:
        """
        工具调用前检查

        Args:
            tool_name: 工具名称
            args: 工具参数

        Returns:
            ToolLoopDecision: 检查决策
        """
        sig = ToolCallSignature.from_call(tool_name, args)

        if not self.config.hard_stop_enabled:
            return ToolLoopDecision(tool_name=tool_name)

        # 检查 exact_failure 是否达到阻止阈值
        exact_count = self._exact_failure_counts.get(sig, 0)
        if exact_count >= self.config.exact_failure_block_after:
            decision = ToolLoopDecision(
                action="block",
                code="repeated_exact_failure_block",
                message=(
                    f"Blocked {tool_name}: the same tool call failed {exact_count} "
                    "times with identical arguments. Stop retrying it unchanged; "
                    "change strategy or explain the blocker."
                ),
                count=exact_count,
                tool_name=tool_name,
            )
            self._halt_decision = decision
            return decision

        # 检查 no_progress（幂等工具）
        if self._is_idempotent(tool_name):
            record = self._no_progress.get(sig)
            if record is not None:
                _, repeat_count = record
                if repeat_count >= self.config.no_progress_block_after:
                    decision = ToolLoopDecision(
                        action="block",
                        code="idempotent_no_progress_block",
                        message=(
                            f"Blocked {tool_name}: this read-only call returned the same "
                            f"result {repeat_count} times. Stop repeating it unchanged; "
                            "use the result already provided or try a different query."
                        ),
                        count=repeat_count,
                        tool_name=tool_name,
                    )
                    self._halt_decision = decision
                    return decision

        return ToolLoopDecision(tool_name=tool_name)

    def after_call(
        self,
        tool_name: str,
        args: Optional[Mapping[str, Any]],
        result: Any,
        failed: Optional[bool] = None,
    ) -> ToolLoopDecision:
        """
        工具调用后更新状态

        Args:
            tool_name: 工具名称
            args: 工具参数
            result: 工具执行结果
            failed: 是否失败（None=自动检测）

        Returns:
            ToolLoopDecision: 检测决策
        """
        args = args or {}
        sig = ToolCallSignature.from_call(tool_name, args)

        # 判断是否失败
        if failed is None:
            failed, _ = _classify_tool_failure(tool_name, result)

        if failed:
            return self._handle_failure(sig, tool_name)
        else:
            return self._handle_success(sig, tool_name, result)

    def _is_idempotent(self, tool_name: str) -> bool:
        """判断工具是否为幂等工具"""
        # 显式声明的变更工具不是幂等
        if tool_name in MUTATING_TOOL_NAMES:
            return False
        # 显式声明的幂等工具是幂等
        if tool_name in IDEMPOTENT_TOOL_NAMES:
            return True
        # 浏览器相关工具默认非幂等
        if tool_name.startswith("browser_"):
            return False
        # 未知工具保守假设为非幂等
        return False

    def _handle_failure(
        self, sig: ToolCallSignature, tool_name: str
    ) -> ToolLoopDecision:
        """处理工具调用失败"""
        # 计数 +1
        exact_count = self._exact_failure_counts.get(sig, 0) + 1
        self._exact_failure_counts[sig] = exact_count
        self._no_progress.pop(sig, None)  # 失败后清除无进展记录

        same_count = self._same_tool_failure_counts.get(tool_name, 0) + 1
        self._same_tool_failure_counts[tool_name] = same_count

        # 检查是否需要 halt
        if (
            self.config.hard_stop_enabled
            and same_count >= self.config.same_tool_failure_halt_after
        ):
            decision = ToolLoopDecision(
                action="halt",
                code="same_tool_failure_halt",
                message=(
                    f"Stopped {tool_name}: it failed {same_count} times this turn. "
                    "Stop retrying the same failing tool path and choose a different approach."
                ),
                count=same_count,
                tool_name=tool_name,
            )
            self._halt_decision = decision
            self._last_warning = decision.message
            return decision

        # 生成警告
        warnings: List[str] = []
        if self.config.warnings_enabled:
            if exact_count >= self.config.exact_failure_warn_after:
                warnings.append(
                    f"{tool_name} has failed {exact_count} times with identical arguments. "
                    "This looks like a loop; inspect the error and change strategy "
                    "instead of retrying it unchanged."
                )
            if same_count >= self.config.same_tool_failure_warn_after:
                warnings.append(
                    f"{tool_name} has failed {same_count} times this turn. "
                    "This looks like a loop. Do not switch to text-only replies; "
                    "keep using tools, but diagnose before retrying."
                )

        if warnings:
            warning_msg = " ".join(warnings)
            self._last_warning = warning_msg
            return ToolLoopDecision(
                action="warn",
                code="tool_failure_warning",
                message=warning_msg,
                count=same_count,
                tool_name=tool_name,
            )

        return ToolLoopDecision(tool_name=tool_name, count=exact_count)

    def _handle_success(
        self, sig: ToolCallSignature, tool_name: str, result: Any
    ) -> ToolLoopDecision:
        """处理工具调用成功"""
        # ✅ 成功执行 → 清除该工具的失败计数
        self._exact_failure_counts.pop(sig, None)
        self._same_tool_failure_counts.pop(tool_name, None)

        # 非幂等工具不追踪无进展
        if not self._is_idempotent(tool_name):
            self._no_progress.pop(sig, None)
            return ToolLoopDecision(tool_name=tool_name)

        # 追踪幂等工具的无进展
        result_hash = hashlib.md5(str(result).encode("utf-8")).hexdigest()[:16]
        previous = self._no_progress.get(sig)
        repeat_count = 1
        if previous is not None and previous[0] == result_hash:
            repeat_count = previous[1] + 1
        self._no_progress[sig] = (result_hash, repeat_count)

        # 检查无进展警告
        if self.config.warnings_enabled and repeat_count >= self.config.no_progress_warn_after:
            warning_msg = (
                f"{tool_name} returned the same result {repeat_count} times. "
                "Use the result already provided or change the query instead of "
                "repeating it unchanged."
            )
            self._last_warning = warning_msg
            return ToolLoopDecision(
                action="warn",
                code="idempotent_no_progress_warning",
                message=warning_msg,
                count=repeat_count,
                tool_name=tool_name,
            )

        return ToolLoopDecision(tool_name=tool_name, count=repeat_count)

    def get_stats(self) -> Dict[str, Any]:
        """获取当前统计信息（用于调试）"""
        return {
            "exact_failure_count": len(self._exact_failure_counts),
            "same_tool_failure_count": len(self._same_tool_failure_counts),
            "no_progress_count": len(self._no_progress),
            "has_halt": self._halt_decision is not None,
            "last_warning": self._last_warning,
        }


def append_toolguard_guidance(
    result: str, decision: ToolLoopDecision
) -> str:
    """
    将警告信息追加到工具结果中

    Args:
        result: 原始结果
        decision: 检测决策

    Returns:
        追加警告后的结果
    """
    if decision.action not in {"warn", "halt"} or not decision.message:
        return result

    label = "Tool loop hard stop" if decision.action == "halt" else "Tool loop warning"
    suffix = (
        f"\n\n[{label}: {decision.code}; count={decision.count}; {decision.message}]"
    )
    return (result or "") + suffix


__all__ = [
    "ToolLoopConfig",
    "ToolCallSignature",
    "ToolLoopDecision",
    "ToolLoopController",
    "IDEMPOTENT_TOOL_NAMES",
    "MUTATING_TOOL_NAMES",
    "append_toolguard_guidance",
]