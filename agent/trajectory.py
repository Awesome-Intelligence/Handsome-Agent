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


@dataclass
class TrajectoryStep:
    """Represents a single step in the agent's execution trajectory."""
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
    def from_dict(cls, data: Dict[str, Any]) -> "TrajectoryStep":
        """Create from dictionary."""
        return cls(
            step_type=data["step_type"],
            content=data["content"],
            timestamp=data["timestamp"],
            metadata=data.get("metadata", {}),
            tool_name=data.get("tool_name"),
            tool_result=data.get("tool_result")
        )


@dataclass
class Trajectory:
    """Represents a complete execution trajectory."""
    id: str
    session_id: str
    steps: List[TrajectoryStep] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_step(self, step: TrajectoryStep):
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
            "steps": [step.to_dict() for step in self.steps]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Trajectory":
        """Create from dictionary."""
        trajectory = cls(
            id=data["id"],
            session_id=data["session_id"],
            start_time=data["start_time"],
            end_time=data.get("end_time", 0.0),
            metadata=data.get("metadata", {})
        )
        
        for step_data in data.get("steps", []):
            trajectory.add_step(TrajectoryStep.from_dict(step_data))
        
        return trajectory


class TrajectoryManager:
    """
    Manages saving and loading of agent trajectories.
    
    Inspired by Hermes Agent's trajectory.py
    """
    
    def __init__(self, base_path: str = "./trajectories"):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
    
    def _get_file_path(self, trajectory_id: str) -> str:
        """Get the file path for a trajectory."""
        return os.path.join(self.base_path, f"{trajectory_id}.json")
    
    def save_trajectory(self, trajectory: Trajectory):
        """Save a trajectory to file."""
        file_path = self._get_file_path(trajectory.id)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(trajectory.to_dict(), f, ensure_ascii=False, indent=2)
    
    def load_trajectory(self, trajectory_id: str) -> Optional[Trajectory]:
        """Load a trajectory from file."""
        file_path = self._get_file_path(trajectory_id)
        
        if not os.path.exists(file_path):
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return Trajectory.from_dict(data)
    
    def list_trajectories(self, session_id: Optional[str] = None) -> List[str]:
        """
        List all trajectory IDs.
        
        Args:
            session_id: Optional filter by session ID
        
        Returns:
            List of trajectory IDs
        """
        trajectories = []
        
        for filename in os.listdir(self.base_path):
            if filename.endswith(".json"):
                traj_id = filename[:-5]  # Remove .json
                trajectories.append(traj_id)
        
        return sorted(trajectories)
    
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
