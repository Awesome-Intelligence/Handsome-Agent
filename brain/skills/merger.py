"""
技能合并器 (Skill Merger)

参考 Hermes Agent 的 Curator umbrella building 策略
自动识别相似技能并合并到伞形技能中

合并策略:
1. 识别前缀聚类 (prefix clusters)
2. 合并到现有伞形技能
3. 创建新的伞形技能
4. 降级为 references/templates/scripts
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set, Tuple
import logging
from pathlib import Path
import re


logger = logging.getLogger(__name__)


@dataclass
class SkillInfo:
    """技能信息"""
    name: str
    path: Path
    description: str = ""
    tags: List[str] = field(default_factory=list)
    trigger_patterns: List[str] = field(default_factory=list)
    content: str = ""


@dataclass
class SkillCluster:
    """技能聚类"""
    name: str
    skills: List[SkillInfo]
    common_prefix: str
    umbrella_skill: Optional[SkillInfo] = None


@dataclass
class MergeResult:
    """合并结果"""
    merged_into: Optional[str]
    action: str
    reason: str
    source_skill: str


class SkillMerger:
    """
    技能合并器

    功能:
    1. 识别前缀聚类
    2. 识别伞形技能
    3. 合并相似技能到伞形
    4. 创建新的伞形技能
    """

    def __init__(
        self,
        min_cluster_size: int = 2,
        similarity_threshold: float = 0.6,
    ):
        self.min_cluster_size = min_cluster_size
        self.similarity_threshold = similarity_threshold
        self._clusters: List[SkillCluster] = []
        self._merge_results: List[MergeResult] = []

    def identify_prefix_clusters(self, skills: List[SkillInfo]) -> List[SkillCluster]:
        """
        识别前缀聚类

        Args:
            skills: 技能列表

        Returns:
            聚类列表
        """
        prefix_map: Dict[str, List[SkillInfo]] = {}

        for skill in skills:
            first_word = skill.name.split("-")[0].split("_")[0].lower()
            if first_word not in prefix_map:
                prefix_map[first_word] = []
            prefix_map[first_word].append(skill)

        clusters = []
        for prefix, cluster_skills in prefix_map.items():
            if len(cluster_skills) >= self.min_cluster_size:
                cluster = SkillCluster(
                    name=prefix,
                    skills=cluster_skills,
                    common_prefix=prefix,
                )
                clusters.append(cluster)
                logger.info(f"Identified cluster: {prefix} with {len(cluster_skills)} skills")

        self._clusters = clusters
        return clusters

    def identify_umbrella_skill(self, cluster: SkillCluster) -> Optional[SkillInfo]:
        """
        识别伞形技能

        伞形技能的特征:
        - 名称更通用
        - 描述覆盖多个子技能
        - 已经是多个技能的合并目标

        Args:
            cluster: 技能聚类

        Returns:
            伞形技能(如果有)
        """
        if not cluster.skills:
            return None

        skills_sorted = sorted(
            cluster.skills,
            key=lambda s: len(s.description),
            reverse=True
        )

        most_generic = skills_sorted[0]
        avg_desc_length = sum(len(s.description) for s in skills_sorted) / len(skills_sorted)

        if len(most_generic.description) > avg_desc_length * 1.5:
            return most_generic

        return None

    def calculate_similarity(self, skill1: SkillInfo, skill2: SkillInfo) -> float:
        """
        计算两个技能的相似度

        基于:
        - 名称相似度
        - 描述相似度
        - 标签重叠
        - 触发模式重叠

        Args:
            skill1: 技能1
            skill2: 技能2

        Returns:
            相似度分数 (0-1)
        """
        score = 0.0

        words1 = set(skill1.name.replace("-", " ").replace("_", " ").lower().split())
        words2 = set(skill2.name.replace("-", " ").replace("_", " ").lower().split())
        if words1 & words2:
            score += 0.4

        tag1 = set(t.lower() for t in skill1.tags)
        tag2 = set(t.lower() for t in skill2.tags)
        if tag1 & tag2:
            score += 0.3 * len(tag1 & tag2) / max(len(tag1 | tag2), 1)

        pattern1 = set(p.lower() for p in skill1.trigger_patterns)
        pattern2 = set(p.lower() for p in skill2.trigger_patterns)
        if pattern1 & pattern2:
            score += 0.3 * len(pattern1 & pattern2) / max(len(pattern1 | pattern2), 1)

        return min(score, 1.0)

    def find_similar_skills(self, skill: SkillInfo, candidates: List[SkillInfo]) -> List[Tuple[SkillInfo, float]]:
        """
        找到与指定技能相似的技能

        Args:
            skill: 目标技能
            candidates: 候选技能列表

        Returns:
            相似技能列表,按相似度降序
        """
        similarities = []
        for candidate in candidates:
            if candidate.name == skill.name:
                continue
            sim = self.calculate_similarity(skill, candidate)
            if sim >= self.similarity_threshold:
                similarities.append((candidate, sim))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities

    def plan_merges(
        self,
        cluster: SkillCluster,
        existing_umbrellas: Optional[Set[str]] = None
    ) -> List[Tuple[SkillInfo, Optional[SkillInfo]]]:
        """
        规划合并

        Args:
            cluster: 技能聚类
            existing_umbrellas: 现有伞形技能名称集合

        Returns:
            合并计划列表 (技能, 目标伞形技能)
        """
        existing_umbrellas = existing_umbrellas or set()

        umbrella = self.identify_umbrella_skill(cluster)
        merge_plan = []

        if umbrella and umbrella.name in existing_umbrellas:
            merge_plan.append((umbrella, umbrella))
            for skill in cluster.skills:
                if skill.name != umbrella.name:
                    merge_plan.append((skill, umbrella))
        else:
            for skill in cluster.skills:
                similar = self.find_similar_skills(skill, cluster.skills)
                if similar:
                    merge_plan.append((skill, similar[0][0]))
                else:
                    merge_plan.append((skill, None))

        return merge_plan

    def merge_skills(
        self,
        source: SkillInfo,
        target: SkillInfo,
        target_dir: Path
    ) -> bool:
        """
        执行合并

        将源技能合并到目标伞形技能中:
        1. 在目标技能的 SKILL.md 中添加章节
        2. 移动源技能到 references/ 子目录

        Args:
            source: 源技能
            target: 目标伞形技能
            target_dir: 技能目录

        Returns:
            是否成功
        """
        try:
            references_dir = target_dir / "references"
            references_dir.mkdir(exist_ok=True)

            ref_file = references_dir / f"{source.name}.md"
            content = f"""# {source.name}

{source.description}

## 触发模式
{', '.join(source.trigger_patterns)}

## 原始内容
{source.content}
"""
            ref_file.write_text(content, encoding="utf-8")

            logger.info(f"Merged {source.name} into {target.name} as references/{source.name}.md")
            return True

        except Exception as e:
            logger.error(f"Failed to merge {source.name} into {target.name}: {e}")
            return False

    def create_umbrella_skill(
        self,
        cluster: SkillCluster,
        skills_dir: Path
    ) -> Optional[SkillInfo]:
        """
        创建新的伞形技能

        Args:
            cluster: 技能聚类
            skills_dir: 技能根目录

        Returns:
            创建的伞形技能(如果有)
        """
        try:
            umbrella_name = f"{cluster.common_prefix}-umbrella"
            umbrella_dir = skills_dir / umbrella_name
            umbrella_dir.mkdir(parents=True, exist_ok=True)

            skill_md_content = f"""# {umbrella_name.title().replace('-', ' ')}

自动合成的伞形技能,包含以下子技能:
{chr(10).join(f"- {s.name}: {s.description}" for s in cluster.skills)}

## 触发模式
{', '.join(p for s in cluster.skills for p in s.trigger_patterns)}

## 使用说明

本技能是以下技能的统一入口:

"""
            for skill in cluster.skills:
                skill_md_content += f"### {skill.name}\n{skill.description}\n\n"

            skill_md_content += """
## 子技能

子技能位于 references/ 目录中。
"""

            (umbrella_dir / "SKILL.md").write_text(skill_md_content, encoding="utf-8")

            (umbrella_dir / "references").mkdir(exist_ok=True)
            for skill in cluster.skills:
                if skill.path.exists():
                    import shutil
                    ref_path = umbrella_dir / "references" / skill.path.name
                    shutil.move(str(skill.path), str(ref_path))

            logger.info(f"Created umbrella skill: {umbrella_name}")
            return SkillInfo(
                name=umbrella_name,
                path=umbrella_dir,
                description=f"伞形技能: {cluster.common_prefix} 系列",
            )

        except Exception as e:
            logger.error(f"Failed to create umbrella skill: {e}")
            return None

    def perform_consolidation(
        self,
        skills: List[SkillInfo],
        skills_dir: Path,
        dry_run: bool = True
    ) -> List[MergeResult]:
        """
        执行技能整合

        完整流程:
        1. 识别前缀聚类
        2. 识别伞形技能
        3. 规划合并
        4. 执行合并

        Args:
            skills: 技能列表
            skills_dir: 技能目录
            dry_run: 是否只生成报告

        Returns:
            合并结果列表
        """
        self._clusters = self.identify_prefix_clusters(skills)
        self._merge_results = []

        existing_umbrellas: Set[str] = set()

        for cluster in self._clusters:
            umbrella = self.identify_umbrella_skill(cluster)
            if umbrella:
                existing_umbrellas.add(umbrella.name)

        for cluster in self._clusters:
            umbrella = self.identify_umbrella_skill(cluster)
            merge_plan = self.plan_merges(cluster, existing_umbrellas)

            if not umbrella and len(merge_plan) >= self.min_cluster_size:
                if not dry_run:
                    new_umbrella = self.create_umbrella_skill(cluster, skills_dir)
                    if new_umbrella:
                        existing_umbrellas.add(new_umbrella.name)
                        umbrella = new_umbrella

                self._merge_results.append(MergeResult(
                    merged_into=umbrella.name if umbrella else "new-umbrella",
                    action="create-umbrella" if not umbrella else "none",
                    reason=f"Found {len(cluster.skills)} skills with prefix '{cluster.common_prefix}'",
                    source_skill="",
                ))

            for skill, target in merge_plan:
                if target and target.name != skill.name:
                    if not dry_run:
                        self.merge_skills(skill, target, skills_dir)

                    self._merge_results.append(MergeResult(
                        merged_into=target.name,
                        action="merge",
                        reason=f"Similar to {target.name}",
                        source_skill=skill.name,
                    ))

        return self._merge_results

    def get_clusters(self) -> List[SkillCluster]:
        """获取识别的聚类"""
        return self._clusters

    def get_merge_results(self) -> List[MergeResult]:
        """获取合并结果"""
        return self._merge_results

    def generate_report(self) -> str:
        """
        生成合并报告

        Returns:
            报告文本
        """
        lines = ["# Skill Consolidation Report\n"]

        lines.append(f"## Identified Clusters: {len(self._clusters)}\n")
        for cluster in self._clusters:
            umbrella = self.identify_umbrella_skill(cluster)
            umbrella_status = f"(umbrella: {umbrella.name})" if umbrella else "(no umbrella)"
            lines.append(f"- {cluster.common_prefix}: {len(cluster.skills)} skills {umbrella_status}")

        lines.append(f"\n## Merge Results: {len(self._merge_results)}\n")
        for result in self._merge_results:
            lines.append(f"- {result.source_skill} → {result.merged_into} ({result.action})")

        return "\n".join(lines)


def load_skills_from_directory(skills_dir: Path) -> List[SkillInfo]:
    """
    从目录加载技能信息

    Args:
        skills_dir: 技能根目录

    Returns:
        技能信息列表
    """
    skills = []

    if not skills_dir.exists():
        return skills

    for skill_path in skills_dir.iterdir():
        if not skill_path.is_dir():
            continue

        skill_md = skill_path / "SKILL.md"
        if not skill_md.exists():
            continue

        try:
            content = skill_md.read_text(encoding="utf-8")

            name = skill_path.name
            description = ""

            lines = content.split("\n")
            in_frontmatter = False
            for line in lines:
                if line.strip() == "---":
                    if in_frontmatter:
                        break
                    in_frontmatter = True
                    continue
                if line.startswith("description:"):
                    description = line.split(":", 1)[1].strip()

            if not description:
                for line in lines:
                    if line.startswith("# "):
                        continue
                    if line.strip():
                        description = line.strip()
                        break

            skills.append(SkillInfo(
                name=name,
                path=skill_path,
                description=description,
                content=content,
            ))
        except Exception as e:
            logger.warning(f"Failed to load skill from {skill_path}: {e}")

    return skills
