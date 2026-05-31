"""
自我进化系统集成测试
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
import sys
import importlib


@pytest.fixture
def temp_dir():
    """创建临时目录"""
    temp = Path(tempfile.mkdtemp())
    yield temp
    shutil.rmtree(temp)


def test_self_evolution_manager_initialization(temp_dir):
    """测试自我进化管理器初始化"""
    from brain.skills import SelfEvolutionManager, SelfEvolutionConfig

    config = SelfEvolutionConfig(
        enable_telemetry=True,
        enable_lifecycle=True,
        enable_curator=True,
        enable_merger=True,
    )

    skills_dir = temp_dir / "skills"
    manager = SelfEvolutionManager(config=config, skills_dir=skills_dir)

    status = manager.get_status()

    assert status["running"] is False


def test_self_evolution_manager_record_usage(temp_dir):
    """测试记录技能使用"""
    from brain.skills.telemetry import SkillTelemetry

    skills_dir = temp_dir / "skills"
    telemetry = SkillTelemetry(skills_dir=skills_dir)

    telemetry.create_skill_record("test_skill", created_by="agent")
    telemetry.record_use("test_skill")
    telemetry.record_use("test_skill")
    telemetry.record_view("test_skill")

    summary = telemetry.get_usage_summary()

    assert summary.get("total_uses") == 2
    assert summary.get("total_views") == 1


def test_self_evolution_manager_components(temp_dir):
    """测试组件获取"""
    from brain.skills import SelfEvolutionManager, SelfEvolutionConfig

    config = SelfEvolutionConfig()
    skills_dir = temp_dir / "skills"
    manager = SelfEvolutionManager(config=config, skills_dir=skills_dir)

    assert manager.merger is not None


def test_enable_disable_components(temp_dir):
    """测试启用/禁用组件"""
    from brain.skills import SelfEvolutionManager, SelfEvolutionConfig

    config = SelfEvolutionConfig()
    skills_dir = temp_dir / "skills"
    manager = SelfEvolutionManager(skills_dir=skills_dir)

    status = manager.get_status()
    assert "components" in status
    assert "telemetry" in status["components"]


def test_lifecycle_manager_integration(temp_dir):
    """测试与生命周期管理器的集成"""
    from brain.skills.telemetry import SkillTelemetry
    from brain.skills.lifecycle import SkillLifecycleManager

    skills_dir = temp_dir / "skills"
    telemetry = SkillTelemetry(skills_dir=skills_dir)
    lifecycle = SkillLifecycleManager(telemetry=telemetry, stale_after_days=7)

    telemetry.create_skill_record("skill1", created_by="agent")
    telemetry.create_skill_record("skill2", created_by="agent")

    summary = lifecycle.get_lifecycle_summary()
    assert summary.get("active") >= 0


def test_curator_integration(temp_dir):
    """测试与 Curator 的集成"""
    from brain_curator.enhanced_curator import EnhancedCurator, CuratorState

    state_file = temp_dir / ".curator_state"
    curator_state = CuratorState(state_file=state_file)
    curator = EnhancedCurator(curator_state=curator_state)

    status = curator.get_status()
    assert "running" in status
    assert "paused" in status


@pytest.mark.asyncio
async def test_start_stop(temp_dir):
    """测试启动/停止"""
    from brain_curator.enhanced_curator import EnhancedCurator, CuratorState
    from brain.skills.lifecycle import SkillLifecycleManager
    from brain.skills.telemetry import SkillTelemetry

    skills_dir = temp_dir / "skills"
    state_file = temp_dir / ".curator_state"

    telemetry = SkillTelemetry(skills_dir=skills_dir)
    lifecycle = SkillLifecycleManager(telemetry=telemetry)
    curator_state = CuratorState(state_file=state_file)
    curator = EnhancedCurator(curator_state=curator_state)

    assert curator_state.paused is False


@pytest.mark.asyncio
async def test_trigger_review(temp_dir):
    """测试触发审查"""
    from brain_curator.enhanced_curator import EnhancedCurator, CuratorState

    state_file = temp_dir / ".curator_state"
    curator_state = CuratorState(state_file=state_file)
    curator = EnhancedCurator(curator_state=curator_state)

    result = await curator.maybe_run(
        idle_for_seconds=7200,
    )

    assert result is None


def test_config_defaults():
    """测试配置默认值"""
    from brain.skills import SelfEvolutionConfig

    config = SelfEvolutionConfig()

    assert config.enable_telemetry is True
    assert config.enable_lifecycle is True
    assert config.enable_curator is True
    assert config.enable_merger is True
    assert config.curator_interval_hours == 168
    assert config.curator_min_idle_hours == 2.0
    assert config.merger_threshold == 0.6


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
