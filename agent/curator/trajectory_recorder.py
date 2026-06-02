"""TrajectoryRecorder — Trajectory Recorder

Based on Hermes's trajectory format, records complete conversation history for:
1. Model training/fine-tuning data
2. Tool usage analysis
3. Self-improvement loop

Trajectory format (Hermes standard):
{
  "from": "gpt",
  "value": "<think>reasoning process\n<tool_call>{...}</tool_call>"
}
{
  "from": "tool",
  "value": "<tool_response>{...}</tool_response>"
}
"""

import json
import os
import time
from typing import Any, Dict, List, Optional

from common.logging_manager import get_decision_logger

logger = get_decision_logger("TrajectoryRecorder")


class TrajectoryRecorder:
    """轨迹记录器 - 记录完整对话历史用于训练和分析"""

    def __init__(self):
        self._trajectories: List[Dict[str, Any]] = []
        self._current_session_id: str = ""
        self._save_path: str = ""
        self._enabled: bool = True

    def initialize(self, session_id: str, save_path: str = "~/.handsome-agent/trajectories"):
        """初始化轨迹记录器"""
        self._current_session_id = session_id
        self._save_path = os.path.expanduser(save_path)
        os.makedirs(self._save_path, exist_ok=True)
        self._trajectories = []
        logger.info(f"TrajectoryRecorder initialized for session {session_id}")

    def enable(self):
        """启用轨迹记录"""
        self._enabled = True

    def disable(self):
        """禁用轨迹记录"""
        self._enabled = False

    def add_message(self, from_role: str, value: str, **kwargs):
        """添加轨迹消息"""
        if not self._enabled:
            return

        entry = {
            "from": from_role,
            "value": value,
            "timestamp": time.time(),
            **kwargs
        }
        self._trajectories.append(entry)
        logger.debug(f"Added trajectory entry: {from_role}")

    def add_system_message(self, content: str):
        """添加系统消息"""
        self.add_message("system", content)

    def add_human_message(self, content: str):
        """添加人类消息"""
        self.add_message("human", content)

    def add_gpt_message(self, content: str, reasoning: str = ""):
        """添加 GPT 消息（包含思考过程）"""
        if reasoning:
            content = f"<think>\n{reasoning}\n</think>\n{content}"
        elif "<think>" not in content:
            content = "<think>\n</think>\n" + content
        self.add_message("gpt", content)

    def add_tool_call(self, tool_name: str, arguments: Dict[str, Any], reasoning: str = ""):
        """添加工具调用"""
        tool_call_json = json.dumps({
            "name": tool_name,
            "arguments": arguments
        }, ensure_ascii=False)
        
        content = f"<think>\n{reasoning}\n</think>\n<tool_call>\n{tool_call_json}\n</tool_call>"
        self.add_message("gpt", content)

    def add_tool_response(self, tool_name: str, content: Any, tool_call_id: str = ""):
        """添加工具响应"""
        # 尝试解析为 JSON
        try:
            if isinstance(content, str) and content.strip().startswith(("{", "[")):
                content = json.loads(content)
        except json.JSONDecodeError:
            pass
        
        response = json.dumps({
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": content
        }, ensure_ascii=False)
        
        self.add_message("tool", f"<tool_response>\n{response}\n</tool_response>")

    def get_trajectory(self) -> List[Dict[str, Any]]:
        """获取当前轨迹"""
        return self._trajectories.copy()

    def save_trajectory(self, filename: Optional[str] = None) -> str:
        """保存轨迹到文件"""
        if not self._trajectories:
            logger.warning("No trajectory to save")
            return ""

        if not filename:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"trajectory_{self._current_session_id}_{timestamp}.jsonl"
        
        filepath = os.path.join(self._save_path, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                for entry in self._trajectories:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            
            logger.info(f"Trajectory saved to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save trajectory: {e}")
            return ""

    def clear(self):
        """清空轨迹"""
        self._trajectories = []

    def get_stats(self) -> Dict[str, Any]:
        """获取轨迹统计信息"""
        stats = {
            "total_entries": len(self._trajectories),
            "roles": {},
            "tool_calls": 0,
            "tool_responses": 0
        }
        
        for entry in self._trajectories:
            role = entry["from"]
            stats["roles"][role] = stats["roles"].get(role, 0) + 1
            
            if role == "gpt" and "<tool_call>" in entry["value"]:
                stats["tool_calls"] += 1
            elif role == "tool":
                stats["tool_responses"] += 1
        
        return stats


# 创建单例实例
trajectory_recorder = TrajectoryRecorder()
