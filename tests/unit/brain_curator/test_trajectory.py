"""TrajectoryRecorder 测试"""
import pytest
import tempfile
import shutil
from brain.trajectory import TrajectoryRecorder, Trajectory, TrajectoryStatus


class TestTrajectoryRecorder:
    """TrajectoryRecorder 测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.recorder = TrajectoryRecorder(storage_path=self.temp_dir)
    
    def teardown_method(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_start_trajectory(self):
        """测试开始轨迹"""
        trajectory_id = self.recorder.start_trajectory("测试输入", "session123")
        
        assert trajectory_id is not None
        assert len(trajectory_id) > 0
        assert self.recorder._current_trajectory is not None
        assert self.recorder._current_trajectory.user_input == "测试输入"
    
    def test_record_thought(self):
        """测试记录思考步骤"""
        self.recorder.start_trajectory("测试输入")
        
        self.recorder.record_thought("这是一个思考过程", confidence=0.9)
        
        assert len(self.recorder._current_trajectory.steps) == 1
        step = self.recorder._current_trajectory.steps[0]
        assert step["type"] == "thought"
        assert step["data"]["reasoning"] == "这是一个思考过程"
        assert step["data"]["confidence"] == 0.9
    
    def test_record_action(self):
        """测试记录行动步骤"""
        self.recorder.start_trajectory("测试输入")
        
        self.recorder.record_action("file_read", {"path": "test.txt"})
        
        assert len(self.recorder._current_trajectory.steps) == 1
        step = self.recorder._current_trajectory.steps[0]
        assert step["type"] == "action"
        assert step["data"]["tool_name"] == "file_read"
    
    def test_record_observation(self):
        """测试记录观察步骤"""
        self.recorder.start_trajectory("测试输入")
        
        self.recorder.record_observation("执行结果", success=True)
        
        assert len(self.recorder._current_trajectory.steps) == 1
        step = self.recorder._current_trajectory.steps[0]
        assert step["type"] == "observation"
        assert step["data"]["result"] == "执行结果"
        assert step["data"]["success"] is True
    
    def test_end_trajectory(self):
        """测试结束轨迹"""
        trajectory_id = self.recorder.start_trajectory("测试输入")
        
        trajectory = self.recorder.end_trajectory(
            final_response="测试响应",
            status=TrajectoryStatus.SUCCESS
        )
        
        assert trajectory is not None
        assert trajectory.user_input == "测试输入"
        assert trajectory.final_response == "测试响应"
        assert trajectory.status == TrajectoryStatus.SUCCESS
    
    def test_save_and_load_trajectory(self):
        """测试轨迹保存和加载"""
        trajectory_id = self.recorder.start_trajectory("测试输入")
        self.recorder.record_thought("思考")
        self.recorder.end_trajectory("响应", TrajectoryStatus.SUCCESS)
        
        loaded = self.recorder.load_trajectory(trajectory_id)
        
        assert loaded is not None
        assert loaded.user_input == "测试输入"
        assert loaded.final_response == "响应"
    
    def test_get_recent_trajectories(self):
        """测试获取最近轨迹"""
        for i in range(5):
            self.recorder.start_trajectory(f"输入{i}")
            self.recorder.end_trajectory(f"响应{i}", TrajectoryStatus.SUCCESS)
        
        recent = self.recorder.get_recent_trajectories(limit=3)
        
        assert len(recent) == 3
    
    def test_add_feedback(self):
        """测试添加反馈"""
        trajectory_id = self.recorder.start_trajectory("测试输入")
        self.recorder.end_trajectory("响应", TrajectoryStatus.SUCCESS)
        
        success = self.recorder.add_feedback(trajectory_id, "good")
        
        assert success is True
        
        loaded = self.recorder.load_trajectory(trajectory_id)
        assert loaded.user_feedback == "good"
    
    def test_get_statistics(self):
        """测试获取统计信息"""
        self.recorder.start_trajectory("输入1")
        self.recorder.end_trajectory("响应1", TrajectoryStatus.SUCCESS)
        
        self.recorder.start_trajectory("输入2")
        self.recorder.end_trajectory("响应2", TrajectoryStatus.FAILURE)
        
        stats = self.recorder.get_statistics()
        
        assert stats["total_trajectories"] == 2
        assert stats["success_count"] == 1
        assert stats["failure_count"] == 1
        assert stats["success_rate"] == 0.5


class TestTrajectory:
    """Trajectory 数据类测试"""
    
    def test_to_dict(self):
        """测试转换为字典"""
        trajectory = Trajectory(
            trajectory_id="test-123",
            user_input="测试",
            final_response="响应",
            status=TrajectoryStatus.SUCCESS,
        )
        
        data = trajectory.to_dict()
        
        assert data["trajectory_id"] == "test-123"
        assert data["user_input"] == "测试"
        assert data["status"] == TrajectoryStatus.SUCCESS
    
    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "trajectory_id": "test-123",
            "user_input": "测试",
            "final_response": "响应",
            "status": "success",
            "steps": [],
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }
        
        trajectory = Trajectory.from_dict(data)
        
        assert trajectory.trajectory_id == "test-123"
        assert trajectory.user_input == "测试"
        assert trajectory.status == TrajectoryStatus.SUCCESS