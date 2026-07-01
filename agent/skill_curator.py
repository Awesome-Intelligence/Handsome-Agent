#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill Curator - 技能生命周期管理

自动管理技能的陈旧和归档：
- 检测 30 天未使用的技能并标记为 stale
- 检测 60 天未使用的技能并归档到 .archive/
- 支持置顶技能不受自动管理影响
- 提供 CLI 命令支持

🚪 Access - 📋 Skills - Curator 管理
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from common.config import get_settings
from agent.skill_usage_tracker import (
    STATE_ACTIVE,
    STATE_STALE,
    STATE_ARCHIVED,
    load_usage,
    archive_skill as tracker_archive,
    restore_skill as tracker_restore,
    set_state,
    set_pinned,
    latest_activity_at,
    activity_count,
    agent_created_report,
)

logger = logging.getLogger(__name__)

# 默认配置
DEFAULT_STALE_DAYS = 30
DEFAULT_ARCHIVE_DAYS = 60


@dataclass
class CuratorConfig:
    """Curator 配置"""
    stale_after_days: int = DEFAULT_STALE_DAYS
    archive_after_days: int = DEFAULT_ARCHIVE_DAYS
    auto_archive: bool = True  # 是否自动归档
    auto_mark_stale: bool = True  # 是否自动标记陈旧
    dry_run: bool = False  # 试运行模式


@dataclass
class CuratorAction:
    """Curator 操作记录"""
    skill_name: str
    action: str  # "mark_stale" | "archive" | "restore" | "unpin"
    reason: str
    before_state: str
    after_state: str
    timestamp: str = ""


@dataclass
class CuratorReport:
    """Curator 报告"""
    timestamp: str
    config: CuratorConfig
    actions: List[CuratorAction] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


def _now_iso() -> str:
    """获取当前 UTC 时间戳"""
    return datetime.now(timezone.utc).isoformat()


def _days_ago(days: int) -> datetime:
    """计算 N 天前的时间"""
    return datetime.now(timezone.utc) - timedelta(days=days)


def _parse_iso_timestamp(value: Any) -> Optional[datetime]:
    """解析 ISO 时间戳"""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def get_curator_config() -> CuratorConfig:
    """从配置获取 Curator 设置"""
    try:
        skills_config = get_settings().skills
        curator_config = skills_config.get("curator", {})

        return CuratorConfig(
            stale_after_days=curator_config.get("stale_after_days", DEFAULT_STALE_DAYS),
            archive_after_days=curator_config.get("archive_after_days", DEFAULT_ARCHIVE_DAYS),
            auto_archive=curator_config.get("auto_archive", True),
            auto_mark_stale=curator_config.get("auto_mark_stale", True),
            dry_run=curator_config.get("dry_run", False),
        )
    except Exception:
        return CuratorConfig()


def check_skill_staleness(
    skill_name: str,
    record: Dict[str, Any],
    config: CuratorConfig,
) -> Optional[str]:
    """
    检查技能是否应该被标记为陈旧

    Returns:
        None: 不需要操作
        "active": 标记为活跃
        "stale": 应该标记为陈旧
    """
    # 置顶技能不受影响
    if record.get("pinned"):
        return None

    # 已经是归档状态
    if record.get("state") == STATE_ARCHIVED:
        return None

    # 获取最近活动时间
    last_activity = latest_activity_at(record)
    if not last_activity:
        # 从未活动过，检查创建时间
        created_at = record.get("created_at")
        if created_at:
            last_activity = created_at
        else:
            return None

    last_dt = _parse_iso_timestamp(last_activity)
    if not last_dt:
        return None

    days_since_activity = (datetime.now(timezone.utc) - last_dt).days

    if days_since_activity >= config.stale_after_days:
        return "stale"

    if record.get("state") == STATE_STALE and days_since_activity < config.stale_after_days:
        # 恢复活跃状态
        return STATE_ACTIVE

    return None


def check_skill_archive(
    skill_name: str,
    record: Dict[str, Any],
    config: CuratorConfig,
) -> bool:
    """
    检查技能是否应该被归档

    Returns:
        True: 应该归档
        False: 不需要归档
    """
    # 置顶技能不受影响
    if record.get("pinned"):
        return False

    # 已经是归档状态
    if record.get("state") == STATE_ARCHIVED:
        return False

    # 获取最近活动时间
    last_activity = latest_activity_at(record)
    if not last_activity:
        created_at = record.get("created_at")
        if created_at:
            last_activity = created_at
        else:
            return False

    last_dt = _parse_iso_timestamp(last_activity)
    if not last_dt:
        return False

    days_since_activity = (datetime.now(timezone.utc) - last_dt).days
    return days_since_activity >= config.archive_after_days


def run_curator(config: Optional[CuratorConfig] = None) -> CuratorReport:
    """
    运行 Curator 清理

    Args:
        config: Curator 配置，None 则使用默认

    Returns:
        CuratorReport: 清理报告
    """
    if config is None:
        config = get_curator_config()

    report = CuratorReport(
        timestamp=_now_iso(),
        config=config,
    )

    # 加载使用数据
    usage_data = load_usage()

    # 统计
    report.stats = {
        "total_skills": 0,
        "active_skills": 0,
        "stale_skills": 0,
        "archived_skills": 0,
        "pinned_skills": 0,
        "marked_stale": 0,
        "archived": 0,
        "restored": 0,
    }

    for skill_name, record in usage_data.items():
        if not isinstance(record, dict):
            continue

        report.stats["total_skills"] += 1

        # 统计各状态数量
        state = record.get("state", STATE_ACTIVE)
        if state == STATE_ACTIVE:
            report.stats["active_skills"] += 1
        elif state == STATE_STALE:
            report.stats["stale_skills"] += 1
        elif state == STATE_ARCHIVED:
            report.stats["archived_skills"] += 1

        if record.get("pinned"):
            report.stats["pinned_skills"] += 1

        # Agent 创建的技能才受 Curator 管理
        if record.get("created_by") != "agent":
            continue

        # 检查是否应该标记为陈旧
        if config.auto_mark_stale:
            staleness_action = check_skill_staleness(skill_name, record, config)
            if staleness_action == "stale" and record.get("state") != STATE_STALE:
                action = CuratorAction(
                    skill_name=skill_name,
                    action="mark_stale",
                    reason=f"Unused for {config.stale_after_days} days",
                    before_state=record.get("state", STATE_ACTIVE),
                    after_state=STATE_STALE,
                    timestamp=_now_iso(),
                )
                report.actions.append(action)
                report.stats["marked_stale"] += 1

                if not config.dry_run:
                    try:
                        set_state(skill_name, STATE_STALE)
                    except Exception as e:
                        report.errors.append(f"Failed to mark {skill_name} as stale: {e}")

        # 检查是否应该归档
        if config.auto_archive:
            if check_skill_archive(skill_name, record, config):
                action = CuratorAction(
                    skill_name=skill_name,
                    action="archive",
                    reason=f"Unused for {config.archive_after_days} days",
                    before_state=record.get("state", STATE_ACTIVE),
                    after_state=STATE_ARCHIVED,
                    timestamp=_now_iso(),
                )
                report.actions.append(action)
                report.stats["archived"] += 1

                if not config.dry_run:
                    try:
                        ok, msg = tracker_archive(skill_name)
                        if not ok:
                            report.errors.append(f"Failed to archive {skill_name}: {msg}")
                    except Exception as e:
                        report.errors.append(f"Failed to archive {skill_name}: {e}")

        # 检查是否应该从陈旧恢复活跃
        if config.auto_mark_stale:
            staleness_action = check_skill_staleness(skill_name, record, config)
            if staleness_action == STATE_ACTIVE and record.get("state") == STATE_STALE:
                action = CuratorAction(
                    skill_name=skill_name,
                    action="restore_active",
                    reason="Used again",
                    before_state=STATE_STALE,
                    after_state=STATE_ACTIVE,
                    timestamp=_now_iso(),
                )
                report.actions.append(action)
                report.stats["restored"] += 1

                if not config.dry_run:
                    try:
                        set_state(skill_name, STATE_ACTIVE)
                    except Exception as e:
                        report.errors.append(f"Failed to restore {skill_name}: {e}")

    return report


def format_report(report: CuratorReport) -> str:
    """格式化 Curator 报告为可读字符串"""
    lines = [
        "=" * 60,
        "Skill Curator Report",
        "=" * 60,
        f"Timestamp: {report.timestamp}",
        f"Dry Run: {report.config.dry_run}",
        "",
        "Configuration:",
        f"  Stale after: {report.config.stale_after_days} days",
        f"  Archive after: {report.config.archive_after_days} days",
        f"  Auto mark stale: {report.config.auto_mark_stale}",
        f"  Auto archive: {report.config.auto_archive}",
        "",
        "Statistics:",
        f"  Total skills: {report.stats.get('total_skills', 0)}",
        f"  Active: {report.stats.get('active_skills', 0)}",
        f"  Stale: {report.stats.get('stale_skills', 0)}",
        f"  Archived: {report.stats.get('archived_skills', 0)}",
        f"  Pinned: {report.stats.get('pinned_skills', 0)}",
        "",
    ]

    if report.actions:
        lines.extend([
            "Actions:",
        ])
        for action in report.actions:
            lines.append(
                f"  [{action.action}] {action.skill_name}: {action.reason}"
            )
        lines.append("")

    if report.stats.get("marked_stale"):
        lines.append(f"  Marked stale: {report.stats['marked_stale']}")
    if report.stats.get("archived"):
        lines.append(f"  Archived: {report.stats['archived']}")
    if report.stats.get("restored"):
        lines.append(f"  Restored to active: {report.stats['restored']}")

    if report.errors:
        lines.extend([
            "",
            "Errors:",
        ])
        for error in report.errors:
            lines.append(f"  ! {error}")

    lines.append("=" * 60)
    return "\n".join(lines)


def list_archived_skills() -> List[str]:
    """列出所有归档的技能"""
    from agent.skill_usage_tracker import _archive_dir
    archive_root = _archive_dir()
    if not archive_root.exists():
        return []
    return sorted({p.name for p in archive_root.iterdir() if p.is_dir()})


def curator_stats() -> Dict[str, Any]:
    """获取 Curator 统计数据"""
    report = run_curator()
    return {
        "timestamp": report.timestamp,
        "stats": report.stats,
        "archived_skills": list_archived_skills(),
        "config": {
            "stale_after_days": report.config.stale_after_days,
            "archive_after_days": report.config.archive_after_days,
        },
    }


def pin_skill(skill_name: str) -> bool:
    """
    置顶技能，防止被 Curator 自动管理

    Returns:
        True: 成功
        False: 失败
    """
    try:
        set_pinned(skill_name, True)
        return True
    except Exception as e:
        logger.error(f"Failed to pin skill {skill_name}: {e}")
        return False


def unpin_skill(skill_name: str) -> bool:
    """
    取消置顶技能

    Returns:
        True: 成功
        False: 失败
    """
    try:
        set_pinned(skill_name, False)
        return True
    except Exception as e:
        logger.error(f"Failed to unpin skill {skill_name}: {e}")
        return False


def restore_archived_skill(skill_name: str) -> Tuple[bool, str]:
    """
    恢复归档的技能

    Returns:
        (成功, 消息)
    """
    try:
        return tracker_restore(skill_name)
    except Exception as e:
        logger.error(f"Failed to restore skill {skill_name}: {e}")
        return False, str(e)


def force_archive_skill(skill_name: str) -> Tuple[bool, str]:
    """
    强制归档技能

    Returns:
        (成功, 消息)
    """
    try:
        return tracker_archive(skill_name)
    except Exception as e:
        logger.error(f"Failed to archive skill {skill_name}: {e}")
        return False, str(e)


if __name__ == "__main__":
    # 试运行
    report = run_curator()
    print(format_report(report))

    # 显示归档的技能
    archived = list_archived_skills()
    if archived:
        print("\nArchived skills:")
        for name in archived:
            print(f"  - {name}")
