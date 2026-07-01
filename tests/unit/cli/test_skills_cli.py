"""
Skills CLI 测试
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def temp_skills_dir():
    """创建临时技能目录"""
    temp = Path(tempfile.mkdtemp())
    yield temp
    shutil.rmtree(temp, ignore_errors=True)


def test_list_skills_empty(temp_skills_dir, monkeypatch):
    """测试列出空技能目录"""
    from cli.skills_cli import list_skills
    from agent.skill_usage_tracker import SkillTelemetry

    telemetry = SkillTelemetry(skills_dir=temp_skills_dir)

    def mock_get_skills_dir():
        return temp_skills_dir

    def mock_get_telemetry():
        return telemetry

    monkeypatch.setattr("cli.skills_cli.get_skills_dir", mock_get_skills_dir)
    monkeypatch.setattr("brain.skills.get_skill_telemetry", mock_get_telemetry)

    result = list_skills()
    assert result is True


def test_list_skills_with_skills(temp_skills_dir, monkeypatch):
    """测试列出有技能的目录"""
    from cli.skills_cli import list_skills
    from agent.skill_usage_tracker import SkillTelemetry

    skill1_dir = temp_skills_dir / "test_skill"
    skill1_dir.mkdir()
    (skill1_dir / "SKILL.md").write_text("# Test Skill\n\nTest skill description", encoding="utf-8")

    telemetry = SkillTelemetry(skills_dir=temp_skills_dir)
    telemetry.create_skill_record("test_skill", created_by="user")

    def mock_get_skills_dir():
        return temp_skills_dir

    def mock_get_telemetry():
        return telemetry

    monkeypatch.setattr("cli.skills_cli.get_skills_dir", mock_get_skills_dir)
    monkeypatch.setattr("brain.skills.get_skill_telemetry", mock_get_telemetry)

    result = list_skills()
    assert result is True


def test_sync_skills_empty(temp_skills_dir, monkeypatch):
    """测试同步空技能目录"""
    from cli.skills_cli import sync_skills
    from agent.skill_usage_tracker import SkillTelemetry

    telemetry = SkillTelemetry(skills_dir=temp_skills_dir)

    async def mock_load_all(self):
        return []

    def mock_get_skills_dir():
        return temp_skills_dir

    def mock_get_telemetry():
        return telemetry

    monkeypatch.setattr("cli.skills_cli.get_skills_dir", mock_get_skills_dir)
    monkeypatch.setattr("brain.skills.get_skill_telemetry", mock_get_telemetry)

    result = asyncio.run(sync_skills())
    assert result is True


def test_uninstall_skill_not_exists(temp_skills_dir, monkeypatch):
    """测试卸载不存在的技能"""
    from cli.skills_cli import uninstall_skill
    from agent.skill_usage_tracker import SkillTelemetry

    telemetry = SkillTelemetry(skills_dir=temp_skills_dir)

    def mock_get_skills_dir():
        return temp_skills_dir

    def mock_get_telemetry():
        return telemetry

    monkeypatch.setattr("cli.skills_cli.get_skills_dir", mock_get_skills_dir)
    monkeypatch.setattr("brain.skills.get_skill_telemetry", mock_get_telemetry)

    result = uninstall_skill("nonexistent")
    assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
