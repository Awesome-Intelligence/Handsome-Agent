"""
技能生命周期管理器 (Skill Lifecycle Manager)

参考 Hermes Agent 的 Curator 实现
自动管理技能的生命周期状态转换:
- active → stale (30天不用)
- stale → archived (90天不用)
- 任何使用 → reactivate

主要职责:
- 定期检查技能的最后使用时间
- 自动更新技能状态
- 生成生命周期报告
"""

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
import asyncio
import logging

from .telemetry import SkillTelemetry, get_skill_telemetry, SKILL_STATE_ACTIVE, SKILL_STATE_STALE, SKILL_STATE_ARCHIVED


logger = logging.getLogger(__name__)

DEFAULT_STALE_AFTER_DAYS = 30
DEFAULT_ARCHIVE_AFTER_DAYS = 90


@dataclass
class LifecycleTransition:
    """生命周期转换记录"""
    skill_id: str
    from_state: str
    to_state: str
    reason: str
    timestamp: str


@dataclass
class LifecycleReport:
    """生命周期报告"""
    checked_count: int
    marked_stale: int
    archived: int
    reactivated: int
    transitions: List[LifecycleTransition]
    timestamp: str


class SkillLifecycleManager:
    """
    技能生命周期管理器

    负责:
    - 自动状态转换 (active → stale → archived)
    - 定期检查技能使用状态
    - 生成生命周期转换报告
    """

    def __init__(
        self,
        telemetry: Optional[SkillTelemetry] = None,
        stale_after_days: int = DEFAULT_STALE_AFTER_DAYS,
        archive_after_days: int = DEFAULT_ARCHIVE_AFTER_DAYS,
        check_interval_seconds: int = 3600,
    ):
        self.telemetry = telemetry or get_skill_telemetry()
        self.stale_after_days = stale_after_days
        self.archive_after_days = archive_after_days
        self.check_interval_seconds = check_interval_seconds

        self._running = False
        self._check_task: Optional[asyncio.Task] = None
        self._callbacks: List[Callable[[LifecycleReport], None]] = []

    def add_callback(self, callback: Callable[[LifecycleReport], None]) -> None:
        """
        添加生命周期变更回调

        Args:
            callback: 回调函数,接收 LifecycleReport
        """
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[LifecycleReport], None]) -> bool:
        """移除回调"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
            return True
        return False

    def _notify_callbacks(self, report: LifecycleReport) -> None:
        """通知所有回调"""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(report))
                else:
                    callback(report)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def apply_automatic_transitions(self, now: Optional[datetime] = None) -> LifecycleReport:
        """
        应用自动状态转换

        检查所有 agent 创建的技能,根据最后活动时间更新状态:
        1. active → stale: 超过 stale_after_days 未使用
        2. stale → archived: 超过 archive_after_days 未使用
        3. stale → active: 被重新使用

        Args:
            now: 可选的当前时间

        Returns:
            LifecycleReport: 包含转换详情
        """
        if now is None:
            now = self._now()

        stale_cutoff = now - timedelta(days=self.stale_after_days)
        archive_cutoff = now - timedelta(days=self.archive_after_days)

        transitions: List[LifecycleTransition] = []
        marked_stale = 0
        archived = 0
        reactivated = 0

        agent_skills = self.telemetry.get_agent_created_skills()
        checked_count = len(agent_skills)

        for record in agent_skills:
            skill_id = record.skill_id

            if record.pinned:
                logger.debug(f"Skipping pinned skill: {skill_id}")
                continue

            current_state = record.state

            latest_activity = self.telemetry.get_latest_activity(skill_id)
            if latest_activity is None:
                created_at = self.telemetry._parse_iso(record.created_at)
                if created_at:
                    latest_activity = created_at

            if latest_activity and latest_activity.tzinfo is None:
                latest_activity = latest_activity.replace(tzinfo=timezone.utc)

            anchor = latest_activity or now

            if anchor <= archive_cutoff and current_state != SKILL_STATE_ARCHIVED:
                if self.telemetry.set_state(skill_id, SKILL_STATE_ARCHIVED):
                    archived += 1
                    transitions.append(LifecycleTransition(
                        skill_id=skill_id,
                        from_state=current_state,
                        to_state=SKILL_STATE_ARCHIVED,
                        reason=f"未使用超过 {self.archive_after_days} 天",
                        timestamp=now.isoformat(),
                    ))
                    logger.info(f"Archived skill: {skill_id}")

            elif anchor <= stale_cutoff and current_state == SKILL_STATE_ACTIVE:
                if self.telemetry.set_state(skill_id, SKILL_STATE_STALE):
                    marked_stale += 1
                    transitions.append(LifecycleTransition(
                        skill_id=skill_id,
                        from_state=current_state,
                        to_state=SKILL_STATE_STALE,
                        reason=f"未使用超过 {self.stale_after_days} 天",
                        timestamp=now.isoformat(),
                    ))
                    logger.info(f"Marked skill as stale: {skill_id}")

            elif anchor > stale_cutoff and current_state == SKILL_STATE_STALE:
                if self.telemetry.set_state(skill_id, SKILL_STATE_ACTIVE):
                    reactivated += 1
                    transitions.append(LifecycleTransition(
                        skill_id=skill_id,
                        from_state=current_state,
                        to_state=SKILL_STATE_ACTIVE,
                        reason="技能重新被使用",
                        timestamp=now.isoformat(),
                    ))
                    logger.info(f"Reactivated skill: {skill_id}")

        report = LifecycleReport(
            checked_count=checked_count,
            marked_stale=marked_stale,
            archived=archived,
            reactivated=reactivated,
            transitions=transitions,
            timestamp=now.isoformat(),
        )

        if transitions:
            self._notify_callbacks(report)

        return report

    async def start_periodic_checks(self) -> None:
        """
        启动定期检查

        在后台运行,每 check_interval_seconds 秒检查一次
        """
        if self._running:
            logger.warning("Lifecycle manager already running")
            return

        self._running = True
        self._check_task = asyncio.create_task(self._periodic_check())
        logger.info(f"Started lifecycle periodic checks (interval: {self.check_interval_seconds}s)")

    async def stop_periodic_checks(self) -> None:
        """停止定期检查"""
        self._running = False
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
            self._check_task = None
        logger.info("Stopped lifecycle periodic checks")

    async def _periodic_check(self) -> None:
        """定期检查协程"""
        while self._running:
            try:
                await asyncio.sleep(self.check_interval_seconds)
                if self._running:
                    self.apply_automatic_transitions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in lifecycle check: {e}", exc_info=True)

    def get_lifecycle_summary(self) -> Dict[str, Any]:
        """
        获取生命周期摘要

        Returns:
            包含各状态技能数量的字典
        """
        telemetry = self.telemetry

        active_skills = telemetry.get_active_skills()
        stale_skills = telemetry.get_stale_skills()
        archived_skills = telemetry.get_archived_skills()
        agent_created = telemetry.get_agent_created_skills()

        return {
            "total_agent_created": len(agent_created),
            "active": len(active_skills),
            "stale": len(stale_skills),
            "archived": len(archived_skills),
            "stale_threshold_days": self.stale_after_days,
            "archive_threshold_days": self.archive_after_days,
            "active_skills": [
                {
                    "name": s.skill_id,
                    "last_used_at": s.last_used_at,
                    "activity_count": telemetry.get_activity_count(s.skill_id),
                }
                for s in sorted(active_skills, key=lambda x: x.last_used_at or "", reverse=True)[:10]
            ],
            "stale_skills": [
                {
                    "name": s.skill_id,
                    "last_used_at": s.last_used_at,
                    "days_since_use": self._days_since(s.last_used_at),
                }
                for s in stale_skills
            ],
            "archived_skills": [
                {
                    "name": s.skill_id,
                    "last_used_at": s.last_used_at,
                }
                for s in archived_skills
            ],
        }

    def _days_since(self, timestamp: Optional[str]) -> Optional[float]:
        """计算距离指定时间的天数"""
        if not timestamp:
            return None
        dt = self.telemetry._parse_iso(timestamp)
        if not dt:
            return None
        delta = self._now() - dt
        return delta.total_seconds() / 86400

    def archive_skill(self, skill_id: str) -> bool:
        """
        手动归档技能

        Args:
            skill_id: 技能 ID

        Returns:
            是否成功
        """
        return self.telemetry.archive_skill(skill_id)

    def restore_skill(self, skill_id: str) -> bool:
        """
        手动恢复技能

        Args:
            skill_id: 技能 ID

        Returns:
            是否成功
        """
        return self.telemetry.restore_skill(skill_id)

    def mark_skill_stale(self, skill_id: str) -> bool:
        """
        手动标记技能为过期

        Args:
            skill_id: 技能 ID

        Returns:
            是否成功
        """
        return self.telemetry.set_state(skill_id, SKILL_STATE_STALE)

    def mark_skill_active(self, skill_id: str) -> bool:
        """
        手动标记技能为活跃

        Args:
            skill_id: 技能 ID

        Returns:
            是否成功
        """
        return self.telemetry.set_state(skill_id, SKILL_STATE_ACTIVE)

    def pin_skill(self, skill_id: str) -> bool:
        """
        固定技能 (防止自动状态转换)

        Args:
            skill_id: 技能 ID

        Returns:
            是否成功
        """
        return self.telemetry.set_pinned(skill_id, True)

    def unpin_skill(self, skill_id: str) -> bool:
        """
        取消固定技能

        Args:
            skill_id: 技能 ID

        Returns:
            是否成功
        """
        return self.telemetry.set_pinned(skill_id, False)


_global_lifecycle_manager: Optional[SkillLifecycleManager] = None


def get_lifecycle_manager() -> SkillLifecycleManager:
    """获取全局生命周期管理器实例"""
    global _global_lifecycle_manager
    if _global_lifecycle_manager is None:
        _global_lifecycle_manager = SkillLifecycleManager()
    return _global_lifecycle_manager
