"""
轨迹评估器
评估每次 Tool Call 的效果
"""

from dataclasses import dataclass
from typing import List, Dict, Any
from enum import Enum


class EvaluationResult(str, Enum):
    """评估结果"""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    ERROR = "error"


@dataclass
class TrajectoryStep:
    """轨迹步骤"""
    step_id: int
    thought: str
    action: str
    observation: str
    result: str
    success: bool


@dataclass
class EvaluationReport:
    """评估报告"""
    trajectory_id: str
    overall_result: EvaluationResult
    success_rate: float
    steps: List[TrajectoryStep]
    suggestions: List[str]
    metrics: Dict[str, Any]


class TrajectoryEvaluator:
    """轨迹评估器"""
    
    def __init__(self):
        self._history: List[Dict[str, Any]] = []
    
    async def evaluate(self, trajectory: List[Dict[str, Any]]) -> EvaluationReport:
        """
        评估轨迹
        
        评估维度：
        1. 每一步的成功率
        2. 整体完成度
        3. 效率评估
        4. 改进建议
        """
        steps = []
        success_count = 0
        
        for i, step in enumerate(trajectory):
            step_result = self._evaluate_step(step)
            success = step_result.get("success", False)
            if success:
                success_count += 1
            
            steps.append(TrajectoryStep(
                step_id=i,
                thought=step.get("thought", ""),
                action=step.get("action", ""),
                observation=step.get("observation", ""),
                result=step_result.get("result", ""),
                success=success,
            ))
        
        success_rate = success_count / len(trajectory) if trajectory else 0.0
        
        # 确定整体结果
        if success_rate == 1.0:
            overall = EvaluationResult.SUCCESS
        elif success_rate > 0.5:
            overall = EvaluationResult.PARTIAL_SUCCESS
        else:
            overall = EvaluationResult.FAILURE
        
        # 生成建议
        suggestions = self._generate_suggestions(steps)
        
        return EvaluationReport(
            trajectory_id=trajectory[0].get("trajectory_id", "unknown") if trajectory else "unknown",
            overall_result=overall,
            success_rate=success_rate,
            steps=steps,
            suggestions=suggestions,
            metrics={
                "total_steps": len(trajectory),
                "success_steps": success_count,
                "efficiency": self._calculate_efficiency(trajectory),
            }
        )
    
    def _evaluate_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """评估单个步骤"""
        # 简化实现：检查是否有错误标记
        result = step.get("result", "")
        error_indicators = ["error", "failed", "exception", "错误", "失败"]
        
        has_error = any(indicator in result.lower() for indicator in error_indicators)
        
        return {
            "success": not has_error,
            "result": result,
        }
    
    def _generate_suggestions(self, steps: List[TrajectoryStep]) -> List[str]:
        """生成改进建议"""
        suggestions = []
        
        # 检查是否有失败的步骤
        failed_steps = [s for s in steps if not s.success]
        if failed_steps:
            suggestions.append(f"有 {len(failed_steps)} 个步骤执行失败，建议检查相关工具")
        
        # 检查步骤数量
        if len(steps) > 10:
            suggestions.append("轨迹过长，建议优化执行路径")
        
        return suggestions
    
    def _calculate_efficiency(self, trajectory: List[Dict[str, Any]]) -> float:
        """计算效率"""
        if not trajectory:
            return 0.0
        
        # 简化的效率计算：基于成功步骤数和总步骤数
        success_steps = sum(1 for s in trajectory if not any(
            word in s.get("result", "").lower() 
            for word in ["error", "failed", "exception"]
        ))
        
        return success_steps / len(trajectory)