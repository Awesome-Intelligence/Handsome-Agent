"""
技能生命周期管理系统测试
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta
from brain.skills.lifecycle import SkillLifecycleManager, SKILL_STATE_ACTIVE, SKILL_STATE_STALE, SKILL_STATE_ARCHIVED


@pytest.fixture
def temp_skills_dir():
    """创建临时技能目录"""
    temp_dir = Path(tempfile.mkdtemp())
    skills_dir = temp_dir / "skills"
    skills_dir.mkdir()
    yield skills_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def lifecycle_manager(temp_skills_dir):
    """创建生命周期管理器实例"""
    from brain.skills.telemetry import SkillTelemetry
    telemetry = SkillTelemetry(skills_dir=temp_skills_dir)
    return SkillLifecycleManager(
        telemetry=telemetry,
        stale_after_days=7,
        archive_after_days=14,
    )


def test_initial_state(lifecycle_manager):
    """测试初始状态"""
    summary = lifecycle_manager.get_lifecycle_summary()
    assert summary["total_agent_created"] == 0
    assert summary["active"] == 0
    assert summary["stale"] == 0
    assert summary["archived"] == 0


def test_active_to_stale_transition(lifecycle_manager):
    """测试活跃到过期状态的转换"""
    telemetry = lifecycle_manager.telemetry

    telemetry.create_skill_record("old_skill", created_by="agent")
    record = telemetry.get_record("old_skill")
    old_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    record.last_used_at = old_time
    telemetry._save_usage()

    telemetry.create_skill_record("new_skill", created_by="agent")

    report = lifecycle_manager.apply_automatic_transitions()

    assert report.checked_count == 2
    assert report.marked_stale == 1
    assert report.archived == 0
    assert telemetry.get_record("new_skill").state == SKILL_STATE_ACTIVE
    assert telemetry.get_record("old_skill").state == SKILL_STATE_STALE


def test_stale_to_archived_transition(lifecycle_manager):
    """测试过期到归档状态的转换"""
    telemetry = lifecycle_manager.telemetry

    telemetry.create_skill_record("very_old_skill", created_by="agent")
    record = telemetry.get_record("very_old_skill")
    old_time = (datetime.now(timezone.utc) - timedelta(days=20)).isoformat()
    record.last_used_at = old_time
    record.state = SKILL_STATE_STALE
    telemetry._save_usage()

    skill_dir = telemetry.skills_dir / "very_old_skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Old Skill")

    report = lifecycle_manager.apply_automatic_transitions()

    assert report.marked_stale == 0
    assert report.archived == 1
    assert telemetry.get_record("very_old_skill").state == SKILL_STATE_ARCHIVED


def test_reactivation(lifecycle_manager):
    """测试过期技能重新激活"""
    telemetry = lifecycle_manager.telemetry

    telemetry.create_skill_record("stale_skill", created_by="agent")
    telemetry.set_state("stale_skill", SKILL_STATE_STALE)

    import time
    time.sleep(0.01)
    telemetry.record_use("stale_skill")

    assert telemetry.get_record("stale_skill").state == SKILL_STATE_ACTIVE


def test_pinned_skill_skipped(lifecycle_manager):
    """测试固定技能被跳过"""
    telemetry = lifecycle_manager.telemetry

    telemetry.create_skill_record("pinned_skill", created_by="agent")
    telemetry.set_pinned("pinned_skill", True)
    record = telemetry.get_record("pinned_skill")
    old_time = (datetime.now(timezone.utc) - timedelta(days=20)).isoformat()
    record.last_used_at = old_time
    telemetry._save_usage()

    report = lifecycle_manager.apply_automatic_transitions()

    assert telemetry.get_record("pinned_skill").state == SKILL_STATE_ACTIVE
    assert report.marked_stale == 0
    assert report.archived == 0


def test_callback(lifecycle_manager):
    """测试回调功能"""
    callback_reports = []

    def callback(report):
        callback_reports.append(report)

    lifecycle_manager.add_callback(callback)

    lifecycle_manager.telemetry.create_skill_record("test_skill", created_by="agent")
    record = lifecycle_manager.telemetry.get_record("test_skill")
    old_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    record.last_used_at = old_time
    lifecycle_manager.telemetry._save_usage()

    lifecycle_manager.apply_automatic_transitions()

    assert len(callback_reports) == 1
    assert callback_reports[0].marked_stale == 1


def test_archive_skill(lifecycle_manager):
    """测试手动归档技能"""
    telemetry = lifecycle_manager.telemetry

    telemetry.create_skill_record("to_archive", created_by="agent")
    skill_dir = telemetry.skills_dir / "to_archive"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Archive Test")

    result = lifecycle_manager.archive_skill("to_archive")

    assert result is True
    assert telemetry.get_record("to_archive").state == SKILL_STATE_ARCHIVED
    assert not skill_dir.exists()
    assert (telemetry.skills_dir / ".archive" / "to_archive").exists()


def test_restore_skill(lifecycle_manager):
    """测试手动恢复技能"""
    telemetry = lifecycle_manager.telemetry

    telemetry.create_skill_record("to_restore", created_by="agent")
    skill_dir = telemetry.skills_dir / "to_restore"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Restore Test")
    lifecycle_manager.archive_skill("to_restore")

    result = lifecycle_manager.restore_skill("to_restore")

    assert result is True
    assert telemetry.get_record("to_restore").state == SKILL_STATE_ACTIVE
    assert skill_dir.exists()


def test_pin_unpin_skill(lifecycle_manager):
    """测试固定/取消固定技能"""
    telemetry = lifecycle_manager.telemetry

    telemetry.create_skill_record("pin_test", created_by="agent")

    result1 = lifecycle_manager.pin_skill("pin_test")
    assert result1 is True
    assert telemetry.get_record("pin_test").pinned is True

    result2 = lifecycle_manager.unpin_skill("pin_test")
    assert result2 is True
    assert telemetry.get_record("pin_test").pinned is False


def test_lifecycle_summary(lifecycle_manager):
    """测试生命周期摘要"""
    telemetry = lifecycle_manager.telemetry

    telemetry.create_skill_record("active1", created_by="agent")
    telemetry.record_use("active1")

    telemetry.create_skill_record("active2", created_by="agent")
    telemetry.record_use("active2")

    telemetry.create_skill_record("stale1", created_by="agent")
    telemetry.set_state("stale1", SKILL_STATE_STALE)

    telemetry.create_skill_record("archived1", created_by="agent")
    skill_dir = telemetry.skills_dir / "archived1"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Archived")
    lifecycle_manager.archive_skill("archived1")

    summary = lifecycle_manager.get_lifecycle_summary()

    assert summary["total_agent_created"] == 4
    assert summary["active"] == 2
    assert summary["stale"] == 1
    assert summary["archived"] == 1
    assert summary["stale_threshold_days"] == 7
    assert summary["archive_threshold_days"] == 14


def test_multiple_transitions(lifecycle_manager):
    """测试多个状态转换"""
    telemetry = lifecycle_manager.telemetry

    telemetry.create_skill_record("active_skill", created_by="agent")
    telemetry.create_skill_record("stale_skill", created_by="agent")
    telemetry.set_state("stale_skill", SKILL_STATE_STALE)
    telemetry.create_skill_record("archived_skill", created_by="agent")
    skill_dir = telemetry.skills_dir / "archived_skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Archived")

    record = telemetry.get_record("archived_skill")
    old_time = (datetime.now(timezone.utc) - timedelta(days=20)).isoformat()
    record.last_used_at = old_time
    telemetry._save_usage()

    lifecycle_manager.archive_skill("archived_skill")

    report = lifecycle_manager.apply_automatic_transitions()

    assert report.checked_count == 3
    assert report.marked_stale == 0
    assert report.archived == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
