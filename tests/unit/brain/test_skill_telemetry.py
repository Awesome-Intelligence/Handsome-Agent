"""
技能使用追踪系统测试
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from brain.skills.telemetry import SkillTelemetry, SkillUsageRecord


@pytest.fixture
def temp_skills_dir():
    """创建临时技能目录"""
    temp_dir = Path(tempfile.mkdtemp())
    skills_dir = temp_dir / "skills"
    skills_dir.mkdir()
    yield skills_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def telemetry(temp_skills_dir):
    """创建技能追踪器实例"""
    return SkillTelemetry(skills_dir=temp_skills_dir)


def test_create_and_get_record(telemetry):
    """测试创建和获取使用记录"""
    record = telemetry.create_skill_record(
        skill_id="test_skill",
        created_by="agent",
        tags=["test", "demo"],
    )

    assert record.skill_id == "test_skill"
    assert record.created_by == "agent"
    assert record.agent_created is True
    assert record.state == "active"
    assert "test" in record.tags

    retrieved = telemetry.get_record("test_skill")
    assert retrieved is not None
    assert retrieved.skill_id == "test_skill"


def test_record_use(telemetry):
    """测试记录技能使用"""
    telemetry.create_skill_record("test_skill", created_by="agent")

    telemetry.record_use("test_skill")
    telemetry.record_use("test_skill")
    telemetry.record_use("test_skill")

    record = telemetry.get_record("test_skill")
    assert record.use_count == 3
    assert record.last_used_at is not None


def test_record_view(telemetry):
    """测试记录技能查看"""
    telemetry.create_skill_record("test_skill", created_by="agent")

    telemetry.record_view("test_skill")
    telemetry.record_view("test_skill")

    record = telemetry.get_record("test_skill")
    assert record.view_count == 2
    assert record.last_viewed_at is not None


def test_record_patch(telemetry):
    """测试记录技能修改"""
    telemetry.create_skill_record("test_skill", created_by="agent")

    telemetry.record_patch("test_skill")

    record = telemetry.get_record("test_skill")
    assert record.patch_count == 1
    assert record.last_patched_at is not None


def test_state_transitions(telemetry):
    """测试状态转换"""
    telemetry.create_skill_record("test_skill", created_by="agent")

    assert telemetry.get_record("test_skill").state == "active"

    telemetry.set_state("test_skill", "stale")
    assert telemetry.get_record("test_skill").state == "stale"

    telemetry.set_state("test_skill", "archived")
    assert telemetry.get_record("test_skill").state == "archived"

    telemetry.set_state("test_skill", "active")
    assert telemetry.get_record("test_skill").state == "active"


def test_reactivation(telemetry):
    """测试过期技能重新激活"""
    telemetry.create_skill_record("test_skill", created_by="agent")
    telemetry.set_state("test_skill", "stale")

    telemetry.record_use("test_skill")

    assert telemetry.get_record("test_skill").state == "active"


def test_pinned(telemetry):
    """测试固定技能"""
    telemetry.create_skill_record("test_skill", created_by="agent")

    telemetry.set_pinned("test_skill", True)
    assert telemetry.get_record("test_skill").pinned is True

    telemetry.set_pinned("test_skill", False)
    assert telemetry.get_record("test_skill").pinned is False


def test_get_by_state(telemetry):
    """测试按状态获取技能"""
    telemetry.create_skill_record("skill1", created_by="agent")
    telemetry.create_skill_record("skill2", created_by="agent")
    telemetry.create_skill_record("skill3", created_by="agent")

    telemetry.set_state("skill2", "stale")

    active_skills = telemetry.get_active_skills()
    assert len(active_skills) == 2

    stale_skills = telemetry.get_stale_skills()
    assert len(stale_skills) == 1
    assert stale_skills[0].skill_id == "skill2"


def test_get_agent_created_skills(telemetry):
    """测试获取 agent 创建的技能"""
    telemetry.create_skill_record("agent_skill1", created_by="agent")
    telemetry.create_skill_record("agent_skill2", created_by="agent")
    telemetry.create_skill_record("user_skill", created_by="user")

    agent_skills = telemetry.get_agent_created_skills()
    assert len(agent_skills) == 2


def test_activity_count(telemetry):
    """测试获取活动次数"""
    telemetry.create_skill_record("test_skill", created_by="agent")

    telemetry.record_use("test_skill")
    telemetry.record_use("test_skill")
    telemetry.record_view("test_skill")
    telemetry.record_patch("test_skill")

    activity_count = telemetry.get_activity_count("test_skill")
    assert activity_count == 4


def test_usage_summary(telemetry):
    """测试使用统计摘要"""
    telemetry.create_skill_record("skill1", created_by="agent")
    telemetry.create_skill_record("skill2", created_by="agent")

    telemetry.record_use("skill1")
    telemetry.record_view("skill1")

    summary = telemetry.get_usage_summary()

    assert summary["total_skills"] == 2
    assert summary["active"] == 2
    assert summary["total_uses"] == 1
    assert summary["total_views"] == 1


def test_skill_report(telemetry):
    """测试技能报告生成"""
    telemetry.create_skill_record("skill1", created_by="agent")
    telemetry.create_skill_record("skill2", created_by="agent")

    telemetry.record_use("skill1")
    telemetry.record_use("skill1")
    telemetry.record_use("skill1")

    telemetry.record_view("skill2")

    report = telemetry.get_skill_report()

    assert len(report) == 2

    report_by_name = {r["name"]: r for r in report}
    assert report_by_name["skill1"]["use_count"] == 3
    assert report_by_name["skill1"]["activity_count"] == 3
    assert report_by_name["skill2"]["view_count"] == 1


def test_persistence(telemetry):
    """测试数据持久化"""
    telemetry.create_skill_record("test_skill", created_by="agent")
    telemetry.record_use("test_skill")
    telemetry.set_state("test_skill", "stale")

    new_telemetry = SkillTelemetry(skills_dir=telemetry.skills_dir)

    record = new_telemetry.get_record("test_skill")
    assert record is not None
    assert record.use_count == 1
    assert record.state == "stale"


def test_archive_skill(telemetry):
    """测试归档技能"""
    skill_dir = telemetry.skills_dir / "test_skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Test Skill")

    telemetry.create_skill_record("test_skill", created_by="agent")
    telemetry.record_use("test_skill")

    result = telemetry.archive_skill("test_skill")

    assert result is True
    assert not skill_dir.exists()
    assert (telemetry.skills_dir / ".archive" / "test_skill").exists()
    assert telemetry.get_record("test_skill").state == "archived"


def test_restore_skill(telemetry):
    """测试恢复技能"""
    skill_dir = telemetry.skills_dir / "test_skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Test Skill")

    telemetry.create_skill_record("test_skill", created_by="agent")
    telemetry.archive_skill("test_skill")

    result = telemetry.restore_skill("test_skill")

    assert result is True
    assert skill_dir.exists()
    assert not (telemetry.skills_dir / ".archive" / "test_skill").exists()
    assert telemetry.get_record("test_skill").state == "active"


def test_delete_record(telemetry):
    """测试删除使用记录"""
    telemetry.create_skill_record("test_skill", created_by="agent")
    telemetry.record_use("test_skill")

    result = telemetry.delete_skill_record("test_skill")

    assert result is True
    assert telemetry.get_record("test_skill") is None


def test_get_latest_activity(telemetry):
    """测试获取最新活动时间"""
    telemetry.create_skill_record("test_skill", created_by="agent")

    import time
    telemetry.record_use("test_skill")
    time.sleep(0.01)
    telemetry.record_view("test_skill")

    latest = telemetry.get_latest_activity("test_skill")
    assert latest is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
