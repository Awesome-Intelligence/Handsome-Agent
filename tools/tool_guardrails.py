#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tool Guardrails - 工具循环防护

防止工具被无限调用导致死循环。

功能：
1. 检测幂等工具的重复调用
2. 检测同一工具的连续失败
3. 提供警告和阻止机制

参考 Hermes 的 agent/tool_guardrails.py 实现。

日志子层：🛠️ ToolExec
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from common.logging_manager import get_execution_logger

# ═══════════════════════════════════════════════════════════════════════════════
# 常量定义
# ═══════════════════════════════════════════════════════════════════════════════

# 幂等工具列表 - 读取操作，重复调用不会改变系统状态
IDEMPOTENT_TOOL_NAMES = frozenset({
    "read_file",
    "list_directory",
    "search_files",
    "web_search",
    "fetch_url",
    "session_search",
    "get_memory",
    "detect_browsers",
    "browser_snapshot",
})

# 可能会修改系统的工具列表
MUTATING_TOOL_NAMES = frozenset({
    "write_file",
    "execute_terminal",
    "execute_code",
    "open_folder",
    "open_browser",
    "memory_save",
    "memory_delete",
    "delete_file",
    "create_directory",
})


# ═══════════════════════════════════════════════════════════════════════════════
# 数据类定义
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ToolGuardrailConfig:
    """工具循环防护配置"""

    warnings_enabled: bool = True  # 是否启用警告
    hard_stop_enabled: bool = False  # 是否启用硬停止
    exact_failure_warn_after: int = 2  # 精确失败警告阈值
    exact_failure_block_after: int = 5  # 精确失败阻止阈值
    same_tool_failure_warn_after: int = 3  # 同一工具失败警告阈值
    same_tool_failure_halt_after: int = 8  # 同一工具失败停止阈值
    no_progress_warn_after: int = 2  # 无进展警告阈值（幂等工具）
    no_progress_block_after: int = 5  # 无进展阻止阈值（幂等工具）
    idempotent_tools: frozenset[str] = field(default_factory=lambda: IDEMPOTENT_TOOL_NAMES)
    mutating_tools: frozenset[str] = field(default_factory=lambda: MUTATING_TOOL_NAMES)


@dataclass(frozen=True)
class ToolCallSignature:
    """工具调用的稳定标识（工具名 + 参数哈希）"""

    tool_name: str
    args_hash: str

    @classmethod
    def from_call(cls, tool_name: str, args: Mapping[str, Any] | None = None) -> "ToolCallSignature":
        """从工具调用创建签名"""
        canonical = _canonicalize_args(args or {})
        return cls(tool_name=tool_name, args_hash=_sha256(canonical))


@dataclass(frozen=True)
class ToolGuardrailDecision:
    """工具循环防护决策"""

    action: str = "allow"  # allow | warn | block | halt
    code: str = ""
    message: str = ""
    tool_name: str = ""
    count: int = 0
    signature: Optional[ToolCallSignature] = None

    @property
    def allows_execution(self) -> bool:
        """是否允许执行"""
        return self.action in {"allow", "warn"}

    @property
    def should_halt(self) -> bool:
        """是否应该停止"""
        return self.action in {"block", "halt"}

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        result = {
            "action": self.action,
            "code": self.code,
            "message": self.message,
            "tool_name": self.tool_name,
            "count": self.count,
        }
        if self.signature:
            result["signature"] = {
                "tool_name": self.signature.tool_name,
                "args_hash": self.signature.args_hash,
            }
        return result


# ═══════════════════════════════════════════════════════════════════════════════
# 工具循环防护控制器
# ═══════════════════════════════════════════════════════════════════════════════

class ToolCallGuardrailController:
    """工具调用循环防护控制器"""

    def __init__(self, config: ToolGuardrailConfig | None = None):
        """
        初始化防护控制器

        Args:
            config: 防护配置，默认使用 ToolGuardrailConfig()
        """
        self.config = config or ToolGuardrailConfig()
        self.logger = get_execution_logger(self.__class__.__name__, sublayer="tool_exec")
        self.reset_for_turn()

    def reset_for_turn(self) -> None:
        """重置每轮的状态"""
        self._exact_failure_counts: dict[ToolCallSignature, int] = {}
        self._same_tool_failure_counts: dict[str, int] = {}
        self._no_progress: dict[ToolCallSignature, tuple[str, int]] = {}
        self._halt_decision: Optional[ToolGuardrailDecision] = None

    @property
    def halt_decision(self) -> Optional[ToolGuardrailDecision]:
        """获取停止决策"""
        return self._halt_decision

    def before_call(self, tool_name: str, args: Mapping[str, Any] | None = None) -> ToolGuardrailDecision:
        """
        在工具调用前检查

        Args:
            tool_name: 工具名称
            args: 工具参数

        Returns:
            ToolGuardrailDecision: 决策结果
        """
        args = _coerce_args(args)
        signature = ToolCallSignature.from_call(tool_name, args)

        # 如果未启用硬停止，直接允许
        if not self.config.hard_stop_enabled:
            return ToolGuardrailDecision(tool_name=tool_name, signature=signature)

        # 检查精确失败阻止
        exact_count = self._exact_failure_counts.get(signature, 0)
        if exact_count >= self.config.exact_failure_block_after:
            decision = ToolGuardrailDecision(
                action="block",
                code="repeated_exact_failure_block",
                message=(
                    f"阻止 {tool_name}: 相同的工具调用已经失败 {exact_count} 次。"
                    "请改变策略或解释阻塞原因。"
                ),
                tool_name=tool_name,
                count=exact_count,
                signature=signature,
            )
            self._halt_decision = decision
            return decision

        # 检查幂等工具的无进展阻止
        if self._is_idempotent(tool_name):
            record = self._no_progress.get(signature)
            if record is not None:
                _, repeat_count = record
                if repeat_count >= self.config.no_progress_block_after:
                    decision = ToolGuardrailDecision(
                        action="block",
                        code="idempotent_no_progress_block",
                        message=(
                            f"阻止 {tool_name}: 这个只读工具已经返回相同结果 {repeat_count} 次。"
                            "请使用已提供的结果或尝试不同的查询。"
                        ),
                        tool_name=tool_name,
                        count=repeat_count,
                        signature=signature,
                    )
                    self._halt_decision = decision
                    return decision

        return ToolGuardrailDecision(tool_name=tool_name, signature=signature)

    def after_call(
        self,
        tool_name: str,
        args: Mapping[str, Any] | None = None,
        result: Any = None,
        failed: bool | None = None,
    ) -> ToolGuardrailDecision:
        """
        在工具调用后检查

        Args:
            tool_name: 工具名称
            args: 工具参数
            result: 工具执行结果
            failed: 是否失败（None 表示自动检测）

        Returns:
            ToolGuardrailDecision: 决策结果
        """
        args = _coerce_args(args)
        signature = ToolCallSignature.from_call(tool_name, args)

        # 自动检测失败
        if failed is None:
            failed = self._detect_failure(tool_name, result)

        if failed:
            # 更新失败计数
            exact_count = self._exact_failure_counts.get(signature, 0) + 1
            self._exact_failure_counts[signature] = exact_count
            self._no_progress.pop(signature, None)

            same_count = self._same_tool_failure_counts.get(tool_name, 0) + 1
            self._same_tool_failure_counts[tool_name] = same_count

            self.logger.warning(
                f"Tool failed: {tool_name} (exact={exact_count}, same_tool={same_count})"
            )

            # 检查硬停止：同一工具多次失败
            if self.config.hard_stop_enabled and same_count >= self.config.same_tool_failure_halt_after:
                decision = ToolGuardrailDecision(
                    action="halt",
                    code="same_tool_failure_halt",
                    message=(
                        f"停止 {tool_name}: 该工具本次对话已失败 {same_count} 次。"
                        "请选择不同的工具路径。"
                    ),
                    tool_name=tool_name,
                    count=same_count,
                    signature=signature,
                )
                self._halt_decision = decision
                return decision

            # 检查警告：精确失败
            if self.config.warnings_enabled and exact_count >= self.config.exact_failure_warn_after:
                return ToolGuardrailDecision(
                    action="warn",
                    code="repeated_exact_failure_warning",
                    message=(
                        f"{tool_name} 已使用相同参数失败 {exact_count} 次。"
                        "这看起来像循环；请检查错误并改变策略。"
                    ),
                    tool_name=tool_name,
                    count=exact_count,
                    signature=signature,
                )

            # 检查警告：同一工具多次失败
            if self.config.warnings_enabled and same_count >= self.config.same_tool_failure_warn_after:
                return ToolGuardrailDecision(
                    action="warn",
                    code="same_tool_failure_warning",
                    message=_get_recovery_hint(tool_name, same_count),
                    tool_name=tool_name,
                    count=same_count,
                    signature=signature,
                )

            return ToolGuardrailDecision(tool_name=tool_name, count=exact_count, signature=signature)

        # 成功时清除失败记录
        self._exact_failure_counts.pop(signature, None)
        self._same_tool_failure_counts.pop(tool_name, None)

        # 检查幂等工具的无进展
        if not self._is_idempotent(tool_name):
            self._no_progress.pop(signature, None)
            return ToolGuardrailDecision(tool_name=tool_name, signature=signature)

        # 计算结果哈希
        result_hash = _compute_result_hash(result)
        previous = self._no_progress.get(signature)
        repeat_count = 1
        if previous is not None and previous[0] == result_hash:
            repeat_count = previous[1] + 1
        self._no_progress[signature] = (result_hash, repeat_count)

        # 检查无进展警告
        if self.config.warnings_enabled and repeat_count >= self.config.no_progress_warn_after:
            return ToolGuardrailDecision(
                action="warn",
                code="idempotent_no_progress_warning",
                message=(
                    f"{tool_name} 已返回相同结果 {repeat_count} 次。"
                    "请使用已提供的结果或改变查询。"
                ),
                tool_name=tool_name,
                count=repeat_count,
                signature=signature,
            )

        return ToolGuardrailDecision(tool_name=tool_name, count=repeat_count, signature=signature)

    def _is_idempotent(self, tool_name: str) -> bool:
        """判断工具是否是幂等的"""
        if tool_name in self.config.mutating_tools:
            return False
        return tool_name in self.config.idempotent_tools

    def _detect_failure(self, tool_name: str, result: Any) -> bool:
        """检测工具是否失败"""
        if result is None:
            return False

        # 解析结果
        result_str = str(result) if not isinstance(result, str) else result
        result_lower = result_str[:500].lower()

        # 检查错误标记
        if '"error"' in result_lower or '"failed"' in result_lower:
            return True

        if result_str.startswith("Error") or result_str.startswith("错误"):
            return True

        # terminal 工具检查 exit_code
        if tool_name == "execute_terminal" or tool_name == "terminal":
            try:
                data = json.loads(result_str) if result_str.startswith("{") else {}
                exit_code = data.get("exit_code")
                if exit_code is not None and exit_code != 0:
                    return True
            except (json.JSONDecodeError, TypeError):
                pass

        # memory 工具检查
        if tool_name == "memory_save":
            try:
                data = json.loads(result_str) if result_str.startswith("{") else {}
                if data.get("success") is False:
                    return True
            except (json.JSONDecodeError, TypeError):
                pass

        return False


# ═══════════════════════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════════════════════

def _canonicalize_args(args: Mapping[str, Any]) -> str:
    """将工具参数规范化为 JSON 字符串"""
    if not isinstance(args, Mapping):
        return "{}"
    return json.dumps(
        args,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def _coerce_args(args: Mapping[str, Any] | None) -> Mapping[str, Any]:
    """确保参数是 Mapping 类型"""
    return args if isinstance(args, Mapping) else {}


def _compute_result_hash(result: Any) -> str:
    """计算结果哈希"""
    if result is None:
        return _sha256("")

    try:
        if isinstance(result, str):
            parsed = json.loads(result)
        else:
            parsed = result

        canonical = json.dumps(
            parsed,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
    except (json.JSONDecodeError, TypeError, ValueError):
        canonical = str(result)

    return _sha256(canonical)


def _sha256(value: str) -> str:
    """计算 SHA256 哈希"""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _get_recovery_hint(tool_name: str, count: int) -> str:
    """获取工具失败的恢复提示"""
    common = (
        f"{tool_name} 已失败 {count} 次。这看起来像循环。"
        "请在重试前先检查错误和输出。"
    )

    if tool_name == "execute_terminal" or tool_name == "terminal":
        return common + (
            " 对于终端失败，请先运行 `pwd` 和 `ls` 诊断，"
            "然后尝试使用绝对路径、更简单的命令、或不同的工具（如 read_file）。"
        )

    return common + (
        " 请尝试不同的参数、更窄的查询、或不同的工具。"
        "如果问题来自外部，请报告阻塞原因。"
    )


def append_guardrail_warning(result: str, decision: ToolGuardrailDecision) -> str:
    """为工具结果附加防护警告"""
    if decision.action not in {"warn", "halt"} or not decision.message:
        return result

    label = "工具循环硬停止" if decision.action == "halt" else "工具循环警告"
    suffix = f"\n\n[{label}: {decision.code}; count={decision.count}; {decision.message}]"

    return (result or "") + suffix


# ═══════════════════════════════════════════════════════════════════════════════
# 全局单例（可选使用）
# ═══════════════════════════════════════════════════════════════════════════════

_default_controller: Optional[ToolCallGuardrailController] = None


def get_guardrail_controller(config: ToolGuardrailConfig | None = None) -> ToolCallGuardrailController:
    """获取全局防护控制器（单例模式）"""
    global _default_controller
    if _default_controller is None or config is not None:
        _default_controller = ToolCallGuardrailController(config)
    return _default_controller


__all__ = [
    "ToolGuardrailConfig",
    "ToolCallSignature",
    "ToolGuardrailDecision",
    "ToolCallGuardrailController",
    "IDEMPOTENT_TOOL_NAMES",
    "MUTATING_TOOL_NAMES",
    "get_guardrail_controller",
    "append_guardrail_warning",
]