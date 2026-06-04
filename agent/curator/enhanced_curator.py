"""
Enhanced Curator - Self-Evolution Core

Reference Hermes Agent's Curator implementation
Integrates:
- Skill usage tracking (SkillTelemetry)
- Skill lifecycle management (SkillLifecycleManager)
- Trajectory evaluation and skill synthesis
- Background periodic execution mechanism
- Idle-triggered review
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timezone
from enum import Enum
import asyncio
import json
from pathlib import Path
from common.logging_manager import get_decision_logger


logger = get_decision_logger(__name__)


class EvaluationResult(str, Enum):
    """评估结果"""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class TrajectoryStep:
    """轨迹步骤"""
    step_id: int
    thought: str
    action: str
    observation: str
    result: str
    success: bool


@dataclass
class EvaluationReport:
    """评估报告"""
    trajectory_id: str
    overall_result: EvaluationResult
    success_rate: float
    steps: List[TrajectoryStep]
    suggestions: List[str]
    metrics: Dict[str, Any]
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class SynthesizedSkill:
    """合成的技能"""
    name: str
    description: str
    trigger_patterns: List[str]
    action_template: str
    confidence: float
    source_trajectory: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


DEFAULT_INTERVAL_HOURS = 24 * 7
DEFAULT_MIN_IDLE_HOURS = 2


class CuratorState:
    """Curator 运行状态"""

    def __init__(self, state_file: Optional[Path] = None):
        if state_file is None:
            from common.config import get_data_dir
            state_file = get_data_dir() / "skills" / ".curator_state"

        self.state_file = state_file
        self._load()

    def _load(self) -> None:
        """从磁盘加载状态"""
        if not self.state_file.exists():
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


class EnhancedCurator:
    """
    增强版 Curator

    功能:
    1. 轨迹评估和技能合成 (从原 Curator 继承)
    2. 后台定期运行机制
    3. 空闲触发审查
    4. 技能生命周期集成
    5. 使用追踪集成
    """

    def __init__(
        self,
        trajectory_recorder: Optional[Any] = None,
        skill_writer: Optional[Any] = None,
        enable_auto_learn: bool = True,
        min_confidence_threshold: float = 0.7,
        interval_hours: int = DEFAULT_INTERVAL_HOURS,
        min_idle_hours: float = DEFAULT_MIN_IDLE_HOURS,
        curator_state: Optional[CuratorState] = None,
    ):
        self.trajectory_recorder = trajectory_recorder
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

        self._lifecycle_manager = None
        self._telemetry = None

    @property
    def telemetry(self):
        """Lazy load telemetry"""
        if self._telemetry is None:
            try:
                from skills import get_skill_telemetry
                self._telemetry = get_skill_telemetry()
            except Exception as e:
                logger.warning(f"Failed to get skill telemetry: {e}")
        return self._telemetry

    @property
    def lifecycle_manager(self):
        """Lazy load lifecycle manager"""
        if self._lifecycle_manager is None:
            try:
                from skills import get_lifecycle_manager
                self._lifecycle_manager = get_lifecycle_manager()
            except Exception as e:
                logger.warning(f"Failed to get lifecycle manager: {e}")
        return self._lifecycle_manager

    def add_evaluation_callback(self, callback: Callable) -> None:
        """Add evaluation callback"""
        self._evaluation_callbacks.append(callback)

    async def process_trajectory(self, trajectory: Dict[str, Any]) -> Optional[SynthesizedSkill]:
        """
        Process trajectory - main entry
        """
        logger.debug(f"Processing trajectory: {trajectory.get('trajectory_id', 'unknown')}")

        report = await self.evaluate(trajectory)

        for callback in self._evaluation_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(report)
                else:
                    callback(report)
            except Exception as e:
                logger.error(f"Callback error: {e}")

        if report.overall_result == EvaluationResult.SUCCESS:
            skill = await self.synthesize_skill(trajectory, report)
            if skill:
                if self.enable_auto_learn:
                    await self.learn_skill(skill)
                return skill

        return None

    async def evaluate(self, trajectory: Dict[str, Any]) -> EvaluationReport:
        """Evaluate trajectory"""
        steps = []
        success_count = 0
        total_steps = 0

        for step in trajectory.get("steps", []):
            step_type = step.get("type")

            if step_type == "thought":
                thought = step.get("data", {}).get("reasoning", "")
                action = ""
                observation = ""
                result = ""
                success = True
            elif step_type == "action":
                thought = ""
                action = step.get("data", {}).get("tool_name", "")
                observation = ""
                result = ""
                success = True
            elif step_type == "observation":
                thought = ""
                action = ""
                observation = step.get("data", {}).get("result", "")
                result = step.get("data", {}).get("result", "")
                success = step.get("data", {}).get("success", True)
            else:
                continue

            steps.append(TrajectoryStep(
                step_id=step.get("step_id", 0),
                thought=thought,
                action=action,
                observation=observation,
                result=result,
                success=success,
            ))

            if step_type == "observation":
                total_steps += 1
                if success:
                    success_count += 1

        success_rate = success_count / total_steps if total_steps > 0 else 0.0

        if success_rate == 1.0:
            overall = EvaluationResult.SUCCESS
        elif success_rate >= 0.5:
            overall = EvaluationResult.PARTIAL_SUCCESS
        elif total_steps == 0:
            overall = EvaluationResult.UNKNOWN
        else:
            overall = EvaluationResult.FAILURE

        suggestions = self._generate_suggestions(steps, overall)

        return EvaluationReport(
            trajectory_id=trajectory.get("trajectory_id", "unknown"),
            overall_result=overall,
            success_rate=success_rate,
            steps=steps,
            suggestions=suggestions,
            metrics={
                "total_steps": total_steps,
                "success_steps": success_count,
                "success_rate": success_rate,
            }
        )

    def _generate_suggestions(self, steps: List[TrajectoryStep], result: EvaluationResult) -> List[str]:
        """Generate improvement suggestions"""
        suggestions = []

        if result == EvaluationResult.FAILURE:
            suggestions.append("Execution failed, suggest checking tool parameters or execution logic")

        if result == EvaluationResult.PARTIAL_SUCCESS:
            suggestions.append("Partial success, some steps may have issues, suggest checking detailed logs")

        failed_steps = [s for s in steps if not s.success]
        if failed_steps:
            suggestions.append(f"{len(failed_steps)} steps failed to execute")

        if len(steps) > 10:
            suggestions.append("Trajectory is long, there may be room for optimization")

        return suggestions

    async def synthesize_skill(
        self,
        trajectory: Dict[str, Any],
        report: EvaluationReport
    ) -> Optional[SynthesizedSkill]:
        """合成技能"""
        if not self._is_candidate_for_synthesis(trajectory):
            return None

        if report.success_rate < self.min_confidence_threshold:
            return None

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

        if len(steps) < 3:
            return False

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
        """Learn skill"""
        if not self.enable_auto_learn:
            logger.info("Auto-learn disabled, skipping")
            return False

        if not self.skill_writer:
            logger.warning("No skill writer configured")
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
        """Learn from user feedback"""
        if not self.trajectory_recorder:
            return None

        trajectory = self.trajectory_recorder.load_trajectory(trajectory_id)
        if not trajectory:
            return None

        if feedback.lower() in ["good", "success", "好", "成功"]:
            await self.trajectory_recorder.mark_trajectory(trajectory_id, "success")
            return await self.process_trajectory(trajectory.to_dict())

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

    async def start_periodic_review(self) -> None:
        """Start periodic review"""
        if self._running:
            logger.warning("Curator already running")
            return

        self._running = True
        self._review_task = asyncio.create_task(self._periodic_review_loop())
        logger.info(f"Started curator periodic review (interval: {self.interval_hours}h)")

    async def stop_periodic_review(self) -> None:
        """Stop periodic review"""
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
        """Periodic review loop"""
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

        lifecycle_report = None
        if self.lifecycle_manager and not dry_run:
            lifecycle_report = self.lifecycle_manager.apply_automatic_transitions()

            if lifecycle_report:
                if lifecycle_report.marked_stale > 0:
                    summary_parts.append(f"{lifecycle_report.marked_stale} marked stale")
                if lifecycle_report.archived > 0:
                    summary_parts.append(f"{lifecycle_report.archived} archived")
                if lifecycle_report.reactivated > 0:
                    summary_parts.append(f"{lifecycle_report.reactivated} reactivated")

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
        """Pause curator"""
        self._state.set_paused(True)
        logger.info("Curator paused")

    def resume(self) -> None:
        """Resume curator"""
        self._state.set_paused(False)
        logger.info("Curator resumed")

    def get_status(self) -> Dict[str, Any]:
        """Get curator status"""
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


_global_curator: Optional[EnhancedCurator] = None


def get_curator() -> EnhancedCurator:
    """Get global Curator instance"""
    global _global_curator
    if _global_curator is None:
        _global_curator = EnhancedCurator()
    return _global_curator
