#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trajectory Saving Module - Inspired by Hermes Agent

This module provides utilities for saving and loading agent trajectories,
which record the complete execution history including thoughts,
tool calls, and responses.
"""

import json
import os
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from common.logging_manager import get_decision_logger


class TrajectoryStatus(str, Enum):
    """轨迹状态枚举"""
    SUCCESS = "success"
    FAILURE = "failure"
    RUNNING = "running"
    CANCELLED = "cancelled"


@dataclass
class ExecutionStep:
    """执行步骤 - 记录 agent 执行轨迹中的单个步骤

    与 EvaluationStep 不同，ExecutionStep 用于轨迹的序列化和持久化，
    包含时间戳、元数据和工具调用结果等完整执行信息。
    """
    step_type: str  # 'thought', 'tool_call', 'response', 'observation'
    content: str
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    tool_name: Optional[str] = None
    tool_result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        result = {
            "step_type": self.step_type,
            "content": self.content,
            "timestamp": self.timestamp
        }

        if self.metadata:
            result["metadata"] = self.metadata
        if self.tool_name:
            result["tool_name"] = self.tool_name
        if self.tool_result:
            result["tool_result"] = self.tool_result

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionStep":
        """Create from dictionary."""
        return cls(
            step_type=data["step_type"],
            content=data["content"],
            timestamp=data["timestamp"],
            metadata=data.get("metadata", {}),
            tool_name=data.get("tool_name"),
            tool_result=data.get("tool_result")
        )

    @classmethod
    def from_message(cls, msg) -> "ExecutionStep":
        """从 Session.Message 转换"""
        return cls(
            step_type=msg.role,
            content=msg.content,
            timestamp=msg.timestamp,
            metadata=msg.metadata or {},
            tool_name=getattr(msg, 'tool_name', None),
            tool_result=getattr(msg, 'tool_result', None),
        )

    def to_hermes_entry(self) -> Dict[str, str]:
        """转换为 Hermes 格式 {from, value}"""
        return {
            "from": self.step_type,
            "value": self.content
        }


# 向后兼容别名
TrajectoryStep = ExecutionStep


@dataclass
class Trajectory:
    """Represents a complete execution trajectory."""
    id: str
    session_id: str
    messages: List[Dict[str, Any]] = field(default_factory=list)  # Hermes 格式消息
    steps: List[ExecutionStep] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_step(self, step: ExecutionStep):
        """Add a step to the trajectory."""
        self.steps.append(step)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "metadata": self.metadata,
            "messages": self.messages,  # 新增
            "steps": [step.to_dict() for step in self.steps]  # 保留兼容
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Trajectory":
        """Create from dictionary."""
        trajectory = cls(
            id=data["id"],
            session_id=data["session_id"],
            start_time=data["start_time"],
            end_time=data.get("end_time", 0.0),
            metadata=data.get("metadata", {}),
            messages=data.get("messages", []),  # 新增
        )

        for step_data in data.get("steps", []):
            trajectory.add_step(ExecutionStep.from_dict(step_data))

        return trajectory

    @classmethod
    def from_session(cls, session, metadata: Optional[Dict[str, Any]] = None) -> "Trajectory":
        """从 Session 转换"""
        timestamp = datetime.now().timestamp()
        if session is None:
            return cls(
                id=f"traj_{int(timestamp)}_none",
                session_id="none",
                messages=[],
                metadata=metadata or {},
                start_time=timestamp,
            )
        trajectory_id = f"traj_{int(timestamp)}_{session.session_id[:8]}"

        # 转换消息为 Hermes 格式
        messages = []
        for msg in session.get_history():
            step = ExecutionStep.from_message(msg)
            messages.append(step.to_hermes_entry())

        return cls(
            id=trajectory_id,
            session_id=session.session_id,
            messages=messages,
            metadata=metadata or {},
            start_time=timestamp,
        )

    def to_hermes_format(self) -> Dict[str, Any]:
        """转换为 Hermes 标准格式"""
        return {
            "conversations": self.messages,
            "timestamp": datetime.fromtimestamp(self.start_time).isoformat() if self.start_time else datetime.now().isoformat(),
            "model": self.metadata.get("model", "unknown"),
            "completed": self.metadata.get("completed", True),
        }


class TrajectoryManager:
    """
    Manages saving and loading of agent trajectories.
    
    Inspired by Hermes Agent's trajectory.py
    """
    
    def __init__(self, base_path: str = None):
        if base_path is None:
            base_path = os.path.join(os.path.expanduser("~"), ".agent_z", "trajectories")
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
    
    def _get_file_path(self, trajectory_id: str) -> str:
        """Get the file path for a trajectory."""
        return os.path.join(self.base_path, f"{trajectory_id}.jsonl")
    
    def save_trajectory(self, trajectory: Trajectory):
        """Save a trajectory to file.
        
        Deprecated: 使用 save() 方法代替，统一使用 JSONL 格式
        """
        self.save(trajectory)
    
    def load_trajectory(self, trajectory_id: str) -> Optional[Trajectory]:
        """Load a trajectory from file.
        
        Deprecated: 使用 load() 方法代替，统一从 JSONL 格式加载
        """
        return self.load(trajectory_id)
    
    def list_trajectories(self, session_id: Optional[str] = None) -> List[str]:
        """List all trajectory IDs.
        
        Deprecated: 使用 list() 方法代替，统一使用 .jsonl 扩展名
        """
        return self.list(session_id)
    
    def delete_trajectory(self, trajectory_id: str) -> bool:
        """
        Delete a trajectory file.
        
        Args:
            trajectory_id: The ID of the trajectory to delete
        
        Returns:
            True if deletion was successful
        """
        file_path = self._get_file_path(trajectory_id)
        
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        
        return False
    
    def create_trajectory(self, session_id: str) -> Trajectory:
        """
        Create a new trajectory.
        
        Args:
            session_id: The session ID
        
        Returns:
            New Trajectory object
        """
        timestamp = datetime.now().timestamp()
        trajectory_id = f"traj_{int(timestamp)}_{session_id[:8]}"
        
        return Trajectory(
            id=trajectory_id,
            session_id=session_id,
            start_time=timestamp,
            steps=[]
        )
    
    def get_recent_trajectories(self, limit: int = 10) -> List[Trajectory]:
        """
        Get the most recent trajectories.
        
        Args:
            limit: Maximum number of trajectories to return
        
        Returns:
            List of recent trajectories
        """
        traj_ids = self.list_trajectories()
        recent_ids = sorted(traj_ids, reverse=True)[:limit]
        
        trajectories = []
        for traj_id in recent_ids:
            traj = self.load_trajectory(traj_id)
            if traj:
                trajectories.append(traj)
        
        return trajectories
    
    def save(self, trajectory: Trajectory, metadata: Dict[str, Any] = None) -> str:
        """保存轨迹到 JSONL 文件（Hermes 风格）
        
        Args:
            trajectory: Trajectory 对象
            metadata: 额外的元数据
            
        Returns:
            保存的文件路径
        """
        import time
        
        # 生成文件名
        if not hasattr(trajectory, 'id') or not trajectory.id:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            trajectory.id = f"traj_{int(time.time())}_{trajectory.session_id[:8]}"
        
        filename = f"{trajectory.id}.jsonl"
        filepath = os.path.join(self.base_path, filename)
        
        # 构建条目
        entry = trajectory.to_hermes_format()
        
        # 合并元数据，确保 session_id 被包含
        merged_metadata = trajectory.metadata.copy()
        if metadata:
            merged_metadata.update(metadata)
        
        # 确保 session_id 始终在元数据中
        merged_metadata["session_id"] = trajectory.session_id
        
        entry["metadata"] = merged_metadata
        
        # 追加到 JSONL 文件
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        
        return filepath
    
    def load(self, trajectory_id: str) -> Optional[Trajectory]:
        """从 JSONL 文件加载轨迹
        
        Args:
            trajectory_id: 轨迹 ID
            
        Returns:
            Trajectory 对象，如果不存在返回 None
        """
        filename = f"{trajectory_id}.jsonl"
        filepath = os.path.join(self.base_path, filename)
        
        if not os.path.exists(filepath):
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        # 转换为 Trajectory 对象
                        return Trajectory(
                            id=trajectory_id,
                            session_id=data.get("metadata", {}).get("session_id", "unknown"),
                            messages=data.get("conversations", []),
                            metadata=data.get("metadata", {}),
                            start_time=datetime.fromisoformat(data["timestamp"]).timestamp() 
                                       if "timestamp" in data else 0.0,
                        )
        except (json.JSONDecodeError, OSError) as e:
            logger = get_decision_logger("TrajectoryManager")
            logger.error(f"Failed to load trajectory {trajectory_id}: {e}")
        
        return None
    
    def list(self, session_id: str = None) -> List[str]:
        """列出轨迹
        
        Args:
            session_id: 可选的会话 ID 过滤
            
        Returns:
            轨迹 ID 列表
        """
        trajectories = []
        
        for filename in os.listdir(self.base_path):
            if not filename.endswith(".jsonl"):
                continue
                
            traj_id = filename[:-6]  # Remove .jsonl
            
            # 如果指定了 session_id，过滤
            if session_id:
                filepath = os.path.join(self.base_path, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        first_line = f.readline()
                        if first_line.strip():
                            data = json.loads(first_line)
                            traj_session_id = data.get("metadata", {}).get("session_id", "")
                            if traj_session_id != session_id:
                                continue
                except (json.JSONDecodeError, OSError):
                    continue
        
            trajectories.append(traj_id)
        
        return sorted(trajectories, reverse=True)
