"""
技能使用追踪系统 (Skill Telemetry)

参考 Hermes Agent 的 skill_usage.py 实现
记录技能的使用、查看、修改等事件
用于支持 Curator 的生命周期管理和智能合并

使用 .skill_usage.json 侧边文件追踪,避免污染用户编写的 SKILL.md 内容
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
import logging
import tempfile
import os

logger = logging.getLogger(__name__)


SKILL_STATE_ACTIVE = "active"
SKILL_STATE_STALE = "stale"
SKILL_STATE_ARCHIVED = "archived"

VALID_STATES = {SKILL_STATE_ACTIVE, SKILL_STATE_STALE, SKILL_STATE_ARCHIVED}


@dataclass
class SkillUsageRecord:
    """技能使用记录"""
    skill_id: str
    created_by: str = "agent"
    agent_created: bool = False

    use_count: int = 0
    view_count: int = 0
    patch_count: int = 0

    last_used_at: Optional[str] = None
    last_viewed_at: Optional[str] = None
    last_patched_at: Optional[str] = None

    created_at: str = ""
    state: str = SKILL_STATE_ACTIVE
    pinned: bool = False

    version: str = "1.0.0"
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if not self.created_at:
            self.created_at = self._now_iso()

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()


class SkillTelemetry:
    """
    技能使用追踪器

    负责:
    - 记录技能使用事件 (use/view/patch)
    - 更新使用时间戳
    - 管理技能状态 (active/stale/archived)
    - 提供使用统计查询
    """

    def __init__(self, skills_dir: Optional[Path] = None):
        if skills_dir is None:
            from shared.config import get_data_dir
            self.skills_dir = get_data_dir() / "skills"
        else:
            self.skills_dir = Path(skills_dir)

        self.usage_file = self.skills_dir / ".skill_usage.json"
        self._cache: Dict[str, SkillUsageRecord] = {}
        self._lock_file = self.usage_file.with_suffix(".json.lock")

        self._load_usage()

    def _load_usage(self) -> None:
        """从磁盘加载使用记录"""
        if not self.usage_file.exists():
            self._cache = {}
            return

        try:
            with open(self.usage_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._cache = {
                    name: SkillUsageRecord(
                        skill_id=name,
                        created_by=record.get("created_by", "agent"),
                        agent_created=record.get("agent_created", False),
                        use_count=record.get("use_count", 0),
                        view_count=record.get("view_count", 0),
                        patch_count=record.get("patch_count", 0),
                        last_used_at=record.get("last_used_at"),
                        last_viewed_at=record.get("last_viewed_at"),
                        last_patched_at=record.get("last_patched_at"),
                        created_at=record.get("created_at", self._now_iso()),
                        state=record.get("state", SKILL_STATE_ACTIVE),
                        pinned=record.get("pinned", False),
                        version=record.get("version", "1.0.0"),
                        tags=record.get("tags", []),
                    )
                    for name, record in data.items()
                    if isinstance(record, dict)
                }
            logger.debug(f"Loaded {len(self._cache)} skill usage records")
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load skill usage file: {e}")
            self._cache = {}

    def _save_usage(self) -> None:
        """持久化使用记录到磁盘"""
        try:
            self.skills_dir.mkdir(parents=True, exist_ok=True)

            fd, tmp = tempfile.mkstemp(
                dir=str(self.skills_dir),
                prefix=".skill_usage_",
                suffix=".tmp"
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    data = {
                        name: {
                            "created_by": record.created_by,
                            "agent_created": record.agent_created,
                            "use_count": record.use_count,
                            "view_count": record.view_count,
                            "patch_count": record.patch_count,
                            "last_used_at": record.last_used_at,
                            "last_viewed_at": record.last_viewed_at,
                            "last_patched_at": record.last_patched_at,
                            "created_at": record.created_at,
                            "state": record.state,
                            "pinned": record.pinned,
                            "version": record.version,
                            "tags": record.tags,
                        }
                        for name, record in self._cache.items()
                    }
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp, self.usage_file)
            except BaseException:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
                raise
        except Exception as e:
            logger.warning(f"Failed to save skill usage file: {e}", exc_info=True)

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _parse_iso(self, value: Optional[str]) -> Optional[datetime]:
        """解析 ISO 时间戳"""
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except (TypeError, ValueError):
            return None

    def get_record(self, skill_id: str) -> Optional[SkillUsageRecord]:
        """获取技能使用记录"""
        return self._cache.get(skill_id)

    def get_all_records(self) -> List[SkillUsageRecord]:
        """获取所有使用记录"""
        return list(self._cache.values())

    def get_agent_created_skills(self) -> List[SkillUsageRecord]:
        """获取 agent 创建的技能 (可被 Curator 管理)"""
        return [
            record for record in self._cache.values()
            if record.agent_created or record.created_by == "agent"
        ]

    def get_active_skills(self) -> List[SkillUsageRecord]:
        """获取活跃状态的技能"""
        return [r for r in self._cache.values() if r.state == SKILL_STATE_ACTIVE]

    def get_stale_skills(self) -> List[SkillUsageRecord]:
        """获取过期状态的技能"""
        return [r for r in self._cache.values() if r.state == SKILL_STATE_STALE]

    def get_archived_skills(self) -> List[SkillUsageRecord]:
        """获取已归档的技能"""
        return [r for r in self._cache.values() if r.state == SKILL_STATE_ARCHIVED]

    def record_use(self, skill_id: str) -> None:
        """
        记录技能使用事件

        Args:
            skill_id: 技能 ID
        """
        if skill_id not in self._cache:
            self._cache[skill_id] = SkillUsageRecord(skill_id=skill_id)

        record = self._cache[skill_id]
        record.use_count += 1
        record.last_used_at = self._now_iso()

        if record.state == SKILL_STATE_STALE:
            record.state = SKILL_STATE_ACTIVE
            logger.info(f"Skill {skill_id} reactivated (was stale)")

        self._save_usage()
        logger.debug(f"Recorded use for skill: {skill_id}")

    def record_view(self, skill_id: str) -> None:
        """
        记录技能查看事件

        Args:
            skill_id: 技能 ID
        """
        if skill_id not in self._cache:
            self._cache[skill_id] = SkillUsageRecord(skill_id=skill_id)

        record = self._cache[skill_id]
        record.view_count += 1
        record.last_viewed_at = self._now_iso()

        self._save_usage()
        logger.debug(f"Recorded view for skill: {skill_id}")

    def record_patch(self, skill_id: str) -> None:
        """
        记录技能修改事件

        Args:
            skill_id: 技能 ID
        """
        if skill_id not in self._cache:
            self._cache[skill_id] = SkillUsageRecord(skill_id=skill_id)

        record = self._cache[skill_id]
        record.patch_count += 1
        record.last_patched_at = self._now_iso()

        self._save_usage()
        logger.debug(f"Recorded patch for skill: {skill_id}")

    def create_skill_record(
        self,
        skill_id: str,
        created_by: str = "agent",
        tags: Optional[List[str]] = None,
    ) -> SkillUsageRecord:
        """
        为新技能创建使用记录

        Args:
            skill_id: 技能 ID
            created_by: 创建者 ("agent", "user", "bundled", "hub")
            tags: 技能标签

        Returns:
            创建的记录
        """
        record = SkillUsageRecord(
            skill_id=skill_id,
            created_by=created_by,
            agent_created=(created_by == "agent"),
            tags=tags or [],
        )
        self._cache[skill_id] = record
        self._save_usage()
        logger.info(f"Created usage record for skill: {skill_id}")
        return record

    def set_state(self, skill_id: str, state: str) -> bool:
        """
        设置技能状态

        Args:
            skill_id: 技能 ID
            state: 新状态 (active/stale/archived)

        Returns:
            是否成功
        """
        if state not in VALID_STATES:
            logger.warning(f"Invalid state: {state}")
            return False

        if skill_id not in self._cache:
            logger.warning(f"Skill {skill_id} not found")
            return False

        old_state = self._cache[skill_id].state
        self._cache[skill_id].state = state
        self._save_usage()

        logger.info(f"Skill {skill_id} state: {old_state} -> {state}")
        return True

    def set_pinned(self, skill_id: str, pinned: bool = True) -> bool:
        """
        设置技能是否被固定

        被固定的技能不会被 Curator 自动管理

        Args:
            skill_id: 技能 ID
            pinned: 是否固定

        Returns:
            是否成功
        """
        if skill_id not in self._cache:
            logger.warning(f"Skill {skill_id} not found")
            return False

        self._cache[skill_id].pinned = pinned
        self._save_usage()

        action = "pinned" if pinned else "unpinned"
        logger.info(f"Skill {skill_id} {action}")
        return True

    def get_latest_activity(self, skill_id: str) -> Optional[datetime]:
        """
        获取技能的最新活动时间

        活动时间 = 最近一次使用、查看或修改
        """
        record = self._cache.get(skill_id)
        if not record:
            return None

        timestamps = [
            self._parse_iso(record.last_used_at),
            self._parse_iso(record.last_viewed_at),
            self._parse_iso(record.last_patched_at),
        ]

        valid_timestamps = [ts for ts in timestamps if ts is not None]
        return max(valid_timestamps) if valid_timestamps else None

    def get_activity_count(self, skill_id: str) -> int:
        """
        获取技能的总活动次数

        活动 = 使用 + 查看 + 修改
        """
        record = self._cache.get(skill_id)
        if not record:
            return 0

        return record.use_count + record.view_count + record.patch_count

    def get_usage_summary(self) -> Dict[str, Any]:
        """
        获取使用统计摘要

        Returns:
            统计摘要字典
        """
        total = len(self._cache)
        active = len(self.get_active_skills())
        stale = len(self.get_stale_skills())
        archived = len(self.get_archived_skills())
        agent_created = len(self.get_agent_created_skills())

        total_uses = sum(r.use_count for r in self._cache.values())
        total_views = sum(r.view_count for r in self._cache.values())
        total_patches = sum(r.patch_count for r in self._cache.values())

        return {
            "total_skills": total,
            "active": active,
            "stale": stale,
            "archived": archived,
            "agent_created": agent_created,
            "total_uses": total_uses,
            "total_views": total_views,
            "total_patches": total_patches,
        }

    def get_skill_report(self) -> List[Dict[str, Any]]:
        """
        获取所有技能的使用报告

        Returns:
            技能报告列表,包含使用统计和状态信息
        """
        reports = []
        for record in self._cache.values():
            latest_activity = self.get_latest_activity(record.skill_id)
            reports.append({
                "name": record.skill_id,
                "state": record.state,
                "pinned": record.pinned,
                "use_count": record.use_count,
                "view_count": record.view_count,
                "patch_count": record.patch_count,
                "activity_count": self.get_activity_count(record.skill_id),
                "last_activity_at": latest_activity.isoformat() if latest_activity else None,
                "last_used_at": record.last_used_at,
                "last_viewed_at": record.last_viewed_at,
                "last_patched_at": record.last_patched_at,
                "created_at": record.created_at,
                "created_by": record.created_by,
                "agent_created": record.agent_created,
                "tags": record.tags,
                "version": record.version,
            })
        return sorted(reports, key=lambda x: x["activity_count"], reverse=True)

    def archive_skill(self, skill_id: str, target_dir: Optional[Path] = None) -> bool:
        """
        归档技能

        将技能移动到 .archive 目录,并设置状态为 archived

        Args:
            skill_id: 技能 ID
            target_dir: 归档目标目录 (默认为 skills/.archive/)

        Returns:
            是否成功
        """
        if target_dir is None:
            target_dir = self.skills_dir / ".archive"

        if skill_id not in self._cache:
            logger.warning(f"Skill {skill_id} not found")
            return False

        skill_dir = self.skills_dir / skill_id
        if not skill_dir.exists():
            logger.warning(f"Skill directory not found: {skill_dir}")
            return False

        try:
            target_dir.mkdir(parents=True, exist_ok=True)

            archive_path = target_dir / skill_id
            if archive_path.exists():
                import shutil
                shutil.rmtree(archive_path)

            skill_dir.rename(archive_path)

            self.set_state(skill_id, SKILL_STATE_ARCHIVED)
            logger.info(f"Archived skill: {skill_id} -> {archive_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to archive skill {skill_id}: {e}")
            return False

    def restore_skill(self, skill_id: str) -> bool:
        """
        恢复已归档的技能

        Args:
            skill_id: 技能 ID

        Returns:
            是否成功
        """
        archive_path = self.skills_dir / ".archive" / skill_id
        if not archive_path.exists():
            logger.warning(f"Archived skill not found: {skill_id}")
            return False

        try:
            skill_dir = self.skills_dir / skill_id
            if skill_dir.exists():
                import shutil
                shutil.rmtree(skill_dir)

            archive_path.rename(skill_dir)

            self.set_state(skill_id, SKILL_STATE_ACTIVE)
            logger.info(f"Restored skill: {skill_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to restore skill {skill_id}: {e}")
            return False

    def delete_skill_record(self, skill_id: str) -> bool:
        """
        删除技能使用记录

        注意:这不会删除实际的技能文件,只会删除追踪记录

        Args:
            skill_id: 技能 ID

        Returns:
            是否成功
        """
        if skill_id in self._cache:
            del self._cache[skill_id]
            self._save_usage()
            logger.info(f"Deleted usage record for skill: {skill_id}")
            return True
        return False


_global_telemetry: Optional[SkillTelemetry] = None


def get_skill_telemetry() -> SkillTelemetry:
    """获取全局技能追踪器实例"""
    global _global_telemetry
    if _global_telemetry is None:
        _global_telemetry = SkillTelemetry()
    return _global_telemetry
