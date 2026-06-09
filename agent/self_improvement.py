"""SelfImprovementEngine — Self-Improvement Engine

Based on Hermes's self-improvement mechanism, implements:
1. Trajectory Evaluation - Analyze conversation quality and tool usage effectiveness
2. Skill Synthesis - Extract new skills from successful conversations
3. Skill Persistence - Save synthesized skills to skill library

Self-improvement loop:
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Trajectory     │ ──▶ │  Evaluation     │ ──▶ │  Skill Synthesis│
│  Recording      │     │  Analysis       │     │                 │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                          │
                                                          ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Persistence    │ ◀── │  Fine-tuning     │ ◀── │  Data Preparation│
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
"""

import json
import os
import time
from typing import Any, Dict, List, Optional

from .trajectory_recorder import TrajectoryRecorder, trajectory_recorder
from common.logging_manager import get_decision_logger

logger = get_decision_logger("SelfImprovementEngine")


class SelfImprovementEngine:
    """自改进引擎 - 实现越用越好用的核心机制"""

    def __init__(self, trajectory_recorder: TrajectoryRecorder):
        self._recorder = trajectory_recorder
        self._skill_manager = None
        self._enabled = True

    def set_skill_manager(self, skill_manager):
        """设置技能管理器"""
        self._skill_manager = skill_manager

    def enable(self):
        """启用以改进"""
        self._enabled = True

    def disable(self):
        """禁用以改进"""
        self._enabled = False

    def evaluate_trajectory(self, trajectory: List[Dict[str, Any]]) -> Dict[str, Any]:
        """评估轨迹质量
        
        返回评估结果：
        - quality_score: 0-100 分数
        - tool_effectiveness: 工具使用效果
        - reasoning_quality: 推理质量
        - completion_status: 完成状态
        - suggestions: 改进建议
        """
        if not trajectory:
            return {
                "quality_score": 0,
                "tool_effectiveness": 0,
                "reasoning_quality": 0,
                "completion_status": "empty",
                "suggestions": []
            }

        score = 0
        tool_effectiveness = 0
        reasoning_quality = 0
        suggestions = []
        
        tool_calls = 0
        successful_calls = 0
        has_reasoning = 0
        total_entries = len(trajectory)
        
        for entry in trajectory:
            role = entry["from"]
            value = entry["value"]
            
            # 评估推理质量
            if role == "gpt" and "<think>" in value:
                has_reasoning += 1
                # 检查推理内容长度
                think_match = value.split("<think>")[1].split("</think>")[0] if "<think>" in value else ""
                if len(think_match.strip()) > 20:
                    reasoning_quality += 1
            
            # 评估工具使用
            if role == "gpt" and "<tool_call>" in value:
                tool_calls += 1
            
            # 评估工具响应
            if role == "tool" and "<tool_response>" in value:
                successful_calls += 1
                # 检查响应中是否有成功标识
                if "success" in value.lower():
                    tool_effectiveness += 1
        
        # 计算分数
        if total_entries > 0:
            reasoning_quality = min(100, (has_reasoning / total_entries) * 100)
        
        if tool_calls > 0:
            tool_effectiveness = min(100, (successful_calls / tool_calls) * 100)
        else:
            tool_effectiveness = 50  # 默认中等
        
        # 综合评分
        quality_score = int((reasoning_quality * 0.4 + tool_effectiveness * 0.4 + 10) / 10 * 10)
        
        # 生成改进建议
        if reasoning_quality < 50:
            suggestions.append("增加详细的推理过程可以提高响应质量")
        
        if tool_effectiveness < 50:
            suggestions.append("优化工具调用参数可以提高执行成功率")
        
        # 判断完成状态
        last_entry = trajectory[-1] if trajectory else {}
        completion_status = "completed" if (last_entry.get("from") == "gpt" and "<tool_call>" not in last_entry.get("value", "")) else "in_progress"
        
        return {
            "quality_score": quality_score,
            "tool_effectiveness": tool_effectiveness,
            "reasoning_quality": reasoning_quality,
            "completion_status": completion_status,
            "suggestions": suggestions,
            "stats": {
                "total_entries": total_entries,
                "tool_calls": tool_calls,
                "successful_calls": successful_calls,
                "reasoning_segments": has_reasoning
            }
        }

    def synthesize_skill(self, trajectory: List[Dict[str, Any]], evaluation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """从轨迹中合成新技能
        
        如果评估分数足够高，从成功的对话中提取可复用的技能。
        """
        if evaluation["quality_score"] < 70:
            logger.info(f"Trajectory quality score {evaluation['quality_score']} < 70, skipping skill synthesis")
            return None

        # 提取工具调用序列
        tool_calls = []
        for entry in trajectory:
            if entry["from"] == "gpt" and "<tool_call>" in entry["value"]:
                # 解析工具调用
                start = entry["value"].find("<tool_call>") + len("<tool_call>")
                end = entry["value"].find("</tool_call>")
                if start < end:
                    try:
                        tool_call_json = entry["value"][start:end].strip()
                        tool_call = json.loads(tool_call_json)
                        tool_calls.append(tool_call)
                    except json.JSONDecodeError:
                        pass
        
        if not tool_calls:
            logger.info("No tool calls found in trajectory")
            return None

        # 合成技能元数据
        skill_name = f"auto_synthesized_{int(time.time())}"
        description = "自动从成功对话轨迹中合成的技能"
        
        # 提取参数模式
        parameters = {}
        for call in tool_calls:
            tool_name = call.get("name", "")
            args = call.get("arguments", {})
            for key, value in args.items():
                if key not in parameters:
                    parameters[key] = {
                        "type": type(value).__name__,
                        "examples": []
                    }
                if value not in parameters[key]["examples"]:
                    parameters[key]["examples"].append(value)
        
        # 生成技能定义
        skill_def = {
            "id": skill_name,
            "name": skill_name,
            "description": description,
            "category": "auto-synthesized",
            "version": "1.0.0",
            "parameters": [
                {
                    "name": key,
                    "type": param["type"],
                    "description": f"参数 {key}",
                    "examples": param["examples"][:3]
                }
                for key, param in parameters.items()
            ],
            "tool_sequence": tool_calls,
            "source_trajectory_length": len(trajectory),
            "evaluation_score": evaluation["quality_score"],
            "created_at": time.time(),
            "status": "draft"
        }
        
        logger.info(f"Synthesized new skill: {skill_name} with {len(tool_calls)} tool calls")
        return skill_def

    def persist_skill(self, skill_def: Dict[str, Any]) -> bool:
        """持久化合成的技能"""
        if not self._skill_manager:
            logger.error("Skill manager not set")
            return False
        
        try:
            # 使用技能管理器保存技能
            self._skill_manager.save_skill_definition(skill_def)
            logger.info(f"Skill persisted: {skill_def['id']}")
            return True
        except Exception as e:
            logger.error(f"Failed to persist skill: {e}")
            return False

    def run_improvement_cycle(self) -> Dict[str, Any]:
        """运行完整的自改进循环"""
        if not self._enabled:
            return {"status": "disabled", "message": "Self-improvement is disabled"}
        
        # 获取当前轨迹
        trajectory = self._recorder.get_trajectory()
        
        if not trajectory:
            return {"status": "no_data", "message": "No trajectory data available"}
        
        # 1. 评估轨迹
        evaluation = self.evaluate_trajectory(trajectory)
        logger.info(f"Trajectory evaluation score: {evaluation['quality_score']}")
        
        # 2. 如果质量足够高，合成技能
        synthesized_skill = None
        if evaluation["quality_score"] >= 70:
            synthesized_skill = self.synthesize_skill(trajectory, evaluation)
        
        # 3. 持久化技能
        persisted = False
        if synthesized_skill:
            persisted = self.persist_skill(synthesized_skill)
        
        # 4. 保存轨迹用于后续训练
        trajectory_path = self._recorder.save_trajectory()
        
        return {
            "status": "completed",
            "evaluation": evaluation,
            "synthesized_skill": synthesized_skill,
            "persisted": persisted,
            "trajectory_saved": trajectory_path,
            "timestamp": time.time()
        }

    def generate_training_data(self, output_dir: str = "~/.handsome_agent/training_data") -> str:
        """生成训练数据（用于微调模型）"""
        output_path = os.path.expanduser(output_dir)
        os.makedirs(output_path, exist_ok=True)
        
        trajectory = self._recorder.get_trajectory()
        if not trajectory:
            return ""
        
        # 转换为训练格式
        training_data = []
        for i in range(len(trajectory) - 1):
            current = trajectory[i]
            next_entry = trajectory[i + 1]
            
            # 创建训练样本
            sample = {
                "input": current["value"],
                "output": next_entry["value"],
                "from": current["from"],
                "to": next_entry["from"],
                "timestamp": current["timestamp"]
            }
            training_data.append(sample)
        
        # 保存训练数据
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"training_data_{timestamp}.json"
        filepath = os.path.join(output_path, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(training_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Training data saved to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save training data: {e}")
            return ""


# 创建单例实例
self_improvement_engine = SelfImprovementEngine(trajectory_recorder)
