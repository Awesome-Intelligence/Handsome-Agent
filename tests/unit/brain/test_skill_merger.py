"""
技能合并器测试
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from brain.skills.merger import SkillMerger, SkillInfo, SkillCluster, load_skills_from_directory


@pytest.fixture
def temp_skills_dir():
    """创建临时技能目录"""
    temp_dir = Path(tempfile.mkdtemp())
    skills_dir = temp_dir / "skills"
    skills_dir.mkdir()
    yield skills_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def merger():
    """创建合并器实例"""
    return SkillMerger(min_cluster_size=2, similarity_threshold=0.4)


def test_identify_prefix_clusters(merger):
    """测试前缀聚类识别"""
    skills = [
        SkillInfo(name="hermes-config-setup", path=Path("test")),
        SkillInfo(name="hermes-config-update", path=Path("test")),
        SkillInfo(name="hermes-dashboard-start", path=Path("test")),
        SkillInfo(name="gateway-test", path=Path("test")),
    ]

    clusters = merger.identify_prefix_clusters(skills)

    assert len(clusters) >= 1
    hermes_cluster = next((c for c in clusters if c.common_prefix == "hermes"), None)
    assert hermes_cluster is not None
    assert len(hermes_cluster.skills) == 3


def test_identify_umbrella_skill(merger):
    """测试伞形技能识别"""
    skills = [
        SkillInfo(
            name="umbrella-skill",
            path=Path("test"),
            description="This is a comprehensive skill that covers multiple use cases",
        ),
        SkillInfo(
            name="umbrella-sub1",
            path=Path("test"),
            description="Simple skill",
        ),
        SkillInfo(
            name="umbrella-sub2",
            path=Path("test"),
            description="Another simple skill",
        ),
    ]

    cluster = SkillCluster(
        name="umbrella",
        skills=skills,
        common_prefix="umbrella",
    )

    umbrella = merger.identify_umbrella_skill(cluster)

    assert umbrella is not None
    assert umbrella.name == "umbrella-skill"


def test_calculate_similarity(merger):
    """测试相似度计算"""
    skill1 = SkillInfo(
        name="python-web-scraper",
        path=Path("test"),
        tags=["python", "web", "scraper"],
        trigger_patterns=["scrape", "web data"],
    )

    skill2 = SkillInfo(
        name="python-data-collector",
        path=Path("test"),
        tags=["python", "data", "collector"],
        trigger_patterns=["collect", "data"],
    )

    similarity = merger.calculate_similarity(skill1, skill2)

    assert 0.3 < similarity < 1.0


def test_find_similar_skills(merger):
    """测试查找相似技能"""
    skills = [
        SkillInfo(name="test-skill1", path=Path("test"), description="Python web scraping"),
        SkillInfo(name="test-skill2", path=Path("test"), description="Python data collection"),
        SkillInfo(name="test-skill3", path=Path("test"), description="Java web scraping"),
    ]

    target = skills[0]
    similar = merger.find_similar_skills(target, skills)

    assert len(similar) >= 1
    assert similar[0][0].name == "test-skill2"


def test_plan_merges(merger):
    """测试合并规划"""
    skills = [
        SkillInfo(name="hermes-auth-login", path=Path("test"), description="Login"),
        SkillInfo(name="hermes-auth-logout", path=Path("test"), description="Logout"),
        SkillInfo(name="hermes-auth-status", path=Path("test"), description="Check status"),
    ]

    clusters = merger.identify_prefix_clusters(skills)
    assert len(clusters) == 1

    cluster = clusters[0]
    merge_plan = merger.plan_merges(cluster)

    assert len(merge_plan) >= 2


def test_load_skills_from_directory(temp_skills_dir):
    """测试从目录加载技能"""
    skill1_dir = temp_skills_dir / "test-skill1"
    skill1_dir.mkdir()
    (skill1_dir / "SKILL.md").write_text(
        """---
description: Test skill 1
---

# Test Skill 1

This is a test skill.
""",
        encoding="utf-8"
    )

    skill2_dir = temp_skills_dir / "test-skill2"
    skill2_dir.mkdir()
    (skill2_dir / "SKILL.md").write_text(
        """# Test Skill 2

This is another test skill.
""",
        encoding="utf-8"
    )

    skills = load_skills_from_directory(temp_skills_dir)

    assert len(skills) == 2
    names = [s.name for s in skills]
    assert "test-skill1" in names
    assert "test-skill2" in names


def test_perform_consolidation_dry_run(merger, temp_skills_dir):
    """测试干运行整合"""
    for i in range(3):
        skill_dir = temp_skills_dir / f"hermes-test-{i}"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            f"# Hermes Test {i}\n\nTest skill {i}",
            encoding="utf-8"
        )

    skills = load_skills_from_directory(temp_skills_dir)
    results = merger.perform_consolidation(skills, temp_skills_dir, dry_run=True)

    assert len(results) > 0
    assert any(r.action == "create-umbrella" for r in results)


def test_generate_report(merger, temp_skills_dir):
    """测试生成报告"""
    for i in range(3):
        skill_dir = temp_skills_dir / f"hermes-test-{i}"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            f"# Hermes Test {i}\n\nTest skill {i}",
            encoding="utf-8"
        )

    skills = load_skills_from_directory(temp_skills_dir)
    merger.perform_consolidation(skills, temp_skills_dir, dry_run=True)

    report = merger.generate_report()

    assert "Consolidation Report" in report
    assert "Identified Clusters" in report


def test_skill_clusters_getter(merger):
    """测试获取聚类"""
    assert merger.get_clusters() == []


def test_merge_results_getter(merger):
    """测试获取合并结果"""
    assert merger.get_merge_results() == []


def test_single_skill_not_clustered(merger):
    """测试单个技能不会被聚类"""
    skills = [
        SkillInfo(name="unique-skill", path=Path("test")),
    ]

    clusters = merger.identify_prefix_clusters(skills)

    assert len(clusters) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
