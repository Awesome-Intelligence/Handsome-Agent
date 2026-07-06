"""工具调用循环检测防护栏。

纯函数式的工具调用循环检测原语，不产生副作用：
- 追踪每轮工具调用观察
- 返回决策结果（允许/警告/阻止/停止）
- 运行时代码决定是否将决策转化为警告、合成工具结果或轮次停止

参考 Hermes 的 tool_guardrails.py 实现。
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

logger = logging.getLogger(__name__)


# ── 幂等工具（只读工具，不会产生副作用）─────────────────────────────

IDEMPOTENT_TOOL_NAMES = frozenset({
    # 文件操作（读）
    "read_file",
    "read_multiple_files",
    "search_files",
    "list_directory",
    "get_file_info",
    "glob_files",
    # Web 操作
    "web_search",
    "web_fetch",
    "web_screenshot",
    # 浏览器（读）
    "browser_snapshot",
    "browser_console",
    "browser_get_images",
    "browser_get_links",
    # 会话/记忆
    "session_search",
    "memory_search",
    # MCP 文件系统（读）
    "mcp_filesystem_read_file",
    "mcp_filesystem_read_text_file",
    "mcp_filesystem_read_multiple_files",
    "mcp_filesystem_list_directory",
    "mcp_filesystem_list_directory_with_sizes",
    "mcp_filesystem_directory_tree",
    "mcp_filesystem_get_file_info",
    "mcp_filesystem_search_files",
    # 代码分析
    "analyze_code",
    "explain_code",
    "get_code_structure",
})

# ── 变更工具（会产生副作用的工具）─────────────────────────────

MUTATING_TOOL_NAMES = frozenset({
    # 终端/代码执行
    "execute_terminal",
    "execute_code",
    "run_script",
    # 文件操作（写）
    "write_file",
    "patch",
    "edit_file",
    "create_file",
    "delete_file",
    # 任务管理
    "todo",
    "create_task",
    "update_task",
    "delete_task",
    # 记忆管理
    "memory",
    "add_memory",
    "delete_memory",
    # 技能管理
    "skill_manage",
    "install_skill",
    "uninstall_skill",
    # 浏览器（写）
    "browser_click",
    "browser_type",
    "browser_press",
    "browser_scroll",
    "browser_navigate",
    "browser_submit",
    # 消息发送
    "send_message",
    "send_email",
    # 定时任务
    "cronjob",
    "schedule_task",
    # 委托任务
    "delegate_task",
    "create_subagent",
    # 进程管理
    "process",
    "kill_process",
    "start_process",
})


@dataclass(frozen=True)
class ToolCallGuardrailConfig:
    """每轮工具调用循环检测阈值配置。

    警告默认启用但不会阻止工具执行。硬停止需要显式启用，
    这样交互式 CLI/TUI 会话可以先得到温和提示，除非用户在
    配置中启用了熔断机制。
    """

    warnings_enabled: bool = True
    hard_stop_enabled: bool = False

    # 精确失败（相同工具名 + 相同参数）
    exact_failure_warn_after: int = 2
    exact_failure_block_after: int = 5

    # 同工具失败（相同工具名，不同参数）
    same_tool_failure_warn_after: int = 3
    same_tool_failure_halt_after: int = 8

    # 幂等工具无进展（相同工具名 + 相同结果）
    no_progress_warn_after: int = 2
    no_progress_block_after: int = 5

    idempotent_tools: frozenset[str] = field(default_factory=lambda: IDEMPOTENT_TOOL_NAMES)
    mutating_tools: frozenset[str] = field(default_factory=lambda: MUTATING_TOOL_NAMES)

    @classmethod
    def from_mapping(cls, data: Optional[Mapping[str, Any]]) -> "ToolCallGuardrailConfig":
        """从配置字典构建设置。"""
        if not isinstance(data, Mapping):
            return cls()

        warn_after = data.get("warn_after") or {}
        hard_stop_after = data.get("hard_stop_after") or {}

        defaults = cls()
        return cls(
            warnings_enabled=_as_bool(data.get("warnings_enabled"), defaults.warnings_enabled),
            hard_stop_enabled=_as_bool(data.get("hard_stop_enabled"), defaults.hard_stop_enabled),
            exact_failure_warn_after=_positive_int(
                warn_after.get("exact_failure", data.get("exact_failure_warn_after")),
                defaults.exact_failure_warn_after,
            ),
            same_tool_failure_warn_after=_positive_int(
                warn_after.get("same_tool_failure", data.get("same_tool_failure_warn_after")),
                defaults.same_tool_failure_warn_after,
            ),
            no_progress_warn_after=_positive_int(
                warn_after.get("idempotent_no_progress", data.get("no_progress_warn_after")),
                defaults.no_progress_warn_after,
            ),
            exact_failure_block_after=_positive_int(
                hard_stop_after.get("exact_failure", data.get("exact_failure_block_after")),
                defaults.exact_failure_block_after,
            ),
            same_tool_failure_halt_after=_positive_int(
                hard_stop_after.get("same_tool_failure", data.get("same_tool_failure_halt_after")),
                defaults.same_tool_failure_halt_after,
            ),
            no_progress_block_after=_positive_int(
                hard_stop_after.get("idempotent_no_progress", data.get("no_progress_block_after")),
                defaults.no_progress_block_after,
            ),
        )


@dataclass(frozen=True)
class ToolCallSignature:
    """工具调用的稳定、不可逆标识（工具名 + 规范化参数哈希）。"""

    tool_name: str
    args_hash: str

    @classmethod
    def from_call(cls, tool_name: str, args: Optional[Mapping[str, Any]]) -> "ToolCallSignature":
        """从工具名和参数创建签名。"""
        canonical = canonical_tool_args(args or {})
        return cls(tool_name=tool_name, args_hash=_sha256(canonical))

    def to_metadata(self) -> dict[str, str]:
        """返回公开元数据（不含原始参数值）。"""
        return {"tool_name": self.tool_name, "args_hash": self.args_hash}


@dataclass(frozen=True)
class ToolGuardrailDecision:
    """工具调用防护栏返回的决策。"""

    action: str = "allow"  # allow | warn | block | halt
    code: str = "allow"
    message: str = ""
    tool_name: str = ""
    count: int = 0
    signature: Optional[ToolCallSignature] = None

    @property
    def allows_execution(self) -> bool:
        """是否允许执行。"""
        return self.action in {"allow", "warn"}

    @property
    def should_halt(self) -> bool:
        """是否应该停止。"""
        return self.action in {"block", "halt"}

    def to_metadata(self) -> dict[str, Any]:
        """转换为元数据字典。"""
        data: dict[str, Any] = {
            "action": self.action,
            "code": self.code,
            "message": self.message,
            "tool_name": self.tool_name,
            "count": self.count,
        }
        if self.signature is not None:
            data["signature"] = self.signature.to_metadata()
        return data


def canonical_tool_args(args: Mapping[str, Any]) -> str:
    """返回解析后工具参数的排序紧凑 JSON。"""
    if not isinstance(args, Mapping):
        raise TypeError(f"tool args must be a mapping, got {type(args).__name__}")
    return json.dumps(
        args,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def classify_tool_failure(tool_name: str, result: Optional[str]) -> tuple[bool, str]:
    """工具失败分类器（用于 caller 未传递 failed 参数时）。

    检测常见失败模式：
    - 终端命令返回非零 exit_code
    - 记忆存储已满
    - JSON 响应中包含 error/failed 字段
    """
    if result is None:
        return False, ""

    # 文件变更类工具：检查 success 字段
    data = _safe_json_loads(result)
    if isinstance(data, dict):
        # 检查通用成功标志
        if data.get("success") is False:
            error_msg = data.get("error", "")
            if "exceed" in error_msg.lower() and "limit" in error_msg.lower():
                return True, " [full]"
            return True, " [error]"

        # 终端命令检查 exit_code
        if tool_name in {"execute_terminal", "run_script"}:
            exit_code = data.get("exit_code")
            if exit_code is not None and exit_code != 0:
                return True, f" [exit {exit_code}]"

    # 纯文本检查
    lower = result[:500].lower()
    if '"error"' in lower or '"failed"' in lower or result.startswith("Error"):
        return True, " [error]"

    return False, ""


class ToolCallGuardrailController:
    """每轮工具调用循环检测控制器。"""

    def __init__(self, config: Optional[ToolCallGuardrailConfig] = None):
        self.config = config or ToolCallGuardrailConfig()
        self.reset_for_turn()

    def reset_for_turn(self) -> None:
        """重置本轮状态。"""
        self._exact_failure_counts: dict[ToolCallSignature, int] = {}
        self._same_tool_failure_counts: dict[str, int] = {}
        self._no_progress: dict[ToolCallSignature, tuple[str, int]] = {}
        self._halt_decision: Optional[ToolGuardrailDecision] = None

    @property
    def halt_decision(self) -> Optional[ToolGuardrailDecision]:
        """获取最终的停止决策（如果有）。"""
        return self._halt_decision

    def before_call(
        self,
        tool_name: str,
        args: Optional[Mapping[str, Any]],
    ) -> ToolGuardrailDecision:
        """在工具调用前检查是否应该阻止。"""
        signature = ToolCallSignature.from_call(tool_name, _coerce_args(args))

        if not self.config.hard_stop_enabled:
            return ToolGuardrailDecision(tool_name=tool_name, signature=signature)

        # 检查精确失败是否超过阈值
        exact_count = self._exact_failure_counts.get(signature, 0)
        if exact_count >= self.config.exact_failure_block_after:
            decision = ToolGuardrailDecision(
                action="block",
                code="repeated_exact_failure_block",
                message=(
                    f"已阻止 {tool_name}：相同工具调用已失败 {exact_count} 次。 "
                    "不要继续重试相同的参数，请改变策略或说明阻碍因素。"
                ),
                tool_name=tool_name,
                count=exact_count,
                signature=signature,
            )
            self._halt_decision = decision
            return decision

        # 检查幂等工具无进展是否超过阈值
        if self._is_idempotent(tool_name):
            record = self._no_progress.get(signature)
            if record is not None:
                _, repeat_count = record
                if repeat_count >= self.config.no_progress_block_after:
                    decision = ToolGuardrailDecision(
                        action="block",
                        code="idempotent_no_progress_block",
                        message=(
                            f"已阻止 {tool_name}：此只读调用已返回相同结果 {repeat_count} 次。 "
                            "请使用已提供的结果或尝试不同的查询，而不是继续重复调用。"
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
        args: Optional[Mapping[str, Any]],
        result: Optional[str],
        *,
        failed: Optional[bool] = None,
    ) -> ToolGuardrailDecision:
        """在工具调用后记录结果并返回决策。"""
        args = _coerce_args(args)
        signature = ToolCallSignature.from_call(tool_name, args)

        if failed is None:
            failed, _ = classify_tool_failure(tool_name, result)

        if failed:
            # 记录精确失败
            exact_count = self._exact_failure_counts.get(signature, 0) + 1
            self._exact_failure_counts[signature] = exact_count
            self._no_progress.pop(signature, None)

            # 记录同工具失败
            same_count = self._same_tool_failure_counts.get(tool_name, 0) + 1
            self._same_tool_failure_counts[tool_name] = same_count

            # 硬停止：同工具失败超过阈值
            if self.config.hard_stop_enabled and same_count >= self.config.same_tool_failure_halt_after:
                decision = ToolGuardrailDecision(
                    action="halt",
                    code="same_tool_failure_halt",
                    message=(
                        f"已停止 {tool_name}：此工具本轮已失败 {same_count} 次。 "
                        "不要继续重试相同的失败工具路径，请选择不同的方法。"
                    ),
                    tool_name=tool_name,
                    count=same_count,
                    signature=signature,
                )
                self._halt_decision = decision
                return decision

            # 警告：精确失败超过阈值
            if self.config.warnings_enabled and exact_count >= self.config.exact_failure_warn_after:
                return ToolGuardrailDecision(
                    action="warn",
                    code="repeated_exact_failure_warning",
                    message=(
                        f"{tool_name} 使用相同参数已失败 {exact_count} 次。 "
                        "这看起来像是一个循环；请检查错误并改变策略，"
                        "而不是继续重试相同的参数。"
                    ),
                    tool_name=tool_name,
                    count=exact_count,
                    signature=signature,
                )

            # 警告：同工具失败超过阈值
            if self.config.warnings_enabled and same_count >= self.config.same_tool_failure_warn_after:
                return ToolGuardrailDecision(
                    action="warn",
                    code="same_tool_failure_warning",
                    message=_tool_failure_recovery_hint(tool_name, same_count),
                    tool_name=tool_name,
                    count=same_count,
                    signature=signature,
                )

            return ToolGuardrailDecision(tool_name=tool_name, count=exact_count, signature=signature)

        # 成功：清除失败记录
        self._exact_failure_counts.pop(signature, None)
        self._same_tool_failure_counts.pop(tool_name, None)

        # 非幂等工具：清除无进展记录
        if not self._is_idempotent(tool_name):
            self._no_progress.pop(signature, None)
            return ToolGuardrailDecision(tool_name=tool_name, signature=signature)

        # 幂等工具：检查是否返回相同结果
        result_hash = _result_hash(result)
        previous = self._no_progress.get(signature)
        repeat_count = 1
        if previous is not None and previous[0] == result_hash:
            repeat_count = previous[1] + 1
        self._no_progress[signature] = (result_hash, repeat_count)

        # 警告：幂等工具无进展
        if self.config.warnings_enabled and repeat_count >= self.config.no_progress_warn_after:
            return ToolGuardrailDecision(
                action="warn",
                code="idempotent_no_progress_warning",
                message=(
                    f"{tool_name} 已返回相同结果 {repeat_count} 次。 "
                    "请使用已提供的结果或改变查询，而不是继续重复调用。"
                ),
                tool_name=tool_name,
                count=repeat_count,
                signature=signature,
            )

        return ToolGuardrailDecision(tool_name=tool_name, count=repeat_count, signature=signature)

    def _is_idempotent(self, tool_name: str) -> bool:
        """判断工具是否为幂等的。"""
        if tool_name in self.config.mutating_tools:
            return False
        return tool_name in self.config.idempotent_tools


def toolguard_synthetic_result(decision: ToolGuardrailDecision) -> str:
    """为阻止的工具调用构建合成结果。"""
    return json.dumps(
        {
            "error": decision.message,
            "guardrail": decision.to_metadata(),
        },
        ensure_ascii=False,
    )


def append_toolguard_guidance(result: str, decision: ToolGuardrailDecision) -> str:
    """向当前工具结果追加运行时指导。"""
    if decision.action not in {"warn", "halt"} or not decision.message:
        return result

    label = "工具循环硬停止" if decision.action == "halt" else "工具循环警告"
    suffix = f"\n\n[{label}: {decision.code}; count={decision.count}; {decision.message}]"
    return (result or "") + suffix


def _tool_failure_recovery_hint(tool_name: str, count: int) -> str:
    """工具失败恢复提示。"""
    common = (
        f"{tool_name} 本轮已失败 {count} 次。这看起来像是一个循环。"
        "不要切换到纯文本回复；继续使用工具，但在重试前先诊断问题。"
        "首先检查最新的错误/输出并验证你的假设。"
    )

    if tool_name in {"execute_terminal", "run_script"}:
        return common + (
            "对于终端失败，请先运行诊断命令如 `pwd && ls -la`，"
            "然后尝试绝对路径、更简单的命令、不同的工作目录，"
            "或使用其他工具如 read_file/write_file/patch。"
        )

    return common + (
        "尝试不同的参数、更窄的查询/路径、相关的绝对路径，"
        "或使用其他能取得进展的工具。如果障碍是外部因素，"
        "在一次诊断尝试后报告障碍，而不是重复相同的失败路径。"
    )


def _coerce_args(args: Optional[Mapping[str, Any]]) -> Mapping[str, Any]:
    """确保参数是 Mapping 类型。"""
    return args if isinstance(args, Mapping) else {}


def _result_hash(result: Optional[str]) -> str:
    """计算结果的规范化哈希。"""
    parsed = _safe_json_loads(result or "")
    if parsed is not None:
        try:
            canonical = json.dumps(
                parsed,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            )
        except TypeError:
            canonical = str(parsed)
    else:
        canonical = result or ""
    return _sha256(canonical)


def _safe_json_loads(text: str) -> Optional[Any]:
    """安全地解析 JSON，失败返回 None。"""
    if not text:
        return None
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


def _as_bool(value: Any, default: bool) -> bool:
    """将值转换为布尔值。"""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on", "enabled", "是", "启用"}:
            return True
        if lowered in {"0", "false", "no", "off", "disabled", "否", "禁用"}:
            return False
    return default


def _positive_int(value: Any, default: int) -> int:
    """将值转换为正整数。"""
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 1 else default


def _sha256(value: str) -> str:
    """计算字符串的 SHA256 哈希。"""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
