"""测试轨迹记录器"""
import pytest
import tempfile
import json
import os
from core.trajectory_recorder import TrajectoryRecorder


class TestTrajectoryRecorder:
    """测试轨迹记录器"""

    def test_initialize(self):
        """测试初始化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = TrajectoryRecorder()
            recorder.initialize("test_session", save_path=tmpdir)
            
            assert recorder._current_session_id == "test_session"
            assert recorder._save_path == tmpdir

    def test_add_messages(self):
        """测试添加消息"""
        recorder = TrajectoryRecorder()
        recorder.initialize("test_session")
        
        recorder.add_system_message("system message")
        recorder.add_human_message("human message")
        recorder.add_gpt_message("gpt message", reasoning="thinking")
        
        trajectory = recorder.get_trajectory()
        assert len(trajectory) == 3
        assert trajectory[0]["from"] == "system"
        assert trajectory[1]["from"] == "human"
        assert trajectory[2]["from"] == "gpt"
        assert "<think>" in trajectory[2]["value"]

    def test_add_tool_call(self):
        """测试添加工具调用"""
        recorder = TrajectoryRecorder()
        recorder.initialize("test_session")
        
        recorder.add_tool_call(
            tool_name="web_search",
            arguments={"query": "test"},
            reasoning="need to search"
        )
        
        trajectory = recorder.get_trajectory()
        assert len(trajectory) == 1
        assert "<tool_call>" in trajectory[0]["value"]
        assert "<think>" in trajectory[0]["value"]

    def test_add_tool_response(self):
        """测试添加工具响应"""
        recorder = TrajectoryRecorder()
        recorder.initialize("test_session")
        
        recorder.add_tool_response(
            tool_name="web_search",
            content={"results": []},
            tool_call_id="123"
        )
        
        trajectory = recorder.get_trajectory()
        assert len(trajectory) == 1
        assert trajectory[0]["from"] == "tool"
        assert "<tool_response>" in trajectory[0]["value"]

    def test_save_trajectory(self):
        """测试保存轨迹"""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = TrajectoryRecorder()
            recorder.initialize("test_session", save_path=tmpdir)
            
            recorder.add_human_message("Hello")
            recorder.add_gpt_message("Hi")
            
            filepath = recorder.save_trajectory()
            
            assert os.path.exists(filepath)
            
            # 读取并验证
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                assert len(lines) == 2
                entry = json.loads(lines[0])
                assert entry["from"] == "human"

    def test_get_stats(self):
        """测试获取统计信息"""
        recorder = TrajectoryRecorder()
        recorder.initialize("test_session")
        
        recorder.add_human_message("Hello")
        recorder.add_gpt_message("response")
        recorder.add_tool_call("web_search", {})
        
        stats = recorder.get_stats()
        assert stats["total_entries"] == 3
        assert stats["roles"]["human"] == 1
        assert stats["roles"]["gpt"] == 2
        assert stats["tool_calls"] == 1

    def test_clear(self):
        """测试清空轨迹"""
        recorder = TrajectoryRecorder()
        recorder.initialize("test_session")
        
        recorder.add_human_message("Hello")
        assert len(recorder.get_trajectory()) == 1
        
        recorder.clear()
        assert len(recorder.get_trajectory()) == 0

    def test_disable(self):
        """测试禁用记录"""
        recorder = TrajectoryRecorder()
        recorder.initialize("test_session")
        recorder.disable()
        
        recorder.add_human_message("Hello")
        assert len(recorder.get_trajectory()) == 0