"""
轨迹记录器
记录每个 Thought/Action/Observation 循环
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import json
import uuid


class TrajectoryStatus(str, Enum):
    """轨迹状态"""
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


@dataclass
class ThoughtStep:
    """思考步骤"""
    reasoning: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    confidence: float = 1.0


@dataclass
class ActionStep:
    """行动步骤"""
    tool_name: str
    parameters: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ObservationStep:
    """观察步骤"""
    result: str
    success: bool = True
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Trajectory:
    """完整轨迹"""
    trajectory_id: str
    user_input: str
    final_response: str
    status: TrajectoryStatus
    steps: List[Dict[str, Any]] = field(default_factory=list)
    user_feedback: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    session_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Trajectory":
        """从字典创建"""
        return cls(**data)


class TrajectoryRecorder:
    """
    轨迹记录器
    
    严格参考 Hermes 的 TrajectoryRecorder 实现
    记录每个 Thought/Action/Observation 循环
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path or ".trajectories"
        self._current_trajectory: Optional[Trajectory] = None
        self._current_step: int = 0
        self._ensure_storage()
    
    def _ensure_storage(self) -> None:
        """确保存储目录存在"""
        import os
        os.makedirs(self.storage_path, exist_ok=True)
    
    def start_trajectory(self, user_input: str, session_id: Optional[str] = None) -> str:
        """
        开始记录新轨迹
        
        Args:
            user_input: 用户输入
            session_id: 会话 ID
            
        Returns:
            trajectory_id: 轨迹 ID
        """
        self._current_trajectory = Trajectory(
            trajectory_id=str(uuid.uuid4()),
            user_input=user_input,
            final_response="",
            status=TrajectoryStatus.IN_PROGRESS,
            steps=[],
            session_id=session_id,
        )
        self._current_step = 0
        return self._current_trajectory.trajectory_id
    
    def record_thought(self, reasoning: str, confidence: float = 1.0) -> None:
        """
        记录思考步骤
        
        Args:
            reasoning: 思考过程
            confidence: 置信度
        """
        if not self._current_trajectory:
            raise RuntimeError("No trajectory started. Call start_trajectory() first.")
        
        step = {
            "step_id": self._current_step,
            "type": "thought",
            "data": {
                "reasoning": reasoning,
                "confidence": confidence,
            },
            "timestamp": datetime.now().isoformat(),
        }
        self._current_trajectory.steps.append(step)
    
    def record_action(self, tool_name: str, parameters: Dict[str, Any]) -> None:
        """
        记录行动步骤
        
        Args:
            tool_name: 工具名称
            parameters: 工具参数
        """
        if not self._current_trajectory:
            raise RuntimeError("No trajectory started. Call start_trajectory() first.")
        
        step = {
            "step_id": self._current_step,
            "type": "action",
            "data": {
                "tool_name": tool_name,
                "parameters": parameters,
            },
            "timestamp": datetime.now().isoformat(),
        }
        self._current_trajectory.steps.append(step)
    
    def record_observation(self, result: str, success: bool = True, error: Optional[str] = None) -> None:
        """
        记录观察步骤
        
        Args:
            result: 执行结果
            success: 是否成功
            error: 错误信息
        """
        if not self._current_trajectory:
            raise RuntimeError("No trajectory started. Call start_trajectory() first.")
        
        step = {
            "step_id": self._current_step,
            "type": "observation",
            "data": {
                "result": result,
                "success": success,
                "error": error,
            },
            "timestamp": datetime.now().isoformat(),
        }
        self._current_trajectory.steps.append(step)
        self._current_step += 1
    
    def end_trajectory(
        self, 
        final_response: str, 
        status: TrajectoryStatus = TrajectoryStatus.SUCCESS
    ) -> Trajectory:
        """
        结束轨迹记录
        
        Args:
            final_response: 最终响应
            status: 状态
            
        Returns:
            Trajectory: 完整轨迹
        """
        if not self._current_trajectory:
            raise RuntimeError("No trajectory started. Call start_trajectory() first.")
        
        self._current_trajectory.final_response = final_response
        self._current_trajectory.status = status
        self._current_trajectory.updated_at = datetime.now().isoformat()
        
        trajectory = self._current_trajectory
        self._current_trajectory = None
        self._current_step = 0
        
        self._save_trajectory(trajectory)
        
        return trajectory
    
    def _save_trajectory(self, trajectory: Trajectory) -> None:
        """保存轨迹到文件"""
        import os
        filename = f"{trajectory.trajectory_id}.json"
        filepath = os.path.join(self.storage_path, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(trajectory.to_dict(), f, ensure_ascii=False, indent=2)
    
    def load_trajectory(self, trajectory_id: str) -> Optional[Trajectory]:
        """加载轨迹"""
        import os
        filename = f"{trajectory_id}.json"
        filepath = os.path.join(self.storage_path, filename)
        
        if not os.path.exists(filepath):
            return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return Trajectory.from_dict(data)
    
    def get_recent_trajectories(self, limit: int = 10) -> List[Trajectory]:
        """获取最近的轨迹"""
        import os
        trajectories = []
        
        for filename in os.listdir(self.storage_path):
            if filename.endswith('.json'):
                filepath = os.path.join(self.storage_path, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    trajectories.append(Trajectory.from_dict(data))
        
        trajectories.sort(key=lambda t: t.created_at, reverse=True)
        return trajectories[:limit]
    
    def get_successful_trajectories(self, limit: int = 10) -> List[Trajectory]:
        """获取成功的轨迹（用于技能提取）"""
        all_trajectories = self.get_recent_trajectories(limit * 2)
        return [t for t in all_trajectories if t.status == TrajectoryStatus.SUCCESS][:limit]
    
    def add_feedback(self, trajectory_id: str, feedback: str) -> bool:
        """
        添加用户反馈
        
        Args:
            trajectory_id: 轨迹 ID
            feedback: 反馈内容 (good/bad/修改建议等)
            
        Returns:
            bool: 是否成功
        """
        trajectory = self.load_trajectory(trajectory_id)
        if not trajectory:
            return False
        
        trajectory.user_feedback = feedback
        trajectory.updated_at = datetime.now().isoformat()
        self._save_trajectory(trajectory)
        
        return True
    
    def mark_trajectory(self, trajectory_id: str, status: TrajectoryStatus) -> bool:
        """标记轨迹状态"""
        trajectory = self.load_trajectory(trajectory_id)
        if not trajectory:
            return False
        
        trajectory.status = status
        trajectory.updated_at = datetime.now().isoformat()
        self._save_trajectory(trajectory)
        
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        trajectories = self.get_recent_trajectories(100)
        
        total = len(trajectories)
        success = sum(1 for t in trajectories if t.status == TrajectoryStatus.SUCCESS)
        failure = sum(1 for t in trajectories if t.status == TrajectoryStatus.FAILURE)
        partial = sum(1 for t in trajectories if t.status == TrajectoryStatus.PARTIAL)
        with_feedback = sum(1 for t in trajectories if t.user_feedback)
        
        return {
            "total_trajectories": total,
            "success_count": success,
            "failure_count": failure,
            "partial_count": partial,
            "with_feedback_count": with_feedback,
            "success_rate": success / total if total > 0 else 0,
        }