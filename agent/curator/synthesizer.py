"""
Skill Synthesizer - Enhanced Version
Uses LLM to assist extracting reusable skills from trajectories
Reference Hermes's skill learning mechanism
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from common.logging_manager import get_decision_logger


logger = get_decision_logger(__name__)


@dataclass
class SynthesizedSkill:
    """合成的技能"""
    name: str
    description: str
    trigger_patterns: List[str]
    action_template: str
    confidence: float
    source_trajectory: str = ""
    quality_score: float = 0.0
    tags: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)


class SkillSynthesizer:
    """技能合成器 - 支持 LLM 辅助"""

    def __init__(
        self,
        llm_provider: Optional[Any] = None,
        llm_client: Optional[Any] = None
    ):
        self._patterns: Dict[str, List[str]] = {}
        self.llm_provider = llm_provider
        self._llm_client = llm_client
    
    def set_llm_client(self, client: Any) -> None:
        """设置 LLM 客户端"""
        self._llm_client = client

    async def synthesize(
        self,
        trajectory: Dict[str, Any],
        context: Dict[str, Any] = None,
    ) -> Optional[SynthesizedSkill]:
        """
        从轨迹中合成技能

        策略：
        1. 分析成功的轨迹
        2. 提取通用的触发模式
        3. 生成可复用的技能模板
        4. 使用 LLM 增强（如可用）
        """
        context = context or {}

        if not self._is_candidate_for_synthesis(trajectory):
            return None

        user_input = trajectory.get("user_input", "")
        steps = trajectory.get("steps", [])

        trigger_patterns = self._extract_trigger_patterns(trajectory)
        action_template = self._generate_action_template(trajectory)
        name = self._generate_name(trajectory, context)
        description = self._generate_description(trajectory)
        confidence = self._calculate_confidence(trajectory)

        skill = SynthesizedSkill(
            name=name,
            description=description,
            trigger_patterns=trigger_patterns,
            action_template=action_template,
            confidence=confidence,
            source_trajectory=trajectory.get("trajectory_id", ""),
        )

        if self.llm_provider:
            try:
                enhanced = await self._enhance_with_llm(skill, trajectory)
                if enhanced:
                    return enhanced
            except Exception as e:
                logger.warning(f"LLM enhancement failed: {e}")

        skill.quality_score = self._assess_quality(skill)
        return skill

    async def _enhance_with_llm(
        self,
        skill: SynthesizedSkill,
        trajectory: Dict[str, Any],
    ) -> Optional[SynthesizedSkill]:
        """使用 LLM 增强技能"""
        from agent.llm import LLMTaskType
        
        prompt = f"""分析以下轨迹，提取一个可复用的技能：

用户输入: {trajectory.get('user_input', '')}

执行步骤:
{self._format_steps(trajectory.get('steps', []))}

请生成：
1. 技能名称 (用英文，用下划线分隔)
2. 技能描述 (用中文，简洁明了)
3. 触发模式 (3-5个关键词)
4. 质量评分 (0-1之间)

以 JSON 格式返回：
{{"name": "...", "description": "...", "trigger_patterns": [...], "quality_score": 0.x}}
"""

        try:
            # 优先使用 LLMClient
            if self._llm_client:
                response = await self._llm_client.auxiliary_call(
                    task=LLMTaskType.SKILL_SYNTHESIS,
                    prompt=prompt
                )
            elif self.llm_provider:
                # 降级：直接使用 provider
                response = await self.llm_provider.generate(prompt)
            else:
                return None
            
            import json
            data = json.loads(response)

            skill.name = data.get("name", skill.name)
            skill.description = data.get("description", skill.description)
            skill.trigger_patterns = data.get("trigger_patterns", skill.trigger_patterns)
            skill.quality_score = data.get("quality_score", 0.5)

            return skill
        except Exception as e:
            logger.warning(f"LLM enhancement parse failed: {e}")
            return None

    def _format_steps(self, steps: List[Dict]) -> str:
        """格式化步骤"""
        lines = []
        for i, step in enumerate(steps[:10], 1):
            step_type = step.get("type", "unknown")
            data = step.get("data", {})
            if step_type == "thought":
                lines.append(f"{i}. 思考: {data.get('reasoning', '')[:100]}")
            elif step_type == "action":
                lines.append(f"{i}. 行动: {data.get('tool_name', '')}({data.get('parameters', {})})")
            elif step_type == "observation":
                lines.append(f"{i}. 观察: {data.get('result', '')[:100]}")
        return "\n".join(lines)

    def _is_candidate_for_synthesis(self, trajectory: Dict[str, Any]) -> bool:
        """检查是否适合提取技能"""
        steps = trajectory.get("steps", [])
        if len(steps) < 3:
            return False

        actions = [s for s in steps if s.get("type") == "action"]
        if len(actions) < 2:
            return False

        user_input = trajectory.get("user_input", "")
        if not user_input or len(user_input) < 5:
            return False

        return True

    def _extract_trigger_patterns(self, trajectory: Dict[str, Any]) -> List[str]:
        """提取触发模式"""
        patterns = []

        user_input = trajectory.get("user_input", "").lower()
        words = user_input.split()

        for word in words:
            clean = "".join(c for c in word if c.isalnum())
            if len(clean) > 2 and clean not in ["帮我", "请", "我想", "帮我", "给我"]:
                patterns.append(clean)

        steps = trajectory.get("steps", [])
        for step in steps:
            if step.get("type") == "action":
                tool_name = step.get("data", {}).get("tool_name", "")
                if tool_name:
                    patterns.append(tool_name)

        return list(set(patterns))[:10]

    def _generate_action_template(self, trajectory: Dict[str, Any]) -> str:
        """生成动作模板"""
        actions = []

        steps = trajectory.get("steps", [])
        for step in steps:
            if step.get("type") == "action":
                tool_name = step.get("data", {}).get("tool_name", "")
                params = step.get("data", {}).get("parameters", {})

                if params:
                    param_str = ", ".join(f"{k}={v}" for k, v in params.items())
                    actions.append(f"- {tool_name}({param_str})")
                else:
                    actions.append(f"- {tool_name}()")

        return "\n".join(actions) if actions else ""

    def _generate_name(self, trajectory: Dict[str, Any], context: Dict[str, Any]) -> str:
        """生成技能名称"""
        user_input = trajectory.get("user_input", "")

        words = []
        for word in user_input.split():
            clean = "".join(c for c in word if c.isalnum())
            if len(clean) > 1:
                words.append(clean.lower())
            if len(words) >= 3:
                break

        if words:
            return f"auto_{'_'.join(words[:3])}"

        return "auto_skill"

    def _generate_description(self, trajectory: Dict[str, Any]) -> str:
        """生成技能描述"""
        user_input = trajectory.get("user_input", "")
        steps = trajectory.get("steps", [])

        action_count = len([s for s in steps if s.get("type") == "action"])

        description = f"自动合成的技能，用于: {user_input[:50]}"
        if user_input[50:]:
            description += "..."

        description += f"\n\n包含 {action_count} 个操作步骤。"

        return description

    def _calculate_confidence(self, trajectory: Dict[str, Any]) -> float:
        """计算置信度"""
        steps = trajectory.get("steps", [])
        action_count = len([s for s in steps if s.get("type") == "action"])

        base = min(action_count * 0.1, 0.5)

        success_steps = [s for s in steps if s.get("type") == "observation" and s.get("data", {}).get("success", False)]
        if steps:
            base += len(success_steps) / len(steps) * 0.5

        return min(base, 0.9)

    def _assess_quality(self, skill: SynthesizedSkill) -> float:
        """评估技能质量"""
        score = 0.0

        if len(skill.trigger_patterns) >= 3:
            score += 0.3

        if len(skill.description) >= 20:
            score += 0.2

        if skill.action_template:
            action_count = len([l for l in skill.action_template.split("\n") if l.strip()])
            if action_count >= 2:
                score += 0.3

        if skill.confidence >= 0.7:
            score += 0.2

        return min(score, 1.0)


class AutoLearnTrigger:
    """
    自动学习触发器

    参考 Hermes 的自动学习机制：
    1. 成功执行后触发
    2. 用户正反馈后触发
    3. 重复模式识别后触发
    """

    def __init__(self, synthesizer: SkillSynthesizer):
        self.synthesizer = synthesizer
        self._pattern_cache: Dict[str, int] = {}
        self._min_pattern_occurrences = 2
        self._min_success_rate = 0.8

    def should_learn_from_trajectory(self, trajectory: Dict[str, Any]) -> bool:
        """
        判断是否应该从轨迹学习

        条件：
        1. 轨迹执行成功
        2. 包含足够的步骤
        3. 用户标记为"好"或"有用"
        """
        steps = trajectory.get("steps", [])
        if len(steps) < 3:
            return False

        observations = [s for s in steps if s.get("type") == "observation"]
        if not observations:
            return False

        success_count = sum(1 for o in observations if o.get("data", {}).get("success", False))
        success_rate = success_count / len(observations)

        if success_rate < self._min_success_rate:
            return False

        if trajectory.get("user_feedback") in ["good", "great", "perfect", "好", "很好", "完美"]:
            return True

        user_input = trajectory.get("user_input", "")
        if user_input:
            pattern_key = user_input[:30].lower()
            self._pattern_cache[pattern_key] = self._pattern_cache.get(pattern_key, 0) + 1

            if self._pattern_cache[pattern_key] >= self._min_pattern_occurrences:
                return True

        return False

    async def learn_from_trajectory(
        self,
        trajectory: Dict[str, Any],
        context: Dict[str, Any] = None,
    ) -> Optional[SynthesizedSkill]:
        """
        Learn skill from trajectory

        Args:
            trajectory: Execution trajectory
            context: Additional context

        Returns:
            Synthesized skill (if any)
        """
        if not self.should_learn_from_trajectory(trajectory):
            return None

        skill = await self.synthesizer.synthesize(trajectory, context)

        if skill and skill.quality_score >= 0.5:
            logger.info(f"Auto-learned skill: {skill.name} (quality: {skill.quality_score:.2f})")
            return skill

        return None

    def record_pattern(self, pattern: str) -> None:
        """Record usage pattern"""
        self._pattern_cache[pattern] = self._pattern_cache.get(pattern, 0) + 1

    def get_frequent_patterns(self, min_count: int = 2) -> List[str]:
        """Get frequently used patterns"""
        return [p for p, c in self._pattern_cache.items() if c >= min_count]
