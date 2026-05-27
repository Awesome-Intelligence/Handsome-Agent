"""Curator 测试"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from brain.trajectory import TrajectoryStatus
from brain_curator.curator import Curator
from brain_curator.synthesizer import SynthesizedSkill


class TestCurator:
    """Curator 测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.mock_recorder = MagicMock()
        self.mock_writer = MagicMock()
        self.curator = Curator(
            trajectory_recorder=self.mock_recorder,
            skill_writer=self.mock_writer,
            enable_auto_learn=True,
            min_confidence_threshold=0.7,
        )
    
    def test_curator_initialization(self):
        """测试 Curator 初始化"""
        assert self.curator.enable_auto_learn is True
        assert self.curator.min_confidence_threshold == 0.7
        assert len(self.curator._learned_skills) == 0
    
    def test_enable_disable_learning(self):
        """测试启用/禁用学习"""
        self.curator.disable_learning()
        assert self.curator._learning_enabled is False
        
        self.curator.enable_learning()
        assert self.curator._learning_enabled is True
    
    def test_get_learned_skills(self):
        """测试获取已学习技能"""
        skills = self.curator.get_learned_skills()
        assert isinstance(skills, list)
        assert len(skills) == 0
    
    def test_get_skill_by_name(self):
        """测试根据名称获取技能"""
        skill = self.curator.get_skill_by_name("nonexistent")
        assert skill is None


class TestCuratorProcess:
    """Curator 处理轨迹测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.mock_recorder = MagicMock()
        self.mock_writer = MagicMock()
        self.curator = Curator(
            trajectory_recorder=self.mock_recorder,
            skill_writer=self.mock_writer,
            enable_auto_learn=True,
        )
    
    @pytest.mark.asyncio
    async def test_process_trajectory_failure(self):
        """测试处理失败轨迹"""
        trajectory = {
            "trajectory_id": "test-456",
            "user_input": "执行任务",
            "steps": [
                {"step_id": 0, "type": "thought", "data": {"reasoning": "思考", "confidence": 0.5}},
                {"step_id": 0, "type": "observation", "data": {"result": "失败", "success": False}},
            ],
            "status": "failure",
        }
        
        result = await self.curator.process_trajectory(trajectory)
        
        assert result is None


class TestCuratorEvaluate:
    """Curator 评估测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.mock_recorder = MagicMock()
        self.mock_writer = MagicMock()
        self.curator = Curator(
            trajectory_recorder=self.mock_recorder,
            skill_writer=self.mock_writer,
        )
    
    @pytest.mark.asyncio
    async def test_evaluate_success_trajectory(self):
        """测试评估成功轨迹"""
        trajectory = {
            "trajectory_id": "test-success",
            "user_input": "测试",
            "steps": [
                {"step_id": 0, "type": "thought", "data": {"reasoning": "思考"}},
                {"step_id": 0, "type": "action", "data": {"tool_name": "test_tool"}},
                {"step_id": 0, "type": "observation", "data": {"result": "成功", "success": True}},
            ],
        }
        
        report = await self.curator.evaluate(trajectory)
        
        assert report.trajectory_id == "test-success"
        assert report.success_rate > 0
    
    @pytest.mark.asyncio
    async def test_evaluate_failure_trajectory(self):
        """测试评估失败轨迹"""
        trajectory = {
            "trajectory_id": "test-failure",
            "user_input": "测试",
            "steps": [
                {"step_id": 0, "type": "observation", "data": {"result": "失败", "success": False}},
            ],
        }
        
        report = await self.curator.evaluate(trajectory)
        
        assert report.overall_result.value in ["failure", "error"]


class TestSynthesizedSkill:
    """SynthesizedSkill 测试"""
    
    def test_skill_creation(self):
        """测试技能创建"""
        skill = SynthesizedSkill(
            name="test_skill",
            description="测试技能",
            trigger_patterns=["test", "测试"],
            action_template="echo test",
            confidence=0.9,
        )
        
        assert skill.name == "test_skill"
        assert skill.confidence == 0.9
        assert "test" in skill.trigger_patterns