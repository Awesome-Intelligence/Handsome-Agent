"""测试自改进引擎"""
import pytest
import tempfile
import os
from unittest.mock import Mock
from core.self_improvement import SelfImprovementEngine
from core.trajectory_recorder import TrajectoryRecorder


class TestSelfImprovementEngine:
    """测试自改进引擎"""

    def test_evaluate_trajectory_empty(self):
        """测试评估空轨迹"""
        recorder = TrajectoryRecorder()
        engine = SelfImprovementEngine(recorder)
        
        result = engine.evaluate_trajectory([])
        
        assert result["quality_score"] == 0
        assert result["completion_status"] == "empty"

    def test_evaluate_trajectory_basic(self):
        """测试评估基本轨迹"""
        recorder = TrajectoryRecorder()
        engine = SelfImprovementEngine(recorder)
        
        trajectory = [
            {"from": "system", "value": "system message"},
            {"from": "human", "value": "Hello"},
            {"from": "gpt", "value": "<think>reasoning</think>Hi!"}
        ]
        
        result = engine.evaluate_trajectory(trajectory)
        
        assert result["quality_score"] > 0
        assert result["completion_status"] == "completed"

    def test_evaluate_trajectory_with_tool_call(self):
        """测试评估包含工具调用的轨迹"""
        recorder = TrajectoryRecorder()
        engine = SelfImprovementEngine(recorder)
        
        trajectory = [
            {"from": "human", "value": "search Python"},
            {"from": "gpt", "value": "<think>need to search</think><tool_call>{\"name\": \"web_search\", \"arguments\": {\"query\": \"Python\"}}</tool_call>"},
            {"from": "tool", "value": "<tool_response>{\"content\": \"results\"}</tool_response>"},
            {"from": "gpt", "value": "<think>got results</think>Here are results"}
        ]
        
        result = engine.evaluate_trajectory(trajectory)
        
        assert result["stats"]["tool_calls"] == 1
        assert result["stats"]["successful_calls"] == 1
        assert result["tool_effectiveness"] == 100

    def test_synthesize_skill_low_score(self):
        """测试低分轨迹不合成技能"""
        recorder = TrajectoryRecorder()
        engine = SelfImprovementEngine(recorder)
        
        trajectory = [
            {"from": "human", "value": "Hi"},
            {"from": "gpt", "value": "<think></think>Hello"}
        ]
        
        evaluation = {"quality_score": 50}
        skill = engine.synthesize_skill(trajectory, evaluation)
        
        assert skill is None

    def test_synthesize_skill_high_score(self):
        """测试高分轨迹合成技能"""
        recorder = TrajectoryRecorder()
        engine = SelfImprovementEngine(recorder)
        
        trajectory = [
            {"from": "human", "value": "search Python"},
            {"from": "gpt", "value": "<think>good reasoning</think><tool_call>{\"name\": \"web_search\", \"arguments\": {\"query\": \"Python\"}}</tool_call>"},
            {"from": "tool", "value": "<tool_response>{\"content\": \"results\"}</tool_response>"},
            {"from": "gpt", "value": "<think>good reasoning</think>Results"}
        ]
        
        evaluation = {"quality_score": 85}
        skill = engine.synthesize_skill(trajectory, evaluation)
        
        assert skill is not None
        assert "tool_sequence" in skill
        assert len(skill["tool_sequence"]) == 1

    def test_persist_skill(self):
        """测试持久化技能"""
        recorder = TrajectoryRecorder()
        engine = SelfImprovementEngine(recorder)
        
        mock_skill_manager = Mock()
        mock_skill_manager.save_skill_definition.return_value = True
        engine.set_skill_manager(mock_skill_manager)
        
        skill_def = {"id": "test_skill", "name": "Test"}
        result = engine.persist_skill(skill_def)
        
        assert result == True
        mock_skill_manager.save_skill_definition.assert_called_once()

    def test_run_improvement_cycle(self):
        """测试运行自改进循环"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = TrajectoryRecorder()
            recorder.initialize("test_session", save_path=tmpdir)
            
            recorder.add_human_message("Hello")
            recorder.add_gpt_message("<think>reasoning</think>Hi!", reasoning="reasoning")
            
            engine = SelfImprovementEngine(recorder)
            result = engine.run_improvement_cycle()
            
            assert result["status"] == "completed"
            assert "evaluation" in result
            assert "trajectory_saved" in result

    def test_generate_training_data(self):
        """测试生成训练数据"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = TrajectoryRecorder()
            recorder.initialize("test_session", save_path=tmpdir)
            
            recorder.add_human_message("Hello")
            recorder.add_gpt_message("Hi")
            
            engine = SelfImprovementEngine(recorder)
            filepath = engine.generate_training_data(output_dir=tmpdir)
            
            assert os.path.exists(filepath)