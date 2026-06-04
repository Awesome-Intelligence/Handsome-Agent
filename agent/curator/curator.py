"""
Curator - Self-Evolution Core
Trajectory Evaluation → Skill Synthesis → Auto-Learning
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from enum import Enum
import asyncio

from common.logging_manager import get_decision_logger


logger = get_decision_logger("Curator")


class EvaluationResult(str, Enum):
    """Evaluation result"""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class TrajectoryStep:
    """Trajectory step"""
    step_id: int
    thought: str
    action: str
    observation: str
    result: str
    success: bool


@dataclass
class EvaluationReport:
    """Evaluation report"""
    trajectory_id: str
    overall_result: EvaluationResult
    success_rate: float
    steps: List[TrajectoryStep]
    suggestions: List[str]
    metrics: Dict[str, Any]
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class SynthesizedSkill:
    """Synthesized skill"""
    name: str
    description: str
    trigger_patterns: List[str]
    action_template: str
    confidence: float
    source_trajectory: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class Curator:
    """
    Curator - 自我进化核心
    
    严格参考 Hermes 的 Curator 实现
    负责轨迹评估、技能合成、自动学习
    """
    
    def __init__(
        self,
        trajectory_recorder: "TrajectoryRecorder",
        skill_writer: "SkillWriter",
        enable_auto_learn: bool = True,
        min_confidence_threshold: float = 0.7,
    ):
        self.trajectory_recorder = trajectory_recorder
        self.skill_writer = skill_writer
        self.enable_auto_learn = enable_auto_learn
        self.min_confidence_threshold = min_confidence_threshold
        
        self._learned_skills: Dict[str, SynthesizedSkill] = {}
        self._evaluation_callbacks: List[Callable] = []
        self._learning_enabled = True
    
    def add_evaluation_callback(self, callback: Callable) -> None:
        """添加评估回调"""
        self._evaluation_callbacks.append(callback)
    
    async def process_trajectory(self, trajectory: Dict[str, Any]) -> Optional[SynthesizedSkill]:
        """
        Process trajectory - main entry

        1. Evaluate trajectory
        2. Generate suggestions
        3. Synthesize skill (if necessary)
        4. Auto learn (if enabled)

        Args:
            trajectory: Trajectory data

        Returns:
            SynthesizedSkill: Synthesized skill (if any)
        """
        logger.debug(f"Processing trajectory: {trajectory.get('trajectory_id', 'unknown')}")

        report = await self.evaluate(trajectory)

        for callback in self._evaluation_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(report)
                else:
                    callback(report)
            except Exception as e:
                logger.error(f"Callback error: {e}")

        if report.overall_result == EvaluationResult.SUCCESS:
            skill = await self.synthesize_skill(trajectory, report)
            if skill:
                if self.enable_auto_learn:
                    await self.learn_skill(skill)
                return skill

        return None

    async def auto_learn_from_trajectory(
        self,
        trajectory: Dict[str, Any],
    ) -> Optional[SynthesizedSkill]:
        """
        Auto learn from trajectory

        Use AutoLearnTrigger to determine if learning should occur,
        and use SkillSynthesizer to synthesize skill

        Args:
            trajectory: Execution trajectory

        Returns:
            SynthesizedSkill: Synthesized skill (if any)
        """
        skill = await self._auto_learn_trigger.learn_from_trajectory(trajectory)

        if skill and self.enable_auto_learn:
            await self.learn_skill(skill)
            return skill

        return None
    
    async def evaluate(self, trajectory: Dict[str, Any]) -> EvaluationReport:
        """
        评估轨迹
        
        分析每个步骤的成功/失败，计算整体评分
        """
        steps = []
        success_count = 0
        total_steps = 0
        
        for step in trajectory.get("steps", []):
            step_type = step.get("type")
            
            if step_type == "thought":
                thought = step.get("data", {}).get("reasoning", "")
                action = ""
                observation = ""
                result = ""
                success = True
            elif step_type == "action":
                thought = ""
                action = step.get("data", {}).get("tool_name", "")
                observation = ""
                result = ""
                success = True
            elif step_type == "observation":
                thought = ""
                action = ""
                observation = step.get("data", {}).get("result", "")
                result = step.get("data", {}).get("result", "")
                success = step.get("data", {}).get("success", True)
            else:
                continue
            
            steps.append(TrajectoryStep(
                step_id=step.get("step_id", 0),
                thought=thought,
                action=action,
                observation=observation,
                result=result,
                success=success,
            ))
            
            if step_type == "observation":
                total_steps += 1
                if success:
                    success_count += 1
        
        # 计算成功率
        success_rate = success_count / total_steps if total_steps > 0 else 0.0
        
        # 确定整体结果
        if success_rate == 1.0:
            overall = EvaluationResult.SUCCESS
        elif success_rate >= 0.5:
            overall = EvaluationResult.PARTIAL_SUCCESS
        elif total_steps == 0:
            overall = EvaluationResult.UNKNOWN
        else:
            overall = EvaluationResult.FAILURE
        
        # 生成建议
        suggestions = self._generate_suggestions(steps, overall)
        
        return EvaluationReport(
            trajectory_id=trajectory.get("trajectory_id", "unknown"),
            overall_result=overall,
            success_rate=success_rate,
            steps=steps,
            suggestions=suggestions,
            metrics={
                "total_steps": total_steps,
                "success_steps": success_count,
                "success_rate": success_rate,
            }
        )
    
    def _generate_suggestions(self, steps: List[TrajectoryStep], result: EvaluationResult) -> List[str]:
        """生成改进建议"""
        suggestions = []
        
        if result == EvaluationResult.FAILURE:
            suggestions.append("本次执行失败，建议检查工具参数或执行逻辑")
        
        if result == EvaluationResult.PARTIAL_SUCCESS:
            suggestions.append("部分成功，部分步骤可能存在问题，建议查看详细日志")
        
        failed_steps = [s for s in steps if not s.success]
        if failed_steps:
            suggestions.append(f"有 {len(failed_steps)} 个步骤执行失败")
        
        if len(steps) > 10:
            suggestions.append("轨迹较长，可能存在优化空间")
        
        return suggestions
    
    async def synthesize_skill(
        self, 
        trajectory: Dict[str, Any], 
        report: EvaluationReport
    ) -> Optional[SynthesizedSkill]:
        """
        合成技能
        
        从成功轨迹中提取可复用的技能
        """
        # 检查是否适合合成
        if not self._is_candidate_for_synthesis(trajectory):
            return None
        
        # 检查置信度
        if report.success_rate < self.min_confidence_threshold:
            return None
        
        # 提取信息
        name = self._generate_skill_name(trajectory)
        description = self._generate_skill_description(trajectory, report)
        trigger_patterns = self._extract_trigger_patterns(trajectory)
        action_template = self._generate_action_template(trajectory)
        
        skill = SynthesizedSkill(
            name=name,
            description=description,
            trigger_patterns=trigger_patterns,
            action_template=action_template,
            confidence=report.success_rate,
            source_trajectory=trajectory.get("trajectory_id", ""),
        )
        
        logger.info(f"Synthesized new skill: {skill.name}")
        self._learned_skills[skill.name] = skill
        
        return skill
    
    def _is_candidate_for_synthesis(self, trajectory: Dict[str, Any]) -> bool:
        """检查轨迹是否适合合成技能"""
        steps = trajectory.get("steps", [])
        
        # 需要有一定数量的步骤
        if len(steps) < 3:
            return False
        
        # 需要有工具调用
        has_action = any(s.get("type") == "action" for s in steps)
        if not has_action:
            return False
        
        return True
    
    def _generate_skill_name(self, trajectory: Dict[str, Any]) -> str:
        """生成技能名称"""
        user_input = trajectory.get("user_input", "")
        words = user_input.split()[:3]
        return f"auto_{'_'.join(words)}"
    
    def _generate_skill_description(self, trajectory: Dict[str, Any], report: EvaluationReport) -> str:
        """生成技能描述"""
        user_input = trajectory.get("user_input", "")
        actions = set()
        
        for step in trajectory.get("steps", []):
            if step.get("type") == "action":
                actions.add(step.get("data", {}).get("tool_name", ""))
        
        return f"自动合成的技能，用于: {user_input[:50]}... (使用工具: {', '.join(actions)})"
    
    def _extract_trigger_patterns(self, trajectory: Dict[str, Any]) -> List[str]:
        """提取触发模式"""
        patterns = []
        user_input = trajectory.get("user_input", "").lower()
        
        # 提取关键词
        words = user_input.split()
        patterns.extend([w for w in words if len(w) > 2])
        
        return list(set(patterns))[:10]
    
    def _generate_action_template(self, trajectory: Dict[str, Any]) -> str:
        """生成动作模板"""
        actions = []
        
        for step in trajectory.get("steps", []):
            if step.get("type") == "action":
                tool_name = step.get("data", {}).get("tool_name", "")
                params = step.get("data", {}).get("parameters", {})
                actions.append(f"{tool_name}: {params}")
        
        return "\n".join(actions)
    
    async def learn_skill(self, skill: SynthesizedSkill) -> bool:
        """
        学习技能
        
        将合成的技能写入 Skills 目录
        """
        if not self.enable_auto_learn:
            logger.info("Auto-learn disabled, skipping")
            return False
        
        try:
            # 使用 SkillWriter 写入
            await self.skill_writer.write(skill)
            logger.info(f"Learned new skill: {skill.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to learn skill: {e}")
            return False
    
    async def learn_from_feedback(self, trajectory_id: str, feedback: str) -> Optional[SynthesizedSkill]:
        """
        Learn from user feedback
        
        Args:
            trajectory_id: Trajectory ID
            feedback: Feedback content
        """
        trajectory = self.trajectory_recorder.load_trajectory(trajectory_id)
        if not trajectory:
            return None
        
        # 根据反馈更新轨迹
        if feedback.lower() in ["good", "success", "好", "成功"]:
            await self.trajectory_recorder.mark_trajectory(trajectory_id, "success")
            return await self.process_trajectory(trajectory.to_dict())
        
        return None
    
    def get_learned_skills(self) -> List[SynthesizedSkill]:
        """Get learned skills"""
        return list(self._learned_skills.values())
    
    def get_skill_by_name(self, name: str) -> Optional[SynthesizedSkill]:
        """Get skill by name"""
        return self._learned_skills.get(name)
    
    def enable_learning(self) -> None:
        """Enable learning"""
        self._learning_enabled = True
        logger.info("Learning enabled")
    
    def disable_learning(self) -> None:
        """Disable learning"""
        self._learning_enabled = False
        logger.info("Learning disabled")