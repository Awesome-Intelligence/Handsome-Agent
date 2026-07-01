#!/usr/bin/env python3
# 🧠 Decision - 🔬 Curator - 自我进化核心

"""
Curator - Self-Evolution Core

Trajectory Evaluation → Skill Synthesis → Auto-Learning

功能：
1. 轨迹评估和技能合成（核心功能）
2. 后台定期运行机制
3. 空闲触发审查
4. 技能生命周期集成
5. 使用追踪集成

整合自原 curator.py 和 enhanced_curator.py。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable, TYPE_CHECKING
from datetime import datetime, timezone
import asyncio
import json

from common.logging_manager import get_decision_logger
from .types import EvaluationResult, EvaluationReport, EvaluationStep, SynthesizedSkill, TrajectoryStep

if TYPE_CHECKING:
    from pathlib import Path


logger = get_decision_logger("Curator")


# 默认配置常量
DEFAULT_INTERVAL_HOURS = 24 * 7
DEFAULT_MIN_IDLE_HOURS = 2


class CuratorState:
    """Curator 运行状态"""

    def __init__(self, state_file: Optional["Path"] = None):
        if state_file is None:
            try:
                from common.config import get_data_dir
                state_file = get_data_dir() / "skills" / ".curator_state"
            except Exception:
                state_file = None

        self.state_file = state_file
        self._load()

    def _load(self) -> None:
        """从磁盘加载状态"""
        if self.state_file is None or not self.state_file.exists():
            self._reset()
            return

        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
            self.last_run_at = data.get("last_run_at")
            self.last_run_duration_seconds = data.get("last_run_duration_seconds")
            self.last_run_summary = data.get("last_run_summary")
            self.paused = data.get("paused", False)
            self.run_count = data.get("run_count", 0)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load curator state: {e}")
            self._reset()

    def _reset(self) -> None:
        """重置状态"""
        self.last_run_at = None
        self.last_run_duration_seconds = None
        self.last_run_summary = None
        self.paused = False
        self.run_count = 0

    def save(self) -> None:
        """保存状态到磁盘"""
        if self.state_file is None:
            return

        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "last_run_at": self.last_run_at,
                "last_run_duration_seconds": self.last_run_duration_seconds,
                "last_run_summary": self.last_run_summary,
                "paused": self.paused,
                "run_count": self.run_count,
            }
            self.state_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError as e:
            logger.warning(f"Failed to save curator state: {e}")

    def update_run(self, duration: float, summary: str) -> None:
        """更新运行记录"""
        self.last_run_at = datetime.now(timezone.utc).isoformat()
        self.last_run_duration_seconds = duration
        self.last_run_summary = summary
        self.run_count += 1
        self.save()

    def set_paused(self, paused: bool) -> None:
        """设置暂停状态"""
        self.paused = paused
        self.save()

    def should_run(self, interval_hours: int = DEFAULT_INTERVAL_HOURS) -> bool:
        """检查是否应该运行"""
        if self.paused:
            return False

        if self.last_run_at is None:
            return False

        try:
            last_run = datetime.fromisoformat(self.last_run_at)
            if last_run.tzinfo is None:
                last_run = last_run.replace(tzinfo=timezone.utc)

            elapsed = datetime.now(timezone.utc) - last_run
            return elapsed.total_seconds() >= interval_hours * 3600
        except (ValueError, TypeError):
            return False


class Curator:
    """
    Curator - 自我进化核心

    功能:
    1. 轨迹评估和技能合成（核心功能）
    2. 后台定期运行机制
    3. 空闲触发审查
    4. 技能生命周期集成（可选）
    5. 使用追踪集成（可选）

    使用方式：
    ```python
    # 简单使用
    curator = Curator()
    result = await curator.process_trajectory(trajectory)

    # 增强使用（带定期审查）
    curator = Curator(
        skill_writer=writer,
        enable_auto_learn=True,
        interval_hours=24,
    )
    await curator.start_periodic_review()
    ```
    """

    def __init__(
        self,
        skill_writer: Optional[Any] = None,
        enable_auto_learn: bool = True,
        min_confidence_threshold: float = 0.7,
        interval_hours: int = DEFAULT_INTERVAL_HOURS,
        min_idle_hours: float = DEFAULT_MIN_IDLE_HOURS,
        curator_state: Optional[CuratorState] = None,
    ):
        """
        Args:
            skill_writer: 技能写入器（用于持久化技能）
            enable_auto_learn: 是否启用自动学习
            min_confidence_threshold: 最小置信度阈值
            interval_hours: 定期审查间隔（小时）
            min_idle_hours: 空闲触发最小空闲时间（小时）
            curator_state: 状态持久化器
        """
        self.skill_writer = skill_writer
        self.enable_auto_learn = enable_auto_learn
        self.min_confidence_threshold = min_confidence_threshold
        self.interval_hours = interval_hours
        self.min_idle_hours = min_idle_hours

        self._learned_skills: Dict[str, SynthesizedSkill] = {}
        self._evaluation_callbacks: List[Callable] = []
        self._learning_enabled = True

        self._state = curator_state or CuratorState()
        self._running = False
        self._review_task: Optional[asyncio.Task] = None

        self._telemetry = None

    @property
    def telemetry(self):
        """Lazy load telemetry"""
        if self._telemetry is None:
            try:
                from agent.skill_usage_tracker import get_skill_telemetry
                self._telemetry = get_skill_telemetry()
            except Exception as e:
                logger.debug(f"Failed to get skill telemetry: {e}")
        return self._telemetry

    def add_evaluation_callback(self, callback: Callable) -> None:
        """添加评估回调"""
        self._evaluation_callbacks.append(callback)

    async def process_trajectory(self, trajectory_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理轨迹数据（核心功能）

        职责说明：
        - 仅负责处理和分析轨迹数据
        - 不涉及存储逻辑，存储由 TrajectoryManager 负责

        支持的数据格式：
        - Trajectory 对象的 to_hermes_format() 返回格式
        - 包含 messages 或 conversations 字段的字典

        处理流程：
        1. 评估轨迹
        2. 触发回调
        3. 合成技能（仅成功轨迹）
        4. 自动学习（如启用）

        Args:
            trajectory_data: 轨迹数据字典，包含：
                - messages/conversations: 消息列表
                - trajectory_id: 轨迹 ID
                - 其他元数据

        Returns:
            Dict containing:
                - evaluation: EvaluationReport
                - skills: List[SynthesizedSkill]
        """
        logger.debug(f"Processing trajectory: {trajectory_data.get('trajectory_id', 'unknown')}")

        report = await self.evaluate(trajectory_data)
        skills: List[SynthesizedSkill] = []

        for callback in self._evaluation_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(report)
                else:
                    callback(report)
            except Exception as e:
                logger.error(f"Callback error: {e}")

        if report.overall_result == EvaluationResult.SUCCESS:
            skill = await self.synthesize_skill(trajectory_data, report)
            if skill:
                skills.append(skill)
                # 自动学习（如启用）
                if self.enable_auto_learn:
                    await self.learn_skill(skill)

        return {"evaluation": report, "skills": skills}

    async def evaluate(self, trajectory: Dict[str, Any]) -> EvaluationReport:
        """
        评估轨迹 - 简化版（纯筛选，无 LLM）

        筛选逻辑（参考 Hermes）：
        1. 检查是否有工具调用
        2. 检查是否有错误关键词
        3. 计算简单的成功率
        """
        # 获取消息列表（支持多种格式）
        messages = trajectory.get("messages", [])
        if not messages:
            messages = trajectory.get("conversations", [])

        # 统计工具调用和错误
        tool_calls = 0
        tool_responses = 0
        errors = 0
        steps = []

        for i, msg in enumerate(messages):
            role = msg.get("from", msg.get("role", ""))
            content = msg.get("value", msg.get("content", ""))

            # 检查工具调用
            if "<tool_call>" in content or "tool_call" in str(msg):
                tool_calls += 1
                steps.append(TrajectoryStep(
                    step_id=i,
                    thought="",
                    action="tool_call",
                    observation="",
                    result="tool executed",
                    success=True,
                ))

            # 检查工具响应
            if role == "tool" or "<tool_response>" in content:
                tool_responses += 1

                # 检查错误关键词
                error_indicators = ["error", "failed", "exception", "错误", "失败"]
                has_error = any(indicator in content.lower() for indicator in error_indicators)

                if has_error:
                    errors += 1
                    steps.append(TrajectoryStep(
                        step_id=i,
                        thought="",
                        action="",
                        observation=content[:100],
                        result=content,
                        success=False,
                    ))
                else:
                    steps.append(TrajectoryStep(
                        step_id=i,
                        thought="",
                        action="",
                        observation=content[:100],
                        result="success",
                        success=True,
                    ))

        # 计算成功率
        total_tool_responses = tool_responses if tool_responses > 0 else 1
        success_count = total_tool_responses - errors
        success_rate = max(0.0, success_count / total_tool_responses)

        # 确定整体结果（基于 Hermes 筛选标准）
        if success_rate == 1.0 and tool_calls > 0:
            overall = EvaluationResult.SUCCESS
        elif success_rate >= 0.5 and tool_calls > 0:
            overall = EvaluationResult.PARTIAL_SUCCESS
        elif tool_calls == 0:
            overall = EvaluationResult.UNKNOWN
        else:
            overall = EvaluationResult.FAILURE

        # 生成建议（简化版）
        suggestions = self._generate_suggestions(steps, overall, tool_calls)

        return EvaluationReport(
            trajectory_id=trajectory.get("trajectory_id", "unknown"),
            overall_result=overall,
            success_rate=success_rate,
            steps=steps,
            suggestions=suggestions,
            metrics={
                "total_tool_calls": tool_calls,
                "total_tool_responses": tool_responses,
                "errors": errors,
                "success_rate": success_rate,
            }
        )

    def _generate_suggestions(self, steps: List[TrajectoryStep], result: EvaluationResult,
                              tool_calls: int = 0) -> List[str]:
        """生成改进建议（简化版）"""
        suggestions = []

        # 基于结果类型生成建议
        if result == EvaluationResult.FAILURE:
            suggestions.append("执行失败，检查工具参数和执行逻辑")
        elif result == EvaluationResult.PARTIAL_SUCCESS:
            suggestions.append("部分成功，建议查看详细日志")

        # 基于步骤统计
        failed_steps = [s for s in steps if not s.success]
        if failed_steps:
            suggestions.append(f"{len(failed_steps)} 个步骤执行失败")

        # 基于工具调用数
        if tool_calls == 0:
            suggestions.append("无工具调用，可能只是简单对话")
        elif len(steps) > 20:
            suggestions.append("轨迹较长，可能存在优化空间")

        return suggestions

    async def synthesize_skill(
        self,
        trajectory: Dict[str, Any],
        report: EvaluationReport
    ) -> Optional[SynthesizedSkill]:
        """
        合成技能

        从成功轨迹中提取可复用的技能
        """
        # 检查是否适合合成
        if not self._is_candidate_for_synthesis(trajectory):
            return None

        # 检查置信度
        if report.success_rate < self.min_confidence_threshold:
            return None

        # 提取信息
        name = self._generate_skill_name(trajectory)
        description = self._generate_skill_description(trajectory, report)
        trigger_patterns = self._extract_trigger_patterns(trajectory)
        action_template = self._generate_action_template(trajectory)

        skill = SynthesizedSkill(
            name=name,
            description=description,
            trigger_patterns=trigger_patterns,
            action_template=action_template,
            confidence=report.success_rate,
            source_trajectory=trajectory.get("trajectory_id", ""),
        )

        logger.info(f"Synthesized new skill: {skill.name}")
        self._learned_skills[skill.name] = skill

        return skill

    def _is_candidate_for_synthesis(self, trajectory: Dict[str, Any]) -> bool:
        """检查轨迹是否适合合成技能"""
        steps = trajectory.get("steps", [])

        # 需要有一定数量的步骤
        if len(steps) < 3:
            return False

        # 需要有工具调用
        has_action = any(s.get("type") == "action" for s in steps)
        if not has_action:
            return False

        return True

    def _generate_skill_name(self, trajectory: Dict[str, Any]) -> str:
        """生成技能名称"""
        user_input = trajectory.get("user_input", "")
        words = user_input.split()[:3]
        return f"auto_{'_'.join(words)}"

    def _generate_skill_description(self, trajectory: Dict[str, Any], report: EvaluationReport) -> str:
        """生成技能描述"""
        user_input = trajectory.get("user_input", "")
        actions = set()

        for step in trajectory.get("steps", []):
            if step.get("type") == "action":
                actions.add(step.get("data", {}).get("tool_name", ""))

        return f"自动合成的技能，用于: {user_input[:50]}... (使用工具: {', '.join(actions)})"

    def _extract_trigger_patterns(self, trajectory: Dict[str, Any]) -> List[str]:
        """提取触发模式"""
        patterns = []
        user_input = trajectory.get("user_input", "").lower()

        # 提取关键词
        words = user_input.split()
        patterns.extend([w for w in words if len(w) > 2])

        return list(set(patterns))[:10]

    def _generate_action_template(self, trajectory: Dict[str, Any]) -> str:
        """生成动作模板"""
        actions = []

        for step in trajectory.get("steps", []):
            if step.get("type") == "action":
                tool_name = step.get("data", {}).get("tool_name", "")
                params = step.get("data", {}).get("parameters", {})
                actions.append(f"{tool_name}: {params}")

        return "\n".join(actions)

    async def learn_skill(self, skill: SynthesizedSkill) -> bool:
        """学习技能（持久化到磁盘）"""
        if not self.enable_auto_learn:
            logger.debug("Auto-learn disabled, skipping")
            return False

        if not self.skill_writer:
            logger.debug("No skill writer configured, skill not persisted")
            return False

        try:
            await self.skill_writer.write(skill)
            logger.info(f"Learned new skill: {skill.name}")

            if self.telemetry:
                self.telemetry.create_skill_record(
                    skill_id=skill.name,
                    created_by="curator",
                    tags=["auto-generated"],
                )

            return True
        except Exception as e:
            logger.error(f"Failed to learn skill: {e}")
            return False

    async def learn_from_feedback(self, trajectory_id: str, feedback: str) -> Optional[SynthesizedSkill]:
        """从用户反馈学习

        由于 TrajectoryRecorder 已删除，此方法仅记录反馈日志。
        如需从反馈学习，请使用 TrajectoryManager 加载轨迹后调用 process_trajectory。
        """
        if feedback.lower() in ["good", "success", "好", "成功"]:
            logger.info(f"Received positive feedback for trajectory {trajectory_id}")
        else:
            logger.info(f"Received feedback for trajectory {trajectory_id}: {feedback}")

        return None

    def get_learned_skills(self) -> List[SynthesizedSkill]:
        """Get learned skills"""
        return list(self._learned_skills.values())

    def get_skill_by_name(self, name: str) -> Optional[SynthesizedSkill]:
        """Get skill by name"""
        return self._learned_skills.get(name)

    def enable_learning(self) -> None:
        """Enable learning"""
        self._learning_enabled = True
        logger.info("Learning enabled")

    def disable_learning(self) -> None:
        """Disable learning"""
        self._learning_enabled = False
        logger.info("Learning disabled")

    # =========================================================================
    # 定期审查功能
    # =========================================================================

    async def start_periodic_review(self) -> None:
        """启动定期审查"""
        if self._running:
            logger.warning("Curator already running")
            return

        self._running = True
        self._review_task = asyncio.create_task(self._periodic_review_loop())
        logger.info(f"Started curator periodic review (interval: {self.interval_hours}h)")

    async def stop_periodic_review(self) -> None:
        """停止定期审查"""
        self._running = False
        if self._review_task:
            self._review_task.cancel()
            try:
                await self._review_task
            except asyncio.CancelledError:
                pass
            self._review_task = None
        logger.info("Stopped curator periodic review")

    async def _periodic_review_loop(self) -> None:
        """定期审查循环"""
        interval_seconds = self.interval_hours * 3600

        while self._running:
            try:
                await asyncio.sleep(interval_seconds)

                if self._running and self._state.should_run(self.interval_hours):
                    await self.run_review()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in curator periodic review: {e}", exc_info=True)

    async def run_review(
        self,
        dry_run: bool = False,
        on_summary: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """
        运行一次完整审查

        Args:
            dry_run: 是否只生成报告不执行变更
            on_summary: 审查完成后的回调

        Returns:
            审查结果字典
        """
        start_time = datetime.now(timezone.utc)
        summary_parts = []

        # 运行 Curator 清理
        if not dry_run:
            try:
                from agent.skill_curator import run_curator, get_curator_config
                curator_config = get_curator_config()
                curator_config.dry_run = dry_run
                curator_report = run_curator(curator_config)

                if curator_report.stats.get("marked_stale", 0) > 0:
                    summary_parts.append(f"{curator_report.stats['marked_stale']} marked stale")
                if curator_report.stats.get("archived", 0) > 0:
                    summary_parts.append(f"{curator_report.stats['archived']} archived")
                if curator_report.stats.get("restored", 0) > 0:
                    summary_parts.append(f"{curator_report.stats['restored']} reactivated")
            except Exception as e:
                logger.debug(f"Failed to run curator: {e}")

        telemetry_summary = None
        if self.telemetry:
            telemetry_summary = self.telemetry.get_usage_summary()
            summary_parts.append(f"{telemetry_summary['total_skills']} total skills")

        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        final_summary = "; ".join(summary_parts) if summary_parts else "no changes"

        if dry_run:
            final_summary = f"[DRY RUN] {final_summary}"

        self._state.update_run(elapsed, final_summary)

        if on_summary:
            try:
                on_summary(final_summary)
            except Exception as e:
                logger.error(f"Callback error: {e}")

        return {
            "started_at": start_time.isoformat(),
            "duration_seconds": elapsed,
            "summary": final_summary,
            "dry_run": dry_run,
            "lifecycle_report": lifecycle_report,
            "telemetry_summary": telemetry_summary,
        }

    async def maybe_run(
        self,
        idle_for_seconds: Optional[float] = None,
        on_summary: Optional[Callable[[str], None]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        条件运行审查

        检查是否满足运行条件:
        1. 距离上次运行超过 interval_hours
        2. 空闲时间超过 min_idle_hours

        Args:
            idle_for_seconds: 空闲秒数
            on_summary: 回调函数

        Returns:
            如果运行了,返回结果; 否则返回 None
        """
        if self._state.paused:
            return None

        if idle_for_seconds is not None:
            min_idle_seconds = self.min_idle_hours * 3600
            if idle_for_seconds < min_idle_seconds:
                logger.debug(f"Not running curator: idle {idle_for_seconds:.0f}s < {min_idle_seconds:.0f}s")
                return None

        if not self._state.should_run(self.interval_hours):
            return None

        return await self.run_review(on_summary=on_summary)

    def pause(self) -> None:
        """暂停 curator"""
        self._state.set_paused(True)
        logger.info("Curator paused")

    def resume(self) -> None:
        """恢复 curator"""
        self._state.set_paused(False)
        logger.info("Curator resumed")

    def get_status(self) -> Dict[str, Any]:
        """获取 curator 状态"""
        return {
            "running": self._running,
            "paused": self._state.paused,
            "interval_hours": self.interval_hours,
            "min_idle_hours": self.min_idle_hours,
            "last_run_at": self._state.last_run_at,
            "last_run_duration_seconds": self._state.last_run_duration_seconds,
            "last_run_summary": self._state.last_run_summary,
            "run_count": self._state.run_count,
            "learned_skills_count": len(self._learned_skills),
        }


# 全局实例
_global_curator: Optional[Curator] = None


def get_curator() -> Curator:
    """获取全局 Curator 实例"""
    global _global_curator
    if _global_curator is None:
        _global_curator = Curator()
    return _global_curator


__all__ = [
    "Curator",
    "CuratorState",
    "EvaluationResult",
    "EvaluationReport",
    "EvaluationStep",
    "SynthesizedSkill",
    "TrajectoryStep",  # 向后兼容别名
    "get_curator",
]
