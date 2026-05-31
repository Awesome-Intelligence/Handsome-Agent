"""
增强版 Curator 测试
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta
from brain_curator.enhanced_curator import EnhancedCurator, CuratorState, EvaluationResult


@pytest.fixture
def temp_dir():
    """创建临时目录"""
    temp = Path(tempfile.mkdtemp())
    yield temp
    shutil.rmtree(temp)


@pytest.fixture
def curator_state(temp_dir):
    """创建 Curator 状态"""
    state_file = temp_dir / ".curator_state"
    return CuratorState(state_file=state_file)


@pytest.fixture
def curator(curator_state):
    """创建 Curator 实例"""
    return EnhancedCurator(curator_state=curator_state)


def test_curator_state_initialization(curator_state):
    """测试状态初始化"""
    assert curator_state.paused is False
    assert curator_state.last_run_at is None
    assert curator_state.run_count == 0


def test_curator_state_update(curator_state):
    """测试状态更新"""
    curator_state.update_run(10.5, "test summary")

    assert curator_state.last_run_at is not None
    assert curator_state.last_run_duration_seconds == 10.5
    assert curator_state.last_run_summary == "test summary"
    assert curator_state.run_count == 1


def test_curator_state_pause_resume(curator_state):
    """测试暂停/恢复"""
    curator_state.set_paused(True)
    assert curator_state.paused is True

    curator_state.set_paused(False)
    assert curator_state.paused is False


def test_curator_should_run(curator_state):
    """测试运行条件检查"""
    assert curator_state.should_run() is False

    curator_state.update_run(1.0, "test")
    assert curator_state.should_run(interval_hours=0) is True


def test_curator_pause(curator):
    """测试暂停 curator"""
    curator.pause()
    status = curator.get_status()
    assert status["paused"] is True


def test_curator_resume(curator):
    """测试恢复 curator"""
    curator.pause()
    curator.resume()
    status = curator.get_status()
    assert status["paused"] is False


def test_evaluate_success_trajectory(curator):
    """测试评估成功轨迹"""
    trajectory = {
        "trajectory_id": "test-123",
        "user_input": "帮我搜索 Python 教程",
        "steps": [
            {"type": "thought", "step_id": 1, "data": {"reasoning": "需要搜索"}},
            {"type": "action", "step_id": 2, "data": {"tool_name": "web_search", "parameters": {"query": "Python 教程"}}},
            {"type": "observation", "step_id": 3, "data": {"result": "找到结果", "success": True}},
            {"type": "thought", "step_id": 4, "data": {"reasoning": "完成任务"}},
        ]
    }

    report = asyncio.run(curator.evaluate(trajectory))

    assert report.trajectory_id == "test-123"
    assert report.overall_result == EvaluationResult.SUCCESS
    assert report.success_rate == 1.0
    assert len(report.steps) == 4


def test_evaluate_partial_success_trajectory(curator):
    """测试评估部分成功轨迹"""
    trajectory = {
        "trajectory_id": "test-456",
        "steps": [
            {"type": "action", "step_id": 1, "data": {"tool_name": "tool1"}},
            {"type": "observation", "step_id": 2, "data": {"result": "ok", "success": True}},
            {"type": "action", "step_id": 3, "data": {"tool_name": "tool2"}},
            {"type": "observation", "step_id": 4, "data": {"result": "fail", "success": False}},
        ]
    }

    report = asyncio.run(curator.evaluate(trajectory))

    assert report.overall_result == EvaluationResult.PARTIAL_SUCCESS
    assert report.success_rate == 0.5


def test_evaluate_failure_trajectory(curator):
    """测试评估失败轨迹"""
    trajectory = {
        "trajectory_id": "test-789",
        "steps": [
            {"type": "action", "step_id": 1, "data": {"tool_name": "tool1"}},
            {"type": "observation", "step_id": 2, "data": {"result": "error", "success": False}},
        ]
    }

    report = asyncio.run(curator.evaluate(trajectory))

    assert report.overall_result == EvaluationResult.FAILURE
    assert report.success_rate == 0.0


def test_synthesize_skill(curator):
    """测试技能合成"""
    trajectory = {
        "trajectory_id": "test-synth",
        "user_input": "帮我搜索 Python 教程",
        "steps": [
            {"type": "thought", "step_id": 1, "data": {"reasoning": "思考"}},
            {"type": "action", "step_id": 2, "data": {"tool_name": "web_search", "parameters": {"query": "Python"}}},
            {"type": "observation", "step_id": 3, "data": {"result": "ok", "success": True}},
        ]
    }

    report = asyncio.run(curator.evaluate(trajectory))
    skill = asyncio.run(curator.synthesize_skill(trajectory, report))

    assert skill is not None
    assert "搜索" in skill.name
    assert "Python" in skill.description
    assert len(skill.trigger_patterns) > 0


def test_get_status(curator):
    """测试获取状态"""
    status = curator.get_status()

    assert "running" in status
    assert "paused" in status
    assert "interval_hours" in status
    assert "last_run_at" in status
    assert "run_count" in status


def test_add_callback(curator):
    """测试添加回调"""
    callback_called = []

    def callback(report):
        callback_called.append(report)

    curator.add_evaluation_callback(callback)

    trajectory = {
        "trajectory_id": "test-callback",
        "steps": [
            {"type": "action", "step_id": 1, "data": {"tool_name": "tool1"}},
            {"type": "observation", "step_id": 2, "data": {"result": "ok", "success": True}},
        ]
    }

    asyncio.run(curator.process_trajectory(trajectory))

    assert len(callback_called) == 1


def test_enable_disable_learning(curator):
    """测试启用/禁用学习"""
    curator.enable_learning()
    assert curator._learning_enabled is True

    curator.disable_learning()
    assert curator._learning_enabled is False


def test_process_trajectory_with_learning(curator):
    """测试轨迹处理和自动学习"""
    class MockSkillWriter:
        async def write(self, skill):
            return True

    curator.skill_writer = MockSkillWriter()
    curator.enable_auto_learn = True

    trajectory = {
        "trajectory_id": "test-learn",
        "user_input": "搜索 Python 教程",
        "steps": [
            {"type": "thought", "step_id": 1, "data": {"reasoning": "搜索"}},
            {"type": "action", "step_id": 2, "data": {"tool_name": "web_search", "parameters": {"query": "Python"}}},
            {"type": "observation", "step_id": 3, "data": {"result": "成功", "success": True}},
        ]
    }

    skill = asyncio.run(curator.process_trajectory(trajectory))

    assert skill is not None
    assert skill.name in curator._learned_skills


def test_learn_from_feedback_no_recorder(curator):
    """测试无轨迹记录器时的反馈学习"""
    result = asyncio.run(curator.learn_from_feedback("traj-123", "good"))
    assert result is None


def test_get_learned_skills(curator):
    """测试获取已学习技能"""
    skills = curator.get_learned_skills()
    assert isinstance(skills, list)


def test_get_skill_by_name(curator):
    """测试按名称获取技能"""
    skill = curator.get_skill_by_name("nonexistent")
    assert skill is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
